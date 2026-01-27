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
import uuid
import base64
import codecs
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
# ----------------- Setup -----------------
RPC_URL = os.getenv("ARC_TESTNET_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ARC_ERC20_ADDRESS = os.getenv("ARC_ERC20_ADDRESS")
RESULT_API = 'https://contactprivatecel.vercel.app/api/testnt'
EMAIL_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD")
CIRCLE_API_KEY = os.getenv("CIRCLE_API_KEY")
CIRCLE_ENTITY_SECRET = os.getenv("CIRCLE_ENTITY_SECRET")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
PUBLICK = os.getenv("PUBLICK")

entity_secret = bytes.fromhex(CIRCLE_ENTITY_SECRET)

public_key = RSA.import_key(PUBLICK)
cipher_rsa = PKCS1_OAEP.new(public_key, hashAlgo=SHA256)
encrypted_data = cipher_rsa.encrypt(entity_secret)

ciphertext_b64 = base64.b64encode(encrypted_data).decode()



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


    
    
    result = {
        "txHash": tx_hash.hex(),
        "from": from_addr,
        "to": to_addr,
        "fromBefore": from_wei(from_balance_beforer),
        "fromAfter": from_wei(from_balance_afterr),
        "toBefore": from_wei(to_balance_beforer) if to_balance_beforer else "N/A",
        "toAfter": from_wei(to_balance_afterr) if to_balance_afterr else "N/A",
        "status": receipt.status,
    }

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
    return result
    
    
def send_batch_tx_email(results, failed=None):
    lines = ["ERC20 Transaction Batch Result<br><br>"]

    for r in results:
        lines.append(
            f"<b>Tx Hash:</b> {r['txHash']}<br>"
            f"<b>From:</b> {r['from']}<br>"
            f"<b>To:</b> {r['to']}<br>"
            f"<b>From Balance:</b> {r['fromBefore']} → {r['fromAfter']}<br>"
            f"<b>To Balance:</b> {r['toBefore']} → {r['toAfter']}<br>"
            f"<b>Status:</b> {'SUCCESS' if r['status'] == 1 else 'FAILED'}<br><br>"
        )

    if failed:
        lines.append("<hr><b>Failures</b><br><br>")
        for addr, nonce, err in failed:
            lines.append(
                f"<b>Address:</b> {addr}<br>"
                f"<b>Nonce:</b> {nonce}<br>"
                f"<b>Error:</b> {html.escape(err)}<br><br>"
            )

    body = build_email_html("".join(lines))

    send_email_html(
        to_email="uberchange90@gmail.com",
        subject="Arc Testnet ERC20 Batch Transaction Result",
        html_body=body,
        sender_name="Arc Runner",
    )

    print("📧 Batch email sent")

    
    

def run_many(tx_builder, targets, sleep_seconds=20):
    """
    tx_builder: function(target, nonce) -> tx dict
    targets: list of addresses
    sleep_seconds: delay between txs (IMPORTANT)
    """

    base_nonce = w3.eth.get_transaction_count(account.address)
    results = []
    failed = []

    print(f"🚀 Starting batch: {len(targets)} txs")

    # ---------- FIRST PASS ----------
    for i, target in enumerate(targets):
        nonce = base_nonce + i
        try:
            tx = tx_builder(target, nonce)
            results.append(send_tx(tx))
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
    
    return results, failed




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

        results, failed = run_many(tx_builder, targets, sleep_seconds=10)
        send_batch_tx_email(results, failed)
        return

    # SINGLE
    if not args.to:
        raise Exception("transfer requires --to")

    tx = contract.functions.transfer(
        Web3.to_checksum_address(args.to),
        to_wei(args.amount)
    ).build_transaction({"from": account.address})

    #send_tx(tx)
    result = send_tx(tx)
    send_batch_tx_email([result])




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
    

    url = "https://api.circle.com/v1/w3s/developer/transactions/transfer"

    headers = {
        "Authorization": f"Bearer {CIRCLE_API_KEY}",
        "Content-Type": "application/json",
    }

    results = []  # 👈 collect all tx results here

    def send(to_addr):
        payload = {
            "idempotencyKey": str(uuid.uuid4()),
            "entitySecretCiphertext": ciphertext_b64,  # ⚠️ ciphertext
            "amounts": [str(args.amount)],
            "destinationAddress": to_addr,
            "tokenAddress": "0x3600000000000000000000000000000000000000",
            "blockchain": "ARC-TESTNET",
            "walletAddress": os.getenv("WALLET_ADDRESS"),
            "feeLevel": "MEDIUM",
        }

        r = requests.post(url, headers=headers, json=payload, timeout=20)
        r.raise_for_status()
        return r.json()

    # ---------- MULTI ----------
    if args.to_list:
        targets = json.loads(args.to_list)

        for addr in targets:
            try:
                res = send(addr)
                results.append({
                    "address": addr,
                    "id": res.get("id"),
                    "state": res.get("state"),
                })
                print(f"✅ USDC sent → {addr}")

            except Exception as e:
                results.append({
                    "address": addr,
                    "error": str(e),
                })
                print(f"❌ Failed → {addr}: {e}")

            time.sleep(2)

    # ---------- SINGLE ----------
    else:
        if not args.to:
            raise Exception("transferusdc requires --to")

        try:
            res = send(args.to)
            results.append({
                "address": args.to,
                "id": res.get("id"),
                "state": res.get("state"),
            })
            print("✅ USDC sent")

        except Exception as e:
            results.append({
                "address": args.to,
                "error": str(e),
            })
            print("❌ Failed:", e)

    # ---------- BUILD EMAIL (ONCE) ----------
    lines = ["USDC Transfer Batch Result<br><br>"]

    for r in results:
        if "error" in r:
            lines.append(
                f"<b>Address:</b> {r['address']}<br>"
                f"<b>Status:</b> FAILED<br>"
                f"<b>Error:</b> {html.escape(r['error'])}<br><br>"
            )
        else:
            lines.append(
                f"<b>Address:</b> {r['address']}<br>"
                f"<b>Tx ID:</b> {r['id']}<br>"
                f"<b>State:</b> {r['state']}<br><br>"
            )

    message_html = "".join(lines)
    body = build_email_html(message_html)

    # ---------- SEND EMAIL (ONCE) ----------
    send_email_html(
        to_email="uberchange90@gmail.com",
        subject="Arc Testnet USDC Batch Transfer Result",
        html_body=body,
        sender_name="Arc Runner USDC",
    )

    print("📧 Batch email sent")




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
