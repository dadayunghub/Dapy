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

from eth_account import Account
from eth_account.messages import encode_structured_data

# ----------------- Setup -----------------
RPC_URL = os.getenv("ARC_TESTNET_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ARC_ERC20_ADDRESS = os.getenv("ARC_ERC20_ADDRESS")
RESULT_API = 'https://contactprivatecel.vercel.app/api/testnt'
token_API = 'https://contactprivatecel.vercel.app/api/token'
EMAIL_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD")
CIRCLE_API_KEY = os.getenv("CIRCLE_API_KEY")
CIRCLE_ENTITY_SECRET = os.getenv("CIRCLE_ENTITY_SECRET")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")

def encrypt_entity_secret():
    PUBLICK = os.getenv("PUBLICK").replace("\\n", "\n")
    entity_secret = bytes.fromhex(os.getenv("CIRCLE_ENTITY_SECRET"))

    public_key = RSA.import_key(PUBLICK)
    cipher_rsa = PKCS1_OAEP.new(public_key, hashAlgo=SHA256)

    encrypted_data = cipher_rsa.encrypt(entity_secret)
    return base64.b64encode(encrypted_data).decode()



DECIMAL_FACTOR = 10**18


def init_chain():
    

    if not RPC_URL or not PRIVATE_KEY or not ARC_ERC20_ADDRESS:
        raise Exception("Missing blockchain environment variables")

    with open("ArcERC20_ABI.json") as f:
        abi = json.load(f)

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        raise Exception("RPC connection failed")

    account = w3.eth.account.from_key(PRIVATE_KEY)
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(ARC_ERC20_ADDRESS),
        abi=abi
    )

    return w3, account, contract



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
    w3, account, contract = init_chain()
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
    w3, account, contract = init_chain()

    # IMPORTANT: use pending nonce
    base_nonce = w3.eth.get_transaction_count(account.address, "pending")

    results = []
    failed = []
    final_failed = []

    print(f"🚀 Starting batch: {len(targets)} txs")

    # ---------- FIRST PASS ----------
    for i, target in enumerate(targets):
        nonce = base_nonce + i
        try:
            tx = tx_builder(target, nonce)
            results.append(send_tx(tx))
        except Exception as e:
            print(f"❌ Failed (1st pass) for {target}: {e}")
            failed.append((target, nonce, str(e)))

        time.sleep(sleep_seconds)

    # ---------- RETRY FAILED (ONCE) ----------
    if failed:
        print(f"🔁 Retrying {len(failed)} failed tx(s)")

    for target, _, first_err in failed:
        try:
            # ALWAYS refresh nonce before retry
            retry_nonce = w3.eth.get_transaction_count(
                account.address, "pending"
            )

            tx = tx_builder(target, retry_nonce)
            results.append(send_tx(tx))

        except Exception as e:
            print(f"⛔ Final failure for {target}: {e}")
            final_failed.append((target, retry_nonce, str(e)))

        time.sleep(sleep_seconds)

    print("✅ Batch completed")

    return results, final_failed




# ----------------- Contract Functions -----------------

def transfer(args):
    w3, account, contract = init_chain()

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
    w3, account, contract = init_chain()

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
            "entitySecretCiphertext": encrypt_entity_secret(),  # ⚠️ ciphertext
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



