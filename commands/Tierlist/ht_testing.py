import discord
import json
import time
import asyncio

from discord import app_commands
from discord.ext import commands
from typing import List
from firebase_admin import db

from commands.Tierlist.ht_waitlist import (
    LINKED_ROLE_ID, RESTRICTED_ROLE_ID, return_item,
    get_tier_index, TIER_THRESHOLDS, TIER_NAMES, TIER_ROLES, TIER_TO_MAIN, tier_colors
)
from commands.Tierlist.waitlist import (
    EMOJI_EMERALD, EMOJI_REDSTONE, EMOJI_STEVE, EMOJI_MC_CLOCK, EMOJI_SCROLL, EMOJI_FEATHER, 
    EMOJI_SPYGLASS, EMOJI_HOURGLASS, EMOJI_REPLY, EMOJI_ARROW,
    EMOJI_TIERLIST, EMOJI_CONNECT, EMOJI_RANK, EMOJI_GOLD, EMOJI_BARRIER, CHECK, CROSS
)
from utils.pagination import PREV_EMOJI, NEXT_EMOJI


def _has_restricted_role(member: discord.Member | discord.User | None) -> bool:
    return bool(member and getattr(member, "roles", None) and any(role.id == RESTRICTED_ROLE_ID for role in member.roles))

GAMEMODE_SHORT = ["npot", "dpot", "smp", "sword", "crystal", "axe", "mace", "uhc"]
GAMEMODE_DISPLAY = {
    "npot": "NPOT", "dpot": "DPOT", "smp": "SMP",
    "sword": "Sword", "crystal": "Crystal", "axe": "Axe", "mace": "Mace", "uhc": "UHC"
}
DISPLAY_TO_SHORT = {v: k for k, v in GAMEMODE_DISPLAY.items()}

RANK_CHAIN = ["LT3", "HT3", "LT2", "HT2"]

REGULATOR_ROLE_ID = 1339144441583370251
AUTHORIZED_USERS = [692254240290242601, 840972960793100309]
REVIEW_CHANNEL_ID = 1467967731625103505
RESULTS_CHANNEL_ID = 1338411690902945832

COOLDOWN_SECONDS = 86400 * 30

CROSS = "<:cross1:1339153202859474956>"
CHECK = "<:checkmark:1339153448926580818>"
WARN = "<:warn:1459986909911842846>"
CIRCLE_SELECTED = EMOJI_ARROW
CIRCLE_UNSELECTED = EMOJI_REDSTONE
EMOTE_DOT = "<:dot:1357188726047899760>"

STATUS_LABELS = {
    "new": "New",
    "ongoing": "Ongoing",
    "overdue": "Overdue",
    "pending": "Pending Review",
    "completed": "Completed",
    "denied": "Denied",
    "cancelled": "Cancelled",
}


def is_regulator(member: discord.Member) -> bool:
    allowed = [REGULATOR_ROLE_ID, 1304851740226748556, 1460312013535318077, 1304848576190484553]
    return any(role.id in allowed for role in member.roles)


def is_authorized(member: discord.Member) -> bool:
    return member.id in AUTHORIZED_USERS


def get_player_rank(member: discord.Member, gamemode_short: str) -> tuple:
    display = GAMEMODE_DISPLAY.get(gamemode_short, gamemode_short.upper())
    for role in member.roles:
        parts = role.name.split(" ")
        if len(parts) >= 2:
            prefix = parts[0].upper()
            suffix = parts[1]
            if suffix.upper() == display.upper() and prefix in RANK_CHAIN:
                return prefix, display
    return None, None


def get_target_rank(current_rank: str) -> str:
    try:
        idx = RANK_CHAIN.index(current_rank)
        if idx + 1 < len(RANK_CHAIN):
            return RANK_CHAIN[idx + 1]
    except ValueError:
        pass
    return None


async def is_linked(bot, user_id: int) -> tuple:
    try:
        async with bot.tllink_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SHOW TABLES")
                result = await cursor.fetchone()
                link_table = result[0] if result else "mystilinking"
                await cursor.execute(
                    f"SELECT player_name, uuid FROM {link_table} WHERE discord_id = %s",
                    (str(user_id),),
                )
                row = await cursor.fetchone()
                if row:
                    return True, row[0], row[1]
                return False, None, None
    except Exception as e:
        print(f"Error fetching linked IGN for {user_id}: {e}")
        return False, None, None


def get_thread_player_id(thread_name: str) -> int:
    parts = thread_name.split("-")
    for part in parts:
        if part.isdigit():
            return int(part)
    return None


def format_gamemode_select_options():
    return [discord.SelectOption(label=d, value=s) for s, d in GAMEMODE_DISPLAY.items()]


# async def ensure_tables(bot):
#     async with bot.tlresults_pool.acquire() as conn:
#         async with conn.cursor() as cursor:
#             await cursor.execute("""
#                 CREATE TABLE IF NOT EXISTS ht_testing_tickets (
#                     id INT AUTO_INCREMENT PRIMARY KEY,
#                     thread_id BIGINT NOT NULL,
#                     channel_id BIGINT NOT NULL,
#                     guild_id BIGINT NOT NULL,
#                     user_id BIGINT NOT NULL,
#                     user_ign VARCHAR(16),
#                     gamemode VARCHAR(20) NOT NULL,
#                     current_rank VARCHAR(10) NOT NULL,
#                     target_rank VARCHAR(10) NOT NULL,
#                     status VARCHAR(20) DEFAULT 'open',
#                     deadline BIGINT NULL,
#                     testers JSON DEFAULT NULL,
#                     created_at BIGINT NOT NULL,
#                     updated_at BIGINT NOT NULL
#                 )
#             """)
#             await cursor.execute("""
#                 CREATE TABLE IF NOT EXISTS ht_testing_cooldowns (
#                     user_id BIGINT NOT NULL,
#                     gamemode VARCHAR(20) NOT NULL,
#                     expires_at BIGINT NOT NULL,
#                     PRIMARY KEY (user_id, gamemode)
#                 )
#             """)
#             await conn.commit()


async def _fetch_ticket(bot, thread_id: int) -> tuple:
    async with bot.tlresults_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT user_id, user_ign, gamemode, current_rank, target_rank, status, deadline, testers FROM ht_testing_tickets WHERE thread_id = %s",
                (thread_id,)
            )
            return await cursor.fetchone()


async def _update_ticket_testers(bot, thread_id: int, testers: list):
    async with bot.tlresults_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "UPDATE ht_testing_tickets SET testers = %s, updated_at = %s WHERE thread_id = %s",
                (json.dumps(testers), int(time.time()), thread_id)
            )
            await conn.commit()


async def _update_ticket_status(bot, thread_id: int, status: str):
    async with bot.tlresults_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "UPDATE ht_testing_tickets SET status = %s, updated_at = %s WHERE thread_id = %s",
                (status, int(time.time()), thread_id)
            )
            await conn.commit()


async def _update_ticket_deadline(bot, thread_id: int, deadline: int):
    async with bot.tlresults_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "UPDATE ht_testing_tickets SET deadline = %s, updated_at = %s WHERE thread_id = %s",
                (deadline, int(time.time()), thread_id)
            )
            await conn.commit()


