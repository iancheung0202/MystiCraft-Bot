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

from constants import ROLE_IDS, SERVER_IDS

EMOJI_EMERALD       = "<:emerald:1518031176730804244>"
EMOJI_REDSTONE      = "<:redstone_dust:1518031324588539986>"
EMOJI_GOLD_INGOT    = "<:gold_ingot:1518031441248653433>"
EMOJI_STEVE         = "<:steve:1518031537814110382>"
EMOJI_NETHER_STAR   = "<:nether_star:1518033504120606771>"
EMOJI_COMPASS       = "<a:compass:1518032475803226214>"
EMOJI_ENDER_PEARL   = "<:ender_pearl:1518033866995269763>"
EMOJI_MC_CLOCK      = "<:mc_clock:1518027805361967104>"
EMOJI_MAP           = "<:map:1518038367521210499>"
EMOJI_BOOK          = "<:book:1518051136488214549>"
EMOJI_SCROLL        = "<:parchment:1518454271719510297>"
EMOJI_FEATHER       = "<:feather:1518454349053952150>"
EMOJI_BARRIER       = "<:barrier:1518454369887195228>"
EMOJI_SPYGLASS      = "<:spyglass:1518454328480891083>"
EMOJI_HOURGLASS     = "<:hourglass:1518454206162538546>"
EMOJI_REPLY         = "<:reply:1036792837821435976>"
EMOJI_ARROW         = "<a:arightarrow:1518483846130040853>"
EMOJI_TIERLIST      = "<:mysticrafttierlist:1460527955309498550>"
EMOJI_CONNECT       = "<:lodestone:1518038285354795158>"
EMOJI_RANK          = "<:Trophy:1523013568067539044>"
EMOJI_GOLD          = "<:gold:1518477859679633539>"
EMOJI_IRON          = "<:iron:1518477842373935174>"
EMOJI_NETHERITE     = "<:netherite:1518477903568830524>"
EMOJI_CRYSTAL       = "<:crystal:1518050761010057290>"
EMOJI_BOOSTER       = "<:Booster_Logo:1154871576047657051>"
EMOJI_STATS         = "<:stats:1523014008490426468>"

CROSS = "<:cross1:1339153202859474956>"
CHECK = "<:checkmark:1339153448926580818>"
WARN  = "<:warn:1459986909911842846>"

BOOSTER_ROLE_ID = 1307344085358481431
BOOSTER_EMOJI = "<:boosting:1466562469773443367>"

NOT_OPEN_TEXT = f"Having access to this channel simply means that you are waiting to be tested at some point. **It does not mean you are going to be tested immediately.** Please be patient!\n\n"
OPEN_TEXT = f"Click `Join Queue` and wait for your turn, though this does not guarantee you'll be tested this time.\n\n"
INSTRUCTIONS_TEXT = (
    f"> {EMOJI_BOOSTER} **<@&{BOOSTER_ROLE_ID}>** can **skip everyone in a queue** to get tested first.\n"
    f"> {EMOJI_BOOK} You will be placed on a **2-day cooldown** after each test.\n"
    f"> {EMOJI_SPYGLASS} Make sure the queue is for **your region** before joining and respond promptly when it's your turn. Otherwise, your tester reserves the right to skip you."
)

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
LINKED_LOG_CHANNEL_ID = 1460005738897473706
RESTRICTED_ROLE_ID = 1340417478857068564

TIER_ROLE_PREFIXES = {"HT1", "LT1", "HT2", "LT2", "HT3", "LT3", "HT4", "LT4", "HT5", "LT5"}
TIER_SYNC_GAMEMODES = {"NPOT", "DPOT", "SMP", "SWORD", "CRYSTAL", "AXE", "MACE", "UHC"}
GAMEMODE_DISPLAY = {"npot": "NPOT", "dpot": "DPOT", "smp": "SMP", "sword": "Sword", "crystal": "Crystal", "axe": "Axe", "mace": "Mace", "uhc": "UHC"}
CHANNEL_TO_GAMEMODE = {
    1337057627661926533: "npot",
    1337057604907700224: "dpot",
    1337057681776836629: "smp",
    1337062543780483137: "sword",
    1337062560150720562: "crystal",
    1337073373393715262: "axe",
    1338250590299488399: "mace",
    1338250613829406741: "uhc",
}

def is_tier_role(role: discord.Role) -> bool:
    parts = role.name.split(" ")
    return len(parts) >= 2 and parts[0].upper() in TIER_ROLE_PREFIXES and parts[1].upper() in TIER_SYNC_GAMEMODES

def get_tier_rolename(rank_data) -> str | None:
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

async def fetch_ign(bot, discord_id: int) -> str | None:
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

async def fetch_tier_profile(player_name: str):
    api_url = f"https://tierlist.mysticraft.xyz/api/player/{quote_plus(player_name)}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"}
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        async with session.get(api_url) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Tier API returned status {resp.status}")
            return await resp.json()

def collect_tier_roles(guild: discord.Guild, data: dict) -> tuple[list[discord.Role], list[str]]:
    ranks = data.get("ranks", {}) if isinstance(data, dict) else {}
    role_matches: list[discord.Role] = []
    missing_roles: list[str] = []
    for mode in ["NPOT", "DPOT", "SMP", "SWORD", "CRYSTAL", "AXE", "MACE", "UHC"]:
        rank_label = get_tier_rolename(ranks.get(mode))
        if not rank_label:
            continue
        expected_name = f"{rank_label} {mode}"
        match = next((role for role in guild.roles if role.name.upper() == expected_name.upper()), None)
        if match:
            role_matches.append(match)
        else:
            missing_roles.append(expected_name)
    return role_matches, missing_roles

async def sync_tier_roles(guild: discord.Guild, member: discord.Member, ign: str, old_member: discord.Member = None):
    profile_data = await fetch_tier_profile(ign)
    target_roles, missing_roles = collect_tier_roles(guild, profile_data)
    current_target_roles = [role for role in member.roles if is_tier_role(role)]
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
        removed_old_roles = [role for role in old_member.roles if is_tier_role(role)]
        if removed_old_roles:
            await old_member.remove_roles(*removed_old_roles, reason=f"Tier role migration to {member.id}")
    return target_roles, missing_roles, removed_old_roles

async def remove_tier_roles(member: discord.Member) -> list[discord.Role]:
    removed_roles = [role for role in member.roles if is_tier_role(role)]
    if removed_roles:
        await member.remove_roles(*removed_roles, reason="Tier link removed")
    return removed_roles

async def sync_member(bot, guild: discord.Guild, member_id: int) -> tuple[list[discord.Role], list[str]]:
    ign = await fetch_ign(bot, member_id)
    if not ign:
        return [], []
    member = guild.get_member(member_id)
    if not member:
        try:
            member = await guild.fetch_member(member_id)
        except Exception:
            return [], []
    target_roles, missing_roles, _ = await sync_tier_roles(guild, member, ign)
    return target_roles, missing_roles


def is_restricted(member: discord.Member | discord.User | None) -> bool:
    return bool(member and getattr(member, "roles", None) and any(role.id == RESTRICTED_ROLE_ID for role in member.roles))

async def deny_if_restricted(interaction: discord.Interaction, *members, message: str = "<:cross1:1339153202859474956> This user is restricted from using waitlist actions.") -> bool:
    if any(is_restricted(member) for member in members if member is not None):
        await interaction.response.send_message(message, ephemeral=True)
        return True
    return False

