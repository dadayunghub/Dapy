from circle.web3 import utils, developer_controlled_wallets, smart_contract_platform
import os

client = utils.init_developer_controlled_wallets_client(
    api_key=os.getenv("CIRCLE_API_KEY"),
    entity_secret=os.getenv("CIRCLE_ENTITY_SECRET")
)

scpClient = utils.init_smart_contract_platform_client(
    api_key=os.getenv("CIRCLE_API_KEY"),
    entity_secret=os.getenv("CIRCLE_ENTITY_SECRET")
)

api_instance = smart_contract_platform.TemplatesApi(scpClient)

request = smart_contract_platform.TemplateContractDeploymentRequest.from_dict({
    "blockchain": "ARC-TESTNET",
    "name": "MyAirdropContract",
    "walletId": os.getenv("WALLET_ID"),
    "templateParameters": {
        "defaultAdmin": os.getenv("WALLET_ADDRESS"),
    },
    "feeLevel": "MEDIUM"
})

response = api_instance.deploy_contract_template("13e322f2-18dc-4f57-8eed-4bddfc50f85e", request)