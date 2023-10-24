# from app import app
from algosdk import encoding
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from algosdk.transaction import AssetCreateTxn, AssetOptInTxn
from beaker import client, consts, sandbox

from contracts_templates.RealToken import app

# from structure import app
# from boxApp import app

AtomicTransactionComposer, TransactionWithSigner

app.build().export("./artifacts")

accounts = sandbox.kmd.get_accounts()
platform = accounts[0]
powner = accounts[1]
buyer = accounts[2]

print("Platform Account:", platform.address)
print("Project Owner Address", powner.address)
print("buyer ", buyer.address)

indexer_client = sandbox.get_indexer_client()


app_client = client.ApplicationClient(
    client=sandbox.get_algod_client(),
    app=app,
    sender=platform.address,
    signer=platform.signer,
)


sp = app_client.get_suggested_params()


app_id, app_addr, txid = app_client.create()
print(f"Created app with id {app_id} and address {app_addr} in transaction {txid}")


sender1_client = client.ApplicationClient(
    client=sandbox.get_algod_client(),
    app=app,
    app_id=app_id,
    sender=powner.address,
    signer=powner.signer,
)

receiver_client = client.ApplicationClient(
    client=sandbox.get_algod_client(),
    app_id=app_id,
    app=app,
    sender=buyer.address,
    signer=buyer.signer,
)

app_client.fund(1 * consts.algo)

# asset_index = app_client.call("mint", name="carsi", url="http://s.com").return_value
tx_id = app_client.client.send_transaction(
    AssetCreateTxn(
        sender=platform.address,
        sp=sp,
        total=30,
        decimals=0,
        default_frozen=True,
        manager=app_addr,
        reserve=app_addr,
        freeze=app_addr,
        clawback=app_addr,
        unit_name="tst",
        asset_name="test1",
        url="ssdf",
    ).sign(platform.private_key)
)

asset_index = sandbox.get_algod_client().pending_transaction_info(tx_id)["asset-index"]

print("asset_index: ", asset_index)


sender_amount1 = indexer_client.account_info(platform.address)["account"]["amount"]
receiver_amount1 = indexer_client.account_info(buyer.address)["account"]["amount"]

app_client.call(
    "add_asset_listing",
    asset=asset_index,
    copies=30,
    price=200,
    lotsize=10,
    coolingtime=333,
    primary=True,
    boxes=[(0, encoding.decode_address(platform.address)), (0, asset_index)],
)

# sender1_client.call(
#     "add_asset_listing",
#     asset=asset_index,
#     copies=31,
#     price=201,
#     lotsize=10,
#     coolingtime=333,
#     boxes=[(0, encoding.decode_address(powner.address)), (0, asset_index)],
# )

# boxes = app_client.get_box_names()
# print(app_client.app_id)

# print(boxes)

before_update = app_client.call(
    "get_asset", asset=asset_index, boxes=[(0, asset_index)]
).return_value
print("Before transfer asset: ", before_update)

before_update1 = app_client.call(
    "get_listing",
    address=platform.address,
    boxes=[(0, asset_index), (0, encoding.decode_address(platform.address))],
).return_value
print("Before transfer listing : ", before_update1)


# for box in app_client.get_box_names():
#     print(f"{box} -> {app_client.get_box_contents(box)}")


# return_value1 = app_client.call("optin", asset=asset_index).return_value
# app_client.call(
#     "update_state", asset=asset_index, listed=0, price=345, boxes=[(0, asset_index)]
# )

#################### Update Test #######################

# app_client.call(
#     "update_state",
#     asset=asset_index,
#     price=300,
#     boxes=[(0, asset_index)],
# )

# after_update = app_client.call(
#     "get_asset", asset=asset_index, boxes=[(0, asset_index)]
# ).return_value


# print("Before transfer box storage: ", after_update)
##########################################################


#################### delist Test #######################

# app_client.call("delistNft", asset=asset_index, boxes=[(0, asset_index)])

# after_delist = app_client.call(
#     "get_asset", asset=asset_index, boxes=[(0, asset_index)]
# ).return_value


# print("Before transfer box storage: ", after_delist)

##########################################################


print("#" * 20, "before transfer", "#" * 20)