async def _refresh_thread_embed(thread: discord.Thread, bot):
    async for msg in thread.history(limit=10, oldest_first=True):
        if msg.embeds:
            embed = msg.embeds[0]
            row = await _fetch_ticket(bot, thread.id)
            if row:
                user_id, user_ign, gamemode, current_rank, target_rank, status, deadline, testers_json = row
                testers = json.loads(testers_json) if testers_json else []
                tester_mentions = "\n".join(f"<@{t}>" for t in testers) if testers else "None assigned"
                embed.clear_fields()
                embed.add_field(name=f"{EMOJI_STEVE} Player", value=f"<@{user_id}> ({user_ign})", inline=True)
                embed.add_field(name=f"{EMOJI_GOLD} Gamemode", value=gamemode, inline=True)
                embed.add_field(name=f"{EMOJI_RANK} Rank", value=f"{current_rank} {EMOJI_ARROW} {target_rank}", inline=True)
                embed.add_field(name=f"{EMOJI_SPYGLASS} Status", value=STATUS_LABELS.get(status, status.replace("_", " ").title()), inline=True)
                if deadline:
                    embed.add_field(name=f"{EMOJI_MC_CLOCK} Deadline", value=f"<t:{deadline}:F> (<t:{deadline}:R>)", inline=True)
                else:
                    embed.add_field(name=f"{EMOJI_MC_CLOCK} Deadline", value="Not set", inline=True)
                embed.add_field(name=f"{EMOJI_FEATHER} Testers", value=tester_mentions, inline=True)
                try:
                    await msg.edit(embed=embed)
                except Exception:
                    pass
        break


class HTTestingSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="Select a gamemode to test for...",
            min_values=1,
            max_values=1,
            options=format_gamemode_select_options(),
            custom_id="ht_testing_gamemode_select",
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        gamemode_short = self.values[0]
        gamemode_display = GAMEMODE_DISPLAY.get(gamemode_short, gamemode_short.upper())

        linked, ign, uuid = await is_linked(interaction.client, interaction.user.id)
        if not linked:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title=f"{EMOJI_CONNECT} Account Linking Required",
                    description=f"To be eligible for testing, you must link your Minecraft account first. Follow the instructions in <#1460525451368861818>.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        current_rank, display = get_player_rank(interaction.user, gamemode_short)
        if not current_rank:
            return await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{CROSS} You need one of these ranks for **{gamemode_display}**: LT3, HT3, LT2, HT2.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        target_rank = get_target_rank(current_rank)
        if not target_rank:
            return await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{CROSS} You are already at the highest rank ({current_rank}) for this system.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        async with interaction.client.tlresults_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT expires_at FROM ht_testing_cooldowns WHERE user_id = %s AND gamemode = %s",
                    (interaction.user.id, gamemode_display)
                )
                cooldown_row = await cursor.fetchone()
                if cooldown_row and cooldown_row[0] > int(time.time()) and interaction.user.id not in AUTHORIZED_USERS:
                    return await interaction.followup.send(
                        embed=discord.Embed(
                            description=f"{CROSS} You are on cooldown for **{gamemode_display}** until <t:{cooldown_row[0]}:F>.",
                            color=discord.Color.red(),
                        ),
                        ephemeral=True,
                    )

                await cursor.execute(
                    "SELECT thread_id FROM ht_testing_tickets WHERE user_id = %s AND status IN ('new', 'ongoing', 'overdue', 'pending')",
                    (interaction.user.id,)
                )
                existing_ticket = await cursor.fetchone()
                if existing_ticket:
                    thread = interaction.guild.get_thread(existing_ticket[0])
                    mention = thread.mention if thread else "`unknown`"
                    return await interaction.followup.send(
                        embed=discord.Embed(
                            description=f"{CROSS} You already have an open ticket: {mention}",
                            color=discord.Color.red(),
                        ),
                        ephemeral=True,
                    )

        try:
            thread = await interaction.channel.create_thread(
                name=f"{target_rank} {gamemode_display} - {ign} ({interaction.user.id})",
                type=discord.ChannelType.private_thread,
            )
        except Exception as e:
            return await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{CROSS} Failed to create thread: {e}",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        deadline_ts = int(time.time()) + 14 * 86400
        created_at = int(time.time())

        async with interaction.client.tlresults_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """INSERT INTO ht_testing_tickets 
                    (thread_id, channel_id, guild_id, user_id, user_ign, gamemode, current_rank, target_rank, status, deadline, testers, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (thread.id, interaction.channel.id, interaction.guild.id, interaction.user.id, ign,
                     gamemode_display, current_rank, target_rank, 'new', deadline_ts, json.dumps([]),
                     created_at, created_at)
                )
                await cursor.execute(
                    "INSERT INTO ht_testing_cooldowns (user_id, gamemode, expires_at) VALUES (%s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE expires_at = %s",
                    (interaction.user.id, gamemode_display, created_at + COOLDOWN_SECONDS, created_at + COOLDOWN_SECONDS)
                )
                await conn.commit()

        instructions = (
            f"-# {EMOTE_DOT} A Regulator will **assign a tester** as soon as they are available.\n"
            f"-# {EMOTE_DOT} The player and tester must complete the test **before the deadline**.\n"
            f"-# {EMOTE_DOT} If the tester is unresponsive after the deadline, a new tester may be assigned.\n"
            f"-# {EMOTE_DOT} Testers should use **`Post Results`** after the test is completed.\n"
        )
        embed = discord.Embed(
            title=f"{EMOJI_TIERLIST} {gamemode_display} High Tier Testing ({ign})",
            description=instructions,
            color=discord.Color.blue(),
        )
        embed.add_field(name=f"{EMOJI_STEVE} Player", value=f"{interaction.user.mention} ([{ign}](https://tierlist.mysticraft.xyz/?player={ign}))", inline=True)
        embed.add_field(name=f"{EMOJI_GOLD} Gamemode", value=gamemode_display, inline=True)
        embed.add_field(name=f"{EMOJI_RANK} Rank", value=f"{current_rank} {EMOJI_ARROW} **{target_rank}**", inline=True)
        embed.add_field(name=f"{EMOJI_SPYGLASS} Status", value=STATUS_LABELS["new"], inline=True)
        embed.add_field(name=f"{EMOJI_MC_CLOCK} Deadline", value=f"<t:{deadline_ts}:F>", inline=True)
        embed.add_field(name=f"{EMOJI_FEATHER} Testers", value="None assigned", inline=True)
        embed.set_footer(text=f"ID: {interaction.user.id}")

        view = HTActionView()
        first_msg = await thread.send(
            content=f"{interaction.user.mention} <@&{REGULATOR_ROLE_ID}>",
            embed=embed,
            view=view,
        )
        await first_msg.pin()

        await interaction.followup.send(
            embed=discord.Embed(
                description=f"{CHECK} Your test thread has been created: {thread.mention}",
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )


class HTTestingPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(HTTestingSelect())

    @discord.ui.button(label="Browse Tickets", style=discord.ButtonStyle.secondary, custom_id="ht_testing_browse", emoji="🔍", row=2)
    async def browse_tickets(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("ht_testing")
        if not cog:
            return
        if is_regulator(interaction.user):
            await cog.show_browse_view(interaction)
        else:
            await cog.show_browse_view(interaction, user_id=interaction.user.id)


class HTActionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _get_ticket_data(self, interaction: discord.Interaction):
        thread_id = interaction.channel_id
        row = await _fetch_ticket(interaction.client, thread_id)
        return thread_id, row

    async def _is_tester(self, user_id: int, testers_json: str) -> bool:
        testers = json.loads(testers_json) if testers_json else []
        return str(user_id) in testers

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        _, row = await self._get_ticket_data(interaction)
        if not row:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} Ticket data not found.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return False
        player_id = row[0]
        if interaction.user.id == player_id:
            custom_id = interaction.data.get("custom_id") if interaction.data else None
            if custom_id == "ht_testing_cancel":
                return True
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} You cannot use these buttons.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return False
        testers_json = row[7]
        is_tester = await self._is_tester(interaction.user.id, testers_json)
        if not is_regulator(interaction.user) and not is_tester:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} Only regulators or assigned testers can use these buttons.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Add Tester", emoji=EMOJI_FEATHER, style=discord.ButtonStyle.primary, custom_id="ht_testing_add_tester")
    async def add_tester(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_regulator(interaction.user):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} Only regulators can add testers.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
        thread_id, row = await self._get_ticket_data(interaction)
        if not row:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} Ticket not found.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
        gamemode_display = row[2]
        guidance = (
            f"-# **1.** Filter testers by your desired tier from the dropdown below\n"
            f"-# **2.** Browse the member list and pick an **active** player as tester\n"
            f"-# **3.** Click **Add User to Thread** to assign them\n\n"
            f"{EMOJI_SPYGLASS} **Example:** If the player is testing for **HT3**, select **HT3** and pick a tester, or select **LT3** and pick a few testers."
        )
        view = discord.ui.View(timeout=300)
        view.add_item(RoleSelectForTester(gamemode_display, thread_id, interaction.client))
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{EMOJI_SPYGLASS} How to Add a Tester for this thread",
                description=guidance,
                color=discord.Color.blue(),
            ),
            view=view,
            ephemeral=True,
        )

    @discord.ui.button(label="Remove Tester", emoji=EMOJI_BARRIER, style=discord.ButtonStyle.gray, custom_id="ht_testing_remove_tester")
    async def remove_tester(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_regulator(interaction.user):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} Only regulators can remove testers.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
        thread_id, row = await self._get_ticket_data(interaction)
        if not row:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} Ticket not found.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        testers_json = row[7]
        existing = json.loads(testers_json) if testers_json else []
        if not existing:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} No testers assigned to remove.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        view = discord.ui.View(timeout=120)
        user_select = discord.ui.UserSelect(
            placeholder="Select testers to remove...",
            min_values=1,
            max_values=len(existing),
        )
        async def remove_callback(select_interaction: discord.Interaction):
            await select_interaction.response.defer(ephemeral=True)
            guild = select_interaction.guild
            thread = guild.get_thread(thread_id)
            if not thread:
                thread = select_interaction.client.get_channel(thread_id)

            removed = []
            for user in user_select.values:
                uid = user.id
                if str(uid) not in existing:
                    continue
                if thread:
                    try:
                        await thread.remove_user(user)
                    except Exception:
                        pass
                existing.remove(str(uid))
                removed.append(str(uid))

            await _update_ticket_testers(select_interaction.client, thread_id, existing)
            if thread:
                await _refresh_thread_embed(thread, select_interaction.client)

            for child in view.children:
                child.disabled = True
            await select_interaction.edit_original_response(
                embed=discord.Embed(
                    description=f"{CHECK} Removed {len(removed)} tester from the thread." if removed else f"{WARN} No testers were removed.",
                    color=discord.Color.green() if removed else discord.Color.orange(),
                ),
                view=view,
            )
        user_select.callback = remove_callback
        view.add_item(user_select)

        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{EMOJI_BARRIER} Remove Tester",
                description=f"Select which tester to remove from this thread. Currently assigned: {len(existing)} tester{'s' if len(existing) <= 1 else ''}.",
                color=discord.Color.orange(),
            ),
            view=view,
            ephemeral=True,
        )

    @discord.ui.button(label="Set Deadline", emoji=EMOJI_MC_CLOCK, style=discord.ButtonStyle.secondary, custom_id="ht_testing_set_deadline")
    async def set_deadline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_regulator(interaction.user):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} Only regulators can set deadlines.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
        thread_id, _ = await self._get_ticket_data(interaction)
        modal = DeadlineModal(thread_id, interaction.client)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Post Results", emoji=EMOJI_RANK, style=discord.ButtonStyle.success, custom_id="ht_testing_finalize")
    async def finalize_results(self, interaction: discord.Interaction, button: discord.ui.Button):
        thread_id, row = await self._get_ticket_data(interaction)
        if not row:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} Ticket not found.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        user_id, user_ign, gamemode_display, current_rank, target_rank, _, _, testers_json = row
        modal = FinalizeModal(thread_id, user_id, user_ign, gamemode_display, current_rank, target_rank, interaction.client)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Cancel Test", style=discord.ButtonStyle.danger, custom_id="ht_testing_cancel")
    async def cancel_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        _, row = await self._get_ticket_data(interaction)
        is_owner = row and row[0] == interaction.user.id
        if not is_regulator(interaction.user) and not is_owner:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} Only the player who requested the test or a regulator can cancel it.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        view = discord.ui.View(timeout=60)
        confirm = discord.ui.Button(label="Confirm", style=discord.ButtonStyle.danger)
        async def confirm_cancel(confirm_interaction: discord.Interaction):
            if confirm_interaction.user.id != interaction.user.id:
                return await confirm_interaction.response.send_message(
                    embed=discord.Embed(
                        description=f"{CROSS} Only {interaction.user.mention} can use this confirmation.",
                        color=discord.Color.red(),
                    ),
                    ephemeral=True,
                )
            thread_id = confirm_interaction.channel_id
            await _update_ticket_status(confirm_interaction.client, thread_id, 'cancelled')
            thread = confirm_interaction.guild.get_thread(thread_id)
            if thread:
                await _refresh_thread_embed(thread, confirm_interaction.client)
                try:
                    await thread.edit(archived=True, locked=True)
                except Exception:
                    pass
            for child in view.children:
                child.disabled = True
            await confirm_interaction.response.edit_message(
                embed=discord.Embed(
                    description=f"{EMOJI_BARRIER} Test cancelled by {interaction.user.mention}.",
                    color=discord.Color.red(),
                ),
                view=view,
            )
        confirm.callback = confirm_cancel
        view.add_item(confirm)

        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{WARN} Cancel Test",
                description=f"Are you sure you want to cancel this test? This will archive and lock the thread.",
                color=discord.Color.orange(),
            ),
            view=view,
            ephemeral=True,
        )


class RoleSelectForTester(discord.ui.Select):
    def __init__(self, gamemode_display: str, thread_id: int, bot):
        self.gamemode_display = gamemode_display
        self.thread_id = thread_id
        self.bot = bot
        options = [discord.SelectOption(label=f"{rank} {gamemode_display}", value=f"{rank} {gamemode_display}") for rank in RANK_CHAIN]
        super().__init__(
            placeholder="Select a tier to browse testers from...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        role_name = self.values[0]
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not role:
            return await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{CROSS} Role with name `{role_name}` not found.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        members = [m for m in role.members if not m.bot]
        if not members:
            return await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{CROSS} No members found with role `{role_name}`.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        view = TesterBrowserView(members, role_name, self.thread_id, self.bot)
        embed = await view._build_embed()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class TesterBrowserView(discord.ui.View):
    def __init__(self, members: List[discord.Member], role_name: str, thread_id: int, bot, page_size: int = 25):
        super().__init__(timeout=300)
        self.members = members
        self.role_name = role_name
        self.thread_id = thread_id
        self.bot = bot
        self.page_size = page_size
        self.page = 0
        self.total_pages = max(1, (len(members) + page_size - 1) // page_size)
        self.selected_ids = set()
        self._rebuild()

    def _rebuild(self):
        self.clear_items()
        self._add_select()

        prev = discord.ui.Button(emoji=PREV_EMOJI, style=discord.ButtonStyle.grey, disabled=self.page == 0, row=1)
        prev.callback = self._make_prev_callback()
        self.add_item(prev)

        label = discord.ui.Button(label=f"Page {self.page + 1} of {self.total_pages}", style=discord.ButtonStyle.grey, disabled=True, row=1)
        self.add_item(label)

        nxt = discord.ui.Button(emoji=NEXT_EMOJI, style=discord.ButtonStyle.grey, disabled=self.page >= self.total_pages - 1, row=1)
        nxt.callback = self._make_next_callback()
        self.add_item(nxt)

        confirm = discord.ui.Button(label="Add User to Thread", emoji=EMOJI_EMERALD, style=discord.ButtonStyle.success, row=2)
        confirm.callback = self._make_confirm_callback()
        self.add_item(confirm)

    def _add_select(self):
        start = self.page * self.page_size
        end = start + self.page_size
        page_members = self.members[start:end]
        options = []
        count = 1
        for m in page_members:
            selected = str(m.id) in self.selected_ids
            options.append(discord.SelectOption(
                label=f"#{count}. {m.display_name[:95]}",
                value=str(m.id),
                description=m.name[:100],
                default=selected
            ))
            count += 1
        if not options:
            options.append(discord.SelectOption(label="No members on this page", value="none"))
        select = discord.ui.Select(
            placeholder="Select a tester from this page...",
            min_values=0,
            # max_values=len(options),
            max_values=1,
            options=options,
            row=0,
        )
        select.callback = self._make_select_callback(select)
        self.add_item(select)

    def _make_select_callback(self, select):
        async def callback(interaction):
            self.selected_ids = set(v for v in select.values if v != "none")
            self._rebuild()
            embed = await self._build_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        return callback

    def _make_prev_callback(self):
        async def callback(interaction):
            if self.page > 0:
                self.page -= 1
            self._rebuild()
            embed = await self._build_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        return callback

    def _make_next_callback(self):
        async def callback(interaction):
            if self.page < self.total_pages - 1:
                self.page += 1
            self._rebuild()
            embed = await self._build_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        return callback

    def _make_confirm_callback(self):
        async def callback(interaction):
            if not self.selected_ids:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        description=f"{CROSS} No testers selected.",
                        color=discord.Color.red(),
                    ),
                    ephemeral=True,
                )
            await interaction.response.defer(ephemeral=True)
            guild = interaction.guild
            thread = guild.get_thread(self.thread_id)
            if not thread:
                thread = interaction.client.get_channel(self.thread_id)
            if not thread:
                return await interaction.followup.send(
                    embed=discord.Embed(
                        description=f"{CROSS} Thread not found.",
                        color=discord.Color.red(),
                    ),
                    ephemeral=True,
                )

            added = []
            for uid_str in self.selected_ids:
                member = guild.get_member(int(uid_str))
                if not member:
                    continue
                try:
                    await thread.add_user(member)
                    added.append(str(member.id))
                except discord.Forbidden as e:
                    print(f"Forbidden adding {member.id}: {e}")
                except discord.HTTPException as e:
                    print(f"HTTP error adding {member.id}: {e}")
                except Exception as e:
                    print(f"Unexpected error adding {member.id}: {e}")

            row = await _fetch_ticket(self.bot, self.thread_id)
            existing = json.loads(row[7]) if row and row[7] else []
            existing.extend(added)
            existing = list(set(existing))
            await _update_ticket_testers(self.bot, self.thread_id, existing)
            if row and row[5] == 'new':
                await _update_ticket_status(self.bot, self.thread_id, 'ongoing')
            await _refresh_thread_embed(thread, self.bot)

            if added and thread:
                player_id = row[0]
                pinned_url = None
                try:
                    pins = await thread.pins()
                    if pins:
                        pinned_url = pins[0].jump_url
                except Exception:
                    pass
                tester_mentions = " ".join(f"<@{uid}>" for uid in added)
                guidance = (
                    f"{EMOJI_REPLY} Coordinate and conduct the test with <@{player_id}>.\n"
                    f"{EMOJI_REPLY} Click `Post Results` button in the **[pinned message]({pinned_url or '#'})** once completed.\n"
                    f"{EMOJI_REPLY} If you have any questions, ping a <@&{REGULATOR_ROLE_ID}> in this thread.\n\n"
                    f"-# {EMOJI_HOURGLASS} This notification is intended for {tester_mentions}."
                )
                try:
                    await thread.send(
                        content=f"{tester_mentions} <@{player_id}>",
                        embed=discord.Embed(
                            title=f"{EMOJI_SPYGLASS} You've been assigned as a tester!",
                            description=guidance,
                            color=discord.Color.green(),
                        )
                    )
                except Exception:
                    pass

            await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{CHECK} Added {len(added)} tester to the thread.",
                    color=discord.Color.green(),
                ),
                ephemeral=True,
            )
            self.stop()
        return callback

    async def _build_embed(self):
        start = self.page * self.page_size
        end = start + self.page_size
        page_members = self.members[start:end]
        desc_lines = []
        for i, m in enumerate(page_members, start=start + 1):
            sel = CIRCLE_SELECTED if str(m.id) in self.selected_ids else CIRCLE_UNSELECTED
            desc_lines.append(f"{sel} `#{i}` **{m.mention}** ({m.name})")
        embed = discord.Embed(
            title=f"{EMOJI_FEATHER} Select Testers — {self.role_name}",
            description="\n".join(desc_lines) if desc_lines else "No members on this page.",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Selected: {len(self.selected_ids)} | Page {self.page + 1} of {self.total_pages}")
        return embed


class DeadlineModal(discord.ui.Modal, title="Set Testing Deadline"):
    days = discord.ui.TextInput(
        label="Days from now (1-30)",
        placeholder="e.g. 7",
        required=True,
        min_length=1,
        max_length=2,
    )

    def __init__(self, thread_id: int, bot):
        super().__init__()
        self.thread_id = thread_id
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        try:
            days = int(self.days.value)
            if days < 1 or days > 30:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        description=f"{CROSS} Please enter a number between 1 and 30.",
                        color=discord.Color.red(),
                    ),
                    ephemeral=True,
                )
        except ValueError:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} Invalid number.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        deadline_ts = int(time.time()) + days * 86400
        await _update_ticket_deadline(self.bot, self.thread_id, deadline_ts)

        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"{CHECK} Deadline set to <t:{deadline_ts}:F> (<t:{deadline_ts}:R>).",
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )
        thread = interaction.guild.get_thread(self.thread_id)
        if thread:
            await _refresh_thread_embed(thread, self.bot)


async def _publish_and_record(bot, payload: dict, guild: discord.Guild):
    player_id = int(payload.get('player_user_id'))
    tester_id = int(payload.get('tester_user_id'))
    attempted_rank_id = payload.get('attempted_rank_id')
    if attempted_rank_id:
        attempted_rank_id = int(attempted_rank_id)
    override_msg = payload.get('override_msg')

    player_member = guild.get_member(player_id)
    if player_member is None:
        try:
            player_member = await guild.fetch_member(player_id)
        except Exception:
            player_member = None

    tester_member = guild.get_member(tester_id)
    if tester_member is None:
        try:
            tester_member = await guild.fetch_member(tester_id)
        except Exception:
            tester_member = None

    if player_member and attempted_rank_id:
        try:
            await player_member.add_roles(guild.get_role(attempted_rank_id))
        except Exception:
            pass

    high_channel = guild.get_channel(RESULTS_CHANNEL_ID)
    results_msg = None

    if override_msg:
        results_msg = await high_channel.send(override_msg)
    else:
        username = payload.get('in_game_username') or payload.get('player_discord_username') or 'Unknown'
        embed = discord.Embed(title=f"{username}'s Results :trophy:", color=discord.Color.gold())
        embed.add_field(name=f"Tester", value=f"<@{tester_id}>", inline=True)
        embed.add_field(name=f"Region", value=payload.get('region'), inline=True)
        embed.add_field(name=f"In-game Username", value=f"[{username}](https://tierlist.mysticraft.xyz/?player={username})", inline=True)
        embed.add_field(name=f"Gamemode", value=payload.get('gamemode'), inline=True)
        embed.add_field(name=f"Previous Rank", value=payload.get('old_rank'), inline=True)
        embed.add_field(name=f"New Rank", value=payload.get('new_rank'), inline=True)
        embed.add_field(name=f"Scores", value=payload.get('score'), inline=True)
        if payload.get('remarks'):
            embed.add_field(name=f"Remarks", value=payload.get('remarks'), inline=True)
        embed.set_thumbnail(url=f"https://render.crafty.gg/3d/bust/{username}")
        results_msg = await high_channel.send(f"<@{player_id}>", embed=embed)
        try:
            await results_msg.add_reaction("🔥")
        except Exception:
            pass

    async with bot.tlresults_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SHOW TABLES LIKE 'tlresults'")
            res = await cursor.fetchone()
            if not res:
                await cursor.execute("""CREATE TABLE tlresults (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    player_discord_username VARCHAR(255),
                    player_user_id BIGINT,
                    uuid VARCHAR(36),
                    is_linked BOOLEAN NOT NULL DEFAULT FALSE,
                    region VARCHAR(10),
                    in_game_username VARCHAR(255),
                    score VARCHAR(255),
                    timestamp BIGINT,
                    old_rank VARCHAR(50),
                    new_rank VARCHAR(50),
                    gamemode VARCHAR(50),
                    remarks TEXT,
                    tester_discord_username VARCHAR(255),
                    tester_user_id BIGINT
                )""")
            await cursor.execute("""
                INSERT INTO tlresults (player_discord_username, player_user_id, uuid, is_linked, region, in_game_username, score, timestamp, old_rank, new_rank, gamemode, remarks, tester_discord_username, tester_user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                payload.get('player_discord_username'), payload.get('player_user_id'),
                payload.get('uuid'), payload.get('is_linked'), payload.get('region'),
                payload.get('in_game_username'), payload.get('score'), payload.get('timestamp'),
                payload.get('old_rank'), payload.get('new_rank'), payload.get('gamemode'),
                payload.get('remarks'), payload.get('tester_discord_username'),
                payload.get('tester_user_id')
            ))
            await conn.commit()

    ref_stats = db.reference("/Tierlist Tester Stats")
    existing = ref_stats.child(str(tester_id)).get() or {}
    old_rep = existing.get("count", 0) + 2 * existing.get("high_count", 0)
    old_tier = get_tier_index(old_rep)
    high_timestamps = existing.get("high_timestamps", [])
    high_timestamps.append(payload.get('timestamp'))
    high_count = len(high_timestamps)
    ref_stats.child(str(tester_id)).update({"high_count": high_count, "high_timestamps": high_timestamps})

    new_existing = ref_stats.child(str(tester_id)).get()
    new_rep = new_existing.get("count", 0) + 2 * new_existing.get("high_count", 0)
    new_tier = get_tier_index(new_rep)

    if new_tier > old_tier and tester_member:
        old_role_id = TIER_ROLES.get(old_tier)
        new_role_id = TIER_ROLES[new_tier]
        try:
            if old_role_id:
                await tester_member.remove_roles(guild.get_role(old_role_id))
            await tester_member.add_roles(guild.get_role(new_role_id))
        except Exception:
            pass
        channel = guild.get_channel(1467403596780929055)
        embed_desc = f"{EMOJI_RANK} <@{tester_id}> has reached **{TIER_THRESHOLDS[new_tier]}** reps and ranked up to `{TIER_NAMES[new_tier]}`!"
        if TIER_TO_MAIN[new_tier] > TIER_TO_MAIN.get(old_tier, -1):
            embed_desc += f"\n{EMOJI_REPLY} They also earned the <@&{new_role_id}> role!"
        rank_embed = discord.Embed(description=embed_desc, color=discord.Color.from_rgb(*tier_colors[new_tier]))
        await channel.send(content=f"<@{tester_id}>", embed=rank_embed)

    ref = db.reference("/HT Waitlist Cooldown")
    data = {guild.name: {"User ID": player_id, "Last Tested": payload.get('timestamp'), "Gamemode": payload.get('gamemode')}}
    ref.push().set(data)

    gamemode_short = DISPLAY_TO_SHORT.get(payload.get('gamemode'))
    if gamemode_short:
        try:
            item = return_item(gamemode_short)
            if player_member:
                try:
                    await player_member.remove_roles(guild.get_role(item[0]))
                except Exception:
                    pass
        except Exception:
            pass

    return results_msg


