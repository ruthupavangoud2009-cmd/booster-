import os
import sys
import time
import yaml
import asyncio
import discord
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
    USED_TOKENS_FILE
)
from tickets import (
    TicketTopicLaunchView,
    TicketInsideControls,
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

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=prefix, intents=intents, help_command=None)

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
        if paid:
            self.stop()
            embed = interaction.message.embeds[0]
            embed.title = "⚔️ Payment Confirmed & Delivered!"
            embed.color = AIZEN_ACCENT
            embed.set_field_at(3, name="Status", value="`PAID & DELIVERED`", inline=False)
            await interaction.message.edit(embed=embed, view=None)

            code = inv.get("redeem_key", "Generated")
            dm_msg = f"⚔️ **Payment Verified!**\nYour redeemable code: `{code}`\nAdded `{inv['boosts']}`x `{inv['duration']}` boost credits to your balance!"

            try:
                await interaction.user.send(dm_msg)
            except Exception:
                pass

            await interaction.followup.send(f"🎉 **Payment Verified!**\nYour instant code: `{code}`\nUse `{prefix}boost <invite> {inv['boosts']} {inv['duration'].replace('m', '')}` to apply your boosts!", ephemeral=True)

            if inv.get("target_invite"):
                months_num = int(inv["duration"].replace("m", ""))
                deduct_user_balance(inv["user_id"], inv["duration"], inv["boosts"])
                await execute_boost(inv["target_invite"], inv["boosts"], months_num, inv["user_id"], interaction.channel)
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
        embed = interaction.message.embeds[0]
        embed.title = "❌ Payment Order Cancelled"
        embed.color = discord.Color.red()
        embed.set_field_at(3, name="Status", value="`CANCELLED`", inline=False)
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("✅ Order has been cancelled.", ephemeral=True)

class BoostLaunchView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🚀 Boost a Server", style=discord.ButtonStyle.primary, custom_id="boost_modal_btn")
    async def boost_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BoostModal())

# ==========================================
# Background Payment Poller
# ==========================================

async def auto_poll_invoice(invoice_id: str, message: discord.Message, channel: discord.abc.Messageable, user_id: int):
    """Periodically checks blockchain in background for 30 minutes."""
    for _ in range(60):
        await asyncio.sleep(30)
        try:
            paid, msg, inv = check_invoice_payment(invoice_id)
            if paid:
                if message and message.embeds:
                    embed = message.embeds[0]
                    embed.title = "⚔️ Payment Confirmed & Delivered!"
                    embed.color = AIZEN_ACCENT
                    embed.set_field_at(3, name="Status", value="`PAID & DELIVERED`", inline=False)
                    await message.edit(embed=embed, view=None)

                code = inv.get("redeem_key", "Generated")
                await channel.send(f"🎉 <@{user_id}> **Payment Confirmed for `{inv.get('amount', inv.get('ltc_amount'))} {inv.get('crypto', 'LTC').upper()}`!**\nYour redeem code: `{code}`\nAdded `{inv['boosts']}`x `{inv['duration']}` boost credits to your balance.")

                if inv.get("target_invite"):
                    months_num = int(inv["duration"].replace("m", ""))
                    deduct_user_balance(inv["user_id"], inv["duration"], inv["boosts"])
                    await execute_boost(inv["target_invite"], inv["boosts"], months_num, user_id, channel)
                break

            inv_data = get_invoice(invoice_id)
            if not inv_data or inv_data.get("status") != "pending":
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

    # Start background poller if LTC
    if c_clean == "ltc":
        asyncio.create_task(auto_poll_invoice(invoice['id'], msg, interaction.channel, interaction.user.id))

