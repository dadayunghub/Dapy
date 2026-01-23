from web3 import Web3
import os

RPC_URL = os.getenv("ARC_TESTNET_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

CONTRACT_ADDRESS = Web3.to_checksum_address(
    "0xb44155e5b8b3213bb9965d63db34c55e7ef555c1"  # your ERC20
)

RECIPIENT = Web3.to_checksum_address(
    "0x825A64Bb9Cc8CBa0ec30254574C72Fed6D92F8e0"
)

AMOUNT = 10 * 10**18  # 10 tokens (18 decimals)

ERC20_TRANSFER_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]

w3 = Web3(Web3.HTTPProvider(RPC_URL))
assert w3.is_connected(), "RPC connection failed"

account = w3.eth.account.from_key(PRIVATE_KEY)

contract = w3.eth.contract(
    address=CONTRACT_ADDRESS,
    abi=ERC20_TRANSFER_ABI
)

tx = contract.functions.transfer(
    RECIPIENT,
    AMOUNT
).build_transaction({
    "from": account.address,
    "nonce": w3.eth.get_transaction_count(account.address),
    "gas": 200_000,
    "gasPrice": w3.eth.gas_price,
    "chainId": w3.eth.chain_id,
})

signed_tx = account.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

print("Transfer tx hash:", tx_hash.hex())
