import os
import json
import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

DEFAULT_DATABASE_URL = "postgresql://postgres:ilovemymomandcar@db.ryjxvgficixwhacywdai.supabase.co:5432/postgres"
DATABASE_URL = os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL

_pg_pool = None
_db_connected = False

def is_db_connected() -> bool:
    return _db_connected

async def get_pg_pool():
    global _pg_pool, _db_connected
    if _pg_pool is not None:
        return _pg_pool

    try:
        import asyncpg
        _pg_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=10,
            command_timeout=15,
            timeout=10
        )
        _db_connected = True
        return _pg_pool
    except Exception as e:
        _db_connected = False
        return None

async def init_database():
    """Initializes all required PostgreSQL tables on startup and syncs cached records."""
    global _db_connected
    pool = await get_pg_pool()
    if not pool:
        print(" [~] Note: PostgreSQL offline or unreachable. Using robust local storage engine.")
        return False

    create_tables_sql = """
    CREATE TABLE IF NOT EXISTS balances (
        user_id BIGINT PRIMARY KEY,
        credits_1m INT DEFAULT 0,
        credits_3m INT DEFAULT 0,
        updated_at DOUBLE PRECISION
    );

    CREATE TABLE IF NOT EXISTS invoices (
        id VARCHAR(64) PRIMARY KEY,
        user_id BIGINT,
        duration VARCHAR(10),
        boosts INT,
        crypto VARCHAR(10),
        amount NUMERIC,
        address TEXT,
        target_invite TEXT,
        discount_code TEXT,
        status VARCHAR(20) DEFAULT 'pending',
        tx_hash TEXT,
        redeem_key TEXT,
        delivered BOOLEAN DEFAULT FALSE,
        created_at DOUBLE PRECISION,
        paid_at DOUBLE PRECISION
    );

    CREATE TABLE IF NOT EXISTS tickets (
        channel_id BIGINT PRIMARY KEY,
        guild_id BIGINT,
        user_id BIGINT,
        user_name TEXT,
        topic TEXT,
        topic_key TEXT,
        status VARCHAR(20) DEFAULT 'open',
        claimed_by BIGINT,
        created_at DOUBLE PRECISION,
        closed_at DOUBLE PRECISION,
        close_reason TEXT
    );

    CREATE TABLE IF NOT EXISTS license_keys (
        key VARCHAR(64) PRIMARY KEY,
        duration VARCHAR(10),
        amount INT,
        created_by TEXT,
        status VARCHAR(20) DEFAULT 'unused',
        redeemed_by BIGINT,
        redeemed_at DOUBLE PRECISION,
        created_at DOUBLE PRECISION
    );

    CREATE TABLE IF NOT EXISTS discounts (
        code VARCHAR(32) PRIMARY KEY,
        percent NUMERIC,
        created_at DOUBLE PRECISION
    );

    CREATE TABLE IF NOT EXISTS claimed_txs (
        tx_hash VARCHAR(128) PRIMARY KEY,
        invoice_id VARCHAR(64),
        crypto VARCHAR(10),
        amount NUMERIC,
        claimed_at DOUBLE PRECISION
    );

    CREATE TABLE IF NOT EXISTS customer_reviews (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        user_name TEXT,
        rating INT,
        comment TEXT,
        product TEXT,
        created_at DOUBLE PRECISION
    );

    CREATE TABLE IF NOT EXISTS bot_settings (
        key VARCHAR(64) PRIMARY KEY,
        value TEXT
    );
    """
    try:
        async with pool.acquire() as conn:
            await conn.execute(create_tables_sql)
        _db_connected = True
        print(" [+] Supabase PostgreSQL Database Initialized Successfully!")

        # Sync existing local cache to database
        asyncio.create_task(sync_all_to_db())
        return True
    except Exception as e:
        print(f" [-] Failed to initialize PostgreSQL tables: {e}")
        _db_connected = False
        return False

# ==========================================
# Review & Vouch Management
# ==========================================

