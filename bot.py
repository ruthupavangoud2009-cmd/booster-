import os
import sys
import time
import yaml
import asyncio
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select

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
    generate_boost_key,
    redeem_boost_key,
    get_wallet_live_info,
    create_discount,
    get_discount_percent,
    get_sales_stats,
    list_all_keys,
    USED_TOKENS_FILE
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

# LTC Configuration
ltc_config = config.get("ltc", {})
ltc_address = os.environ.get("LTC_ADDRESS") or ltc_config.get("address", "").strip()
price_1m = float(os.environ.get("PRICE_1M") or ltc_config.get("price_per_boost_1m", 0.25))
price_3m = float(os.environ.get("PRICE_3M") or ltc_config.get("price_per_boost_3m", 0.50))

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=prefix, intents=intents, help_command=None)

# ==========================================
# Core Boosting Helper
# ==========================================

async def execute_boost(invite_str: str, amount: int, months: int, user_id: int, channel: discord.abc.Messageable):
    """Executes the full boosting process and handles stock removal and token archiving."""
    dur_key = f"{months}m"
    invite_code = getinviteCode(invite_str)
    guild_id = checkInvite(invite_code)

    if not guild_id:
        return await channel.send(embed=discord.Embed(
            title="❌ Invalid Invite",
            description=f"Could not reach server with invite code: `.gg/{invite_code}`",
            color=0xFF0000
        ))

    filename = "data/1m.txt" if months == 1 else "data/3m.txt"
    stock = getStock(filename) or []
    required_tokens = int(amount / 2)

    if required_tokens > len(stock):
        return await channel.send(embed=discord.Embed(
            title="❌ Stock Empty",
            description=f"The bot is temporarily out of stock! Need `{required_tokens}` tokens, but only `{len(stock)}` available in `{filename}`.",
            color=0xFF0000
        ))

    tokens_to_use = stock[:required_tokens]
    for token in tokens_to_use:
        remove(token, filename)

    status_msg = await channel.send(embed=discord.Embed(
        title="⏳ Instant Boosting in Progress...",
        description=f"Applying `{amount}` boosts to **.gg/{invite_code}** using `{required_tokens}` tokens...\nPlease wait.",
        color=0xFEE75C
    ))

    session_folder = create_session_folder()
    booster = Booster(session_folder)
    start_time = time.time()

    def do_boost():
        return booster.thread(invite_code, tokens_to_use, guild_id)

    status = await asyncio.to_thread(do_boost)
    elapsed = round(time.time() - start_time, 2)

    # Archive used tokens so they never mix with stock
    archive_used_tokens(tokens_to_use, dur_key, invite_code)

    success_count = len(status.get("success", [])) * 2 if isinstance(status, dict) else 0
    failed_count = len(status.get("failed", [])) * 2 if isinstance(status, dict) else 0

    result_embed = discord.Embed(
        title="✅ Instant Boosting Complete",
        description=f"Finished boosting **.gg/{invite_code}** in `{elapsed}s`.",
        color=0x57F287 if success_count > 0 else 0xED4245
    )
    result_embed.add_field(name="Successful Boosts", value=f"`{success_count}` applied", inline=True)
    result_embed.add_field(name="Failed Boosts", value=f"`{failed_count}` failed", inline=True)
    result_embed.add_field(name="Tokens Used & Archived", value=f"`{required_tokens}` tokens", inline=True)
    result_embed.set_footer(text="BoostBot Crafted by .gg/coderz")

    await status_msg.edit(embed=result_embed)

# ==========================================
# Payment View with Interactive Buttons
# ==========================================

