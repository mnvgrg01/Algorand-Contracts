# from app import app
from beaker import client, sandbox

from Extras.app import app

# from structure import app
# from boxApp import app

app.build().export("./artifacts")

accounts = sandbox.kmd.get_accounts()
sender = accounts[0]
receiver = accounts[1]
sender1 = accounts[2]


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

return_value = app_client.call("logger", a="maanav", b="garg").return_value

print(return_value)
