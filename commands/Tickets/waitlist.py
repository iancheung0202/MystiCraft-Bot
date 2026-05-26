import discord
import datetime
import re
import emoji
import time
import asyncio
import io
import aiohttp
from urllib.parse import quote_plus

from discord import app_commands
from discord.ext import commands
from firebase_admin import db
from typing import List, Dict

# Tier definitions for rep roles
TIER_THRESHOLDS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 120, 140, 160, 190, 220, 250, 290, 330, 370, 420, 470, 500]
TIER_NAMES = [
    "Leather I", "Leather II", "Leather III",
    "Iron I", "Iron II", "Iron III",
    "Gold I", "Gold II", "Gold III",
    "Diamond I", "Diamond II", "Diamond III",
    "Emerald I", "Emerald II", "Emerald III",
    "Amethyst I", "Amethyst II", "Amethyst III",
    "Crimson I", "Crimson II", "Crimson III",
    "Crown Tier"
]
TIER_ROLES = {
    0: 1467403902667460775, 1: 1467403902667460775, 2: 1467403902667460775,  # Leather
    3: 1467403910196232408, 4: 1467403910196232408, 5: 1467403910196232408,  # Iron
    6: 1467403910724587571, 7: 1467403910724587571, 8: 1467403910724587571,  # Gold
    9: 1467403911433293928, 10: 1467403911433293928, 11: 1467403911433293928,  # Diamond
    12: 1467403911882084412, 13: 1467403911882084412, 14: 1467403911882084412,  # Emerald
    15: 1467404857047515177, 16: 1467404857047515177, 17: 1467404857047515177,  # Amethyst
    18: 1467404939251679437, 19: 1467404939251679437, 20: 1467404939251679437,  # Crimson
    21: 1467404979709939927  # Crown
}
MAIN_TIERS = ["Leather", "Iron", "Gold", "Diamond", "Emerald", "Amethyst", "Crimson", "Crown"]
TIER_TO_MAIN = {
    0: 0, 1: 0, 2: 0,
    3: 1, 4: 1, 5: 1,
    6: 2, 7: 2, 8: 2,
    9: 3, 10: 3, 11: 3,
    12: 4, 13: 4, 14: 4,
    15: 5, 16: 5, 17: 5,
    18: 6, 19: 6, 20: 6,
    21: 7
}

tier_colors = {
        0: (139, 69, 19), 1: (139, 69, 19), 2: (139, 69, 19),  # Leather brown
        3: (128, 128, 128), 4: (128, 128, 128), 5: (128, 128, 128),  # Iron gray
        6: (255, 215, 0), 7: (255, 215, 0), 8: (255, 215, 0),  # Gold yellow
        9: (0, 191, 255), 10: (0, 191, 255), 11: (0, 191, 255),  # Diamond blue
        12: (0, 128, 0), 13: (0, 128, 0), 14: (0, 128, 0),  # Emerald green
        15: (128, 0, 128), 16: (128, 0, 128), 17: (128, 0, 128),  # Amethyst purple
        18: (220, 20, 60), 19: (220, 20, 60), 20: (220, 20, 60),  # Crimson red
        21: (255, 215, 0)  # Crown gold
    }

def get_tier_index(rep_total):
    for i, thresh in enumerate(TIER_THRESHOLDS):
        if rep_total >= thresh:
            continue
        else:
            return i - 1 if i > 0 else 0
    return len(TIER_THRESHOLDS) - 1  # Max tier


def return_item(obj):
    # Waitlist Role ID, Waitlist Channel ID, Tester Role ID
    if "npot" in obj:
        item = [1307373700848554074, 1337057627661926533, 1305574148201906269]
    elif "dpot" in obj:
        item = [1308828456615940189, 1337057604907700224, 1305916012364828712]
    elif "smp" in obj:
        item = [1337061671520440330, 1337057681776836629, 1305934684026441759]
    elif "sword" in obj:
        item = [1337061742601179189, 1337062543780483137, 1309889388532072478]
    elif "crystal" in obj:
        item = [1337061820547993650, 1337062560150720562, 1338251533065650236]
    elif "axe" in obj:
        item = [1337061861488726071, 1337073373393715262, 1338251536467230730]
    elif "mace" in obj:
        item = [1337073432466034772, 1338250590299488399, 1338251539583860809]
    elif "uhc" in obj:
        item = [1338251110464622685, 1338250613829406741, 1338251541248741529]
    return item

AUTHORIZED_USERS = [692254240290242601, 840972960793100309]
LINKED_ROLE_ID = 1459863162223595656
LINKED_LOG_CHANNEL_ID = 1460005738897473706
RESTRICTED_ROLE_ID = 1340417478857068564

TIER_ROLE_PREFIXES = {"HT1", "LT1", "HT2", "LT2", "HT3", "LT3", "HT4", "LT4", "HT5", "LT5"}
TIER_SYNC_GAMEMODES = {"NPOT", "DPOT", "SMP", "SWORD", "CRYSTAL", "AXE", "MACE", "UHC"}


def _is_tier_role(role: discord.Role) -> bool:
    parts = role.name.split(" ")
    return len(parts) >= 2 and parts[0].upper() in TIER_ROLE_PREFIXES and parts[1].upper() in TIER_SYNC_GAMEMODES


def _extract_tier_role_name(rank_data) -> str | None:
    if not rank_data:
        return None

    if isinstance(rank_data, dict):
        tier_type = str(rank_data.get("type", "")).strip()
        tier_value = str(rank_data.get("tier", "")).strip()
        label = f"{tier_type}{tier_value}".strip()
    else:
        label = str(rank_data).strip()

    if not label or label.upper() in {"N/A", "NONE", "UNRANKED", "-"}:
        return None

    return label


async def _get_linked_player_name(bot, discord_id: int) -> str | None:
    try:
        async with bot.tllink_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SHOW TABLES")
                result = await cursor.fetchone()
                link_table = result[0] if result else "mystilinking"
                await cursor.execute(
                    f"SELECT player_name FROM {link_table} WHERE discord_id = %s",
                    (str(discord_id),),
                )
                row = await cursor.fetchone()
                return row[0] if row else None
    except Exception as e:
        print(f"Error fetching linked IGN for {discord_id}: {e}")
        return None


async def _fetch_tier_profile(player_name: str):
    api_url = f"https://tierlist.mysticraft.xyz/api/player/{quote_plus(player_name)}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"}
    timeout = aiohttp.ClientTimeout(total=15)

    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        async with session.get(api_url) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Tier API returned status {resp.status}")
            return await resp.json()


def _collect_tier_roles(guild: discord.Guild, data: dict) -> tuple[list[discord.Role], list[str]]:
    ranks = data.get("ranks", {}) if isinstance(data, dict) else {}
    role_matches: list[discord.Role] = []
    missing_roles: list[str] = []

    for mode in ["NPOT", "DPOT", "SMP", "SWORD", "CRYSTAL", "AXE", "MACE", "UHC"]:
        rank_label = _extract_tier_role_name(ranks.get(mode))
        if not rank_label:
            continue

        expected_name = f"{rank_label} {mode}"
        match = next((role for role in guild.roles if role.name.upper() == expected_name.upper()), None)
        if match:
            role_matches.append(match)
        else:
            missing_roles.append(expected_name)

    return role_matches, missing_roles


async def _sync_tier_roles_for_member(guild: discord.Guild, member: discord.Member, ign: str, old_member: discord.Member = None):
    profile_data = await _fetch_tier_profile(ign)
    target_roles, missing_roles = _collect_tier_roles(guild, profile_data)

    current_target_roles = [role for role in member.roles if _is_tier_role(role)]
    target_role_ids = {role.id for role in target_roles}
    current_role_ids = {role.id for role in member.roles}

    remove_from_target = [role for role in current_target_roles if role.id not in target_role_ids]
    add_to_target = [role for role in target_roles if role.id not in current_role_ids]

    if remove_from_target:
        await member.remove_roles(*remove_from_target, reason=f"Tier role sync for {ign}")
    if add_to_target:
        await member.add_roles(*add_to_target, reason=f"Tier role sync for {ign}")

    removed_old_roles = []
    if old_member:
        removed_old_roles = [role for role in old_member.roles if _is_tier_role(role)]
        if removed_old_roles:
            await old_member.remove_roles(*removed_old_roles, reason=f"Tier role migration to {member.id}")

    return target_roles, missing_roles, removed_old_roles


async def _remove_tier_roles_from_member(member: discord.Member) -> list[discord.Role]:
    removed_roles = [role for role in member.roles if _is_tier_role(role)]
    if removed_roles:
        await member.remove_roles(*removed_roles, reason="Tier link removed")
    return removed_roles


async def _sync_member_from_link(bot, guild: discord.Guild, member_id: int) -> tuple[list[discord.Role], list[str]]:
    ign = await _get_linked_player_name(bot, member_id)
    if not ign:
        return [], []

    member = guild.get_member(member_id)
    if not member:
        try:
            member = await guild.fetch_member(member_id)
        except Exception:
            return [], []

    target_roles, missing_roles, _ = await _sync_tier_roles_for_member(guild, member, ign)
    return target_roles, missing_roles


async def _get_linked_discord_ids_for_player(bot, player_name: str) -> list[int]:
    try:
        async with bot.tllink_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SHOW TABLES")
                result = await cursor.fetchone()
                link_table = result[0] if result else "mystilinking"
                await cursor.execute(
                    f"SELECT discord_id FROM {link_table} WHERE LOWER(player_name) = LOWER(%s)",
                    (player_name,),
                )
                rows = await cursor.fetchall()
                discord_ids = []
                for row in rows:
                    try:
                        discord_ids.append(int(row[0]))
                    except Exception:
                        continue
                return discord_ids
    except Exception as e:
        print(f"Error fetching linked discord ids for {player_name}: {e}")
        return []


def _has_restricted_role(member: discord.Member | discord.User | None) -> bool:
    return bool(member and getattr(member, "roles", None) and any(role.id == RESTRICTED_ROLE_ID for role in member.roles))


async def _deny_if_restricted(interaction: discord.Interaction, *members, message: str = "<:cross1:1339153202859474956> This user is restricted from using waitlist actions.") -> bool:
    if any(_has_restricted_role(member) for member in members if member is not None):
        await interaction.response.send_message(message, ephemeral=True)
        return True
    return False


async def _apply_blacklist(guild: discord.Guild, member: discord.Member):
    removed_roles = await _remove_tier_roles_from_member(member)
    restricted_role = guild.get_role(RESTRICTED_ROLE_ID)
    if restricted_role and restricted_role not in member.roles:
        await member.add_roles(restricted_role, reason="Waitlist blacklist")
    return removed_roles

# Queue Management Constants
BOOSTER_ROLE_ID = 1307344085358481431
BOOSTER_EMOJI = "<:boosting:1466562469773443367>"


class QueueEntry:
    """Represents a single queue entry."""
    def __init__(self, user_id: int, mention: str, username: str, is_booster: bool, join_time: int = None):
        self.user_id = user_id
        self.mention = mention
        self.username = username
        self.is_booster = is_booster
        self.join_time = join_time if join_time is not None else int(time.time())

    def to_string(self, position: int) -> str:
        """Convert to embed-displayable string."""
        display = f"{self.mention} (joined <t:{self.join_time}:R>)"
        if self.is_booster:
            display += f" {BOOSTER_EMOJI}"
        return f"{position}. {display}"


class QueueOperation:
    """Represents a queued operation (join/leave)."""
    def __init__(self, op_type: str, user_id: int, member: discord.Member, interaction: discord.Interaction, is_booster: bool = False):
        self.op_type = op_type  # "JOIN" or "LEAVE"
        self.user_id = user_id
        self.member = member
        self.interaction = interaction
        self.is_booster = is_booster
        self.timestamp = time.time()


