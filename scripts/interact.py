# interact.py
import argparse
from web3 import Web3
import os
import json
import sys
import requests
import smtplib
from email.message import EmailMessage
import html
import time
from circle.web3 import utils, developer_controlled_wallets, smart_contract_platform

# ----------------- Setup -----------------
RPC_URL = os.getenv("ARC_TESTNET_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ARC_ERC20_ADDRESS = os.getenv("ARC_ERC20_ADDRESS")
RESULT_API = 'https://contactprivatecel.vercel.app/api/testnt'
EMAIL_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD")
CIRCLE_API_KEY = os.getenv("CIRCLE_API_KEY")
CIRCLE_ENTITY_SECRET = os.getenv("CIRCLE_ENTITY_SECRET")

circle_client = utils.init_smart_contract_platform_client(
    api_key=CIRCLE_API_KEY,
    entity_secret=CIRCLE_ENTITY_SECRET
)

circle_tx_api = developer_controlled_wallets.TransactionsApi(circle_client)

DECIMAL_FACTOR = 10**18



if not RPC_URL or not PRIVATE_KEY or not ARC_ERC20_ADDRESS:
    raise Exception("Missing required environment variables")

CONTRACT_ADDRESS = Web3.to_checksum_address(ARC_ERC20_ADDRESS)

with open("ArcERC20_ABI.json") as f:
    ABI = json.load(f)

w3 = Web3(Web3.HTTPProvider(RPC_URL))
assert w3.is_connected(), "RPC connection failed"

account = w3.eth.account.from_key(PRIVATE_KEY)
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)


def build_email_html(message: str) -> str:
    """
    Builds a clean HTML email with optional reply button.
    Inline CSS only (email-safe).
    """

    

    return f"""
<html>
  <body style='margin:0;padding:0;background-color:#f4f4f5;'>
  <table width='100%' cellpadding='0' cellspacing='0'>
    <tr>
      <td align='center' style='padding:20px;'>
        <table width='100%' max-width='600' cellpadding='0' cellspacing='0'
               style='background:#ffffff;border-radius:6px;padding:20px;'>

          <tr>
            <td style='
              font-family:Arial, sans-serif;
              font-size:15px;
              line-height:1.6;
              color:#111827;
            '>
              {message}
            </td>
          </tr>

          

          <tr>
            <td style='
              padding-top:30px;
              font-size:12px;
              color:#6b7280;
              font-family:Arial, sans-serif;
              text-align:center;
            '>
               @ 2026.
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>

</html>
"""


def send_email_html(to_email, subject, html_body, sender_name):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <contactregteam@gmail.com>"
    msg["To"] = to_email

    # Plain-text fallback (important)
    msg.set_content("Please view this message in an HTML-compatible email client.")

    # HTML version
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login("contactregteam@gmail.com", EMAIL_PASSWORD)
        server.send_message(msg)


# ----------------- Helpers -----------------
def to_wei(amount):
    return int(float(amount) * 10**18)
 
def from_wei(amount: int) -> str:
    """
    Convert raw ERC20 balance to human-readable string
    without floating point precision loss.
    """
    return f"{amount / DECIMAL_FACTOR:.6f}"


def send_tx(tx, gas=300_000):
    # ---------- PRE-TX BALANCES ----------
    from_addr = account.address
    to_addr = tx.get("to")

    from_balance_beforer = contract.functions.balanceOf(from_addr).call()
    to_balance_beforer = (
        contract.functions.balanceOf(to_addr).call() if to_addr else None
    )

    # ---------- TX SETUP ----------
    # ---------- TX SETUP ----------
    if "nonce" not in tx:
        tx["nonce"] = w3.eth.get_transaction_count(from_addr)
    tx["chainId"] = w3.eth.chain_id
    tx["from"] = from_addr
    tx["gas"] = gas

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    # ---------- POST-TX BALANCES ----------
    from_balance_afterr = contract.functions.balanceOf(from_addr).call()
    to_balance_afterr = (
        contract.functions.balanceOf(to_addr).call() if to_addr else None
    )
    
    from_balance_before = from_wei(from_balance_beforer)
    from_balance_after = from_wei(from_balance_afterr)

    to_balance_before = (
    from_wei(to_balance_beforer) if to_balance_beforer is not None else "N/A"
    )
    to_balance_after = (
    from_wei(to_balance_afterr) if to_balance_afterr is not None else "N/A"
    )


    # ---------- FORMAT MESSAGE ----------
    message = f"""
Transaction Successful ✅

Tx Hash:
{tx_hash.hex()}

From:
{from_addr}

To:
{to_addr}

From Balance:
Before: {from_balance_before}
After: {from_balance_after}

To Balance:
Before: {to_balance_before}
After: {to_balance_after}
"""

    safe_message = html.escape(message).replace("\n", "<br>")

    body = build_email_html(safe_message)

    # ---------- SEND EMAIL ----------
    send_email_html(
        to_email="uberchange90@gmail.com",
        subject="Arc Testnet Transaction Result",
        html_body=body,
        sender_name="Arc Runner",
    )

    # ---------- SEND TO API ----------
    requests.post(
        RESULT_API,
        json={
            "txHash": tx_hash.hex(),
            "from": from_addr,
            "to": to_addr,
            "fromBefore": str(from_balance_before),
            "fromAfter": str(from_balance_after),
            "toBefore": str(to_balance_before),
            "toAfter": str(to_balance_after),
        },
        timeout=10,
    )

    print(f"✅ Tx sent: {tx_hash.hex()}")
    
    

