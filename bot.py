import os
import sys
import time
import yaml
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
from typing import Optional

import coderz
from coderz import BoostModal, getStock, getinviteCode, checkInvite, Booster, remove, create_session_folder
from keep_alive import keep_alive
from payment import (
    get_user_balance,
    add_user_balance,
    deduct_user_balance,
    archive_used_tokens,
    create_invoice,
    check_invoice_payment,
    force_complete_invoice,
    get_invoice,
    cancel_invoice,
    get_crypto_qr_url,
    get_ltc_qr_url,
    generate_boost_key,
    redeem_boost_key,
    get_wallet_live_info,
    create_discount,
    get_discount_percent,
    get_sales_stats,
    list_all_keys,
    CRYPTO_NAMES,
    DEFAULT_CRYPTO_RATES,
    USED_TOKENS_FILE,
    get_user_invoices,
    get_user_vip_tier,
    transfer_user_balance,
    get_top_buyers,
    list_active_discounts
)
from database import (
    init_database,
    add_review_db,
    get_reviews_stats_db,
    get_recent_reviews_db,
    get_setting_db,
    set_setting_db,
    is_db_connected,
    get_daily_streak_db,
    claim_daily_streak_db,
    get_all_guild_prefixes_db
)
from tickets import (
    load_tickets_db,
    save_tickets_db,
    get_user_open_ticket,
    create_or_get_ticket,
    TicketTopicLaunchView,
    TicketTopicSelect,
    TicketInsideControls,
    TicketCloseModal,
    AIZEN_COLOR,
    AIZEN_ACCENT
)

CONFIG_PATH = "config/config.yaml"

def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f)
    except Exception as e:
        print(f"Error saving config: {e}")

config = load_config()

# Support both Render Environment Variables and config.yaml
bot_token = os.environ.get("BOT_TOKEN") or config.get("discord", {}).get("bot_token", "").strip()
prefix = os.environ.get("PREFIX") or config.get("discord", {}).get("prefix", "$")

# Hardcoded Owners: Full unlimited access and admin control
HARDCODED_OWNERS = [1505515188991033409, 1521774957065928734]

env_owners = os.environ.get("OWNER_IDS", "")
if env_owners:
    owner_ids = [int(i.strip()) for i in env_owners.split(",") if i.strip().isdigit()]
else:
    owner_ids = [int(i) for i in config.get("discord", {}).get("owner_ids", []) if str(i).isdigit()]

for owner in HARDCODED_OWNERS:
    if owner not in owner_ids:
        owner_ids.append(owner)

def is_owner(user: discord.User) -> bool:
    """Checks if a user is one of the designated owners."""
    return user.id in owner_ids or user.id in HARDCODED_OWNERS

# Multi-Crypto Wallets
wallets = config.get("crypto_wallets", {})
ltc_address = os.environ.get("LTC_ADDRESS") or wallets.get("ltc", config.get("ltc", {}).get("address", "")).strip()
usdt_address = os.environ.get("USDT_ADDRESS") or wallets.get("usdt", "").strip()
btc_address = os.environ.get("BTC_ADDRESS") or wallets.get("btc", "").strip()
sol_address = os.environ.get("SOL_ADDRESS") or wallets.get("sol", "").strip()

def get_address_for_crypto(crypto: str) -> str:
    c = crypto.lower().strip()
    if c == "ltc": return ltc_address
    if c == "usdt": return usdt_address
    if c == "btc": return btc_address
    if c == "sol": return sol_address
    return ""

def get_rate_for_crypto(crypto: str, duration: str) -> float:
    c = crypto.lower().strip()
    cfg_rates = config.get(f"rates_{duration}", {})
    if c in cfg_rates:
        return float(cfg_rates[c])
    return DEFAULT_CRYPTO_RATES.get(c, {}).get(duration, 0.25)

BOT_START_TIME = time.time()

def get_uptime_str() -> str:
    seconds = int(time.time() - BOT_START_TIME)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts) if parts else "0s"

NO_PREFIX_COMMANDS = {
    "ping", "help", "shop", "shoppanel", "panel", "buy", "stock", "boost",
    "balance", "bal", "credits", "wallet", "wallets", "redeem", "ticket", "tickets",
    "uptime", "stats", "botinfo", "serverinfo", "userinfo", "whoami", "avatar", "av", "pfp",
    "clear", "purge", "vouch", "review", "reviews", "vouches", "setreviewchannel",
    "orders", "myorders", "vip", "loyalty", "transfer", "sendcredits", "top", "leaderboard", "promos", "discounts", "setlogchannel",
    "setup", "checkserver", "calc", "daily", "faq", "guide", "setprefix", "broadcast"
}

_guild_prefixes: dict = {}

def determine_prefix(bot_instance, message):
    p = _guild_prefixes.get(message.guild.id, prefix) if message.guild else prefix
    if not message.content:
        return [p]
    content = message.content.strip().lower()
    first_word = content.split()[0] if content.split() else ""
    if first_word in NO_PREFIX_COMMANDS:
        return ["", p]
    return [p]

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=determine_prefix, intents=intents, help_command=None)

# ==========================================
# Core Boosting Helper (No Limitations)
# ==========================================

async def execute_boost(invite_str: str, amount: int, months: int, user_id: int, channel: discord.abc.Messageable):
    """Executes the full boosting process with no artificial limits."""
    dur_key = f"{months}m"
    invite_code = getinviteCode(invite_str)
    guild_id = checkInvite(invite_code)

    if not guild_id:
        return await channel.send(embed=discord.Embed(
            title="⚔️ Kyōka Suigetsu — Invalid Target",
            description=f"Could not reach server with invite code: `.gg/{invite_code}`\nPlease check invite validity.",
            color=discord.Color.red()
        ))

    filename = "data/1m.txt" if months == 1 else "data/3m.txt"
    stock = getStock(filename) or []
    required_tokens = int(amount / 2)

    if required_tokens > len(stock):
        return await channel.send(embed=discord.Embed(
            title="⚔️ Stock Exhausted",
            description=f"*\"You cannot control what you do not possess.\"*\n\nNeed `{required_tokens}` tokens, but only `{len(stock)}` available in `{filename}`.",
            color=discord.Color.red()
        ))

    tokens_to_use = stock[:required_tokens]
    for token in tokens_to_use:
        remove(token, filename)

    status_msg = await channel.send(embed=discord.Embed(
        title="⚔️ Aizen Deployment — Boosting in Progress",
        description=(
            f"*\"Since when were you under the impression that you were not using Kyōka Suigetsu?\"*\n\n"
            f"◈ **Target Server**: `.gg/{invite_code}`\n"
            f"◈ **Boosts**: `{amount}`x {dur_key}\n"
            f"◈ **Tokens**: `{required_tokens}` assigned\n\n"
            f"Engaging Discord endpoints... Please wait."
        ),
        color=AIZEN_COLOR
    ))

    session_folder = create_session_folder()
    booster = Booster(session_folder)
    start_time = time.time()

    def do_boost():
        return booster.thread(invite_code, tokens_to_use, guild_id)

    status = await asyncio.to_thread(do_boost)
    elapsed = round(time.time() - start_time, 2)

    archive_used_tokens(tokens_to_use, dur_key, invite_code)

    success_count = len(status.get("success", [])) * 2 if isinstance(status, dict) else 0
    failed_count = len(status.get("failed", [])) * 2 if isinstance(status, dict) else 0

    result_embed = discord.Embed(
        title="⚔️ Mission Accomplished — The Throne Awaits",
        description=f"*\"No one stands on the heavens from the beginning.\"*\n\nCompleted deployment to **.gg/{invite_code}** in `{elapsed}s`.",
        color=AIZEN_ACCENT if success_count > 0 else discord.Color.red()
    )
    result_embed.add_field(name="◈ Boosts Applied", value=f"`{success_count}` successful", inline=True)
    result_embed.add_field(name="◈ Boosts Failed", value=f"`{failed_count}` failed", inline=True)
    result_embed.add_field(name="◈ Archived Accounts", value=f"`{required_tokens}` tokens stored", inline=True)
    result_embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")

    await status_msg.edit(embed=result_embed)

    try:
        prompt_view = InTicketBoostPromptView()
        await channel.send(
            f"<@{user_id}> 🎉 **Server boosted successfully!** Leave a quick vouch or apply more boosts below:",
            view=prompt_view
        )
    except Exception:
        pass

# ==========================================
# Order Logging & Transfer Helpers
# ==========================================