class QueueManager:
    """Manages a single gamemode's queue with atomic operations via asyncio.Queue."""
    
    def __init__(self, gamemode: str, bot):
        self.gamemode = gamemode
        self.bot = bot
        self.queue: List[QueueEntry] = []
        self.operation_queue = asyncio.Queue()
        self.worker_task = None
        self.sync_task = None
        self.queue_message_id = None
        self.queue_channel_id = None
        self.active_sessions: Dict[int, int] = {}  # Maps member_id -> tester_id for currently serving
        self._lock = asyncio.Lock()  # For concurrent access to internal queue state
        self._last_state_hash = None  # Track last synced state to detect changes
        self.last_closed_time = None  # Track when queue was last closed
    
    async def start_worker(self):
        """Start the worker task that processes operations."""
        if self.worker_task is None:
            self.worker_task = asyncio.create_task(self._worker())
        if self.sync_task is None:
            self.sync_task = asyncio.create_task(self._embed_sync_loop())
    
    async def stop_worker(self):
        """Stop the worker task."""
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
            self.sync_task = None
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            self.worker_task = None
    
    async def _worker(self):
        """Worker task that processes operations one-by-one."""
        while True:
            try:
                operation = await self.operation_queue.get()
                await self._process_operation(operation)
                self.operation_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error processing queue operation for {self.gamemode}: {e}")
    
    async def _process_operation(self, op: QueueOperation):
        """Process a single operation atomically."""
        async with self._lock:
            try:
                if op.op_type == "JOIN":
                    await self._handle_join(op)
                elif op.op_type == "LEAVE":
                    await self._handle_leave(op)
            except Exception as e:
                print(f"Error in _process_operation: {e}")
    
    async def _handle_join(self, op: QueueOperation):
        """Handle a join operation. Internal data update only."""
        # Check if already in queue (safety check, though callback handles this)
        if any(e.user_id == op.user_id for e in self.queue):
            return

        # Create entry
        entry = QueueEntry(
            user_id=op.user_id,
            mention=op.member.mention,
            username=op.member.name,
            is_booster=op.is_booster,
            join_time=int(time.time())
        )
        
        # Insert logic: boosters go after last booster, non-boosters go at end
        if op.is_booster:
            last_booster_idx = -1
            for i, e in enumerate(self.queue):
                if e.is_booster:
                    last_booster_idx = i
            
            self.queue.insert(last_booster_idx + 1, entry)
        else:
            self.queue.append(entry)

    async def _handle_leave(self, op: QueueOperation):
        """Handle a leave operation. Internal data update only."""
        # Simple list comprehension to remove the user
        self.queue = [e for e in self.queue if e.user_id != op.user_id]
    
    def _get_state_hash(self) -> str:
        """Generate a hash of current queue state to detect changes."""
        queue_str = "|".join([str(e.user_id) for e in self.queue])
        active_str = "|".join([f"{k}:{v}" for k, v in sorted(self.active_sessions.items())])
        return f"{queue_str}#{active_str}"
    
    async def _embed_sync_loop(self):
        """Periodically sync embed every 5 seconds if queue state changed."""
        while True:
            try:
                await asyncio.sleep(5)
                current_state = self._get_state_hash()
                if current_state != self._last_state_hash:
                    await self._sync_embed()
                    self._last_state_hash = current_state
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in embed sync loop for {self.gamemode}: {e}")
    
    async def _sync_embed(self):
        """Fetch the queue message and update the embed with current state."""
        if not self.queue_channel_id:
            return
        
        try:
            channel = self.bot.get_channel(self.queue_channel_id)
            if not channel:
                return
            
            # Find the queue message
            async for msg in channel.history(limit=10):
                if msg.author.id == self.bot.application_id and msg.embeds:
                    if "Tester(s) Available!" in msg.embeds[0].title or "No Testers Online" in msg.embeds[0].title:
                        embed = msg.embeds[0]
                        
                        # Build queue string - only show first 15 users
                        if self.queue:
                            display_queue = self.queue[:15]
                            queue_lines = [e.to_string(i + 1) for i, e in enumerate(display_queue)]
                            queue_string = "\n".join(queue_lines)
                            if len(self.queue) > 15:
                                queue_string += f"\n-# ... and {len(self.queue) - 15} more in queue"
                        else:
                            queue_string = "Empty"
                        
                        # Build active testers string
                        if self.active_sessions:
                            active_lines = []
                            for i, (member_id, tester_id) in enumerate(self.active_sessions.items(), 1):
                                active_lines.append(f"{i}. <@{member_id}> (being served by <@{tester_id}>)")
                            active_string = "\n".join(active_lines)
                        else:
                            active_string = "N/A"
                        
                        embed.set_field_at(0, name="Queue", value=queue_string, inline=False)
                        embed.set_field_at(1, name="Currently Serving", value=active_string, inline=False)
                        await msg.edit(embed=embed)
                        break
        except Exception as e:
            print(f"Error syncing embed for {self.gamemode}: {e}")
    
    def set_message_location(self, channel_id: int, message_id: int = None):
        """Set the channel/message location for this queue."""
        self.queue_channel_id = channel_id
        self.queue_message_id = message_id
    
    async def enqueue_join(self, user_id: int, member: discord.Member, interaction: discord.Interaction, is_booster: bool):
        """Enqueue a join operation."""
        operation = QueueOperation("JOIN", user_id, member, interaction, is_booster)
        await self.operation_queue.put(operation)
    
    async def enqueue_leave(self, user_id: int, member: discord.Member, interaction: discord.Interaction):
        """Enqueue a leave operation."""
        operation = QueueOperation("LEAVE", user_id, member, interaction, is_booster=False)
        await self.operation_queue.put(operation)
    
    def get_queue_copy(self) -> List[QueueEntry]:
        """Get a copy of the current queue."""
        return self.queue.copy()
    
    async def pop_first(self) -> QueueEntry:
        """Remove and return the first user in queue."""
        async with self._lock:
            if self.queue:
                return self.queue.pop(0)
            return None
    
    def set_active_sessions(self, sessions: Dict[int, int]):
        """Update the active testing sessions (member_id -> tester_id)."""
        self.active_sessions = sessions.copy()
    
    def add_active_session(self, member_id: int, tester_id: int):
        """Add an active testing session."""
        self.active_sessions[member_id] = tester_id
    
    def remove_active_session(self, member_id: int):
        """Remove an active testing session."""
        if member_id in self.active_sessions:
            del self.active_sessions[member_id]
    
    def mark_closed(self):
        """Mark the queue as closed (preserves queue data for quick reopens)."""
        self.last_closed_time = int(time.time())
    
    def should_clear_on_start(self) -> bool:
        """Check if queue should be cleared on start (more than 10 minutes since last closure)."""
        if self.last_closed_time is None:
            return False
        time_since_close = int(time.time()) - self.last_closed_time
        return time_since_close > 600  # 10 minutes
    
    def clear_active_sessions(self):
        """Clear only the active testing sessions."""
        self.active_sessions.clear()
    
    def clear(self):
        """Clear all queue and session data."""
        self.queue.clear()
        self.active_sessions.clear()
        self._last_state_hash = None
        self.last_closed_time = None


class QueueManagerPool:
    """Manages QueueManager instances for all gamemodes."""
    
    def __init__(self, bot):
        self.bot = bot
        self.managers: Dict[str, QueueManager] = {}
    
    def get_manager(self, gamemode: str) -> QueueManager:
        """Get or create a QueueManager for the given gamemode."""
        if gamemode not in self.managers:
            manager = QueueManager(gamemode, self.bot)
            self.managers[gamemode] = manager
            asyncio.create_task(manager.start_worker())
        return self.managers[gamemode]
    
    async def shutdown(self):
        """Shutdown all managers."""
        for manager in self.managers.values():
            await manager.stop_worker()


class WaitlistSelection(discord.ui.Select):
    def __init__(self, placeholder, options):
        super().__init__(
            placeholder=placeholder,
            max_values=1,
            min_values=1,
            options=options,
            custom_id="waitlistcreation",
        )

    async def callback(self, interaction: discord.Interaction):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        await interaction.response.defer()
        selectedValue = self.values[0]

        ref = db.reference("/Waitlist Cooldown")
        ticketcooldown = ref.get()
        cooldown = None
        try:
            for key, value in ticketcooldown.items():
                if (value["User ID"] == interaction.user.id) and (
                    value["Gamemode"] == selectedValue
                ):
                    ogtimestamp = value["Last Tested"]
                    if (
                        int(interaction.created_at.timestamp()) - int(ogtimestamp)
                    ) < 172800:
                        cooldown = ogtimestamp
        except Exception:
            pass

        if cooldown != None:
            return await interaction.followup.send(
                f"<:cross1:1339153202859474956> You cannot join the **{selectedValue}** waitlist since you are on a cooldown. Try again <t:{cooldown + 172800}:R>.",
                ephemeral=True,
            )

        item = return_item(selectedValue.lower())

        haveRole = False
        for role in interaction.user.roles:
            if role.id == item[0]:
                haveRole = True

        if haveRole:
            await interaction.user.remove_roles(interaction.guild.get_role(item[0]))
            embed = discord.Embed(
                title=f"You've been removed from the {selectedValue} waitlist.",
                colour=0xFF0000,
            )
            if interaction.user.avatar:
                embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url)
            else:
                embed.set_author(name=interaction.user.name)
            await interaction.followup.send(embed=embed, ephemeral=True)

        elif not (haveRole):  # doesn't have role
            await interaction.user.add_roles(interaction.guild.get_role(item[0]))
            embeds = []
            embed = discord.Embed(
                title=f"You've been added to the {selectedValue} waitlist.",
                description=f"You now have access to <#{item[1]}>",
                colour=0x008000,
            )
            if interaction.user.avatar:
                embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url)
            else:
                embed.set_author(name=interaction.user.name)
            embeds.append(embed)
            if LINKED_ROLE_ID not in [role.id for role in interaction.user.roles]:
                embeds.append(
                    discord.Embed(
                        title="<:warn:1459986909911842846> **Account Linking Required for Testing**",
                        description=f"> To be eligible for testing, you must follow the instructions in <#1460525451368861818> to get linked. Once completed, you will automatically receive the <@&{LINKED_ROLE_ID}> role and gain access to the queue.",
                        color=discord.Colour.red(),
                    )
                )
            await interaction.followup.send(embeds=embeds, ephemeral=True)


class WaitlistSelectionView(discord.ui.View):
    def __init__(self, placeholder=None, options=None, *, timeout=None):
        super().__init__(timeout=timeout)
        self.add_item(WaitlistSelection(placeholder, options))


class JoinQueueButton(discord.ui.Button):
    def __init__(self, title, color, queue_manager=None):
        super().__init__(label=title, style=color, custom_id="joinqueue")
        self.queue_manager = queue_manager

    async def callback(self, interaction: discord.Interaction):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        if LINKED_ROLE_ID not in [role.id for role in interaction.user.roles]:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="<:warn:1459986909911842846> **Account Linking Required for Testing**",
                    description=f"> To be eligible for testing, you must follow the instructions in <#1460525451368861818> to get linked. Once completed, you will automatically receive the <@&{LINKED_ROLE_ID}> role and gain access to the queue.",
                    color=discord.Colour.red(),
                ),
                ephemeral=True,
            )

        if not self.queue_manager:
            return await interaction.response.send_message(
                "<:cross1:1339153202859474956> Sorry, something went terribly wrong. `[Error Code: 1]`",
                ephemeral=True
            )

        # 1. Check if they are already in the internal queue list
        existing_pos = None
        for i, e in enumerate(self.queue_manager.queue):
            if e.user_id == interaction.user.id:
                existing_pos = i + 1
                break

        # 2. ALSO check if they are currently waiting in the operation queue
        # This prevents people who clicked 1 second ago from joining again
        is_waiting_in_ops = False
        if not existing_pos:
            # We look at the internal buffer of the asyncio Queue
            for op in list(self.queue_manager.operation_queue._queue):
                if op.user_id == interaction.user.id and op.op_type == "JOIN":
                    is_waiting_in_ops = True
                    break

        if existing_pos or is_waiting_in_ops:
            msg = f"<:cross1:1339153202859474956> You are already in the queue!"
            if existing_pos:
                msg += f" Position: **{existing_pos}**"
            
            return await interaction.response.send_message(msg, ephemeral=True)

        # 3. Calculate predicted position
        predicted_pos = len(self.queue_manager.queue) + self.queue_manager.operation_queue.qsize() + 1

        # 4. Respond IMMEDIATELY
        await interaction.response.send_message(
            f"<:checkmark:1339153448926580818> You've been added to the queue! Position: **{predicted_pos}**\n"
            f"<:reply:1036792837821435976> *Note that you are not guaranteed to be tested, especially if you are in a long queue.* <:warn:1459986909911842846>",
            ephemeral=True
        )

        # 5. Enqueue for worker
        self.queue_manager.set_message_location(interaction.channel_id, interaction.message.id)
        is_booster = any(role.id == BOOSTER_ROLE_ID for role in interaction.user.roles)
        await self.queue_manager.enqueue_join(interaction.user.id, interaction.user, interaction, is_booster)