class FinalizeModal(discord.ui.Modal, title="Finalize Test Results"):
    def __init__(self, thread_id: int, user_id: int, user_ign: str, gamemode: str, current_rank: str, target_rank: str, bot):
        super().__init__()
        self.thread_id = thread_id
        for r in ["NA", "EU", "AS", "AU"]:
            self.region.component.add_option(label=r, value=r)
        for r in ["Pass", "Fail"]:
            self.result.component.add_option(label=r, value=r)
        self.user_id = user_id
        self.user_ign = user_ign
        self.gamemode = gamemode
        self.current_rank = current_rank
        self.target_rank = target_rank
        self.bot = bot

    region = discord.ui.Label(
        text="Region",
        component=discord.ui.RadioGroup(required=True),
    )
    scores = discord.ui.TextInput(
        label="Scores",
        placeholder="3-0",
        required=True,
        max_length=100,
    )
    result = discord.ui.Label(
        text="Pass or Fail",
        component=discord.ui.RadioGroup(required=True),
    )
    remarks = discord.ui.TextInput(
        label="Remarks (optional)",
        placeholder="Any additional notes",
        required=False,
        max_length=500,
        style=discord.TextStyle.paragraph,
    )

    async def on_submit(self, interaction: discord.Interaction):
        passed = self.result.component.value == "Pass"
        guild = interaction.guild
        player_member = guild.get_member(self.user_id)
        tester_member = interaction.user

        if _has_restricted_role(player_member) or _has_restricted_role(tester_member):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} Restricted users cannot be processed.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        if LINKED_ROLE_ID not in [role.id for role in tester_member.roles]:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{EMOJI_CONNECT} Account Linking Required for Testing",
                    description=f"To be eligible for testing, you must follow the instructions in <#1460525451368861818> to get linked.",
                    color=discord.Color.red(),
                ),
                ephemeral=True
            )

        if player_member and LINKED_ROLE_ID not in [role.id for role in player_member.roles]:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} This player is not linked. They must link their account to receive results.",
                    color=discord.Color.red(),
                ),
                ephemeral=True
            )

        linked, ign, linked_uuid = await is_linked(self.bot, self.user_id)
        username = ign or self.user_ign
        if not linked:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} Could not find linked account in database despite having the linked role.",
                    color=discord.Color.red(),
                ),
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        region = self.region.component.value
        scores_val = self.scores.value.strip()
        remarks_val = self.remarks.value.strip() or None

        attempted_rank_str = self.target_rank
        gamemode = self.gamemode

        is_reg = is_regulator(tester_member)

        previous_rank = self.current_rank
        remove_role = None
        if player_member:
            for role in player_member.roles:
                parts = role.name.split(" ")
                if len(parts) >= 2 and parts[1].upper() == gamemode.upper():
                    if parts[0] in RANK_CHAIN:
                        remove_role = role
                        previous_rank = parts[0]
                        break

        if player_member and remove_role:
            try:
                await player_member.remove_roles(remove_role)
            except Exception:
                pass

        attempted_role_name = f"{attempted_rank_str} {gamemode}"
        attempted_role = discord.utils.get(guild.roles, name=attempted_role_name)

        override_message = None
        new_rank = attempted_rank_str

        if not passed:
            fail_map = {"HT3": "LT3", "HT2": "LT2", "LT2": "HT3"}
            target_rank = fail_map.get(attempted_rank_str)
            override_message = f"<@{self.user_id}> - {username} - **Failed {attempted_rank_str} {gamemode} Test**\n\n> {scores_val} vs <@{tester_member.id}>"

            if target_rank:
                fallback_role_name = f"{target_rank} {gamemode}"
                fallback_role = discord.utils.get(guild.roles, name=fallback_role_name)
                if fallback_role:
                    attempted_role = fallback_role
                    new_rank = target_rank
                    fail_note = f"Failed {attempted_rank_str} Test"
                    remarks_val = f"{remarks_val} | {fail_note}" if remarks_val else fail_note
                else:
                    new_rank = "None"
                    attempted_role = None
            else:
                fail_note = f"Failed {attempted_rank_str} Test"
                remarks_val = f"{remarks_val} | {fail_note}" if remarks_val else fail_note
                new_rank = "None"
                attempted_role = None

        if player_member and attempted_role:
            try:
                await player_member.add_roles(attempted_role)
            except Exception:
                pass

        timestamp = int(time.time())

        embed = discord.Embed(title=f"{username}'s Results :trophy:", color=discord.Color.gold())
        embed.add_field(name=f"Tester", value=tester_member.mention, inline=True)
        embed.add_field(name=f"Region", value=region, inline=True)
        embed.add_field(name=f"In-game Username", value=f"[{username}](https://tierlist.mysticraft.xyz/?player={username})", inline=True)
        embed.add_field(name=f"Gamemode", value=gamemode, inline=True)
        embed.add_field(name=f"Previous Rank", value=previous_rank, inline=True)
        embed.add_field(name=f"New Rank", value=new_rank, inline=True)
        embed.add_field(name=f"Scores", value=scores_val, inline=True)
        if remarks_val:
            embed.add_field(name=f"Remarks", value=remarks_val, inline=True)
        embed.set_thumbnail(url=f"https://render.crafty.gg/3d/bust/{username}")

        player_name = player_member.name if player_member else str(self.user_id)

        payload = {
            'player_discord_username': player_name,
            'player_user_id': self.user_id,
            'uuid': linked_uuid,
            'is_linked': linked,
            'region': region,
            'in_game_username': username,
            'score': scores_val,
            'timestamp': timestamp,
            'old_rank': previous_rank,
            'new_rank': new_rank,
            'gamemode': gamemode,
            'remarks': remarks_val,
            'tester_discord_username': tester_member.name,
            'tester_user_id': tester_member.id,
            'attempted_rank_id': attempted_role.id if attempted_role else None,
            'attempted_rank_name': attempted_role.name if attempted_role else None,
            'submitted_by': tester_member.id,
            'override_msg': override_message,
            'thread_id': self.thread_id,
        }

        thread = guild.get_thread(self.thread_id)

        if is_reg:
            result_msg = await _publish_and_record(self.bot, payload, guild)
            if result_msg:
                await _update_ticket_status(self.bot, self.thread_id, 'completed')
                if thread:
                    await _refresh_thread_embed(thread, self.bot)
                if thread:
                    try:
                        await thread.edit(archived=True, locked=True)
                    except Exception:
                        pass
                if thread:
                    action_embed = discord.Embed(
                        title=f"{EMOJI_RANK} Results Posted",
                        description=f"{CHECK} Results have been posted to {guild.get_channel(RESULTS_CHANNEL_ID).mention}.",
                        color=discord.Color.green(),
                    )
                    try:
                        await thread.send(embeds=[action_embed, embed])
                    except Exception:
                        pass
                await interaction.followup.send(
                    embed=discord.Embed(
                        description=f"{CHECK} [Results posted]({result_msg.jump_url})",
                        color=discord.Color.green(),
                    ),
                )
            else:
                await interaction.followup.send(
                    embed=discord.Embed(
                        description=f"{CROSS} Failed to publish results.",
                        color=discord.Color.red(),
                    ),
                )
        else:
            review_channel = guild.get_channel(REVIEW_CHANNEL_ID)
            if not review_channel:
                return await interaction.followup.send(
                    embed=discord.Embed(
                        description=f"{CROSS} Review channel not found.",
                        color=discord.Color.red(),
                    ),
                    ephemeral=True,
                )

            view = HTApproveDenyView()
            thread_url = f"https://discord.com/channels/{guild.id}/{self.thread_id}"
            view.add_item(discord.ui.Button(label="Go to Thread", style=discord.ButtonStyle.link, url=thread_url))
            review_msg = await review_channel.send(f"<@{self.user_id}>", embed=embed, view=view)

            await _update_ticket_status(self.bot, self.thread_id, 'pending')
            if thread:
                await _refresh_thread_embed(thread, self.bot)

            try:
                db.reference('/Pending HT Results').child(str(review_msg.id)).set(payload)
            except Exception:
                pass

            action_embed = discord.Embed(
                title=f"{EMOJI_SCROLL} Submitted for Review",
                description=f"{EMOJI_HOURGLASS} Results have been sent for approval by a regulator. Please wait patiently.",
                color=discord.Color.orange(),
            )
            await interaction.followup.send(embeds=[action_embed, embed])


class HTApproveDenyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, custom_id="ht_testing_approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        allowed_roles = [1304851740226748556, 1460312013535318077, 1304848576190484553]
        if not any(role.id in allowed_roles for role in interaction.user.roles):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} You do not have permission to approve.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)
        review_msg_id = interaction.message.id

        try:
            ref = db.reference(f"/Pending HT Results/{review_msg_id}")
            payload = ref.get()
            if not payload:
                return await interaction.followup.send(
                    embed=discord.Embed(
                        description=f"{CROSS} Pending result not found.",
                        color=discord.Color.red(),
                    ),
                    ephemeral=True,
                )
        except Exception:
            return await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{CROSS} Firebase error.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        guild = interaction.guild
        thread_id = payload.get('thread_id')

        result_msg = await _publish_and_record(interaction.client, payload, guild)
        if not result_msg:
            return await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{CROSS} Failed to publish results.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        try:
            db.reference("/Pending HT Results").child(str(review_msg_id)).delete()
        except Exception:
            pass

        if thread_id:
            await _update_ticket_status(interaction.client, thread_id, 'completed')
            thread = guild.get_thread(thread_id)
            if thread:
                await _refresh_thread_embed(thread, interaction.client)
            if thread:
                try:
                    await thread.edit(archived=True, locked=True)
                except Exception:
                    pass

        for item in self.children:
            if item.style != discord.ButtonStyle.link:
                item.disabled = True
        await interaction.message.edit(content=f"{interaction.message.content}\n\n{CHECK} Approved by {interaction.user.mention}", view=self)
        await interaction.followup.send(
            embed=discord.Embed(
                description=f"{CHECK} Approved. [Results posted]({result_msg.jump_url}).",
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, custom_id="ht_testing_deny")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        allowed_roles = [1304851740226748556, 1460312013535318077, 1304848576190484553]
        if not any(role.id in allowed_roles for role in interaction.user.roles):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} You do not have permission to deny.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        thread_id = None
        try:
            ref = db.reference(f"/Pending HT Results/{interaction.message.id}")
            payload = ref.get()
            if payload:
                thread_id = payload.get('thread_id')
        except Exception:
            pass

        if thread_id:
            await _update_ticket_status(interaction.client, thread_id, 'denied')
            thread = interaction.client.get_channel(thread_id)
            if thread:
                await _refresh_thread_embed(thread, interaction.client)

        try:
            db.reference("/Pending HT Results").child(str(interaction.message.id)).delete()
        except Exception:
            pass

        for item in self.children:
            if item.style != discord.ButtonStyle.link:
                item.disabled = True
        await interaction.message.edit(content=f"{interaction.message.content}\n\n{CROSS} Denied by {interaction.user.mention}", view=self)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"{CROSS} Result denied.",
                color=discord.Color.red(),
            ),
            ephemeral=True,
        )