async def add_review_db(user_id: int, user_name: str, rating: int, comment: str, product: str = "Discord Server Boosts") -> dict:
    rating = max(1, min(5, int(rating)))
    created_at = time.time()
    pool = await get_pg_pool()

    if pool and _db_connected:
        try:
            async with pool.acquire() as conn:
                row_id = await conn.fetchval(
                    """
                    INSERT INTO customer_reviews (user_id, user_name, rating, comment, product, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id;
                    """,
                    user_id, user_name, rating, comment, product, created_at
                )
                return {
                    "id": row_id,
                    "user_id": user_id,
                    "user_name": user_name,
                    "rating": rating,
                    "comment": comment,
                    "product": product,
                    "created_at": created_at
                }
        except Exception:
            pass

    # Local fallback
    os.makedirs("data", exist_ok=True)
    reviews_file = "data/reviews.json"
    reviews = []
    if os.path.exists(reviews_file):
        try:
            with open(reviews_file, "r", encoding="utf-8") as f:
                reviews = json.load(f)
        except Exception:
            reviews = []

    rev_obj = {
        "id": len(reviews) + 1,
        "user_id": user_id,
        "user_name": user_name,
        "rating": rating,
        "comment": comment,
        "product": product,
        "created_at": created_at
    }
    reviews.append(rev_obj)
    with open(reviews_file, "w", encoding="utf-8") as f:
        json.dump(reviews, f, indent=2)
    return rev_obj

async def get_reviews_stats_db() -> Dict[str, Any]:
    pool = await get_pg_pool()
    if pool and _db_connected:
        try:
            async with pool.acquire() as conn:
                total = await conn.fetchval("SELECT COUNT(*) FROM customer_reviews;") or 0
                avg_val = await conn.fetchval("SELECT AVG(rating) FROM customer_reviews;") or 5.0
                return {
                    "total_reviews": int(total),
                    "average_rating": round(float(avg_val), 1) if total > 0 else 5.0
                }
        except Exception:
            pass

    reviews_file = "data/reviews.json"
    if os.path.exists(reviews_file):
        try:
            with open(reviews_file, "r", encoding="utf-8") as f:
                reviews = json.load(f)
            if reviews:
                avg = sum(r.get("rating", 5) for r in reviews) / len(reviews)
                return {"total_reviews": len(reviews), "average_rating": round(avg, 1)}
        except Exception:
            pass
    return {"total_reviews": 0, "average_rating": 5.0}

async def get_recent_reviews_db(limit: int = 5) -> List[Dict[str, Any]]:
    pool = await get_pg_pool()
    if pool and _db_connected:
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, user_id, user_name, rating, comment, product, created_at
                    FROM customer_reviews
                    ORDER BY id DESC
                    LIMIT $1;
                    """,
                    limit
                )
                if rows:
                    return [dict(r) for r in rows]
        except Exception:
            pass

    reviews_file = "data/reviews.json"
    if os.path.exists(reviews_file):
        try:
            with open(reviews_file, "r", encoding="utf-8") as f:
                reviews = json.load(f)
                return reviews[-limit:][::-1]
        except Exception:
            pass
    return []

# ==========================================
# Settings & Config in Database
# ==========================================

async def get_setting_db(key: str, default: Optional[str] = None) -> Optional[str]:
    pool = await get_pg_pool()
    if pool and _db_connected:
        try:
            async with pool.acquire() as conn:
                val = await conn.fetchval("SELECT value FROM bot_settings WHERE key = $1;", key)
                if val is not None:
                    return val
        except Exception:
            pass

    settings_file = "data/settings.json"
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                return json.load(f).get(key, default)
        except Exception:
            pass
    return default

async def set_setting_db(key: str, value: str):
    pool = await get_pg_pool()
    if pool and _db_connected:
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO bot_settings (key, value)
                    VALUES ($1, $2)
                    ON CONFLICT (key) DO UPDATE SET value = $2;
                    """,
                    key, value
                )
        except Exception:
            pass

    settings_file = "data/settings.json"
    settings = {}
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except Exception:
            pass
    settings[key] = value
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

# ==========================================
# Full Database Synchronization
# ==========================================