async def restrict(guild: discord.Guild, member: discord.Member):
    removed_roles = await remove_tier_roles(member)
    restricted_role = guild.get_role(RESTRICTED_ROLE_ID)
    if restricted_role and restricted_role not in member.roles:
        await member.add_roles(restricted_role, reason="Waitlist blacklist")
    return removed_roles

class QueueEntry:
    """Represents a single queue entry."""
    def __init__(self, user_id: int, mention: str, username: str, is_booster: bool, join_time: int = None):
        self.user_id = user_id
        self.mention = mention
        self.username = username
        self.is_booster = is_booster
        self.join_time = join_time if join_time is not None else int(time.time())

    def to_string(self, position: int) -> str:
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
        self.active_sessions: Dict[int, dict] = {} # member_id -> {tester_id, thread_url}
        self.lock = asyncio.Lock() # for concurrent access to internal queue state
        self.last_hash = None # track last synced state to detect changes
        self.last_closed_time = None # track when queue was last closed
        self.is_open = False # track whether the queue is currently open (no embed check needed)
    
    async def start_worker(self):
        if self.worker_task is None:
            self.worker_task = asyncio.create_task(self.worker())
        if self.sync_task is None:
            self.sync_task = asyncio.create_task(self.sync_loop())
    
    async def stop_worker(self):
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
    
    async def worker(self):
        while True:
            try:
                operation = await self.operation_queue.get()
                await self.handle_operation(operation)
                self.operation_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error processing queue operation for {self.gamemode}: {e}")
    
    async def handle_operation(self, op: QueueOperation):
        async with self.lock:
            try:
                if op.op_type == "JOIN":
                    await self.handle_join(op)
                elif op.op_type == "LEAVE":
                    await self.handle_leave(op)
            except Exception as e:
                print(f"Error in handle_operation: {e}")
    
    async def handle_join(self, op: QueueOperation):
        if any(e.user_id == op.user_id for e in self.queue):
            return
        entry = QueueEntry(user_id=op.user_id, mention=op.member.mention, username=op.member.name, is_booster=op.is_booster, join_time=int(time.time()))
        if op.is_booster:
            last_booster_idx = -1
            for i, e in enumerate(self.queue):
                if e.is_booster:
                    last_booster_idx = i
            self.queue.insert(last_booster_idx + 1, entry)
        else:
            self.queue.append(entry)

    async def handle_leave(self, op: QueueOperation):
        self.queue = [e for e in self.queue if e.user_id != op.user_id]
    
    def get_hash(self) -> str:
        queue_str = "|".join([str(e.user_id) for e in self.queue])
        active_str = "|".join([f"{k}:{v['tester_id']}" for k, v in sorted(self.active_sessions.items())])
        return f"{queue_str}#{active_str}"
    
    async def sync_loop(self):
        while True:
            try:
                await asyncio.sleep(5)
                current_state = self.get_hash()
                if current_state != self.last_hash:
                    await self.sync_layout()
                    self.last_hash = current_state
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in layout sync loop for {self.gamemode}: {e}")

    async def sync_layout(self):
        if not self.queue_channel_id:
            return
        try:
            channel = self.bot.get_channel(self.queue_channel_id)
            if not channel:
                return
            async for msg in channel.history(limit=10):
                if msg.author.id == self.bot.application_id:
                    item = return_item(self.gamemode)
                    container = build_queue_container(gamemode=self.gamemode, queue=self.queue.copy(), active_sessions=self.active_sessions.copy(), is_open=self.is_open, ping_role_id=item[0])
                    new_view = QueuePanelView(gamemode=self.gamemode, queue_manager=self, bot=self.bot, is_open=self.is_open, container=container, )
                    await msg.edit(view=new_view)
                    break
        except Exception as e:
            print(f"Error syncing layout for {self.gamemode}: {e}")
    
    def set_message_location(self, channel_id: int, message_id: int = None):
        self.queue_channel_id = channel_id
        self.queue_message_id = message_id
    
    async def enqueue_join(self, user_id: int, member: discord.Member, interaction: discord.Interaction, is_booster: bool):
        operation = QueueOperation("JOIN", user_id, member, interaction, is_booster)
        await self.operation_queue.put(operation)
    
    async def enqueue_leave(self, user_id: int, member: discord.Member, interaction: discord.Interaction):
        operation = QueueOperation("LEAVE", user_id, member, interaction, is_booster=False)
        await self.operation_queue.put(operation)
    
    def get_queue_copy(self) -> List[QueueEntry]:
        return self.queue.copy()
    
    async def pop_first(self) -> QueueEntry:
        async with self.lock:
            if self.queue:
                return self.queue.pop(0)
            return None
    
    def set_active_sessions(self, sessions: Dict[int, dict]):
        self.active_sessions = sessions.copy()
    
    def add_active_session(self, member_id: int, tester_id: int, thread_url: str = ""):
        self.active_sessions[member_id] = {"tester_id": tester_id, "thread_url": thread_url}
    
    def remove_active_session(self, member_id: int):
        if member_id in self.active_sessions:
            del self.active_sessions[member_id]
    
    def mark_closed(self):
        self.last_closed_time = int(time.time())
        self.is_open = False
    
    def should_clear_on_start(self) -> bool:
        if self.last_closed_time is None:
            return False
        time_since_close = int(time.time()) - self.last_closed_time
        return time_since_close > 600  # 10 minutes
    
    def clear_active_sessions(self):
        self.active_sessions.clear()
    
    def clear(self):
        self.queue.clear()
        self.active_sessions.clear()
        self.last_hash = None
        self.last_closed_time = None
        self.is_open = False


class QueueManagerPool:
    """Manages QueueManager instances for all gamemodes."""
    def __init__(self, bot):
        self.bot = bot
        self.managers: Dict[str, QueueManager] = {}
    
    def get_manager(self, gamemode: str) -> QueueManager:
        if gamemode not in self.managers:
            manager = QueueManager(gamemode, self.bot)
            self.managers[gamemode] = manager
            asyncio.create_task(manager.start_worker())
        return self.managers[gamemode]
    
    async def shutdown(self):
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
        if await deny_if_restricted(interaction, interaction.user):
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
            linked_role_id = ROLE_IDS[SERVER_IDS["tierlist"]]["linked"]
            if linked_role_id not in [role.id for role in interaction.user.roles]:
                embeds.append(
                    discord.Embed(
                        title=f"{WARN} Account Linking Required for Testing",
                        description=f"> To be eligible for testing, you must follow the instructions in <#1460525451368861818> to get linked. Once completed, you will automatically receive <@&{linked_role_id}> and gain access to the queue.",
                        color=discord.Colour.red(),
                    )
                )
            await interaction.followup.send(embeds=embeds, ephemeral=True)


class WaitlistSelectionView(discord.ui.View):
    def __init__(self, placeholder=None, options=None, *, timeout=None):
        super().__init__(timeout=timeout)
        self.add_item(WaitlistSelection(placeholder, options))


def build_ign_embed(ign: str) -> discord.Embed:
    if ign and ign != "None":
        return discord.Embed(
            description=f'{EMOJI_STEVE} [{ign}](https://tierlist.mysticraft.xyz/?player={ign}) will be the account that receives your new rank.\n\n-# If this is the wrong account, use `/unlink` in <#1306688932746104972> and follow the linking instructions in <#1460525451368861818> to link a different account.',
            color=discord.Color.blue(),
        )
    return None

