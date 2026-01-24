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
    "name": "MyTokenContract",
    "walletId": os.getenv("WALLET_ID"),
    "templateParameters": {
        "name": "MyToken",
        "symbol": "MTK",
        "defaultAdmin": os.getenv("WALLET_ADDRESS"),
        "primarySaleRecipient": os.getenv("WALLET_ADDRESS"),
    },
    "feeLevel": "MEDIUM"
})

response = api_instance.deploy_contract_template("76b83278-50e2-4006-8b63-5b1a2a814533", request)