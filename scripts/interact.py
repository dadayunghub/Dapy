# interact.py
import argparse
from web3 import Web3
import os
import json
import sys

# ----------------- Setup -----------------
RPC_URL = os.getenv("ARC_TESTNET_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ARC_ERC20_ADDRESS = os.getenv("ARC_ERC20_ADDRESS")

if not RPC_URL or not PRIVATE_KEY or not ARC_ERC20_ADDRESS:
    raise Exception("Missing required environment variables")

CONTRACT_ADDRESS = Web3.to_checksum_address(ARC_ERC20_ADDRESS)

with open("ArcERC20_ABI.json") as f:
    ABI = json.load(f)

w3 = Web3(Web3.HTTPProvider(RPC_URL))
assert w3.is_connected(), "RPC connection failed"

account = w3.eth.account.from_key(PRIVATE_KEY)
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

# ----------------- Helpers -----------------
def to_wei(amount):
    return int(float(amount) * 10**18)

def send_tx(tx, gas=300_000):
    tx["nonce"] = w3.eth.get_transaction_count(account.address)
    tx["chainId"] = w3.eth.chain_id
    # tx["gasPrice"] = w3.eth.gas_price
    tx["from"] = account.address
    tx["gas"] = gas

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"✅ Tx sent: {tx_hash.hex()}")

# ----------------- Contract Functions -----------------

def transfer(args):
    if not args.to or not args.amount:
        raise Exception("transfer requires --to and --amount")

    tx = contract.functions.transfer(
        Web3.to_checksum_address(args.to),
        to_wei(args.amount)
    ).build_transaction({"from": account.address})

    send_tx(tx)

def mint(args):
    if not args.to or not args.amount:
        raise Exception("mint requires --to and --amount")

    tx = contract.functions.mintTo(
        Web3.to_checksum_address(args.to),
        to_wei(args.amount)
    ).build_transaction({})

    send_tx(tx)

def burn(args):
    if not args.amount:
        raise Exception("burn requires --amount")

    tx = contract.functions.burn(
        to_wei(args.amount)
    ).build_transaction({})

    send_tx(tx)

def burnFrom(args):
    if not args.from_addr or not args.amount:
        raise Exception("burnFrom requires --from_addr and --amount")

    tx = contract.functions.burnFrom(
        Web3.to_checksum_address(args.from_addr),
        to_wei(args.amount)
    ).build_transaction({})

    send_tx(tx)

def approve(args):
    if not args.spender or not args.amount:
        raise Exception("approve requires --spender and --amount")

    tx = contract.functions.approve(
        Web3.to_checksum_address(args.spender),
        to_wei(args.amount)
    ).build_transaction({})

    send_tx(tx)

def transferFrom(args):
    if not args.from_addr or not args.to or not args.amount:
        raise Exception("transferFrom requires --from_addr, --to, --amount")

    tx = contract.functions.transferFrom(
        Web3.to_checksum_address(args.from_addr),
        Web3.to_checksum_address(args.to),
        to_wei(args.amount)
    ).build_transaction({})

    send_tx(tx)

def increaseAllowance(args):
    if not args.spender or not args.amount:
        raise Exception("increaseAllowance requires --spender and --amount")

    tx = contract.functions.increaseAllowance(
        Web3.to_checksum_address(args.spender),
        to_wei(args.amount)
    ).build_transaction({})

    send_tx(tx)

def decreaseAllowance(args):
    if not args.spender or not args.amount:
        raise Exception("decreaseAllowance requires --spender and --amount")

    tx = contract.functions.decreaseAllowance(
        Web3.to_checksum_address(args.spender),
        to_wei(args.amount)
    ).build_transaction({})

    send_tx(tx)

def delegate(args):
    if not args.delegatee:
        raise Exception("delegate requires --delegatee")

    tx = contract.functions.delegate(
        Web3.to_checksum_address(args.delegatee)
    ).build_transaction({})

    send_tx(tx)

def grantRole(args):
    if not args.role or not args.account:
        raise Exception("grantRole requires --role and --account")

    tx = contract.functions.grantRole(
        args.role,
        Web3.to_checksum_address(args.account)
    ).build_transaction({})

    send_tx(tx)

def revokeRole(args):
    if not args.role or not args.account:
        raise Exception("revokeRole requires --role and --account")

    tx = contract.functions.revokeRole(
        args.role,
        Web3.to_checksum_address(args.account)
    ).build_transaction({})

    send_tx(tx)

def renounceRole(args):
    if not args.role:
        raise Exception("renounceRole requires --role")

    tx = contract.functions.renounceRole(
        args.role,
        account.address
    ).build_transaction({})

    send_tx(tx)

def setContractURI(args):
    if not args.uri:
        raise Exception("setContractURI requires --uri")

    tx = contract.functions.setContractURI(args.uri).build_transaction({})
    send_tx(tx)

def setPrimarySaleRecipient(args):
    if not args.to:
        raise Exception("setPrimarySaleRecipient requires --to")

    tx = contract.functions.setPrimarySaleRecipient(
        Web3.to_checksum_address(args.to)
    ).build_transaction({})

    send_tx(tx)

def setPlatformFeeInfo(args):
    if not args.to or args.bps is None:
        raise Exception("setPlatformFeeInfo requires --to and --bps")

    tx = contract.functions.setPlatformFeeInfo(
        Web3.to_checksum_address(args.to),
        args.bps
    ).build_transaction({})

    send_tx(tx)

def multicall(args):
    if not args.calls:
        raise Exception("multicall requires --calls")

    calls = [bytes.fromhex(c.replace("0x", "")) for c in args.calls]
    tx = contract.functions.multicall(calls).build_transaction({"gas": 800_000})
    send_tx(tx)

# ----------------- CLI -----------------
parser = argparse.ArgumentParser(description="Interact with ArcERC20")

parser.add_argument("function")

parser.add_argument("--to")
parser.add_argument("--from_addr")
parser.add_argument("--amount")
parser.add_argument("--spender")
parser.add_argument("--delegatee")
parser.add_argument("--role")
parser.add_argument("--account")
parser.add_argument("--uri")
parser.add_argument("--bps", type=int)
parser.add_argument("--calls", nargs="*")

args = parser.parse_args()

FUNC_MAP = {
    "transfer": transfer,
    "mint": mint,
    "burn": burn,
    "burnFrom": burnFrom,
    "approve": approve,
    "transferFrom": transferFrom,
    "increaseAllowance": increaseAllowance,
    "decreaseAllowance": decreaseAllowance,
    "delegate": delegate,
    "grantRole": grantRole,
    "revokeRole": revokeRole,
    "renounceRole": renounceRole,
    "setContractURI": setContractURI,
    "setPrimarySaleRecipient": setPrimarySaleRecipient,
    "setPlatformFeeInfo": setPlatformFeeInfo,
    "multicall": multicall,
}

fn = FUNC_MAP.get(args.function)
if not fn:
    sys.exit(f"❌ Function '{args.function}' not implemented")

fn(args)