def build_queue_container(gamemode: str, queue: list, active_sessions: dict, is_open: bool, ping_role_id: int = None) -> discord.ui.Container:
    """Build a Container with instructions + queue list + currently testing."""
    attrs: dict = {}

    if is_open and ping_role_id:
        attrs["ping"] = discord.ui.TextDisplay(f"## {EMOJI_TIERLIST} **{GAMEMODE_DISPLAY.get(gamemode, gamemode)}** Queue Open - <@&{ping_role_id}> ")
        attrs["instructions"] = discord.ui.TextDisplay(f"{OPEN_TEXT}{INSTRUCTIONS_TEXT}")
    else:
        attrs["panel_title"] = discord.ui.TextDisplay(f"## {EMOJI_TIERLIST} **{GAMEMODE_DISPLAY.get(gamemode, gamemode)}** Waitlist")
        attrs["instructions"] = discord.ui.TextDisplay(f"{NOT_OPEN_TEXT}{INSTRUCTIONS_TEXT}")

    if is_open:
        attrs["sep0"] = discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large)

        total = len(queue)
        attrs["queue_header"] = discord.ui.TextDisplay(
            f"### {EMOJI_COMPASS} Queue ({total} player{'s' if total != 1 else ''})"
        )
        if queue:
            for i, entry in enumerate(queue[:15]):
                display = entry.to_string(i + 1)
                attrs[f"entry_{i}"] = discord.ui.TextDisplay(display)
            if total > 15:
                attrs["overflow"] = discord.ui.TextDisplay(
                    f"{EMOJI_REPLY} ... and {total - 15} more in queue"
                )
        else:
            attrs["empty"] = discord.ui.TextDisplay(
                f"{EMOJI_HOURGLASS} Queue is empty - waiting for players to join!"
            )

        attrs["sep1"] = discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large)
        attrs["serving_header"] = discord.ui.TextDisplay(
            f"### {EMOJI_SPYGLASS} Currently Testing"
        )
        if active_sessions:
            for i, (member_id, session) in enumerate(active_sessions.items(), 1):
                tester_id = session["tester_id"]
                thread_url = session.get("thread_url", "")
                url_suffix = f" [〚↗〛]({thread_url})" if thread_url else ""
                attrs[f"session_{i}"] = discord.ui.TextDisplay(
                    f"{i}. {EMOJI_STEVE} <@{member_id}> *(by <@{tester_id}>)*{url_suffix}"
                )
        else:
            attrs["no_session"] = discord.ui.TextDisplay(
                f"{EMOJI_HOURGLASS} No active sessions"
            )
    else:
        attrs["instructions"] = discord.ui.TextDisplay(f"{NOT_OPEN_TEXT}{INSTRUCTIONS_TEXT}")
        attrs["sep0"] = discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large)
        attrs["closed_msg"] = discord.ui.TextDisplay(
            f"{EMOJI_BARRIER} **Queue is closed.** No testers are currently available.\n"
            f"{EMOJI_REPLY} You will be pinged when a tester opens the queue."
        )

    container_cls = type("QueueContainer", (discord.ui.Container,), attrs)
    return container_cls(accent_color=0x22aef5)


