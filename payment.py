import os
import json
import time
import requests
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

BALANCES_FILE = "data/balances.json"
INVOICES_FILE = "data/invoices.json"
USED_TOKENS_FILE = "data/used_tokens.txt"

def load_json(filepath: str, default: Any) -> Any:
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(filepath: str, data: Any):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ==========================================
# Balance Management
# ==========================================

def get_user_balance(user_id: int) -> Dict[str, int]:
    """Returns the user's boost credit balance: {'1m': int, '3m': int}."""
    balances = load_json(BALANCES_FILE, {})
    user_data = balances.get(str(user_id), {})
    return {
        "1m": int(user_data.get("1m", 0)),
        "3m": int(user_data.get("3m", 0))
    }

def add_user_balance(user_id: int, duration: str, amount: int) -> Dict[str, int]:
    """Adds boost credits to a user."""
    balances = load_json(BALANCES_FILE, {})
    uid = str(user_id)
    if uid not in balances:
        balances[uid] = {"1m": 0, "3m": 0}
    balances[uid][duration] = balances[uid].get(duration, 0) + amount
    save_json(BALANCES_FILE, balances)
    return balances[uid]

def deduct_user_balance(user_id: int, duration: str, amount: int) -> bool:
    """Deducts boost credits from a user if they have sufficient balance."""
    balances = load_json(BALANCES_FILE, {})
    uid = str(user_id)
    if uid not in balances:
        return False
    current = balances[uid].get(duration, 0)
    if current < amount:
        return False
    balances[uid][duration] = current - amount
    save_json(BALANCES_FILE, balances)
    return True

# ==========================================
# Used Tokens Archiving
# ==========================================

def archive_used_tokens(tokens: list, duration: str, invite: str):
    """
    Archives used tokens into data/used_tokens.txt and data/used_{1m|3m}.txt.
    Ensures they are moved out of stock and never re-used for boosts.
    """
    os.makedirs("data", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(USED_TOKENS_FILE, "a", encoding="utf-8") as f:
        for t in tokens:
            f.write(f"[{timestamp}] [{duration}] [Invite: .gg/{invite}] {t}\n")

    # Also keep duration-specific used lists
    sep_file = f"data/used_{duration}.txt"
    with open(sep_file, "a", encoding="utf-8") as f:
        for t in tokens:
            f.write(f"{t}\n")

# ==========================================
# LTC Blockchain Verification
# ==========================================

def get_address_total_received(address: str) -> float:
    """Queries public block explorers for total LTC received by this address."""
    if not address or "PASTE" in address or len(address) < 20:
        return 0.0

    # Provider 1: Blockchair API
    try:
        url = f"https://api.blockchair.com/litecoin/dashboards/address/{address}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json().get("data", {}).get(address, {})
            addr_info = data.get("address", {})
            return round(addr_info.get("received", 0) / 1e8, 8)
    except Exception:
        pass

    # Provider 2: BlockCypher API
    try:
        url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}/balance"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            total_sat = data.get("total_received", 0) + data.get("unconfirmed_balance", 0)
            return round(total_sat / 1e8, 8)
    except Exception:
        pass

    return 0.0

# ==========================================
# Invoice Management
# ==========================================

def create_invoice(user_id: int, duration: str, boosts: int, ltc_amount: float, address: str) -> Dict[str, Any]:
    invoices = load_json(INVOICES_FILE, {})
    invoice_id = f"INV-{int(time.time())}-{user_id % 10000}"
    current_received = get_address_total_received(address)

    invoice = {
        "id": invoice_id,
        "user_id": user_id,
        "duration": duration,
        "boosts": boosts,
        "ltc_amount": round(ltc_amount, 6),
        "address": address,
        "created_at": time.time(),
        "status": "pending",
        "initial_received": current_received
    }
    invoices[invoice_id] = invoice
    save_json(INVOICES_FILE, invoices)
    return invoice

def get_invoice(invoice_id: str) -> Optional[Dict[str, Any]]:
    invoices = load_json(INVOICES_FILE, {})
    return invoices.get(invoice_id)

def check_invoice_payment(invoice_id: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    invoices = load_json(INVOICES_FILE, {})
    inv = invoices.get(invoice_id)
    if not inv:
        return False, "Invoice not found.", None

    if inv["status"] == "completed":
        return True, "Payment already completed and credits delivered.", inv

    if time.time() - inv["created_at"] > 3600:  # 60 min expiration
        inv["status"] = "expired"
        save_json(INVOICES_FILE, invoices)
        return False, "This invoice has expired (60 minute limit). Please create a new one using $buy.", inv

    address = inv["address"]
    expected_ltc = inv["ltc_amount"]
    initial_ltc = inv.get("initial_received", 0.0)

    current_ltc = get_address_total_received(address)
    diff = round(current_ltc - initial_ltc, 6)

    # If new funds received match expected amount (with 0.5% tolerance for dust/fees)
    if diff >= round(expected_ltc * 0.995, 6) and diff > 0:
        inv["status"] = "completed"
        inv["paid_at"] = time.time()
        invoices[invoice_id] = inv
        save_json(INVOICES_FILE, invoices)

        # Credit the user's balance
        add_user_balance(inv["user_id"], inv["duration"], inv["boosts"])
        return True, f"Payment confirmed! Received {diff} LTC. Added {inv['boosts']}x {inv['duration']} boost credits to your account.", inv

    return False, f"Payment not detected yet. Expected {expected_ltc} LTC at `{address}`. (New detected: {diff} LTC)", inv

def force_complete_invoice(invoice_id: str) -> Tuple[bool, str]:
    """Allows an owner to manually approve and credit an invoice."""
    invoices = load_json(INVOICES_FILE, {})
    inv = invoices.get(invoice_id)
    if not inv:
        return False, "Invoice not found."
    if inv["status"] == "completed":
        return True, "Invoice was already completed."

    inv["status"] = "completed"
    inv["paid_at"] = time.time()
    invoices[invoice_id] = inv
    save_json(INVOICES_FILE, invoices)

    add_user_balance(inv["user_id"], inv["duration"], inv["boosts"])
    return True, f"Invoice {invoice_id} manually approved! Credited {inv['boosts']}x {inv['duration']} boosts to user <@{inv['user_id']}>."