class LeaveQueueButton(discord.ui.Button):
    def __init__(self, title, color, queue_manager=None):
        super().__init__(label=title, style=color, custom_id="leavequeue")
        self.queue_manager = queue_manager

    async def callback(self, interaction: discord.Interaction):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        if await _deny_if_restricted(interaction, interaction.user):
            return
        if not self.queue_manager:
            return await interaction.response.send_message("<:cross1:1339153202859474956> Sorry, something went terribly wrong. `[Error Code: 2]`", ephemeral=True)

        # Check if they are actually in the queue
        is_in_queue = any(e.user_id == interaction.user.id for e in self.queue_manager.queue)
        
        if not is_in_queue:
            return await interaction.response.send_message(
                "<:cross1:1339153202859474956> You are not currently in the queue!", 
                ephemeral=True
            )

        await interaction.response.send_message(
            f"<:checkmark:1339153448926580818> You've been removed from the queue.",
            ephemeral=True
        )

        self.queue_manager.set_message_location(interaction.channel_id, interaction.message.id)
        await self.queue_manager.enqueue_leave(interaction.user.id, interaction.user, interaction)


class JoinQueueButtonView(discord.ui.View):
    def __init__(
        self, title="Join Queue", color=discord.ButtonStyle.blurple, queue_manager=None, *, timeout=None
    ):
        super().__init__(timeout=timeout)
        self.add_item(JoinQueueButton(title, color, queue_manager))
        self.add_item(LeaveQueueButton("Leave Queue", discord.ButtonStyle.grey, queue_manager))


class HistoryPaginationView(discord.ui.View):
    def __init__(self, embeds, author_id):
        super().__init__(timeout=120)
        self.embeds = embeds
        self.author_id = author_id
        self.current_page = 0
        self.update_buttons()

    def update_buttons(self):
        self.previous_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page == len(self.embeds) - 1
        self.page_info.label = f"Page {self.current_page + 1}/{len(self.embeds)}"

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("You cannot use these buttons.", ephemeral=True)
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="Page 1/1", style=discord.ButtonStyle.grey, disabled=True)
    async def page_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
             return await interaction.response.send_message("You cannot use these buttons.", ephemeral=True)
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)