class QueuePanelView(discord.ui.LayoutView):
    """Queue control panel – rebuilt fresh on each sync cycle."""
    def __init__(self, gamemode: str, queue_manager, bot, is_open: bool, container: discord.ui.Container):
        super().__init__(timeout=None)
        self.gamemode = gamemode.lower()
        self.queue_manager = queue_manager
        self.bot = bot
        self.is_open = is_open

        self.add_item(container)

        gm = self.gamemode

        start_btn = discord.ui.Button(
            label="Start",
            style=discord.ButtonStyle.gray if is_open else discord.ButtonStyle.green,
            emoji=EMOJI_EMERALD,
            disabled=is_open,
            custom_id=f"{gm}_start",
        )
        start_btn.callback = self.start_queue

        next_btn = discord.ui.Button(
            label="Next",
            style=discord.ButtonStyle.blurple if is_open else discord.ButtonStyle.gray,
            emoji=EMOJI_ARROW,
            disabled=not is_open,
            custom_id=f"{gm}_next",
        )
        next_btn.callback = self.next_player

        end_btn = discord.ui.Button(
            label="End",
            style=discord.ButtonStyle.gray,
            emoji=EMOJI_BARRIER,
            disabled=not is_open,
            custom_id=f"{gm}_end",
        )
        end_btn.callback = self.end_queue

        self.add_item(discord.ui.ActionRow(start_btn, next_btn, end_btn))

        join_btn = discord.ui.Button(
            label=f"Join Queue",
            style=discord.ButtonStyle.green if is_open else discord.ButtonStyle.gray,
            disabled=not is_open,
            emoji=EMOJI_CONNECT,
            custom_id=f"{gm}_join",
        )
        join_btn.callback = self.join_queue

        leave_btn = discord.ui.Button(
            label="Leave Queue",
            style=discord.ButtonStyle.gray,
            disabled=not is_open,
            emoji=EMOJI_REDSTONE,
            custom_id=f"{gm}_leave",
        )
        leave_btn.callback = self.leave_queue

        self.add_item(discord.ui.ActionRow(join_btn, leave_btn))

    async def require_tester(self, interaction: discord.Interaction) -> bool:
        item = return_item(self.gamemode)
        if interaction.guild.get_role(item[2]) in interaction.user.roles:
            return True
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"{CROSS} You are not a tester for this gamemode. Apply to be a tester at <#1516294780231876689>.",
                color=discord.Color.red()
            ),
            ephemeral=True,
        )
        return False

    async def start_queue(self, interaction: discord.Interaction):
        if await deny_if_restricted(interaction, interaction.user):
            return
        if not await self.require_tester(interaction):
            return

        item = return_item(self.gamemode)
        channel_id = item[1]
        gamemode_channel = interaction.guild.get_channel(channel_id)
        queue_manager = self.queue_manager
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{EMOJI_MAP} Select Your Region",
                description=(
                    f"Choose the region you are testing **{GAMEMODE_DISPLAY.get(self.gamemode, self.gamemode)}** for.\n"
                    f"{EMOJI_REPLY} The queue will open and ping <@&{item[0]}>."
                ),
                color=discord.Color.blue(),
            ),
            view=RegionSelectView(gamemode_channel, queue_manager, self.gamemode, self.bot),
            ephemeral=True,
        )

    async def next_player(self, interaction: discord.Interaction):
        if await deny_if_restricted(interaction, interaction.user):
            return
        if not await self.require_tester(interaction):
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        queue_manager = self.queue_manager
        next_entry = await queue_manager.pop_first()
        if not next_entry:
            return await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{CROSS} Queue is empty. Please wait for players to join first.",
                    color=discord.Color.red()
                ),
                ephemeral=True,
            )
        next_id = next_entry.user_id
        next_member = interaction.guild.get_member(next_id)
        if next_member is None:
            try:
                next_member = await interaction.guild.fetch_member(next_id)
            except Exception:
                next_member = None
        tester_id = interaction.user.id
        try:
            thread = await interaction.channel.create_thread(name=f"{(next_member.name if next_member else str(next_id))}'s ticket ({next_id})")
        except Exception as e:
            return await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{WARN} Unable to create a thread: {e}",
                    color=discord.Color.red()
                ),
                ephemeral=True,
            )
        queue_manager.add_active_session(next_id, tester_id, thread.jump_url)
        linked_ign = "None"
        try:
            async with self.bot.tllink_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SHOW TABLES")
                    tb = await cursor.fetchone()
                    link_table = tb[0] if tb else "mystilinking"
                    await cursor.execute(
                        f"SELECT player_name FROM {link_table} WHERE discord_id = %s",
                        (str(next_id),),
                    )
                    link_res = await cursor.fetchone()
                    if link_res:
                        linked_ign = link_res[0]
        except Exception as e:
            print(f"Error fetching IGN: {e}")
        region_str = f"{WARN} Unknown"
        try:
            async with self.bot.tlresults_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "SELECT region FROM tlresults WHERE player_user_id = %s AND gamemode = %s ORDER BY timestamp DESC LIMIT 1",
                        (next_id, self.gamemode.upper()),
                    )
                    row = await cursor.fetchone()
                    if row:
                        region_str = row[0]
        except Exception:
            pass
        current_rank = "None"
        if next_member:
            for role in next_member.roles:
                if self.gamemode in role.name.lower() and "waitlist" not in role.name.lower():
                    current_rank = role.name.split(" ")[0]
                    break
        # await thread.add_user(next_member)
        # await thread.add_user(interaction.user)
        await interaction.followup.send(
            embed=discord.Embed(
                description=f"{EMOJI_EMERALD} Successfully added you and <@{next_id}> to a thread.",
                color=discord.Color.green()
            ),
            view=discord.ui.View().add_item(discord.ui.Button(label="Go to Thread", url=thread.jump_url, style=discord.ButtonStyle.link)),
            ephemeral=True,
        )
        tester_ign = await fetch_ign(self.bot, tester_id)
        has_linked = next_member and ROLE_IDS[SERVER_IDS["tierlist"]]["linked"] in [r.id for r in next_member.roles]
        session_container = build_session_container(member_name=next_member.name if next_member else str(next_id), ign=linked_ign, current_rank=current_rank, region=region_str, is_linked=has_linked, tester_ign=tester_ign, member_mention=f"<@{next_id}>", tester_mention=f"<@{tester_id}>", gamemode=self.gamemode)
        session_layout = discord.ui.LayoutView(timeout=None)
        session_layout.add_item(session_container)
        await thread.send(view=session_layout)
        await thread.send(view=ThreadActionsView())

    async def end_queue(self, interaction: discord.Interaction):
        if await deny_if_restricted(interaction, interaction.user):
            return
        if not await self.require_tester(interaction):
            return

        embed = discord.Embed(
            title=f"{EMOJI_GOLD_INGOT} Close the {GAMEMODE_DISPLAY.get(self.gamemode, self.gamemode)} queue?",
            description=(
                f"-# {EMOJI_REPLY} The queue will be marked as closed and players can no longer join.\n"
                f"-# {EMOJI_REPLY} If another tester is still testing, **DO NOT** end the queue before they are finished.\n"
                f"-# {EMOJI_REPLY} Queue positions will be preserved for **10 minutes** in case of a quick reopen."
            ),
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(
            embed=embed,
            view=ConfirmActionView(self.confirm_end_queue),
            ephemeral=True,
        )

    async def confirm_end_queue(self, interaction: discord.Interaction):
        item = return_item(self.gamemode)
        channel_id = item[1]
        gamemode_channel = interaction.guild.get_channel(channel_id)
        messages = [m async for m in gamemode_channel.history(limit=10) if m.author.id == interaction.client.application_id]
        if not messages:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} No queue message found.",
                    color=discord.Color.red()
                ),
                ephemeral=True,
            )
        old = messages[0]
        self.queue_manager.mark_closed()
        container = build_queue_container(gamemode=self.gamemode, queue=self.queue_manager.queue.copy(), active_sessions=self.queue_manager.active_sessions.copy(), is_open=False, ping_role_id=item[0])
        closed_view = QueuePanelView(gamemode=self.gamemode, queue_manager=self.queue_manager, bot=self.bot, is_open=False, container=container)
        await old.edit(view=closed_view)
        await interaction.response.edit_message(
            embed=discord.Embed(
                description=f"{CHECK} Queue closed and positions preserved for a quick reopen within 10 minutes.",
                color=discord.Color.green()
            ),
            view=None,
        )

    async def join_queue(self, interaction: discord.Interaction):
        if await deny_if_restricted(interaction, interaction.user):
            return
        if ROLE_IDS[SERVER_IDS["tierlist"]]["linked"] not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{WARN} Account Linking Required for Testing",
                    description=f"Link your account by following the instructions in <#1460525451368861818> first and then try again.",
                    color=discord.Colour.red(),
                ),
                ephemeral=True,
            )

        qm = self.queue_manager
        if not qm:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} Something went wrong. `[Error 1]`",
                    color=discord.Color.red()
                ),
                ephemeral=True,
            )

        if interaction.user.id in qm.active_sessions:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} You are currently being tested! You cannot join the queue.",
                    color=discord.Color.red()
                ),
                ephemeral=True,
            )

        ign = await fetch_ign(self.bot, interaction.user.id)
        ign_embed = build_ign_embed(ign)

        existing_pos = next((i + 1 for i, e in enumerate(qm.queue) if e.user_id == interaction.user.id), None)
        is_waiting = False
        if not existing_pos:
            for op in list(qm.operation_queue._queue):
                if op.user_id == interaction.user.id and op.op_type == "JOIN":
                    is_waiting = True
                    break

        if existing_pos or is_waiting:
            pos_msg = f"{CROSS} You are already in the queue!"
            if existing_pos:
                pos_msg += f" Position: **{existing_pos}**"
            return await interaction.response.send_message(
                embeds=[discord.Embed(description=pos_msg, color=discord.Color.red()), ign_embed],
                ephemeral=True,
            )

        predicted = len(qm.queue) + qm.operation_queue.qsize() + 1
        success_embed = discord.Embed(
            description=f"{CHECK} You've been added to the queue! Position: **{predicted}**\n-# {EMOJI_REPLY} You are not guaranteed to be tested, especially in a long queue. {WARN}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(
            embeds=[success_embed, ign_embed],
            ephemeral=True,
        )

        qm.set_message_location(interaction.channel_id, interaction.message.id)
        is_booster = any(r.id == BOOSTER_ROLE_ID for r in interaction.user.roles)
        await qm.enqueue_join(interaction.user.id, interaction.user, interaction, is_booster)

    async def leave_queue(self, interaction: discord.Interaction):
        if await deny_if_restricted(interaction, interaction.user):
            return

        qm = self.queue_manager
        if not qm:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} Something went wrong. `[Error 2]`",
                    color=discord.Color.red()
                ),
                ephemeral=True,
            )

        if not any(e.user_id == interaction.user.id for e in qm.queue):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} You are not currently in the queue!",
                    color=discord.Color.red()
                ),
                ephemeral=True,
            )

        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"{CHECK} You've been removed from the queue.",
                color=discord.Color.green()
            ),
            ephemeral=True,
        )
        qm.set_message_location(interaction.channel_id, interaction.message.id)
        await qm.enqueue_leave(interaction.user.id, interaction.user, interaction)


