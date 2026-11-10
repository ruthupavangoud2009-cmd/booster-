import os
import json
import time
import random
import string
import requests
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List

BALANCES_FILE = "data/balances.json"
INVOICES_FILE = "data/invoices.json"
USED_TOKENS_FILE = "data/used_tokens.txt"
KEYS_FILE = "data/keys/keys.json"
DISCOUNTS_FILE = "data/discounts.json"

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
# Redeemable Key System (Instant Delivery Codes)
# ==========================================

def generate_boost_key(duration: str, amount: int, created_by: str = "shop") -> str:
    """
    Generates a unique redeemable boost code:
    e.g. BOOST-1M-2X-ABCD-1234
    """
    keys = load_json(KEYS_FILE, [])
    chars = string.ascii_uppercase + string.digits
    seg1 = ''.join(random.choices(chars, k=4))
    seg2 = ''.join(random.choices(chars, k=4))
    key_str = f"BOOST-{duration.upper()}-{amount}X-{seg1}-{seg2}"

    key_obj = {
        "key": key_str,
        "duration": duration.lower(),
        "amount": amount,
        "created_at": time.time(),
        "created_by": created_by,
        "status": "unused",
        "redeemed_by": None,
        "redeemed_at": None
    }
    keys.append(key_obj)
    save_json(KEYS_FILE, keys)
    return key_str

