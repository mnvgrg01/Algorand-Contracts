import beaker
import pyteal as pt
from beaker.lib.storage import BoxMapping


class ProcessRecord(pt.abi.NamedTuple):
    state: pt.abi.Field[pt.abi.String]
    asset: pt.abi.Field[pt.abi.Uint64]
    seller: pt.abi.Field[pt.abi.Address]
    buyer: pt.abi.Field[pt.abi.Address]
    copies: pt.abi.Field[pt.abi.Uint64]


class ListRecord(pt.abi.NamedTuple):
    copies: pt.abi.Field[pt.abi.Uint64]
    price: pt.abi.Field[pt.abi.Uint64]
    primary: pt.abi.Field[pt.abi.Bool]


class AssetRecord(pt.abi.NamedTuple):
    lotsize: pt.abi.Field[pt.abi.Uint64]
    coolingtime: pt.abi.Field[pt.abi.Uint64]


class AssetState:
    asset_records = BoxMapping(pt.abi.Uint64, AssetRecord)
    list_records = BoxMapping(pt.abi.Address, ListRecord)
    process_record = BoxMapping(pt.abi.Uint64, ProcessRecord)
    process_id = beaker.GlobalStateValue(
        stack_type=pt.TealType.uint64, default=pt.Int(0)
    )


app = beaker.Application(
    "asset",
    state=AssetState(),
    build_options=beaker.BuildOptions(scratch_slots=False),
)


@app.create(bare=True)
def create() -> pt.Expr:
    return pt.Seq(app.initialize_global_state(), app.initialize_local_state())


##################### Box ops ##############################


@app.external
def add_asset_listing(
    asset: pt.abi.Asset,
    copies: pt.abi.Uint64,
    price: pt.abi.Uint64,
    lotsize: pt.abi.Uint64,
    coolingtime: pt.abi.Uint64,
    primary: pt.abi.Bool,
) -> pt.Expr:
    account_balance = pt.AssetHolding.balance(pt.Txn.sender(), asset.asset_id())
    return pt.Seq(
        account_balance,
        pt.Assert(
            account_balance.hasValue(),
            comment="Sender does not have the asset balance.",
        ),
        pt.Assert(
            copies.get() <= account_balance.value(),
            comment="Sender does not have enough copies to list",
        ),
        (lr := ListRecord()).set(copies, price, primary),
        app.state.list_records[pt.Txn.sender()].set(lr),
        (asset_id := pt.abi.Uint64()).set(asset.asset_id()),
        (ar := AssetRecord()).set(lotsize, coolingtime),
        app.state.asset_records[asset_id].set(ar),
    )


@app.external
def get_asset(asset: pt.abi.Asset, *, output: AssetRecord) -> pt.Expr:
    return pt.Seq(
        (asset_id := pt.abi.Uint64()).set(asset.asset_id()),
        app.state.asset_records[asset_id].store_into(output),
    )


@app.external
def get_listing(address: pt.abi.Address, *, output: ListRecord) -> pt.Expr:
    return pt.Seq(
        app.state.list_records[address].store_into(output),
    )


################ Drop Asset ###################


@app.external
def get_processid(*, output: pt.abi.Uint64) -> pt.Expr:
    return output.set(app.state.process_id)


@app.external
def purchase_asset(copies: pt.abi.Uint64, asset: pt.abi.Asset) -> pt.Expr:
    # AssetRecord()
    pt.AssetHolding.balance(pt.Txn.accounts[1], asset.asset_id())
    buyer = pt.abi.Address()
    seller = pt.abi.Address()
    state = pt.abi.String()
    asset_id = pt.abi.Uint64()
    return pt.Seq(
        buyer.set(pt.Txn.accounts[1]),
        seller.set(pt.Txn.accounts[2]),
        state.set("AWAIT_CONFIRM"),
        asset_id.set(asset.asset_id()),
        pt.Assert(
            app.state.list_records[buyer].exists(),
            comment="Asset is not listed.",
        ),
        # (app.state.asset_records[asset_id].store_into(ar)),
        pt.InnerTxnBuilder.Execute(
            {
                pt.TxnField.type_enum: pt.TxnType.AssetTransfer,
                pt.TxnField.asset_receiver: pt.Global.current_application_address(),
                pt.TxnField.asset_sender: pt.Txn.accounts[1],
                pt.TxnField.asset_amount: copies.get(),
                pt.TxnField.xfer_asset: asset.asset_id(),
            }
        ),
        (pr := ProcessRecord()).set(
            state,
            asset_id,
            buyer,
            seller,
            copies,
        ),
        (processid := pt.abi.Uint64()).set(app.state.process_id.get() + pt.Int(1)),
        app.state.process_record[processid].set(pr),
        app.state.process_id.set(processid.get()),
    )


