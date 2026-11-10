import os
import sys
import time
import yaml
import asyncio
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

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
    USED_TOKENS_FILE
)

def load_config():
    try:
        with open("config/config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}

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
# Payment View with Interactive Buttons
# ==========================================

class PaymentView(View):
    def __init__(self, invoice_id: str, ltc_addy: str, expected_ltc: float):
        super().__init__(timeout=3600)  # 60 minute button validity
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
            embed.set_field_at(3, name="Status", value="`PAID & CREDITED`", inline=False)
            await interaction.message.edit(embed=embed, view=None)
            await interaction.followup.send(f"🎉 **Payment Verified!** {msg}\nUse `{prefix}boost <invite> {inv['boosts']} {inv['duration'].replace('m', '')}` to apply your boosts!", ephemeral=True)
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
    """Periodically checks blockchain for 30 minutes in background."""
    for _ in range(60):  # 60 checks * 30 seconds = 30 minutes
        await asyncio.sleep(30)
        try:
            paid, msg, inv = check_invoice_payment(invoice_id)
            if paid:
                if message and message.embeds:
                    embed = message.embeds[0]
                    embed.title = "✅ Payment Confirmed & Delivered!"
                    embed.color = 0x57F287
                    embed.set_field_at(3, name="Status", value="`PAID & CREDITED`", inline=False)
                    await message.edit(embed=embed, view=None)
                await channel.send(f"🎉 <@{user_id}> **Your payment of `{inv['ltc_amount']} LTC` was confirmed!**\nAdded `{inv['boosts']}`x `{inv['duration']}` boost credits to your balance.\nUse `{prefix}boost <invite> {inv['boosts']} {inv['duration'].replace('m', '')}` to boost!")
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
    print("=" * 55)
    print(f" [+] Bot Logged in as: {bot.user.name} ({bot.user.id})")
    print(f" [+] Prefix: {prefix}")
    print(f" [+] Authorized Owners: {owner_ids}")
    print(f" [+] LTC Address: {ltc_address or 'NOT SET (Configure in config.yaml)'}")
    print(f" [+] Pricing: 1m = {price_1m} LTC/boost | 3m = {price_3m} LTC/boost")
    print("=" * 55)
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
    # If no parameters provided, send button to open interactive modal
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

    # Validate parameters
    if amount % 2 != 0 or amount <= 0:
        return await ctx.send(embed=discord.Embed(
            title="❌ Invalid Amount",
            description="Number of boosts must be a positive even number (2 boosts per token).",
            color=0xFF0000
        ))

    if months not in [1, 3]:
        return await ctx.send(embed=discord.Embed(
            title="❌ Invalid Duration",
            description="Months must be either `1` or `3`.",
            color=0xFF0000
        ))

    dur_key = f"{months}m"

    # Check credit balance if not owner
    if not is_owner(ctx.author):
        bal = get_user_balance(ctx.author.id)
        current_credits = bal.get(dur_key, 0)
        if current_credits < amount:
            return await ctx.send(embed=discord.Embed(
                title="❌ Insufficient Boost Credits",
                description=f"You need `{amount}`x {dur_key} credits, but you only have `{current_credits}`.\n\nUse `{prefix}buy {dur_key} {amount}` to auto-buy credits with Litecoin!",
                color=0xFF0000
            ))

    invite_code = getinviteCode(invite)
    guild_id = checkInvite(invite_code)

    if not guild_id:
        return await ctx.send(embed=discord.Embed(
            title="❌ Invalid Invite",
            description=f"Could not reach server with invite: `.gg/{invite_code}`",
            color=0xFF0000
        ))

    filename = "data/1m.txt" if months == 1 else "data/3m.txt"
    stock = getStock(filename) or []
    required_tokens = int(amount / 2)

    if required_tokens > len(stock):
        return await ctx.send(embed=discord.Embed(
            title="❌ Stock Empty",
            description=f"The bot is temporarily out of stock! Need `{required_tokens}` tokens, but only `{len(stock)}` available in `{filename}`.",
            color=0xFF0000
        ))

    # Reserve tokens from stock
    tokens_to_use = stock[:required_tokens]
    for token in tokens_to_use:
        remove(token, filename)

    status_msg = await ctx.send(embed=discord.Embed(
        title="⏳ Boosting in Progress...",
        description=f"Joining and applying `{amount}` boosts to **.gg/{invite_code}**...\nPlease wait.",
        color=0xFEE75C
    ))

    # Execute boosting logic in background thread
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

    # Deduct credits for regular users
    if not is_owner(ctx.author):
        deduct_user_balance(ctx.author.id, dur_key, amount)

    result_embed = discord.Embed(
        title="✅ Boosting Finished",
        description=f"Completed boosting **.gg/{invite_code}** in `{elapsed}s`.",
        color=0x57F287 if success_count > 0 else 0xED4245
    )
    result_embed.add_field(name="Successful Boosts", value=f"`{success_count}` applied", inline=True)
    result_embed.add_field(name="Failed Boosts", value=f"`{failed_count}` failed", inline=True)
    result_embed.add_field(name="Tokens Used & Archived", value=f"`{required_tokens}` tokens", inline=True)

    if not is_owner(ctx.author):
        new_bal = get_user_balance(ctx.author.id)
        result_embed.add_field(name="Remaining Credits", value=f"`{new_bal[dur_key]}` {dur_key} boosts", inline=False)

    result_embed.set_footer(text="BoostBot Crafted by .gg/coderz")
    await status_msg.edit(embed=result_embed)

# ==========================================
# Auto Buy Boosts with LTC
# ==========================================

@bot.command(name="buy")
async def cmd_buy(ctx: commands.Context, duration: str = None, amount: int = None):
    """
    Auto-buy boost credits with Litecoin (LTC).
    Usage:
      $buy 1m 2
      $buy 3m 14
    """
    if not duration or not amount:
        return await ctx.send(embed=discord.Embed(
            title="🛒 Auto-Buy Boosts with Litecoin",
            description=(
                f"**Pricing**:\n"
                f"• **1-Month Boost**: `{price_1m} LTC` per boost (2 boosts = `{round(price_1m * 2, 4)} LTC`)\n"
                f"• **3-Month Boost**: `{price_3m} LTC` per boost (2 boosts = `{round(price_3m * 2, 4)} LTC`)\n\n"
                f"**Usage**:\n"
                f"`{prefix}buy <1m|3m> <number of boosts>`\n\n"
                f"**Examples**:\n"
                f"`{prefix}buy 1m 2` — Buy 2x 1-month boosts\n"
                f"`{prefix}buy 1m 14` — Buy 14x 1-month boosts (Level 3)\n"
                f"`{prefix}buy 3m 14` — Buy 14x 3-month boosts"
            ),
            color=0x5865F2
        ))

    dur_clean = duration.lower().strip()
    if dur_clean not in ["1m", "3m"]:
        return await ctx.send(embed=discord.Embed(title="❌ Invalid Duration", description="Please choose `1m` or `3m`.", color=0xFF0000))

    if amount % 2 != 0 or amount <= 0:
        return await ctx.send(embed=discord.Embed(title="❌ Invalid Amount", description="Boost amount must be a positive even number (2, 4, 14, etc.).", color=0xFF0000))

    rate = price_1m if dur_clean == "1m" else price_3m
    total_ltc = round(rate * amount, 6)

    target_address = ltc_address
    if not target_address or "PASTE" in target_address:
        return await ctx.send(embed=discord.Embed(
            title="❌ LTC Address Not Configured",
            description="The bot owner has not set a Litecoin receiving address in `config/config.yaml`.",
            color=0xFF0000
        ))

    invoice = create_invoice(ctx.author.id, dur_clean, amount, total_ltc, target_address)

    embed = discord.Embed(
        title="⚡ Litecoin Payment Invoice",
        description=f"Send exact amount to the address below. Your boost credits will be credited automatically upon payment confirmation.",
        color=0xFEE75C
    )
    embed.add_field(name="📦 Order ID", value=f"`{invoice['id']}`", inline=True)
    embed.add_field(name="💎 Product", value=f"`{amount}x {dur_clean}` Boost Credits", inline=True)
    embed.add_field(name="💰 Amount to Send", value=f"**`{total_ltc} LTC`**", inline=False)
    embed.add_field(name="📬 Send To Address", value=f"```{target_address}```", inline=False)
    embed.add_field(name="⏳ Status", value="`Awaiting Payment (Expires in 60 mins)`", inline=False)
    embed.set_footer(text="Click 'Check Payment' once you have sent the transaction")

    view = PaymentView(invoice['id'], target_address, total_ltc)
    msg = await ctx.send(embed=embed, view=view)

    # Start automated background polling task
    asyncio.create_task(auto_poll_invoice(invoice['id'], msg, ctx.channel, ctx.author.id))

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

    # 1. Check for attached file (Bulk upload of 100s or 1000s of tokens)
    if ctx.message.attachments:
        for attachment in ctx.message.attachments:
            if attachment.filename.endswith(".txt"):
                content = await attachment.read()
                lines = content.decode("utf-8", errors="ignore").splitlines()
                tokens_to_add.extend([l.strip() for l in lines if l.strip()])

    # 2. Check for pasted text
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

    # Existing stock to avoid duplicates
    existing_stock = set(getStock(filename) or [])
    new_tokens = []
    for t in tokens_to_add:
        actual_t = t.split(":")[2] if ":" in t else t
        if actual_t not in existing_stock:
            new_tokens.append(t)
            existing_stock.add(actual_t)

    # Append new tokens to stock
    with open(filename, "a", encoding="utf-8") as f:
        for t in new_tokens:
            f.write(t + "\n")

    # Delete command message for privacy
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

    success, msg = force_complete_invoice(invoice_id.strip())
    color = 0x57F287 if success else 0xFF0000
    await ctx.send(embed=discord.Embed(title="Order Update", description=msg, color=color))

# ==========================================
# Help Command
# ==========================================

@bot.command(name="help")
async def cmd_help(ctx: commands.Context):
    """Show comprehensive help menu."""
    embed = discord.Embed(title="🤖 Booster & Auto-Shop Bot Commands", color=0x5865F2)

    embed.add_field(
        name="🛒 Purchasing Boosts",
        value=(
            f"`{prefix}buy <1m|3m> <boosts>` — Auto-buy boost credits with Litecoin\n"
            f"`{prefix}balance` — Check your available boost credits\n"
            f"`{prefix}stock` — View available Nitro token stock"
        ),
        inline=False
    )

    embed.add_field(
        name="🚀 Boosting",
        value=(
            f"`{prefix}boost <invite> <amount> <months>` — Boost a server with credits\n"
            f"`{prefix}boost` — Open the interactive booster panel"
        ),
        inline=False
    )

    if is_owner(ctx.author):
        embed.add_field(
            name="👑 Owner Administration",
            value=(
                f"`{prefix}restock <1m|3m>` — Bulk restock tokens (paste or attach `.txt`)\n"
                f"`{prefix}addcredits @user <1m|3m> <amt>` — Gift credits manually\n"
                f"`{prefix}removecredits @user <1m|3m> <amt>` — Deduct credits\n"
                f"`{prefix}confirmorder <INV-ID>` — Force-approve a pending invoice\n"
                f"`{prefix}usedtokens` — View count of archived used tokens"
            ),
            inline=False
        )
        embed.set_footer(text="👑 Owner Status Active | Unlimited Boosts")
    else:
        embed.set_footer(text=f"Use {prefix}buy to purchase boosts with Litecoin")

    await ctx.send(embed=embed)

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

    # Start 24/7 web server for Render health checks and uptime pingers
    keep_alive()

    # Load initial tokens from environment variables if present (useful on Render)
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
