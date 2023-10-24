from beaker import PyTeal, types


def nft_mint():
    # Define the NFT metadata
    metadata = {
        "name": "My NFT",
        "description": "This is my first NFT",
        "image": "https://ipfs.io/ipfs/QmZjK6J5vZz5J6yWJ7jvYQ2z1L4g7X9Q2fJ8y8tL4wU3ZS",
    }

    # Create the NFT
    nft = types.NFTAsset(
        metadata=metadata,
        total=1,
        decimals=0,
        default_frozen=False,
    )

    # Mint the NFT
    mint_txn = nft.mint(
        manager_address="YOUR_ADDRESS_HERE",
        asset_receiver_address="YOUR_ADDRESS_HERE",
    )

    return PyTeal.compileTeal(mint_txn.get_program())


if __name__ == "__main__":
    app.build().export("./artifacts")