@app.external
def get_process_record(processid: pt.abi.Uint64, *, output: ProcessRecord) -> pt.Expr:
    return app.state.process_record[processid].store_into(output)


################ Approve Asset #################


@app.external
def approve_asset(processid: pt.abi.Uint64) -> pt.Expr:
    actual_state = pt.abi.String()
    desired_state = pt.abi.String()
    buyer = pt.abi.Address()
    copies = pt.abi.Uint64()
    asset_id = pt.abi.Uint64()
    return pt.Seq(
        desired_state.set("AWAIT_CONFIRM"),
        pt.Assert(
            app.state.process_record[processid].exists(),
            comment="Process id invalid.",
        ),
        # (app.state.asset_records[asset_id].store_into(ar)),
        (pr := ProcessRecord()).decode(app.state.process_record[processid].get()),
        pr.state.store_into(actual_state),
        pr.buyer.store_into(buyer),
        pr.copies.store_into(copies),
        pr.asset.store_into(asset_id),
        pt.Assert(
            buyer.get() == pt.Txn.accounts[1],
            comment="Receiver address doesn't match.",
        ),
        # pt.Assert(
        #     asset_id.get() == pt.Txn.assets,
        #     comment="Receiver address doesn't match.",
        # ),
        pt.Assert(
            actual_state.get() == desired_state.get(), comment="State does not match"
        ),
        pt.InnerTxnBuilder.Execute(
            {
                pt.TxnField.type_enum: pt.TxnType.AssetTransfer,
                pt.TxnField.asset_receiver: pt.Txn.accounts[1],
                pt.TxnField.asset_sender: pt.Global.current_application_address(),
                pt.TxnField.asset_amount: copies.get(),
                pt.TxnField.xfer_asset: asset_id.get(),
            }
        ),
        pt.Pop(app.state.process_record[processid].delete()),
    )


########### Mint ###########


@app.external
def mint_asset(
    name: pt.abi.String, url: pt.abi.String, *, output: pt.abi.Uint64
) -> pt.Expr:
    return pt.Seq(
        pt.InnerTxnBuilder.Execute(
            {
                pt.TxnField.type_enum: pt.TxnType.AssetConfig,
                pt.TxnField.config_asset_total: pt.Int(1),
                pt.TxnField.config_asset_default_frozen: pt.Int(1),
                pt.TxnField.config_asset_decimals: pt.Int(0),
                pt.TxnField.config_asset_unit_name: name.get(),
                pt.TxnField.config_asset_name: name.get(),
                pt.TxnField.config_asset_url: url.get(),
                pt.TxnField.config_asset_manager: pt.Global.current_application_address(),
                pt.TxnField.config_asset_reserve: pt.Global.current_application_address(),
                pt.TxnField.config_asset_freeze: pt.Global.current_application_address(),
                pt.TxnField.config_asset_clawback: pt.Global.current_application_address(),
            }
        ),
        output.set(pt.InnerTxn.created_asset_id()),
    )


#   app.state.nftOwner.set(pt.InnerTxn.created_asset_id()),


@app.external(authorize=beaker.Authorize.only_creator())
def freeze_asset(
    asset: pt.abi.Asset, freeze: pt.abi.Uint8, account: pt.abi.Account
) -> pt.Expr:
    return pt.InnerTxnBuilder.Execute(
        {
            pt.TxnField.type_enum: pt.TxnType.AssetFreeze,
            pt.TxnField.freeze_asset: asset.asset_id(),
            pt.TxnField.freeze_asset_account: account.address(),
            pt.TxnField.freeze_asset_frozen: freeze.get(),
        }
    )


# @app.external
# def update_asset(
#     asset: pt.abi.Asset,
#     copies: pt.abi.Uint64,
#     price: pt.abi.Uint64,
# ) -> pt.Expr:
#     account_balance = pt.AssetHolding.balance(pt.Txn.sender(), asset.asset_id())
#     return pt.Seq(
#         account_balance,
#         pt.Assert(
#             account_balance.hasValue(),
#             comment="Sender does not have the asset balance.",
#         ),
#         pt.Assert(
#             copies <= account_balance.value(),
#             comment="Sender does not have enough copies to list",
#         ),
#         (asset_id := pt.abi.Uint64()).set(asset.asset_id()),
#         pt.If(
#             app.state.asset_records[asset_id].exists(),
#             pt.Seq(
#                 (ar := AssetRecord()).decode(app.state.asset_records[asset_id].get()),
#                 (nmaxp := pt.abi.Uint64()).set(ar.maxcopies),
#                 ar.set(nmaxp, price),
#                 app.state.asset_records[asset_id].set(ar),
#             ),
#             pt.Seq(
#                 (maxcopies := pt.abi.Uint64()).set(pt.Int(0)),
#                 (asset_id := pt.abi.Uint64()).set(asset.asset_id()),
#                 (ar := AssetRecord()).set(maxcopies, price),
#                 app.state.asset_records[asset_id].set(ar),
#             ),
#         ),
#     )