def redeem_boost_key(key_str: str, user_id: int) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Validates and redeems a key, adding credits to user's balance.
    """
    keys = load_json(KEYS_FILE, [])
    clean_key = key_str.strip().upper()

    for item in keys:
        if item.get("key", "").upper() == clean_key:
            if item.get("status") == "used":
                redeemed_at = datetime.fromtimestamp(item.get("redeemed_at", time.time())).strftime("%Y-%m-%d %H:%M")
                return False, f"This key has already been redeemed on {redeemed_at}.", item

            # Mark as redeemed
            item["status"] = "used"
            item["redeemed_by"] = user_id
            item["redeemed_at"] = time.time()
            save_json(KEYS_FILE, keys)

            # Credit balance
            add_user_balance(user_id, item["duration"], item["amount"])
            return True, f"Successfully redeemed key for **{item['amount']}x {item['duration']}** boosts!", item

    return False, "Invalid key code. Please check your spelling and try again.", None

def list_all_keys(filter_status: Optional[str] = None) -> List[Dict[str, Any]]:
    keys = load_json(KEYS_FILE, [])
    if filter_status:
        return [k for k in keys if k.get("status") == filter_status]
    return keys

# ==========================================
# Discount Codes
# ==========================================

def create_discount(code: str, percent: float) -> dict:
    discounts = load_json(DISCOUNTS_FILE, {})
    discounts[code.upper().strip()] = {
        "percent": min(max(percent, 1.0), 99.0),
        "created_at": time.time()
    }
    save_json(DISCOUNTS_FILE, discounts)
    return discounts[code.upper().strip()]

def get_discount_percent(code: str) -> float:
    if not code:
        return 0.0
    discounts = load_json(DISCOUNTS_FILE, {})
    d = discounts.get(code.upper().strip())
    if d:
        return float(d.get("percent", 0.0))
    return 0.0

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

    sep_file = f"data/used_{duration}.txt"
    with open(sep_file, "a", encoding="utf-8") as f:
        for t in tokens:
            f.write(f"{t}\n")

# ==========================================
# LTC Blockchain Verification & Live Wallet Inspector
# ==========================================

def get_wallet_live_info(address: str) -> Dict[str, Any]:
    """
    Fetches real-time wallet balance, total received, and recent transactions.
    """
    if not address or "PASTE" in address or len(address) < 20:
        return {"error": "LTC address not configured."}

    # 1. Try Blockchair API
    try:
        url = f"https://api.blockchair.com/litecoin/dashboards/address/{address}"
        resp = requests.get(url, timeout=6)
        if resp.status_code == 200:
            data = resp.json().get("data", {}).get(address, {})
            addr_info = data.get("address", {})
            return {
                "address": address,
                "balance_ltc": round(addr_info.get("balance", 0) / 1e8, 8),
                "total_received_ltc": round(addr_info.get("received", 0) / 1e8, 8),
                "total_sent_ltc": round(addr_info.get("spent", 0) / 1e8, 8),
                "tx_count": addr_info.get("transaction_count", 0),
                "recent_txs": data.get("transactions", [])[:5],
                "provider": "Blockchair",
                "explorer_url": f"https://blockchair.com/litecoin/address/{address}"
            }
    except Exception:
        pass

    # 2. Try BlockCypher API
    try:
        url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}"
        resp = requests.get(url, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "address": address,
                "balance_ltc": round(data.get("balance", 0) / 1e8, 8),
                "unconfirmed_balance_ltc": round(data.get("unconfirmed_balance", 0) / 1e8, 8),
                "total_received_ltc": round(data.get("total_received", 0) / 1e8, 8),
                "total_sent_ltc": round(data.get("total_sent", 0) / 1e8, 8),
                "tx_count": data.get("n_tx", 0),
                "recent_txs": [tx.get("tx_hash") for tx in data.get("txrefs", [])[:5]],
                "provider": "BlockCypher",
                "explorer_url": f"https://live.blockcypher.com/ltc/address/{address}/"
            }
    except Exception:
        pass

    return {
        "address": address,
        "balance_ltc": 0.0,
        "total_received_ltc": 0.0,
        "tx_count": 0,
        "explorer_url": f"https://blockchair.com/litecoin/address/{address}"
    }

def get_address_total_received(address: str) -> float:
    info = get_wallet_live_info(address)
    return info.get("total_received_ltc", 0.0)

# ==========================================
# Invoice Management & Auto-Delivery
# ==========================================

def create_invoice(
    user_id: int,
    duration: str,
    boosts: int,
    ltc_amount: float,
    address: str,
    target_invite: Optional[str] = None,
    discount_code: Optional[str] = None
) -> Dict[str, Any]:
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
        "target_invite": target_invite,
        "discount_code": discount_code,
        "created_at": time.time(),
        "status": "pending",
        "initial_received": current_received,
        "redeem_key": None
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
        return True, "Payment already completed and delivered.", inv

    if time.time() - inv["created_at"] > 3600:
        inv["status"] = "expired"
        save_json(INVOICES_FILE, invoices)
        return False, "This invoice has expired (60 minute limit). Please create a new one using $buy.", inv

    address = inv["address"]
    expected_ltc = inv["ltc_amount"]
    initial_ltc = inv.get("initial_received", 0.0)

    current_ltc = get_address_total_received(address)
    diff = round(current_ltc - initial_ltc, 6)

    # Tolerant match for incoming payment
    if diff >= round(expected_ltc * 0.995, 6) and diff > 0:
        inv["status"] = "completed"
        inv["paid_at"] = time.time()

        # Generate a redeemable key for instant delivery
        redeem_code = generate_boost_key(inv["duration"], inv["boosts"], created_by=f"order_{invoice_id}")
        inv["redeem_key"] = redeem_code

        invoices[invoice_id] = inv
        save_json(INVOICES_FILE, invoices)

        # Also credit user balance directly
        add_user_balance(inv["user_id"], inv["duration"], inv["boosts"])

        return True, f"Payment confirmed! Received {diff} LTC. Added {inv['boosts']}x {inv['duration']} boost credits to your account.", inv

    return False, f"Payment not detected yet. Expected {expected_ltc} LTC. (Received new: {diff} LTC)", inv

def force_complete_invoice(invoice_id: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Allows an owner to manually approve and credit an invoice."""
    invoices = load_json(INVOICES_FILE, {})
    inv = invoices.get(invoice_id)
    if not inv:
        return False, "Invoice not found.", None
    if inv["status"] == "completed":
        return True, "Invoice was already completed.", inv

    inv["status"] = "completed"
    inv["paid_at"] = time.time()
    redeem_code = generate_boost_key(inv["duration"], inv["boosts"], created_by=f"manual_{invoice_id}")
    inv["redeem_key"] = redeem_code
    invoices[invoice_id] = inv
    save_json(INVOICES_FILE, invoices)

    add_user_balance(inv["user_id"], inv["duration"], inv["boosts"])
    return True, f"Invoice {invoice_id} manually approved! Credited {inv['boosts']}x {inv['duration']} boosts to user <@{inv['user_id']}>.", inv

# ==========================================
# Sales Statistics
# ==========================================

def get_sales_stats() -> Dict[str, Any]:
    invoices = load_json(INVOICES_FILE, {})
    keys = load_json(KEYS_FILE, [])

    total_revenue_ltc = 0.0
    completed_orders = 0
    pending_orders = 0
    total_boosts_sold = 0

    for inv in invoices.values():
        if inv.get("status") == "completed":
            total_revenue_ltc += float(inv.get("ltc_amount", 0.0))
            completed_orders += 1
            total_boosts_sold += int(inv.get("boosts", 0))
        elif inv.get("status") == "pending":
            pending_orders += 1

    return {
        "total_revenue_ltc": round(total_revenue_ltc, 6),
        "completed_orders": completed_orders,
        "pending_orders": pending_orders,
        "total_boosts_sold": total_boosts_sold,
        "total_keys_generated": len(keys),
        "total_keys_redeemed": len([k for k in keys if k.get("status") == "used"])
    }
