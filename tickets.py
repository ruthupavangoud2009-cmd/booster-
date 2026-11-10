import os
import json
import time
import random
import asyncio
import discord
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

TICKETS_DB_FILE = "data/tickets.json"
AIZEN_COLOR = 0x4A0E4E  # Deep Velvet Aizen Purple
AIZEN_ACCENT = 0x8A2BE2 # Kyōka Suigetsu Violet

TOPIC_TITLES = {
    "order": "🛒 Boost Order & Instant Auto-Buy",
    "boosts": "🛒 Boost Purchases & Custom Deals",
    "vip": "💎 VIP & Wholesale Bulk Orders",
    "support": "❓ General Support & Assistance",
    "partner": "💼 Partnerships & Collaborations"
}

def load_tickets_db() -> Dict[str, Any]:
    if not os.path.exists(TICKETS_DB_FILE):
        return {}
    try:
        with open(TICKETS_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_tickets_db(data: Dict[str, Any]):
    os.makedirs("data", exist_ok=True)
    temp_path = f"{TICKETS_DB_FILE}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(temp_path, TICKETS_DB_FILE)

def get_user_open_ticket(guild: discord.Guild, user_id: int) -> Optional[discord.TextChannel]:
    """Finds an existing active ticket for the user if it still exists."""
    db = load_tickets_db()
    for ch_id, t_info in list(db.items()):
        if t_info.get("user_id") == user_id and t_info.get("status") == "open":
            ch = guild.get_channel(int(ch_id))
            if ch:
                return ch
            else:
                # Channel was deleted manually from Discord, clean it
                db[ch_id]["status"] = "closed"
                save_tickets_db(db)
    return None

async def create_or_get_ticket(
    guild: discord.Guild,
    user: discord.Member,
    topic_key: str = "order",
    owners_list: list = None,
    bot_ref = None
) -> Tuple[Optional[discord.TextChannel], bool, dict]:
    """
    Creates or returns an active ticket channel for the user.
    Returns: (channel, is_newly_created, ticket_data)
    """
    owners_list = owners_list or []
    db = load_tickets_db()

    # Check for existing open ticket
    existing_ch = get_user_open_ticket(guild, user.id)
    if existing_ch:
        t_data = db.get(str(existing_ch.id), {})
        return existing_ch, False, t_data

    # Ensure "🎫 ── TICKETS ──" category exists
    category = discord.utils.get(guild.categories, name="🎫 ── TICKETS ──")
    if not category:
        try:
            category = await guild.create_category(name="🎫 ── TICKETS ──")
        except Exception:
            category = None

    # Overwrites
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False, view_channel=False),
        user: discord.PermissionOverwrite(
            read_messages=True,
            view_channel=True,
            send_messages=True,
            attach_files=True,
            embed_links=True,
            read_message_history=True
        ),
        guild.me: discord.PermissionOverwrite(
            read_messages=True,
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            manage_permissions=True,
            embed_links=True,
            attach_files=True
        )
    }

    # Grant access to bot owners
    for owner_id in owners_list:
        owner_member = guild.get_member(owner_id)
        if owner_member:
            overwrites[owner_member] = discord.PermissionOverwrite(
                read_messages=True,
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                embed_links=True
            )

    prefix = "order" if topic_key == "order" else "ticket"
    clean_user = "".join(c for c in user.name.lower() if c.isalnum())[:10] or "user"
    channel_name = f"{prefix}-{clean_user}-{random.randint(100, 999)}"
    topic_name = TOPIC_TITLES.get(topic_key, "General Inquiries")

    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites,
        topic=f"Topic: {topic_name} | User: {user.name} ({user.id})"
    )

    ticket_data = {
        "channel_id": ticket_channel.id,
        "guild_id": guild.id,
        "user_id": user.id,
        "user_name": user.name,
        "topic": topic_name,
        "topic_key": topic_key,
        "status": "open",
        "created_at": time.time(),
        "claimed_by": None
    }
    db[str(ticket_channel.id)] = ticket_data
    save_tickets_db(db)

    return ticket_channel, True, ticket_data