class PaymentView(View):
    def __init__(self, invoice_id: str, ltc_addy: str, expected_ltc: float):
        super().__init__(timeout=3600)
        self.invoice_id = invoice_id
        self.ltc_addy = ltc_addy
        self.expected_ltc = expected_ltc

    @discord.ui.button(label="🔄 Check Payment", style=discord.ButtonStyle.success, custom_id="btn_check_pay")
    async def check_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        paid, msg, inv = check_invoice_payment(self.invoice_id)
        if paid:
            self.stop()
            embed = interaction.message.embeds[0]
            embed.title = "✅ Payment Confirmed & Delivered!"
            embed.color = 0x57F287
            embed.set_field_at(3, name="Status", value="`PAID & DELIVERED`", inline=False)
            await interaction.message.edit(embed=embed, view=None)

            code = inv.get("redeem_key", "Generated")
            dm_msg = f"🎉 **Payment Verified!**\nYour redeemable code: `{code}`\nAdded `{inv['boosts']}`x `{inv['duration']}` boost credits to your balance!"

            # Try to DM buyer with their code
            try:
                await interaction.user.send(dm_msg)
            except Exception:
                pass

            await interaction.followup.send(f"🎉 **Payment Verified!**\nYour instant code: `{code}`\nUse `{prefix}boost <invite> {inv['boosts']} {inv['duration'].replace('m', '')}` to apply your boosts!", ephemeral=True)

            # If user provided invite at purchase time, trigger instant delivery
            if inv.get("target_invite"):
                months_num = int(inv["duration"].replace("m", ""))
                deduct_user_balance(inv["user_id"], inv["duration"], inv["boosts"])
                await execute_boost(inv["target_invite"], inv["boosts"], months_num, inv["user_id"], interaction.channel)
        else:
            await interaction.followup.send(f"⏳ {msg}\n*If you just sent the transaction, please allow 1-2 minutes for the Litecoin network to broadcast it.*", ephemeral=True)

    @discord.ui.button(label="📋 Copy Address", style=discord.ButtonStyle.secondary, custom_id="btn_copy_addy")
    async def copy_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(f"```{self.ltc_addy}```", ephemeral=True)

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
                    embed.title = "✅ Payment Confirmed & Delivered!"
                    embed.color = 0x57F287
                    embed.set_field_at(3, name="Status", value="`PAID & DELIVERED`", inline=False)
                    await message.edit(embed=embed, view=None)

                code = inv.get("redeem_key", "Generated")
                await channel.send(f"🎉 <@{user_id}> **Payment Confirmed for `{inv['ltc_amount']} LTC`!**\nYour instant redeem code: `{code}`\nAdded `{inv['boosts']}`x `{inv['duration']}` boost credits to your balance.")

                # If user provided invite link, execute instant boost!
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
# Bot Events
# ==========================================

@bot.event
async def on_ready():
    print("=" * 60)
    print(f" [+] Bot Logged in as: {bot.user.name} ({bot.user.id})")
    print(f" [+] Prefix: {prefix}")
    print(f" [+] Authorized Owners: {owner_ids}")
    print(f" [+] LTC Address: {ltc_address or 'NOT SET (Use $setwallet to configure)'}")
    print(f" [+] Pricing: 1m = {price_1m} LTC/boost | 3m = {price_3m} LTC/boost")
    print("=" * 60)
    try:
        synced = await bot.tree.sync()
        print(f" [+] Synced {len(synced)} Slash Commands.")
    except Exception as e:
        print(f" [-] Failed to sync slash commands: {e}")

# ==========================================
# Boost Commands
# ==========================================

@bot.tree.command(name="boost", description="Open the Discord server booster panel")
async def slash_boost(interaction: discord.Interaction):
    await interaction.response.send_modal(BoostModal())

@bot.command(name="boost")
async def cmd_boost(ctx: commands.Context, invite: str = None, amount: int = None, months: int = None):
    """
    Apply boosts to a server.
    Owners have UNLIMITED boosts.
    Regular users consume their credits.
    """
    if not invite or not amount or not months:
        embed = discord.Embed(
            title="🚀 Discord Server Booster",
            description=f"Apply boosts to any Discord server.\n\n**Usage**:\n`{prefix}boost <invite> <amount> <months>`\nExample: `{prefix}boost discord.gg/example 2 1`",
            color=0x5865F2
        )
        if is_owner(ctx.author):
            embed.set_footer(text="👑 Owner Mode: Unlimited Boosts Active")
        else:
            bal = get_user_balance(ctx.author.id)
            embed.add_field(name="Your Credits", value=f"• 1-Month: `{bal['1m']}` boosts\n• 3-Month: `{bal['3m']}` boosts", inline=False)
            embed.set_footer(text=f"Use {prefix}buy to purchase boost credits with LTC")
        view = BoostLaunchView()
        return await ctx.send(embed=embed, view=view)

    if amount % 2 != 0 or amount <= 0:
        return await ctx.send(embed=discord.Embed(
            title="❌ Invalid Amount",
            description="Number of boosts must be an even positive number (2 boosts per token).",
            color=0xFF0000
        ))

    if months not in [1, 3]:
        return await ctx.send(embed=discord.Embed(
            title="❌ Invalid Duration",
            description="Months must be either `1` or `3`.",
            color=0xFF0000
        ))

    dur_key = f"{months}m"

    if not is_owner(ctx.author):
        bal = get_user_balance(ctx.author.id)
        current_credits = bal.get(dur_key, 0)
        if current_credits < amount:
            return await ctx.send(embed=discord.Embed(
                title="❌ Insufficient Boost Credits",
                description=f"You need `{amount}`x {dur_key} credits, but you only have `{current_credits}`.\n\nUse `{prefix}buy {dur_key} {amount}` to auto-buy credits with Litecoin!",
                color=0xFF0000
            ))
        deduct_user_balance(ctx.author.id, dur_key, amount)

    await execute_boost(invite, amount, months, ctx.author.id, ctx.channel)