class RegionSelectView(discord.ui.View):
    def __init__(self, channel, queue_manager, gamemode, bot):
        super().__init__(timeout=500)
        self.channel = channel
        self.queue_manager = queue_manager
        self.gamemode = gamemode.lower()
        self.bot = bot

    async def open_queue(self, interaction: discord.Interaction, region: str):
        item = return_item(self.gamemode)
        channel_id = item[1]
        gamemode_channel = interaction.guild.get_channel(channel_id)

        messages = [
            m async for m in gamemode_channel.history(limit=10)
            if m.author.id == interaction.client.application_id
        ]
        if not messages:
            return await interaction.response.edit_message(
                embed=discord.Embed(
                    title=f"{CROSS} No queue message found in <#{channel_id}>.",
                    color=discord.Color.red()
                ),
                view=None,
            )

        old = messages[0]
        if not self.queue_manager.is_open:
            await old.delete()
            qm = self.queue_manager
            qm.clear_active_sessions()
            if qm.should_clear_on_start():
                qm.clear()
            qm.is_open = True

            container = build_queue_container(
                gamemode=self.gamemode,
                queue=qm.queue.copy(),
                active_sessions=qm.active_sessions.copy(),
                is_open=True,
                ping_role_id=item[0],
            )
            panel = QueuePanelView(
                gamemode=self.gamemode,
                queue_manager=qm,
                bot=self.bot,
                is_open=True,
                container=container,
            )
            new_msg = await gamemode_channel.send(view=panel)
            qm.set_message_location(channel_id, new_msg.id)
            await interaction.response.edit_message(
                embed=discord.Embed(
                    description=f"{CHECK} You've opened the **{GAMEMODE_DISPLAY.get(self.gamemode, self.gamemode)}** queue for **{region}**.",
                    color=discord.Color.green()
                ),
                view=None,
            )
        else:
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title=f"{WARN} Queue already open.",
                    color=discord.Color.orange()
                ),
                view=None,
            )

    @discord.ui.button(label="Asia", style=discord.ButtonStyle.primary)
    async def _btn_asia(self, interaction, button):
        await self.open_queue(interaction, "AS")

    @discord.ui.button(label="Australia", style=discord.ButtonStyle.primary)
    async def _btn_aus(self, interaction, button):
        await self.open_queue(interaction, "AU")

    @discord.ui.button(label="North America", style=discord.ButtonStyle.primary)
    async def _btn_na(self, interaction, button):
        await self.open_queue(interaction, "NA")

    @discord.ui.button(label="Europe", style=discord.ButtonStyle.primary)
    async def _btn_eu(self, interaction, button):
        await self.open_queue(interaction, "EU")


class ConfirmActionView(discord.ui.View):
    def __init__(self, confirm_coro, timeout=500):
        super().__init__(timeout=timeout)
        self.confirm_coro = confirm_coro

    @discord.ui.button(label=f"Confirm", style=discord.ButtonStyle.red, emoji=EMOJI_EMERALD)
    async def _confirm(self, interaction, button):
        await self.confirm_coro(interaction)


def build_session_container(member_name: str, ign: str, current_rank: str, region: str, is_linked: bool, tester_ign: str = "", member_mention: str = "", tester_mention: str = "", gamemode: str = "") -> discord.ui.Container:
    attrs = {}
    attrs["header"] = discord.ui.TextDisplay(
        f"### {EMOJI_SPYGLASS} Testing Session - {member_name}"
    )
    ign_display = (
        f"[{ign}](https://tierlist.mysticraft.xyz/?player={ign})"
        if is_linked and ign not in (None, "None")
        else f"{CROSS} Not Linked"
    )
    tester_ign_display = (
        f"[{tester_ign}](https://tierlist.mysticraft.xyz/?player={tester_ign})"
        if tester_ign and tester_ign != "None"
        else f"{CROSS} Unknown"
    )
    attrs["info"] = discord.ui.TextDisplay(
        f"> {EMOJI_STEVE} **Player:** {ign_display} - {member_mention}\n"
        f"> {EMOJI_SPYGLASS} **Tester:** {tester_ign_display} - {tester_mention}\n"
        f"> {EMOJI_STATS} **Gamemode:** {GAMEMODE_DISPLAY.get(gamemode.lower(), gamemode)}\n"
        f"> {EMOJI_RANK} **Current Rank:** {current_rank}\n"
        f"> {EMOJI_MAP} **Region:** {region}\n"
        f"> {EMOJI_MC_CLOCK} **Started:** <t:{int(time.time())}:R>"
    )
    attrs["sep"] = discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small)
    attrs["hint"] = discord.ui.TextDisplay(
        f"-# {EMOJI_REPLY} Verify the player's Minecraft account matches the IGN above.\n"
        f"-# {EMOJI_REPLY} Click **Skip** if player is unresponsive and **Results** to post scores."
    )
    cls_ = type("SessionContainer", (discord.ui.Container,), attrs)
    return cls_(accent_color=0x22aef5)


def parse_thread_info(interaction: discord.Interaction):
    """Extract member_id and gamemode from the interaction's thread context."""
    match = re.compile(r"'s ticket \((\d+)\)$").search(interaction.channel.name)
    member_id = int(match.group(1)) if match else None
    gamemode = CHANNEL_TO_GAMEMODE.get(interaction.channel.parent_id)
    return member_id, gamemode