print(
    "buyer algo balance : ",
    indexer_client.account_info(buyer.address)["account"]["amount"],
)

print(
    "platform algo balance : ",
    indexer_client.account_info(platform.address)["account"]["amount"],
)
print(
    "platform asset balance : ",
    indexer_client.account_info(platform.address)["account"]["assets"],
)

# print(
#     "buyer asset balance : ",
#     indexer_client.account_info(buyer.address)["account"]["assets"],
# )


################# Drop method call  ###############

# 1. Receiver OptIn
# 2. app OptIn
# 3. asset transfer to app_address(escrow)

atc = AtomicTransactionComposer()

optin = TransactionWithSigner(
    AssetOptInTxn(sender=buyer.address, sp=sp, index=asset_index),
    signer=buyer.signer,
)
atc.add_transaction(optin)

app_client.add_method_call(
    atc=atc,
    method="optin_asset",
    asset=asset_index,
    suggested_params=sp,
    sender=buyer.address,
    signer=buyer.signer,
),

current_processid = app_client.call("get_processid").return_value
print("current process id", current_processid)

app_client.add_method_call(
    atc=atc,
    method="purchase_asset",
    asset=asset_index,
    copies=10,
    accounts=[platform.address, buyer.address],
    suggested_params=sp,
    sender=buyer.address,
    signer=buyer.signer,
    boxes=[
        (0, asset_index),
        (0, encoding.decode_address(platform.address)),
        (0, current_processid + 1),
    ],
),

tx_id1 = atc.execute(sandbox.get_algod_client(), 3)

before_update = app_client.call(
    "get_process_record", processid=1, boxes=[(0, 1)]
).return_value
print("Before transfer box storage: ", before_update)

after_processid = app_client.call("get_processid").return_value
print("current process id", after_processid)


###################################################################################

################# Approval method call  ###############

# 1. asset transfer from app_address(escrow) to approval

atc = AtomicTransactionComposer()

app_client.add_method_call(
    atc=atc,
    method="approve_asset",
    processid=1,
    accounts=[buyer.address],
    foreign_assets=[asset_index],
    suggested_params=sp,
    sender=platform.address,
    signer=platform.signer,
    boxes=[(0, 1)],
),

tx_id1 = atc.execute(sandbox.get_algod_client(), 3)


###################################################################################

############### Receiver Txn ####################

## 1. Receiver optin
## 3. Buy method call


## 1. Receiver optin

# optin = TransactionWithSigner(
#     AssetOptInTxn(sender=app_addr, sp=sp, index=asset_index),
#     signer=app_addr.signer,
# )
# atc.add_transaction(optin)

## 2. payment Txn

# pay_txn = TransactionWithSigner(
#     txn=PaymentTxn(sender=buyer.address, buyer=sender.address, amt=300, sp=sp),
#     signer=buyer.signer,
# )

## 3. Buy method call

# app_client.add_method_call(
#     atc=atc,
#     method="buy",
#     asset=asset_index,
#     payment=pay_txn,
#     accounts=[sender.address],
#     suggested_params=sp,
#     sender=buyer.address,
#     signer=buyer.signer,
#     boxes=[(0, asset_index)],
# ),


# print("Before Update: ", return_value)

print("#" * 20, "After transfer", "#" * 20)

print(
    "buyer algo balance : ",
    indexer_client.account_info(buyer.address)["account"]["amount"],
)

print(
    "sender algo balance : ",
    indexer_client.account_info(platform.address)["account"]["amount"],
)
print(
    "sender asset balance : ",
    indexer_client.account_info(platform.address)["account"]["assets"],
)
# print(
#     "buyer asset balance : ",
#     indexer_client.account_info(buyer.address)["account"]["assets"],
# )


# sender_amount2 = indexer_client.account_info(sender.address)["account"]["amount"]
# receiver_amount2 = indexer_client.account_info(buyer.address)["account"]["amount"]

# boxreturn = app_client.call(
#     "get_asset", asset=asset_index, boxes=[(0, asset_index)]
# ).return_value
# print("After transfer box storage: ", boxreturn)

# print("Receiver spend amount", receiver_amount1 - receiver_amount2)
# print("Sender spend amount", sender_amount1 - sender_amount2)