# ==========================================
# Auto Buy Boosts with LTC & Instant Delivery
# ==========================================

@bot.command(name="buy")
async def cmd_buy(ctx: commands.Context, duration: str = None, amount: int = None, *args):
    """
    Auto-buy boost credits with instant delivery.
    Usage:
      $buy 1m 2
      $buy 1m 2 discord.gg/myinvite
      $buy 1m 14 code:PROMO10
    """
    if not duration or not amount:
        return await ctx.send(embed=discord.Embed(
            title="🛒 Auto-Buy Boosts with Litecoin",
            description=(
                f"**Pricing**:\n"
                f"• **1-Month Boost**: `{price_1m} LTC` per boost (2 boosts = `{round(price_1m * 2, 4)} LTC`)\n"
                f"• **3-Month Boost**: `{price_3m} LTC` per boost (2 boosts = `{round(price_3m * 2, 4)} LTC`)\n\n"
                f"**Usage**:\n"
                f"`{prefix}buy <1m|3m> <amount> [optional: invite link] [optional: discount code]`\n\n"
                f"**Features**:\n"
                f"⚡ **Instant Delivery**: Include your invite link for immediate auto-boosting once paid!\n"
                f"🔑 **Redeemable Key**: Receive a unique code for your records or gifts.\n"
                f"💳 **Credits**: Unused boosts stay in your `{prefix}balance` forever."
            ),
            color=0x5865F2
        ))

    dur_clean = duration.lower().strip()
    if dur_clean not in ["1m", "3m"]:
        return await ctx.send(embed=discord.Embed(title="❌ Invalid Duration", description="Please choose `1m` or `3m`.", color=0xFF0000))

    if amount % 2 != 0 or amount <= 0:
        return await ctx.send(embed=discord.Embed(title="❌ Invalid Amount", description="Boost amount must be an even positive number (2, 4, 14, etc.).", color=0xFF0000))

    # Parse optional arguments (invite link or discount code)
    target_invite = None
    discount_code = None
    for arg in args:
        if "discord.gg" in arg or "discord.com" in arg or len(arg) > 4 and not arg.startswith("code:"):
            target_invite = arg
        elif arg.startswith("code:"):
            discount_code = arg.replace("code:", "").strip().upper()

    rate = price_1m if dur_clean == "1m" else price_3m
    total_ltc = round(rate * amount, 6)

    # Apply discount if valid
    discount_percent = get_discount_percent(discount_code) if discount_code else 0.0
    if discount_percent > 0:
        savings = round(total_ltc * (discount_percent / 100.0), 6)
        total_ltc = round(total_ltc - savings, 6)

    target_address = ltc_address
    if not target_address or "PASTE" in target_address:
        return await ctx.send(embed=discord.Embed(
            title="❌ LTC Address Not Configured",
            description=f"The bot owner has not linked an LTC address yet. Use `{prefix}setwallet <address>` to set it.",
            color=0xFF0000
        ))

    invoice = create_invoice(ctx.author.id, dur_clean, amount, total_ltc, target_address, target_invite, discount_code)

    embed = discord.Embed(
        title="⚡ Instant Delivery Litecoin Invoice",
        description=f"Send exact amount to the address below. Your order will be confirmed and delivered automatically upon blockchain confirmation.",
        color=0xFEE75C
    )
    embed.add_field(name="📦 Order ID", value=f"`{invoice['id']}`", inline=True)
    embed.add_field(name="💎 Product", value=f"`{amount}x {dur_clean}` Boosts", inline=True)
    embed.add_field(name="💰 Amount to Send", value=f"**`{total_ltc} LTC`**" + (f" *({int(discount_percent)}% off applied)*" if discount_percent else ""), inline=False)
    embed.add_field(name="📬 Send To Address", value=f"```{target_address}```", inline=False)

    if target_invite:
        embed.add_field(name="⚡ Auto-Delivery Target", value=f"`.gg/{getinviteCode(target_invite)}` (Will boost instantly once paid)", inline=False)

    embed.add_field(name="⏳ Status", value="`Awaiting Payment (Expires in 60 mins)`", inline=False)
    embed.set_footer(text="Click 'Check Payment' once sent to check blockchain immediately")

    view = PaymentView(invoice['id'], target_address, total_ltc)
    msg = await ctx.send(embed=embed, view=view)

    asyncio.create_task(auto_poll_invoice(invoice['id'], msg, ctx.channel, ctx.author.id))