def getfaucet(args):
    results = []
    last_failed_addr = None
    last_processed_addr = None

    FAUCET_URL = "https://api.circle.com/v1/faucet/drips"
    TOKEN_API = token_API  # assumed already defined

    HEADERS = {
        "Authorization": f"Bearer {os.getenv('CIRCLE_API_KEY')}",
        "Content-Type": "application/json",
    }

    def send(to_addr):
        last_processed_addr = to_addr
        last_failed_addr = to_addr
        payload = {
            "address": to_addr,
            "blockchain": "ARC-TESTNET",
            "native": False,
            "usdc": True,
            "eurc": True,
        }

        response = requests.post(
            FAUCET_URL,
            json=payload,
            headers=HEADERS,
            timeout=15,
        )

        # ✅ Circle faucet success = 204 No Content
        if response.status_code != 204:
            try:
                error_json = response.json()
                error_message = error_json.get("message", response.text)
            except Exception:
                error_message = response.text

            raise Exception(f"HTTP {response.status_code}: {error_message}")

        return True

    # ---------- RUN FAUCET FOR MULTIPLE WALLETS ----------
    if args.to_list:
        targets = json.loads(args.to_list)

        for addr in targets:
            try:
                send(addr)

                results.append({
                    "address": addr,
                    "status": "success",
                })

                print(f"✅ Faucet USDC & EURC sent → {addr}")

            except Exception as e:
                last_failed_addr = addr

                results.append({
                    "address": addr,
                    "status": "failed",
                    "error": str(e),
                })

                print(f"❌ Faucet failed → {addr}: {e}")

                # ⛔ Stop batch on first failure
                break

            time.sleep(50)

    # ---------- NOTIFY TOKEN API ON FAILURE ----------
    #if last_failed_addr:
        #requests.post(
            #TOKEN_API,
            #json={"failed": last_failed_addr},
            #timeout=10,
        #)
        
    # ---------- NOTIFY TOKEN API ----------
    if last_processed_addr:
        requests.post(
            TOKEN_API,
            json={
            "lastaddr": last_processed_addr,
            "failed": last_failed_addr,
        },
        timeout=10,
        )


    # ---------- BUILD EMAIL ----------
    lines = ["<h3>ARC Testnet Faucet Batch Result</h3><br>"]

    for r in results:
        if r["status"] == "failed":
            lines.append(
                f"<b>Address:</b> {r['address']}<br>"
                f"<b>Status:</b> ❌ FAILED<br>"
                f"<b>Error:</b> {html.escape(r['error'])}<br><br>"
            )
        else:
            lines.append(
                f"<b>Address:</b> {r['address']}<br>"
                f"<b>Status:</b> ✅ SUCCESS<br><br>"
            )

    message_html = "".join(lines)
    body = build_email_html(message_html)

    # ---------- SEND EMAIL (ONCE) ----------
    send_email_html(
        to_email="uberchange90@gmail.com",
        subject="ARC Testnet Faucet – USDC & EURC Batch Result",
        html_body=body,
        sender_name="Arc Runner",
    )

    print("📧 Faucet batch email sent")

    return results



def transferdev(args):
    

    url = "https://api.circle.com/v1/w3s/developer/transactions/contractExecution"

    headers = {
        "Authorization": f"Bearer {CIRCLE_API_KEY}",
        "Content-Type": "application/json",
    }

    results = []  # 👈 collect all tx results here

    def send(to_addr):
        payload = {
            "idempotencyKey": str(uuid.uuid4()),
            "entitySecretCiphertext": encrypt_entity_secret(),  # ⚠️ ciphertext
            "abiFunctionSignature": "transfer(address,uint256)",
            "abiParameters": [
                to_addr,
             str(args.amount)
                        ],
            "contractAddress": ARC_ERC20_ADDRESS,
           
            "walletId": os.getenv("PRIVATE_KEY"),
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
                print(f"✅ Arc contract sent → {addr}")

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
            print("✅ Arc CA sent")

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
                f"<b>Address CA:</b> {r['address']}<br>"
                f"<b>Status:</b> FAILED<br>"
                f"<b>Error:</b> {html.escape(r['error'])}<br><br>"
            )
        else:
            lines.append(
                f"<b>Address CA:</b> {r['address']}<br>"
                f"<b>Tx ID:</b> {r['id']}<br>"
                f"<b>State:</b> {r['state']}<br><br>"
            )

    message_html = "".join(lines)
    body = build_email_html(message_html)

    # ---------- SEND EMAIL (ONCE) ----------
    send_email_html(
        to_email="uberchange90@gmail.com",
        subject="Arc Testnet Arc contract Batch Transfer Result",
        html_body=body,
        sender_name="Arc Arc CA",
    )

    print("📧 Batch email sent")


def sign_permit(
    private_key,
    owner,
    spender,
    value,
    nonce,
    deadline=None
):
    if deadline is None:
        deadline = int(time.time()) + 3600  # 1 hour
        
    TOKEN_NAME = "ArcToken"          # ⚠️ MUST match contract
    CHAIN_ID = 12345

    typed_data = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "Permit": [
                {"name": "owner", "type": "address"},
                {"name": "spender", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "nonce", "type": "uint256"},
                {"name": "deadline", "type": "uint256"},
            ],
        },
        "primaryType": "Permit",
        "domain": {
            "name": TOKEN_NAME,
            "version": "1",
            "chainId": CHAIN_ID,
            "verifyingContract": TOKEN_ADDRESS,
        },
        "message": {
            "owner": owner,
            "spender": spender,
            "value": value,
            "nonce": nonce,
            "deadline": deadline,
        },
    }

    msg = encode_structured_data(typed_data)
    signed = Account.sign_message(msg, private_key)

    return signed.v, signed.r, signed.s, deadline



