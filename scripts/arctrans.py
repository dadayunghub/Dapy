from web3 import Web3
import os
import time

# ---------------------------
# Environment variables
# ---------------------------
RPC_URL = os.getenv("ARC_TESTNET_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

CONTRACT_ADDRESS = Web3.to_checksum_address(
    "0x758dca35b6d8158f8d1fa65c59a7c8f570dc7014"
)
FEE_RECIPIENT = Web3.to_checksum_address(
    "0x758dca35b6d8158f8d1fa65c59a7c8f570dc7014"
)
RECIPIENTS = [
    Web3.to_checksum_address("0x825A64Bb9Cc8CBa0ec30254574C72Fed6D92F8e0")
]  # Add as many as needed

# ---------------------------
# ERC20 ABI (write functions only)
# ---------------------------
ERC20_ABI = [
    {
        "constant": False,
        "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}],
        "name": "mintTo",
        "outputs": [],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [{"name": "recipient", "type": "address"}],
        "name": "setPrimarySaleRecipient",
        "outputs": [],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [{"name": "recipient", "type": "address"}, {"name": "bps", "type": "uint256"}],
        "name": "setPlatformFeeInfo",
        "outputs": [],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    }
]

# ---------------------------
# Setup web3 and contract
# ---------------------------
w3 = Web3(Web3.HTTPProvider(RPC_URL))
assert w3.is_connected(), "RPC connection failed"

account = w3.eth.account.from_key(PRIVATE_KEY)

contract = w3.eth.contract(
    address=CONTRACT_ADDRESS,
    abi=ERC20_ABI
)

# ---------------------------
# Helper function to send signed tx
# ---------------------------
def send_tx(tx):
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print("Sent tx:", tx_hash.hex())
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print("Tx status:", "Success" if receipt.status == 1 else "Failed")
    time.sleep(1)  # small delay for nonce safety
    return receipt

# ---------------------------
# Use pending nonce to avoid underpriced replacement error
# ---------------------------
nonce = w3.eth.get_transaction_count(account.address, "pending")

# ---------------------------
# 1️⃣ Setup primary sale recipient
# ---------------------------
tx = contract.functions.setPrimarySaleRecipient(account.address).build_transaction({
    "from": account.address,
    "nonce": nonce,
    "gas": 200_000,
    "gasPrice": w3.eth.gas_price,
    "chainId": w3.eth.chain_id,
})
send_tx(tx)
nonce += 1

# ---------------------------
# 2️⃣ Setup platform fee (example 5%)
# ---------------------------
tx = contract.functions.setPlatformFeeInfo(FEE_RECIPIENT, 500).build_transaction({
    "from": account.address,
    "nonce": nonce,
    "gas": 200_000,
    "gasPrice": w3.eth.gas_price,
    "chainId": w3.eth.chain_id,
})
send_tx(tx)
nonce += 1

# ---------------------------
# 3️⃣ Mint tokens to dev wallet if balance < 10 tokens
# ---------------------------
balance = contract.functions.balanceOf(account.address).call()
print("Dev wallet balance:", balance)

MIN_BALANCE = 10 * 10**18  # 10 tokens
if balance < MIN_BALANCE:
    mint_amount = 50 * 10**18
    tx = contract.functions.mintTo(account.address, mint_amount).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 200_000,
        "gasPrice": w3.eth.gas_price,
        "chainId": w3.eth.chain_id,
    })
    send_tx(tx)
    nonce += 1

# ---------------------------
# 4️⃣ Transfer tokens to multiple users
# ---------------------------
TRANSFER_AMOUNT = 10 * 10**18  # 10 tokens each
for recipient in RECIPIENTS:
    tx = contract.functions.transfer(recipient, TRANSFER_AMOUNT).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 200_000,
        "gasPrice": w3.eth.gas_price,
        "chainId": w3.eth.chain_id,
    })
    send_tx(tx)
    nonce += 1

# ---------------------------
# 5️⃣ Check recipient balances
# ---------------------------
for recipient in RECIPIENTS:
    bal = contract.functions.balanceOf(recipient).call()
    print(f"Recipient {recipient} balance:", bal)
