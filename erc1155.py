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
    "name": "MyMultiTokenContract",
    "walletId": os.getenv("WALLET_ID"),
    "templateParameters": {
        "name": "MyMultiToken",
        "symbol": "MMTK",
        "defaultAdmin": os.getenv("WALLET_ADDRESS"),
        "primarySaleRecipient": os.getenv("WALLET_ADDRESS"),
        "royaltyRecipient": os.getenv("WALLET_ADDRESS"),
        "royaltyPercent": "0.01",
    },
    "feeLevel": "MEDIUM"
})

request.template_parameters["royaltyPercent"] = 0.01

response = api_instance.deploy_contract_template("aea21da6-0aa2-4971-9a1a-5098842b1248", request)