from beaker import State, event, global_, read_state, types, write_state

# Define the state variables for the contract
nft_storage = State("nft_storage", types.bytes)
nft_creator = State("nft_creator", types.address)
nft_id = State("nft_id", types.uint64)
nft_balances = State("nft_balances", types.bytes)


# Define the event for NFT minting
@event
def MintNFT(address: types.Address, id: types.uint64, amount: types.uint64):
    pass


# Mint NFT function to create and distribute the NFTs
def mint_nft(receiver: types.Address, metadata: types.bytes, quantity: types.uint64):
    # Ensure that only the creator can mint NFTs
    if not global_.get_creator() == read_state(nft_creator):
        return

    # Generate the NFT ID
    id = read_state(nft_id) + 1
    write_state(nft_id, id)

    # Set the initial NFT balance to the specified quantity
    nft_balance = types.pack([(receiver, quantity)])
    write_state(nft_balances[nft_id], nft_balance)

    # Store the NFT metadata in the contract state
    write_state(nft_storage[nft_id], metadata)

    # Emit the MintNFT event
    MintNFT(receiver, id, quantity)


# Get the balance of an NFT for a specific account
def balance_of(account: types.Address, id: types.uint64) -> types.uint64:
    nft_balance = read_state(nft_balances[id])
    for addr, amount in types.unpack(nft_balance):
        if addr == account:
            return amount
    return 0


# Transfer an NFT from the sender to the recipient
def transfer(
    from_addr: types.Address,
    to_addr: types.Address,
    id: types.uint64,
    amount: types.uint64,
):
    if not from_addr == global_.txn.sender():
        return

    from_balance = balance_of(from_addr, id)
    if from_balance < amount:
        return

    nft_balance = read_state(nft_balances[id])
    to_balance = 0
    new_nft_balance = []
    for addr, bal in types.unpack(nft_balance):
        if addr == to_addr:
            to_balance = bal
        elif addr == from_addr:
            from_balance -= amount
        new_nft_balance.append((addr, bal))

    to_balance += amount
    new_nft_balance.append((to_addr, to_balance))
    write_state(nft_balances[id], types.pack(new_nft_balance))


# Get the metadata for a specific NFT
def token_uri(id: types.uint64) -> types.bytes:
    return read_state(nft_storage[id])
