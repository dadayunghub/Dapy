from circle.web3 import utils, developer_controlled_wallets
import os

client = utils.init_developer_controlled_wallets_client(
    api_key=os.getenv("CIRCLE_API_KEY"),
    entity_secret=os.getenv("CIRCLE_ENTITY_SECRET")
)

wallet_sets_api = developer_controlled_wallets.WalletSetsApi(client)
wallets_api = developer_controlled_wallets.WalletsApi(client)

# Create a wallet set
wallet_set = wallet_sets_api.create_wallet_set(
    developer_controlled_wallets.CreateWalletSetRequest.from_dict({
        "name": "Wallet Set 1"
    })
)

# Create a wallet on Arc Testnet
wallet = wallets_api.create_wallet(
    developer_controlled_wallets.CreateWalletRequest.from_dict({
        "blockchains": ["ARC-TESTNET"],
        "count": 1,
        "walletSetId": wallet_set.data.wallet_set.actual_instance.id,
        "accountType": "SCA"
    })
)
print(wallet)