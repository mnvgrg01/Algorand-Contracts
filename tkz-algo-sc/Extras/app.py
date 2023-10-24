from beaker import *
from pyteal import *

app = Application("HelloWorld")


@app.external
def hello(name: abi.String, *, output: abi.String) -> Expr:
    return output.set(Concat(Bytes("Hello, "), name.get()))


@app.delete(bare=True, authorize=Authorize.only(Global.creator_address()))
def delete() -> Expr:
    return Approve()


@app.external
def logger(a: abi.String, b: abi.String, *, output: abi.Uint64) -> Expr:
    return Seq(
        Log(a.get()),
        Log(b.get()),
        # Log(Global.latest_timestamp()),
        Log(Txn.sender()),
        output.set(Global.latest_timestamp()),
        # output.set(Txn.sender()),
    )


if __name__ == "__main__":
    app.build().export("./artifacts")