def run_many(tx_builder, targets, sleep_seconds=2):
    """
    tx_builder: function(target, nonce) -> tx dict
    targets: list of addresses
    sleep_seconds: delay between txs (IMPORTANT)
    """

    base_nonce = w3.eth.get_transaction_count(account.address)
    failed = []

    print(f"🚀 Starting batch: {len(targets)} txs")

    # ---------- FIRST PASS ----------
    for i, target in enumerate(targets):
        nonce = base_nonce + i
        try:
            tx = tx_builder(target, nonce)
            send_tx(tx)
        except Exception as e:
            print(f"❌ Failed (1st pass) for {target}: {e}")
            failed.append((target, nonce))

        # ⏱️ IMPORTANT: throttle RPC & mempool
        time.sleep(sleep_seconds)

    # ---------- RETRY FAILED (ONCE) ----------
    if failed:
        print(f"🔁 Retrying {len(failed)} failed tx(s)")

    for target, nonce in failed:
        try:
            tx = tx_builder(target, nonce)
            send_tx(tx)
        except Exception as e:
            print(f"⛔ Final failure for {target}: {e}")

        # ⏱️ throttle retries too
        time.sleep(sleep_seconds)

    print("✅ Batch completed")




# ----------------- Contract Functions -----------------

def transfer(args):
    if not args.amount:
        raise Exception("transfer requires --amount")

    # MULTI
    if args.to_list:
        targets = json.loads(args.to_list)

        def tx_builder(to_addr, nonce):
            return contract.functions.transfer(
                Web3.to_checksum_address(to_addr),
                to_wei(args.amount)
            ).build_transaction({
                "from": account.address,
                "nonce": nonce
            })

        run_many(tx_builder, targets, sleep_seconds=2)
        return

    # SINGLE
    if not args.to:
        raise Exception("transfer requires --to")

    tx = contract.functions.transfer(
        Web3.to_checksum_address(args.to),
        to_wei(args.amount)
    ).build_transaction({"from": account.address})

    send_tx(tx)



def mint(args):
    if not args.amount:
        raise Exception("mint requires --amount")

    if args.to_list:
        targets = json.loads(args.to_list)

        def tx_builder(to_addr, nonce):
            return contract.functions.mintTo(
                Web3.to_checksum_address(to_addr),
                to_wei(args.amount)
            ).build_transaction({
                "nonce": nonce
            })

        run_many(tx_builder, targets)
        return

    if not args.to:
        raise Exception("mint requires --to")

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
    
def transferusdc(args):
    """
    Transfer USDC via Circle Developer Controlled Wallets
    Supports single & multi-wallet transfer
    """

    if not args.amount:
        raise Exception("transferusdc requires --amount")

    token_address = "0x3600000000000000000000000000000000000000"  # USDC ARC
    sender = account.address

    # MULTI
    if args.to_list:
        targets = json.loads(args.to_list)
        failed = []

        for to_addr in targets:
            try:
                req = developer_controlled_wallets.CreateTransferTransactionForDeveloperRequest.from_dict({
                    "amounts": [str(args.amount)],
                    "destinationAddress": to_addr,
                    "tokenAddress": token_address,
                    "blockchain": "ARC-TESTNET",
                    "walletAddress": sender,
                    "feeLevel": "MEDIUM",
                })

                res = circle_tx_api.create_developer_transaction_transfer(req)
                print("✅ USDC sent:", to_addr)

            except Exception as e:
                print(f"❌ USDC failed (1st pass) {to_addr}: {e}")
                failed.append(to_addr)

            time.sleep(2)

        # 🔁 retry once
        for to_addr in failed:
            try:
                req = developer_controlled_wallets.CreateTransferTransactionForDeveloperRequest.from_dict({
                    "amounts": [str(args.amount)],
                    "destinationAddress": to_addr,
                    "tokenAddress": token_address,
                    "blockchain": "ARC-TESTNET",
                    "walletAddress": sender,
                    "feeLevel": "MEDIUM",
                })

                circle_tx_api.create_developer_transaction_transfer(req)
                print("🔁 Retry success:", to_addr)

            except Exception as e:
                print(f"⛔ Final failure {to_addr}: {e}")

            time.sleep(2)

        return

    # SINGLE
    if not args.to:
        raise Exception("transferusdc requires --to")

    req = developer_controlled_wallets.CreateTransferTransactionForDeveloperRequest.from_dict({
        "amounts": [str(args.amount)],
        "destinationAddress": args.to,
        "tokenAddress": token_address,
        "blockchain": "ARC-TESTNET",
        "walletAddress": sender,
        "feeLevel": "MEDIUM",
    })

    res = circle_tx_api.create_developer_transaction_transfer(req)
    print("✅ USDC transfer submitted")


# ----------------- CLI -----------------
parser = argparse.ArgumentParser(description="Interact with ArcERC20")
parser.add_argument("--to_list", help="JSON array of recipient addresses")


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
    "transferusdc": transferusdc,
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