class WaitlistCmd(commands.GroupCog, name="waitlist"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.queue_manager_pool = QueueManagerPool(bot)
        super().__init__()

    @app_commands.command(name="check", description="Check test history")
    @app_commands.describe(
        user="The Discord user to check",
        duration="Filter by time range"
    )
    @app_commands.choices(
        duration=[
            app_commands.Choice(name="Past 7 Days", value="7d"),
            app_commands.Choice(name="Past 14 Days", value="14d"),
            app_commands.Choice(name="Past 30 Days", value="30d"),
            app_commands.Choice(name="All Time", value="alltime"),
        ]
    )
    async def waitlist_check(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duration: app_commands.Choice[str] = None
    ):
        if await _deny_if_restricted(interaction, interaction.user, user):
            return
        await interaction.response.defer()
        target_user = user
        duration_val = duration.value if duration else "alltime"
        
        # Calculate timestamp threshold
        threshold = 0
        now = int(interaction.created_at.timestamp())
        if duration_val == "7d":
            threshold = now - (7 * 24 * 60 * 60)
        elif duration_val == "14d":
            threshold = now - (14 * 24 * 60 * 60)
        elif duration_val == "30d":
            threshold = now - (30 * 24 * 60 * 60)
        
        async with self.bot.tlresults_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Check if table exists to avoid errors on fresh start
                await cursor.execute("SHOW TABLES LIKE 'tlresults'")
                if not await cursor.fetchone():
                     return await interaction.followup.send("No history found (Database empty).")

                query = "SELECT * FROM tlresults WHERE player_user_id = %s"
                params = [target_user.id]
                
                if threshold > 0:
                    query += " AND timestamp >= %s"
                    params.append(threshold)
                
                query += " ORDER BY timestamp DESC"
                
                await cursor.execute(query, tuple(params))
                results = await cursor.fetchall()

        if not results:
             return await interaction.followup.send(f"No test history found for {target_user.mention} in the selected period.")

        chunk_size = 5
        chunks = [results[i:i + chunk_size] for i in range(0, len(results), chunk_size)]
        
        embeds = []
        for i, chunk in enumerate(chunks):
            embed = discord.Embed(
                title=f"Test History for {target_user.display_name}",
                description=f"> **Duration:** {duration.name if duration else 'All Time'} | **Total Tests:** {len(results)}",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=target_user.display_avatar.url if target_user.avatar else discord.Embed.Empty)
            
            for row in chunk:
                # id(0), player_discord_username(1), player_user_id(2), is_linked(3), region(4), 
                # in_game_username(5), score(6), timestamp(7), old_rank(8), new_rank(9), 
                # gamemode(10), remarks(11), tester_discord_username(12), tester_user_id(13)
                
                r_ign = row[5]
                r_score = row[6]
                r_ts = row[7]
                r_old = row[8]
                r_new = row[9]
                r_mode = row[10]
                r_remark = row[11]
                r_tester_id = row[13]
                
                date_str = f"<t:{r_ts}:R>"
                
                field_val = (
                    f"-# **Tester:** <@{r_tester_id}>\n"
                    f"-# **Date:** {date_str}\n"
                    f"-# **IGN:** {r_ign}\n"
                    f"-# **Score:** {r_score}\n"
                    f"-# **Rank:** {r_old} ➔ {r_new}\n"
                )
                if r_remark:
                     field_val += f"-# **Remarks:** {r_remark}\n"
                
                embed.add_field(name=f"{r_mode}", value=field_val, inline=False)
            
            embed.set_footer(text=f"Page {i+1} of {len(chunks)} • Requested by {interaction.user.name}")
            embeds.append(embed)
            
        view = HistoryPaginationView(embeds, interaction.user.id)
        await interaction.followup.send(embed=embeds[0], view=view)

    
    @app_commands.command(
        name="skip",
        description="Skip a user currently being served (removes user from thread)"
    )
    @app_commands.describe(
        user="The Discord user to skip",
        gamemode="Specify the gamemode"
    )
    @app_commands.choices(
        gamemode=[
            app_commands.Choice(name="Netherite Pot", value="NPOT"),
            app_commands.Choice(name="Diamond Pot", value="DPOT"),
            app_commands.Choice(name="SMP Kit", value="SMP"),
            app_commands.Choice(name="Sword", value="Sword"),
            app_commands.Choice(name="Crystal", value="Crystal"),
            app_commands.Choice(name="Axe", value="Axe"),
            app_commands.Choice(name="Mace", value="Mace"),
            app_commands.Choice(name="UHC", value="UHC"),
        ]
    )
    async def waitlist_skip(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        gamemode: app_commands.Choice[str],
    ):
        if await _deny_if_restricted(interaction, interaction.user, user):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        item = return_item(gamemode.value.lower())
        channelID = item[1]
        gamemodeChannel = interaction.guild.get_channel(channelID)
        # Find the waitlist panel message
        messages = [
            message
            async for message in gamemodeChannel.history(limit=10)
            if message.author.id == interaction.client.application_id
        ]
        if not messages:
            return await interaction.followup.send(f"<:cross1:1339153202859474956> No queue message found in <#{channelID}>.", ephemeral=True)
        oldMessage = messages[0]
        if not oldMessage.embeds:
            return await interaction.followup.send(f"<:cross1:1339153202859474956> The last message in <#{channelID}> has no embed. Delete any non-queue messages in the channel and try again.", ephemeral=True)
        embed = oldMessage.embeds[0]
        # Check if embed has required fields
        if len(embed.fields) < 2:
            return await interaction.followup.send(f"<:cross1:1339153202859474956> The queue isn't properly formatted or not open at all. Delete any non-queue messages in the channel and try again.", ephemeral=True)
        queueString = embed.fields[0].value
        activeTesters = embed.fields[1].value
        # Remove user from active testers
        lines = activeTesters.split("\n")
        new_active = []
        found = False
        for line in lines:
            # Handle format: "N. <@member_id> (being served by <@tester_id>)"
            member_match = re.search(r'<@!?(\d+)>\s*\(being served by', line)
            member_uid = int(member_match.group(1)) if member_match else None
            
            if member_uid != user.id:
                new_active.append(line)
            else:
                found = True
        if not found:
            return await interaction.followup.send(f"<:cross1:1339153202859474956> {user.mention} is not currently being served.", ephemeral=True)
        # Renumber active testers if needed
        for i in range(len(new_active)):
            # Remove the number prefix and re-number
            l = re.sub(r'^\d+\. ', '', new_active[i])
            new_active[i] = f"{i+1}. {l}"
        new_active_str = "\n".join(new_active) if new_active else "N/A"
        embed.set_field_at(1, name="Currently Serving", value=new_active_str, inline=False)
        await oldMessage.edit(embed=embed)
        # Try to remove user from thread if present
        try:
            if interaction.channel and interaction.channel.type.name == "public_thread":
                await interaction.channel.remove_user(user)
            else:
                # Try to find a thread in the channel where user is a member
                for thread in gamemodeChannel.threads:
                    if user in thread.members and f"{user.id}" in thread.name:
                        await thread.remove_user(user)
        except Exception:
            pass
        await interaction.followup.send(f"<:checkmark:1339153448926580818> {user.mention} has been skipped and removed from the active slot.", ephemeral=True)

    @app_commands.command(
        name="results", description="Finalize a user's waitlist result"
    )
    @app_commands.describe(
        user="Specify the Discord user",
        region="Specify the user's region",
        scores="Specify the score",
        new_role="Specify the new rank role to be added",
        remarks="Optional remarks",
    )
    @app_commands.choices(
        region=[
            app_commands.Choice(name="Asia", value="AS"),
            app_commands.Choice(name="Australia", value="AU"),
            app_commands.Choice(name="North America", value="NA"),
            app_commands.Choice(name="Europe", value="EU"),
        ]
    )
    async def tlresults(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        region: str,
        scores: str,
        new_role: discord.Role,
        remarks: str = None,
    ) -> None:
        if await _deny_if_restricted(interaction, interaction.user, user):
            return
        await interaction.response.defer()
        
        # Check if target is linked
        if LINKED_ROLE_ID not in [role.id for role in user.roles]:
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> This player is not linked. They must link their account to receive results.",
                ephemeral=True
            )

        # Database Check: Verify target exists in DB
        username = "Unknown"
        linked_uuid = None
        async with self.bot.tllink_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SHOW TABLES")
                db_result = await cursor.fetchone()
                link_table = db_result[0] if db_result else "mystilinking"
                await cursor.execute(f"SELECT player_name, uuid FROM {link_table} WHERE discord_id = %s", (str(user.id),))
                db_result = await cursor.fetchone()
                if db_result:
                    username = db_result[0]
                    linked_uuid = db_result[1]
                else:
                    return await interaction.followup.send(
                        "<:cross1:1339153202859474956> Could not find linked account in database despite having the linked role.",
                        ephemeral=True
                    )

        # Parse Logic
        gamemode = new_role.name.split(" ")[1]
        new_rank = new_role.name.split(" ")[0]

        # Tester Permission Check
        legit = False
        for role in interaction.user.roles:
            if "tester" in role.name.lower() and gamemode.lower() in role.name.lower():
                legit = True
                break

        if not legit:
            return await interaction.followup.send(
                f"<:cross1:1339153202859474956> You cannot run this command. You are not a {gamemode} tester.",
                ephemeral=True,
            )

        # Role Name Validation
        if not (("LT" in new_role.name or "HT" in new_role.name) and "tester" not in new_role.name.lower()):
            return await interaction.followup.send(
                "<:warn:1459986909911842846> Double check you selected the correct role!", ephemeral=True
            )

        # High Tier Restriction Check (This was previously after roles were already swapped!)
        high_tier_ranks = ["HT3", "LT2", "HT2", "LT1", "HT1"]
        if new_rank in high_tier_ranks:
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> You cannot give high tier roles with this command. Use `/ht results` instead.",
                ephemeral=True
            )

        # Tester Link Check
        if LINKED_ROLE_ID not in [role.id for role in interaction.user.roles]:
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> As a tester yourself, you must also have your account linked.", 
                embed=discord.Embed(
                    title="<:warn:1459986909911842846> **Account Linking Required**",
                    description=f"Link your account in <#1460525451368861818> to use this command.",
                    color=discord.Colour.red()
                ),
                ephemeral=True
            )
            
        # Self-Test Check
        if user.id == interaction.user.id and interaction.user.id not in AUTHORIZED_USERS:
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> You cannot test yourself!", ephemeral=True
            )

        # Handle Previous Roles
        previousRank = "N/A"
        removeRole = None
        for role in user.roles:
            try:
                if len(role.name.split(" ")) > 1 and role.name.split(" ")[1] == gamemode:
                    removeRole = role
                    break
            except Exception:
                continue

        if removeRole:
            previousRank = removeRole.name.split(" ")[0]
            await user.remove_roles(removeRole)

        # Add New Role
        await user.add_roles(new_role)

        # Clear Waitlist Cooldown
        ref = db.reference("/Waitlist Cooldown")
        ticketcooldown = ref.get()
        if ticketcooldown:
            for key, value in ticketcooldown.items():
                if (value.get("User ID") == user.id) and (value.get("Gamemode") == gamemode):
                    ref.child(key).delete()
                    break

        # Remove from channel
        try:
            await interaction.channel.remove_user(user)
        except:
            pass
        
        # Prepare Embed
        embed = discord.Embed(title=f"{username}'s Results :trophy:", color=0x22aef5)
        embed.add_field(name="Tester", value=interaction.user.mention, inline=True)
        embed.add_field(name="Region", value=region, inline=True)
        embed.add_field(name="In-game Username", value=f"[{username}](https://tierlist.mysticraft.xyz/?player={username})", inline=True)
        embed.add_field(name="Gamemode", value=gamemode, inline=True)
        embed.add_field(name="Previous Rank", value=previousRank, inline=True)
        embed.add_field(name="New Rank", value=new_rank, inline=True)
        embed.add_field(name="Scores", value=scores, inline=True)
        if remarks:
            embed.add_field(name="Remarks", value=remarks, inline=True)
        embed.set_thumbnail(url=f"https://render.crafty.gg/3d/bust/{username}")

        # Send Results to Channel
        results_channel = interaction.guild.get_channel(1304859270885412975)
        results_msg = await results_channel.send(content=user.mention, embed=embed)

        # Set Waitlist Cooldown
        ref = db.reference("/Waitlist Cooldown")
        ref.push().set({
            "User ID": user.id,
            "Last Tested": int(interaction.created_at.timestamp()),
            "Gamemode": gamemode,
        })

        # Database Log
        async with self.bot.tlresults_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO tlresults (player_discord_username, player_user_id, uuid, is_linked, region, in_game_username, score, timestamp, old_rank, new_rank, gamemode, remarks, tester_discord_username, tester_user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (user.name, user.id, linked_uuid, True, region, username, scores, int(interaction.created_at.timestamp()), previousRank, new_rank, gamemode, remarks, interaction.user.name, interaction.user.id))
                await conn.commit()

        # Tester Stats & Rank Up Logic
        ref_stats = db.reference("/Tierlist Tester Stats")
        tester_data = ref_stats.child(str(interaction.user.id)).get() or {}
        
        old_rep = tester_data.get("count", 0) + 2 * tester_data.get("high_count", 0)
        old_tier = get_tier_index(old_rep)
        
        timestamps = tester_data.get("timestamps", [])
        timestamps.append(int(interaction.created_at.timestamp()))
        
        ref_stats.child(str(interaction.user.id)).update({
            "count": len(timestamps),
            "timestamps": timestamps
        })

        # Rank Up Calculation
        new_rep = len(timestamps) + 2 * tester_data.get("high_count", 0)
        new_tier = get_tier_index(new_rep)
        
        if new_tier > old_tier:
            new_role_id = TIER_ROLES.get(new_tier)
            old_role_id = TIER_ROLES.get(old_tier)
            if old_role_id:
                await interaction.user.remove_roles(interaction.guild.get_role(old_role_id))
            if new_role_id:
                await interaction.user.add_roles(interaction.guild.get_role(new_role_id))
            
            log_channel = interaction.guild.get_channel(1467403596780929055)
            rank_embed = discord.Embed(
                description=f"{interaction.user.mention} reached **{TIER_THRESHOLDS[new_tier]}** reps and ranked up to `{TIER_NAMES[new_tier]}`!",
                color=discord.Color.from_rgb(*tier_colors[new_tier])
            )
            await log_channel.send(content=interaction.user.mention, embed=rank_embed)

        # Cleanup Roles & Queue
        item = return_item(gamemode.lower())
        await user.remove_roles(interaction.guild.get_role(item[0]))
        
        try:
            queue_manager = self.queue_manager_pool.get_manager(gamemode.lower())
            queue_manager.remove_active_session(user.id)
        except Exception as e:
            print(f"Queue Sync Error: {e}")

        await interaction.followup.send(f"<:checkmark:1339153448926580818> [Results sent]({results_msg.jump_url})")


    @app_commands.command(
        name="migrate", description="Migrate a user's tier from another server (Admin+ only)"
    )
    @app_commands.describe(
        user="Specify the user",
        region="Specify the user's region",
        new_role="Specify the new rank role to be added",
        server="Specify the server they are migrating from",
    )
    @app_commands.choices(
        region=[
            app_commands.Choice(name="Asia", value="AS"),
            app_commands.Choice(name="Australia", value="AU"),
            app_commands.Choice(name="North America", value="NA"),
            # app_commands.Choice(name="South America", value="SA"),
            app_commands.Choice(name="Europe", value="EU"),
        ]
    )
    async def tlmigrate(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        region: str,
        new_role: discord.Role,
        server: str,
    ) -> None:
        if await _deny_if_restricted(interaction, interaction.user, user):
            return
        await interaction.response.defer()

        allowed_roles = [1304851740226748556, 1460312013535318077, 1304848576190484553]
        has_permission = any(role.id in allowed_roles for role in interaction.user.roles)
        
        if not has_permission:
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> You do not have permission to migrate tiers.",
                ephemeral=True
            )

        # Check linking
        if LINKED_ROLE_ID not in [role.id for role in user.roles]:
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> This player is not linked. They must link their account to receive results.",
                ephemeral=True
            )

        # Get Username from DB
        username = "Unknown"
        linked_uuid = None
        async with self.bot.tllink_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SHOW TABLES")
                result = await cursor.fetchone()
                link_table = result[0] if result else "mystilinking"
                await cursor.execute(f"SELECT player_name, uuid FROM {link_table} WHERE discord_id = %s", (str(user.id),))
                result = await cursor.fetchone()
                if result:
                    username = result[0]
                    try:
                        linked_uuid = result[1]
                    except Exception:
                        linked_uuid = None
                else:
                    return await interaction.followup.send(
                        "<:cross1:1339153202859474956> Could not find linked account in database despite having the linked role.",
                        ephemeral=True
                    )
        
        gamemode = new_role.name.split(" ")[1]
        removeRole = None
        for role in user.roles:
            try:
                if role.name.split(" ")[1] == gamemode:
                    removeRole = role
            except Exception:
                continue
        if removeRole != None:
            await user.remove_roles(removeRole)
            previousRank = removeRole.name.split(" ")[0]
        else:
            previousRank = "N/A"

        if not (
            ("LT" in new_role.name or "HT" in new_role.name)
            and "tester" not in new_role.name.lower()
        ):
            return await interaction.followup.send(
                "<:warn:1459986909911842846> Double check you selected the correct role!", ephemeral=True
            )
            
        if user.id == interaction.user.id:
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> You cannot migrate yourself!", ephemeral=True
            )
        
        new_rank = new_role.name.split(" ")[0]

        ref = db.reference("/Waitlist Cooldown")
        ticketcooldown = ref.get()
        try:
            for key, value in ticketcooldown.items():
                if (value["User ID"] == interaction.user.id) and (
                    value["Gamemode"] == gamemode
                ):
                    db.reference("/Waitlist Cooldown").child(key).delete()
                    break
        except Exception:
            pass

        try:
            await interaction.channel.remove_user(user)
        except Exception:
            pass
        
        embed = discord.Embed(title=f"{username}'s Results :trophy:")
        embed.add_field(
            name="Tester",
            value=f"{interaction.user.mention}",
            inline=True,
        )
        embed.add_field(name="Region", value=f"{region}", inline=True)
        embed.add_field(name="In-game Username", value=f"[{username}](https://tierlist.mysticraft.xyz/?player={username})", inline=True)
        embed.add_field(name="Gamemode", value=f"{gamemode}", inline=True)
        embed.add_field(name="Previous Rank", value=f"{previousRank}", inline=True)
        embed.add_field(name="New Rank", value=new_rank, inline=True)
        embed.add_field(name="Scores", value="N/A", inline=True)
        embed.add_field(name="Remarks", value=f"Migrated from {server}", inline=True)
        embed.set_thumbnail(url=f"https://render.crafty.gg/3d/bust/{username}")
        await user.add_roles(new_role)

        # Set Waitlist Cooldown
        ref = db.reference("/Waitlist Cooldown")
        ref.push().set({
            "User ID": user.id,
            "Last Tested": int(interaction.created_at.timestamp()),
            "Gamemode": gamemode,
        })
        
        # Determine channel
        if new_rank in ["HT3", "LT2", "HT2", "LT1", "HT1"]:
            results_channel = interaction.guild.get_channel(1338411690902945832)  # High Results
        else:
            results_channel = interaction.guild.get_channel(1304859270885412975)  # Regular Results
        
        results = await results_channel.send(
            user.mention, embed=embed
        )
            
        async with self.bot.tlresults_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SHOW TABLES LIKE 'tlresults'")
                result = await cursor.fetchone()
                if not result:
                    await cursor.execute("""
                        CREATE TABLE tlresults (
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
                        )
                    """)
                await cursor.execute("""
                    INSERT INTO tlresults (player_discord_username, player_user_id, uuid, is_linked, region, in_game_username, score, timestamp, old_rank, new_rank, gamemode, remarks, tester_discord_username, tester_user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (user.name, user.id, linked_uuid, True, region, username, "N/A", int(interaction.created_at.timestamp()), previousRank, new_rank, gamemode, f"Migrated from {server}", interaction.user.name, interaction.user.id))
                await conn.commit()

        item = return_item(gamemode.lower())

        await user.remove_roles(interaction.guild.get_role(item[0]))
        await interaction.followup.send(f"<:checkmark:1339153448926580818> [Migration Results sent]({results.jump_url})")


    @app_commands.command(name="start", description="Start the queue in a waitlist")
    @app_commands.describe(
        gamemode="Specify the gamemode",
        region="Specify your region",
        message="Optional message to announce",
    )
    @app_commands.choices(
        gamemode=[
            app_commands.Choice(name="Netherite Pot", value="NPOT"),
            app_commands.Choice(name="Diamond Pot", value="DPOT"),
            app_commands.Choice(name="SMP Kit", value="SMP"),
            app_commands.Choice(name="Sword", value="Sword"),
            app_commands.Choice(name="Crystal", value="Crystal"),
            app_commands.Choice(name="Axe", value="Axe"),
            app_commands.Choice(name="Mace", value="Mace"),
            app_commands.Choice(name="UHC", value="UHC"),
        ],
        region=[
            app_commands.Choice(name="Asia", value="AS"),
            app_commands.Choice(name="Australia", value="AU"),
            app_commands.Choice(name="North America", value="NA"),
            # app_commands.Choice(name="South America", value="SA"),
            app_commands.Choice(name="Europe", value="EU"),
        ],
    )
    async def waitlist_start(
        self,
        interaction: discord.Interaction,
        gamemode: app_commands.Choice[str],
        region: str,
        message: str = "",
    ) -> None:
        if await _deny_if_restricted(interaction, interaction.user):
            return

        item = return_item(gamemode.value.lower())

        if interaction.guild.get_role(item[2]) not in interaction.user.roles:
            return await interaction.response.send_message(
                f"<:cross1:1339153202859474956> You cannot run this command. You are not a <@&{item[2]}>!",
                ephemeral=True,
            )
        channelID = item[1]
        gamemodeChannel = interaction.guild.get_channel(channelID)
        messages = [
            message
            async for message in gamemodeChannel.history(limit=10)
            if message.author.id == interaction.client.application_id
        ]
        if not messages:
            return await interaction.response.send_message(
                f"<:cross1:1339153202859474956> No queue message found in <#{channelID}>.",
                ephemeral=True,
            )
        oldMessage = messages[0]
        if not oldMessage.embeds:
            return await interaction.response.send_message(
                f"<:cross1:1339153202859474956> The last message in <#{channelID}> has no embed. Delete any non-queue messages in the channel and try again.",
                ephemeral=True,
            )
        if oldMessage.embeds[0].title == "No Testers Online":
            await oldMessage.delete()
            embed = discord.Embed(
                title=f"{region} Tester(s) Available!",
                color=0x5865F2,
            )
            embed.add_field(name="Queue", value="Empty", inline=False)
            embed.add_field(name="Currently Serving", value="N/A", inline=False)
            embed.set_footer(text=f"Queue opened by {interaction.user.name}")
            
            # Get queue manager for this gamemode
            queue_manager = self.queue_manager_pool.get_manager(gamemode.value.lower())
            # Always clear active sessions (currently serving)
            queue_manager.clear_active_sessions()
            # Only clear queue if it was closed more than 30 minutes ago
            if queue_manager.should_clear_on_start():
                queue_manager.clear()
            
            newMessage = await gamemodeChannel.send(
                content=f"<@&{item[0]}> {message}",
                embed=embed,
                view=JoinQueueButtonView(queue_manager=queue_manager),
            )
            # Set message location in queue manager
            queue_manager.set_message_location(channelID, newMessage.id)
            
            await interaction.response.send_message(
                f"<:checkmark:1339153448926580818> [Queue opened]({newMessage.jump_url})", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"<:warn:1459986909911842846> The queue in <#{channelID}> ({gamemode.value}) has been opened already...",
                ephemeral=True,
            )

    @app_commands.command(
        name="next", description="Call up the next player in the queue"
    )
    @app_commands.describe(
        gamemode="Specify the gamemode",
    )
    @app_commands.choices(
        gamemode=[
            app_commands.Choice(name="Netherite Pot", value="NPOT"),
            app_commands.Choice(name="Diamond Pot", value="DPOT"),
            app_commands.Choice(name="SMP Kit", value="SMP"),
            app_commands.Choice(name="Sword", value="Sword"),
            app_commands.Choice(name="Crystal", value="Crystal"),
            app_commands.Choice(name="Axe", value="Axe"),
            app_commands.Choice(name="Mace", value="Mace"),
            app_commands.Choice(name="UHC", value="UHC"),
        ]
    )
    async def waitlist_next(
        self, interaction: discord.Interaction, gamemode: app_commands.Choice[str]
    ) -> None:
        if await _deny_if_restricted(interaction, interaction.user):
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        item = return_item(gamemode.value.lower())

        if interaction.guild.get_role(item[2]) not in interaction.user.roles:
            return await interaction.followup.send(
                f"<:cross1:1339153202859474956> You cannot run this command. You are not a <@&{item[2]}>!",
                ephemeral=True,
            )
        
        # Get queue manager for this gamemode
        queue_manager = self.queue_manager_pool.get_manager(gamemode.value.lower())
        
        # Pop the first user from the queue
        next_entry = await queue_manager.pop_first()
        
        if not next_entry:
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> Queue is empty. Please wait for players to join first.",
                ephemeral=True,
            )
        
        nextID = next_entry.user_id
        nextMember = interaction.guild.get_member(nextID)
        if nextMember is None:
            try:
                nextMember = await interaction.guild.fetch_member(nextID)
            except Exception:
                nextMember = None
        
        # Add testing session: member_id -> tester_id
        tester_id = interaction.user.id
        queue_manager.add_active_session(nextID, tester_id)
        
        # Embed will be synced by the background loop within 5 seconds
        
        # Create thread
        try:
            thread = await interaction.channel.create_thread(name=f"{(nextMember.name if nextMember else str(nextID))}'s ticket ({nextID})")
        except Exception as e:
            await interaction.followup.send(
                f"<:warn:1459986909911842846> Unable to create a thread: {e}",
                ephemeral=True,
            )
            return

        try:
            await thread.add_user(interaction.user)
        except Exception:
            await interaction.followup.send(
                "<:warn:1459986909911842846> Could not add you to the thread (insufficient permissions).",
                ephemeral=True,
            )

        if nextMember:
            try:
                await thread.add_user(nextMember)
            except discord.Forbidden:
                await interaction.followup.send(
                    f"<:warn:1459986909911842846> Could not add <@{nextID}> to the thread due to permission restrictions.",
                    ephemeral=True,
                )
            except Exception:
                await interaction.followup.send(
                    f"<:warn:1459986909911842846> Failed to add <@{nextID}> to the thread.",
                    ephemeral=True,
                )
        else:
            await interaction.followup.send(
                f"<:warn:1459986909911842846> {nextID} is not a guild member or could not be fetched; they were not added to the thread.",
                ephemeral=True,
            )

        await interaction.followup.send(
            f"Successfully added <@{nextID}> to {thread.mention}.", ephemeral=True
        )

        linked_ign = "None"
        try:
            async with self.bot.tllink_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SHOW TABLES")
                    tb_res = await cursor.fetchone()
                    link_table = tb_res[0] if tb_res else "mystilinking"
                    await cursor.execute(f"SELECT player_name FROM {link_table} WHERE discord_id = %s", (str(nextID),))
                    link_res = await cursor.fetchone()
                    if link_res:
                        linked_ign = link_res[0]
        except Exception as e:
            print(f"Error fetching linked IGN for thread: {e}")

        async with self.bot.tlresults_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT region FROM tlresults WHERE player_user_id = %s AND gamemode = %s ORDER BY timestamp DESC LIMIT 1", (nextID, gamemode.value))
                result = await cursor.fetchone()
                
        if result:
            recorded_region = result[0]
        else:
            recorded_region = "<:warn:1459986909911842846> Unknown"

        current_rank = "None"
        if nextMember:
            for role in nextMember.roles:
                if gamemode.value.lower() in role.name.lower() and "waitlist" not in role.name.lower():
                    current_rank = role.name.split(" ")[0]
                    break

        has_linked = nextMember and LINKED_ROLE_ID in [role.id for role in nextMember.roles]
        display_ign = linked_ign if linked_ign != "None" else "Not Linked"

        embed = discord.Embed(title=f"Testing Session for {nextMember.name if nextMember else str(nextID)}", description="> **Reminder for testers:** Verify the player's Minecraft account matches the one below before testing. If they changed their name, ask the player to [link](https://ptb.discord.com/channels/1304829305443844096/1460525451368861818) their accounts again.", color=discord.Colour.blue())
        embed.add_field(name="Linked IGN", value=f"[{display_ign}](https://tierlist.mysticraft.xyz/?player={display_ign})" if has_linked else "<:no:1036810470860013639> Not Linked", inline=True)
        embed.add_field(name="Current Rank", value=current_rank, inline=True)
        embed.add_field(name="Region", value=recorded_region, inline=True)
        embed.set_footer(text=f"These details are based on the user's database records.")
        await thread.send(embed=embed)

    @app_commands.command(name="end", description="End the queue in a waitlist")
    @app_commands.describe(
        gamemode="Specify the gamemode",
    )
    @app_commands.choices(
        gamemode=[
            app_commands.Choice(name="Netherite Pot", value="NPOT"),
            app_commands.Choice(name="Diamond Pot", value="DPOT"),
            app_commands.Choice(name="SMP Kit", value="SMP"),
            app_commands.Choice(name="Sword", value="Sword"),
            app_commands.Choice(name="Crystal", value="Crystal"),
            app_commands.Choice(name="Axe", value="Axe"),
            app_commands.Choice(name="Mace", value="Mace"),
            app_commands.Choice(name="UHC", value="UHC"),
        ]
    )
    async def waitlist_end(
        self, interaction: discord.Interaction, gamemode: app_commands.Choice[str]
    ) -> None:
        if await _deny_if_restricted(interaction, interaction.user):
            return
        item = return_item(gamemode.value.lower())

        if interaction.guild.get_role(item[2]) not in interaction.user.roles:
            return await interaction.response.send_message(
                f"<:cross1:1339153202859474956> You cannot run this command. You are not a <@&{item[2]}>!",
                ephemeral=True,
            )
        channelID = item[1]
        gamemodeChannel = interaction.guild.get_channel(channelID)
        messages = [
            message
            async for message in gamemodeChannel.history(limit=10)
            if message.author.id == interaction.client.application_id
        ]
        if not messages:
            return await interaction.response.send_message(
                f"<:cross1:1339153202859474956> No queue message found in <#{channelID}>.",
                ephemeral=True,
            )
        oldMessage = messages[0]
        if not oldMessage.embeds:
            return await interaction.response.send_message(
                f"<:cross1:1339153202859474956> The last message in <#{channelID}> has no embed. Delete any non-queue messages in the channel and try again.",
                ephemeral=True,
            )
        if "Tester(s) Available!" in oldMessage.embeds[0].title:
            embed = discord.Embed(
                title="No Testers Online",
                description=f"No testers for your region are available at this time.\nYou will be pinged when a tester is available. Check back later!\n\n**Last testing session:** <t:{int(time.mktime(datetime.datetime.now().timetuple()))}>",
                color=0xFF4500,
            )
            embed.set_footer(text=f"Queue is closed by {interaction.user.name}")
            await oldMessage.edit(content=None, embed=embed, view=None)
            
            # Mark the queue manager as closed (preserves data for quick reopens within 1 hour)
            queue_manager = self.queue_manager_pool.get_manager(gamemode.value.lower())
            queue_manager.mark_closed()
            
            await interaction.response.send_message(
                f"<:checkmark:1339153448926580818> [Queue closed]({oldMessage.jump_url})", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"<:warn:1459986909911842846> The queue in <#{channelID}> ({gamemode.value}) has been ended already...",
                ephemeral=True,
            )

    @app_commands.command(
        name="dropdown", description="Creates a waitlist panel with dropdown menu"
    )
    @app_commands.describe(
        title="Makes the title of the embed",
        description="Makes the description of the embed",
        color="Sets the color of the embed",
        thumbnail="Please provide a URL for the thumbnail of the embed (upper-right hand corner image)",
        image="Please provide a URL for the image of the embed (appears at the bottom of the embed)",
        footer="Sets the footer of the embed that appears at the bottom of the embed as small texts",
        dropdown_placeholder="Sets the placeholder of the dropdown menu",
        dropdown1_title="Format: Emoji | Title | Shortform",
        dropdown2_title="Format: Emoji | Title | Shortform",
        dropdown3_title="Format: Emoji | Title | Shortform",
        dropdown4_title="Format: Emoji | Title | Shortform",
        dropdown5_title="Format: Emoji | Title | Shortform",
        dropdown6_title="Format: Emoji | Title | Shortform",
        dropdown7_title="Format: Emoji | Title | Shortform",
        dropdown8_title="Format: Emoji | Title | Shortform",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def waitlist_dropdown(
        self,
        interaction: discord.Interaction,
        title: str = None,
        description: str = None,
        color: str = None,
        thumbnail: str = None,
        image: str = None,
        footer: str = None,
        dropdown_placeholder: str = "Select a Category",
        dropdown1_title: str = None,
        dropdown2_title: str = None,
        dropdown3_title: str = None,
        dropdown4_title: str = None,
        dropdown5_title: str = None,
        dropdown6_title: str = None,
        dropdown7_title: str = None,
        dropdown8_title: str = None,
    ) -> None:
        if await _deny_if_restricted(interaction, interaction.user):
            return
        if color is not None:
            try:
                color = await commands.ColorConverter().convert(interaction, color)
            except:
                color = None
        if color is None:
            color = discord.Color.default()
        embed = discord.Embed(color=color)
        if title is not None:
            embed.title = title
        if description is not None:
            embed.description = description
        if thumbnail is not None:
            embed.set_thumbnail(url=thumbnail)
        if image is not None:
            embed.set_image(url=image)
        if footer is not None:
            embed.set_footer(text=footer)

        options = []

        list = [
            [
                dropdown1_title.split("|")[0].strip(),
                dropdown1_title.split("|")[1].strip(),
                dropdown1_title.split("|")[2].strip(),
            ],
            [
                dropdown2_title.split("|")[0].strip(),
                dropdown2_title.split("|")[1].strip(),
                dropdown2_title.split("|")[2].strip(),
            ],
            [
                dropdown3_title.split("|")[0].strip(),
                dropdown3_title.split("|")[1].strip(),
                dropdown3_title.split("|")[2].strip(),
            ],
            [
                dropdown4_title.split("|")[0].strip(),
                dropdown4_title.split("|")[1].strip(),
                dropdown4_title.split("|")[2].strip(),
            ],
            [
                dropdown5_title.split("|")[0].strip(),
                dropdown5_title.split("|")[1].strip(),
                dropdown5_title.split("|")[2].strip(),
            ],
            [
                dropdown6_title.split("|")[0].strip(),
                dropdown6_title.split("|")[1].strip(),
                dropdown6_title.split("|")[2].strip(),
            ],
            [
                dropdown7_title.split("|")[0].strip(),
                dropdown7_title.split("|")[1].strip(),
                dropdown7_title.split("|")[2].strip(),
            ],
            [
                dropdown8_title.split("|")[0].strip(),
                dropdown8_title.split("|")[1].strip(),
                dropdown8_title.split("|")[2].strip(),
            ],
        ]

        for item in list:
            if item[0] is not None and item[1] is not None:  # Emoji + Title
                emote = emoji.emojize(item[0].strip())
                title = item[1].strip()
                options.append(
                    discord.SelectOption(
                        label=title,
                        value=item[2],
                        emoji=emote,
                        description=f"{title} Queue",
                    )
                )
            else:  # Title missing
                embed = discord.Embed(
                    title="Format incorrect",
                    description="Please double check!",
                    color=0xFF0000,
                )
                return await interaction.response.send_message(
                    embed=embed, ephemeral=True
                )

        await interaction.channel.send(
            embed=embed, view=WaitlistSelectionView(dropdown_placeholder, options)
        )
        embed = discord.Embed(
            title="<:checkmark:1339153448926580818> Custom Waitlist Panel Sent",
            description="All members who have access to this channel can submit a waitlist request by selecting the dropdown menu below the panel!",
            color=0x00FF00,
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)



class Waitlist(commands.Cog):
    def __init__(self, bot):
        self.client = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return

        if message.content == "mc!queue" and not message.author.bot:
            if _has_restricted_role(message.author):
                return
            embed = discord.Embed(
                title="No Testers Online",
                description=f"No testers for your region are available at this time.\nYou will be pinged when a tester is available. Check back later!\n\n**Last testing session:** <t:{int(time.mktime(datetime.datetime.now().timetuple()))}>",
                color=0xFF4500,
            )
            await message.channel.send(embed=embed)
            await message.delete()
        
        if message.channel.id == LINKED_LOG_CHANNEL_ID and message.author.id == 1459850286087802952:
            if "Alt Link Attempt Detected" in message.content:
                return
            
            match_ign = re.search(r"Minecraft Username:\s*(.+)", message.content)
            match_discord = re.search(r"Discord Username:\s*<@!?(\d+)>", message.content)
            
            if match_ign and match_discord:
                ign = match_ign.group(1).strip()
                discord_id = int(match_discord.group(1))

                try:
                    async with self.client.tllink_pool.acquire() as conn:
                        async with conn.cursor() as cursor:
                            await cursor.execute("SHOW TABLES")
                            result = await cursor.fetchone()
                            link_table = result[0] if result else "mystilinking"
                            
                            await cursor.execute(f"SELECT 1 FROM {link_table} WHERE LOWER(player_name) = LOWER(%s) AND discord_id = %s", (ign, str(discord_id)))
                            link_exists = await cursor.fetchone()
                except Exception as e:
                    print(f"Error checking linking DB: {e}")
                    link_exists = False
                
                if link_exists:
                    guild = message.guild
                    member = guild.get_member(discord_id)
                    if not member:
                        try:
                            member = await guild.fetch_member(discord_id)
                        except:
                            pass
                    
                    if member:

                        # Update past entries that match this user's UUID
                        try:
                            async with self.client.tllink_pool.acquire() as conn2:
                                async with conn2.cursor() as cursor2:
                                    await cursor2.execute("SHOW TABLES")
                                    tb = await cursor2.fetchone()
                                    link_table = tb[0] if tb else "mystilinking"

                                    # Get the CURRENT uuid associated with this discord_id from the linking table
                                    await cursor2.execute(f"SELECT uuid FROM {link_table} WHERE discord_id = %s", (str(discord_id),))
                                    link_row = await cursor2.fetchone()

                                    if link_row and link_row[0]:
                                        the_uuid = link_row[0]

                                        async with self.client.tlresults_pool.acquire() as conn3:
                                            async with conn3.cursor() as cursor3:
                                                # Check if 'uuid' column exists in tlresults
                                                await cursor3.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = 'tlresults' AND column_name = 'uuid'")
                                                colcheck = await cursor3.fetchone()

                                                if colcheck and colcheck[0] > 0:
                                                    ### NEW SCENARIO: Check if UUID has changed for this Discord User ###
                                                    # We check if there are entries for this discord_id that have a DIFFERENT uuid
                                                    await cursor3.execute("SELECT COUNT(*) FROM tlresults WHERE player_user_id = %s AND uuid != %s", (discord_id, the_uuid))
                                                    uuid_mismatch_row = await cursor3.fetchone()

                                                    if uuid_mismatch_row and uuid_mismatch_row[0] > 0:
                                                        # The user is linking a new Minecraft account. Unlink all previous entries for this Discord ID.
                                                        await cursor3.execute("UPDATE tlresults SET is_linked = 0 WHERE player_user_id = %s AND uuid != %s", (discord_id, the_uuid))
                                                        await conn3.commit()

                                                        embed_unlink = discord.Embed(
                                                            title="<:warn:1459986909911842846> Previous Account Unlinked",
                                                            description=f"Detected a new Minecraft UUID for <@{discord_id}>. Previous testing entries have been marked as **Unlinked**.",
                                                            color=discord.Color.red()
                                                        )
                                                        await message.channel.send(embed=embed_unlink)

                                                    ### EXISTING SCENARIO: Update IGN if UUID is the same but name changed ###
                                                    await cursor3.execute("SELECT COUNT(*) FROM tlresults WHERE uuid = %s AND LOWER(in_game_username) != LOWER(%s)", (the_uuid, ign))
                                                    diff_count_row = await cursor3.fetchone()
                                                    diff_count = diff_count_row[0] if diff_count_row else 0

                                                    if diff_count > 0:
                                                        await cursor3.execute("UPDATE tlresults SET in_game_username = %s WHERE uuid = %s AND LOWER(in_game_username) != LOWER(%s)", (ign, the_uuid, ign))
                                                        await conn3.commit()

                                                        embed_update = discord.Embed(
                                                            title="<:edit:1048779043287351408> Tierlist IGN Updated",
                                                            description=f"Updated {diff_count} past entries to reflect new IGN `{ign}` for <@{discord_id}>.",
                                                            color=discord.Color.yellow()
                                                        )
                                                        await message.channel.send(embed=embed_update)

                                        previous_owner = None
                                        try:
                                            async with self.client.tllink_pool.acquire() as conn4:
                                                async with conn4.cursor() as cursor4:
                                                    await cursor4.execute("SHOW TABLES")
                                                    tb4 = await cursor4.fetchone()
                                                    link_table = tb4[0] if tb4 else "mystilinking"
                                                    await cursor4.execute(
                                                        f"SELECT discord_id FROM {link_table} WHERE LOWER(player_name) = LOWER(%s) AND discord_id != %s LIMIT 1",
                                                        (ign, str(discord_id)),
                                                    )
                                                    previous_owner = await cursor4.fetchone()
                                        except Exception as e:
                                            print(f"Error checking previous IGN owner: {e}")

                                        if previous_owner:
                                            previous_owner_id = int(previous_owner[0])
                                            old_member = guild.get_member(previous_owner_id)
                                            if not old_member:
                                                try:
                                                    old_member = await guild.fetch_member(previous_owner_id)
                                                except Exception:
                                                    old_member = None

                                            try:
                                                target_roles, missing_roles, removed_old_roles = await _sync_tier_roles_for_member(
                                                    guild,
                                                    member,
                                                    ign,
                                                    old_member=old_member,
                                                )

                                                sync_embed = discord.Embed(
                                                    title="<:refresh:1048779043287351408> Tier Roles Synced",
                                                    description=f"Detected a previous Discord owner for `{ign}` and synced tier roles to {member.mention}.",
                                                    color=discord.Color.green(),
                                                )
                                                if target_roles:
                                                    sync_embed.add_field(
                                                        name="Assigned Roles",
                                                        value=", ".join(role.mention for role in target_roles),
                                                        inline=False,
                                                    )
                                                if removed_old_roles and old_member:
                                                    sync_embed.add_field(
                                                        name="Old Account Cleaned",
                                                        value=f"Removed {len(removed_old_roles)} tier role{'s' if len(removed_old_roles) != 1 else ''} from {old_member.mention}.",
                                                        inline=False,
                                                    )
                                                if missing_roles:
                                                    sync_embed.add_field(
                                                        name="Missing Roles",
                                                        value="\n".join(missing_roles),
                                                        inline=False,
                                                    )
                                                await message.channel.send(embed=sync_embed)
                                            except Exception as e:
                                                print(f"Error syncing roles for linked account transfer: {e}")

                        except Exception as e:
                            print(f"Error while processing UUID/IGN updates: {e}")

                        RANK_VALUES = {"HT1": 10, "LT1": 9, "HT2": 8, "LT2": 7, "HT3": 6, "LT3": 5, "HT4": 4, "LT4": 3, "HT5": 2, "LT5": 1, "N/A": 0}

                        updated_entries = []
                        total_updated = 0
                        
                        try:
                            async with self.client.tlresults_pool.acquire() as conn:
                                async with conn.cursor() as cursor:
                                    # Select candidate entries
                                    await cursor.execute("SELECT id, new_rank, gamemode FROM tlresults WHERE LOWER(in_game_username) = LOWER(%s) AND player_user_id = %s AND (is_linked = 0 OR is_linked IS NULL)", (ign, discord_id))
                                    candidates = await cursor.fetchall()
                                    
                                    ids_to_update = []
                                    count_map = {}

                                    for entry_id, rank, gamemode in candidates:
                                        # Check if user has corresponding role >= rank
                                        rank_val = RANK_VALUES.get(rank, 0)
                                        has_valid_role = False
                                        
                                        # Check user roles
                                        for role in member.roles:
                                            parts = role.name.split(" ")
                                            if len(parts) >= 2:
                                                r_rank = parts[0]
                                                r_gamemode = parts[1]
                                                
                                                # Match gamemode (case insensitive? usually title case in roles/db)
                                                if r_gamemode.lower() == gamemode.lower():
                                                    r_val = RANK_VALUES.get(r_rank, 0)
                                                    if r_val >= rank_val:
                                                        has_valid_role = True
                                                        break
                                        
                                        if has_valid_role:
                                            ids_to_update.append(entry_id)
                                            key = f"{rank} {gamemode}"
                                            count_map[key] = count_map.get(key, 0) + 1

                                    if ids_to_update:
                                        format_strings = ','.join(['%s'] * len(ids_to_update))
                                        await cursor.execute(f"UPDATE tlresults SET is_linked = 1 WHERE id IN ({format_strings})", tuple(ids_to_update))
                                        await conn.commit()
                                        total_updated = len(ids_to_update)
                                        
                                        details = []
                                        for key, count in count_map.items():
                                            details.append(f"- **{key}**: {count} entr{'y' if count == 1 else 'ies'}")
                                        
                                        summary = "\n".join(details)
                                        
                                        embed_log = discord.Embed(
                                            title="<:refresh:1048779043287351408> Tierlist Results Synced",
                                            description=f"Detected new linked account for {member.mention} (`{ign}`) and updated **{total_updated}** past testing results to Linked status based on current roles.",
                                            color=discord.Color.gold()
                                        )
                                        embed_log.add_field(name="Synced Entries", value=summary if summary else "None")
                                        await message.channel.send(embed=embed_log)

                        except Exception as e:
                            print(f"Error updating results DB: {e}")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        linked_role = before.guild.get_role(LINKED_ROLE_ID)
        if linked_role and linked_role in before.roles and linked_role not in after.roles:
            embed = discord.Embed(
                description=f"{after.mention} has un<@&1459863162223595656> their account.",
                color=discord.Color.red()
            )
            channel = self.client.get_channel(LINKED_LOG_CHANNEL_ID)
            await channel.send(embed=embed)
        elif linked_role and linked_role not in before.roles and linked_role in after.roles:
            embed = discord.Embed(
                description=f"{after.mention} has <@&1459863162223595656> their account.",
                color=discord.Color.green()
            )
            channel = self.client.get_channel(LINKED_LOG_CHANNEL_ID)
            await channel.send(embed=embed)


class DatabaseCmd(commands.GroupCog, name="database"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="view", description="View database entries")
    @app_commands.describe(
        table="Select the database table",
        limit="Number of entries to show (default 100)",
        offset="Number of entries to skip (default 0)",
        player="Filter by Discord user",
        minecraft_username="Filter by Minecraft username"
    )
    @app_commands.choices(
        table=[
            app_commands.Choice(name="Tierlist Results", value="results"),
            app_commands.Choice(name="Tierlist Linking", value="linking")
        ]
    )
    async def database_view(
        self, 
        interaction: discord.Interaction,
        table: app_commands.Choice[str],
        limit: int = 100, 
        offset: int = 0, 
        player: discord.User = None, 
        minecraft_username: str = None
    ):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        if interaction.user.id not in AUTHORIZED_USERS:
            return await interaction.response.send_message("Unauthorized", ephemeral=True)
            
        pool = self.bot.tlresults_pool if table.value == "results" else self.bot.tllink_pool

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if table.value == "results":
                    table_name = "tlresults"
                else:
                    await cursor.execute("SHOW TABLES")
                    result = await cursor.fetchone()
                    if result:
                        table_name = result[0]
                    else:
                         return await interaction.response.send_message("No table found in Tierlist Linking database.", ephemeral=True)

                await cursor.execute(f"SHOW COLUMNS FROM {table_name}")
                columns = [column[0] for column in await cursor.fetchall()]
                
                query = f"SELECT * FROM {table_name}"
                conditions = []
                params = []

                if player:
                    if table.value == "results":
                        conditions.append("player_user_id = %s")
                        params.append(player.id)
                    else:
                        conditions.append("discord_id = %s")
                        params.append(str(player.id))
                
                if minecraft_username:
                    if table.value == "results":
                        conditions.append("in_game_username = %s")
                    else:
                        conditions.append("player_name = %s")
                    params.append(minecraft_username)

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                if table.value == "results":
                    query += " ORDER BY timestamp DESC"
                
                query += f" LIMIT {limit} OFFSET {offset}"
                
                await cursor.execute(query, tuple(params) if params else None)
                results = await cursor.fetchall()

        if not results:
            return await interaction.response.send_message("No entries found.", ephemeral=True)

        output = io.StringIO()
        
        header = " | ".join(columns)
        output.write(header + "\n")
        output.write("-" * len(header) + "\n")
        
        for row in results:
            row_str = [str(item) if item is not None else "NULL" for item in row]
            output.write(" | ".join(row_str) + "\n")
            
        output.seek(0)
        file = discord.File(output, filename=f"database_view_{offset}_{limit}.txt")
        
        await interaction.response.send_message(
            f"Showing {len(results)} entries (Limit: {limit}, Offset: {offset})", 
            file=file, 
            ephemeral=True
        )

    @app_commands.command(name="reset", description="Reset entire database table (DANGEROUS)")
    @app_commands.describe(
        table="Select the database table",
        confirm="Type 'confirm' to execute this command"
    )
    @app_commands.choices(
        table=[
            app_commands.Choice(name="Tierlist Results", value="results"),
            app_commands.Choice(name="Tierlist Linking", value="linking")
        ]
    )
    async def database_reset(self, interaction: discord.Interaction, table: app_commands.Choice[str], confirm: str):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        if interaction.user.id not in AUTHORIZED_USERS:
            return await interaction.response.send_message("Unauthorized", ephemeral=True)

        if confirm != "confirm":
             return await interaction.response.send_message("You must type 'confirm' to reset the database.", ephemeral=True)

        pool = self.bot.tlresults_pool if table.value == "results" else self.bot.tllink_pool
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if table.value == "results":
                    table_name = "tlresults"
                else:
                    await cursor.execute("SHOW TABLES")
                    result = await cursor.fetchone()
                    table_name = result[0] if result else "mystilinking" 

                await cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        await interaction.response.send_message(f"Table {table_name} reset in {table.name}", ephemeral=True)

    @app_commands.command(name="add", description="Manually add a database entry")
    @app_commands.describe(
        table="Select the database table",
        player="The player (Required)",
        in_game_username="In-game username (Required)",
        uuid="Minecraft UUID (Linking required, Results optional)",
        is_linked="Is the account linked? (Results only)",
        region="The region (Results only)",
        verification_code="Verification Code (Linking only)",
        score="Score achieved (Results only)",
        old_rank="Previous rank (Results only)",
        new_rank="New rank (Results only)",
        gamemode="Gamemode (Results only)",
        tester="The tester (Results only)",
        remarks="Optional remarks (Results only)",
        timestamp="Optional unix timestamp (Results only, defaults to now)"
    )
    @app_commands.choices(
        table=[
            app_commands.Choice(name="Tierlist Results", value="results"),
            app_commands.Choice(name="Tierlist Linking", value="linking")
        ]
    )
    async def database_add(
        self,
        interaction: discord.Interaction,
        table: app_commands.Choice[str],
        player: discord.User,
        in_game_username: str,
        uuid: str = None,
        is_linked: bool = False,
        region: str = None,
        verification_code: str = None,
        score: str = None,
        old_rank: str = None,
        new_rank: str = None,
        gamemode: str = None,
        tester: discord.User = None,
        remarks: str = None,
        timestamp: int = None
    ):
        if await _deny_if_restricted(interaction, interaction.user, player, tester):
            return
        if interaction.user.id not in AUTHORIZED_USERS:
            return await interaction.response.send_message("Unauthorized", ephemeral=True)
        
        final_timestamp = timestamp if timestamp is not None else int(interaction.created_at.timestamp())
        
        pool = self.bot.tlresults_pool if table.value == "results" else self.bot.tllink_pool

        if table.value == "results":
            if not all([region, score, old_rank, new_rank, gamemode, tester]):
                 return await interaction.response.send_message("<:cross1:1339153202859474956> Missing required fields for Results: region, score, old_rank, new_rank, gamemode, tester", ephemeral=True)
            
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SHOW TABLES LIKE 'tlresults'")
                    result = await cursor.fetchone()
                    if not result:
                        await cursor.execute("""
                            CREATE TABLE tlresults (
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
                            )
                        """)

                    await cursor.execute("""
                        INSERT INTO tlresults (player_discord_username, player_user_id, uuid, is_linked, region, in_game_username, score, timestamp, old_rank, new_rank, gamemode, remarks, tester_discord_username, tester_user_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (player.name, player.id, uuid, is_linked, region, in_game_username, score, final_timestamp, old_rank, new_rank, gamemode, remarks, tester.name, tester.id))
                    await conn.commit()

            try:
                await _sync_member_from_link(self.bot, interaction.guild, player.id)
            except Exception as e:
                print(f"Error syncing roles after results add for {player.id}: {e}")
        else:
            if not all([uuid, verification_code]):
                 return await interaction.response.send_message("<:cross1:1339153202859474956> Missing required fields for Linking: uuid, verification_code", ephemeral=True)

            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SHOW TABLES")
                    result = await cursor.fetchone()
                    if result:
                        table_name = result[0]
                    else:
                        table_name = "linking"
                        await cursor.execute(f"""
                            CREATE TABLE {table_name} (
                                uuid VARCHAR(36) PRIMARY KEY,
                                player_name VARCHAR(16),
                                discord_id VARCHAR(20),
                                discord_name VARCHAR(100),
                                verification_code VARCHAR(10)
                            )
                        """)
                    
                    await cursor.execute(f"""
                        INSERT INTO {table_name} (uuid, player_name, discord_id, discord_name, verification_code)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (uuid, in_game_username, str(player.id), player.name, verification_code))
                    await conn.commit()

            try:
                previous_owner_id = None
                async with self.bot.tllink_pool.acquire() as conn2:
                    async with conn2.cursor() as cursor2:
                        await cursor2.execute("SHOW TABLES")
                        tb = await cursor2.fetchone()
                        link_table = tb[0] if tb else "mystilinking"
                        await cursor2.execute(
                            f"SELECT discord_id FROM {link_table} WHERE LOWER(player_name) = LOWER(%s) AND discord_id != %s LIMIT 1",
                            (in_game_username, str(player.id)),
                        )
                        previous_owner = await cursor2.fetchone()
                        if previous_owner:
                            previous_owner_id = int(previous_owner[0])

                old_member = None
                if previous_owner_id is not None:
                    old_member = interaction.guild.get_member(previous_owner_id)
                    if not old_member:
                        try:
                            old_member = await interaction.guild.fetch_member(previous_owner_id)
                        except Exception:
                            old_member = None

                if old_member:
                    await _sync_tier_roles_for_member(interaction.guild, player, in_game_username, old_member=old_member)
                else:
                    await _sync_member_from_link(self.bot, interaction.guild, player.id)
            except Exception as e:
                print(f"Error syncing roles after linking add for {player.id}: {e}")
                
        await interaction.response.send_message(f"Entry added manually for {player.name} ({in_game_username}) in {table.name}. Roles synced too.", ephemeral=True)


    @app_commands.command(name="remove", description="Remove a database entry by ID or UUID")
    @app_commands.describe(
        table="Select the database table",
        entry_id_or_uuid="The ID (Results) or UUID (Linking) of the entry to remove"
    )
    @app_commands.choices(
        table=[
            app_commands.Choice(name="Tierlist Results", value="results"),
            app_commands.Choice(name="Tierlist Linking", value="linking")
        ]
    )
    async def database_remove(self, interaction: discord.Interaction, table: app_commands.Choice[str], entry_id_or_uuid: str):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        if interaction.user.id not in AUTHORIZED_USERS:
            return await interaction.response.send_message("Unauthorized", ephemeral=True)

        pool = self.bot.tlresults_pool if table.value == "results" else self.bot.tllink_pool
        affected_member_ids = []

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if table.value == "results":
                    await cursor.execute("SELECT player_user_id FROM tlresults WHERE id = %s", (entry_id_or_uuid,))
                    rows = await cursor.fetchall()
                    affected_member_ids = [int(row[0]) for row in rows if row and row[0] is not None]
                    if any(_has_restricted_role(interaction.guild.get_member(member_id)) for member_id in affected_member_ids):
                        return await interaction.response.send_message("<:cross1:1339153202859474956> That entry belongs to a restricted user and cannot be modified here.", ephemeral=True)
                    query = "DELETE FROM tlresults WHERE id = %s"
                else:
                    await cursor.execute("SHOW TABLES")
                    result = await cursor.fetchone()
                    table_name = result[0] if result else "linking"
                    await cursor.execute(f"SELECT discord_id FROM {table_name} WHERE uuid = %s", (entry_id_or_uuid,))
                    rows = await cursor.fetchall()
                    affected_member_ids = [int(row[0]) for row in rows if row and row[0] is not None]
                    if any(_has_restricted_role(interaction.guild.get_member(member_id)) for member_id in affected_member_ids):
                        return await interaction.response.send_message("<:cross1:1339153202859474956> That entry belongs to a restricted user and cannot be modified here.", ephemeral=True)
                    query = f"DELETE FROM {table_name} WHERE uuid = %s"

                await cursor.execute(query, (entry_id_or_uuid,))
                deleted_count = cursor.rowcount
                await conn.commit()

        if deleted_count > 0:
            if table.value == "results":
                for member_id in sorted(set(affected_member_ids)):
                    try:
                        await _sync_member_from_link(self.bot, interaction.guild, member_id)
                    except Exception as e:
                        print(f"Error syncing roles after results remove for {member_id}: {e}")
            else:
                for member_id in sorted(set(affected_member_ids)):
                    member = interaction.guild.get_member(member_id)
                    if not member:
                        try:
                            member = await interaction.guild.fetch_member(member_id)
                        except Exception:
                            member = None
                    if member:
                        try:
                            await _remove_tier_roles_from_member(member)
                        except Exception as e:
                            print(f"Error removing roles after link remove for {member_id}: {e}")

        if deleted_count > 0:
            await interaction.response.send_message(f"Successfully removed entry with ID/UUID {entry_id_or_uuid} from {table.name}. Roles synced too.", ephemeral=True)
        else:
            await interaction.response.send_message(f"<:warn:1459986909911842846> No entry found with ID/UUID {entry_id_or_uuid} in {table.name}.", ephemeral=True)

    @app_commands.command(name="blacklist", description="Blacklist a user by removing all matching entries and applying the Restricted role")
    @app_commands.describe(
        table="Select the database table",
        discord_user="Discord user to match",
        minecraft_username="Minecraft username to match",
    )
    @app_commands.choices(
        table=[
            app_commands.Choice(name="Tierlist Results", value="results"),
            app_commands.Choice(name="Tierlist Linking", value="linking"),
        ]
    )
    async def database_blacklist(
        self,
        interaction: discord.Interaction,
        table: app_commands.Choice[str],
        discord_user: discord.User = None,
        minecraft_username: str = None,
    ):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        if interaction.user.id not in AUTHORIZED_USERS:
            return await interaction.response.send_message("Unauthorized", ephemeral=True)

        if bool(discord_user) == bool(minecraft_username):
            return await interaction.response.send_message(
                "<:warn:1459986909911842846> Provide exactly one of `discord_user` or `minecraft_username`.",
                ephemeral=True,
            )

        pool = self.bot.tlresults_pool if table.value == "results" else self.bot.tllink_pool
        affected_member_ids: list[int] = []

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if table.value == "results":
                    if discord_user:
                        await cursor.execute(
                            "SELECT DISTINCT player_user_id FROM tlresults WHERE player_user_id = %s",
                            (discord_user.id,),
                        )
                        affected_member_ids = [int(row[0]) for row in await cursor.fetchall() if row and row[0] is not None]
                        delete_query = "DELETE FROM tlresults WHERE player_user_id = %s"
                        delete_param = discord_user.id
                    else:
                        await cursor.execute(
                            "SELECT DISTINCT player_user_id FROM tlresults WHERE LOWER(in_game_username) = LOWER(%s)",
                            (minecraft_username,),
                        )
                        affected_member_ids = [int(row[0]) for row in await cursor.fetchall() if row and row[0] is not None]
                        delete_query = "DELETE FROM tlresults WHERE LOWER(in_game_username) = LOWER(%s)"
                        delete_param = minecraft_username
                else:
                    await cursor.execute("SHOW TABLES")
                    result = await cursor.fetchone()
                    table_name = result[0] if result else "mystilinking"
                    if discord_user:
                        await cursor.execute(
                            f"SELECT DISTINCT discord_id FROM {table_name} WHERE discord_id = %s",
                            (str(discord_user.id),),
                        )
                        affected_member_ids = [int(row[0]) for row in await cursor.fetchall() if row and row[0] is not None]
                        delete_query = f"DELETE FROM {table_name} WHERE discord_id = %s"
                        delete_param = str(discord_user.id)
                    else:
                        await cursor.execute(
                            f"SELECT DISTINCT discord_id FROM {table_name} WHERE LOWER(player_name) = LOWER(%s)",
                            (minecraft_username,),
                        )
                        affected_member_ids = [int(row[0]) for row in await cursor.fetchall() if row and row[0] is not None]
                        delete_query = f"DELETE FROM {table_name} WHERE LOWER(player_name) = LOWER(%s)"
                        delete_param = minecraft_username

                await cursor.execute(delete_query, (delete_param,))
                deleted_count = cursor.rowcount
                await conn.commit()

        if deleted_count > 0:
            for member_id in sorted(set(affected_member_ids)):
                member = interaction.guild.get_member(member_id)
                if not member:
                    try:
                        member = await interaction.guild.fetch_member(member_id)
                    except Exception:
                        member = None
                if not member:
                    continue
                try:
                    await _apply_blacklist(interaction.guild, member)
                except Exception as e:
                    print(f"Error blacklisting member {member_id}: {e}")

        if deleted_count > 0:
            await interaction.response.send_message(
                f"<:checkmark:1339153448926580818> Blacklisted {deleted_count} entr{'y' if deleted_count == 1 else 'ies'} from {table.name} and applied the Restricted role.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"<:warn:1459986909911842846> No matching entries found in {table.name}.",
                ephemeral=True,
            )

    @app_commands.command(name="fixname", description="Update one or more old usernames to a new username and optionally set linked status to true.")
    @app_commands.describe(
        old_names="Comma-separated list of old in-game usernames to update",
        new_name="The new in-game username to set",
        set_linked="Set is_linked to True for the new username (default: True)"
    )
    async def fixname(self, interaction: discord.Interaction, old_names: str, new_name: str, set_linked: bool = True):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        if interaction.user.id not in AUTHORIZED_USERS:
            return await interaction.response.send_message("Unauthorized", ephemeral=True)

        pool = self.bot.tlresults_pool
        updated_count = 0
        old_names_list = [name.strip() for name in old_names.split(",") if name.strip()]
        if not old_names_list:
            return await interaction.response.send_message("No valid old names provided.", ephemeral=True)
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Find all matching ids for all old_names
                format_strings = ','.join(['%s'] * len(old_names_list))
                await cursor.execute(f"SELECT id, in_game_username FROM tlresults WHERE in_game_username IN ({format_strings})", tuple(old_names_list))
                rows = await cursor.fetchall()
                ids = [row[0] for row in rows]
                found_names = set(row[1] for row in rows)
                await cursor.execute(f"SELECT DISTINCT player_user_id FROM tlresults WHERE in_game_username IN ({format_strings})", tuple(old_names_list))
                affected_member_ids = [int(row[0]) for row in await cursor.fetchall() if row and row[0] is not None]
                if any(_has_restricted_role(interaction.guild.get_member(member_id)) for member_id in affected_member_ids):
                    return await interaction.response.send_message("<:cross1:1339153202859474956> One or more matching entries belong to a restricted user and cannot be modified here.", ephemeral=True)
                if ids:
                    for entry_id in ids:
                        await cursor.execute(
                            "UPDATE tlresults SET in_game_username = %s, is_linked = %s WHERE id = %s",
                            (new_name, set_linked, entry_id)
                        )
                        updated_count += 1
                    await conn.commit()
        if updated_count > 0:
            old_names_str = ', '.join(found_names)
            affected_member_ids = sorted({int(row[0]) for row in rows if row and row[0] is not None})
            for member_id in affected_member_ids:
                try:
                    await _sync_member_from_link(self.bot, interaction.guild, member_id)
                except Exception as e:
                    print(f"Error syncing roles after fixname for {member_id}: {e}")
            await interaction.response.send_message(
                f"<:checkmark:1339153448926580818> Updated {updated_count} entr{'y' if updated_count == 1 else 'ies'} from '{old_names_str}' to '{new_name}' and set linked status to {set_linked}. Roles synced too.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"No entries found for the provided old names.", ephemeral=True
            )

    @app_commands.command(
        name="rolesync",
        description="Sync a user's tier roles from their linked account or a provided IGN",
    )
    @app_commands.describe(
        user="The Discord user to receive the tier roles",
        minecraft_username="Optional in-game username. If blank, the user's linked IGN will be used.",
        old_account="Optional second Discord account to remove all tier roles from",
    )
    async def rolesync(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        minecraft_username: str = None,
        old_account: discord.Member = None,
    ):
        if await _deny_if_restricted(interaction, interaction.user, user, old_account):
            return
        if interaction.user.id not in AUTHORIZED_USERS:
            return await interaction.response.send_message("Unauthorized", ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)

        if old_account and old_account.id == user.id:
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> The old account must be a different Discord user from the target user.",
                ephemeral=True,
            )

        ign = minecraft_username.strip() if minecraft_username else None
        if not ign:
            ign = await _get_linked_player_name(self.bot, user.id)

        if not ign:
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> No IGN was provided and no linked IGN could be found for that user.",
                ephemeral=True,
            )

        try:
            target_roles, missing_roles, removed_old_roles = await _sync_tier_roles_for_member(
                interaction.guild,
                user,
                ign,
                old_member=old_account,
            )
        except Exception as e:
            return await interaction.followup.send(
                f"<:cross1:1339153202859474956> Failed to fetch tier data for `{ign}`: {e}",
                ephemeral=True,
            )

        embed = discord.Embed(
            title="Tier roles synced",
            description=f"Synced tier roles for {user.mention} using `{ign}`.",
            color=discord.Color.green(),
        )
        if target_roles:
            embed.add_field(
                name="Assigned Roles",
                value=", ".join(role.mention for role in target_roles),
                inline=False,
            )
        else:
            embed.add_field(
                name="Assigned Roles",
                value="No tier roles were found to assign.",
                inline=False,
            )

        if removed_old_roles:
            embed.add_field(
                name="Removed From Old Account",
                value=f"Removed {len(removed_old_roles)} tier role{'s' if len(removed_old_roles) != 1 else ''} from {old_account.mention}.",
                inline=False,
            )

        if missing_roles:
            embed.add_field(
                name="Missing Roles",
                value="\n".join(missing_roles),
                inline=False,
            )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Waitlist(bot))
    await bot.add_cog(WaitlistCmd(bot))
    await bot.add_cog(DatabaseCmd(bot))