class CryptoSelect(Select):
    def __init__(self, duration: str, amount: int, invite: Optional[str] = None, discount: Optional[str] = None):
        self.duration = duration
        self.amount = amount
        self.invite = invite
        self.discount = discount
        options = [
            discord.SelectOption(label="Litecoin (LTC)", value="ltc", emoji="🪙", description="Lowest network fees • Instant auto-confirm"),
            discord.SelectOption(label="Tether USDT", value="usdt", emoji="💵", description="Stablecoin (Zero volatility)"),
            discord.SelectOption(label="Bitcoin (BTC)", value="btc", emoji="₿", description="The standard cryptocurrency"),
            discord.SelectOption(label="Solana (SOL)", value="sol", emoji="🟣", description="High-speed Solana network")
        ]
        super().__init__(placeholder="💎 Choose Your Payment Cryptocurrency...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        crypto = self.values[0]
        await generate_crypto_invoice(interaction, self.duration, self.amount, crypto, self.invite, self.discount)

class CryptoSelectionView(View):
    def __init__(self, duration: str, amount: int, invite: Optional[str] = None, discount: Optional[str] = None):
        super().__init__(timeout=180)
        self.add_item(CryptoSelect(duration, amount, invite, discount))

class BuyOrderModal(Modal):
    def __init__(self, duration: str):
        super().__init__(title=f"⚔️ Buy {duration.upper()} Boosts")
        self.duration = duration

        self.amount_input = TextInput(
            label="Amount of Boosts",
            placeholder="Must be an even number (e.g. 2, 4, 14)",
            required=True,
            max_length=4
        )
        self.add_item(self.amount_input)

        self.invite_input = TextInput(
            label="Server Invite (Optional for Auto-Boost)",
            placeholder="e.g. discord.gg/yourserver (boosts instantly upon payment)",
            required=False,
            max_length=60
        )
        self.add_item(self.invite_input)

        self.discount_input = TextInput(
            label="Promo / Discount Code (Optional)",
            placeholder="e.g. SUMMER10",
            required=False,
            max_length=20
        )
        self.add_item(self.discount_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount_input.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ Amount must be a valid number.", ephemeral=True)

        if amount <= 0 or amount % 2 != 0:
            return await interaction.response.send_message("❌ Amount must be an even positive number (2 boosts per token).", ephemeral=True)

        invite = self.invite_input.value.strip() or None
        discount = self.discount_input.value.strip().upper() or None

        embed = discord.Embed(
            title=f"⚔️ Sōsuke Aizen — Select Payment Currency",
            description=(
                f"*\"No one stands on the heavens from the beginning.\"*\n\n"
                f"◈ **Product**: `{amount}x {self.duration}` Boosts\n"
                f"◈ **Target**: `{invite or 'Credit to Account / Redeem Code'}`\n\n"
                f"Select your preferred cryptocurrency below to generate your invoice:"
            ),
            color=AIZEN_COLOR
        )
        view = CryptoSelectionView(self.duration, amount, invite, discount)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ==========================================
# All-in-One Persistent Shop Panel View
# ==========================================

class ShopPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🛒 Buy 1-Month Boosts", style=discord.ButtonStyle.primary, custom_id="shop_btn_buy_1m", row=0)
    async def btn_buy_1m(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BuyOrderModal("1m"))

    @discord.ui.button(label="🚀 Buy 3-Month Boosts", style=discord.ButtonStyle.primary, custom_id="shop_btn_buy_3m", row=0)
    async def btn_buy_3m(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BuyOrderModal("3m"))

    @discord.ui.button(label="🎫 Open Ticket", style=discord.ButtonStyle.success, custom_id="shop_btn_ticket", row=0)
    async def btn_ticket(self, interaction: discord.Interaction, button: Button):
        view = TicketTopicLaunchView(bot, HARDCODED_OWNERS)
        await interaction.response.send_message(
            "⚔️ **Select a ticket topic below to open your consultation channel:**",
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="💳 My Balance", style=discord.ButtonStyle.secondary, custom_id="shop_btn_bal", row=1)
    async def btn_bal(self, interaction: discord.Interaction, button: Button):
        bal = get_user_balance(interaction.user.id)
        embed = discord.Embed(
            title=f"💳 Balance — {interaction.user.name}",
            description=f"◈ **1-Month Boosts**: `{bal['1m']}` credits\n◈ **3-Month Boosts**: `{bal['3m']}` credits",
            color=AIZEN_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="📦 Live Stock", style=discord.ButtonStyle.secondary, custom_id="shop_btn_stock", row=1)
    async def btn_stock(self, interaction: discord.Interaction, button: Button):
        t1m = len(getStock("data/1m.txt") or [])
        t3m = len(getStock("data/3m.txt") or [])
        embed = discord.Embed(
            title="📦 Real-Time Stock Availability",
            description=f"◈ **1-Month Tokens**: `{t1m}` tokens (`{t1m * 2}` boosts)\n◈ **3-Month Tokens**: `{t3m}` tokens (`{t3m * 2}` boosts)",
            color=AIZEN_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
# Boosting Commands
# ==========================================

@bot.tree.command(name="boost", description="Open the Discord server booster panel")
async def slash_boost(interaction: discord.Interaction):
    await interaction.response.send_modal(BoostModal())

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
# Modular Multi-Crypto Buy Command
# ==========================================

@bot.command(name="buy")
@commands.cooldown(1, 3, commands.BucketType.user)
async def cmd_buy(ctx: commands.Context, duration: str = None, amount: int = None, crypto: str = None, *args):
    """
    Buy boosts with Litecoin, USDT, Bitcoin, or Solana.
    Usage:
      $buy 1m 2 ltc
      $buy 1m 2 usdt discord.gg/example
      $buy (opens modular selector modal)
    """
    if not duration or not amount:
        embed = discord.Embed(
            title="⚔️ Aizen Portal — Purchase Boost Credits",
            description=(
                f"*\"No one stands on the heavens from the beginning.\"*\n\n"
                f"**Select your duration below to configure your order**:\n"
                f"◈ Supported Coins: `🪙 LTC` • `💵 USDT` • `₿ BTC` • `🟣 SOL`\n"
                f"◈ Instant Delivery: Server invite can be included for auto-boosting!"
            ),
            color=AIZEN_COLOR
        )
        view = View()
        view.add_item(Button(label="🛒 Buy 1-Month", style=discord.ButtonStyle.primary, custom_id="quick_buy_1m"))
        view.add_item(Button(label="🚀 Buy 3-Month", style=discord.ButtonStyle.primary, custom_id="quick_buy_3m"))

        async def qb1_callback(interaction: discord.Interaction):
            await interaction.response.send_modal(BuyOrderModal("1m"))
        async def qb3_callback(interaction: discord.Interaction):
            await interaction.response.send_modal(BuyOrderModal("3m"))

        view.children[0].callback = qb1_callback
        view.children[1].callback = qb3_callback
        return await ctx.send(embed=embed, view=view)

    dur_clean = duration.lower().strip()
    if dur_clean not in ["1m", "3m"]:
        return await ctx.send("❌ Duration must be `1m` or `3m`.")

    if amount % 2 != 0 or amount <= 0:
        return await ctx.send("❌ Amount must be an even positive number (2, 4, 14, etc.).")

    # If crypto was not provided or was an invite, show crypto selection view
    target_crypto = crypto.lower().strip() if crypto and crypto.lower() in ["ltc", "usdt", "btc", "sol"] else None
    target_invite = None
    discount_code = None

    for arg in ([crypto] if crypto and crypto.lower() not in ["ltc", "usdt", "btc", "sol"] else []) + list(args):
        if "discord.gg" in arg or "discord.com" in arg or len(arg) > 4 and not arg.startswith("code:"):
            target_invite = arg
        elif arg.startswith("code:"):
            discount_code = arg.replace("code:", "").strip().upper()

    if not target_crypto:
        embed = discord.Embed(
            title=f"⚔️ Sōsuke Aizen — Choose Payment Currency",
            description=f"Order: `{amount}x {dur_clean}` Boosts.\nPlease select which cryptocurrency you want to pay with:",
            color=AIZEN_COLOR
        )
        view = CryptoSelectionView(dur_clean, amount, target_invite, discount_code)
        return await ctx.send(embed=embed, view=view)

    # Fake interaction adapter for text command
    class MsgInteraction:
        def __init__(self, context):
            self.user = context.author
            self.channel = context.channel
            self.response = type("Resp", (), {"is_done": lambda: True})()
            self.followup = type("Follow", (), {"send": lambda *a, **kw: context.send(*a, **kw)})()

    fake_interaction = MsgInteraction(ctx)
    await generate_crypto_invoice(fake_interaction, dur_clean, amount, target_crypto, target_invite, discount_code)

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

@bot.command(name="ping")
@commands.cooldown(1, 3, commands.BucketType.user)
async def cmd_ping(ctx: commands.Context):
    """Check bot responsiveness and gateway latency."""
    start_time = time.time()
    msg = await ctx.send("🏓 Pinging...")
    end_time = time.time()

    api_latency = round((end_time - start_time) * 1000)
    ws_latency = round(bot.latency * 1000)

    embed = discord.Embed(title="🏓 Pong!", color=AIZEN_ACCENT)
    embed.add_field(name="Gateway Latency", value=f"`{ws_latency}ms`", inline=True)
    embed.add_field(name="API Latency", value=f"`{api_latency}ms`", inline=True)
    embed.add_field(name="Security Status", value="`Hardened & Active`", inline=True)
    await msg.edit(content=None, embed=embed)

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

    else:
        # Minimalist Sleek Aizen Home Screen
        embed = discord.Embed(
            title="⚔️ ── SŌSUKE AIZEN | THE THRONE ── ⚔️",
            description=(
                f"*\"No one stands on the heavens from the beginning.\"*\n\n"
                f"> **Prefix**: `{p}`  •  **Status**: `Online 24/7`  •  **Security**: `Active`\n\n"
                f"Select a category from the dropdown menu below to view commands:\n\n"
                f"• 🛒 **Auto-Shop**: Buy boosts with multi-crypto, redeem keys & credits\n"
                f"• 🚀 **Server Boosting**: Direct boosting & interactive panel\n"
                f"• 🪙 **Crypto & Wallets**: LTC, USDT, BTC, SOL live check & pricing\n"
                f"• 🎫 **Tickets**: Advanced consultation tickets with topics\n"
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
# Main Startup
# ==========================================

def main():
    if not bot_token:
        print("\n [!] ERROR: No bot token found!")
        print(" [!] Please set BOT_TOKEN environment variable or set 'bot_token' in config/config.yaml.")
        print(" [!] Example: bot_token: \"MTI...\"\n")
        if not os.environ.get("RENDER"):
            input(" Press Enter to exit...")
        sys.exit(1)

    keep_alive()

    for env_key, filepath in [("TOKENS_1M", "data/1m.txt"), ("TOKENS_3M", "data/3m.txt")]:
        tokens_raw = os.environ.get(env_key, "").strip()
        if tokens_raw:
            os.makedirs("data", exist_ok=True)
            with open(filepath, "a", encoding="utf-8") as f:
                for line in tokens_raw.replace("\\n", "\n").splitlines():
                    if line.strip():
                        f.write(line.strip() + "\n")
            print(f" [+] Loaded tokens from {env_key} into {filepath}")

    print(" [*] Connecting to Discord...")
    bot.run(bot_token)

if __name__ == "__main__":
    main()