def transferpermit(args):
    results = []
    
    CIRCLE_URL = "https://api.circle.com/v1/w3s/developer/transactions/contractExecution"

    w3 = Web3(Web3.HTTPProvider(RPC_URL))

    # -------- PARSE INPUTS --------
    recipients = json.loads(args.to_list)   # list of {to, amount} OR list of addresses
    owner_private_key = args.wpr
    circle_wallet_id = args.wpr2

    # -------- DERIVE ADDRESSES --------
    sender_address = Account.from_key(owner_private_key).address
    spender_address = os.getenv("CIRCLE_WALLET_ADDRESS")

    # -------- READ NONCE --------
    token_abi = [{
        "name": "nonces",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "owner", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
    }]

    token = w3.eth.contract(address=TOKEN_ADDRESS, abi=token_abi)
    nonce = token.functions.nonces(sender_address).call()

    try:
        # -------- CALCULATE TOTAL PERMIT AMOUNT --------
        if isinstance(recipients[0], dict):
            total_amount = sum(int(r["amount"]) for r in recipients)
        else:
            total_amount = int(args.amount) * len(recipients)

        # -------- SIGN PERMIT OFF-CHAIN --------
        v, r, s, deadline = sign_permit(
            private_key=owner_private_key,
            owner=sender_address,
            spender=spender_address,
            value=total_amount,
            nonce=nonce,
        )

        headers = {
            "Authorization": f"Bearer {CIRCLE_API_KEY}",
            "Content-Type": "application/json",
        }

        # -------- 1️⃣ SUBMIT PERMIT --------
        permit_payload = {
            "idempotencyKey": str(uuid.uuid4()),
            "walletId": circle_wallet_id,
            "contractAddress": TOKEN_ADDRESS,
            "abiFunctionSignature": "permit(address,address,uint256,uint256,uint8,bytes32,bytes32)",
            "abiParameters": [
                sender_address,
                spender_address,
                str(total_amount),
                str(deadline),
                v,
                Web3.to_hex(r),
                Web3.to_hex(s),
            ],
            "feeLevel": "HIGH",
        }

        permit_res = requests.post(
            CIRCLE_URL,
            json=permit_payload,
            headers=headers,
            timeout=20,
        )
        permit_res.raise_for_status()
        permit_data = permit_res.json()

        permit_tx_id = permit_data.get("id")

        # -------- 2️⃣ TRANSFERFROM (BATCH) --------
        for rec in recipients:
            to_addr = rec["to"] if isinstance(rec, dict) else rec
            amt = int(rec["amount"]) if isinstance(rec, dict) else int(args.amount)

            transfer_payload = {
                "idempotencyKey": str(uuid.uuid4()),
                "walletId": circle_wallet_id,
                "contractAddress": TOKEN_ADDRESS,
                "abiFunctionSignature": "transferFrom(address,address,uint256)",
                "abiParameters": [
                    sender_address,
                    to_addr,
                    str(amt),
                ],
                "feeLevel": "HIGH",
            }

            tx_res = requests.post(
                CIRCLE_URL,
                json=transfer_payload,
                headers=headers,
                timeout=20,
            )
            tx_res.raise_for_status()
            tx_data = tx_res.json()

            results.append({
                "from": sender_address,
                "to": to_addr,
                "permitTx": permit_tx_id,
                "transferTx": tx_data.get("id"),
                "state": tx_data.get("state", "SUBMITTED"),
            })

    except Exception as e:
        results.append({
            "from": sender_address,
            "to": "N/A",
            "error": str(e),
        })

    # -------- BUILD EMAIL --------
    lines = ["<b>Permit + Transfer Result</b><br><br>"]

    for r in results:
        if "error" in r:
            lines.append(
                f"<b>From:</b> {r['from']}<br>"
                f"<b>Status:</b> FAILED<br>"
                f"<b>Error:</b> {html.escape(r['error'])}<br><br>"
            )
        else:
            lines.append(
                f"<b>From:</b> {r['from']}<br>"
                f"<b>To:</b> {r['to']}<br>"
                f"<b>Permit Tx:</b> {r['permitTx']}<br>"
                f"<b>Transfer Tx:</b> {r['transferTx']}<br>"
                f"<b>Status:</b> {r['state']}<br><br>"
            )

    body = build_email_html("".join(lines))

    send_email_html(
        to_email="uberchange90@gmail.com",
        subject="Arc Permit + Transfer Result",
        html_body=body,
        sender_name="Arc Admin",
    )

    return results


# ----------------- CLI -----------------
parser = argparse.ArgumentParser(description="Interact with ArcERC20")
parser.add_argument("--to_list", help="JSON array of recipient addresses")


parser.add_argument("function")

parser.add_argument("--to")
parser.add_argument("--from_addr")
parser.add_argument("--amount")
parser.add_argument("--wpr")
parser.add_argument("--wpr2")
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
    "transferdev": transferdev,
    "mint": mint,
    "getfaucet": getfaucet,
}

fn = FUNC_MAP.get(args.function)
if not fn:
    sys.exit(f"❌ Function '{args.function}' not implemented")

fn(args)
