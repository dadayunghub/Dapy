from web3 import Web3
from abi import HELLO_ARCHITECT_ABI
import os

RPC_URL = os.getenv("ARC_TESTNET_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

CONTRACT_ADDRESS = Web3.to_checksum_address(
    "0xfd3da227520b77363Fc298b6786dFC91A7E81f48"
)

w3 = Web3(Web3.HTTPProvider(RPC_URL))
assert w3.is_connected(), "RPC connection failed"

account = w3.eth.account.from_key(PRIVATE_KEY)

contract = w3.eth.contract(
    address=CONTRACT_ADDRESS,
    abi=HELLO_ARCHITECT_ABI
)

# 🔹 READ (no gas)
current = contract.functions.getGreeting().call()
print("Current greeting:", current)

# 🔹 WRITE (transaction)
tx = contract.functions.setGreeting(
    "Hello from GitHub Actions + Python 🚀"
).build_transaction({
    "from": account.address,
    "nonce": w3.eth.get_transaction_count(account.address),
    "gas": 200_000,
    "gasPrice": w3.eth.gas_price,
    "chainId": w3.eth.chain_id,
})

signed = account.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)

print("Tx hash:", tx_hash.hex())