# ==========================================
# In-Ticket Controls View
# ==========================================

class TicketCloseModal(discord.ui.Modal, title="⚔️ Close Ticket"):
    reason = discord.ui.TextInput(
        label="Closing Reason",
        placeholder="e.g. Order delivered, issue resolved, answered.",
        required=False,
        max_length=200
    )

    def __init__(self, ticket_data: dict):
        super().__init__()
        self.ticket_data = ticket_data

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        reason_text = str(self.reason.value).strip() or "Ticket closed by client/staff."

        channel = interaction.channel
        db = load_tickets_db()
        t_id = str(channel.id)

        # Generate Transcript
        transcript_lines = [
            f"=== SŌSUKE AIZEN TICKET TRANSCRIPT ===",
            f"Ticket: #{channel.name}",
            f"User: {self.ticket_data.get('user_name')} ({self.ticket_data.get('user_id')})",
            f"Topic: {self.ticket_data.get('topic')}",
            f"Closed At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Reason: {reason_text}",
            f"======================================\n"
        ]

        async for msg in channel.history(limit=500, oldest_first=True):
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            transcript_lines.append(f"[{timestamp}] {msg.author.name}: {msg.content}")

        transcript_text = "\n".join(transcript_lines)
        os.makedirs("data/transcripts", exist_ok=True)
        transcript_file = f"data/transcripts/ticket-{channel.id}.txt"
        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(transcript_text)

        # Update DB
        if t_id in db:
            db[t_id]["status"] = "closed"
            db[t_id]["closed_at"] = time.time()
            db[t_id]["close_reason"] = reason_text
            save_tickets_db(db)

        # Send closing embed with countdown
        embed = discord.Embed(
            title="⚔️ Ticket Closing",
            description=f"*\"No one stands on the heavens from the beginning.\"*\n\nReason: `{reason_text}`\nChannel will be deleted in **5 seconds**.",
            color=discord.Color.red()
        )
        await channel.send(embed=embed)

        # Attempt to DM user the transcript
        try:
            guild = interaction.guild
            user = guild.get_member(self.ticket_data.get("user_id"))
            if user:
                dm_embed = discord.Embed(
                    title=f"📁 Ticket Transcript — #{channel.name}",
                    description=f"Your ticket in **{guild.name}** was closed.\n**Reason**: `{reason_text}`",
                    color=AIZEN_COLOR
                )
                with open(transcript_file, "rb") as fp:
                    await user.send(embed=dm_embed, file=discord.File(fp, filename=f"transcript-{channel.name}.txt"))
        except Exception:
            pass

        await asyncio.sleep(5)
        try:
            await channel.delete(reason=f"Ticket closed: {reason_text}")
        except Exception:
            pass

class TicketInsideControls(discord.ui.View):
    def __init__(self, ticket_data: dict, bot_ref=None):
        super().__init__(timeout=None)
        self.ticket_data = ticket_data
        self.bot_ref = bot_ref

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="btn_tkt_close")
    async def btn_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketCloseModal(self.ticket_data))

    @discord.ui.button(label="✋ Claim Ticket", style=discord.ButtonStyle.secondary, custom_id="btn_tkt_claim")
    async def btn_claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        db = load_tickets_db()
        t_id = str(channel.id)

        embed = discord.Embed(
            title="⚔️ Ticket Claimed",
            description=f"*\"Since when were you under the impression...\"*\n\n{interaction.user.mention} has claimed this ticket and will assist you shortly.",
            color=AIZEN_ACCENT
        )
        if t_id in db:
            db[t_id]["claimed_by"] = interaction.user.id
            save_tickets_db(db)

        button.disabled = True
        button.label = f"Claimed by {interaction.user.name}"
        await interaction.message.edit(view=self)
        await channel.send(embed=embed)

    @discord.ui.button(label="📄 Transcript", style=discord.ButtonStyle.primary, custom_id="btn_tkt_transcript")
    async def btn_transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

        lines = [
            f"=== SŌSUKE AIZEN TICKET TRANSCRIPT ===",
            f"Ticket: #{channel.name}",
            f"Exported At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"======================================\n"
        ]
        async for msg in channel.history(limit=500, oldest_first=True):
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"[{timestamp}] {msg.author.name}: {msg.content}")

        transcript_text = "\n".join(lines)
        os.makedirs("data/transcripts", exist_ok=True)
        file_path = f"data/transcripts/snapshot-{channel.id}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(transcript_text)

        with open(file_path, "rb") as fp:
            await interaction.followup.send("📄 Here is the live ticket transcript snapshot:", file=discord.File(fp, filename=f"transcript-{channel.name}.txt"), ephemeral=True)