# ==========================================
# Redeem Code Command
# ==========================================

@bot.command(name="redeem")
async def cmd_redeem(ctx: commands.Context, key_code: str = None):
    """
    Redeem an instant delivery boost key code.
    Usage:
      $redeem BOOST-1M-2X-ABCD-1234
    """
    if not key_code:
        return await ctx.send(embed=discord.Embed(
            title="🔑 Redeem Boost Code",
            description=f"Enter your boost key to claim your credits:\n`{prefix}redeem <KEY-CODE>`\n\nExample: `{prefix}redeem BOOST-1M-2X-ABCD-1234`",
            color=0x5865F2
        ))

    success, msg, item = redeem_boost_key(key_code, ctx.author.id)
    color = 0x57F287 if success else 0xFF0000

    embed = discord.Embed(title="Code Redemption", description=msg, color=color)
    if success and item:
        bal = get_user_balance(ctx.author.id)
        embed.add_field(name="Updated Balance", value=f"• 1-Month: `{bal['1m']}` boosts\n• 3-Month: `{bal['3m']}` boosts", inline=False)
        embed.set_footer(text=f"Use {prefix}boost <invite> {item['amount']} {item['duration'].replace('m', '')} to apply your boosts!")

    await ctx.send(embed=embed)

# ==========================================
# Live Wallet Inspector & Wallet Linking
# ==========================================

@bot.command(name="wallet")
async def cmd_wallet(ctx: commands.Context):
    """Inspect linked LTC wallet live on the blockchain."""
    global ltc_address
    if not ltc_address or "PASTE" in ltc_address:
        return await ctx.send(embed=discord.Embed(
            title="🪙 No Wallet Linked",
            description=f"No Litecoin wallet has been configured yet.\nOwners can link a wallet anytime using: `{prefix}setwallet <address>`",
            color=0xFF0000
        ))

    status_msg = await ctx.send("🔍 Fetching live blockchain data for your wallet...")
    info = await asyncio.to_thread(get_wallet_live_info, ltc_address)

    embed = discord.Embed(title="🪙 Linked Litecoin Wallet (Live Blockchain)", color=0x5865F2)
    embed.add_field(name="Address", value=f"```{ltc_address}```", inline=False)
    embed.add_field(name="Current Balance", value=f"**`{info.get('balance_ltc', 0.0)} LTC`**", inline=True)
    embed.add_field(name="Total Received", value=f"`{info.get('total_received_ltc', 0.0)} LTC`", inline=True)
    embed.add_field(name="Transactions Count", value=f"`{info.get('tx_count', 0)}` txs", inline=True)
    embed.add_field(name="🔗 Blockchain Explorer", value=f"[View on {info.get('provider', 'Blockchair')}]({info.get('explorer_url')})", inline=False)
    embed.set_footer(text="Live data directly queried from Litecoin nodes")

    await status_msg.edit(content=None, embed=embed)

@bot.command(name="setwallet")
async def cmd_setwallet(ctx: commands.Context, new_address: str = None):
    """Link a new Litecoin receiving address (Owner Only)."""
    global ltc_address
    if not is_owner(ctx.author):
        return await ctx.send(embed=discord.Embed(title="❌ Unauthorized", color=0xFF0000))

    if not new_address or len(new_address.strip()) < 20:
        return await ctx.send(f"❌ Usage: `{prefix}setwallet <valid_ltc_address>`")

    clean_addy = new_address.strip()
    ltc_address = clean_addy

    cfg = load_config()
    if "ltc" not in cfg:
        cfg["ltc"] = {}
    cfg["ltc"]["address"] = clean_addy
    save_config(cfg)

    embed = discord.Embed(
        title="✅ LTC Wallet Linked Successfully",
        description=f"New Litecoin receiving address has been saved and is now active for all incoming `$buy` payments:\n```{clean_addy}```",
        color=0x57F287
    )
    await ctx.send(embed=embed)

# ==========================================
# Dynamic Pricing & Discounts
# ==========================================

