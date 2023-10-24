# from app import app
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from algosdk.transaction import AssetCreateTxn, AssetOptInTxn, PaymentTxn
from beaker import client, consts, sandbox

from app21 import app

# from structure import app
# from boxApp import app

app.build().export("./artifacts")

accounts = sandbox.kmd.get_accounts()
sender = accounts.pop()
receiver = accounts.pop()

print("Sender Account:", sender.address)
print("receiver ", receiver.address)

indexer_client = sandbox.get_indexer_client()


app_client = client.ApplicationClient(
    client=sandbox.get_algod_client(),
    app=app,
    sender=sender.address,
    signer=sender.signer,
)


sp = app_client.get_suggested_params()


app_id, app_addr, txid = app_client.create()
print(f"Created app with id {app_id} and address {app_addr} in transaction {txid}")

receiver_client = client.ApplicationClient(
    client=sandbox.get_algod_client(),
    app_id=app_id,
    app=app,
    sender=receiver.address,
    signer=receiver.signer,
)

app_client.fund(1 * consts.algo)

# asset_index = app_client.call("mint", name="carsi", url="http://s.com").return_value
tx_id = app_client.client.send_transaction(
    AssetCreateTxn(
        sender=sender.address,
        sp=sp,
        total=1,
        decimals=0,
        default_frozen=True,
        manager=app_addr,
        reserve=app_addr,
        freeze=app_addr,
        clawback=app_addr,
        unit_name="tst",
        asset_name="test1",
        url="ssdf",
    ).sign(sender.private_key)
)

asset_index = sandbox.get_algod_client().pending_transaction_info(tx_id)["asset-index"]

print("asset_index: ", asset_index)


app_client.call(
    "add_asset",
    asset=asset_index,
    maxp=12,
    listed=1,
    price=200,
    boxes=[(0, asset_index)],
)


# boxes = app_client.get_box_names()
# print(app_client.app_id)

# print(boxes)

return_value = app_client.call(
    "get_asset", asset=asset_index, boxes=[(0, asset_index)]
).return_value

print("Before transfer box storage: ", return_value)
# return_value1 = app_client.call("optin", asset=asset_index).return_value
# app_client.call(
#     "update_state", asset=asset_index, listed=0, price=345, boxes=[(0, asset_index)]
# )


print("#" * 20, "before transfer", "#" * 20)


sender_amount1 = indexer_client.account_info(sender.address)["account"]["amount"]
receiver_amount1 = indexer_client.account_info(receiver.address)["account"]["amount"]


print(
    "receiver algo balance : ",
    indexer_client.account_info(receiver.address)["account"]["amount"],
)

print(
    "sender algo balance : ",
    indexer_client.account_info(sender.address)["account"]["amount"],
)
print(
    "sender asset balance : ",
    indexer_client.account_info(sender.address)["account"]["assets"],
)

############### Receiver txn ####################

atc = AtomicTransactionComposer()

## Receiver must optin

optin = TransactionWithSigner(
    AssetOptInTxn(sender=receiver.address, sp=sp, index=asset_index),
    signer=receiver.signer,
)


atc.add_transaction(optin)

pay_txn = TransactionWithSigner(
    txn=PaymentTxn(sender=receiver.address, receiver=sender.address, amt=200, sp=sp),
    signer=receiver.signer,
)

# atc.add_transaction(pay_txn)

app_client.add_method_call(
    atc=atc,
    method="buy",
    asset=asset_index,
    payment=pay_txn,
    accounts=[sender.address],
    suggested_params=sp,
    sender=receiver.address,
    signer=receiver.signer,
    boxes=[(0, asset_index)],
),

# return_value1 = app_client.call(
#     "buy", asset=asset_index, payment=payment, boxes=[(0, asset_index)]
# ).return_value

tx_id1 = atc.execute(sandbox.get_algod_client(), 3)
print(tx_id1)


#######################################################################################

# print("Before Update: ", return_value)

print("#" * 20, "After transfer", "#" * 20)

print(
    "receiver algo balance : ",
    indexer_client.account_info(receiver.address)["account"]["amount"],
)

print(
    "sender algo balance : ",
    indexer_client.account_info(sender.address)["account"]["amount"],
)
print(
    "sender asset balance : ",
    indexer_client.account_info(sender.address)["account"]["assets"],
)
print(
    "receiver asset balance : ",
    indexer_client.account_info(receiver.address)["account"]["assets"],
)


sender_amount2 = indexer_client.account_info(sender.address)["account"]["amount"]
receiver_amount2 = indexer_client.account_info(receiver.address)["account"]["amount"]

boxreturn = app_client.call(
    "get_asset", asset=asset_index, boxes=[(0, asset_index)]
).return_value

print("After transfer box storage: ", boxreturn)

print("app spend amount", receiver_amount1 - receiver_amount2)
print(" sender spend amount", sender_amount1 - sender_amount2)
