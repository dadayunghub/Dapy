# interact.py
import argparse
from web3 import Web3
import os
import json

# ----------------- Setup -----------------
RPC_URL = os.getenv("ARC_TESTNET_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = Web3.to_checksum_address(
    os.getenv("ARC_ERC20_ADDRESS")  # set in your env
)

# Load ABI
with open("ArcERC20_ABI.json") as f:
    ABI = json.load(f)

w3 = Web3(Web3.HTTPProvider(RPC_URL))
assert w3.is_connected(), "RPC connection failed"

account = w3.eth.account.from_key(PRIVATE_KEY)
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

def send_tx(tx):
    tx["nonce"] = w3.eth.get_transaction_count(account.address)
    tx["chainId"] = w3.eth.chain_id
    tx["gasPrice"] = w3.eth.gas_price
    tx["from"] = account.address

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Tx sent! Hash: {tx_hash.hex()}")

# ----------------- Functions -----------------

def transfer():
    to = Web3.to_checksum_address(input("Recipient address: ").strip())
    amount = int(float(input("Amount (tokens): ")) * 10**18)
    tx = contract.functions.transfer(to, amount).build_transaction({"gas": 200_000})
    send_tx(tx)

def mint():
    to = Web3.to_checksum_address(input("Recipient address: ").strip())
    amount = int(float(input("Amount (tokens): ")) * 10**18)
    tx = contract.functions.mintTo(to, amount).build_transaction({"gas": 300_000})
    send_tx(tx)

def burn():
    amount = int(float(input("Amount (tokens): ")) * 10**18)
    tx = contract.functions.burn(amount).build_transaction({"gas": 200_000})
    send_tx(tx)

def burn_from():
    from_addr = Web3.to_checksum_address(input("From address: ").strip())
    amount = int(float(input("Amount (tokens): ")) * 10**18)
    tx = contract.functions.burnFrom(from_addr, amount).build_transaction({"gas": 250_000})
    send_tx(tx)

def approve():
    spender = Web3.to_checksum_address(input("Spender address: ").strip())
    amount = int(float(input("Amount (tokens): ")) * 10**18)
    tx = contract.functions.approve(spender, amount).build_transaction({"gas": 200_000})
    send_tx(tx)

def transfer_from():
    from_addr = Web3.to_checksum_address(input("From address: ").strip())
    to = Web3.to_checksum_address(input("To address: ").strip())
    amount = int(float(input("Amount (tokens): ")) * 10**18)
    tx = contract.functions.transferFrom(from_addr, to, amount).build_transaction({"gas": 250_000})
    send_tx(tx)

def increase_allowance():
    spender = Web3.to_checksum_address(input("Spender address: ").strip())
    amount = int(float(input("Amount (tokens): ")) * 10**18)
    tx = contract.functions.increaseAllowance(spender, amount).build_transaction({"gas": 200_000})
    send_tx(tx)

def decrease_allowance():
    spender = Web3.to_checksum_address(input("Spender address: ").strip())
    amount = int(float(input("Amount (tokens): ")) * 10**18)
    tx = contract.functions.decreaseAllowance(spender, amount).build_transaction({"gas": 200_000})
    send_tx(tx)

# You can add other functions like delegate, setContractURI, etc. in same style

# ----------------- CLI -----------------
parser = argparse.ArgumentParser(description="Interact with ArcERC20 contract")
parser.add_argument("function", help="Function to call (transfer, mint, burn, etc.)")
args = parser.parse_args()

functions = {
    "transfer": transfer,
    "mint": mint,
    "burn": burn,
    "burnFrom": burn_from,
    "approve": approve,
    "transferFrom": transfer_from,
    "increaseAllowance": increase_allowance,
    "decreaseAllowance": decrease_allowance,
    # add more as needed
}

func = functions.get(args.function)
if func:
    func()
else:
    print(f"Function {args.function} not implemented!")
