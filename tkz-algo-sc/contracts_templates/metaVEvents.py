import beaker
import pyteal as pt
from beaker.consts import BOX_BYTE_MIN_BALANCE, BOX_FLAT_MIN_BALANCE
from beaker.lib.storage import BoxMapping


class AssetRecord(pt.abi.NamedTuple):
    maxp: pt.abi.Field[pt.abi.Uint64]
    price: pt.abi.Field[pt.abi.Uint64]  # In microAlgos


class AssetState:
    def __init__(self, *, record_type: type[pt.abi.BaseType]):
        self.record_type = record_type

        self.asset_records = BoxMapping(pt.abi.Uint64, record_type)

        # Math for determining min balance based on expected size of boxes
        self.minimum_balance = pt.Int(
            BOX_FLAT_MIN_BALANCE + (pt.abi.size_of(record_type) * BOX_BYTE_MIN_BALANCE)
        )


app = beaker.Application(
    "asset",
    state=AssetState(record_type=AssetRecord),
    build_options=beaker.BuildOptions(scratch_slots=False),
)


@app.create(bare=True)
def create() -> pt.Expr:
    return pt.Seq(app.initialize_global_state(), app.initialize_local_state())


##################### Box ops ##############################


@app.external
def addAssetToListing(
    asset: pt.abi.Asset,
    maxp: pt.abi.Uint64,
    price: pt.abi.Uint64,
) -> pt.Expr:
    return pt.Seq(
        (asset_id := pt.abi.Uint64()).set(asset.asset_id()),
        (ar := AssetRecord()).set(maxp, price),
        app.state.asset_records[asset_id].set(ar),
    )


@app.external
def getAsset(asset: pt.abi.Asset, *, output: AssetRecord) -> pt.Expr:
    return pt.Seq(
        (asset_id := pt.abi.Uint64()).set(asset.asset_id()),
        app.state.asset_records[asset_id].store_into(output),
    )


#####################################################################


####### Get ASA details ######

# @app.external
# def getAsa(name: pt.abi.String, url: pt.abi.String, *, output: pt.abi.Uint64) -> pt.Expr:
#     return pt.Seq(
#         pt.InnerTxnBuilder.Execute(
#           pt.TxnField.type_enum : pt.TxnType.a


########### Mint ###########


@app.external
def mintNft(
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
def freezeNft(
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


@app.external
def updateNft(
    asset: pt.abi.Asset,
    price: pt.abi.Uint64,
) -> pt.Expr:
    account_balance = pt.AssetHolding.balance(pt.Txn.sender(), asset.asset_id())
    return pt.Seq(
        account_balance,
        pt.Assert(
            account_balance.hasValue(),
            comment="Sender does not have the asset balance.",
        ),
        (asset_id := pt.abi.Uint64()).set(asset.asset_id()),
        pt.If(
            app.state.asset_records[asset_id].exists(),
            pt.Seq(
                (ar := AssetRecord()).decode(app.state.asset_records[asset_id].get()),
                (nmaxp := pt.abi.Uint64()).set(ar.maxp),
                ar.set(nmaxp, price),
                app.state.asset_records[asset_id].set(ar),
            ),
            pt.Seq(
                (maxp := pt.abi.Uint64()).set(pt.Int(0)),
                (asset_id := pt.abi.Uint64()).set(asset.asset_id()),
                (ar := AssetRecord()).set(maxp, price),
                app.state.asset_records[asset_id].set(ar),
            ),
        ),
    )


@app.external
def buyNft(
    asset: pt.abi.Asset,
    payment: pt.abi.PaymentTransaction,
) -> pt.Expr:
    ar = AssetRecord()
    price = pt.abi.Uint64()
    asset_balance = pt.AssetHolding.balance(pt.Txn.accounts[1], asset.asset_id())
    algo_balance = pt.AccountParamObject(pt.Txn.sender()).balance()
    return pt.Seq(
        pt.Assert(
            pt.Txn.sender() == payment.get().sender(),
            comment="Txn sender and Buyer are not same.",
        ),
        pt.Assert(
            pt.Txn.accounts[1] == payment.get().receiver(),
            comment="Txn sender and Buyer are not same.",
        ),
        (asset_id := pt.abi.Uint64()).set(asset.asset_id()),
        pt.Assert(
            app.state.asset_records[asset_id].exists(),
            comment="Asset is not listed.",
        ),
        (app.state.asset_records[asset_id].store_into(ar)),
        ar.price.store_into(price),
        asset_balance,
        pt.Assert(
            asset_balance.hasValue(),
            comment="Sender does not have the asset balance.",
        ),
        algo_balance,
        pt.Assert(
            algo_balance.value() >= price.get(),
            comment="Buyer does not have enough Algos.",
        ),
        pt.Assert(
            payment.get().amount() == price.get(),
            comment="Payment amount is not enough.",
        ),
        pt.InnerTxnBuilder.Execute(
            {
                pt.TxnField.type_enum: pt.TxnType.AssetTransfer,
                pt.TxnField.asset_receiver: pt.Txn.sender(),
                pt.TxnField.asset_sender: payment.get().receiver(),
                pt.TxnField.asset_amount: pt.Int(1),
                pt.TxnField.xfer_asset: asset.asset_id(),
            }
        ),
        pt.Pop(app.state.asset_records[asset_id].delete()),
    )


@app.external(authorize=beaker.Authorize.only_creator())
def dropNft(asset: pt.abi.Asset) -> pt.Expr:
    ar = AssetRecord()
    asset_balance = pt.AssetHolding.balance(pt.Txn.accounts[1], asset.asset_id())
    return pt.Seq(
        (asset_id := pt.abi.Uint64()).set(asset.asset_id()),
        pt.Assert(
            app.state.asset_records[asset_id].exists(),
            comment="Asset is not listed.",
        ),
        (app.state.asset_records[asset_id].store_into(ar)),
        asset_balance,
        pt.Assert(
            asset_balance.hasValue(),
            comment="Sender does not have the asset balance.",
        ),
        pt.InnerTxnBuilder.Execute(
            {
                pt.TxnField.type_enum: pt.TxnType.AssetTransfer,
                pt.TxnField.asset_receiver: pt.Txn.accounts[2],
                pt.TxnField.asset_sender: pt.Txn.accounts[1],
                pt.TxnField.asset_amount: pt.Int(1),
                pt.TxnField.xfer_asset: asset.asset_id(),
            }
        ),
        pt.Pop(app.state.asset_records[asset_id].delete()),
    )


@app.external
def delistNft(asset: pt.abi.Asset) -> pt.Expr:
    account_balance = pt.AssetHolding.balance(pt.Txn.sender(), asset.asset_id())
    return pt.Seq(
        account_balance,
        pt.Assert(
            account_balance.hasValue(),
            comment="Sender does not have the asset balance.",
        ),
        (asset_id := pt.abi.Uint64()).set(asset.asset_id()),
        pt.Pop(app.state.asset_records[asset_id].delete()),
    )


@app.external(authorize=beaker.Authorize.only_creator())
def optinNft(asset: pt.abi.Asset) -> pt.Expr:
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
