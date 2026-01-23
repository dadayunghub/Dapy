from web3 import Web3
import os

# ---------------------------
# Environment variables
# ---------------------------
RPC_URL = os.getenv("ARC_TESTNET_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

CONTRACT_ADDRESS = Web3.to_checksum_address(
    "0xb44155e5b8b3213bb9965d63db34c55e7ef555c1"
)
FEE_RECIPIENT = Web3.to_checksum_address(
    "0x758dca35b6d8158f8d1fa65c59a7c8f570dc7014"  # Example fee recipient
)
RECIPIENT = Web3.to_checksum_address(
    "0x825A64Bb9Cc8CBa0ec30254574C72Fed6D92F8e0"  # The user you want to send tokens to
)

# ---------------------------
# Minimal ERC20 ABI for write functions
# ---------------------------
ERC20_ABI = [
    # Core functions
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
        "inputs": [
            {"name": "recipient", "type": "address"},
            {"name": "bps", "type": "uint256"}
        ],
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

# Helper to send signed tx
def send_tx(tx):
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print("Tx hash:", tx_hash.hex())
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print("Tx status:", receipt.status)
    return receipt

# ---------------------------
# 1️⃣ Setup primary sale recipient
# ---------------------------
tx = contract.functions.setPrimarySaleRecipient(account.address).build_transaction({
    "from": account.address,
    "nonce": w3.eth.get_transaction_count(account.address),
    "gas": 200_000,
    "gasPrice": w3.eth.gas_price,
    "chainId": w3.eth.chain_id,
})
send_tx(tx)

# ---------------------------
# 2️⃣ Setup platform fee (example 5%)
# ---------------------------
tx = contract.functions.setPlatformFeeInfo(FEE_RECIPIENT, 500).build_transaction({
    "from": account.address,
    "nonce": w3.eth.get_transaction_count(account.address),
    "gas": 200_000,
    "gasPrice": w3.eth.gas_price,
    "chainId": w3.eth.chain_id,
})
send_tx(tx)

# ---------------------------
# 3️⃣ Mint tokens to dev wallet if balance is low
# ---------------------------
balance = contract.functions.balanceOf(account.address).call()
print("Dev wallet balance:", balance)

MIN_BALANCE = 10 * 10**18  # 10 tokens minimum
if balance < MIN_BALANCE:
    mint_amount = 50 * 10**18  # Mint 50 tokens
    tx = contract.functions.mintTo(account.address, mint_amount).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 200_000,
        "gasPrice": w3.eth.gas_price,
        "chainId": w3.eth.chain_id,
    })
    send_tx(tx)

# ---------------------------
# 4️⃣ Transfer tokens to user
# ---------------------------
TRANSFER_AMOUNT = 10 * 10**18  # 10 tokens
tx = contract.functions.transfer(RECIPIENT, TRANSFER_AMOUNT).build_transaction({
    "from": account.address,
    "nonce": w3.eth.get_transaction_count(account.address),
    "gas": 200_000,
    "gasPrice": w3.eth.gas_price,
    "chainId": w3.eth.chain_id,
})
send_tx(tx)

# ---------------------------
# ✅ Check recipient balance
# ---------------------------
recipient_balance = contract.functions.balanceOf(RECIPIENT).call()
print("Recipient balance:", recipient_balance)