class BrowseFilterView(discord.ui.View):
    def __init__(self, tickets: list, bot, user_id: int = None):
        super().__init__(timeout=300)
        self.tickets = tickets
        self.bot = bot
        self.page = 0
        self.page_size = 10
        self.show_filters = user_id is None
        self.filters = {
            "gamemode": "all",
            "status": "all",
            "rank": "all",
            "user_id": user_id,
        }
        self._apply_filters()
        self._rebuild()

    def _apply_filters(self):
        self.filtered = list(self.tickets)
        if self.filters["gamemode"] != "all":
            self.filtered = [t for t in self.filtered if t[4] == self.filters["gamemode"]]
        if self.filters["status"] != "all":
            self.filtered = [t for t in self.filtered if t[7] == self.filters["status"]]
        if self.filters["rank"] != "all":
            self.filtered = [t for t in self.filtered if t[5] == self.filters["rank"] or t[6] == self.filters["rank"]]
        if self.filters["user_id"] is not None:
            self.filtered = [t for t in self.filtered if t[3] == self.filters["user_id"]]
        if self.page * self.page_size >= len(self.filtered):
            self.page = max(0, (len(self.filtered) - 1) // self.page_size) if self.filtered else 0

    def _rebuild(self):
        self.clear_items()
        total_pages = max(1, (len(self.filtered) + self.page_size - 1) // self.page_size)

        prev = discord.ui.Button(emoji=PREV_EMOJI, style=discord.ButtonStyle.grey, disabled=self.page == 0, row=0)
        prev.callback = self._make_prev_callback()
        self.add_item(prev)

        label = discord.ui.Button(label=f"Page {self.page + 1} of {total_pages}", style=discord.ButtonStyle.grey, disabled=True, row=0)
        self.add_item(label)

        nxt = discord.ui.Button(emoji=NEXT_EMOJI, style=discord.ButtonStyle.grey, disabled=self.page >= total_pages - 1, row=0)
        nxt.callback = self._make_next_callback()
        self.add_item(nxt)

        if not self.show_filters:
            return

        gm_options = [discord.SelectOption(label="All Gamemodes", value="all")]
        for display in GAMEMODE_DISPLAY.values():
            gm_options.append(discord.SelectOption(label=display, value=display))
        gm_select = discord.ui.Select(placeholder="Filter by Gamemode", options=gm_options, row=1)
        gm_select.callback = self._make_gamemode_callback(gm_select)
        self.add_item(gm_select)

        status_options = [
            discord.SelectOption(label="All Statuses", value="all"),
            discord.SelectOption(label="New", value="new"),
            discord.SelectOption(label="Ongoing", value="ongoing"),
            discord.SelectOption(label="Overdue", value="overdue"),
            discord.SelectOption(label="Pending Review", value="pending"),
            discord.SelectOption(label="Completed", value="completed"),
            discord.SelectOption(label="Denied", value="denied"),
            discord.SelectOption(label="Cancelled", value="cancelled"),
        ]
        rank_options = [discord.SelectOption(label="All Ranks", value="all")]
        for r in RANK_CHAIN:
            rank_options.append(discord.SelectOption(label=r, value=r))
        
        rank_select = discord.ui.Select(placeholder="Filter by Rank", options=rank_options, row=2)
        rank_select.callback = self._make_rank_callback(rank_select)
        self.add_item(rank_select)

        status_select = discord.ui.Select(placeholder="Filter by Status", options=status_options, row=3)
        status_select.callback = self._make_status_callback(status_select)
        self.add_item(status_select)

        user_select = discord.ui.UserSelect(placeholder="Filter by User", row=4)
        user_select.callback = self._make_user_callback(user_select)
        self.add_item(user_select)

        clear = discord.ui.Button(label="Clear Filters", style=discord.ButtonStyle.danger, row=0)
        clear.callback = self._make_clear_callback()
        self.add_item(clear)

    def _make_prev_callback(self):
        async def callback(interaction):
            if self.page > 0:
                self.page -= 1
            embed = self._build_embed()
            self._rebuild()
            await interaction.response.edit_message(embed=embed, view=self)
        return callback

    def _make_next_callback(self):
        async def callback(interaction):
            total = max(1, (len(self.filtered) + self.page_size - 1) // self.page_size)
            if self.page < total - 1:
                self.page += 1
            embed = self._build_embed()
            self._rebuild()
            await interaction.response.edit_message(embed=embed, view=self)
        return callback

    def _make_clear_callback(self):
        async def callback(interaction):
            self.page = 0
            self.filters = {"gamemode": "all", "status": "all", "rank": "all", "user_id": None}
            self._apply_filters()
            embed = self._build_embed()
            self._rebuild()
            await interaction.response.edit_message(embed=embed, view=self)
        return callback

    def _make_gamemode_callback(self, select):
        async def callback(interaction):
            self.filters["gamemode"] = select.values[0]
            self._apply_filters()
            embed = self._build_embed()
            self._rebuild()
            await interaction.response.edit_message(embed=embed, view=self)
        return callback

    def _make_status_callback(self, select):
        async def callback(interaction):
            self.filters["status"] = select.values[0]
            self._apply_filters()
            embed = self._build_embed()
            self._rebuild()
            await interaction.response.edit_message(embed=embed, view=self)
        return callback

    def _make_rank_callback(self, select):
        async def callback(interaction):
            self.filters["rank"] = select.values[0]
            self._apply_filters()
            embed = self._build_embed()
            self._rebuild()
            await interaction.response.edit_message(embed=embed, view=self)
        return callback

    def _make_user_callback(self, user_select):
        async def callback(interaction):
            if user_select.values:
                self.filters["user_id"] = user_select.values[0].id
            else:
                self.filters["user_id"] = None
            self._apply_filters()
            embed = self._build_embed()
            self._rebuild()
            await interaction.response.edit_message(embed=embed, view=self)
        return callback

    def _build_embed(self):
        embed = discord.Embed(title=f"<:globe:1523013604780146739> High Tier Testing Tickets Browser", color=discord.Color.blue())
        start = self.page * self.page_size
        end = start + self.page_size
        page_tickets = self.filtered[start:end]
        if not page_tickets:
            embed.description = "No tickets match your filters."
            return embed

        for t in page_tickets:
            thread_id, _, _, user_id, gamemode, cur_rank, tgt_rank, status, deadline, testers_json, created = t[:11]
            testers = json.loads(testers_json) if testers_json else []
            val = f"Opened on <t:{created}:d> | Player: <@{user_id}> | {EMOJI_FEATHER} Testers: {len(testers)}"
            if deadline:
                val += f" | {EMOJI_MC_CLOCK} Deadline <t:{deadline}:R>"
            embed.add_field(
                name=f"{EMOJI_GOLD} {gamemode} — {STATUS_LABELS.get(status, status.replace('_', ' ').title())}",
                value=f"-# <#{thread_id}> | {val}",
                inline=False,
            )
        total = max(1, (len(self.filtered) + self.page_size - 1) // self.page_size)
        embed.set_footer(text=f"Page {self.page + 1} of {total} | Total: {len(self.filtered)}")
        return embed


class HTCog(commands.Cog, name="ht_testing"):
    def __init__(self, bot):
        self.bot = bot
        self.deadline_check_task = None

    async def cog_load(self):
        # await ensure_tables(self.bot)
        self.deadline_check_task = asyncio.create_task(self._deadline_checker())

    async def cog_unload(self):
        if self.deadline_check_task:
            self.deadline_check_task.cancel()

    async def _deadline_checker(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                async with self.bot.tlresults_pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute(
                            "SELECT thread_id FROM ht_testing_tickets WHERE status IN ('new', 'ongoing') AND deadline IS NOT NULL AND deadline < %s",
                            (int(time.time()),)
                        )
                        overdue = await cursor.fetchall()
                for (thread_id,) in overdue:
                    await _update_ticket_status(self.bot, thread_id, 'overdue')
                    thread = self.bot.get_channel(thread_id)
                    if thread:
                        try:
                            await _refresh_thread_embed(thread, self.bot)
                            await thread.send(
                                embed=discord.Embed(
                                    description=f"{EMOJI_HOURGLASS} Deadline passed! <@&{REGULATOR_ROLE_ID}> please review this ticket.",
                                    color=discord.Color.orange(),
                                ),
                            )
                        except Exception:
                            pass
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Deadline checker error: {e}")
                await asyncio.sleep(60)

    async def show_browse_view(self, interaction: discord.Interaction, user_id: int = None):
        async with self.bot.tlresults_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT thread_id, channel_id, guild_id, user_id, gamemode, current_rank, target_rank, status, deadline, testers, created_at FROM ht_testing_tickets ORDER BY created_at DESC"
                )
                tickets = await cursor.fetchall()
        view = BrowseFilterView(tickets, self.bot, user_id=user_id)
        embed = view._build_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class HTTestingCmd(commands.GroupCog, name="ht_test"):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="panel", description="Post the HT testing panel in this channel")
    async def ht_panel(self, interaction: discord.Interaction):
        if not is_authorized(interaction.user):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} Only the bot owner can use this command.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        embed = discord.Embed(
            title=f"{EMOJI_TIERLIST} High Tier Testing",
            description=(
                f"Select a gamemode below to start a test request for HT3 or above. A thread will be created for your test. Please wait patiently for a regulator to assign you testers.\n\n"
                f"{EMOJI_RANK} You must have either **LT3, HT3, LT2, HT2** in the selected gamemode to request a high tier test.\n"
            ),
            color=discord.Color.blue(),
        )

        view = HTTestingPanelView()
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"{CHECK} Panel posted.",
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )

    @app_commands.command(name="results", description="Post a high tier test result (manager only)")
    @app_commands.describe(
        user="The player who was tested",
        gamemode="The gamemode",
        current_rank="Their current rank",
        target_rank="The rank they tested for",
        score="Score or result description",
        tester="The tester (defaults to you)",
        remarks="Optional remarks",
    )
    @app_commands.choices(
        gamemode=[app_commands.Choice(name=d, value=s) for s, d in GAMEMODE_DISPLAY.items()],
        current_rank=[app_commands.Choice(name=r, value=r) for r in RANK_CHAIN],
        target_rank=[app_commands.Choice(name=r, value=r) for r in RANK_CHAIN],
    )
    async def ht_results(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        gamemode: app_commands.Choice[str],
        current_rank: app_commands.Choice[str],
        target_rank: app_commands.Choice[str],
        score: str,
        tester: discord.Member = None,
        remarks: str = None,
    ):
        allowed_roles = [1304851740226748556, 1460312013535318077, 1304848576190484553]
        if not any(role.id in allowed_roles for role in interaction.user.roles):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} Managers only.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        await interaction.response.defer()
        gamemode_display = GAMEMODE_DISPLAY.get(gamemode.value, gamemode.value.upper())
        tester_user = tester or interaction.user
        linked, ign, uuid = await is_linked(self.bot, user.id)
        timestamp = int(time.time())

        async with self.bot.tlresults_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO tlresults (player_discord_username, player_user_id, uuid, is_linked, region, in_game_username, score, timestamp, old_rank, new_rank, gamemode, remarks, tester_discord_username, tester_user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user.name, user.id, uuid, linked, 'N/A', ign or user.name,
                    score, timestamp, current_rank.value, target_rank.value,
                    gamemode_display, remarks or 'N/A', tester_user.name, tester_user.id
                ))
                await conn.commit()

        rank_role_name = f"{target_rank.value} {gamemode_display}"
        rank_role = discord.utils.get(interaction.guild.roles, name=rank_role_name)
        if rank_role:
            try:
                for role in user.roles:
                    parts = role.name.split(" ")
                    if len(parts) >= 2 and parts[1].upper() == gamemode_display.upper():
                        await user.remove_roles(role)
                        break
                await user.add_roles(rank_role)
            except Exception:
                pass

        channel = interaction.guild.get_channel(RESULTS_CHANNEL_ID)
        embed = discord.Embed(title=f"{ign or user.name}'s Results :trophy:", color=discord.Color.gold())
        embed.add_field(name=f"Tester", value=tester_user.mention, inline=True)
        embed.add_field(name=f"Region", value="N/A", inline=True)
        embed.add_field(name=f"In-game Username", value=f"[{ign or user.name}](https://tierlist.mysticraft.xyz/?player={ign or user.name})", inline=True)
        embed.add_field(name=f"Gamemode", value=gamemode_display, inline=True)
        embed.add_field(name=f"Previous Rank", value=current_rank.value, inline=True)
        embed.add_field(name=f"New Rank", value=target_rank.value, inline=True)
        embed.add_field(name=f"Scores", value=score, inline=True)
        if remarks:
            embed.add_field(name=f"Remarks", value=remarks, inline=True)
        if ign:
            embed.set_thumbnail(url=f"https://render.crafty.gg/3d/bust/{ign}")

        if channel:
            msg = await channel.send(f"<@{user.id}>", embed=embed)
            await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{CHECK} [Results posted]({msg.jump_url})",
                    color=discord.Color.green(),
                ),
            )
        else:
            await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{CHECK} Results recorded (channel not found).",
                    color=discord.Color.green(),
                ),
            )


    @app_commands.command(name="cleanup", description="Clean up ht_testing database entries (owner only)")
    @app_commands.describe(
        target="What to clean",
        user_id="Discord user ID (for user-specific cleanup)",
        thread_id="Thread ID (for thread-specific cleanup)",
        gamemode="Gamemode to filter by",
    )
    @app_commands.choices(
        target=[
            app_commands.Choice(name="All completed/cancelled tickets", value="old_tickets"),
            app_commands.Choice(name="All cooldowns", value="all_cooldowns"),
            app_commands.Choice(name="All tickets for a user", value="user_tickets"),
            app_commands.Choice(name="All cooldowns for a user", value="user_cooldowns"),
            app_commands.Choice(name="Specific thread ticket", value="thread"),
            app_commands.Choice(name="All data (both tables)", value="all"),
        ]
    )
    async def ht_cleanup(
        self,
        interaction: discord.Interaction,
        target: str,
        user_id: str = None,
        thread_id: str = None,
        gamemode: str = None,
    ):
        if not is_authorized(interaction.user):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} Only the bot owner can use this command.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)

        deleted_tickets = 0
        deleted_cooldowns = 0

        async with self.bot.tlresults_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if target == "old_tickets":
                    await cursor.execute(
                        "DELETE FROM ht_testing_tickets WHERE status IN ('completed', 'cancelled', 'denied')"
                    )
                    deleted_tickets = cursor.rowcount

                elif target == "all_cooldowns":
                    await cursor.execute("DELETE FROM ht_testing_cooldowns")
                    deleted_cooldowns = cursor.rowcount

                elif target == "user_tickets":
                    if not user_id:
                        return await interaction.followup.send(
                            embed=discord.Embed(
                                description=f"{CROSS} Provide a `user_id`.",
                                color=discord.Color.red(),
                            ),
                            ephemeral=True,
                        )
                    await cursor.execute(
                        "DELETE FROM ht_testing_tickets WHERE user_id = %s",
                        (int(user_id),)
                    )
                    deleted_tickets = cursor.rowcount

                elif target == "user_cooldowns":
                    if not user_id:
                        return await interaction.followup.send(
                            embed=discord.Embed(
                                description=f"{CROSS} Provide a `user_id`.",
                                color=discord.Color.red(),
                            ),
                            ephemeral=True,
                        )
                    await cursor.execute(
                        "DELETE FROM ht_testing_cooldowns WHERE user_id = %s",
                        (int(user_id),)
                    )
                    deleted_cooldowns = cursor.rowcount

                elif target == "thread":
                    if not thread_id:
                        return await interaction.followup.send(
                            embed=discord.Embed(
                                description=f"{CROSS} Provide a `thread_id`.",
                                color=discord.Color.red(),
                            ),
                            ephemeral=True,
                        )
                    await cursor.execute(
                        "DELETE FROM ht_testing_tickets WHERE thread_id = %s",
                        (int(thread_id),)
                    )
                    deleted_tickets = cursor.rowcount

                elif target == "all":
                    await cursor.execute("DELETE FROM ht_testing_tickets")
                    deleted_tickets = cursor.rowcount
                    await cursor.execute("DELETE FROM ht_testing_cooldowns")
                    deleted_cooldowns = cursor.rowcount

                await conn.commit()

        parts = [f"{EMOJI_EMERALD} Cleanup complete."]
        if deleted_tickets is not None:
            parts.append(f"-# {EMOJI_REPLY} Deleted `{deleted_tickets}` ticket(s).")
        if deleted_cooldowns is not None:
            parts.append(f"-# {EMOJI_REPLY} Deleted `{deleted_cooldowns}` cooldown(s).")
        await interaction.followup.send(
            embed=discord.Embed(
                description="\n".join(parts),
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(HTCog(bot))
    await bot.add_cog(HTTestingCmd(bot))