# ==========================================
# Ticket Topic Selection Dropdown
# ==========================================

class TicketTopicSelect(discord.ui.Select):
    def __init__(self, bot_ref, owners_list: list):
        self.bot_ref = bot_ref
        self.owners_list = owners_list
        options = [
            discord.SelectOption(
                label="Boost Purchases & Custom Deals",
                value="boosts",
                emoji="🛒",
                description="Purchase boosts, custom orders, or payment questions."
            ),
            discord.SelectOption(
                label="VIP & Wholesale Bulk Orders",
                value="vip",
                emoji="💎",
                description="Large orders (50+ boosts), reseller pricing & keys."
            ),
            discord.SelectOption(
                label="General Support & Assistance",
                value="support",
                emoji="❓",
                description="Questions about the bot, commands, or troubleshooting."
            ),
            discord.SelectOption(
                label="Partnerships & Collaborations",
                value="partner",
                emoji="💼",
                description="Collaborate with our shop, sponsorships & affiliates."
            )
        ]
        super().__init__(placeholder="⚔️ Choose a ticket topic to begin...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        selected_topic = self.values[0]

        await interaction.response.defer(ephemeral=True)

        ticket_channel, is_new, ticket_data = await create_or_get_ticket(
            guild=guild,
            user=user,
            topic_key=selected_topic,
            owners_list=self.owners_list,
            bot_ref=self.bot_ref
        )

        if not is_new:
            return await interaction.followup.send(
                f"❌ You already have an active ticket open in {ticket_channel.mention}!",
                ephemeral=True
            )

        topic_name = TOPIC_TITLES.get(selected_topic, "General Inquiries")

        # Send Aizen-themed welcome card inside ticket
        embed = discord.Embed(
            title=f"⚔️ {topic_name.upper()} ⚔️",
            description=(
                f"*\"Admiration is the emotion furthest from understanding.\"*\n\n"
                f"Welcome {user.mention} to your private consultation channel.\n"
                f"Staff and management have been notified of your inquiry.\n\n"
                f"◈ **Topic**: `{topic_name}`\n"
                f"◈ **Client**: `{user.name}` (`{user.id}`)\n"
                f"◈ **Security Status**: `Encrypted & Monitored`\n\n"
                f"Please describe your requirements, desired boost quantity, or question below."
            ),
            color=AIZEN_COLOR
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Sōsuke Aizen • Kyōka Suigetsu Engine | Use controls below")

        view = TicketInsideControls(ticket_data, self.bot_ref)
        await ticket_channel.send(content=f"{user.mention} | <@&{guild.id}>", embed=embed, view=view)

        await interaction.followup.send(
            f"✅ Your private ticket has been created: {ticket_channel.mention}",
            ephemeral=True
        )

class TicketTopicLaunchView(discord.ui.View):
    def __init__(self, bot_ref, owners_list: list):
        super().__init__(timeout=None)
        self.add_item(TicketTopicSelect(bot_ref, owners_list))