@bot.command(name="setprice")
async def cmd_setprice(ctx: commands.Context, duration: str = None, new_price: float = None):
    """Set the price per boost in LTC (Owner Only)."""
    global price_1m, price_3m
    if not is_owner(ctx.author):
        return await ctx.send(embed=discord.Embed(title="❌ Unauthorized", color=0xFF0000))

    if duration not in ["1m", "3m"] or not new_price or new_price <= 0:
        return await ctx.send(f"❌ Usage: `{prefix}setprice <1m|3m> <price_in_ltc>`\nExample: `{prefix}setprice 1m 0.20`")

    cfg = load_config()
    if "ltc" not in cfg:
        cfg["ltc"] = {}

    if duration == "1m":
        price_1m = round(float(new_price), 6)
        cfg["ltc"]["price_per_boost_1m"] = price_1m
    else:
        price_3m = round(float(new_price), 6)
        cfg["ltc"]["price_per_boost_3m"] = price_3m

    save_config(cfg)
    await ctx.send(f"✅ Price for **{duration}** boosts updated to **`{new_price} LTC`** per boost!")

@bot.command(name="creatediscount")
async def cmd_creatediscount(ctx: commands.Context, code: str = None, percent: float = None):
    """Create a promotional discount code (Owner Only)."""
    if not is_owner(ctx.author):
        return await ctx.send(embed=discord.Embed(title="❌ Unauthorized", color=0xFF0000))

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
        return await ctx.send(embed=discord.Embed(title="❌ Unauthorized", color=0xFF0000))

    if duration not in ["1m", "3m"] or not amount or amount <= 0:
        return await ctx.send(f"❌ Usage: `{prefix}createcode <1m|3m> <amount>`\nExample: `{prefix}createcode 1m 2`")

    key_str = generate_boost_key(duration, amount, created_by=f"owner_{ctx.author.id}")
    embed = discord.Embed(
        title="🎁 Gift Boost Code Generated",
        description=f"**Code**: `{key_str}`\n**Product**: `{amount}x {duration}` Boosts\n\nGive this code to any user to redeem with `{prefix}redeem {key_str}`.",
        color=0x57F287
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

    embed = discord.Embed(title="📊 Booster Shop Statistics", color=0x5865F2)
    embed.add_field(name="💰 Total Revenue", value=f"`{stats['total_revenue_ltc']} LTC`", inline=True)
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
async def cmd_balance(ctx: commands.Context, member: discord.Member = None):
    """Check boost credit balance."""
    target = member or ctx.author
    bal = get_user_balance(target.id)

    embed = discord.Embed(title=f"💳 Boost Credits — {target.name}", color=0x5865F2)
    embed.add_field(name="1-Month Credits", value=f"`{bal['1m']}` boosts", inline=True)
    embed.add_field(name="3-Month Credits", value=f"`{bal['3m']}` boosts", inline=True)

    if is_owner(target):
        embed.set_footer(text="👑 Owner: Unlimited Boosts Active")
    else:
        embed.set_footer(text=f"Use {prefix}buy to auto-buy more credits | Use {prefix}boost to spend")
    await ctx.send(embed=embed)

# ==========================================
# Stock & Restock Commands (Bulk Restock Supported)
# ==========================================

@bot.command(name="stock")
async def cmd_stock(ctx: commands.Context):
    """Check current available stock of Nitro tokens."""
    tokens_1m = getStock("data/1m.txt") or []
    tokens_3m = getStock("data/3m.txt") or []

    embed = discord.Embed(title="📦 Current Stock Availability", color=0x5865F2)
    embed.add_field(name="1-Month Tokens", value=f"`{len(tokens_1m)}` tokens (`{len(tokens_1m) * 2}` boosts)", inline=True)
    embed.add_field(name="3-Month Tokens", value=f"`{len(tokens_3m)}` tokens (`{len(tokens_3m) * 2}` boosts)", inline=True)
    embed.set_footer(text=f"Use {prefix}buy to purchase boosts with LTC")
    await ctx.send(embed=embed)

@bot.command(name="restock")
async def cmd_restock(ctx: commands.Context, duration: str = None, *, token_data: str = None):
    """
    Bulk restock tokens directly from Discord (Owner Only).
    Accepts tokens pasted in text OR a .txt file attachment for massive bulk restocks!
    """
    if not is_owner(ctx.author):
        return await ctx.send(embed=discord.Embed(title="❌ Unauthorized", description="Only bot owners can restock tokens.", color=0xFF0000))

    if not duration or duration.lower() not in ["1m", "3m"]:
        return await ctx.send(embed=discord.Embed(
            title="ℹ️ Restock Usage",
            description=(
                f"**Method 1 (Paste Tokens)**:\n`{prefix}restock <1m|3m> <tokens>`\n\n"
                f"**Method 2 (Bulk File Upload)**:\nAttach a `.txt` file containing your tokens and type: `{prefix}restock <1m|3m>`"
            ),
            color=0x5865F2
        ))

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
        return await ctx.send(embed=discord.Embed(
            title="❌ No Tokens Found",
            description="Please paste tokens in the message or attach a `.txt` file containing them.",
            color=0xFF0000
        ))

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
        color=0x57F287
    )
    await ctx.send(embed=embed)