class ThreadActionsView(discord.ui.LayoutView):
    """Buttons inside the testing thread"""
    def __init__(self):
        super().__init__(timeout=None)

        skip_btn = discord.ui.Button(
            label="Skip",
            style=discord.ButtonStyle.danger,
            emoji=EMOJI_FEATHER,
            custom_id="thread_skip",
        )
        skip_btn.callback = self.skip_player

        results_btn = discord.ui.Button(
            label="Results",
            style=discord.ButtonStyle.success,
            emoji=EMOJI_EMERALD,
            custom_id="thread_results",
        )
        results_btn.callback = self.open_results_modal

        history_btn = discord.ui.Button(
            label="History",
            style=discord.ButtonStyle.blurple,
            emoji=EMOJI_BOOK,
            custom_id="thread_history",
        )
        history_btn.callback = self.show_history

        ign_refresh_btn = discord.ui.Button(
            label="Refresh IGN",
            style=discord.ButtonStyle.gray,
            emoji=EMOJI_MC_CLOCK,
            custom_id="thread_refreshign",
        )
        ign_refresh_btn.callback = self.refresh_ign

        self.add_item(discord.ui.ActionRow(skip_btn, results_btn, history_btn, ign_refresh_btn))

    async def skip_player(self, interaction: discord.Interaction):
        member_id, gamemode = parse_thread_info(interaction)
        member = interaction.guild.get_member(member_id) if member_id else None
        if member_id and not member:
            try:
                member = await interaction.guild.fetch_member(member_id)
            except:
                pass
        if not gamemode:
            return await interaction.response.send_message(
                embed=discord.Embed(description=f"{CROSS} Could not determine gamemode.", color=discord.Color.red()),
                ephemeral=True
            )
        if await deny_if_restricted(interaction, interaction.user, member):
            return
        item = return_item(gamemode)
        if interaction.guild.get_role(item[2]) not in interaction.user.roles:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{CROSS} Only testers can use this.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
        embed = discord.Embed(
            title=f"{EMOJI_GOLD_INGOT} Skip {member.name if member else 'Unknown'}?",
            description=f"{EMOJI_REPLY} This will remove both of you from the active session and the thread.",
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(
            embed=embed,
            view=ConfirmActionView(self.confirm_skip_player),
            ephemeral=True,
        )

    async def confirm_skip_player(self, interaction: discord.Interaction):
        member_id, gamemode = parse_thread_info(interaction)
        member = interaction.guild.get_member(member_id) if member_id else None
        if member_id and not member:
            try:
                member = await interaction.guild.fetch_member(member_id)
            except:
                pass
        if not member:
            return await interaction.response.edit_message(
                embed=discord.Embed(
                    title=f"{CROSS} Player not found.",
                    color=discord.Color.red()
                ),
                view=None,
            )

        qm = interaction.client.queue_manager_pool.get_manager(gamemode)
        qm.remove_active_session(member.id)

        thread = interaction.channel
        try:
            if thread and thread.type.name in ("public_thread", "private_thread"):
                await thread.remove_user(member)
                await thread.remove_user(interaction.user)
        except Exception as e:
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title=f"{CHECK} Skipped {member.mention}.",
                    description=f"{WARN} Could not remove from thread: {e}",
                    color=discord.Color.orange()
                ),
                view=None,
            )
            return

        await interaction.response.edit_message(
            embed=discord.Embed(
                description=f"{CHECK} {member.mention} has been skipped and both of you are removed from the thread.",
                color=discord.Color.green()
            ),
            view=None,
        )

    async def show_history(self, interaction: discord.Interaction):
        member_id, gamemode = parse_thread_info(interaction)
        member = interaction.guild.get_member(member_id) if member_id else None
        if member_id and not member:
            try:
                member = await interaction.guild.fetch_member(member_id)
            except:
                pass
        if not gamemode:
            return await interaction.response.send_message(
                embed=discord.Embed(description=f"{CROSS} Could not determine gamemode.", color=discord.Color.red()),
                ephemeral=True
            )
        item = return_item(gamemode)
        if interaction.guild.get_role(item[2]) not in interaction.user.roles:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{CROSS} Only testers can use this.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
        if not member:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{CROSS} No player data available.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True, thinking=True)

        bot = interaction.client
        async with bot.tlresults_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SHOW TABLES LIKE 'tlresults'")
                if not await cursor.fetchone():
                    return await interaction.followup.send(
                        embed=discord.Embed(description="No history found.", color=discord.Color.red()),
                        ephemeral=True,
                    )
                await cursor.execute(
                    "SELECT * FROM tlresults WHERE player_user_id = %s ORDER BY timestamp DESC",
                    (member.id,),
                )
                results = await cursor.fetchall()

        if not results:
            return await interaction.followup.send(
                embed=discord.Embed(
                    description=f"No test history found for {member.mention}.",
                    color=discord.Color.blue()
                ),
                ephemeral=True,
            )

        chunk_size = 5
        chunks = [results[i:i + chunk_size] for i in range(0, len(results), chunk_size)]

        embeds = []
        for i, chunk in enumerate(chunks):
            embed = discord.Embed(
                title=f"Test History for {member.display_name}",
                description=f"> **Total Tests:** {len(results)}",
                color=discord.Color.blue()
            )
            if member.avatar:
                embed.set_thumbnail(url=member.display_avatar.url)

            for row in chunk:
                r_ign = row[5]
                r_score = row[6]
                r_ts = row[7]
                r_old = row[8]
                r_new = row[9]
                r_mode = row[10]
                r_remark = row[11]
                r_tester_id = row[13]

                field_val = (
                    f"-# **Tester:** <@{r_tester_id}>\n"
                    f"-# **Date:** <t:{r_ts}:R>\n"
                    f"-# **IGN:** {r_ign}\n"
                    f"-# **Score:** {r_score}\n"
                    f"-# **Rank:** {r_old} ➔ {r_new}\n"
                )
                if r_remark:
                    field_val += f"-# **Remarks:** {r_remark}\n"

                embed.add_field(name=f"{r_mode}", value=field_val, inline=False)

            embed.set_footer(text=f"Page {i+1} of {len(chunks)} - Requested by {interaction.user.name}")
            embeds.append(embed)

        view = HistoryPaginationView(embeds, interaction.user.id)
        await interaction.followup.send(embed=embeds[0], view=view, ephemeral=True)

    async def refresh_ign(self, interaction: discord.Interaction):
        member_id, gamemode = parse_thread_info(interaction)
        member = interaction.guild.get_member(member_id) if member_id else None
        if member_id and not member:
            try:
                member = await interaction.guild.fetch_member(member_id)
            except:
                pass
        if not gamemode:
            return await interaction.response.send_message(
                embed=discord.Embed(description=f"{CROSS} Could not determine gamemode.", color=discord.Color.red()),
                ephemeral=True
            )
        item = return_item(gamemode)
        if interaction.guild.get_role(item[2]) not in interaction.user.roles:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{CROSS} Only testers can use this.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
        if not member:
            return await interaction.response.send_message(
                embed=discord.Embed(description=f"{CROSS} Player not found.", color=discord.Color.red()),
                ephemeral=True
            )

        bot = interaction.client
        ign = await fetch_ign(bot, member.id)

        current_rank = "None"
        for role in member.roles:
            if gamemode in role.name.lower() and "waitlist" not in role.name.lower():
                current_rank = role.name.split(" ")[0]
                break

        region_str = "Unknown"
        try:
            async with bot.tlresults_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "SELECT region FROM tlresults WHERE player_user_id = %s AND gamemode = %s ORDER BY timestamp DESC LIMIT 1",
                        (member.id, gamemode.upper()),
                    )
                    row = await cursor.fetchone()
                    if row:
                        region_str = row[0]
        except Exception:
            pass

        has_linked = ROLE_IDS[SERVER_IDS["tierlist"]]["linked"] in [r.id for r in member.roles]
        tester_ign = await fetch_ign(bot, interaction.user.id)

        channel = interaction.channel
        async for msg in channel.history(limit=10, oldest_first=True):
            if msg.author.id == bot.user.id and msg.components:
                first_comp = msg.components[0]
                if not hasattr(first_comp, 'children') or not first_comp.children:
                    new_container = build_session_container(
                        member_name=member.name,
                        ign=ign,
                        current_rank=current_rank,
                        region=region_str,
                        is_linked=has_linked,
                        tester_ign=tester_ign,
                        member_mention=member.mention,
                        tester_mention=interaction.user.mention,
                        gamemode=gamemode,
                    )
                    new_container_view = discord.ui.LayoutView(timeout=None)
                    new_container_view.add_item(new_container)
                    await msg.edit(view=new_container_view)
                    break

        await interaction.response.send_message(
            embed=discord.Embed(description=f"{CHECK} IGN info refreshed.", color=discord.Color.green()),
            ephemeral=True,
        )

    async def open_results_modal(self, interaction: discord.Interaction):
        member_id, gamemode = parse_thread_info(interaction)
        member = interaction.guild.get_member(member_id) if member_id else None
        if member_id and not member:
            try:
                member = await interaction.guild.fetch_member(member_id)
            except:
                pass
        if not gamemode:
            return await interaction.response.send_message(
                embed=discord.Embed(description=f"{CROSS} Could not determine gamemode.", color=discord.Color.red()),
                ephemeral=True
            )
        if await deny_if_restricted(interaction, interaction.user, member):
            return
        item = return_item(gamemode)
        if interaction.guild.get_role(item[2]) not in interaction.user.roles:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{CROSS} Only testers can use this.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

        modal = ResultsModal(
            member=member,
            gamemode=gamemode,
            tester=interaction.user,
            queue_manager=interaction.client.queue_manager_pool.get_manager(gamemode),
            bot=interaction.client,
        )
        await interaction.response.send_modal(modal)