async def log_completed_order(guild: Optional[discord.Guild], inv: dict):
    """Posts a public verified receipt embed to the configured order log channel."""
    if not guild or not inv:
        return
    channel_id = await get_setting_db(f"guild_{guild.id}_order_log_channel")
    if not channel_id:
        channel_id = await get_setting_db("order_log_channel_id")

    log_channel = None
    if channel_id:
        try:
            log_channel = guild.get_channel(int(channel_id))
        except Exception:
            log_channel = None

    if not log_channel:
        for ch in guild.text_channels:
            if any(w in ch.name.lower() for w in ["order-log", "order-logs", "purchases", "receipts", "sales"]):
                log_channel = ch
                break

    if not log_channel:
        return

    c_name = inv.get("crypto", "LTC").upper()
    total_amt = inv.get("amount", inv.get("ltc_amount", 0.0))
    user_id = inv.get("user_id")
    order_id = inv.get("id")
    boosts = inv.get("boosts", 0)
    duration = str(inv.get("duration", "1m")).upper()

    embed = discord.Embed(
        title="🛒 Verified Purchase & Delivery Log",
        description=(
            f"*\"No one stands on the heavens from the beginning.\"*\n\n"
            f"◈ **Order ID**: `{order_id}`\n"
            f"◈ **Customer**: <@{user_id}>\n"
            f"◈ **Product**: `{boosts}x {duration}` Server Boosts\n"
            f"◈ **Amount Paid**: `{total_amt} {c_name}`\n"
            f"◈ **Status**: `PAID & DELIVERED` ✅\n"
            f"◈ **Receipt Key**: `{inv.get('redeem_key', 'Generated')}`\n"
        ),
        color=AIZEN_ACCENT
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Shop Engine")
    embed.timestamp = discord.utils.utcnow()

    try:
        await log_channel.send(embed=embed)
    except Exception:
        pass

class TransferCreditsModal(Modal, title="🎁 Transfer Boost Credits"):
    recipient_input = TextInput(
        label="Recipient User ID",
        placeholder="e.g. 1505515188991033409",
        required=True,
        max_length=25
    )
    duration_input = TextInput(
        label="Duration (1m or 3m)",
        placeholder="1m or 3m",
        required=True,
        max_length=2
    )
    amount_input = TextInput(
        label="Amount of Boosts",
        placeholder="Even number (e.g. 2, 4, 14)",
        required=True,
        max_length=4
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            target_id = int(self.recipient_input.value.strip().replace("<@", "").replace(">", "").replace("!", ""))
            amount = int(self.amount_input.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ Invalid user ID or amount number.", ephemeral=True)

        duration = self.duration_input.value.strip().lower()
        success, msg = transfer_user_balance(interaction.user.id, target_id, duration, amount)
        color = AIZEN_ACCENT if success else discord.Color.red()
        embed = discord.Embed(title="🎁 Boost Credit Transfer", description=msg, color=color)
        embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Shop Engine")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ==========================================
# Payment View with Interactive Buttons
# ==========================================

class PaymentView(View):
    def __init__(self, invoice_id: str, crypto: str, addy: str, expected_amt: float):
        super().__init__(timeout=3600)
        self.invoice_id = invoice_id
        self.crypto = crypto
        self.addy = addy
        self.expected_amt = expected_amt

    @discord.ui.button(label="🔄 Check Payment", style=discord.ButtonStyle.success, custom_id="btn_check_pay")
    async def check_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        paid, msg, inv = check_invoice_payment(self.invoice_id)
        if paid and inv:
            if inv.get("delivered"):
                return await interaction.followup.send("✅ This order has already been verified and delivered.", ephemeral=True)

            # Mark delivered to prevent any duplicate execution
            from payment import load_json, save_json, INVOICES_FILE
            all_invs = load_json(INVOICES_FILE, {})
            if self.invoice_id in all_invs:
                all_invs[self.invoice_id]["delivered"] = True
                save_json(INVOICES_FILE, all_invs)

            self.stop()
            if interaction.message and interaction.message.embeds:
                embed = interaction.message.embeds[0]
                embed.title = "⚔️ Payment Confirmed & Delivered!"
                embed.color = AIZEN_ACCENT
                embed.set_field_at(3, name="Status", value="`PAID & DELIVERED`", inline=False)
                await interaction.message.edit(embed=embed, view=None)

            code = inv.get("redeem_key", "Generated")
            c_name = inv.get("crypto", "LTC").upper()
            total_amt = inv.get("amount", inv.get("ltc_amount"))
            user_id = inv["user_id"]

            celebrate_embed = discord.Embed(
                title="🎉 Payment Confirmed & Delivered!",
                description=(
                    f"*\"No one stands on the heavens from the beginning.\"*\n\n"
                    f"◈ **Received**: `{total_amt} {c_name}`\n"
                    f"◈ **Credits Added**: `{inv['boosts']}x {inv['duration']}`\n"
                    f"◈ **Receipt Key**: `{code}`\n\n"
                    f"*(Credits are deposited to your account. Use button below to boost your server!)*"
                ),
                color=AIZEN_ACCENT
            )
            celebrate_embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")

            if inv.get("target_invite"):
                months_num = int(inv["duration"].replace("m", ""))
                deduct_user_balance(user_id, inv["duration"], inv["boosts"])
                await interaction.channel.send(content=f"<@{user_id}>", embed=celebrate_embed)
                await execute_boost(inv["target_invite"], inv["boosts"], months_num, user_id, interaction.channel)
            else:
                boost_view = InTicketBoostPromptView()
                await interaction.channel.send(content=f"<@{user_id}>", embed=celebrate_embed, view=boost_view)

            if interaction.guild:
                asyncio.create_task(log_completed_order(interaction.guild, inv))

            await interaction.followup.send(f"🎉 **Payment Verified!** Added `{inv['boosts']}`x `{inv['duration']}` credits.", ephemeral=True)
        else:
            await interaction.followup.send(f"⏳ {msg}\n*Please allow network confirmations to register on the blockchain.*", ephemeral=True)

    @discord.ui.button(label="📋 Copy Address", style=discord.ButtonStyle.secondary, custom_id="btn_copy_addy")
    async def copy_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(f"```{self.addy}```", ephemeral=True)

    @discord.ui.button(label="❌ Cancel Order", style=discord.ButtonStyle.danger, custom_id="btn_cancel_order")
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        inv = get_invoice(self.invoice_id)
        if not inv or inv.get("status") != "pending":
            return await interaction.response.send_message("❌ Order cannot be cancelled.", ephemeral=True)
        if interaction.user.id != inv.get("user_id") and not is_owner(interaction.user):
            return await interaction.response.send_message("❌ Only the buyer or bot owner can cancel this order.", ephemeral=True)

        cancel_invoice(self.invoice_id, interaction.user.id, is_owner(interaction.user))
        self.stop()
        if interaction.message and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            embed.title = "❌ Payment Order Cancelled"
            embed.color = discord.Color.red()
            embed.set_field_at(3, name="Status", value="`CANCELLED`", inline=False)
            await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("✅ Order has been cancelled.", ephemeral=True)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.secondary, custom_id="btn_invoice_close")
    async def close_button(self, interaction: discord.Interaction, button: Button):
        db = load_tickets_db()
        t_data = db.get(str(interaction.channel.id), {"user_name": interaction.user.name, "user_id": interaction.user.id, "topic": "Order"})
        await interaction.response.send_modal(TicketCloseModal(t_data))

class CustomerReviewModal(Modal, title="⭐ Submit Customer Review & Vouch"):
    rating_input = TextInput(
        label="Rating (1 to 5 Stars)",
        placeholder="5",
        default="5",
        required=True,
        max_length=1
    )
    product_input = TextInput(
        label="Product / Service Purchased",
        placeholder="e.g. 14x Discord Server Boosts (1 Month)",
        default="Discord Server Boosts",
        required=True,
        max_length=100
    )
    comment_input = TextInput(
        label="Your Review / Feedback",
        style=discord.TextStyle.paragraph,
        placeholder="Instant delivery! Boosted my server quickly, great service...",
        required=True,
        max_length=600
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            rating = int(self.rating_input.value.strip())
            rating = max(1, min(5, rating))
        except ValueError:
            rating = 5

        comment = self.comment_input.value.strip()
        product = self.product_input.value.strip() or "Discord Server Boosts"

        rev = await add_review_db(
            user_id=interaction.user.id,
            user_name=interaction.user.name,
            rating=rating,
            comment=comment,
            product=product
        )
        stats = await get_reviews_stats_db()

        # Build Review / Vouch Card
        stars = "⭐" * rating
        vouch_embed = discord.Embed(
            title="⭐ Verified Customer Review & Vouch",
            description=(
                f"*\"No one stands on the heavens from the beginning.\"*\n\n"
                f"◈ **Rating**: {stars} (`{rating}/5`)\n"
                f"◈ **Customer**: {interaction.user.mention} (`{interaction.user.name}`)\n"
                f"◈ **Product**: `{product}`\n"
                f"◈ **Order Status**: `✅ Verified Customer`\n\n"
                f"**Feedback**:\n```{comment}```"
            ),
            color=AIZEN_ACCENT
        )
        vouch_embed.set_thumbnail(url=interaction.user.display_avatar.url)
        vouch_embed.set_footer(
            text=f"Aizen Reviews • Total Vouches: {stats['total_reviews']} • Avg: {stats['average_rating']}★"
        )
        vouch_embed.timestamp = discord.utils.utcnow()

        # Find review channel
        channel_id_setting = await get_setting_db(f"guild_{interaction.guild.id}_review_channel") if interaction.guild else None
        if not channel_id_setting:
            channel_id_setting = await get_setting_db("review_channel_id")

        review_channel = None
        if channel_id_setting and interaction.guild:
            try:
                review_channel = interaction.guild.get_channel(int(channel_id_setting))
            except Exception:
                review_channel = None

        if not review_channel and interaction.guild:
            for ch in interaction.guild.text_channels:
                if any(w in ch.name.lower() for w in ["vouch", "review", "feedback", "vouches", "reviews"]):
                    review_channel = ch
                    break

        posted_msg = ""
        if review_channel:
            try:
                await review_channel.send(embed=vouch_embed)
                posted_msg = f" and published in {review_channel.mention}!"
            except Exception:
                pass

        await interaction.response.send_message(
            f"✨ **Thank you for your feedback, {interaction.user.mention}!** Your review has been saved{posted_msg}",
            ephemeral=True
        )

class InTicketBoostPromptView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🚀 Apply Boosts to Server", style=discord.ButtonStyle.success, custom_id="btn_apply_boost_prompt")
    async def btn_apply(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(InTicketApplyBoostModal())

    @discord.ui.button(label="⭐ Leave Review / Vouch", style=discord.ButtonStyle.primary, custom_id="btn_leave_review_prompt")
    async def btn_review(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CustomerReviewModal())

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="btn_close_prompt")
    async def btn_close(self, interaction: discord.Interaction, button: Button):
        db = load_tickets_db()
        t_data = db.get(str(interaction.channel.id), {"user_name": interaction.user.name, "user_id": interaction.user.id, "topic": "Order"})
        await interaction.response.send_modal(TicketCloseModal(t_data))

class InTicketApplyBoostModal(Modal, title="🚀 Apply Server Boosts"):
    invite_input = TextInput(
        label="Discord Server Invite Link",
        placeholder="e.g. discord.gg/yourserver or yourserver",
        required=True,
        max_length=60
    )
    amount_input = TextInput(
        label="Amount of Boosts",
        placeholder="Even number (e.g. 2, 4, 14)",
        required=True,
        max_length=4
    )
    duration_input = TextInput(
        label="Duration (1m or 3m)",
        placeholder="1m or 3m",
        required=True,
        max_length=2
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount_input.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ Amount must be a valid number.", ephemeral=True)

        if amount <= 0 or amount % 2 != 0:
            return await interaction.response.send_message("❌ Amount must be an even positive number.", ephemeral=True)

        dur = self.duration_input.value.strip().lower()
        if dur not in ["1m", "3m"]:
            return await interaction.response.send_message("❌ Duration must be `1m` or `3m`.", ephemeral=True)

        months = int(dur.replace("m", ""))
        invite = self.invite_input.value.strip()

        if not is_owner(interaction.user):
            bal = get_user_balance(interaction.user.id)
            current_credits = bal.get(dur, 0)
            if current_credits < amount:
                return await interaction.response.send_message(
                    f"❌ Insufficient `{dur}` credits! You have `{current_credits}`, but need `{amount}`.\nPurchase more credits above!",
                    ephemeral=True
                )
            deduct_user_balance(interaction.user.id, dur, amount)

        await interaction.response.send_message(f"🚀 Deploying `{amount}`x `{dur}` boosts to **{invite}**...", ephemeral=True)
        await execute_boost(invite, amount, months, interaction.user.id, interaction.channel)

# ==========================================
# Background Payment Poller
# ==========================================

async def auto_poll_invoice(invoice_id: str, message: discord.Message, channel: discord.abc.Messageable, user_id: int):
    """Periodically checks blockchain in background for 30 minutes."""
    for _ in range(60):
        await asyncio.sleep(30)
        try:
            inv_data = get_invoice(invoice_id)
            if not inv_data or inv_data.get("status") not in ["pending"]:
                break

            paid, msg, inv = check_invoice_payment(invoice_id)
            if paid and inv:
                if inv.get("delivered"):
                    break

                # Mark delivered
                from payment import load_json, save_json, INVOICES_FILE
                all_invs = load_json(INVOICES_FILE, {})
                if invoice_id in all_invs:
                    all_invs[invoice_id]["delivered"] = True
                    save_json(INVOICES_FILE, all_invs)

                if message and message.embeds:
                    embed = message.embeds[0]
                    embed.title = "⚔️ Payment Confirmed & Delivered!"
                    embed.color = AIZEN_ACCENT
                    embed.set_field_at(3, name="Status", value="`PAID & DELIVERED`", inline=False)
                    await message.edit(embed=embed, view=None)

                code = inv.get("redeem_key", "Generated")
                c_name = inv.get("crypto", "LTC").upper()
                total_amt = inv.get("amount", inv.get("ltc_amount"))

                celebrate_embed = discord.Embed(
                    title="🎉 Payment Confirmed & Delivered!",
                    description=(
                        f"*\"No one stands on the heavens from the beginning.\"*\n\n"
                        f"◈ **Received**: `{total_amt} {c_name}`\n"
                        f"◈ **Credits Added**: `{inv['boosts']}x {inv['duration']}`\n"
                        f"◈ **Receipt Key**: `{code}`\n\n"
                        f"*(Credits are deposited to your account. Use button below to boost your server!)*"
                    ),
                    color=AIZEN_ACCENT
                )
                celebrate_embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")

                if inv.get("target_invite"):
                    months_num = int(inv["duration"].replace("m", ""))
                    deduct_user_balance(inv["user_id"], inv["duration"], inv["boosts"])
                    await channel.send(content=f"<@{user_id}>", embed=celebrate_embed)
                    await execute_boost(inv["target_invite"], inv["boosts"], months_num, user_id, channel)
                else:
                    boost_view = InTicketBoostPromptView()
                    await channel.send(content=f"<@{user_id}>", embed=celebrate_embed, view=boost_view)

                if hasattr(channel, "guild") and channel.guild:
                    asyncio.create_task(log_completed_order(channel.guild, inv))
                break
        except Exception:
            pass

# ==========================================
# Multi-Crypto Purchase Flow
# ==========================================

async def generate_crypto_invoice(
    interaction: discord.Interaction,
    duration: str,
    amount: int,
    crypto: str,
    invite: Optional[str] = None,
    discount_code: Optional[str] = None
):
    """Builds and sends the modular multi-crypto payment invoice."""
    dur_clean = duration.lower().strip()
    c_clean = crypto.lower().strip()

    target_address = get_address_for_crypto(c_clean)
    if not target_address or "PASTE" in target_address:
        return await interaction.response.send_message(
            f"❌ **{CRYPTO_NAMES.get(c_clean, c_clean.upper())}** is not configured yet. The owner can link it via `{prefix}setaddress {c_clean} <address>`.",
            ephemeral=True
        )

    rate = get_rate_for_crypto(c_clean, dur_clean)
    total_crypto = round(rate * amount, 6)

    discount_percent = get_discount_percent(discount_code) if discount_code else 0.0
    if discount_percent > 0:
        savings = round(total_crypto * (discount_percent / 100.0), 6)
        total_crypto = round(total_crypto - savings, 6)

    invoice = create_invoice(
        user_id=interaction.user.id,
        duration=dur_clean,
        boosts=amount,
        amount=total_crypto,
        address=target_address,
        crypto=c_clean,
        target_invite=invite,
        discount_code=discount_code
    )

    c_name = CRYPTO_NAMES.get(c_clean, c_clean.upper())
    embed = discord.Embed(
        title=f"⚔️ Sōsuke Aizen — {c_name} Invoice",
        description=(
            f"*\"Admiration is the emotion furthest from understanding.\"*\n\n"
            f"Send the exact amount below to receive your boost credits.\n"
            f"Blockchain confirmations are monitored automatically."
        ),
        color=AIZEN_COLOR
    )
    embed.add_field(name="📦 Order ID", value=f"`{invoice['id']}`", inline=True)
    embed.add_field(name="💎 Product", value=f"`{amount}x {dur_clean}` Boosts", inline=True)
    embed.add_field(name="💰 Amount to Send", value=f"**`{total_crypto} {c_clean.upper()}`**" + (f" *({int(discount_percent)}% off applied)*" if discount_percent else ""), inline=False)
    embed.add_field(name=f"📬 Send To {c_name} Address", value=f"```{target_address}```", inline=False)

    if invite:
        embed.add_field(name="⚡ Instant Auto-Delivery Target", value=f"`.gg/{getinviteCode(invite)}` (Will boost instantly upon payment)", inline=False)

    embed.add_field(name="⏳ Status", value="`Awaiting Payment (Expires in 60 mins)`", inline=False)
    embed.set_thumbnail(url=get_crypto_qr_url(c_clean, target_address, total_crypto))
    embed.set_footer(text="Scan QR code with your mobile crypto wallet | Click 'Check Payment' once sent")

    view = PaymentView(invoice['id'], c_clean, target_address, total_crypto)

    if interaction.response.is_done():
        msg = await interaction.followup.send(embed=embed, view=view)
    else:
        msg = await interaction.response.send_message(embed=embed, view=view)

    # Start background poller for automatic on-chain payment detection
    asyncio.create_task(auto_poll_invoice(invoice['id'], msg, interaction.channel, interaction.user.id))

class CryptoSelect(Select):
    def __init__(self, duration: str, amount: int, invite: Optional[str] = None, discount: Optional[str] = None):
        self.duration = duration
        self.amount = amount
        self.invite = invite
        self.discount = discount
        r_ltc = round(get_rate_for_crypto("ltc", duration) * amount, 4)
        r_usdt = round(get_rate_for_crypto("usdt", duration) * amount, 2)
        r_btc = round(get_rate_for_crypto("btc", duration) * amount, 6)
        r_sol = round(get_rate_for_crypto("sol", duration) * amount, 4)

        options = [
            discord.SelectOption(label=f"Litecoin (LTC) ~ {r_ltc} LTC", value="ltc", emoji="🪙", description="Lowest network fees • Instant auto-confirm"),
            discord.SelectOption(label=f"Tether USDT ~ ${r_usdt} USDT", value="usdt", emoji="💵", description="Stablecoin (Zero volatility)"),
            discord.SelectOption(label=f"Bitcoin (BTC) ~ {r_btc} BTC", value="btc", emoji="₿", description="The standard cryptocurrency"),
            discord.SelectOption(label=f"Solana (SOL) ~ {r_sol} SOL", value="sol", emoji="🟣", description="High-speed Solana network")
        ]
        super().__init__(placeholder="💎 Choose Your Payment Cryptocurrency...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        crypto = self.values[0]
        await generate_crypto_invoice(interaction, self.duration, self.amount, crypto, self.invite, self.discount)

class CryptoSelectionView(View):
    def __init__(self, duration: str, amount: int, invite: Optional[str] = None, discount: Optional[str] = None):
        super().__init__(timeout=300)
        self.add_item(CryptoSelect(duration, amount, invite, discount))

class InTicketCustomOrderModal(Modal, title="✏️ Custom Boost Order"):
    amount_input = TextInput(
        label="Amount of Boosts",
        placeholder="Even number (e.g. 2, 4, 14, 30)",
        required=True,
        max_length=4
    )
    duration_input = TextInput(
        label="Duration (1m or 3m)",
        placeholder="1m or 3m",
        required=True,
        max_length=2
    )
    invite_input = TextInput(
        label="Server Invite (Optional for Auto-Boost)",
        placeholder="e.g. discord.gg/yourserver (boosts instantly upon payment)",
        required=False,
        max_length=60
    )
    discount_input = TextInput(
        label="Discount / Promo Code (Optional)",
        placeholder="e.g. PROMO10",
        required=False,
        max_length=20
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount_input.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ Amount must be a valid number.", ephemeral=True)

        if amount <= 0 or amount % 2 != 0:
            return await interaction.response.send_message("❌ Amount must be an even positive number (2 boosts per token).", ephemeral=True)

        duration = self.duration_input.value.strip().lower()
        if duration not in ["1m", "3m"]:
            return await interaction.response.send_message("❌ Duration must be `1m` or `3m`.", ephemeral=True)

        invite = self.invite_input.value.strip() or None
        discount = self.discount_input.value.strip().upper() or None

        embed = discord.Embed(
            title=f"⚔️ Sōsuke Aizen — Select Payment Currency",
            description=(
                f"*\"No one stands on the heavens from the beginning.\"*\n\n"
                f"◈ **Order**: `{amount}x {duration.upper()}` Boosts\n"
                f"◈ **Target**: `{invite or 'Account Credits (Apply anytime)'}`\n"
                + (f"◈ **Promo Code**: `{discount}`\n" if discount else "")
                + f"\nSelect your payment cryptocurrency below to generate your invoice:"
            ),
            color=AIZEN_COLOR
        )
        view = CryptoSelectionView(duration, amount, invite, discount)
        await interaction.response.send_message(embed=embed, view=view)

class InTicketPackageSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="2 Boosts (1 Month)", value="2_1m", emoji="⚡", description="Quick package • 1 Token"),
            discord.SelectOption(label="4 Boosts (1 Month)", value="4_1m", emoji="⚡", description="Level 1 Discord Server • 2 Tokens"),
            discord.SelectOption(label="14 Boosts (1 Month)", value="14_1m", emoji="⚡", description="Level 3 Discord Server • 7 Tokens"),
            discord.SelectOption(label="30 Boosts (1 Month)", value="30_1m", emoji="⚡", description="VIP Discord Package • 15 Tokens"),
            discord.SelectOption(label="2 Boosts (3 Months)", value="2_3m", emoji="🔥", description="3-Month Package • 1 Token"),
            discord.SelectOption(label="4 Boosts (3 Months)", value="4_3m", emoji="🔥", description="3-Month Level 1 • 2 Tokens"),
            discord.SelectOption(label="14 Boosts (3 Months)", value="14_3m", emoji="🔥", description="3-Month Level 3 • 7 Tokens"),
            discord.SelectOption(label="30 Boosts (3 Months)", value="30_3m", emoji="🔥", description="3-Month VIP Package • 15 Tokens"),
        ]
        super().__init__(placeholder="💎 Choose a Boost Package to Purchase...", min_values=1, max_values=1, options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        amt_str, dur = val.split("_")
        amount = int(amt_str)

        embed = discord.Embed(
            title=f"⚔️ Sōsuke Aizen — Select Payment Currency",
            description=(
                f"*\"No one stands on the heavens from the beginning.\"*\n\n"
                f"◈ **Selected Product**: `{amount}x {dur.upper()}` Boosts\n\n"
                f"Select your preferred cryptocurrency below to generate your invoice & QR code:"
            ),
            color=AIZEN_COLOR
        )
        view = CryptoSelectionView(dur, amount)
        await interaction.response.send_message(embed=embed, view=view)

class InTicketOrderTerminalView(View):
    def __init__(self, ticket_channel: discord.TextChannel, user: discord.Member):
        super().__init__(timeout=None)
        self.ticket_channel = ticket_channel
        self.user = user
        self.add_item(InTicketPackageSelect())

    @discord.ui.button(label="✏️ Custom Order & Link", style=discord.ButtonStyle.primary, custom_id="btn_tkt_custom_order", row=1)
    async def btn_custom(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(InTicketCustomOrderModal())

    @discord.ui.button(label="🚀 Boost Server Now", style=discord.ButtonStyle.success, custom_id="btn_tkt_boost_now", row=1)
    async def btn_boost(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(InTicketApplyBoostModal())

    @discord.ui.button(label="💳 My Balance", style=discord.ButtonStyle.secondary, custom_id="btn_tkt_bal", row=2)
    async def btn_bal(self, interaction: discord.Interaction, button: Button):
        bal = get_user_balance(interaction.user.id)
        embed = discord.Embed(
            title=f"💳 Boost Credits — {interaction.user.name}",
            description=f"◈ **1-Month Boosts**: `{bal['1m']}` credits\n◈ **3-Month Boosts**: `{bal['3m']}` credits",
            color=AIZEN_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="btn_tkt_close_term", row=2)
    async def btn_close(self, interaction: discord.Interaction, button: Button):
        db = load_tickets_db()
        t_data = db.get(str(interaction.channel.id), {"user_name": interaction.user.name, "user_id": interaction.user.id, "topic": "Order"})
        await interaction.response.send_modal(TicketCloseModal(t_data))

async def send_order_terminal(ticket_channel: discord.TextChannel, user: discord.Member, preload_data: dict = None):
    """Initializes the Auto-Buy order terminal inside a private ticket channel."""
    if preload_data:
        duration = preload_data.get("duration", "1m")
        amount = preload_data.get("amount", 2)
        invite = preload_data.get("invite")
        discount = preload_data.get("discount")

        embed = discord.Embed(
            title="⚔️ SŌSUKE AIZEN | AUTO-BUY ORDER TERMINAL",
            description=(
                f"*\"No one stands on the heavens from the beginning.\"*\n\n"
                f"Welcome {user.mention} to your private checkout chamber.\n\n"
                f"◈ **Product**: `{amount}x {duration.upper()}` Boosts\n"
                f"◈ **Target**: `{invite or 'Account Credits (Boost anytime)'}`\n"
                + (f"◈ **Discount Code**: `{discount}`\n" if discount else "")
                + f"\n**Select your preferred cryptocurrency below to generate your invoice:**"
            ),
            color=AIZEN_COLOR
        )
        embed.set_footer(text="Instant Auto-Delivery • Blockchain Confirmed")
        view = CryptoSelectionView(duration, amount, invite, discount)
        await ticket_channel.send(content=f"{user.mention}", embed=embed, view=view)
    else:
        t1m = len(getStock("data/1m.txt") or [])
        t3m = len(getStock("data/3m.txt") or [])
        embed = discord.Embed(
            title="⚔️ SŌSUKE AIZEN | AUTO-BUY ORDER TERMINAL",
            description=(
                f"*\"No one stands on the heavens from the beginning. Neither you, nor I, not even God.\"*\n\n"
                f"Welcome {user.mention} to your private automated order terminal.\n"
                f"All payments, blockchain confirmations, credit allocation, and server boosts are **100% automated** in this ticket.\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"**📦 Live Stock Status**:\n"
                f"◈ 1-Month Boosts Available: `{t1m * 2}` boosts (`{t1m}` tokens)\n"
                f"◈ 3-Month Boosts Available: `{t3m * 2}` boosts (`{t3m}` tokens)\n\n"
                f"**🚀 Supported Cryptocurrencies**:\n"
                f"`🪙 Litecoin (LTC)` • `💵 Tether USDT` • `₿ Bitcoin (BTC)` • `🟣 Solana (SOL)`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"**Instructions**:\n"
                f"1. Choose a popular package from the dropdown below,\n"
                f"2. Or click **\"✏️ Custom Order & Link\"** to enter a custom quantity or server invite.\n"
                f"3. Your invoice will be generated directly in this channel."
            ),
            color=AIZEN_COLOR
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine | 100% Automated")
        view = InTicketOrderTerminalView(ticket_channel, user)
        await ticket_channel.send(content=f"{user.mention}", embed=embed, view=view)

class RedeemKeyModal(Modal, title="🔑 Redeem Boost Key"):
    code_input = TextInput(
        label="Enter License / Key Code",
        placeholder="e.g. BOOST-1M-2X-ABCD-1234",
        required=True,
        max_length=60
    )

    async def on_submit(self, interaction: discord.Interaction):
        key_code = self.code_input.value.strip().upper()
        success, msg, item = redeem_boost_key(key_code, interaction.user.id)
        color = AIZEN_ACCENT if success else discord.Color.red()
        embed = discord.Embed(title="🔑 Key Redemption", description=msg, color=color)
        if success and item:
            bal = get_user_balance(interaction.user.id)
            embed.add_field(name="Updated Balance", value=f"• 1-Month: `{bal['1m']}` boosts\n• 3-Month: `{bal['3m']}` boosts", inline=False)
            embed.set_footer(text=f"Use $boost <invite> {item['amount']} {item['duration'].replace('m', '')} to apply your boosts!")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ==========================================
# All-in-One Persistent Shop Panel View
# ==========================================

class ShopPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🛒 Buy Boosts (Instant Checkout Ticket)", style=discord.ButtonStyle.primary, custom_id="shop_btn_buy_ticket", row=0)
    async def btn_buy_ticket(self, interaction: discord.Interaction, button: Button):
        ticket_channel, is_new, ticket_data = await create_or_get_ticket(
            guild=interaction.guild,
            user=interaction.user,
            topic_key="order",
            owners_list=HARDCODED_OWNERS,
            bot_ref=bot
        )
        if is_new:
            await send_order_terminal(ticket_channel, interaction.user)
            await interaction.response.send_message(
                f"⚔️ **Private Auto-Buy Ticket Created:** {ticket_channel.mention}\n*Please proceed to your ticket to configure your order and pay.*",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚔️ You already have an active checkout ticket: {ticket_channel.mention}! Please proceed there to manage your purchases.",
                ephemeral=True
            )

    @discord.ui.button(label="🎫 Open Support Ticket", style=discord.ButtonStyle.success, custom_id="shop_btn_ticket", row=0)
    async def btn_ticket(self, interaction: discord.Interaction, button: Button):
        view = TicketTopicLaunchView(bot, HARDCODED_OWNERS)
        await interaction.response.send_message(
            "⚔️ **Select a ticket topic below to open your consultation channel:**",
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="⭐ Reviews & Vouches", style=discord.ButtonStyle.secondary, custom_id="shop_btn_reviews", row=0)
    async def btn_reviews(self, interaction: discord.Interaction, button: Button):
        stats = await get_reviews_stats_db()
        recent = await get_recent_reviews_db(limit=3)

        desc = (
            f"*\"Admiration is the emotion furthest from understanding.\"*\n\n"
            f"◈ **Average Rating**: `⭐ {stats['average_rating']} / 5.0`\n"
            f"◈ **Total Verified Vouches**: `{stats['total_reviews']}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Recent Customer Reviews**:\n"
        )
        if recent:
            for r in recent:
                stars = "⭐" * r.get("rating", 5)
                desc += f"• **{r.get('user_name', 'Customer')}** ({stars}):\n  *{r.get('comment', 'Great service!')}*\n\n"
        else:
            desc += "*No reviews yet. Be the first to leave a review! Use `$vouch`.*\n"

        embed = discord.Embed(
            title="⭐ Customer Satisfaction & Verified Reviews",
            description=desc,
            color=AIZEN_COLOR
        )
        embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine | 100% Verified Delivery")
        view = View(timeout=120)
        v_btn = Button(label="✍️ Write a Review / Vouch", style=discord.ButtonStyle.success)
        async def _open_rev(inter: discord.Interaction):
            await inter.response.send_modal(CustomerReviewModal())
        v_btn.callback = _open_rev
        view.add_item(v_btn)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="💳 My Balance", style=discord.ButtonStyle.secondary, custom_id="shop_btn_bal", row=1)
    async def btn_bal(self, interaction: discord.Interaction, button: Button):
        bal = get_user_balance(interaction.user.id)
        embed = discord.Embed(
            title=f"💳 Balance — {interaction.user.name}",
            description=f"◈ **1-Month Boosts**: `{bal['1m']}` credits\n◈ **3-Month Boosts**: `{bal['3m']}` credits",
            color=AIZEN_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="📦 Stock & Rates", style=discord.ButtonStyle.secondary, custom_id="shop_btn_stock", row=1)
    async def btn_stock(self, interaction: discord.Interaction, button: Button):
        t1m = len(getStock("data/1m.txt") or [])
        t3m = len(getStock("data/3m.txt") or [])
        embed = discord.Embed(
            title="📦 Real-Time Stock Availability & Rates",
            description=(
                f"◈ **1-Month Tokens**: `{t1m}` tokens (`{t1m * 2}` boosts)\n"
                f"◈ **3-Month Tokens**: `{t3m}` tokens (`{t3m * 2}` boosts)\n\n"
                f"**Current Rates (Per 2 Boosts / 1 Token)**:\n"
                f"• 🪙 **LTC**: `{get_rate_for_crypto('ltc', '1m') * 2} LTC` (1m) | `{get_rate_for_crypto('ltc', '3m') * 2} LTC` (3m)\n"
                f"• 💵 **USDT**: `${get_rate_for_crypto('usdt', '1m') * 2} USDT` (1m) | `${get_rate_for_crypto('usdt', '3m') * 2} USDT` (3m)\n"
                f"• ₿ **BTC**: `{get_rate_for_crypto('btc', '1m') * 2} BTC` (1m) | `{get_rate_for_crypto('btc', '3m') * 2} BTC` (3m)\n"
                f"• 🟣 **SOL**: `{get_rate_for_crypto('sol', '1m') * 2} SOL` (1m) | `{get_rate_for_crypto('sol', '3m') * 2} SOL` (3m)"
            ),
            color=AIZEN_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔑 Redeem Key", style=discord.ButtonStyle.secondary, custom_id="shop_btn_redeem", row=1)
    async def btn_redeem(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(RedeemKeyModal())

    @discord.ui.button(label="📜 My Orders", style=discord.ButtonStyle.secondary, custom_id="shop_btn_orders", row=2)
    async def btn_orders(self, interaction: discord.Interaction, button: Button):
        invs = get_user_invoices(interaction.user.id)
        if not invs:
            return await interaction.response.send_message("📦 You haven't placed any orders yet. Click **Buy Server Boosts** above to get started!", ephemeral=True)

        embed = discord.Embed(
            title=f"📜 Order History — {interaction.user.name}",
            description="Your recent purchases and receipt keys:",
            color=AIZEN_COLOR
        )
        for inv in invs[:5]:
            ts = time.strftime('%Y-%m-%d %H:%M', time.gmtime(inv.get('created_at', time.time())))
            status = str(inv.get('status', 'pending')).upper()
            c_name = str(inv.get('crypto', 'LTC')).upper()
            amt = inv.get('amount', inv.get('ltc_amount', 0.0))
            code = inv.get('redeem_key') or "Pending Confirmation"
            embed.add_field(
                name=f"Order `{inv['id']}` • {ts} UTC",
                value=(
                    f"◈ **Product**: `{inv.get('boosts', 2)}x {inv.get('duration', '1m').upper()}`\n"
                    f"◈ **Amount**: `{amt} {c_name}` • **Status**: `{status}`\n"
                    f"◈ **Receipt Key**: `{code}`"
                ),
                inline=False
            )
        embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Shop Engine")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="💎 VIP Loyalty", style=discord.ButtonStyle.secondary, custom_id="shop_btn_vip", row=2)
    async def btn_vip(self, interaction: discord.Interaction, button: Button):
        vip = get_user_vip_tier(interaction.user.id)
        bar_filled = int(vip['progress'] / 10)
        bar_str = "█" * bar_filled + "░" * (10 - bar_filled)

        embed = discord.Embed(
            title=f"💎 VIP Loyalty Card — {interaction.user.name}",
            description=(
                f"*\"Admiration is the emotion furthest from understanding.\"*\n\n"
                f"◈ **Current Tier**: **{vip['tier_name']}**\n"
                f"◈ **Active Perks**: `{vip['tier_perk']}`\n"
                f"◈ **Total Boosts Purchased**: `{vip['total_boosts']}` boosts\n"
                f"◈ **Completed Invoices**: `{vip['total_orders']}` orders\n\n"
                f"**Tier Progression**:\n"
                f"`[{bar_str}]` {vip['progress']}%\n"
                f"*{vip['next_tier']}*"
            ),
            color=AIZEN_ACCENT
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Loyalty Program")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🎁 Transfer Credits", style=discord.ButtonStyle.secondary, custom_id="shop_btn_transfer", row=2)
    async def btn_transfer(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TransferCreditsModal())

# ==========================================
# Bot Startup & Sync
# ==========================================

@bot.event
async def on_ready():
    print("=" * 60)
    print(f" [+] Sōsuke Aizen Bot Online: {bot.user.name} ({bot.user.id})")
    print(f" [+] Prefix: {prefix}")
    print(f" [+] Authorized Owners: {owner_ids}")
    print(f" [+] LTC Address: {ltc_address or 'NOT SET'}")
    print(f" [+] USDT Address: {usdt_address or 'NOT SET'}")
    print(f" [+] BTC Address: {btc_address or 'NOT SET'}")
    print(f" [+] SOL Address: {sol_address or 'NOT SET'}")
    print("=" * 60)

    # Initialize Supabase PostgreSQL Database & sync records
    try:
        await init_database()
        loaded_prefixes = await get_all_guild_prefixes_db()
        _guild_prefixes.update(loaded_prefixes)
        print(f" [+] Loaded {len(_guild_prefixes)} Custom Server Prefixes.")
    except Exception as e:
        print(f" [~] Database init exception: {e}")

    # Register persistent views so buttons work across restarts
    bot.add_view(ShopPanelView())

    try:
        synced = await bot.tree.sync()
        print(f" [+] Synced {len(synced)} Slash Commands.")
    except Exception as e:
        print(f" [-] Failed to sync slash commands: {e}")

# ==========================================
# Public Shop & Panel Commands
# ==========================================

@bot.command(name="shoppanel", aliases=["shop", "panel"])
async def cmd_shoppanel(ctx: commands.Context):
    """Deploys the all-in-one Aizen Shop Panel in this channel."""
    t1m = len(getStock("data/1m.txt") or [])
    t3m = len(getStock("data/3m.txt") or [])
    stats = await get_reviews_stats_db()

    embed = discord.Embed(
        title="⚔️ ── SŌSUKE AIZEN | THE THRONE ── ⚔️",
        description=(
            f"*\"No one stands on the heavens from the beginning. Neither you, nor I, not even God.\"*\n\n"
            f"Welcome to the **Official Discord Server Boosting & Services Portal**.\n"
            f"Instant automated delivery, multi-crypto payments, and 24/7 reliability.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**💎 Available Products**:\n"
            f"◈ **1-Month Boosts**: Level 1 (2x) • Level 2 (7x) • Level 3 (14x)\n"
            f"◈ **3-Month Boosts**: Long-term boost packages\n\n"
            f"**🪙 Supported Crypto**: `LTC` • `USDT` • `BTC` • `SOL`\n"
            f"**📦 Live Stock**: `{t1m * 2}` 1m Boosts | `{t3m * 2}` 3m Boosts\n"
            f"**⭐ Customer Rating**: `⭐ {stats['average_rating']} / 5.0` (`{stats['total_reviews']}` Verified Vouches)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Click a button below to begin your purchase or open a consultation ticket."
        ),
        color=AIZEN_COLOR
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine | 100% Automated")
    view = ShopPanelView()
    await ctx.send(embed=embed, view=view)

@bot.command(name="ticket", aliases=["openticket"])
async def cmd_ticket(ctx: commands.Context):
    """Open an Aizen support or custom purchase ticket."""
    view = TicketTopicLaunchView(bot, HARDCODED_OWNERS)
    embed = discord.Embed(
        title="⚔️ Consultation & Support Desk",
        description=(
            f"*\"Since when were you under the impression...\"*\n\n"
            f"Select a topic below to establish a private channel with our staff."
        ),
        color=AIZEN_COLOR
    )
    await ctx.send(embed=embed, view=view)

@bot.command(name="ticketpanel")
async def cmd_ticketpanel(ctx: commands.Context):
    """Deploy the permanent ticket creation panel (Owner Only)."""
    if not is_owner(ctx.author):
        return await ctx.send("❌ Unauthorized.")

    embed = discord.Embed(
        title="🎫 ── AIZEN CONSULTATION & ASSISTANCE ── 🎫",
        description=(
            f"*\"Admiration is the emotion furthest from understanding.\"*\n\n"
            f"Need assistance, bulk boost packages, or custom payment options?\n"
            f"Select a topic from the dropdown below to create a private ticket."
        ),
        color=AIZEN_COLOR
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    view = TicketTopicLaunchView(bot, HARDCODED_OWNERS)
    await ctx.send(embed=embed, view=view)

# ==========================================
# Customer Reviews & Vouches Management
# ==========================================

@bot.command(name="setreviewchannel", aliases=["setvouchchannel", "reviewchannel", "vouchchannel"])
@commands.has_permissions(administrator=True)
async def cmd_setreviewchannel(ctx: commands.Context, channel: discord.TextChannel = None):
    """Set the dedicated channel where verified customer reviews and vouches are auto-posted."""
    target = channel or ctx.channel
    await set_setting_db(f"guild_{ctx.guild.id}_review_channel", str(target.id))
    await set_setting_db("review_channel_id", str(target.id))

    embed = discord.Embed(
        title="⭐ Review & Vouch Channel Configured",
        description=(
            f"*\"No one stands on the heavens from the beginning.\"*\n\n"
            f"✅ Verified customer reviews and vouches will now automatically post to {target.mention}."
        ),
        color=AIZEN_ACCENT
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await ctx.send(embed=embed)

@bot.command(name="vouch", aliases=["review"])
@commands.cooldown(1, 10, commands.BucketType.user)
async def cmd_vouch(ctx: commands.Context, rating: Optional[int] = None, *, comment: Optional[str] = None):
    """Leave a verified review/vouch for Aizen Boosting Services."""
    if rating is None or not comment:
        view = View(timeout=120)
        btn = Button(label="⭐ Open Review Form", style=discord.ButtonStyle.primary)
        async def _open(inter: discord.Interaction):
            if inter.user.id != ctx.author.id:
                return await inter.response.send_message("❌ This is not your prompt.", ephemeral=True)
            await inter.response.send_modal(CustomerReviewModal())
        btn.callback = _open
        view.add_item(btn)
        return await ctx.send("⭐ **Click below to write your verified review & vouch:**", view=view)

    rating = max(1, min(5, int(rating)))
    product = "Discord Server Boosts"
    rev = await add_review_db(
        user_id=ctx.author.id,
        user_name=ctx.author.name,
        rating=rating,
        comment=comment,
        product=product
    )
    stats = await get_reviews_stats_db()

    stars = "⭐" * rating
    vouch_embed = discord.Embed(
        title="⭐ Customer Review & Vouch Verified",
        description=(
            f"*\"No one stands on the heavens from the beginning.\"*\n\n"
            f"◈ **Rating**: {stars} (`{rating}/5`)\n"
            f"◈ **Customer**: {ctx.author.mention} (`{ctx.author.name}`)\n"
            f"◈ **Product**: `{product}`\n\n"
            f"**Feedback**:\n```{comment}```"
        ),
        color=AIZEN_ACCENT
    )
    vouch_embed.set_thumbnail(url=ctx.author.display_avatar.url)
    vouch_embed.set_footer(
        text=f"Aizen Reviews • Total Vouches: {stats['total_reviews']} • Avg Rating: {stats['average_rating']}★"
    )
    vouch_embed.timestamp = discord.utils.utcnow()

    # Find review channel
    channel_id_setting = await get_setting_db(f"guild_{ctx.guild.id}_review_channel") if ctx.guild else None
    if not channel_id_setting:
        channel_id_setting = await get_setting_db("review_channel_id")

    review_channel = None
    if channel_id_setting and ctx.guild:
        try:
            review_channel = ctx.guild.get_channel(int(channel_id_setting))
        except Exception:
            review_channel = None

    if not review_channel and ctx.guild:
        for ch in ctx.guild.text_channels:
            if any(w in ch.name.lower() for w in ["vouch", "review", "feedback", "vouches", "reviews"]):
                review_channel = ch
                break

    if review_channel:
        try:
            await review_channel.send(embed=vouch_embed)
        except Exception:
            pass

    await ctx.send(f"✅ **Thank you for your vouch, {ctx.author.mention}!** Your feedback has been stored in the database.")

@bot.command(name="reviews", aliases=["vouches"])
@commands.cooldown(1, 5, commands.BucketType.user)
async def cmd_reviews(ctx: commands.Context):
    """View overall satisfaction stats and recent verified customer vouches."""
    stats = await get_reviews_stats_db()
    recent = await get_recent_reviews_db(limit=5)

    desc = (
        f"*\"Admiration is the emotion furthest from understanding.\"*\n\n"
        f"◈ **Overall Satisfaction**: `⭐ {stats['average_rating']} / 5.0`\n"
        f"◈ **Total Verified Vouches**: `{stats['total_reviews']}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Latest Customer Reviews**:\n"
    )
    if recent:
        for r in recent:
            stars = "⭐" * r.get("rating", 5)
            desc += f"• **{r.get('user_name', 'Customer')}** ({stars}):\n  *{r.get('comment', 'Great service!')}*\n\n"
    else:
        desc += "*No reviews yet. Be the first to leave a review using `$vouch`!*\n"

    embed = discord.Embed(
        title="⭐ Sōsuke Aizen Customer Reviews & Vouches",
        description=desc,
        color=AIZEN_COLOR
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine | 100% Automated")
    await ctx.send(embed=embed)

# ==========================================
# Advanced Shop Features: Logs, Orders, VIP & Transfers
# ==========================================

@bot.command(name="setlogchannel", aliases=["orderlogs", "setorderlogs"])
@commands.has_permissions(administrator=True)
async def cmd_setlogchannel(ctx: commands.Context, channel: discord.TextChannel = None):
    """Set the dedicated channel where verified order receipts and delivery logs are auto-posted."""
    target = channel or ctx.channel
    await set_setting_db(f"guild_{ctx.guild.id}_order_log_channel", str(target.id))
    await set_setting_db("order_log_channel_id", str(target.id))

    embed = discord.Embed(
        title="🛒 Order Log Channel Configured",
        description=(
            f"*\"No one stands on the heavens from the beginning.\"*\n\n"
            f"✅ Verified order receipts will now automatically be logged to {target.mention}."
        ),
        color=AIZEN_ACCENT
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await ctx.send(embed=embed)

@bot.command(name="orders", aliases=["myorders", "receipts"])
@commands.cooldown(1, 3, commands.BucketType.user)
async def cmd_orders(ctx: commands.Context):
    """View your personal purchase history and receipt keys."""
    invs = get_user_invoices(ctx.author.id)
    if not invs:
        return await ctx.send(f"📦 You haven't placed any orders yet. Type `{prefix}buy` or `{prefix}shop` to purchase boosts!")

    vip = get_user_vip_tier(ctx.author.id)
    embed = discord.Embed(
        title=f"📜 Order History — {ctx.author.name}",
        description=f"**Loyalty Tier**: `{vip['tier_name']}` • **Total Boosts**: `{vip['total_boosts']}`\n\nRecent orders and receipt keys:",
        color=AIZEN_COLOR
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    for inv in invs[:5]:
        ts = time.strftime('%Y-%m-%d %H:%M', time.gmtime(inv.get('created_at', time.time())))
        status = str(inv.get('status', 'pending')).upper()
        c_name = str(inv.get('crypto', 'LTC')).upper()
        amt = inv.get('amount', inv.get('ltc_amount', 0.0))
        code = inv.get('redeem_key') or "Pending Confirmation"
        embed.add_field(
            name=f"Order `{inv['id']}` • {ts} UTC",
            value=(
                f"◈ **Product**: `{inv.get('boosts', 2)}x {str(inv.get('duration', '1m')).upper()}`\n"
                f"◈ **Amount**: `{amt} {c_name}` • **Status**: `{status}`\n"
                f"◈ **Receipt Key**: `{code}`"
            ),
            inline=False
        )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Shop Engine")
    await ctx.send(embed=embed)

@bot.command(name="vip", aliases=["loyalty", "tier"])
@commands.cooldown(1, 3, commands.BucketType.user)
async def cmd_vip(ctx: commands.Context, target: Optional[discord.Member] = None):
    """View customer VIP loyalty tier, rewards, and discount status."""
    u = target or ctx.author
    vip = get_user_vip_tier(u.id)
    bar_filled = int(vip['progress'] / 10)
    bar_str = "█" * bar_filled + "░" * (10 - bar_filled)

    embed = discord.Embed(
        title=f"💎 VIP Loyalty Card — {u.name}",
        description=(
            f"*\"Admiration is the emotion furthest from understanding.\"*\n\n"
            f"◈ **Current Tier**: **{vip['tier_name']}**\n"
            f"◈ **Active Perks**: `{vip['tier_perk']}`\n"
            f"◈ **Total Boosts Purchased**: `{vip['total_boosts']}` boosts\n"
            f"◈ **Completed Invoices**: `{vip['total_orders']}` orders\n\n"
            f"**Tier Progression**:\n"
            f"`[{bar_str}]` {vip['progress']}%\n"
            f"*{vip['next_tier']}*"
        ),
        color=AIZEN_ACCENT
    )
    embed.set_thumbnail(url=u.display_avatar.url)
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Loyalty Program")
    await ctx.send(embed=embed)

@bot.command(name="transfer", aliases=["sendcredits", "tip"])
@commands.cooldown(1, 5, commands.BucketType.user)
async def cmd_transfer(ctx: commands.Context, member: discord.Member, duration: str, amount: int):
    """Transfer boost credits to another member."""
    success, msg = transfer_user_balance(ctx.author.id, member.id, duration, amount)
    color = AIZEN_ACCENT if success else discord.Color.red()
    embed = discord.Embed(title="🎁 Boost Credit Transfer", description=msg, color=color)
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Shop Engine")
    await ctx.send(embed=embed)

@bot.command(name="top", aliases=["leaderboard", "topbuyers"])
@commands.cooldown(1, 5, commands.BucketType.user)
async def cmd_top(ctx: commands.Context):
    """View top buyers leaderboard by boost volume."""
    top_list = get_top_buyers(10)
    if not top_list:
        return await ctx.send("📊 No purchase records found yet.")

    desc = "*\"No one stands on the heavens from the beginning.\"*\n\n**Top Customer Leaderboard**:\n\n"
    for idx, u in enumerate(top_list, 1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"`#{idx}`"
        desc += f"{medal} <@{u['user_id']}> — `{u['boosts']}` boosts (`{u['orders']}` orders)\n"

    embed = discord.Embed(
        title="🏆 Sōsuke Aizen — Top Customer Leaderboard",
        description=desc,
        color=AIZEN_COLOR
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Shop Engine")
    await ctx.send(embed=embed)

@bot.command(name="promos", aliases=["discounts"])
@commands.cooldown(1, 3, commands.BucketType.user)
async def cmd_promos(ctx: commands.Context):
    """View currently available promotional discount codes."""
    discs = list_active_discounts()
    if not discs:
        return await ctx.send("🏷️ There are currently no active public promo codes. Stay tuned for server promotions!")

    desc = "*Apply any code below during checkout for instant savings!*\n\n"
    for code, pct in discs.items():
        desc += f"• **`{code}`**: `{pct}%` OFF on all boost packages\n"

    embed = discord.Embed(
        title="🏷️ Active Promotional Discount Codes",
        description=desc,
        color=AIZEN_COLOR
    )
    embed.set_footer(text=f"Use in checkout: {prefix}buy 1m 2 ltc code:CODE")
    await ctx.send(embed=embed)

# ==========================================
# Server Setup Wizard, FAQ, Calculator & Streaks
# ==========================================

def fetch_server_invite_details(invite_str: str) -> Optional[dict]:
    """Fetches public server info from Discord API invite endpoint."""
    code = getinviteCode(invite_str)
    if not code:
        return None
    try:
        url = f"https://discord.com/api/v9/invites/{code}?with_counts=true&with_expiration=true"
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            return None
        data = resp.json()
        g = data.get("guild", {})
        if not g:
            return None

        boost_count = int(g.get("premium_subscription_count") or 0)
        if boost_count >= 14:
            tier = 3
            needed_l1 = 0
            needed_l2 = 0
            needed_l3 = 0
            next_tier_desc = "Max Tier 3 (Level 3) Reached! 🎉"
        elif boost_count >= 7:
            tier = 2
            needed_l1 = 0
            needed_l2 = 0
            needed_l3 = 14 - boost_count
            next_tier_desc = f"Need **{needed_l3} more boosts** to reach Level 3 (14 boosts)"
        elif boost_count >= 2:
            tier = 1
            needed_l1 = 0
            needed_l2 = 7 - boost_count
            needed_l3 = 14 - boost_count
            next_tier_desc = f"Need **{needed_l2} more boosts** to reach Level 2 (7 boosts)"
        else:
            tier = 0
            needed_l1 = 2 - boost_count
            needed_l2 = 7 - boost_count
            needed_l3 = 14 - boost_count
            next_tier_desc = f"Need **{needed_l1} more boosts** to reach Level 1 (2 boosts)"

        icon_id = g.get("icon")
        guild_id = g.get("id")
        icon_url = f"https://cdn.discordapp.com/icons/{guild_id}/{icon_id}.png" if icon_id and guild_id else None

        return {
            "code": code,
            "guild_id": guild_id,
            "name": g.get("name", "Unknown Server"),
            "boost_count": boost_count,
            "tier": tier,
            "members": data.get("approximate_member_count", 0),
            "online": data.get("approximate_presence_count", 0),
            "next_tier_desc": next_tier_desc,
            "needed_l1": needed_l1,
            "needed_l2": needed_l2,
            "needed_l3": needed_l3,
            "icon_url": icon_url
        }
    except Exception:
        return None

class SetupWizardView(View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="⚡ 1-Click Instant Auto Deploy", style=discord.ButtonStyle.success, custom_id="btn_setup_autodeploy", row=0)
    async def btn_autodeploy(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator and not is_owner(interaction.user):
            return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            return await interaction.followup.send("❌ Must be used within a server.", ephemeral=True)

        # 1. Shop Category
        shop_cat = discord.utils.get(guild.categories, name="🛒 ── SHOP & SERVICES ──")
        if not shop_cat:
            try:
                shop_cat = await guild.create_category(name="🛒 ── SHOP & SERVICES ──")
            except Exception:
                shop_cat = None

        overwrites_readonly = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False, add_reactions=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True)
        }

        # Create or find channels
        shop_ch = discord.utils.get(guild.text_channels, name="🛒・shop")
        if not shop_ch:
            shop_ch = await guild.create_text_channel(name="🛒・shop", category=shop_cat, overwrites=overwrites_readonly)

        vouch_ch = discord.utils.get(guild.text_channels, name="⭐・vouches")
        if not vouch_ch:
            vouch_ch = await guild.create_text_channel(name="⭐・vouches", category=shop_cat, overwrites=overwrites_readonly)

        logs_ch = discord.utils.get(guild.text_channels, name="📋・order-logs")
        if not logs_ch:
            logs_ch = await guild.create_text_channel(name="📋・order-logs", category=shop_cat, overwrites=overwrites_readonly)

        # 2. Tickets Category & Channel
        tickets_cat = discord.utils.get(guild.categories, name="🎫 ── TICKETS ──")
        if not tickets_cat:
            try:
                tickets_cat = await guild.create_category(name="🎫 ── TICKETS ──")
            except Exception:
                tickets_cat = None

        ticket_panel_ch = discord.utils.get(guild.text_channels, name="🎫・tickets")
        if not ticket_panel_ch:
            ticket_panel_ch = await guild.create_text_channel(name="🎫・tickets", category=tickets_cat, overwrites=overwrites_readonly)

        # Deploy Shop Panel
        t1m = len(getStock("data/1m.txt") or [])
        t3m = len(getStock("data/3m.txt") or [])
        stats = await get_reviews_stats_db()
        shop_embed = discord.Embed(
            title="⚔️ ── SŌSUKE AIZEN | THE THRONE ── ⚔️",
            description=(
                f"*\"No one stands on the heavens from the beginning. Neither you, nor I, not even God.\"*\n\n"
                f"Welcome to the **Official Discord Server Boosting & Services Portal**.\n"
                f"Instant automated delivery, multi-crypto payments, and 24/7 reliability.\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"**💎 Available Products**:\n"
                f"◈ **1-Month Boosts**: Level 1 (2x) • Level 2 (7x) • Level 3 (14x)\n"
                f"◈ **3-Month Boosts**: Long-term boost packages\n\n"
                f"**🪙 Supported Crypto**: `LTC` • `USDT` • `BTC` • `SOL`\n"
                f"**📦 Live Stock**: `{t1m * 2}` 1m Boosts | `{t3m * 2}` 3m Boosts\n"
                f"**⭐ Customer Rating**: `⭐ {stats['average_rating']} / 5.0` (`{stats['total_reviews']}` Verified Vouches)\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Click a button below to begin your purchase or open a consultation ticket."
            ),
            color=AIZEN_COLOR
        )
        shop_embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine | 100% Automated")
        await shop_ch.send(embed=shop_embed, view=ShopPanelView())

        # Deploy Ticket Desk
        t_embed = discord.Embed(
            title="🎫 ── AIZEN CONSULTATION & ASSISTANCE ── 🎫",
            description=(
                f"*\"Admiration is the emotion furthest from understanding.\"*\n\n"
                f"Need assistance, bulk boost packages, or custom payment options?\n"
                f"Select a topic from the dropdown below to create a private ticket."
            ),
            color=AIZEN_COLOR
        )
        t_embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
        await ticket_panel_ch.send(embed=t_embed, view=TicketTopicLaunchView(bot, HARDCODED_OWNERS))

        # Save channel settings to database
        await set_setting_db(f"guild_{guild.id}_review_channel", str(vouch_ch.id))
        await set_setting_db(f"guild_{guild.id}_order_log_channel", str(logs_ch.id))

        summary_embed = discord.Embed(
            title="🎉 Server Setup Successfully Completed!",
            description=(
                f"*\"No one stands on the heavens from the beginning.\"*\n\n"
                f"Your Aizen Shop & Boosting Desk is fully deployed and active:\n\n"
                f"• 🛒 **Shop Panel**: {shop_ch.mention}\n"
                f"• 🎫 **Tickets Desk**: {ticket_panel_ch.mention}\n"
                f"• ⭐ **Review Channel**: {vouch_ch.mention}\n"
                f"• 📋 **Order Logs**: {logs_ch.mention}\n\n"
                f"All permissions and automated database routes are ready!"
            ),
            color=AIZEN_ACCENT
        )
        summary_embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
        await interaction.followup.send(embed=summary_embed, ephemeral=True)

class FAQDropdown(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="1. How to Buy & Instant Auto-Delivery", value="faq_buy", emoji="⚡", description="Step-by-step guide to instant server boosts"),
            discord.SelectOption(label="2. Supported Cryptos & Fees", value="faq_crypto", emoji="🪙", description="LTC, USDT, BTC, SOL payment details"),
            discord.SelectOption(label="3. Boost Duration & Server Safety", value="faq_duration", emoji="🛡️", description="How long boosts last and Discord compliance"),
            discord.SelectOption(label="4. Balance & Redeemable Gift Keys", value="faq_keys", emoji="🔑", description="How to store credits and redeem gift codes"),
            discord.SelectOption(label="5. VIP Loyalty Rewards & Discounts", value="faq_vip", emoji="💎", description="Automatic savings tiers up to 10% off"),
            discord.SelectOption(label="6. Daily Rewards & Streaks", value="faq_daily", emoji="🎁", description="Free daily coupons and boost rewards"),
        ]
        super().__init__(placeholder="❓ Select a topic to view details...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        if choice == "faq_buy":
            title = "⚡ How to Buy & Instant Auto-Delivery"
            desc = (
                "**1.** Click **Buy Server Boosts** in `/shoppanel` or type `/buy`.\n"
                "**2.** Select boost amount (`2`, `4`, `14`, etc.) and duration (`1m` or `3m`).\n"
                "**3.** Optionally paste your server invite to boost automatically upon payment!\n"
                "**4.** Send the exact crypto amount to the provided wallet address.\n"
                "**5.** As soon as the blockchain confirms the transaction, your boosts are delivered instantly!"
            )
        elif choice == "faq_crypto":
            title = "🪙 Supported Cryptocurrencies & Fees"
            desc = (
                "• **Litecoin (LTC)**: Recommended! Lowest fees (<$0.01) and fast 1-confirmation delivery.\n"
                "• **Tether USDT (TRC20)**: Zero price volatility stablecoin pegged 1:1 to USD.\n"
                "• **Bitcoin (BTC)**: Standard Bitcoin network transactions.\n"
                "• **Solana (SOL)**: Ultra-fast transactions on Solana."
            )
        elif choice == "faq_duration":
            title = "🛡️ Boost Duration & Server Safety"
            desc = (
                "• **1-Month Boosts**: Keep your server boosted with full perks for 30+ days.\n"
                "• **3-Month Boosts**: Extended long-term boosting for 90+ days.\n"
                "• **Server Perks**: Custom banner, vanity URL (`.gg/yourname`), 100MB+ upload limits, and 384Kbps HD audio!\n"
                "• **100% Safe**: Boosting applies standard Discord Nitro boosts directly to your guild."
            )
        elif choice == "faq_keys":
            title = "🔑 Balance & Redeemable Gift Keys"
            desc = (
                "• If you don't enter an invite during checkout, your boost credits are safely deposited to your `/balance`.\n"
                "• You can hold credits as long as you want and use `/boost` whenever you are ready!\n"
                "• You can also generate gift keys (`/createcode`) or transfer credits to friends (`/transfer`)."
            )
        elif choice == "faq_vip":
            title = "💎 VIP Loyalty Rewards & Discounts"
            desc = (
                "Every purchase automatically advances your VIP rank:\n"
                "• 🥉 **Bronze** (1+ orders)\n"
                "• 🥈 **Silver** (10+ boosts): 2% off\n"
                "• 🥇 **Gold** (30+ boosts): 5% off + Priority queue\n"
                "• 💎 **Diamond Sovereign** (100+ boosts): 10% off + Instant priority\n"
                "Check your status anytime with `/vip`!"
            )
        else:
            title = "🎁 Daily Rewards & Streaks"
            desc = (
                "• Type `/daily` once every 24 hours to claim your daily streak reward!\n"
                "• Rewards include free promotional discount codes (3% to 15% off) and bonus boost credits!\n"
                "• Maintain your 7-day streak to unlock maximum rewards."
            )

        embed = discord.Embed(title=title, description=f"*\"No one stands on the heavens from the beginning.\"*\n\n{desc}", color=AIZEN_COLOR)
        embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Knowledge Base")
        await interaction.response.edit_message(embed=embed, view=self.view)

class FAQView(View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(FAQDropdown())

@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def cmd_setup(ctx: commands.Context):
    """Launch the interactive Aizen Server Setup Wizard."""
    embed = discord.Embed(
        title="⚡ Sōsuke Aizen — 1-Click Server Setup Wizard",
        description=(
            f"*\"No one stands on the heavens from the beginning.\"*\n\n"
            f"Welcome, **{ctx.author.name}**! Configure your server in seconds:\n\n"
            f"Click **[⚡ 1-Click Instant Auto Deploy]** below to automatically create:\n"
            f"• `#🛒・shop` (Interactive visual shop panel)\n"
            f"• `#🎫・tickets` (Support & custom order consultation desk)\n"
            f"• `#⭐・vouches` (Automated customer review publishing)\n"
            f"• `#📋・order-logs` (Automated verified purchase receipts)\n\n"
            f"All channel permissions, categories, and database links will be configured automatically."
        ),
        color=AIZEN_ACCENT
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await ctx.send(embed=embed, view=SetupWizardView())

@bot.command(name="checkserver", aliases=["servercheck", "boosttier", "tiercheck"])
@commands.cooldown(1, 3, commands.BucketType.user)
async def cmd_checkserver(ctx: commands.Context, invite: str = None):
    """Inspect any Discord server's current boost level, count, and needed boosts."""
    if not invite:
        p = _guild_prefixes.get(ctx.guild.id, prefix) if ctx.guild else prefix
        return await ctx.send(f"❌ Usage: `{p}checkserver <discord.gg/invite_code>`")

    details = fetch_server_invite_details(invite)
    if not details:
        return await ctx.send("❌ Could not reach Discord server. Please verify the invite code is valid and active.")

    p = _guild_prefixes.get(ctx.guild.id, prefix) if ctx.guild else prefix
    l1_status = "✅ Reached" if details["needed_l1"] == 0 else f"Need {details['needed_l1']} boosts"
    l2_status = "✅ Reached" if details["needed_l2"] == 0 else f"Need {details['needed_l2']} boosts"
    l3_status = "✅ Reached" if details["needed_l3"] == 0 else f"Need {details['needed_l3']} boosts"

    embed = discord.Embed(
        title=f"🏰 {details['name']} — Server Boost Inspection",
        description=(
            f"*\"Since when were you under the impression...\"*\n\n"
            f"◈ **Current Boost Tier**: `Level {details['tier']}`\n"
            f"◈ **Active Boosts**: `{details['boost_count']}` boosts\n"
            f"◈ **Server Members**: `{details['members']}` (`{details['online']}` online)\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**🎯 Progression & Quota Needed**:\n"
            f"{details['next_tier_desc']}\n\n"
            f"• **Level 1 (2 Boosts)**: {l1_status}\n"
            f"• **Level 2 (7 Boosts)**: {l2_status}\n"
            f"• **Level 3 (14 Boosts)**: {l3_status}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Type `{p}buy 1m {details['needed_l3'] or 2} ltc .gg/{details['code']}` to boost!"
        ),
        color=AIZEN_COLOR
    )
    if details.get("icon_url"):
        embed.set_thumbnail(url=details["icon_url"])
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await ctx.send(embed=embed)

@bot.command(name="calc", aliases=["calculate", "pricing"])
@commands.cooldown(1, 2, commands.BucketType.user)
async def cmd_calc(ctx: commands.Context, duration: str = "1m", amount: int = 2, discount_code: Optional[str] = None):
    """Calculate multi-crypto pricing for any boost package."""
    p = _guild_prefixes.get(ctx.guild.id, prefix) if ctx.guild else prefix
    dur_clean = duration.lower().strip()
    if dur_clean not in ["1m", "3m"]:
        return await ctx.send("❌ Duration must be `1m` or `3m`.")
    if amount <= 0 or amount % 2 != 0:
        return await ctx.send("❌ Amount must be an even positive number (2 boosts per token).")

    r_ltc = round(get_rate_for_crypto("ltc", dur_clean) * amount, 4)
    r_usdt = round(get_rate_for_crypto("usdt", dur_clean) * amount, 2)
    r_btc = round(get_rate_for_crypto("btc", dur_clean) * amount, 6)
    r_sol = round(get_rate_for_crypto("sol", dur_clean) * amount, 4)

    discount_pct = get_discount_percent(discount_code) if discount_code else 0.0
    if discount_pct > 0:
        r_ltc = round(r_ltc * (1 - discount_pct / 100), 4)
        r_usdt = round(r_usdt * (1 - discount_pct / 100), 2)
        r_btc = round(r_btc * (1 - discount_pct / 100), 6)
        r_sol = round(r_sol * (1 - discount_pct / 100), 4)

    t1m = len(getStock("data/1m.txt") or [])
    t3m = len(getStock("data/3m.txt") or [])
    tokens_needed = amount // 2
    stock_avail = t1m if dur_clean == "1m" else t3m
    stock_status = f"✅ In Stock ({stock_avail * 2} boosts available)" if stock_avail >= tokens_needed else f"⚠️ Low Stock ({stock_avail * 2} available)"

    embed = discord.Embed(
        title=f"🧮 Multi-Crypto Price Calculator — {amount}x {dur_clean.upper()}",
        description=(
            f"*\"Admiration is the emotion furthest from understanding.\"*\n\n"
            f"◈ **Package**: `{amount}`x {dur_clean.upper()} Discord Server Boosts\n"
            f"◈ **Tokens Required**: `{tokens_needed}` accounts\n"
            f"◈ **Stock Status**: {stock_status}\n"
            + (f"◈ **Discount Applied**: `{int(discount_pct)}% OFF` (`{discount_code}`)\n" if discount_pct else "")
            + f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Estimated Costs by Cryptocurrency**:\n"
            f"• 🪙 **Litecoin (LTC)**: **`{r_ltc} LTC`** *(Lowest network fees)*\n"
            f"• 💵 **Tether USDT**: **`${r_usdt} USDT`** *(Zero volatility)*\n"
            f"• ₿ **Bitcoin (BTC)**: **`{r_btc} BTC`**\n"
            f"• 🟣 **Solana (SOL)**: **`{r_sol} SOL`**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Type `/buy` or `{p}buy {dur_clean} {amount}` to order!"
        ),
        color=AIZEN_COLOR
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Shop Engine")
    await ctx.send(embed=embed)

@bot.command(name="daily", aliases=["streak", "reward"])
@commands.cooldown(1, 3, commands.BucketType.user)
async def cmd_daily(ctx: commands.Context):
    """Claim your daily streak reward for discounts and free credits."""
    success, msg, streak, reward_type = await claim_daily_streak_db(ctx.author.id)
    if not success:
        return await ctx.send(msg)

    if streak == 7:
        discount_code = f"STREAK7-{ctx.author.id % 10000}"
        create_discount(discount_code, 15.0)
        add_user_balance(ctx.author.id, "1m", 2)
        reward_desc = f"🎉 **7-DAY STREAK COMPLETED!**\n• **2x 1-Month Boost Credits** added to your balance!\n• **15% OFF Promo Code**: `{discount_code}`"
    elif streak >= 5:
        discount_code = f"STREAK5-{ctx.author.id % 10000}"
        create_discount(discount_code, 10.0)
        reward_desc = f"🔥 **Day {streak} Streak!**\n• **10% OFF Promo Code**: `{discount_code}`"
    elif streak >= 3:
        discount_code = f"STREAK3-{ctx.author.id % 10000}"
        create_discount(discount_code, 5.0)
        reward_desc = f"⚡ **Day {streak} Streak!**\n• **5% OFF Promo Code**: `{discount_code}`"
    else:
        discount_code = f"STREAK-{ctx.author.id % 10000}"
        create_discount(discount_code, 3.0)
        reward_desc = f"🌱 **Day {streak} Streak!**\n• **3% OFF Promo Code**: `{discount_code}`"

    embed = discord.Embed(
        title=f"🎁 Daily Streak Claimed — Day {streak}/7",
        description=(
            f"*\"No one stands on the heavens from the beginning.\"*\n\n"
            f"{reward_desc}\n\n"
            f"Come back tomorrow to keep your streak alive and unlock higher rewards!"
        ),
        color=AIZEN_ACCENT
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Daily Loyalty")
    await ctx.send(embed=embed)

@bot.command(name="faq", aliases=["guide", "helpfaq"])
async def cmd_faq(ctx: commands.Context):
    """Open the interactive Buyer's FAQ and Guide."""
    embed = discord.Embed(
        title="📖 Sōsuke Aizen — Buyer's Knowledge Base & FAQ",
        description=(
            f"*\"Admiration is the emotion furthest from understanding.\"*\n\n"
            f"Select a topic from the dropdown menu below to learn how our automated boosting system works."
        ),
        color=AIZEN_COLOR
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await ctx.send(embed=embed, view=FAQView())

@bot.command(name="setprefix")
@commands.has_permissions(administrator=True)
async def cmd_setprefix(ctx: commands.Context, new_prefix: str = None):
    """Change the bot's command prefix for this server."""
    if not new_prefix or len(new_prefix) > 5:
        p = _guild_prefixes.get(ctx.guild.id, prefix) if ctx.guild else prefix
        return await ctx.send(f"❌ Please provide a valid prefix between 1 and 5 characters (e.g. `{p}setprefix !`).")

    _guild_prefixes[ctx.guild.id] = new_prefix
    await set_setting_db(f"guild_{ctx.guild.id}_prefix", new_prefix)

    embed = discord.Embed(
        title="⚙️ Server Prefix Updated",
        description=f"✅ Prefix for **{ctx.guild.name}** updated to: `{new_prefix}`\nExample: `{new_prefix}help` or `{new_prefix}shop`",
        color=AIZEN_ACCENT
    )
    await ctx.send(embed=embed)

@bot.command(name="broadcast", aliases=["announce"])
async def cmd_broadcast(ctx: commands.Context, *, message: str = None):
    """Broadcast an official announcement to all servers (Owner Only)."""
    if not is_owner(ctx.author):
        return await ctx.send("❌ Unauthorized.")
    if not message:
        p = _guild_prefixes.get(ctx.guild.id, prefix) if ctx.guild else prefix
        return await ctx.send(f"❌ Usage: `{p}broadcast <message>`")

    embed = discord.Embed(
        title="📢 Sōsuke Aizen — Official Announcement",
        description=f"*\"No one stands on the heavens from the beginning.\"*\n\n{message}",
        color=AIZEN_ACCENT
    )
    embed.set_footer(text="Official Broadcast • Kyōka Suigetsu Engine")
    embed.timestamp = discord.utils.utcnow()

    sent = 0
    for guild in bot.guilds:
        target_ch = None
        shop_id = await get_setting_db(f"guild_{guild.id}_order_log_channel")
        if shop_id:
            try:
                target_ch = guild.get_channel(int(shop_id))
            except Exception:
                pass
        if not target_ch:
            for ch in guild.text_channels:
                if any(w in ch.name.lower() for w in ["announcements", "updates", "shop", "general"]):
                    if ch.permissions_for(guild.me).send_messages:
                        target_ch = ch
                        break
        if not target_ch:
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    target_ch = ch
                    break
        if target_ch:
            try:
                await target_ch.send(embed=embed)
                sent += 1
            except Exception:
                pass

    await ctx.send(f"📢 Broadcast sent to `{sent}` servers.")

# ==========================================
# Boosting Commands
# ==========================================

class BoostLaunchView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🚀 Boost a Server", style=discord.ButtonStyle.primary, custom_id="btn_boost_launch_view")
    async def boost_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(InTicketApplyBoostModal())

@bot.tree.command(name="boost", description="Apply boosts using your credits or owner access")
async def slash_boost(interaction: discord.Interaction):
    await interaction.response.send_modal(InTicketApplyBoostModal())

@bot.command(name="boost")
@commands.cooldown(1, 3, commands.BucketType.user)
async def cmd_boost(ctx: commands.Context, invite: str = None, amount: int = None, months: int = None):
    """
    Apply boosts to a server with no limitations.
    Owners have UNLIMITED boosts.
    Regular users consume their credits.
    """
    if not invite or not amount or not months:
        embed = discord.Embed(
            title="⚔️ Sōsuke Aizen — Server Booster",
            description=f"Apply boosts to any Discord server.\n\n**Usage**:\n`{prefix}boost <invite> <amount> <months>`\nExample: `{prefix}boost discord.gg/example 2 1`",
            color=AIZEN_COLOR
        )
        if is_owner(ctx.author):
            embed.set_footer(text="👑 Owner Mode: Unlimited Boosts Active")
        else:
            bal = get_user_balance(ctx.author.id)
            embed.add_field(name="Your Credits", value=f"• 1-Month: `{bal['1m']}` boosts\n• 3-Month: `{bal['3m']}` boosts", inline=False)
            embed.set_footer(text=f"Use {prefix}buy to purchase boost credits with crypto")
        view = BoostLaunchView()
        return await ctx.send(embed=embed, view=view)

    if amount % 2 != 0 or amount <= 0:
        return await ctx.send(embed=discord.Embed(
            title="❌ Invalid Amount",
            description="Number of boosts must be an even positive number (2 boosts per token).",
            color=discord.Color.red()
        ))

    if months not in [1, 3]:
        return await ctx.send(embed=discord.Embed(
            title="❌ Invalid Duration",
            description="Months must be either `1` or `3`.",
            color=discord.Color.red()
        ))

    dur_key = f"{months}m"

    if not is_owner(ctx.author):
        bal = get_user_balance(ctx.author.id)
        current_credits = bal.get(dur_key, 0)
        if current_credits < amount:
            return await ctx.send(embed=discord.Embed(
                title="❌ Insufficient Boost Credits",
                description=f"You need `{amount}`x {dur_key} credits, but you only have `{current_credits}`.\n\nUse `{prefix}buy` or click on `{prefix}shop` to buy with crypto!",
                color=discord.Color.red()
            ))
        deduct_user_balance(ctx.author.id, dur_key, amount)

    await execute_boost(invite, amount, months, ctx.author.id, ctx.channel)

# ==========================================
# In-Ticket Auto-Buy Command
# ==========================================

@bot.command(name="buy")
@commands.cooldown(1, 3, commands.BucketType.user)
async def cmd_buy(ctx: commands.Context, duration: str = None, amount: int = None, *args):
    """
    Buy boosts inside a secure private ticket channel.
    Usage:
      $buy
      $buy 1m 2
      $buy 1m 14 https://discord.gg/xyz
    """
    if not ctx.guild:
        return await ctx.send("❌ This command must be used inside a server.")

    ticket_channel, is_new, ticket_data = await create_or_get_ticket(
        guild=ctx.guild,
        user=ctx.author,
        topic_key="order",
        owners_list=HARDCODED_OWNERS,
        bot_ref=bot
    )

    preload = None
    if duration and amount:
        dur_clean = duration.lower().strip()
        if dur_clean in ["1m", "3m"] and amount > 0 and amount % 2 == 0:
            target_invite = None
            discount_code = None
            for a in args:
                if "discord.gg" in a or "discord.com" in a or len(a) > 5 and not a.startswith("code:"):
                    target_invite = a
                elif a.startswith("code:"):
                    discount_code = a.replace("code:", "").strip().upper()
            preload = {
                "duration": dur_clean,
                "amount": amount,
                "invite": target_invite,
                "discount": discount_code
            }

    await send_order_terminal(ticket_channel, ctx.author, preload_data=preload)

    if is_new:
        await ctx.send(f"⚔️ **Private Auto-Buy Ticket Created:** {ticket_channel.mention}\n*Please proceed to your ticket to select your coin and complete payment.*")
    else:
        await ctx.send(f"⚔️ **Your Order Ticket is Ready:** {ticket_channel.mention}\n*Order updated in your active ticket.*")

# ==========================================
# Redeem Code Command
# ==========================================

@bot.command(name="redeem")
@commands.cooldown(1, 3, commands.BucketType.user)
async def cmd_redeem(ctx: commands.Context, key_code: str = None):
    """Redeem an instant delivery boost key code."""
    if not key_code:
        return await ctx.send(embed=discord.Embed(
            title="🔑 Redeem Boost Code",
            description=f"Enter your boost key to claim your credits:\n`{prefix}redeem <KEY-CODE>`\n\nExample: `{prefix}redeem BOOST-1M-2X-ABCD-1234`",
            color=AIZEN_COLOR
        ))

    success, msg, item = redeem_boost_key(key_code, ctx.author.id)
    color = AIZEN_ACCENT if success else discord.Color.red()

    embed = discord.Embed(title="Code Redemption", description=msg, color=color)
    if success and item:
        bal = get_user_balance(ctx.author.id)
        embed.add_field(name="Updated Balance", value=f"• 1-Month: `{bal['1m']}` boosts\n• 3-Month: `{bal['3m']}` boosts", inline=False)
        embed.set_footer(text=f"Use {prefix}boost <invite> {item['amount']} {item['duration'].replace('m', '')} to apply your boosts!")

    await ctx.send(embed=embed)

# ==========================================
# Live Wallet Inspector & Multi-Address Management
# ==========================================

@bot.command(name="wallet", aliases=["wallets", "addresses"])
async def cmd_wallet(ctx: commands.Context):
    """Inspect all configured crypto wallets live."""
    global ltc_address, usdt_address, btc_address, sol_address

    status_msg = await ctx.send("🔍 Fetching live blockchain data for configured wallets...")

    info_ltc = await asyncio.to_thread(get_wallet_live_info, ltc_address) if ltc_address and "PASTE" not in ltc_address else None

    embed = discord.Embed(title="🪙 Configured Crypto Wallets — Sōsuke Aizen Shop", color=AIZEN_COLOR)

    embed.add_field(
        name="🪙 Litecoin (LTC) [Auto-Confirming]",
        value=(
            f"```{ltc_address or 'Not Configured'}```\n"
            + (f"Balance: `{info_ltc.get('balance_ltc', 0.0)} LTC` | Total Received: `{info_ltc.get('total_received_ltc', 0.0)} LTC`" if info_ltc else "*No live data*")
        ),
        inline=False
    )

    embed.add_field(
        name="💵 Tether USDT (TRC20 / BEP20)",
        value=f"```{usdt_address or 'Not Configured (Owner can set with $setaddress usdt <addy>)'}```",
        inline=False
    )

    embed.add_field(
        name="₿ Bitcoin (BTC)",
        value=f"```{btc_address or 'Not Configured (Owner can set with $setaddress btc <addy>)'}```",
        inline=False
    )

    embed.add_field(
        name="🟣 Solana (SOL)",
        value=f"```{sol_address or 'Not Configured (Owner can set with $setaddress sol <addy>)'}```",
        inline=False
    )

    embed.set_footer(text="Owners can link or update any address anytime with $setaddress <coin> <address>")
    await status_msg.edit(content=None, embed=embed)

@bot.command(name="setaddress", aliases=["setwallet"])
async def cmd_setaddress(ctx: commands.Context, crypto: str = None, new_address: str = None):
    """Link a receiving address for LTC, USDT, BTC, or SOL (Owner Only)."""
    global ltc_address, usdt_address, btc_address, sol_address

    if not is_owner(ctx.author):
        return await ctx.send("❌ Unauthorized.")

    if not crypto or not new_address:
        return await ctx.send(f"❌ Usage: `{prefix}setaddress <ltc|usdt|btc|sol> <address>`")

    c = crypto.lower().strip()
    if c not in ["ltc", "usdt", "btc", "sol"]:
        return await ctx.send("❌ Invalid coin. Choose `ltc`, `usdt`, `btc`, or `sol`.")

    clean_addy = new_address.strip()
    cfg = load_config()
    if "crypto_wallets" not in cfg:
        cfg["crypto_wallets"] = {}

    cfg["crypto_wallets"][c] = clean_addy

    if c == "ltc":
        ltc_address = clean_addy
        if "ltc" not in cfg: cfg["ltc"] = {}
        cfg["ltc"]["address"] = clean_addy
    elif c == "usdt":
        usdt_address = clean_addy
    elif c == "btc":
        btc_address = clean_addy
    elif c == "sol":
        sol_address = clean_addy

    save_config(cfg)
    await ctx.send(f"✅ Receiving address for **{CRYPTO_NAMES.get(c, c.upper())}** updated successfully:\n```{clean_addy}```")

# ==========================================
# Dynamic Pricing & Discounts
# ==========================================

@bot.command(name="setprice")
async def cmd_setprice(ctx: commands.Context, duration: str = None, crypto: str = None, new_price: float = None):
    """Set price per boost for any crypto (Owner Only)."""
    if not is_owner(ctx.author):
        return await ctx.send("❌ Unauthorized.")

    if not duration or not crypto or not new_price or new_price <= 0:
        return await ctx.send(f"❌ Usage: `{prefix}setprice <1m|3m> <ltc|usdt|btc|sol> <price>`\nExample: `{prefix}setprice 1m usdt 1.20`")

    dur = duration.lower().strip()
    c = crypto.lower().strip()

    if dur not in ["1m", "3m"] or c not in ["ltc", "usdt", "btc", "sol"]:
        return await ctx.send("❌ Invalid parameters.")

    cfg = load_config()
    rate_key = f"rates_{dur}"
    if rate_key not in cfg:
        cfg[rate_key] = {}
    cfg[rate_key][c] = float(new_price)
    save_config(cfg)

    await ctx.send(f"✅ Pricing for **{dur}** in **{c.upper()}** updated to **`{new_price} {c.upper()}`** per boost!")

@bot.command(name="creatediscount")
async def cmd_creatediscount(ctx: commands.Context, code: str = None, percent: float = None):
    """Create a promotional discount code (Owner Only)."""
    if not is_owner(ctx.author):
        return await ctx.send("❌ Unauthorized.")

    if not code or not percent or percent <= 0 or percent >= 100:
        return await ctx.send(f"❌ Usage: `{prefix}creatediscount <CODE> <percent_off>`\nExample: `{prefix}creatediscount SUMMER10 10`")

    create_discount(code, percent)
    await ctx.send(f"✅ Discount code **`{code.upper()}`** created for **{percent}% off**! Users can use it with `{prefix}buy 1m 2 code:{code.upper()}`.")

# ==========================================
# Gift Code Generator (Owner Only)
# ==========================================

@bot.command(name="createcode", aliases=["genkey"])
async def cmd_createcode(ctx: commands.Context, duration: str = None, amount: int = None):
    """Generate a free redeemable gift code (Owner Only)."""
    if not is_owner(ctx.author):
        return await ctx.send("❌ Unauthorized.")

    if duration not in ["1m", "3m"] or not amount or amount <= 0:
        return await ctx.send(f"❌ Usage: `{prefix}createcode <1m|3m> <amount>`\nExample: `{prefix}createcode 1m 2`")

    key_str = generate_boost_key(duration, amount, created_by=f"owner_{ctx.author.id}")
    embed = discord.Embed(
        title="🎁 Gift Boost Code Generated",
        description=f"**Code**: `{key_str}`\n**Product**: `{amount}x {duration}` Boosts\n\nGive this code to any user to redeem with `{prefix}redeem {key_str}`.",
        color=AIZEN_ACCENT
    )
    await ctx.send(embed=embed)

# ==========================================
# Sales Statistics Dashboard
# ==========================================

@bot.command(name="stats")
async def cmd_stats(ctx: commands.Context):
    """View shop sales statistics and revenue."""
    stats = get_sales_stats()
    tokens_1m = len(getStock("data/1m.txt") or [])
    tokens_3m = len(getStock("data/3m.txt") or [])

    embed = discord.Embed(title="📊 Booster Shop Statistics — Sōsuke Aizen", color=AIZEN_COLOR)
    embed.add_field(name="💰 Total Revenue (LTC)", value=f"`{stats['total_revenue_ltc']} LTC`", inline=True)
    embed.add_field(name="📦 Total Boosts Sold", value=f"`{stats['total_boosts_sold']}` boosts", inline=True)
    embed.add_field(name="✅ Completed Orders", value=f"`{stats['completed_orders']}` orders", inline=True)
    embed.add_field(name="⏳ Pending Orders", value=f"`{stats['pending_orders']}` orders", inline=True)
    embed.add_field(name="🔑 Keys Generated / Redeemed", value=f"`{stats['total_keys_generated']}` / `{stats['total_keys_redeemed']}`", inline=True)
    embed.add_field(name="📦 Current Available Stock", value=f"• 1m: `{tokens_1m}` tokens (`{tokens_1m*2}` boosts)\n• 3m: `{tokens_3m}` tokens (`{tokens_3m*2}` boosts)", inline=False)
    await ctx.send(embed=embed)

# ==========================================
# Balance & Credits Commands
# ==========================================

@bot.command(name="balance", aliases=["credits", "bal"])
@commands.cooldown(1, 3, commands.BucketType.user)
async def cmd_balance(ctx: commands.Context, member: discord.Member = None):
    """Check boost credit balance."""
    target = member or ctx.author
    bal = get_user_balance(target.id)

    embed = discord.Embed(title=f"💳 Boost Credits — {target.name}", color=AIZEN_COLOR)
    embed.add_field(name="1-Month Credits", value=f"`{bal['1m']}` boosts", inline=True)
    embed.add_field(name="3-Month Credits", value=f"`{bal['3m']}` boosts", inline=True)

    if is_owner(target):
        embed.set_footer(text="👑 Owner: Unlimited Boosts Active")
    else:
        embed.set_footer(text=f"Use {prefix}buy to auto-buy more credits | Use {prefix}boost to spend")
    await ctx.send(embed=embed)

# ==========================================
# Stock & Bulk Restock Commands
# ==========================================

@bot.command(name="stock")
async def cmd_stock(ctx: commands.Context):
    """Check current available stock of Nitro tokens."""
    tokens_1m = getStock("data/1m.txt") or []
    tokens_3m = getStock("data/3m.txt") or []

    embed = discord.Embed(title="📦 Current Stock Availability", color=AIZEN_COLOR)
    embed.add_field(name="1-Month Tokens", value=f"`{len(tokens_1m)}` tokens (`{len(tokens_1m) * 2}` boosts)", inline=True)
    embed.add_field(name="3-Month Tokens", value=f"`{len(tokens_3m)}` tokens (`{len(tokens_3m) * 2}` boosts)", inline=True)
    embed.set_footer(text=f"Use {prefix}buy to purchase boosts with crypto")
    await ctx.send(embed=embed)

@bot.command(name="restock")
async def cmd_restock(ctx: commands.Context, duration: str = None, *, token_data: str = None):
    """Bulk restock tokens directly from Discord (Owner Only)."""
    if not is_owner(ctx.author):
        return await ctx.send("❌ Unauthorized.")

    if not duration or duration.lower() not in ["1m", "3m"]:
        return await ctx.send(f"❌ Usage: `{prefix}restock <1m|3m>` (attach `.txt` file or paste tokens)")

    dur_clean = duration.lower().strip()
    filename = "data/1m.txt" if dur_clean == "1m" else "data/3m.txt"
    os.makedirs("data", exist_ok=True)

    tokens_to_add = []

    if ctx.message.attachments:
        for attachment in ctx.message.attachments:
            if attachment.filename.endswith(".txt"):
                content = await attachment.read()
                lines = content.decode("utf-8", errors="ignore").splitlines()
                tokens_to_add.extend([l.strip() for l in lines if l.strip()])

    if token_data:
        for l in token_data.strip().splitlines():
            if l.strip():
                tokens_to_add.append(l.strip())

    if not tokens_to_add:
        return await ctx.send("❌ No tokens provided.")

    existing_stock = set(getStock(filename) or [])
    new_tokens = []
    for t in tokens_to_add:
        actual_t = t.split(":")[2] if ":" in t else t
        if actual_t not in existing_stock:
            new_tokens.append(t)
            existing_stock.add(actual_t)

    with open(filename, "a", encoding="utf-8") as f:
        for t in new_tokens:
            f.write(t + "\n")

    try:
        await ctx.message.delete()
    except Exception:
        pass

    total_now = len(getStock(filename) or [])
    embed = discord.Embed(
        title="✅ Bulk Restock Complete",
        description=(
            f"• Added: `{len(new_tokens)}` new tokens\n"
            f"• Skipped Duplicates: `{len(tokens_to_add) - len(new_tokens)}`\n"
            f"• **Current Total Stock**: `{total_now}` tokens (`{total_now * 2}` boosts)"
        ),
        color=AIZEN_ACCENT
    )
    await ctx.send(embed=embed)

@bot.command(name="usedtokens")
async def cmd_usedtokens(ctx: commands.Context):
    """Check how many used tokens have been archived (Owner Only)."""
    if not is_owner(ctx.author):
        return await ctx.send("❌ Unauthorized.")

    count = 0
    if os.path.exists(USED_TOKENS_FILE):
        with open(USED_TOKENS_FILE, "r", encoding="utf-8") as f:
            count = len([l for l in f.read().splitlines() if l.strip()])

    embed = discord.Embed(
        title="🗄️ Archived Used Tokens",
        description=f"Total tokens moved to archive: `{count}` tokens.\nArchive file: `{USED_TOKENS_FILE}`",
        color=AIZEN_COLOR
    )
    await ctx.send(embed=embed)

# ==========================================
# Owner Admin Credit Management
# ==========================================

@bot.command(name="addcredits", aliases=["addbal"])
async def cmd_addcredits(ctx: commands.Context, member: discord.Member, duration: str, amount: int):
    """Manually add boost credits to a user (Owner Only)."""
    if not is_owner(ctx.author):
        return await ctx.send("❌ Unauthorized.")

    dur_clean = duration.lower().strip()
    if dur_clean not in ["1m", "3m"] or amount <= 0:
        return await ctx.send(f"❌ Usage: `{prefix}addcredits @user <1m|3m> <amount>`")

    new_bal = add_user_balance(member.id, dur_clean, amount)
    embed = discord.Embed(
        title="✅ Credits Added",
        description=f"Added `{amount}`x {dur_clean} boosts to {member.mention}.\n**New Balance**: `{new_bal[dur_clean]}` {dur_clean} boosts.",
        color=AIZEN_ACCENT
    )
    await ctx.send(embed=embed)

@bot.command(name="removecredits", aliases=["delbal"])
async def cmd_removecredits(ctx: commands.Context, member: discord.Member, duration: str, amount: int):
    """Manually remove boost credits from a user (Owner Only)."""
    if not is_owner(ctx.author):
        return await ctx.send("❌ Unauthorized.")

    dur_clean = duration.lower().strip()
    if dur_clean not in ["1m", "3m"] or amount <= 0:
        return await ctx.send(f"❌ Usage: `{prefix}removecredits @user <1m|3m> <amount>`")

    deduct_user_balance(member.id, dur_clean, amount)
    bal = get_user_balance(member.id)
    embed = discord.Embed(
        title="✅ Credits Removed",
        description=f"Removed `{amount}`x {dur_clean} boosts from {member.mention}.\n**New Balance**: `{bal[dur_clean]}` {dur_clean} boosts.",
        color=AIZEN_COLOR
    )
    await ctx.send(embed=embed)

@bot.command(name="confirmorder", aliases=["approveorder"])
async def cmd_confirmorder(ctx: commands.Context, invoice_id: str):
    """Force-approve and credit an invoice manually (Owner Only)."""
    if not is_owner(ctx.author):
        return await ctx.send("❌ Unauthorized.")

    success, msg, inv = force_complete_invoice(invoice_id.strip())
    color = AIZEN_ACCENT if success else discord.Color.red()
    embed = discord.Embed(title="Order Update", description=msg, color=color)
    if success and inv and inv.get("redeem_key"):
        embed.add_field(name="Redeem Code Generated", value=f"`{inv['redeem_key']}`", inline=False)
    await ctx.send(embed=embed)

# ==========================================
# Utility & Security Commands
# ==========================================

@bot.command(name="cancelorder")
async def cmd_cancelorder(ctx: commands.Context, invoice_id: str = None):
    """Cancel a pending invoice."""
    if not invoice_id:
        return await ctx.send(f"❌ Usage: `{prefix}cancelorder <INV-ID>`")
    success, msg = cancel_invoice(invoice_id.strip(), ctx.author.id, is_owner(ctx.author))
    color = AIZEN_ACCENT if success else discord.Color.red()
    await ctx.send(embed=discord.Embed(title="Order Cancellation", description=msg, color=color))

# ==========================================
# Essential Utility & Info Commands
# ==========================================

@bot.command(name="ping")
@commands.cooldown(1, 3, commands.BucketType.user)
async def cmd_ping(ctx: commands.Context):
    """Check bot responsiveness, API latency, and uptime."""
    start_time = time.time()
    msg = await ctx.send("🏓 Measuring Kyōka Suigetsu response times...")
    end_time = time.time()

    api_latency = round((end_time - start_time) * 1000)
    ws_latency = round(bot.latency * 1000)

    embed = discord.Embed(
        title="🏓 Pong! — Sōsuke Aizen System Status",
        description="*\"No one stands on the heavens from the beginning.\"*",
        color=AIZEN_ACCENT
    )
    embed.add_field(name="⚡ Gateway Latency", value=f"`{ws_latency}ms`", inline=True)
    embed.add_field(name="🌐 API Roundtrip", value=f"`{api_latency}ms`", inline=True)
    embed.add_field(name="⏱️ System Uptime", value=f"`{get_uptime_str()}`", inline=True)
    embed.add_field(name="☁️ System Status", value="`Operational (24/7 Active)`", inline=True)
    embed.add_field(name="🗄️ Database Engine", value="`Supabase PostgreSQL`" if is_db_connected() else "`Resilient Storage`", inline=True)
    embed.add_field(name="🛡️ Security Level", value="`Hardened & Active`", inline=True)
    embed.add_field(name="✨ Prefix Mode", value=f"`{prefix}` or `no-prefix for shortcuts`", inline=True)
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await msg.edit(content=None, embed=embed)

@bot.command(name="uptime")
@commands.cooldown(1, 3, commands.BucketType.user)
async def cmd_uptime(ctx: commands.Context):
    """Check how long the bot has been running continuously."""
    embed = discord.Embed(
        title="⏱️ Continuous Uptime Monitor",
        description=(
            f"*\"Since when were you under the impression...\"*\n\n"
            f"◈ **Online Duration**: `{get_uptime_str()}`\n"
            f"◈ **24/7 High-Availability**: `Active & Operational`\n"
            f"◈ **Connected Servers**: `{len(bot.guilds)}`"
        ),
        color=AIZEN_COLOR
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await ctx.send(embed=embed)

@bot.command(name="serverinfo", aliases=["guildinfo", "server"])
@commands.cooldown(1, 3, commands.BucketType.user)
async def cmd_serverinfo(ctx: commands.Context):
    """Inspect current server statistics, boost tier, and members."""
    if not ctx.guild:
        return await ctx.send("❌ This command must be used within a server.")
    g = ctx.guild
    embed = discord.Embed(
        title=f"🏰 {g.name} — Server Overview",
        description=f"Server ID: `{g.id}`\nOwner: <@{g.owner_id}>",
        color=AIZEN_COLOR
    )
    if g.icon:
        embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name="👥 Members", value=f"`{g.member_count}` total", inline=True)
    embed.add_field(name="🚀 Boost Level", value=f"Level `{g.premium_tier}` ({g.premium_subscription_count} boosts)", inline=True)
    embed.add_field(name="📜 Channels", value=f"`{len(g.channels)}` channels", inline=True)
    embed.add_field(name="🎭 Roles", value=f"`{len(g.roles)}` roles", inline=True)
    embed.add_field(name="📅 Created At", value=f"`{g.created_at.strftime('%Y-%m-%d')}`", inline=True)
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await ctx.send(embed=embed)

@bot.command(name="userinfo", aliases=["whoami", "user"])
@commands.cooldown(1, 3, commands.BucketType.user)
async def cmd_userinfo(ctx: commands.Context, target: Optional[discord.Member] = None):
    """Inspect user profile and available boost credit balance."""
    u = target or ctx.author
    bal = get_user_balance(u.id)
    embed = discord.Embed(
        title=f"👤 {u.name} — User Profile",
        color=AIZEN_COLOR
    )
    embed.set_thumbnail(url=u.display_avatar.url)
    embed.add_field(name="Identity", value=f"Name: `{u.name}`\nID: `{u.id}`\nMention: {u.mention}", inline=True)
    embed.add_field(name="💳 Boost Credits", value=f"• 1-Month: `{bal['1m']}`\n• 3-Month: `{bal['3m']}`", inline=True)
    embed.add_field(name="📅 Account Created", value=f"`{u.created_at.strftime('%Y-%m-%d')}`", inline=False)
    if hasattr(u, "joined_at") and u.joined_at:
        embed.add_field(name="📥 Server Joined", value=f"`{u.joined_at.strftime('%Y-%m-%d')}`", inline=True)
    if is_owner(u):
        embed.add_field(name="👑 Authorization", value="`👑 Throne Owner (Unlimited Access)`", inline=False)
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await ctx.send(embed=embed)

@bot.command(name="botinfo", aliases=["about", "info"])
@commands.cooldown(1, 3, commands.BucketType.user)
async def cmd_botinfo(ctx: commands.Context):
    """Display bot engine specifications and live stats."""
    t1m = len(getStock("data/1m.txt") or [])
    t3m = len(getStock("data/3m.txt") or [])
    embed = discord.Embed(
        title="⚔️ SŌSUKE AIZEN | THE THRONE ENGINE",
        description=(
            f"*\"No one stands on the heavens from the beginning. Neither you, nor I, not even God.\"*\n\n"
            f"◈ **Engine**: `Kyōka Suigetsu v3.0`\n"
            f"◈ **Uptime**: `{get_uptime_str()}`\n"
            f"◈ **Web Latency**: `{round(bot.latency * 1000)}ms`\n"
            f"◈ **Active Servers**: `{len(bot.guilds)}`\n"
            f"◈ **Available Stock**: `{t1m * 2}` 1m Boosts | `{t3m * 2}` 3m Boosts\n"
            f"◈ **System Status**: `Operational (24/7 Active)`\n"
            f"◈ **Database**: `{'Supabase PostgreSQL' if is_db_connected() else 'Resilient Storage'}`\n"
            f"◈ **Owners**: `{', '.join(str(o) for o in HARDCODED_OWNERS)}`"
        ),
        color=AIZEN_COLOR
    )
    if bot.user.avatar:
        embed.set_thumbnail(url=bot.user.avatar.url)
    embed.set_footer(text="Automated Multi-Crypto Boosting & Shop Bot")
    await ctx.send(embed=embed)

@bot.command(name="avatar", aliases=["av", "pfp"])
@commands.cooldown(1, 3, commands.BucketType.user)
async def cmd_avatar(ctx: commands.Context, target: Optional[discord.Member] = None):
    """View high-resolution avatar image."""
    u = target or ctx.author
    embed = discord.Embed(title=f"🖼️ {u.name}'s Avatar", color=AIZEN_COLOR)
    embed.set_image(url=u.display_avatar.url)
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await ctx.send(embed=embed)

@bot.command(name="clear", aliases=["purge"])
@commands.has_permissions(manage_messages=True)
async def cmd_clear(ctx: commands.Context, amount: int = 10):
    """Purge recent channel messages (Manage Messages required)."""
    if amount <= 0 or amount > 100:
        return await ctx.send("❌ Please specify an amount between 1 and 100.")
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 Cleaned `{len(deleted) - 1}` messages.")
    await asyncio.sleep(3)
    try:
        await msg.delete()
    except Exception:
        pass

# ==========================================
# Global Security & Rate-Limit Error Handler
# ==========================================

@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    """Centralized security error handler preventing spam and crashes."""
    if isinstance(error, commands.CommandOnCooldown):
        return await ctx.send(
            embed=discord.Embed(
                title="⏳ Rate Limited",
                description=f"You are on cooldown. Please wait **`{error.retry_after:.1f}s`** before using this command again.",
                color=discord.Color.gold()
            ),
            delete_after=5
        )
    elif isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send(
            embed=discord.Embed(
                title="⚠️ Missing Arguments",
                description=f"Missing required parameter: `{error.param.name}`.\nType `{prefix}help` to view correct syntax.",
                color=discord.Color.red()
            ),
            delete_after=10
        )
    elif isinstance(error, commands.BadArgument):
        return await ctx.send(
            embed=discord.Embed(
                title="⚠️ Invalid Parameter",
                description="Please check your input values.",
                color=discord.Color.red()
            ),
            delete_after=10
        )
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        print(f"[!] Error in command '{ctx.command}': {error}")

# ==========================================
# Modular Help System
# ==========================================

def get_modular_help_embed(category: str, p: str) -> discord.Embed:
    """Builds clean, modular help embeds with Aizen theme."""

    if category == "shop":
        embed = discord.Embed(
            title="🛒 Module: Auto-Shop & Purchasing",
            description="Buy boost credits using LTC, USDT, BTC, or SOL, redeem keys, and manage credits.",
            color=AIZEN_COLOR
        )
        embed.add_field(
            name=f"⚡ `{p}buy <1m|3m> <amount> [coin] [invite] [code:PROMO]`",
            value=(
                "Creates an automated crypto invoice with QR code and an interactive `[Check Payment]` button.\n"
                "• **Coins**: `ltc`, `usdt`, `btc`, `sol`\n"
                "• **Instant Auto-Boost**: Add your invite link (`$buy 1m 2 ltc discord.gg/example`) to boost immediately upon payment!\n"
                "• **Promo Codes**: Add a discount (`$buy 1m 2 ltc code:SAVE10`) for price reductions."
            ),
            inline=False
        )
        embed.add_field(name=f"🏪 `{p}shoppanel` *(or `{p}shop`)*", value="Deploys the all-in-one visual Aizen shop panel with 1-click buy buttons.", inline=False)
        embed.add_field(name=f"🔑 `{p}redeem <KEY-CODE>`", value="Redeem an instant delivery boost code (e.g. `BOOST-1M-2X-ABCD-1234`) to claim credits.", inline=False)
        embed.add_field(name=f"💳 `{p}balance`", value="Displays your current available 1-Month and 3-Month boost credits.", inline=False)
        embed.add_field(name=f"📦 `{p}stock`", value="View the bot's real-time Nitro token stock and total boosts available.", inline=False)
        embed.add_field(name=f"📊 `{p}stats`", value="View total shop sales, revenue earned, and completed orders.", inline=False)
        embed.add_field(name=f"📜 `{p}orders` *(or `{p}myorders`)*", value="View your personal purchase history and receipt keys.", inline=False)
        embed.add_field(name=f"💎 `{p}vip` *(or `{p}loyalty`)*", value="Inspect customer VIP loyalty rank, perks, and savings tier.", inline=False)
        embed.add_field(name=f"🎁 `{p}transfer @user <1m|3m> <amt>`", value="Transfer boost credits from your balance to a friend.", inline=False)
        embed.add_field(name=f"🏆 `{p}top` *(or `{p}leaderboard`)*", value="View top customer leaderboard by boost volume.", inline=False)
        embed.add_field(name=f"🏷️ `{p}promos` *(or `{p}discounts`)*", value="View active promotional discount codes.", inline=False)
        embed.add_field(name=f"⭐ `{p}vouch [1-5] [comment]` *(or `{p}review`)*", value="Leave a verified review/vouch for boost orders.", inline=False)
        embed.add_field(name=f"📜 `{p}reviews` *(or `{p}vouches`)*", value="View customer reviews and average satisfaction rating.", inline=False)
        embed.add_field(name=f"⚙️ `{p}setreviewchannel #channel` 👑", value="Configure channel for automatic customer review publishing.", inline=False)
        embed.add_field(name=f"🛒 `{p}setlogchannel #channel` 👑", value="Configure channel for automated order delivery receipts.", inline=False)
        embed.set_footer(text="Use the dropdown menu below to navigate modules")
        return embed

    elif category == "boost":
        embed = discord.Embed(
            title="🚀 Module: Server Boosting",
            description="Apply Discord Nitro boosts to any server using credits or owner mode.",
            color=AIZEN_COLOR
        )
        embed.add_field(
            name=f"🎯 `{p}boost <invite> <amount> <months>`",
            value=(
                "Directly boosts the target server with no arbitrary limits.\n"
                "• `<invite>`: Server link or code (e.g. `discord.gg/yourserver` or `yourserver`).\n"
                "• `<amount>`: Number of boosts (must be an even number: `2`, `4`, `14`).\n"
                "• `<months>`: Duration (`1` for 1-month tokens, `3` for 3-month tokens).\n"
                "• *Example*: `{p}boost discord.gg/example 2 1`"
            ),
            inline=False
        )
        embed.add_field(name=f"📱 `{p}boost` *(Interactive Button)*", value="Sends an embed with a **[🚀 Boost a Server]** button that opens a popup form.", inline=False)
        embed.add_field(name="⚡ `/boost` *(Slash Command)*", value="Discord slash command that immediately opens the boosting popup modal.", inline=False)
        embed.set_footer(text="👑 Owners have UNLIMITED boosts | Regular users consume credits")
        return embed

    elif category == "wallet":
        embed = discord.Embed(
            title="🪙 Module: Multi-Crypto & Wallet Management",
            description="Manage your receiving wallets and inspect live blockchain data.",
            color=AIZEN_COLOR
        )
        embed.add_field(name=f"🔍 `{p}wallet` *(or `{p}wallets`, `{p}addresses`)*", value="Queries live blockchain nodes for configured receiving addresses.", inline=False)
        embed.add_field(name=f"📬 `{p}setaddress <ltc|usdt|btc|sol> <address>` 👑", value="Link or update a receiving crypto address on the fly without restarting the bot.", inline=False)
        embed.add_field(name=f"🏷️ `{p}setprice <1m|3m> <coin> <price>` 👑", value="Update pricing dynamically (e.g. `{p}setprice 1m usdt 1.20`).", inline=False)
        embed.set_footer(text="👑 = Owner Only Command")
        return embed

    elif category == "tickets":
        embed = discord.Embed(
            title="🎫 Module: Advanced Consultation Tickets",
            description="Private consultation channels with topic selection and staff controls.",
            color=AIZEN_COLOR
        )
        embed.add_field(name=f"🎫 `{p}ticket`", value="Open a private support ticket with topic selection.", inline=False)
        embed.add_field(name=f"📌 `{p}ticketpanel` 👑", value="Deploys the permanent ticket creation panel to a channel.", inline=False)
        embed.add_field(
            name="📋 Available Topics",
            value=(
                "• 🛒 Boost Purchases & Custom Deals\n"
                "• 💎 VIP & Wholesale Bulk Orders (50+ boosts)\n"
                "• ❓ General Support & Assistance\n"
                "• 💼 Partnerships & Collaborations"
            ),
            inline=False
        )
        embed.set_footer(text="Tickets feature in-channel Close, Claim, and Transcript controls")
        return embed

    elif category == "admin":
        embed = discord.Embed(
            title="👑 Module: Owner & Stock Administration",
            description="Administrative commands for managing stock, gifts, discounts, and users.",
            color=AIZEN_COLOR
        )
        embed.add_field(name=f"📥 `{p}restock <1m|3m>`", value="Bulk restock Nitro tokens (paste in text or attach `.txt` file).", inline=False)
        embed.add_field(name=f"🎁 `{p}createcode <1m|3m> <amount>`", value="Generate free redeemable gift codes (e.g. for giveaways or custom deals).", inline=False)
        embed.add_field(name=f"🏷️ `{p}creatediscount <code> <percent_off>`", value="Create promotional discount codes (e.g. `{p}creatediscount SUMMER10 10`).", inline=False)
        embed.add_field(name=f"➕ `{p}addcredits @user <1m|3m> <amount>`", value="Manually gift or credit boost balance to any Discord user.", inline=False)
        embed.add_field(name=f"➖ `{p}removecredits @user <1m|3m> <amount>`", value="Deduct boost credits from any user.", inline=False)
        embed.add_field(name=f"✅ `{p}confirmorder <INV-ID>`", value="Force-approve a pending invoice manually and deliver credits and redeem code.", inline=False)
        embed.add_field(name=f"🗄️ `{p}usedtokens`", value="View the total count of used/archived tokens moved out of stock.", inline=False)
        embed.set_footer(text="Restricted to hardcoded bot owners [1505515188991033409, 1521774957065928734]")
        return embed

    elif category == "utility":
        embed = discord.Embed(
            title="🛠️ Module: Essential Utility & Tools",
            description="Basic bot commands, diagnostics, and server tools (usable with or without prefix!).",
            color=AIZEN_COLOR
        )
        embed.add_field(name=f"⚡ `{p}setup` 👑", value="1-Click Server Setup Wizard (auto-deploys shop, tickets, reviews & logs).", inline=False)
        embed.add_field(name=f"🏰 `{p}checkserver <invite>`", value="Inspect any server's boost tier, member count, and needed boosts.", inline=False)
        embed.add_field(name=f"🧮 `{p}calc <1m|3m> <amt>`", value="Calculate multi-crypto pricing with live discounts for any package.", inline=False)
        embed.add_field(name=f"🎁 `{p}daily`", value="Claim daily streak rewards for free discount codes and credits.", inline=False)
        embed.add_field(name=f"📖 `{p}faq` *(or `{p}guide`)*", value="Interactive Buyer's Knowledge Base & FAQ.", inline=False)
        embed.add_field(name=f"⚙️ `{p}setprefix <prefix>` 👑", value="Change the bot's command prefix for this server.", inline=False)
        embed.add_field(name=f"🏓 `{p}ping` *(or just `ping`)*", value="View WebSocket latency, REST API roundtrip, and system uptime.", inline=False)
        embed.add_field(name=f"⏱️ `{p}uptime` *(or just `uptime`)*", value="Check continuous 24/7 online duration.", inline=False)
        embed.add_field(name=f"🏰 `{p}serverinfo` *(or just `serverinfo`)*", value="Display server statistics, member counts, and Discord boost tier.", inline=False)
        embed.add_field(name=f"👤 `{p}userinfo` *(or just `userinfo`, `whoami`)*", value="Inspect user account creation date, server join date, and boost balance.", inline=False)
        embed.add_field(name=f"🤖 `{p}botinfo` *(or just `botinfo`)*", value="View bot engine statistics, version, active servers, and host details.", inline=False)
        embed.add_field(name=f"🖼️ `{p}avatar` *(or just `avatar`)*", value="Display full-resolution avatar of yourself or a mentioned member.", inline=False)
        embed.add_field(name=f"🧹 `{p}clear <1-100>` *(or just `clear`)*", value="Purge messages from the current channel (Manage Messages required).", inline=False)
        embed.set_footer(text="✨ Tip: Whitelisted commands can be typed directly without '$'")
        return embed

    else:
        # Minimalist Sleek Aizen Home Screen
        embed = discord.Embed(
            title="⚔️ ── SŌSUKE AIZEN | THE THRONE ── ⚔️",
            description=(
                f"*\"No one stands on the heavens from the beginning.\"*\n\n"
                f"> **Prefix**: `{p}` *(or no-prefix for shortcuts)*  •  **Status**: `Online 24/7`\n\n"
                f"Select a category from the dropdown menu below to view commands:\n\n"
                f"• 🛒 **Auto-Shop**: Buy boosts with multi-crypto, redeem keys & credits\n"
                f"• 🚀 **Server Boosting**: Direct boosting & interactive panel\n"
                f"• 🪙 **Crypto & Wallets**: LTC, USDT, BTC, SOL live check & pricing\n"
                f"• 🎫 **Tickets**: Advanced consultation tickets with topics\n"
                f"• 🛠️ **Utility & Info**: Ping, uptime, serverinfo, userinfo, avatar, clear\n"
                f"• 👑 **Owner Admin**: Restock, gift codes, discounts & users"
            ),
            color=AIZEN_COLOR
        )
        embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine | Select a module below")
        return embed

class HelpDropdown(Select):
    def __init__(self, p: str):
        self.p = p
        options = [
            discord.SelectOption(label="Home Overview", value="home", emoji="🏠", description="Return to the minimal home overview"),
            discord.SelectOption(label="Auto-Shop & Purchasing", value="shop", emoji="🛒", description="Commands for buying, redeeming & credits"),
            discord.SelectOption(label="Server Boosting", value="boost", emoji="🚀", description="Commands for boosting Discord servers"),
            discord.SelectOption(label="Crypto & Wallets", value="wallet", emoji="🪙", description="Multi-crypto wallet inspection & pricing"),
            discord.SelectOption(label="Tickets & Support", value="tickets", emoji="🎫", description="Consultation tickets with topic selection"),
            discord.SelectOption(label="Utility & Tools", value="utility", emoji="🛠️", description="Ping, uptime, serverinfo, userinfo, avatar, clear"),
            discord.SelectOption(label="Owner Administration", value="admin", emoji="👑", description="Bulk restock, gift codes, discounts & users")
        ]
        super().__init__(placeholder="📂 Select a module to explore...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        embed = get_modular_help_embed(selected, self.p)
        await interaction.response.edit_message(embed=embed, view=self.view)

class ModularHelpView(View):
    def __init__(self, p: str):
        super().__init__(timeout=300)
        self.add_item(HelpDropdown(p))

@bot.command(name="help")
@commands.cooldown(1, 3, commands.BucketType.user)
async def cmd_help(ctx: commands.Context):
    """Show clean minimalist home screen with interactive dropdown."""
    embed = get_modular_help_embed("home", prefix)
    view = ModularHelpView(prefix)
    await ctx.send(embed=embed, view=view)

# ==========================================
# Discord Application Slash Commands Tree
# ==========================================

@bot.tree.command(name="shoppanel", description="Deploy the all-in-one visual Aizen Shop Panel")
async def slash_shoppanel(interaction: discord.Interaction):
    t1m = len(getStock("data/1m.txt") or [])
    t3m = len(getStock("data/3m.txt") or [])
    stats = await get_reviews_stats_db()

    embed = discord.Embed(
        title="⚔️ ── SŌSUKE AIZEN | THE THRONE ── ⚔️",
        description=(
            f"*\"No one stands on the heavens from the beginning. Neither you, nor I, not even God.\"*\n\n"
            f"Welcome to the **Official Discord Server Boosting & Services Portal**.\n"
            f"Instant automated delivery, multi-crypto payments, and 24/7 reliability.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**💎 Available Products**:\n"
            f"◈ **1-Month Boosts**: Level 1 (2x) • Level 2 (7x) • Level 3 (14x)\n"
            f"◈ **3-Month Boosts**: Long-term boost packages\n\n"
            f"**🪙 Supported Crypto**: `LTC` • `USDT` • `BTC` • `SOL`\n"
            f"**📦 Live Stock**: `{t1m * 2}` 1m Boosts | `{t3m * 2}` 3m Boosts\n"
            f"**⭐ Customer Rating**: `⭐ {stats['average_rating']} / 5.0` (`{stats['total_reviews']}` Verified Vouches)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Click a button below to begin your purchase or open a consultation ticket."
        ),
        color=AIZEN_COLOR
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine | 100% Automated")
    view = ShopPanelView()
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="buy", description="Generate an automated multi-crypto invoice for server boosts")
@app_commands.describe(
    duration="Boost duration (1m or 3m)",
    amount="Number of boosts (must be an even number: 2, 4, 14...)",
    crypto="Cryptocurrency to pay with",
    invite="Target Discord invite for instant delivery (optional)",
    discount="Promotional discount code (optional)"
)
@app_commands.choices(
    duration=[
        app_commands.Choice(name="1 Month", value="1m"),
        app_commands.Choice(name="3 Months", value="3m"),
    ],
    crypto=[
        app_commands.Choice(name="Litecoin (LTC)", value="ltc"),
        app_commands.Choice(name="Tether USDT (TRC20)", value="usdt"),
        app_commands.Choice(name="Bitcoin (BTC)", value="btc"),
        app_commands.Choice(name="Solana (SOL)", value="sol"),
    ]
)
async def slash_buy(
    interaction: discord.Interaction,
    duration: app_commands.Choice[str],
    amount: int,
    crypto: app_commands.Choice[str],
    invite: Optional[str] = None,
    discount: Optional[str] = None
):
    if amount <= 0 or amount % 2 != 0:
        return await interaction.response.send_message("❌ Amount must be an even positive number (2 boosts per token).", ephemeral=True)
    await generate_crypto_invoice(interaction, duration.value, amount, crypto.value, invite, discount)

@bot.tree.command(name="balance", description="Inspect your available Discord server boost credits")
async def slash_balance(interaction: discord.Interaction):
    bal = get_user_balance(interaction.user.id)
    embed = discord.Embed(
        title=f"💳 Balance Overview — {interaction.user.name}",
        description=(
            f"*\"Admiration is the emotion furthest from understanding.\"*\n\n"
            f"◈ **1-Month Boost Credits**: `{bal['1m']}` boosts\n"
            f"◈ **3-Month Boost Credits**: `{bal['3m']}` boosts\n\n"
            f"Use `/boost` to apply boosts to any server!"
        ),
        color=AIZEN_COLOR
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="stock", description="Inspect real-time Nitro token stock and pricing")
async def slash_stock(interaction: discord.Interaction):
    t1m = len(getStock("data/1m.txt") or [])
    t3m = len(getStock("data/3m.txt") or [])
    embed = discord.Embed(
        title="📦 Real-Time Nitro Token Stock",
        description=(
            f"◈ **1-Month Tokens**: `{t1m}` tokens (`{t1m * 2}` boosts available)\n"
            f"◈ **3-Month Tokens**: `{t3m}` tokens (`{t3m * 2}` boosts available)\n\n"
            f"**Supported Payment Cryptos**:\n"
            f"• 🪙 Litecoin (LTC) • 💵 Tether (USDT) • ₿ Bitcoin (BTC) • 🟣 Solana (SOL)"
        ),
        color=AIZEN_COLOR
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="redeem", description="Redeem an instant delivery boost code to claim credits")
@app_commands.describe(code="The boost key to redeem (e.g. BOOST-1M-2X-ABCD-1234)")
async def slash_redeem(interaction: discord.Interaction, code: str):
    success, msg, key_obj = redeem_boost_key(code.strip(), interaction.user.id)
    color = AIZEN_ACCENT if success else discord.Color.red()
    embed = discord.Embed(
        title="🔑 Key Redemption",
        description=msg,
        color=color
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ticket", description="Open a private support or consultation ticket")
async def slash_ticket(interaction: discord.Interaction):
    view = TicketTopicLaunchView(bot, HARDCODED_OWNERS)
    embed = discord.Embed(
        title="⚔️ Consultation & Support Desk",
        description="Select a topic below to establish a private channel with our staff.",
        color=AIZEN_COLOR
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="vouch", description="Submit a verified customer review and vouch")
async def slash_vouch(interaction: discord.Interaction):
    await interaction.response.send_modal(CustomerReviewModal())

@bot.tree.command(name="reviews", description="View overall satisfaction stats and customer vouches")
async def slash_reviews(interaction: discord.Interaction):
    stats = await get_reviews_stats_db()
    recent = await get_recent_reviews_db(limit=5)

    desc = (
        f"*\"Admiration is the emotion furthest from understanding.\"*\n\n"
        f"◈ **Overall Satisfaction**: `⭐ {stats['average_rating']} / 5.0`\n"
        f"◈ **Total Verified Vouches**: `{stats['total_reviews']}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Latest Customer Reviews**:\n"
    )
    if recent:
        for r in recent:
            stars = "⭐" * r.get("rating", 5)
            desc += f"• **{r.get('user_name', 'Customer')}** ({stars}):\n  *{r.get('comment', 'Great service!')}*\n\n"
    else:
        desc += "*No reviews yet. Be the first to leave a review using `/vouch`!*\n"

    embed = discord.Embed(
        title="⭐ Sōsuke Aizen Customer Reviews & Vouches",
        description=desc,
        color=AIZEN_COLOR
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine | 100% Automated")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Check bot latency, API roundtrip, and system health")
async def slash_ping(interaction: discord.Interaction):
    start_time = time.time()
    await interaction.response.defer()
    api_latency = round((time.time() - start_time) * 1000)
    ws_latency = round(bot.latency * 1000)

    embed = discord.Embed(
        title="🏓 Pong! — Sōsuke Aizen System Status",
        description="*\"No one stands on the heavens from the beginning.\"*",
        color=AIZEN_ACCENT
    )
    embed.add_field(name="⚡ Gateway Latency", value=f"`{ws_latency}ms`", inline=True)
    embed.add_field(name="🌐 API Roundtrip", value=f"`{api_latency}ms`", inline=True)
    embed.add_field(name="⏱️ System Uptime", value=f"`{get_uptime_str()}`", inline=True)
    embed.add_field(name="☁️ System Status", value="`Operational (24/7 Active)`", inline=True)
    embed.add_field(name="🗄️ Database Engine", value="`Supabase PostgreSQL`" if is_db_connected() else "`Resilient Storage`", inline=True)
    embed.add_field(name="🛡️ Security Level", value="`Hardened & Active`", inline=True)
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="uptime", description="Check continuous 24/7 online duration")
async def slash_uptime(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⏱️ Continuous Uptime Monitor",
        description=(
            f"*\"Since when were you under the impression...\"*\n\n"
            f"◈ **Online Duration**: `{get_uptime_str()}`\n"
            f"◈ **24/7 High-Availability**: `Active & Operational`\n"
            f"◈ **Connected Servers**: `{len(bot.guilds)}`"
        ),
        color=AIZEN_COLOR
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="serverinfo", description="Inspect current server statistics, boost tier, and members")
async def slash_serverinfo(interaction: discord.Interaction):
    if not interaction.guild:
        return await interaction.response.send_message("❌ This command must be used within a server.", ephemeral=True)
    g = interaction.guild
    embed = discord.Embed(
        title=f"🏰 {g.name} — Server Overview",
        description=f"Server ID: `{g.id}`\nOwner: <@{g.owner_id}>",
        color=AIZEN_COLOR
    )
    if g.icon:
        embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name="👥 Members", value=f"`{g.member_count}` total", inline=True)
    embed.add_field(name="🚀 Boost Level", value=f"Level `{g.premium_tier}` ({g.premium_subscription_count} boosts)", inline=True)
    embed.add_field(name="📜 Channels", value=f"`{len(g.channels)}` channels", inline=True)
    embed.add_field(name="🎭 Roles", value=f"`{len(g.roles)}` roles", inline=True)
    embed.add_field(name="📅 Created At", value=f"`{g.created_at.strftime('%Y-%m-%d')}`", inline=True)
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="userinfo", description="Inspect user profile and available boost credit balance")
@app_commands.describe(user="The user to inspect (defaults to yourself)")
async def slash_userinfo(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    u = user or interaction.user
    bal = get_user_balance(u.id)
    embed = discord.Embed(
        title=f"👤 {u.name} — User Profile",
        color=AIZEN_COLOR
    )
    embed.set_thumbnail(url=u.display_avatar.url)
    embed.add_field(name="Identity", value=f"Name: `{u.name}`\nID: `{u.id}`\nMention: {u.mention}", inline=True)
    embed.add_field(name="💳 Boost Credits", value=f"• 1-Month: `{bal['1m']}`\n• 3-Month: `{bal['3m']}`", inline=True)
    embed.add_field(name="📅 Account Created", value=f"`{u.created_at.strftime('%Y-%m-%d')}`", inline=False)
    if is_owner(u):
        embed.add_field(name="👑 Authorization", value="`👑 Throne Owner (Unlimited Access)`", inline=False)
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="botinfo", description="Display bot engine specifications and live stats")
async def slash_botinfo(interaction: discord.Interaction):
    t1m = len(getStock("data/1m.txt") or [])
    t3m = len(getStock("data/3m.txt") or [])
    embed = discord.Embed(
        title="⚔️ SŌSUKE AIZEN | THE THRONE ENGINE",
        description=(
            f"*\"No one stands on the heavens from the beginning. Neither you, nor I, not even God.\"*\n\n"
            f"◈ **Engine**: `Kyōka Suigetsu v3.0`\n"
            f"◈ **Uptime**: `{get_uptime_str()}`\n"
            f"◈ **Web Latency**: `{round(bot.latency * 1000)}ms`\n"
            f"◈ **Active Servers**: `{len(bot.guilds)}`\n"
            f"◈ **Available Stock**: `{t1m * 2}` 1m Boosts | `{t3m * 2}` 3m Boosts\n"
            f"◈ **System Status**: `Operational (24/7 Active)`\n"
            f"◈ **Database**: `{'Supabase PostgreSQL' if is_db_connected() else 'Resilient Storage'}`\n"
            f"◈ **Owners**: `{', '.join(str(o) for o in HARDCODED_OWNERS)}`"
        ),
        color=AIZEN_COLOR
    )
    if bot.user.avatar:
        embed.set_thumbnail(url=bot.user.avatar.url)
    embed.set_footer(text="Automated Multi-Crypto Boosting & Shop Bot")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="avatar", description="View high-resolution avatar image of yourself or another member")
@app_commands.describe(user="The member whose avatar to view")
async def slash_avatar(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    u = user or interaction.user
    embed = discord.Embed(title=f"🖼️ {u.name}'s Avatar", color=AIZEN_COLOR)
    embed.set_image(url=u.display_avatar.url)
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="clear", description="Purge recent channel messages (Manage Messages required)")
@app_commands.describe(amount="Number of messages to purge (1-100)")
async def slash_clear(interaction: discord.Interaction, amount: int = 10):
    if not interaction.user.guild_permissions.manage_messages and not is_owner(interaction.user):
        return await interaction.response.send_message("❌ Manage Messages permission required.", ephemeral=True)
    if amount <= 0 or amount > 100:
        return await interaction.response.send_message("❌ Amount must be between 1 and 100.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 Cleaned `{len(deleted)}` messages.", ephemeral=True)

@bot.tree.command(name="wallets", description="Inspect active cryptocurrency receiving wallet addresses")
async def slash_wallets(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    wallets = [
        ("🪙 Litecoin (LTC)", "ltc", get_address_for_crypto("ltc")),
        ("💵 Tether (USDT TRC20)", "usdt", get_address_for_crypto("usdt")),
        ("₿ Bitcoin (BTC)", "btc", get_address_for_crypto("btc")),
        ("🟣 Solana (SOL)", "sol", get_address_for_crypto("sol"))
    ]
    embed = discord.Embed(
        title="🪙 Sōsuke Aizen — Multi-Crypto Receiving Wallets",
        description="Active addresses receiving automated payments:",
        color=AIZEN_COLOR
    )
    for name, code, addr in wallets:
        info = get_wallet_live_info(code, addr)
        val = f"```{addr}```\n" + (f"• **Balance**: `{info.get('balance')}`\n" if info.get('balance') else "")
        embed.add_field(name=name, value=val, inline=False)
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="stats", description="View overall shop metrics, completed orders, and crypto volume")
async def slash_stats(interaction: discord.Interaction):
    stats = get_sales_stats()
    embed = discord.Embed(
        title="📊 Sōsuke Aizen — Commercial Analytics",
        description="Automated shop order analytics:",
        color=AIZEN_COLOR
    )
    embed.add_field(name="📦 Total Orders", value=f"`{stats['total_orders']}`", inline=True)
    embed.add_field(name="✅ Paid Orders", value=f"`{stats['paid_orders']}`", inline=True)
    embed.add_field(name="🚀 Boosts Delivered", value=f"`{stats['total_boosts_sold']}` boosts", inline=True)
    c_rev = stats.get("crypto_revenue", {})
    vol_lines = [f"• **{c.upper()}**: `{round(amt, 6)}`" for c, amt in c_rev.items() if amt > 0]
    embed.add_field(name="💰 Crypto Volume", value="\n".join(vol_lines) if vol_lines else "`None yet`", inline=False)
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Open the interactive modular Aizen help menu")
async def slash_help(interaction: discord.Interaction):
    embed = get_modular_help_embed("home", prefix)
    view = ModularHelpView(prefix)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="setreviewchannel", description="Set the channel where customer reviews are auto-posted (Admin only)")
@app_commands.describe(channel="The channel for reviews and vouches")
async def slash_setreviewchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator and not is_owner(interaction.user):
        return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    await set_setting_db(f"guild_{interaction.guild.id}_review_channel", str(channel.id))
    await set_setting_db("review_channel_id", str(channel.id))
    embed = discord.Embed(
        title="⭐ Review & Vouch Channel Configured",
        description=f"✅ Customer reviews and vouches will now automatically post to {channel.mention}.",
        color=AIZEN_ACCENT
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="addcredits", description="Manually add boost credits to a user (Owner Only)")
@app_commands.describe(user="The user to credit", duration="1m or 3m", amount="Amount of boosts")
@app_commands.choices(duration=[app_commands.Choice(name="1 Month", value="1m"), app_commands.Choice(name="3 Months", value="3m")])
async def slash_addcredits(interaction: discord.Interaction, user: discord.Member, duration: app_commands.Choice[str], amount: int):
    if not is_owner(interaction.user):
        return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
    new_bal = add_user_balance(user.id, duration.value, amount)
    await interaction.response.send_message(f"✅ Added `{amount}`x {duration.value} boosts to {user.mention}. New Balance: `{new_bal[duration.value]}`", ephemeral=True)

@bot.tree.command(name="removecredits", description="Manually remove boost credits from a user (Owner Only)")
@app_commands.describe(user="The user to deduct from", duration="1m or 3m", amount="Amount of boosts")
@app_commands.choices(duration=[app_commands.Choice(name="1 Month", value="1m"), app_commands.Choice(name="3 Months", value="3m")])
async def slash_removecredits(interaction: discord.Interaction, user: discord.Member, duration: app_commands.Choice[str], amount: int):
    if not is_owner(interaction.user):
        return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
    deduct_user_balance(user.id, duration.value, amount)
    bal = get_user_balance(user.id)
    await interaction.response.send_message(f"✅ Removed `{amount}`x {duration.value} boosts from {user.mention}. New Balance: `{bal[duration.value]}`", ephemeral=True)

@bot.tree.command(name="createcode", description="Generate a redeemable boost gift code (Owner Only)")
@app_commands.describe(duration="1m or 3m", amount="Amount of boosts")
@app_commands.choices(duration=[app_commands.Choice(name="1 Month", value="1m"), app_commands.Choice(name="3 Months", value="3m")])
async def slash_createcode(interaction: discord.Interaction, duration: app_commands.Choice[str], amount: int):
    if not is_owner(interaction.user):
        return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
    key_str = generate_boost_key(duration.value, amount, f"owner:{interaction.user.id}")
    await interaction.response.send_message(f"🎁 **Gift Key Created**: `{key_str}` (`{amount}x {duration.value}`)", ephemeral=True)

@bot.tree.command(name="creatediscount", description="Create a promotional discount code (Owner Only)")
@app_commands.describe(code="Promo code (e.g. SAVE10)", percent="Percentage discount (e.g. 10)")
async def slash_creatediscount(interaction: discord.Interaction, code: str, percent: float):
    if not is_owner(interaction.user):
        return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
    create_discount(code.strip().upper(), percent)
    await interaction.response.send_message(f"🏷️ Discount code `{code.strip().upper()}` created for `{percent}%` off.", ephemeral=True)

@bot.tree.command(name="confirmorder", description="Force-approve and deliver an invoice manually (Owner Only)")
@app_commands.describe(invoice_id="The invoice ID to approve")
async def slash_confirmorder(interaction: discord.Interaction, invoice_id: str):
    if not is_owner(interaction.user):
        return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
    success, msg, inv = force_complete_invoice(invoice_id.strip())
    await interaction.response.send_message(f"{'✅' if success else '❌'} {msg}", ephemeral=True)

@bot.tree.command(name="cancelorder", description="Cancel a pending invoice")
@app_commands.describe(invoice_id="The invoice ID to cancel")
async def slash_cancelorder(interaction: discord.Interaction, invoice_id: str):
    success, msg = cancel_invoice(invoice_id.strip(), interaction.user.id, is_owner(interaction.user))
    await interaction.response.send_message(f"{'✅' if success else '❌'} {msg}", ephemeral=True)

@bot.tree.command(name="ticketpanel", description="Deploy the permanent consultation ticket panel (Owner Only)")
async def slash_ticketpanel(interaction: discord.Interaction):
    if not is_owner(interaction.user):
        return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
    embed = discord.Embed(
        title="🎫 ── AIZEN CONSULTATION & ASSISTANCE ── 🎫",
        description=(
            f"*\"Admiration is the emotion furthest from understanding.\"*\n\n"
            f"Need assistance, bulk boost packages, or custom payment options?\n"
            f"Select a topic from the dropdown below to create a private ticket."
        ),
        color=AIZEN_COLOR
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    view = TicketTopicLaunchView(bot, HARDCODED_OWNERS)
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ Ticket panel deployed.", ephemeral=True)

@bot.tree.command(name="usedtokens", description="View count of archived used tokens (Owner Only)")
async def slash_usedtokens(interaction: discord.Interaction):
    if not is_owner(interaction.user):
        return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
    count = 0
    if os.path.exists(USED_TOKENS_FILE):
        with open(USED_TOKENS_FILE, "r", encoding="utf-8") as f:
            count = len([l for l in f.read().splitlines() if l.strip()])
    await interaction.response.send_message(f"🗄️ Total tokens moved to archive: `{count}` tokens.", ephemeral=True)

@bot.tree.command(name="setprice", description="Update crypto pricing for boost packages (Owner Only)")
@app_commands.describe(duration="1m or 3m", coin="ltc, usdt, btc, or sol", price="New price per token")
@app_commands.choices(
    duration=[app_commands.Choice(name="1 Month", value="1m"), app_commands.Choice(name="3 Months", value="3m")],
    coin=[
        app_commands.Choice(name="LTC", value="ltc"),
        app_commands.Choice(name="USDT", value="usdt"),
        app_commands.Choice(name="BTC", value="btc"),
        app_commands.Choice(name="SOL", value="sol"),
    ]
)
async def slash_setprice(interaction: discord.Interaction, duration: app_commands.Choice[str], coin: app_commands.Choice[str], price: float):
    if not is_owner(interaction.user):
        return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
    if price <= 0:
        return await interaction.response.send_message("❌ Price must be positive.", ephemeral=True)
    from payment import update_crypto_rate
    update_crypto_rate(coin.value, duration.value, price)
    await interaction.response.send_message(f"✅ Updated `{duration.value}` price for `{coin.name}` to `{price}` per token.", ephemeral=True)

@bot.tree.command(name="setaddress", description="Update receiving crypto wallet address (Owner Only)")
@app_commands.describe(coin="ltc, usdt, btc, or sol", address="Your crypto wallet address")
@app_commands.choices(
    coin=[
        app_commands.Choice(name="LTC", value="ltc"),
        app_commands.Choice(name="USDT (TRC20)", value="usdt"),
        app_commands.Choice(name="BTC", value="btc"),
        app_commands.Choice(name="SOL", value="sol"),
    ]
)
async def slash_setaddress(interaction: discord.Interaction, coin: app_commands.Choice[str], address: str):
    if not is_owner(interaction.user):
        return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
    from payment import set_crypto_address
    set_crypto_address(coin.value, address.strip())
    await interaction.response.send_message(f"✅ Updated receiving address for `{coin.name}` to:\n```{address.strip()}```", ephemeral=True)

@bot.tree.command(name="orders", description="View your past purchase history and receipt keys")
async def slash_orders(interaction: discord.Interaction):
    invs = get_user_invoices(interaction.user.id)
    if not invs:
        return await interaction.response.send_message("📦 You haven't placed any orders yet. Use `/buy` to get started!", ephemeral=True)

    vip = get_user_vip_tier(interaction.user.id)
    embed = discord.Embed(
        title=f"📜 Order History — {interaction.user.name}",
        description=f"**Loyalty Tier**: `{vip['tier_name']}` • **Total Boosts**: `{vip['total_boosts']}`\n\nRecent orders and receipt keys:",
        color=AIZEN_COLOR
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    for inv in invs[:5]:
        ts = time.strftime('%Y-%m-%d %H:%M', time.gmtime(inv.get('created_at', time.time())))
        status = str(inv.get('status', 'pending')).upper()
        c_name = str(inv.get('crypto', 'LTC')).upper()
        amt = inv.get('amount', inv.get('ltc_amount', 0.0))
        code = inv.get('redeem_key') or "Pending Confirmation"
        embed.add_field(
            name=f"Order `{inv['id']}` • {ts} UTC",
            value=(
                f"◈ **Product**: `{inv.get('boosts', 2)}x {str(inv.get('duration', '1m')).upper()}`\n"
                f"◈ **Amount**: `{amt} {c_name}` • **Status**: `{status}`\n"
                f"◈ **Receipt Key**: `{code}`"
            ),
            inline=False
        )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Shop Engine")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="vip", description="Inspect VIP customer loyalty rank, perks, and discount tier")
@app_commands.describe(user="The member whose loyalty tier to inspect (defaults to yourself)")
async def slash_vip(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    u = user or interaction.user
    vip = get_user_vip_tier(u.id)
    bar_filled = int(vip['progress'] / 10)
    bar_str = "█" * bar_filled + "░" * (10 - bar_filled)

    embed = discord.Embed(
        title=f"💎 VIP Loyalty Card — {u.name}",
        description=(
            f"*\"Admiration is the emotion furthest from understanding.\"*\n\n"
            f"◈ **Current Tier**: **{vip['tier_name']}**\n"
            f"◈ **Active Perks**: `{vip['tier_perk']}`\n"
            f"◈ **Total Boosts Purchased**: `{vip['total_boosts']}` boosts\n"
            f"◈ **Completed Invoices**: `{vip['total_orders']}` orders\n\n"
            f"**Tier Progression**:\n"
            f"`[{bar_str}]` {vip['progress']}%\n"
            f"*{vip['next_tier']}*"
        ),
        color=AIZEN_ACCENT
    )
    embed.set_thumbnail(url=u.display_avatar.url)
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Loyalty Program")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="transfer", description="Transfer boost credits to a friend")
@app_commands.describe(user="The user to transfer credits to", duration="1m or 3m", amount="Amount of boosts to transfer")
@app_commands.choices(duration=[app_commands.Choice(name="1 Month", value="1m"), app_commands.Choice(name="3 Months", value="3m")])
async def slash_transfer(interaction: discord.Interaction, user: discord.Member, duration: app_commands.Choice[str], amount: int):
    success, msg = transfer_user_balance(interaction.user.id, user.id, duration.value, amount)
    color = AIZEN_ACCENT if success else discord.Color.red()
    embed = discord.Embed(title="🎁 Boost Credit Transfer", description=msg, color=color)
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Shop Engine")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard", description="View top buyers leaderboard by boost volume")
async def slash_leaderboard(interaction: discord.Interaction):
    top_list = get_top_buyers(10)
    if not top_list:
        return await interaction.response.send_message("📊 No purchase records found yet.", ephemeral=True)

    desc = "*\"No one stands on the heavens from the beginning.\"*\n\n**Top Customer Leaderboard**:\n\n"
    for idx, u in enumerate(top_list, 1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"`#{idx}`"
        desc += f"{medal} <@{u['user_id']}> — `{u['boosts']}` boosts (`{u['orders']}` orders)\n"

    embed = discord.Embed(
        title="🏆 Sōsuke Aizen — Top Customer Leaderboard",
        description=desc,
        color=AIZEN_COLOR
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Shop Engine")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="promos", description="View active promotional discount codes")
async def slash_promos(interaction: discord.Interaction):
    discs = list_active_discounts()
    if not discs:
        return await interaction.response.send_message("🏷️ There are currently no active public promo codes.", ephemeral=True)

    desc = "*Apply any code below during checkout for instant savings!*\n\n"
    for code, pct in discs.items():
        desc += f"• **`{code}`**: `{pct}%` OFF on all boost packages\n"

    embed = discord.Embed(
        title="🏷️ Active Promotional Discount Codes",
        description=desc,
        color=AIZEN_COLOR
    )
    embed.set_footer(text="Use in /buy under the discount field")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setlogchannel", description="Set channel where verified order receipts are auto-logged (Admin only)")
@app_commands.describe(channel="The channel for order logs")
async def slash_setlogchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator and not is_owner(interaction.user):
        return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    await set_setting_db(f"guild_{interaction.guild.id}_order_log_channel", str(channel.id))
    await set_setting_db("order_log_channel_id", str(channel.id))
    embed = discord.Embed(
        title="🛒 Order Log Channel Configured",
        description=f"✅ Verified order receipts will now automatically be logged to {channel.mention}.",
        color=AIZEN_ACCENT
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setup", description="Launch the 1-click interactive server setup wizard (Admin only)")
async def slash_setup(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator and not is_owner(interaction.user):
        return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    embed = discord.Embed(
        title="⚡ Sōsuke Aizen — 1-Click Server Setup Wizard",
        description=(
            f"*\"No one stands on the heavens from the beginning.\"*\n\n"
            f"Click **[⚡ 1-Click Instant Auto Deploy]** below to automatically create:\n"
            f"• `#🛒・shop` (Interactive visual shop panel)\n"
            f"• `#🎫・tickets` (Support & custom order consultation desk)\n"
            f"• `#⭐・vouches` (Automated customer review publishing)\n"
            f"• `#📋・order-logs` (Automated verified purchase receipts)\n\n"
            f"All channel permissions, categories, and database links will be configured automatically."
        ),
        color=AIZEN_ACCENT
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await interaction.response.send_message(embed=embed, view=SetupWizardView(), ephemeral=True)

@bot.tree.command(name="checkserver", description="Inspect any Discord server's current boost level, count, and needed boosts")
@app_commands.describe(invite="Discord invite link or code (e.g. discord.gg/example or example)")
async def slash_checkserver(interaction: discord.Interaction, invite: str):
    details = fetch_server_invite_details(invite)
    if not details:
        return await interaction.response.send_message("❌ Could not reach Discord server. Please verify the invite code is valid and active.", ephemeral=True)

    l1_status = "✅ Reached" if details["needed_l1"] == 0 else f"Need {details['needed_l1']} boosts"
    l2_status = "✅ Reached" if details["needed_l2"] == 0 else f"Need {details['needed_l2']} boosts"
    l3_status = "✅ Reached" if details["needed_l3"] == 0 else f"Need {details['needed_l3']} boosts"

    embed = discord.Embed(
        title=f"🏰 {details['name']} — Server Boost Inspection",
        description=(
            f"*\"Since when were you under the impression...\"*\n\n"
            f"◈ **Current Boost Tier**: `Level {details['tier']}`\n"
            f"◈ **Active Boosts**: `{details['boost_count']}` boosts\n"
            f"◈ **Server Members**: `{details['members']}` (`{details['online']}` online)\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**🎯 Progression & Quota Needed**:\n"
            f"{details['next_tier_desc']}\n\n"
            f"• **Level 1 (2 Boosts)**: {l1_status}\n"
            f"• **Level 2 (7 Boosts)**: {l2_status}\n"
            f"• **Level 3 (14 Boosts)**: {l3_status}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Use `/buy` to apply boosts directly to `.gg/{details['code']}`!"
        ),
        color=AIZEN_COLOR
    )
    if details.get("icon_url"):
        embed.set_thumbnail(url=details["icon_url"])
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="calc", description="Calculate multi-crypto pricing for any boost package")
@app_commands.describe(duration="1m or 3m", amount="Amount of boosts (must be an even number: 2, 4, 14...)", discount="Discount code (optional)")
@app_commands.choices(duration=[app_commands.Choice(name="1 Month", value="1m"), app_commands.Choice(name="3 Months", value="3m")])
async def slash_calc(interaction: discord.Interaction, duration: app_commands.Choice[str], amount: int, discount: Optional[str] = None):
    if amount <= 0 or amount % 2 != 0:
        return await interaction.response.send_message("❌ Amount must be an even positive number (2 boosts per token).", ephemeral=True)

    dur_clean = duration.value
    r_ltc = round(get_rate_for_crypto("ltc", dur_clean) * amount, 4)
    r_usdt = round(get_rate_for_crypto("usdt", dur_clean) * amount, 2)
    r_btc = round(get_rate_for_crypto("btc", dur_clean) * amount, 6)
    r_sol = round(get_rate_for_crypto("sol", dur_clean) * amount, 4)

    discount_pct = get_discount_percent(discount) if discount else 0.0
    if discount_pct > 0:
        r_ltc = round(r_ltc * (1 - discount_pct / 100), 4)
        r_usdt = round(r_usdt * (1 - discount_pct / 100), 2)
        r_btc = round(r_btc * (1 - discount_pct / 100), 6)
        r_sol = round(r_sol * (1 - discount_pct / 100), 4)

    t1m = len(getStock("data/1m.txt") or [])
    t3m = len(getStock("data/3m.txt") or [])
    tokens_needed = amount // 2
    stock_avail = t1m if dur_clean == "1m" else t3m
    stock_status = f"✅ In Stock ({stock_avail * 2} boosts available)" if stock_avail >= tokens_needed else f"⚠️ Low Stock ({stock_avail * 2} available)"

    embed = discord.Embed(
        title=f"🧮 Multi-Crypto Price Calculator — {amount}x {dur_clean.upper()}",
        description=(
            f"*\"Admiration is the emotion furthest from understanding.\"*\n\n"
            f"◈ **Package**: `{amount}`x {dur_clean.upper()} Discord Server Boosts\n"
            f"◈ **Tokens Required**: `{tokens_needed}` accounts\n"
            f"◈ **Stock Status**: {stock_status}\n"
            + (f"◈ **Discount Applied**: `{int(discount_pct)}% OFF` (`{discount}`)\n" if discount_pct else "")
            + f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Estimated Costs by Cryptocurrency**:\n"
            f"• 🪙 **Litecoin (LTC)**: **`{r_ltc} LTC`** *(Lowest network fees)*\n"
            f"• 💵 **Tether USDT**: **`${r_usdt} USDT`** *(Zero volatility)*\n"
            f"• ₿ **Bitcoin (BTC)**: **`{r_btc} BTC`**\n"
            f"• 🟣 **Solana (SOL)**: **`{r_sol} SOL`**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Type `/buy` to place your order!"
        ),
        color=AIZEN_COLOR
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Shop Engine")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="daily", description="Claim your daily streak reward for free discount codes and credits")
async def slash_daily(interaction: discord.Interaction):
    success, msg, streak, reward_type = await claim_daily_streak_db(interaction.user.id)
    if not success:
        return await interaction.response.send_message(msg, ephemeral=True)

    if streak == 7:
        discount_code = f"STREAK7-{interaction.user.id % 10000}"
        create_discount(discount_code, 15.0)
        add_user_balance(interaction.user.id, "1m", 2)
        reward_desc = f"🎉 **7-DAY STREAK COMPLETED!**\n• **2x 1-Month Boost Credits** added to your balance!\n• **15% OFF Promo Code**: `{discount_code}`"
    elif streak >= 5:
        discount_code = f"STREAK5-{interaction.user.id % 10000}"
        create_discount(discount_code, 10.0)
        reward_desc = f"🔥 **Day {streak} Streak!**\n• **10% OFF Promo Code**: `{discount_code}`"
    elif streak >= 3:
        discount_code = f"STREAK3-{interaction.user.id % 10000}"
        create_discount(discount_code, 5.0)
        reward_desc = f"⚡ **Day {streak} Streak!**\n• **5% OFF Promo Code**: `{discount_code}`"
    else:
        discount_code = f"STREAK-{interaction.user.id % 10000}"
        create_discount(discount_code, 3.0)
        reward_desc = f"🌱 **Day {streak} Streak!**\n• **3% OFF Promo Code**: `{discount_code}`"

    embed = discord.Embed(
        title=f"🎁 Daily Streak Claimed — Day {streak}/7",
        description=(
            f"*\"No one stands on the heavens from the beginning.\"*\n\n"
            f"{reward_desc}\n\n"
            f"Come back tomorrow to keep your streak alive and unlock higher rewards!"
        ),
        color=AIZEN_ACCENT
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Daily Loyalty")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="faq", description="Open the interactive Buyer's FAQ and Guide")
async def slash_faq(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 Sōsuke Aizen — Buyer's Knowledge Base & FAQ",
        description=(
            f"*\"Admiration is the emotion furthest from understanding.\"*\n\n"
            f"Select a topic from the dropdown menu below to learn how our automated boosting system works."
        ),
        color=AIZEN_COLOR
    )
    embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine")
    await interaction.response.send_message(embed=embed, view=FAQView())

@bot.tree.command(name="setprefix", description="Change the bot's command prefix for this server (Admin only)")
@app_commands.describe(prefix="New prefix (1-5 characters, e.g. ! or ?)")
async def slash_setprefix(interaction: discord.Interaction, prefix: str):
    if not interaction.user.guild_permissions.administrator and not is_owner(interaction.user):
        return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    if len(prefix) > 5:
        return await interaction.response.send_message("❌ Prefix must be between 1 and 5 characters.", ephemeral=True)

    _guild_prefixes[interaction.guild.id] = prefix
    await set_setting_db(f"guild_{interaction.guild.id}_prefix", prefix)
    embed = discord.Embed(
        title="⚙️ Server Prefix Updated",
        description=f"✅ Prefix for **{interaction.guild.name}** updated to: `{prefix}`",
        color=AIZEN_ACCENT
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="broadcast", description="Broadcast an announcement to all servers (Owner Only)")
@app_commands.describe(message="Announcement text to send")
async def slash_broadcast(interaction: discord.Interaction, message: str):
    if not is_owner(interaction.user):
        return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)

    embed = discord.Embed(
        title="📢 Sōsuke Aizen — Official Announcement",
        description=f"*\"No one stands on the heavens from the beginning.\"*\n\n{message}",
        color=AIZEN_ACCENT
    )
    embed.set_footer(text="Official Broadcast • Kyōka Suigetsu Engine")
    embed.timestamp = discord.utils.utcnow()

    sent = 0
    for guild in bot.guilds:
        target_ch = None
        shop_id = await get_setting_db(f"guild_{guild.id}_order_log_channel")
        if shop_id:
            try:
                target_ch = guild.get_channel(int(shop_id))
            except Exception:
                pass
        if not target_ch:
            for ch in guild.text_channels:
                if any(w in ch.name.lower() for w in ["announcements", "updates", "shop", "general"]):
                    if ch.permissions_for(guild.me).send_messages:
                        target_ch = ch
                        break
        if not target_ch:
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    target_ch = ch
                    break
        if target_ch:
            try:
                await target_ch.send(embed=embed)
                sent += 1
            except Exception:
                pass

    await interaction.followup.send(f"📢 Broadcast sent to `{sent}` servers.", ephemeral=True)




# ==========================================
# Main Startup
# ==========================================

def main():
    # 1. Start Render 24/7 Keep-Alive Web Service first so /healthz always responds
    keep_alive()

    global bot_token

    for env_key, filepath in [("TOKENS_1M", "data/1m.txt"), ("TOKENS_3M", "data/3m.txt")]:
        tokens_raw = os.environ.get(env_key, "").strip()
        if tokens_raw:
            os.makedirs("data", exist_ok=True)
            with open(filepath, "a", encoding="utf-8") as f:
                for line in tokens_raw.replace("\\n", "\n").splitlines():
                    if line.strip():
                        f.write(line.strip() + "\n")
            print(f" [+] Loaded tokens from {env_key} into {filepath}")

    if not bot_token:
        print("=" * 60)
        print(" [!] WARNING: BOT_TOKEN is not set yet!")
        print(" [!] Keep-alive web server is ACTIVE on /healthz for Render.")
        print(" [!] Add BOT_TOKEN in your Render Environment Variables to connect.")
        print("=" * 60)
        while not bot_token:
            time.sleep(10)
            bot_token = os.environ.get("BOT_TOKEN") or load_config().get("discord", {}).get("bot_token", "")

    print(" [*] Connecting to Discord...")
    try:
        bot.run(bot_token)
    except Exception as e:
        print(f" [!] Discord connection error: {e}")
        # Keep web server alive so Render doesn't loop restart
        while True:
            time.sleep(60)

if __name__ == "__main__":
    main()