@bot.command(name="usedtokens")
async def cmd_usedtokens(ctx: commands.Context):
    """Check how many used tokens have been archived (Owner Only)."""
    if not is_owner(ctx.author):
        return await ctx.send(embed=discord.Embed(title="❌ Unauthorized", color=0xFF0000))

    count = 0
    if os.path.exists(USED_TOKENS_FILE):
        with open(USED_TOKENS_FILE, "r", encoding="utf-8") as f:
            count = len([l for l in f.read().splitlines() if l.strip()])

    embed = discord.Embed(
        title="🗄️ Archived Used Tokens",
        description=f"Total tokens moved to archive: `{count}` tokens.\nArchive file: `{USED_TOKENS_FILE}`",
        color=0x5865F2
    )
    await ctx.send(embed=embed)

# ==========================================
# Owner Admin Credit Management
# ==========================================

@bot.command(name="addcredits", aliases=["addbal"])
async def cmd_addcredits(ctx: commands.Context, member: discord.Member, duration: str, amount: int):
    """Manually add boost credits to a user (Owner Only)."""
    if not is_owner(ctx.author):
        return await ctx.send(embed=discord.Embed(title="❌ Unauthorized", color=0xFF0000))

    dur_clean = duration.lower().strip()
    if dur_clean not in ["1m", "3m"] or amount <= 0:
        return await ctx.send(f"❌ Usage: `{prefix}addcredits @user <1m|3m> <amount>`")

    new_bal = add_user_balance(member.id, dur_clean, amount)
    embed = discord.Embed(
        title="✅ Credits Added",
        description=f"Added `{amount}`x {dur_clean} boosts to {member.mention}.\n**New Balance**: `{new_bal[dur_clean]}` {dur_clean} boosts.",
        color=0x57F287
    )
    await ctx.send(embed=embed)

@bot.command(name="removecredits", aliases=["delbal"])
async def cmd_removecredits(ctx: commands.Context, member: discord.Member, duration: str, amount: int):
    """Manually remove boost credits from a user (Owner Only)."""
    if not is_owner(ctx.author):
        return await ctx.send(embed=discord.Embed(title="❌ Unauthorized", color=0xFF0000))

    dur_clean = duration.lower().strip()
    if dur_clean not in ["1m", "3m"] or amount <= 0:
        return await ctx.send(f"❌ Usage: `{prefix}removecredits @user <1m|3m> <amount>`")

    deduct_user_balance(member.id, dur_clean, amount)
    bal = get_user_balance(member.id)
    embed = discord.Embed(
        title="✅ Credits Removed",
        description=f"Removed `{amount}`x {dur_clean} boosts from {member.mention}.\n**New Balance**: `{bal[dur_clean]}` {dur_clean} boosts.",
        color=0xFEE75C
    )
    await ctx.send(embed=embed)

@bot.command(name="confirmorder", aliases=["approveorder"])
async def cmd_confirmorder(ctx: commands.Context, invoice_id: str):
    """Force-approve and credit an invoice manually (Owner Only)."""
    if not is_owner(ctx.author):
        return await ctx.send(embed=discord.Embed(title="❌ Unauthorized", color=0xFF0000))

    success, msg, inv = force_complete_invoice(invoice_id.strip())
    color = 0x57F287 if success else 0xFF0000
    embed = discord.Embed(title="Order Update", description=msg, color=color)
    if success and inv and inv.get("redeem_key"):
        embed.add_field(name="Redeem Code Generated", value=f"`{inv['redeem_key']}`", inline=False)
    await ctx.send(embed=embed)

# ==========================================
# Modular Help System
# ==========================================