class ResultsModal(discord.ui.Modal):
    def __init__(self, member, gamemode, tester, queue_manager, bot):
        super().__init__(title=f"Post Results")
        self.member = member
        self.gamemode = gamemode
        self.tester = tester
        self.queue_manager = queue_manager
        self.bot = bot

    region = discord.ui.TextInput(label="Region", placeholder="AS, AU, NA, EU", max_length=2, required=True)
    scores = discord.ui.TextInput(label="Scores", placeholder='3-0', max_length=50, required=True)
    new_rank = discord.ui.TextInput(label="New Rank", placeholder='HT5', max_length=10, required=True)
    remarks = discord.ui.TextInput(label="Remarks (optional)", placeholder="What they did well or can improve on...", required=False, max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        if await deny_if_restricted(interaction, interaction.user, self.member):
            return

        await interaction.response.defer()

        gamemode = self.gamemode.upper()
        member = self.member
        user = member if member else None
        if ROLE_IDS[SERVER_IDS["tierlist"]]["linked"] not in [r.id for r in user.roles]:
            return await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{CROSS} This player is not linked.",
                    color=discord.Color.red()
                ),
                ephemeral=True,
            )

        username = "Unknown"
        linked_uuid = None
        async with self.bot.tllink_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SHOW TABLES")
                db_res = await cursor.fetchone()
                link_table = db_res[0] if db_res else "mystilinking"
                await cursor.execute(
                    f"SELECT player_name, uuid FROM {link_table} WHERE discord_id = %s",
                    (str(user.id),),
                )
                db_res = await cursor.fetchone()
                if db_res:
                    username = db_res[0]
                    linked_uuid = db_res[1]
                else:
                    return await interaction.followup.send(
                        embed=discord.Embed(
                            description=f"{CROSS} Could not find linked account.",
                            color=discord.Color.red()
                        ),
                        ephemeral=True,
                    )

        region_val = self.region.value.strip().upper()
        scores_val = self.scores.value.strip()
        remarks_val = self.remarks.value.strip() or None

        rank_input = self.new_rank.value.strip().upper()
        if rank_input not in TIER_ROLE_PREFIXES:
            return await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{CROSS} Invalid rank `{rank_input}`. Must be one of: "
                + ", ".join(sorted(TIER_ROLE_PREFIXES))
                + ".", color=discord.Color.red()
                ),
                ephemeral=True,
            )

        target_role_name = f"{rank_input.lower()} {gamemode.lower()}"
        new_role = None
        for role in interaction.guild.roles:
            if role.name.lower() == target_role_name:
                new_role = role
                break
        if not new_role:
            return await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{CROSS} Could not find the correct tier role in the server.",
                    color=discord.Color.red()
                ),
                ephemeral=True,
            )

        rank_name = rank_input
        legit = False
        for role in interaction.user.roles:
            if "tester" in role.name.lower() and gamemode.lower() in role.name.lower():
                legit = True
                break
        if not legit:
            return await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{CROSS} You cannot post results. You are not a {gamemode} tester.",
                    color=discord.Color.red()
                ),
                ephemeral=True,
            )

        if "tester" in new_role.name.lower():
            return await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{WARN} Double check you selected the correct role!",
                    color=discord.Color.yellow()
                ),
                ephemeral=True,
            )

        high_tier_ranks = ["HT3", "LT2", "HT2", "LT1", "HT1"]
        if rank_name in high_tier_ranks:
            return await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{CROSS} High tier roles require `/ht results` instead.",
                    color=discord.Color.red()
                ),
                ephemeral=True,
            )

        if ROLE_IDS[SERVER_IDS["tierlist"]]["linked"] not in [r.id for r in interaction.user.roles]:
            return await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{CROSS} You must also have your account linked to post results.",
                    color=discord.Color.red()
                ),
                ephemeral=True,
            )

        if user.id == interaction.user.id and interaction.user.id not in AUTHORIZED_USERS:
            return await interaction.followup.send(
                embed=discord.Embed(
                    description=f"{CROSS} You cannot test yourself!",
                    color=discord.Color.red()
                ),
                ephemeral=True,
            )

        previous_rank = "N/A"
        remove_role = None
        for role in user.roles:
            try:
                if len(role.name.split(" ")) > 1 and role.name.split(" ")[1].lower() == gamemode.lower():
                    remove_role = role
                    break
            except Exception:
                continue

        if remove_role:
            previous_rank = remove_role.name.split(" ")[0]
            await user.remove_roles(remove_role)

        await user.add_roles(new_role)

        ref_cd = db.reference("/Waitlist Cooldown")
        ticketcooldown = ref_cd.get()
        if ticketcooldown:
            for key, value in ticketcooldown.items():
                if value.get("User ID") == user.id and value.get("Gamemode") == gamemode:
                    ref_cd.child(key).delete()
                    break

        embed = discord.Embed(title=f"{username}'s Results :trophy:", color=0x22aef5)
        embed.add_field(name="Tester", value=interaction.user.mention, inline=True)
        embed.add_field(name="Region", value=region_val, inline=True)
        embed.add_field(name="IGN", value=f"[{username}](https://tierlist.mysticraft.xyz/?player={username})", inline=True)
        embed.add_field(name="Gamemode", value=gamemode, inline=True)
        embed.add_field(name="Previous Rank", value=previous_rank, inline=True)
        embed.add_field(name="New Rank", value=rank_name, inline=True)
        embed.add_field(name="Scores", value=scores_val, inline=True)
        if remarks_val:
            embed.add_field(name="Remarks", value=remarks_val, inline=True)
        embed.set_thumbnail(url=f"https://render.crafty.gg/3d/bust/{username}")

        results_channel = interaction.guild.get_channel(1304859270885412975)
        results_msg = await results_channel.send(content=user.mention, embed=embed)
        await interaction.followup.send(
            embeds=[discord.Embed(
                description=f"{CHECK} Results posted successfully in {results_channel.mention} [here]({results_msg.jump_url}).",
                color=discord.Color.green()
            ), embed],
            view=discord.ui.View().add_item(discord.ui.Button(label="Jump to Results", url=results_msg.jump_url, style=discord.ButtonStyle.link))
        )

        try:
            await interaction.channel.remove_user(user)
            await interaction.channel.remove_user(interaction.user)
        except Exception:
            pass

        ref_cd.push().set({
            "User ID": user.id,
            "Last Tested": int(interaction.created_at.timestamp()),
            "Gamemode": gamemode,
        })

        async with self.bot.tlresults_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """INSERT INTO tlresults
                    (player_discord_username, player_user_id, uuid, is_linked, region, in_game_username, score, timestamp, old_rank, new_rank, gamemode, remarks, tester_discord_username, tester_user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (user.name, user.id, linked_uuid, True, region_val, username, scores_val,
                     int(interaction.created_at.timestamp()), previous_rank, rank_name, gamemode,
                     remarks_val, interaction.user.name, interaction.user.id),
                )
                await conn.commit()

        ref_stats = db.reference("/Tierlist Tester Stats")
        tester_data = ref_stats.child(str(interaction.user.id)).get() or {}
        old_rep = tester_data.get("count", 0) + 2 * tester_data.get("high_count", 0)
        old_tier = get_tier_index(old_rep)
        timestamps = tester_data.get("timestamps", [])
        timestamps.append(int(interaction.created_at.timestamp()))
        ref_stats.child(str(interaction.user.id)).update({"count": len(timestamps), "timestamps": timestamps,})

        new_rep = len(timestamps) + 2 * tester_data.get("high_count", 0)
        new_tier = get_tier_index(new_rep)
        if new_tier > old_tier:
            n_role_id = TIER_ROLES.get(new_tier)
            o_role_id = TIER_ROLES.get(old_tier)
            if o_role_id:
                await interaction.user.remove_roles(interaction.guild.get_role(o_role_id))
            if n_role_id:
                await interaction.user.add_roles(interaction.guild.get_role(n_role_id))
            log_ch = interaction.guild.get_channel(1467403596780929055)
            rank_embed = discord.Embed(
                description=f"{interaction.user.mention} reached **{TIER_THRESHOLDS[new_tier]}** reps and ranked up to `{TIER_NAMES[new_tier]}`!",
                color=discord.Color.from_rgb(*tier_colors[new_tier]),
            )
            await log_ch.send(content=interaction.user.mention, embed=rank_embed)

        item = return_item(gamemode.lower())
        await user.remove_roles(interaction.guild.get_role(item[0]))
        try:
            self.queue_manager.remove_active_session(user.id)
        except Exception as e:
            print(f"Queue Sync Error: {e}")


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
        self.queue_manager_pool = bot.queue_manager_pool
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
        if await deny_if_restricted(interaction, interaction.user, user):
            return
        await interaction.response.defer()
        target_user = user
        duration_val = duration.value if duration else "alltime"
        
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
        if await deny_if_restricted(interaction, interaction.user, user):
            return
        await interaction.response.defer()

        allowed_roles = [1304851740226748556, 1460312013535318077, 1304848576190484553]
        has_permission = any(role.id in allowed_roles for role in interaction.user.roles)
        
        if not has_permission:
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> You do not have permission to migrate tiers.",
                ephemeral=True
            )

        if ROLE_IDS[SERVER_IDS["tierlist"]]["linked"] not in [role.id for role in user.roles]:
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> This player is not linked. They must link their account to receive results.",
                ephemeral=True
            )

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

        ref = db.reference("/Waitlist Cooldown")
        ref.push().set({
            "User ID": user.id,
            "Last Tested": int(interaction.created_at.timestamp()),
            "Gamemode": gamemode,
        })
        
        if new_rank in ["HT3", "LT2", "HT2", "LT1", "HT1"]:
            results_channel = interaction.guild.get_channel(1338411690902945832)  # High Results
        else:
            results_channel = interaction.guild.get_channel(1304859270885412975)  # Regular Results
        
        results = await results_channel.send(user.mention, embed=embed)
            
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
        if await deny_if_restricted(interaction, interaction.user):
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
        self.queue_manager_pool = bot.queue_manager_pool

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return

        if message.content == "mc!queue" and not message.author.bot:
            if is_restricted(message.author):
                return

            gamemode = CHANNEL_TO_GAMEMODE.get(message.channel.id)
            if not gamemode:
                await message.delete()
                return

            qm = self.queue_manager_pool.get_manager(gamemode)
            item = return_item(gamemode)
            container = build_queue_container(gamemode=gamemode, queue=qm.queue.copy(), active_sessions=qm.active_sessions.copy(), is_open=False, ping_role_id=item[0]) 
            panel = QueuePanelView(gamemode=gamemode, queue_manager=qm, bot=self.client, is_open=False, container=container)
            new_msg = await message.channel.send(view=panel)
            qm.set_message_location(message.channel.id, new_msg.id)
            await message.delete()
        
        if message.channel.id == LINKED_LOG_CHANNEL_ID and message.author.id == 1459850286087802952:
            if "Alt Link Attempt Detected" in message.content:
                return
            
            match_ign = re.search(r"Minecraft Username:\s*(.+)", message.content)
            match_discord = re.search(r"Discord Username:\s*<@!?(\d+)>", message.content)
            
            if match_ign and match_discord:
                ign = match_ign.group(1).strip()
                discord_id = int(match_discord.group(1))

                tierlist_guild = self.client.get_guild(SERVER_IDS["tierlist"])
                main_guild = self.client.get_guild(SERVER_IDS["main"])
                tierlist_member = tierlist_guild.get_member(discord_id)
                main_member = main_guild.get_member(discord_id)
                if tierlist_member is not None:
                    await tierlist_member.add_roles(tierlist_guild.get_role(ROLE_IDS[SERVER_IDS["tierlist"]]["linked"]))
                if main_member is not None:
                    await main_member.add_roles(main_guild.get_role(ROLE_IDS[SERVER_IDS["main"]]["linked"]))

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
                                                target_roles, missing_roles, removed_old_roles = await sync_tier_roles(
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
        linked_role_id = ROLE_IDS[SERVER_IDS["tierlist"]]["linked"]
        linked_role = before.guild.get_role(linked_role_id)
        if linked_role and linked_role in before.roles and linked_role not in after.roles:
            embed = discord.Embed(
                description=f"{after.mention} has un<@&{linked_role_id}> their account.",
                color=discord.Color.red()
            )
            channel = self.client.get_channel(LINKED_LOG_CHANNEL_ID)
            await channel.send(embed=embed)
        elif linked_role and linked_role not in before.roles and linked_role in after.roles:
            embed = discord.Embed(
                description=f"{after.mention} has <@&{linked_role_id}> their account.",
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
        if await deny_if_restricted(interaction, interaction.user):
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
        if await deny_if_restricted(interaction, interaction.user):
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
        if await deny_if_restricted(interaction, interaction.user, player, tester):
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
                await sync_member(self.bot, interaction.guild, player.id)
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
                    await sync_tier_roles(interaction.guild, player, in_game_username, old_member=old_member)
                else:
                    await sync_member(self.bot, interaction.guild, player.id)
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
        if await deny_if_restricted(interaction, interaction.user):
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
                    if any(is_restricted(interaction.guild.get_member(member_id)) for member_id in affected_member_ids):
                        return await interaction.response.send_message("<:cross1:1339153202859474956> That entry belongs to a restricted user and cannot be modified here.", ephemeral=True)
                    query = "DELETE FROM tlresults WHERE id = %s"
                else:
                    await cursor.execute("SHOW TABLES")
                    result = await cursor.fetchone()
                    table_name = result[0] if result else "linking"
                    await cursor.execute(f"SELECT discord_id FROM {table_name} WHERE uuid = %s", (entry_id_or_uuid,))
                    rows = await cursor.fetchall()
                    affected_member_ids = [int(row[0]) for row in rows if row and row[0] is not None]
                    if any(is_restricted(interaction.guild.get_member(member_id)) for member_id in affected_member_ids):
                        return await interaction.response.send_message("<:cross1:1339153202859474956> That entry belongs to a restricted user and cannot be modified here.", ephemeral=True)
                    query = f"DELETE FROM {table_name} WHERE uuid = %s"

                await cursor.execute(query, (entry_id_or_uuid,))
                deleted_count = cursor.rowcount
                await conn.commit()

        if deleted_count > 0:
            if table.value == "results":
                for member_id in sorted(set(affected_member_ids)):
                    try:
                        await sync_member(self.bot, interaction.guild, member_id)
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
                            await remove_tier_roles(member)
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
        if await deny_if_restricted(interaction, interaction.user):
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
                    await restrict(interaction.guild, member)
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
        if await deny_if_restricted(interaction, interaction.user):
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
                if any(is_restricted(interaction.guild.get_member(member_id)) for member_id in affected_member_ids):
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
                    await sync_member(self.bot, interaction.guild, member_id)
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
        if await deny_if_restricted(interaction, interaction.user, user, old_account):
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
            ign = await fetch_ign(self.bot, user.id)

        if not ign:
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> No IGN was provided and no linked IGN could be found for that user.",
                ephemeral=True,
            )

        try:
            target_roles, missing_roles, removed_old_roles = await sync_tier_roles(
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
    bot.queue_manager_pool = QueueManagerPool(bot)

    for gm in ["npot", "dpot", "smp", "sword", "crystal", "axe", "mace", "uhc"]:
        qm = bot.queue_manager_pool.get_manager(gm)
        container = build_queue_container(gm, [], {}, False)
        bot.add_view(QueuePanelView(gm, qm, bot, False, container))

    bot.add_view(ThreadActionsView())

    await bot.add_cog(Waitlist(bot))
    await bot.add_cog(WaitlistCmd(bot))
    await bot.add_cog(DatabaseCmd(bot))