from pyteal import *


def contract():
    # Store the balances of the token holders
    balances = App.local().get(Int(0), Bytes("balances"))

    # Events emitted by the contract
    event_transfer_single = Event(
        "TransferSingle",
        {
            "operator": Bytes("address"),
            "from": Bytes("address"),
            "to": Bytes("address"),
            "id": Int,
            "value": Int,
        },
    )

    Event(
        "TransferBatch",
        {
            "operator": Bytes("address"),
            "from": Bytes("address"),
            "to": Bytes("address"),
            "ids": Array(Int),
            "values": Array(Int),
        },
    )

    Event(
        "ApprovalForAll",
        {"owner": Bytes("address"), "operator": Bytes("address"), "approved": Bool},
    )

    Event(
        "ApprovalForAllBatch",
        {"owner": Bytes("address"), "operators": Array(Bytes), "approved": Bool},
    )

    # Mint new NFTs
    def mint(to: Bytes, id: Int, amount: Int):
        # Ensure the sender is the contract creator
        on_create = App.globalPut(Bytes("creator"), Txn.sender())
        creator = App.globalGet(Bytes("creator"))
        is_creator = Txn.sender() == creator
        # Ensure the token has not been minted before
        token_exists = balances.get(id, Int(0)) == Int(0)
        # Mint the token
        update_balance = balances.put(id, amount + balances.get(id, Int(0)))
        on_mint = And(on_create, is_creator, token_exists, update_balance)
        # Emit a TransferSingle event
        on_transfer_single = event_transfer_single.emit(
            Txn.sender(),
            App.localGet(Int(0), Bytes("balances")).get(id, Int(0)),
            amount,
            id,
            to,
        )
        return And(on_mint, on_transfer_single)

    # Burn existing NFTs
    def burn(from_: Bytes, id: Int, amount: Int):
        # Ensure the sender is the owner of the token
        on_transfer = App.localGet(Int(0), Bytes("balances")).get(id, Int(0)) >= amount
        # Burn the token
        update_balance = App.localGet(Int(0), Bytes("balances")).put(
            id, App.localGet(Int(0), Bytes("balances")).get(id, Int(0)) - amount
        )
        on_burn = And(on_transfer, update_balance)
        # Emit a TransferSingle event
        on_transfer_single = event_transfer_single.emit(
            from_,
            App.localGet(Int(0), Bytes("balances")).get(id, Int(0)),
            amount,
            id,
            Txn.sender(),
        )
        return And(on_burn, on_transfer_single)

    # Transfer NFTs from one account to another
    def safe_transfer_from(from_: Bytes, to: Bytes, id: Int, amount: Int):
        # Ensure the sender is either the owner of the token or an approved operator
        operator_approved = App.localGet(Int(0), Bytes("operators")).get(
            from_ + to, False
        )
        Txn.sender() == from_
        operator_approved & (Txn.sender() != from_)
        # Ensure the token exists and is not being