def get_modular_help_embed(category: str, p: str) -> discord.Embed:
    """Builds clean, modular help embeds with GitHub-style formatting."""

    if category == "shop":
        embed = discord.Embed(
            title="🛒 Module: Auto-Shop & Purchasing",
            description="Buy boost credits using Litecoin, redeem keys, and manage credits.",
            color=0x5865F2
        )
        embed.add_field(
            name=f"⚡ `{p}buy <1m|3m> <amount> [invite] [code:PROMO]`",
            value=(
                "Creates an automated Litecoin invoice with an interactive `[Check Payment]` button.\n"
                "• **Instant Auto-Boost**: Add your invite link (`$buy 1m 2 discord.gg/example`) to boost immediately upon payment!\n"
                "• **Promo Codes**: Add a discount (`$buy 1m 2 code:SAVE10`) to get a price reduction."
            ),
            inline=False
        )
        embed.add_field(
            name=f"🔑 `{p}redeem <KEY-CODE>`",
            value="Redeem an instant delivery boost code (e.g. `BOOST-1M-2X-ABCD-1234`) to claim credits.",
            inline=False
        )
        embed.add_field(
            name=f"💳 `{p}balance` *(or `{p}credits`)*",
            value="Displays your current available 1-Month and 3-Month boost credits.",
            inline=False
        )
        embed.add_field(
            name=f"📦 `{p}stock`",
            value="View the bot's real-time Nitro token stock and total boosts available.",
            inline=False
        )
        embed.add_field(
            name=f"📊 `{p}stats`",
            value="View total shop sales, revenue earned in LTC, and completed orders.",
            inline=False
        )
        embed.set_footer(text="Use the dropdown menu below to navigate modules")
        return embed

    elif category == "boost":
        embed = discord.Embed(
            title="🚀 Module: Server Boosting",
            description="Apply Discord Nitro boosts to any server using credits or owner mode.",
            color=0x5865F2
        )
        embed.add_field(
            name=f"🎯 `{p}boost <invite> <amount> <months>`",
            value=(
                "Directly boosts the target server.\n"
                "• `<invite>`: Server link or code (e.g. `discord.gg/yourserver` or `yourserver`).\n"
                "• `<amount>`: Number of boosts (must be an even number: `2`, `4`, `14`).\n"
                "• `<months>`: Duration (`1` for 1-month tokens, `3` for 3-month tokens).\n"
                "• *Example*: `{p}boost discord.gg/example 2 1`"
            ),
            inline=False
        )
        embed.add_field(
            name=f"📱 `{p}boost` *(Interactive Button)*",
            value="Sends an embed with a **[🚀 Boost a Server]** button that opens a popup form in Discord.",
            inline=False
        )
        embed.add_field(
            name="⚡ `/boost` *(Slash Command)*",
            value="Discord slash command that immediately opens the boosting popup modal.",
            inline=False
        )
        embed.set_footer(text="👑 Owners have UNLIMITED boosts | Regular users consume credits")
        return embed

    elif category == "wallet":
        embed = discord.Embed(
            title="🪙 Module: Litecoin & Wallet Management",
            description="Manage your receiving wallet and inspect blockchain status live.",
            color=0x5865F2
        )
        embed.add_field(
            name=f"🔍 `{p}wallet`",
            value=(
                "Queries the Litecoin blockchain in real-time (Blockchair / BlockCypher).\n"
                "Displays confirmed balance, total received, transaction count, and live explorer link."
            ),
            inline=False
        )
        embed.add_field(
            name=f"📬 `{p}setwallet <ltc_address>` 👑",
            value="Updates the receiving LTC wallet address on the fly without restarting the bot.",
            inline=False
        )
        embed.add_field(
            name=f"🏷️ `{p}setprice <1m|3m> <price_in_ltc>` 👑",
            value="Update the boost pricing dynamically (e.g. `{p}setprice 1m 0.20`).",
            inline=False
        )
        embed.set_footer(text="👑 = Owner Only Command")
        return embed

    elif category == "admin":
        embed = discord.Embed(
            title="👑 Module: Owner & Stock Administration",
            description="Administrative commands for managing stock, gifts, discounts, and users.",
            color=0xED4245
        )
        embed.add_field(
            name=f"📥 `{p}restock <1m|3m>`",
            value=(
                "Bulk restock Nitro tokens into stock.\n"
                "• **Text Restock**: `{p}restock 1m token1 token2...`\n"
                "• **Bulk File Upload**: Attach a `.txt` file containing 100s or 1,000s of tokens!\n"
                "• *Duplicates are automatically filtered out.*"
            ),
            inline=False
        )
        embed.add_field(
            name=f"🎁 `{p}createcode <1m|3m> <amount>`",
            value="Generate free redeemable gift codes (e.g. for giveaways, promos, or manual deals).",
            inline=False
        )
        embed.add_field(
            name=f"🏷️ `{p}creatediscount <code> <percent_off>`",
            value="Create promotional discount codes (e.g. `{p}creatediscount SUMMER10 10`).",
            inline=False
        )
        embed.add_field(
            name=f"➕ `{p}addcredits @user <1m|3m> <amount>`",
            value="Manually gift or credit boost balance to any Discord user.",
            inline=False
        )
        embed.add_field(
            name=f"➖ `{p}removecredits @user <1m|3m> <amount>`",
            value="Deduct boost credits from any user.",
            inline=False
        )
        embed.add_field(
            name=f"✅ `{p}confirmorder <INV-ID>`",
            value="Force-approve a pending invoice manually and deliver credits and redeem code.",
            inline=False
        )
        embed.add_field(
            name=f"🗄️ `{p}usedtokens`",
            value="View the total count of used/archived tokens that were moved out of stock.",
            inline=False
        )
        embed.set_footer(text="Restricted to hardcoded bot owners [1505515188991033409, 1521774957065928734]")
        return embed

    else:
        # Default All-in-One Modular View
        embed = discord.Embed(
            title="⚡ Booster & Auto-Shop Bot — Command Menu",
            description=(
                f"Welcome to the Booster Bot. All commands are organized below into modular categories.\n"
                f"Use the **interactive dropdown menu** below to view detailed syntax and examples for any module."
            ),
            color=0x5865F2
        )

        embed.add_field(
            name="🛒 Auto-Shop & Purchasing",
            value=(
                f"• `{p}buy <1m|3m> <amount> [invite]` — Auto-buy with LTC (instant boost or code)\n"
                f"• `{p}redeem <code>` — Redeem a boost key code\n"
                f"• `{p}balance` *(or `{p}credits`)* — Check your available boost credits\n"
                f"• `{p}stock` — View available Nitro token stock\n"
                f"• `{p}stats` — View total shop sales & revenue"
            ),
            inline=False
        )

        embed.add_field(
            name="🚀 Server Boosting",
            value=(
                f"• `{p}boost <invite> <amount> <months>` — Boost a server with credits\n"
                f"• `{p}boost` — Open the interactive booster panel button\n"
                f"• `/boost` — Slash command version of the boost popup"
            ),
            inline=False
        )

        embed.add_field(
            name="🪙 Litecoin & Wallet",
            value=(
                f"• `{p}wallet` — Live blockchain inspect of linked LTC wallet\n"
                f"• `{p}setwallet <address>` — 👑 Link a new LTC receiving address\n"
                f"• `{p}setprice <1m|3m> <ltc>` — 👑 Change boost prices on the fly"
            ),
            inline=False
        )

        embed.add_field(
            name="👑 Owner & Administration",
            value=(
                f"• `{p}restock <1m|3m>` — Bulk restock tokens (paste or attach `.txt`)\n"
                f"• `{p}createcode <1m|3m> <amt>` — Generate free redeemable gift keys\n"
                f"• `{p}creatediscount <code> <%>` — Create promotional discount codes\n"
                f"• `{p}addcredits @user <1m|3m> <amt>` — Gift credits manually\n"
                f"• `{p}removecredits @user <1m|3m> <amt>` — Deduct credits manually\n"
                f"• `{p}confirmorder <INV-ID>` — Force-approve a pending invoice\n"
                f"• `{p}usedtokens` — Check count of archived used accounts"
            ),
            inline=False
        )

        embed.set_footer(text=f"Prefix: {p} | Select a category below for full guide & examples")
        return embed

class HelpDropdown(Select):
    def __init__(self, p: str):
        self.p = p
        options = [
            discord.SelectOption(label="All Commands Overview", value="all", emoji="🌐", description="View all modules and commands at once"),
            discord.SelectOption(label="Auto-Shop & Purchasing", value="shop", emoji="🛒", description="Commands for buying, redeeming & credits"),
            discord.SelectOption(label="Server Boosting", value="boost", emoji="🚀", description="Commands for boosting Discord servers"),
            discord.SelectOption(label="Litecoin & Wallet", value="wallet", emoji="🪙", description="LTC wallet inspection & pricing"),
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
async def cmd_help(ctx: commands.Context):
    """Show super clean modular help menu with interactive dropdown."""
    embed = get_modular_help_embed("all", prefix)
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
