from typing import Final

import beaker
import pyteal as pt
from beaker.lib.storage import BoxMapping

# class NftOwner(pt.abi.NamedTuple):
#     owner: pt.abi.Field[pt.abi.String]
#     nftid: pt.abi.Field[pt.abi.Uint16]


# class StructerState:
#     nftowner = beaker.ReservedGlobalStateValue(
#         stack_type=pt.TealType.bytes,
#         max_keys=64,
#         prefix="",
#     )


class AsaState:
    asa: Final[beaker.GlobalStateValue] = beaker.GlobalStateValue(
        stack_type=pt.TealType.uint64,
        default=pt.Int(0),
        descr="ID of the ASA",
    )

    owner = BoxMapping(pt.abi.String, pt.abi.Uint64)

    reserved_global_value = beaker.ReservedGlobalStateValue(
        stack_type=pt.TealType.bytes,
        max_keys=32,
        descr="A reserved app state variable, with 64 possible keys",
    )


app = (
    beaker.Application("asset", state=AsaState())
    # allow opt-in and initialise local/account state
    .apply(beaker.unconditional_opt_in_approval)
)


@app.create(bare=True)
def create() -> pt.Expr:
    return pt.Seq(app.initialize_global_state(), app.initialize_local_state())


############## For Box #################

# @app.external
# def store_nft_data(value: pt.abi.Uint64) -> pt.Expr:
#     return app.state.owner[pt.Txn.sender()].set(value)


# @app.external
# def get_nft_data(key: pt.abi.Address) -> pt.Expr:
#     return app.state.owner[key].get()

############ For Global State Value ############


@app.external
def store_nft(value: pt.abi.Uint64) -> pt.Expr:
    return app.state.asa.set(value.get())


@app.external(read_only=True)
def get_global_state_val(*, output: pt.abi.Uint64) -> pt.Expr:
    return output.set(app.state.asa)


######################### For Reserved Global Value #########################


@app.external
def set_reserved_global_state_val(k: pt.abi.Uint64, v: pt.abi.String) -> pt.Expr:
    # Accessing the key with square brackets, accepts both Expr and an ABI type
    # If the value is an Expr it must evaluate to `TealType.bytes`
    # If the value is an ABI type, the `encode` method is used to convert it to bytes
    return app.state.reserved_global_value[k].set(v.get())


@app.external(read_only=True)
def get_reserved_global_state_val(
    k: pt.abi.Uint64, *, output: pt.abi.String
) -> pt.Expr:
    return output.set(app.state.reserved_global_value[k])


####### Get ASA details ######

# @app.external
# def getAsa(name: pt.abi.String, url: pt.abi.String, *, output: pt.abi.Uint64) -> pt.Expr:
#     return pt.Seq(
#         pt.InnerTxnBuilder.Execute(
#           pt.TxnField.type_enum : pt.Txn.


########### Mint ###########


@app.external
def mint(name: pt.abi.String, url: pt.abi.String, *, output: pt.abi.Uint64) -> pt.Expr:
    return pt.Seq(
        pt.InnerTxnBuilder.Execute(
            {
                pt.TxnField.type_enum: pt.TxnType.AssetConfig,
                pt.TxnField.config_asset_total: pt.Int(1),
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
        app.state.asa.set(pt.InnerTxn.created_asset_id()),
    )

    #   app.state.nftOwner.set(pt.InnerTxn.created_asset_id()),


@app.external
def freeze(
    asset: pt.abi.Asset, freeze: pt.abi.Uint8, account: pt.abi.Address
) -> pt.Expr:
    return pt.InnerTxnBuilder.Execute(
        {
            pt.TxnField.type_enum: pt.TxnType.AssetFreeze,
            pt.TxnField.freeze_asset: asset.asset_id(),
            pt.TxnField.freeze_asset_account: account.get(),
            pt.TxnField.freeze_asset_frozen: freeze.get(),
        }
    )


@app.external
def buy(asset: pt.abi.Asset) -> pt.Expr:
    return pt.Seq(
        pt.InnerTxnBuilder.Execute(
            {
                pt.TxnField.type_enum: pt.TxnType.AssetTransfer,
                pt.TxnField.asset_amount: pt.Int(1),
                pt.TxnField.asset_receiver: pt.Txn.sender(),
                pt.TxnField.xfer_asset: asset.asset_id(),
            }
        ),
        pt.InnerTxnBuilder.Execute(
            {
                pt.TxnField.type_enum: pt.TxnType.AssetFreeze,
                pt.TxnField.freeze_asset: asset.asset_id(),
                pt.TxnField.freeze_asset_account: pt.Txn.sender(),
                pt.TxnField.freeze_asset_frozen: pt.Int(1),
            }
        ),
    )


@app.external
def optin(asset: pt.abi.Asset) -> pt.Expr:
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