# @app.external
# def buyNft(
#     asset: pt.abi.Asset,
#     payment: pt.abi.PaymentTransaction,
# ) -> pt.Expr:
#     ar = AssetRecord()
#     price = pt.abi.Uint64()
#     asset_balance = pt.AssetHolding.balance(pt.Txn.accounts[1], asset.asset_id())
#     algo_balance = pt.AccountParamObject(pt.Txn.sender()).balance()
#     return pt.Seq(
#         pt.Assert(
#             pt.Txn.sender() == payment.get().sender(),
#             comment="Txn sender and Buyer are not same.",
#         ),
#         pt.Assert(
#             pt.Txn.accounts[1] == payment.get().receiver(),
#             comment="Txn sender and Buyer are not same.",
#         ),
#         (asset_id := pt.abi.Uint64()).set(asset.asset_id()),
#         pt.Assert(
#             app.state.asset_records[asset_id].exists(),
#             comment="Asset is not listed.",
#         ),
#         (app.state.asset_records[asset_id].store_into(ar)),
#         ar.price.store_into(price),
#         asset_balance,
#         pt.Assert(
#             asset_balance.hasValue(),
#             comment="Sender does not have the asset balance.",
#         ),
#         algo_balance,
#         pt.Assert(
#             algo_balance.value() >= price.get(),
#             comment="Buyer does not have enough Algos.",
#         ),
#         pt.Assert(
#             payment.get().amount() == price.get(),
#             comment="Payment amount is not enough.",
#         ),
#         pt.InnerTxnBuilder.Execute(
#             {
#                 pt.TxnField.type_enum: pt.TxnType.AssetTransfer,
#                 pt.TxnField.asset_receiver: pt.Txn.sender(),
#                 pt.TxnField.asset_sender: payment.get().receiver(),
#                 pt.TxnField.asset_amount: pt.Int(1),
#                 pt.TxnField.xfer_asset: asset.asset_id(),
#             }
#         ),
#         pt.Pop(app.state.asset_records[asset_id].delete()),
#     )


# @app.external(authorize=beaker.Authorize.only_creator())
# def drop_asset(asset: pt.abi.Asset) -> pt.Expr:
#     ar = AssetRecord()
#     asset_balance = pt.AssetHolding.balance(pt.Txn.accounts[1], asset.asset_id())
#     return pt.Seq(
#         (asset_id := pt.abi.Uint64()).set(asset.asset_id()),
#         pt.Assert(
#             app.state.asset_records[asset_id].exists(),
#             comment="Asset is not listed.",
#         ),
#         (app.state.asset_records[asset_id].store_into(ar)),
#         asset_balance,
#         pt.Assert(
#             asset_balance.hasValue(),
#             comment="Sender does not have the asset balance.",
#         ),
#         pt.InnerTxnBuilder.Execute(
#             {
#                 pt.TxnField.type_enum: pt.TxnType.AssetTransfer,
#                 pt.TxnField.asset_receiver: pt.Txn.accounts[2],
#                 pt.TxnField.asset_sender: pt.Txn.accounts[1],
#                 pt.TxnField.asset_amount: pt.Int(1),
#                 pt.TxnField.xfer_asset: asset.asset_id(),
#             }
#         ),
#         pt.Pop(app.state.asset_records[asset_id].delete()),
#     )


# @app.external
# def delistNft(asset: pt.abi.Asset) -> pt.Expr:
#     account_balance = pt.AssetHolding.balance(pt.Txn.sender(), asset.asset_id())
#     return pt.Seq(
#         account_balance,
#         pt.Assert(
#             account_balance.hasValue(),
#             comment="Sender does not have the asset balance.",
#         ),
#         (asset_id := pt.abi.Uint64()).set(asset.asset_id()),
#         pt.Pop(app.state.asset_records[asset_id].delete()),
#     )


@app.external
def optin_asset(asset: pt.abi.Asset) -> pt.Expr:
    return pt.Seq(
        pt.InnerTxnBuilder.Execute(
            {
                pt.TxnField.type_enum: pt.TxnType.AssetTransfer,
                pt.TxnField.asset_receiver: pt.Global.current_application_address(),
                pt.TxnField.xfer_asset: asset.asset_id(),
                pt.TxnField.asset_amount: pt.Int(0),
            }
        ),
    )


if __name__ == "__main__":
    app.build().export("./artifacts")