async def sync_all_to_db():
    """Syncs local cache records to PostgreSQL."""
    pool = await get_pg_pool()
    if not pool or not _db_connected:
        return

    try:
        async with pool.acquire() as conn:
            # Sync Balances
            if os.path.exists("data/balances.json"):
                with open("data/balances.json", "r", encoding="utf-8") as f:
                    bals = json.load(f)
                for uid_str, data in bals.items():
                    try:
                        uid = int(uid_str)
                        await conn.execute(
                            """
                            INSERT INTO balances (user_id, credits_1m, credits_3m, updated_at)
                            VALUES ($1, $2, $3, $4)
                            ON CONFLICT (user_id) DO UPDATE
                            SET credits_1m = $2, credits_3m = $3, updated_at = $4;
                            """,
                            uid, int(data.get("1m", 0)), int(data.get("3m", 0)), time.time()
                        )
                    except Exception:
                        pass

            # Sync Invoices
            if os.path.exists("data/invoices.json"):
                with open("data/invoices.json", "r", encoding="utf-8") as f:
                    invs = json.load(f)
                for inv_id, inv in invs.items():
                    try:
                        await conn.execute(
                            """
                            INSERT INTO invoices (
                                id, user_id, duration, boosts, crypto, amount, address,
                                target_invite, discount_code, status, tx_hash, redeem_key,
                                delivered, created_at, paid_at
                            )
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                            ON CONFLICT (id) DO UPDATE SET
                                status = $10, tx_hash = $11, redeem_key = $12,
                                delivered = $13, paid_at = $15;
                            """,
                            inv_id,
                            int(inv.get("user_id", 0)),
                            str(inv.get("duration", "1m")),
                            int(inv.get("boosts", 0)),
                            str(inv.get("crypto", "ltc")),
                            float(inv.get("amount", inv.get("ltc_amount", 0.0))),
                            str(inv.get("address", "")),
                            inv.get("target_invite"),
                            inv.get("discount_code"),
                            str(inv.get("status", "pending")),
                            inv.get("tx_hash"),
                            inv.get("redeem_key"),
                            bool(inv.get("delivered", False)),
                            float(inv.get("created_at", time.time())),
                            float(inv.get("paid_at")) if inv.get("paid_at") else None
                        )
                    except Exception:
                        pass

            # Sync Keys
            if os.path.exists("data/keys/keys.json"):
                with open("data/keys/keys.json", "r", encoding="utf-8") as f:
                    keys = json.load(f)
                for k in keys:
                    try:
                        await conn.execute(
                            """
                            INSERT INTO license_keys (
                                key, duration, amount, created_by, status, redeemed_by, redeemed_at, created_at
                            )
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                            ON CONFLICT (key) DO UPDATE SET
                                status = $5, redeemed_by = $6, redeemed_at = $7;
                            """,
                            str(k.get("key")),
                            str(k.get("duration", "1m")),
                            int(k.get("amount", 2)),
                            str(k.get("created_by", "shop")),
                            str(k.get("status", "unused")),
                            k.get("redeemed_by"),
                            float(k.get("redeemed_at")) if k.get("redeemed_at") else None,
                            float(k.get("created_at", time.time()))
                        )
                    except Exception:
                        pass

            # Sync Discounts
            if os.path.exists("data/discounts.json"):
                with open("data/discounts.json", "r", encoding="utf-8") as f:
                    discs = json.load(f)
                for code, pct in discs.items():
                    try:
                        await conn.execute(
                            """
                            INSERT INTO discounts (code, percent, created_at)
                            VALUES ($1, $2, $3)
                            ON CONFLICT (code) DO UPDATE SET percent = $2;
                            """,
                            code.upper(), float(pct), time.time()
                        )
                    except Exception:
                        pass

            # Sync Tickets
            if os.path.exists("data/tickets.json"):
                with open("data/tickets.json", "r", encoding="utf-8") as f:
                    tickets = json.load(f)
                for ch_str, t in tickets.items():
                    try:
                        await conn.execute(
                            """
                            INSERT INTO tickets (
                                channel_id, guild_id, user_id, user_name, topic, topic_key,
                                status, claimed_by, created_at, closed_at, close_reason
                            )
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                            ON CONFLICT (channel_id) DO UPDATE SET
                                status = $7, claimed_by = $8, closed_at = $10, close_reason = $11;
                            """,
                            int(ch_str),
                            int(t.get("guild_id", 0)) if t.get("guild_id") else None,
                            int(t.get("user_id", 0)),
                            str(t.get("user_name", "")),
                            str(t.get("topic", "")),
                            str(t.get("topic_key", "")),
                            str(t.get("status", "open")),
                            int(t.get("claimed_by")) if t.get("claimed_by") else None,
                            float(t.get("created_at", time.time())),
                            float(t.get("closed_at")) if t.get("closed_at") else None,
                            t.get("close_reason")
                        )
                    except Exception:
                        pass
    except Exception as e:
        print(f" [~] Database sync notice: {e}")
