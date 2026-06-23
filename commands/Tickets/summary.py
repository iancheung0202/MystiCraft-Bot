import discord
import time
import asyncio
import re

from discord import app_commands
from discord.ext import commands
from firebase_admin import db
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from commands.Tickets.tickets import check_for_manager
from commands.Utility.loa import HistoryPageView
from constants import CATEGORY_IDS, CATEGORY_EMOJIS_MAP, SERVER_IDS, ROLE_IDS

categories     = CATEGORY_IDS.get(SERVER_IDS["support"], {})
category_ids   = {cat_id: cat_name.title() for cat_name, cat_id in categories.items()}
ORDERED_STAFF_KEYS   = ["owner", "manager", "senior_admin", "admin", "developer", "senior_mod", "mod", "helper"]
CORE_STAFF_ROLE_IDS   = set(ROLE_IDS[SERVER_IDS["support"]]["roles"][k] for k in ORDERED_STAFF_KEYS)

TIERLIST_TESTER_ROLE_ID  = 1305918277549162586
TESTER_WEEKLY_REQUIREMENT = 16

PUNISHMENT_LOG_CHANNEL_ID = 1155910232204128256
APPEAL_LOG_CHANNEL_ID     = 1286031597845614625
SM_LOGS_CHANNEL_ID        = 1353556989497704460

COLOR_SUCCESS = 0x2ecc71
COLOR_ERROR   = 0xe74c3c
COLOR_INFO    = 0x1ec7f1
COLOR_WARNING = 0xf1c40f

EMOJI_EMERALD     = "<:emerald:1518031176730804244>"
EMOJI_REDSTONE    = "<:redstone_dust:1518031324588539986>"
EMOJI_GOLD_INGOT  = "<:gold_ingot:1518031441248653433>"
EMOJI_STEVE       = "<:steve:1518031537814110382>"
EMOJI_NETHER_STAR = "<:nether_star:1518033504120606771>"
EMOJI_COMPASS     = "<a:compass:1518032475803226214>"
EMOJI_ENDER_PEARL = "<:ender_pearl:1518033866995269763>"
EMOJI_MC_CLOCK    = "<:mc_clock:1518027805361967104>"
EMOJI_MAP         = "<:map:1518038367521210499>"
EMOJI_BOOK        = "<:book:1518051136488214549>"
EMOJI_SCROLL      = "<:parchment:1518454271719510297>"
EMOJI_FEATHER     = "<:feather:1518454349053952150>"
EMOJI_BARRIER     = "<:barrier:1518454369887195228>"
EMOJI_SPYGLASS    = "<:spyglass:1518454328480891083>"
EMOJI_HOURGLASS   = "<:hourglass:1518454206162538546>"

EMOJI_FAST_BACKWARD = "<:fastbackward:1351972112696479824>"
EMOJI_BACK_ARROW    = "<:backarrow:1351972111010369618>"
EMOJI_RIGHT_ARROW   = "<:rightarrow:1351972116819480616>"
EMOJI_FAST_FORWARD  = "<:fastforward:1351972114433048719>"

PER_PAGE = 10  # entries per leaderboard page

def embed_success(title: str, description: str = None) -> discord.Embed:
    return discord.Embed(title=f"{EMOJI_EMERALD} {title}", description=description, color=COLOR_SUCCESS)

def embed_error(title: str, description: str = None) -> discord.Embed:
    return discord.Embed(title=f"{EMOJI_REDSTONE} {title}", description=description, color=COLOR_ERROR)

def embed_info(title: str, description: str = None) -> discord.Embed:
    return discord.Embed(title=f"{EMOJI_MAP} {title}", description=description, color=COLOR_INFO)

def embed_warning(title: str, description: str = None) -> discord.Embed:
    return discord.Embed(title=f"{EMOJI_GOLD_INGOT} {title}", description=description, color=COLOR_WARNING)

def get_week_start_timstamp() -> int:
    """Return the Unix timestamp for the most recent past Sunday at 00:00:00 local time."""
    now = datetime.now()
    days_since_sunday = (now.weekday() + 1) % 7
    last_sunday = now - timedelta(days=days_since_sunday)
    return int(last_sunday.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())

def ranges(label: str) -> tuple[int | None, int | None]:
    """Convert a preset range label to (start_ts, end_ts). None = unbounded."""
    now = int(time.time())
    week_start = get_week_start_timstamp()
    return {
        "7d":        (now - 7   * 86400, now),
        "30d":       (now - 30  * 86400, now),
        "90d":       (now - 90  * 86400, now),
        "180d":      (now - 180 * 86400, now),
        "365d":      (now - 365 * 86400, now),
        "this_week": (week_start, now),
        "all":       (None, None),
    }.get(label, (None, None))

RANGE_LABELS = {
    "7d":        "Last 7 Days",
    "30d":       "Last 30 Days",
    "90d":       "Last 90 Days",
    "180d":      "Last 180 Days",
    "365d":      "Last 365 Days",
    "this_week": "This Week",
    "all":       "All Time",
}


async def get_all_staff_ticket_stats(guild: discord.Guild = None) -> list[dict]:
    """Return per-user ticket counts filtered to current core staff."""
    ref = db.reference("/Staff Claim")
    claim_database = ref.get() or {}
    now = int(time.time())

    core_staff_ids: set[int] = set()
    if guild is not None:
        for role_id in CORE_STAFF_ROLE_IDS:
            role = guild.get_role(role_id)
            if role:
                for member in role.members:
                    core_staff_ids.add(member.id)

    week_start_ts = get_week_start_timstamp()
    result = []
    for val in claim_database.values():
        user_id = val["User ID"]
        if guild is not None and user_id not in core_staff_ids:
            continue
        ts_list = val.get("List", [])
        result.append({
            "user_id":    user_id,
            "last_7d":    sum(1 for ts in ts_list if ts > now - 604800),
            "last_30d":   sum(1 for ts in ts_list if ts > now - 2592000),
            "last_90d":   sum(1 for ts in ts_list if ts > now - 7776000),
            "last_180d":  sum(1 for ts in ts_list if ts > now - 15552000),
            "last_365d":  sum(1 for ts in ts_list if ts > now - 31536000),
            "this_week":  sum(1 for ts in ts_list if ts >= week_start_ts),
            "total":      len(ts_list),
        })
    return result


async def get_all_tester_stats(guild_tierlist: discord.Guild = None) -> list[dict]:
    """Return per-user tester stats filtered to members with the tester role."""
    ref = db.reference("/Tierlist Tester Stats")
    claim_database = ref.get() or {}
    now = int(time.time())
    week_start_ts = get_week_start_timstamp()

    tester_ids: set[int] = set()
    if guild_tierlist is not None:
        tester_role = guild_tierlist.get_role(TIERLIST_TESTER_ROLE_ID)
        if tester_role:
            for member in tester_role.members:
                tester_ids.add(member.id)

    result = []
    for user_id_str, val in claim_database.items():
        user_id = int(user_id_str)
        if guild_tierlist is not None and user_id not in tester_ids:
            continue
        ts        = val.get("timestamps", [])
        high_ts   = val.get("high_timestamps", [])
        result.append({
            "user_id":          user_id,
            "last_7d":          sum(1 for t in ts if t > now - 604800),
            "last_30d":         sum(1 for t in ts if t > now - 2592000),
            "last_90d":         sum(1 for t in ts if t > now - 7776000),
            "last_180d":        sum(1 for t in ts if t > now - 15552000),
            "last_365d":        sum(1 for t in ts if t > now - 31536000),
            "this_week":        sum(1 for t in ts if t >= week_start_ts),
            "total":            val.get("count", len(ts)),
            "high_last_7d":     sum(1 for t in high_ts if t > now - 604800),
            "high_last_30d":    sum(1 for t in high_ts if t > now - 2592000),
            "high_last_90d":    sum(1 for t in high_ts if t > now - 7776000),
            "high_last_180d":   sum(1 for t in high_ts if t > now - 15552000),
            "high_last_365d":   sum(1 for t in high_ts if t > now - 31536000),
            "high_this_week":   sum(1 for t in high_ts if t >= week_start_ts),
            "high_total":       val.get("high_count", len(high_ts)),
        })
    return result


async def fetch_punishment_counts(channel: discord.TextChannel, since: datetime) -> dict[int, dict]:
    counts: dict[int, dict] = defaultdict(lambda: {"total": 0, "bans": 0, "mutes": 0, "warns": 0})
    try:
        async for msg in channel.history(limit=None, after=since, oldest_first=False):
            if msg.author.bot or "reason" not in msg.content.lower():
                continue
            low = msg.content.lower()
            uid = msg.author.id
            counts[uid]["total"] += 1
            if "ban"  in low: counts[uid]["bans"]  += 1
            if "mute" in low: counts[uid]["mutes"] += 1
            if "warn" in low: counts[uid]["warns"] += 1
    except (discord.Forbidden, discord.HTTPException):
        pass
    return counts


async def fetch_punishment_counts_all(channel: discord.TextChannel) -> dict[int, dict]:
    """Fetch punishment counts for all time (no after= filter)."""
    counts: dict[int, dict] = defaultdict(lambda: {"total": 0, "bans": 0, "mutes": 0, "warns": 0})
    try:
        async for msg in channel.history(limit=None, oldest_first=True):
            if msg.author.bot or "reason" not in msg.content.lower():
                continue
            low = msg.content.lower()
            uid = msg.author.id
            counts[uid]["total"] += 1
            if "ban"  in low: counts[uid]["bans"]  += 1
            if "mute" in low: counts[uid]["mutes"] += 1
            if "warn" in low: counts[uid]["warns"] += 1
    except (discord.Forbidden, discord.HTTPException):
        pass
    return counts


async def fetch_appeal_counts(channel: discord.TextChannel, since: datetime) -> dict[int, int]:
    counts: dict[int, int] = defaultdict(int)
    try:
        async for msg in channel.history(limit=None, after=since, oldest_first=True):
            if not msg.author.bot or not msg.embeds:
                continue
            embed = msg.embeds[0]
            if embed.title not in ("Appeal Accepted", "Appeal Rejected"):
                continue
            try:
                staff_id = int(embed.description.split("<@")[1].split(">")[0])
                counts[staff_id] += 1
            except Exception:
                continue
    except (discord.Forbidden, discord.HTTPException):
        pass
    return counts


async def fetch_appeal_counts_all(channel: discord.TextChannel) -> dict[int, int]:
    """Fetch appeal counts for all time (no after= filter)."""
    counts: dict[int, int] = defaultdict(int)
    try:
        async for msg in channel.history(limit=None, oldest_first=True):
            if not msg.author.bot or not msg.embeds:
                continue
            embed = msg.embeds[0]
            if embed.title not in ("Appeal Accepted", "Appeal Rejected"):
                continue
            try:
                staff_id = int(embed.description.split("<@")[1].split(">")[0])
                counts[staff_id] += 1
            except Exception:
                continue
    except (discord.Forbidden, discord.HTTPException):
        pass
    return counts


TICKET_SORT_LABELS = {
    "last_7d":    "Last 7 Days",
    "last_30d":   "Last 30 Days",
    "last_90d":   "Last 90 Days",
    "last_180d":  "Last 180 Days",
    "last_365d":  "Last 365 Days",
    "this_week":  "This Week",
    "total":      "All Time",
}

TESTER_SORT_LABELS = {
    "last_7d":   "Last 7 Days",
    "last_30d":  "Last 30 Days",
    "last_90d":  "Last 90 Days",
    "last_180d": "Last 180 Days",
    "last_365d": "Last 365 Days",
    "this_week": "This Week",
    "total":     "All Time",
}

TESTER_HIGH_KEY = {
    "last_7d":   "high_last_7d",
    "last_30d":  "high_last_30d",
    "last_90d":  "high_last_90d",
    "last_180d": "high_last_180d",
    "last_365d": "high_last_365d",
    "this_week": "high_this_week",
    "total":     "high_total",
}


def build_ticket_leaderboard_pages(stats: list[dict], sort_key: str) -> list[discord.Embed]:
    """Build paginated ticket leaderboard embeds (MC style)."""
    if not stats:
        return [embed_info("No Data", "No ticket data is available for this period.")]

    label  = TICKET_SORT_LABELS.get(sort_key, sort_key)
    sorted_stats = sorted(stats, key=lambda x: x.get(sort_key, 0), reverse=True)
    total_pages  = max(1, (len(sorted_stats) + PER_PAGE - 1) // PER_PAGE)
    pages = []

    for page_idx, page_start in enumerate(range(0, len(sorted_stats), PER_PAGE)):
        chunk = sorted_stats[page_start:page_start + PER_PAGE]

        # Build header line
        header = (
            f"-# {EMOJI_SPYGLASS} Sorted by **{label}**  •  {len(sorted_stats)} staff listed  •  high → low\n"
        )
        # Build entry lines
        lines = []
        for rank, entry in enumerate(chunk, start=page_start + 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"`#{rank}`")
            val   = entry.get(sort_key, 0)
            lines.append(
                f"{medal} <@{entry['user_id']}>\n"
                f"-# <:reply:1036792837821435976> {EMOJI_MC_CLOCK} **{label}:** `{val}` tickets"
            )

        embed = discord.Embed(
            title=f"{EMOJI_SCROLL} Staff Ticket Leaderboard",
            description=header + "\n" + "\n\n".join(lines),
            color=COLOR_INFO,
        )
        embed.set_footer(text=f"Page {page_idx + 1} of {total_pages}  •  Records sorted {label}")
        pages.append(embed)

    return pages


def build_tester_leaderboard_pages(stats: list[dict], sort_key: str) -> list[discord.Embed]:
    """Build paginated tester leaderboard embeds (MC style)."""
    if not stats:
        return [embed_info("No Data", "No tester data is available for this period.")]

    label    = TESTER_SORT_LABELS.get(sort_key, sort_key)
    high_key = TESTER_HIGH_KEY.get(sort_key, "high_total")
    sorted_stats = sorted(stats, key=lambda x: x.get(sort_key, 0), reverse=True)
    total_pages  = max(1, (len(sorted_stats) + PER_PAGE - 1) // PER_PAGE)
    pages = []

    for page_idx, page_start in enumerate(range(0, len(sorted_stats), PER_PAGE)):
        chunk = sorted_stats[page_start:page_start + PER_PAGE]

        header = (
            f"-# {EMOJI_SPYGLASS} Sorted by **{label}**  •  {len(sorted_stats)} testers listed  •  high → low\n"
        )
        lines = []
        for rank, entry in enumerate(chunk, start=page_start + 1):
            medal    = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"`#{rank}`")
            val      = entry.get(sort_key, 0)
            high_val = entry.get(high_key, 0)
            lines.append(
                f"{medal} <@{entry['user_id']}>\n"
                f"-# <:reply:1036792837821435976> {EMOJI_MC_CLOCK} **{label}:** `{val}` tests  •  `{high_val}` high tests"
            )

        embed = discord.Embed(
            title=f"{EMOJI_NETHER_STAR} Tester Leaderboard",
            description=header + "\n" + "\n\n".join(lines),
            color=COLOR_INFO,
        )
        embed.set_footer(text=f"Page {page_idx + 1} of {total_pages}  •  Records sorted {label}")
        pages.append(embed)

    return pages


def build_tester_checkup_pages(stats: list[dict], week_start_ts: int) -> list[discord.Embed]:
    """Build paginated tester weekly checkup embeds (MC style)."""
    if not stats:
        return [embed_info("No Data", "No tester data available.")]

    met     = sorted([(e["user_id"], e.get("this_week", 0), e.get("high_this_week", 0)) for e in stats if e.get("this_week", 0) >= TESTER_WEEKLY_REQUIREMENT], key=lambda x: x[1], reverse=True)
    not_met = sorted([(e["user_id"], e.get("this_week", 0), e.get("high_this_week", 0)) for e in stats if e.get("this_week", 0) < TESTER_WEEKLY_REQUIREMENT],  key=lambda x: x[1], reverse=True)

    per_page = 15
    pages    = []

    summary_line = (
        f"{EMOJI_EMERALD} `{len(met)}` met  •  "
        f"{EMOJI_REDSTONE} `{len(not_met)}` not met  •  "
        f"{EMOJI_STEVE} `{len(stats)}` testers total"
    )

    def _make_base() -> discord.Embed:
        return discord.Embed(
            title=f"{EMOJI_BOOK} Tester Weekly Checkup",
            description=(
                f"{EMOJI_MC_CLOCK} **Week starting:** <t:{week_start_ts}:D>\n"
                f"{EMOJI_HOURGLASS} **Requirement:** `{TESTER_WEEKLY_REQUIREMENT}` tests\n"
                f"{summary_line}\n"
            ),
            color=COLOR_WARNING,
        )

    not_met_lines = [f"{EMOJI_REDSTONE} <@{uid}> — `{n}` tests  •  `{h}` high" for uid, n, h in not_met]
    met_lines     = [f"{EMOJI_EMERALD} <@{uid}> — `{n}` tests  •  `{h}` high" for uid, n, h in met]
    sections      = [("Not Met", not_met_lines), ("Met Requirement", met_lines)]

    current = _make_base()
    current_count = 0

    for section_title, lines in sections:
        if not lines:
            current.add_field(name=f"{section_title}", value=f"-# No testers in this group.", inline=False)
            continue

        chunk = []
        raw_title = section_title
        for line in lines:
            chunk.append(line)
            current_count += 1
            if current_count >= per_page:
                current.add_field(name=raw_title, value="\n".join(chunk), inline=False)
                pages.append(current)
                current = _make_base()
                chunk   = []
                current_count = 0
                raw_title = f"{section_title} (cont.)"
        if chunk:
            current.add_field(name=raw_title, value="\n".join(chunk), inline=False)

    if current.fields:
        pages.append(current)
    elif not pages:
        pages.append(current)

    total = len(pages)
    for i, p in enumerate(pages):
        p.set_footer(text=f"Page {i + 1} of {total}  •  This Week Checkup")
    return pages


def build_punishments_pages(sorted_data: list[tuple], label: str) -> list[discord.Embed]:
    """Build paginated punishment leaderboard embeds (MC style)."""
    if not sorted_data:
        return [embed_info("No Data", f"No punishments found for the selected period.")]

    total_pages = max(1, (len(sorted_data) + PER_PAGE - 1) // PER_PAGE)
    pages       = []

    for page_idx, page_start in enumerate(range(0, len(sorted_data), PER_PAGE)):
        chunk = sorted_data[page_start:page_start + PER_PAGE]

        header = (
            f"-# {EMOJI_SPYGLASS} Sorted by total  •  {len(sorted_data)} staff listed  •  high → low\n"
        )
        lines = []
        for rank, (user, data) in enumerate(chunk, start=page_start + 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"`#{rank}`")
            lines.append(
                f"{medal} {user.mention if hasattr(user, 'mention') else f'<@{user}>'}\n"
                f"-# <:reply:1036792837821435976> {EMOJI_BARRIER} `{data['total']}` total  •  "
                f"{EMOJI_REDSTONE} `{data['bans']}` bans  •  "
                f"{EMOJI_GOLD_INGOT} `{data['mutes']}` mutes  •  "
                f"{EMOJI_FEATHER} `{data['warns']}` warns"
            )

        embed = discord.Embed(
            title=f"{EMOJI_BARRIER} Punishment Leaderboard",
            description=header + "\n" + "\n\n".join(lines),
            color=COLOR_ERROR,
        )
        embed.set_footer(text=f"Page {page_idx + 1} of {total_pages}  •  {label}")
        pages.append(embed)

    return pages


def build_appeals_pages(sorted_data: list[tuple], label: str) -> list[discord.Embed]:
    """Build paginated appeal leaderboard embeds (MC style)."""
    if not sorted_data:
        return [embed_info("No Data", f"No appeal actions found for the selected period.")]

    total_pages = max(1, (len(sorted_data) + PER_PAGE - 1) // PER_PAGE)
    pages       = []

    for page_idx, page_start in enumerate(range(0, len(sorted_data), PER_PAGE)):
        chunk = sorted_data[page_start:page_start + PER_PAGE]

        header = (
            f"-# {EMOJI_SPYGLASS} Sorted by actions  •  {len(sorted_data)} staff listed  •  high → low\n"
        )
        lines = []
        for rank, (mention, count) in enumerate(chunk, start=page_start + 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"`#{rank}`")
            lines.append(
                f"{medal} {mention}\n"
                f"-# <:reply:1036792837821435976> {EMOJI_ENDER_PEARL} `{count}` appeal action{'s' if count != 1 else ''}"
            )

        embed = discord.Embed(
            title=f"{EMOJI_ENDER_PEARL} Appeal Actions Leaderboard",
            description=header + "\n" + "\n\n".join(lines),
            color=COLOR_WARNING,
        )
        embed.set_footer(text=f"Page {page_idx + 1} of {total_pages}  •  {label}")
        pages.append(embed)

    return pages


class LoadingView(discord.ui.View):
    """Temporary view shown while data is loading."""
    def __init__(self):
        super().__init__(timeout=None)
        btn = discord.ui.Button(label="Loading...", style=discord.ButtonStyle.secondary, disabled=True, emoji=EMOJI_HOURGLASS)
        self.add_item(btn)


class TicketRangeView(discord.ui.View):
    """Time-range picker for the ticket leaderboard."""

    def __init__(self, stats: list[dict]):
        super().__init__(timeout=120)
        self.stats = stats

    async def update_embed(self, interaction: discord.Interaction, sort_key: str):
        await interaction.response.edit_message(view=LoadingView())
        pages = build_ticket_leaderboard_pages(self.stats, sort_key)
        await interaction.edit_original_response(embed=pages[0], view=HistoryPageView(pages))

    @discord.ui.button(label="Last 7 Days",   style=discord.ButtonStyle.secondary, emoji=EMOJI_MC_CLOCK)
    async def last_7(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "last_7d")

    @discord.ui.button(label="Last 30 Days",  style=discord.ButtonStyle.secondary, emoji=EMOJI_COMPASS)
    async def last_30(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "last_30d")

    @discord.ui.button(label="Last 90 Days",  style=discord.ButtonStyle.secondary, emoji=EMOJI_MAP)
    async def last_90(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "last_90d")

    @discord.ui.button(label="Last 180 Days", style=discord.ButtonStyle.secondary, emoji=EMOJI_HOURGLASS)
    async def last_180(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "last_180d")

    @discord.ui.button(label="Last 365 Days", style=discord.ButtonStyle.secondary, emoji=EMOJI_ENDER_PEARL)
    async def last_365(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "last_365d")

    @discord.ui.button(label="All Time",      style=discord.ButtonStyle.secondary, emoji=EMOJI_NETHER_STAR)
    async def all_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "total")

    @discord.ui.button(label="This Week",     style=discord.ButtonStyle.primary,   emoji=EMOJI_BOOK)
    async def this_week(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "this_week")


class TesterRangeView(discord.ui.View):
    """Time-range picker for the tester leaderboard."""

    def __init__(self, stats: list[dict]):
        super().__init__(timeout=120)
        self.stats = stats

    async def update_embed(self, interaction: discord.Interaction, sort_key: str):
        await interaction.response.edit_message(view=LoadingView())
        if sort_key == "this_week":
            week_start_ts = get_week_start_timstamp()
            pages = build_tester_checkup_pages(self.stats, week_start_ts)
        else:
            pages = build_tester_leaderboard_pages(self.stats, sort_key)
        await interaction.edit_original_response(embed=pages[0], view=HistoryPageView(pages))

    @discord.ui.button(label="Last 7 Days",        style=discord.ButtonStyle.secondary, emoji=EMOJI_MC_CLOCK)
    async def last_7(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "last_7d")

    @discord.ui.button(label="Last 30 Days",       style=discord.ButtonStyle.secondary, emoji=EMOJI_COMPASS)
    async def last_30(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "last_30d")

    @discord.ui.button(label="Last 90 Days",       style=discord.ButtonStyle.secondary, emoji=EMOJI_MAP)
    async def last_90(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "last_90d")

    @discord.ui.button(label="Last 180 Days",      style=discord.ButtonStyle.secondary, emoji=EMOJI_HOURGLASS)
    async def last_180(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "last_180d")

    @discord.ui.button(label="Last 365 Days",      style=discord.ButtonStyle.secondary, emoji=EMOJI_ENDER_PEARL)
    async def last_365(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "last_365d")

    @discord.ui.button(label="All Time",           style=discord.ButtonStyle.secondary, emoji=EMOJI_NETHER_STAR)
    async def all_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "total")

    @discord.ui.button(label="This Week (Checkup)", style=discord.ButtonStyle.primary,  emoji=EMOJI_BOOK)
    async def this_week(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "this_week")


class PunishmentRangeView(discord.ui.View):
    """Time-range picker for the punishment leaderboard."""

    def __init__(self, channel: discord.TextChannel, guild: discord.Guild):
        super().__init__(timeout=120)
        self.channel = channel
        self.guild   = guild

    async def update_embed(self, interaction: discord.Interaction, range_key: str):
        await interaction.response.edit_message(view=LoadingView())

        # Fetch core staff IDs from the support guild
        core_staff_ids: set[int] = set()
        support_guild = interaction.client.get_guild(SERVER_IDS["support"])
        if support_guild:
            for role_id in CORE_STAFF_ROLE_IDS:
                role = support_guild.get_role(role_id)
                if role:
                    for member in role.members:
                        core_staff_ids.add(member.id)

        start_ts, _ = ranges(range_key)
        if start_ts is not None:
            since = datetime.fromtimestamp(start_ts, tz=timezone.utc)
            counts = await fetch_punishment_counts(self.channel, since)
        else:
            # All-time: fetch entire channel history
            counts = await fetch_punishment_counts_all(self.channel)

        # Filter to core staff only
        if core_staff_ids:
            counts = {uid: data for uid, data in counts.items() if uid in core_staff_ids}

        sorted_data = sorted(counts.items(), key=lambda x: x[1]["total"], reverse=True)
        label = RANGE_LABELS.get(range_key, range_key)
        pages = build_punishments_pages(sorted_data, label)
        await interaction.edit_original_response(embed=pages[0], view=HistoryPageView(pages))

    @discord.ui.button(label="Last 7 Days",   style=discord.ButtonStyle.secondary, emoji=EMOJI_MC_CLOCK)
    async def last_7(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "7d")

    @discord.ui.button(label="Last 30 Days",  style=discord.ButtonStyle.secondary, emoji=EMOJI_COMPASS)
    async def last_30(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "30d")

    @discord.ui.button(label="Last 90 Days",  style=discord.ButtonStyle.secondary, emoji=EMOJI_MAP)
    async def last_90(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "90d")

    @discord.ui.button(label="Last 180 Days", style=discord.ButtonStyle.secondary, emoji=EMOJI_HOURGLASS)
    async def last_180(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "180d")

    @discord.ui.button(label="Last 365 Days", style=discord.ButtonStyle.secondary, emoji=EMOJI_ENDER_PEARL)
    async def last_365(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "365d")

    @discord.ui.button(label="All Time",      style=discord.ButtonStyle.secondary, emoji=EMOJI_NETHER_STAR)
    async def all_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "all")

    @discord.ui.button(label="This Week",     style=discord.ButtonStyle.primary,   emoji=EMOJI_BOOK)
    async def this_week(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "this_week")


class AppealRangeView(discord.ui.View):
    """Time-range picker for the appeal leaderboard."""

    def __init__(self, channel: discord.TextChannel, guild: discord.Guild):
        super().__init__(timeout=120)
        self.channel = channel
        self.guild   = guild

    async def update_embed(self, interaction: discord.Interaction, range_key: str):
        await interaction.response.edit_message(view=LoadingView())

        # Fetch core staff IDs from the support guild
        core_staff_ids: set[int] = set()
        support_guild = interaction.client.get_guild(SERVER_IDS["support"])
        if support_guild:
            for role_id in CORE_STAFF_ROLE_IDS:
                role = support_guild.get_role(role_id)
                if role:
                    for member in role.members:
                        core_staff_ids.add(member.id)

        start_ts, _ = ranges(range_key)
        if start_ts is not None:
            since = datetime.fromtimestamp(start_ts, tz=timezone.utc)
            counts = await fetch_appeal_counts(self.channel, since)
        else:
            counts = await fetch_appeal_counts_all(self.channel)

        # Filter to core staff only and resolve mentions
        resolved: list[tuple[str, int]] = []
        for staff_id, count in counts.items():
            if core_staff_ids and staff_id not in core_staff_ids:
                continue
            member = self.guild.get_member(staff_id)
            resolved.append((member.mention if member else f"<@{staff_id}>", count))

        sorted_data = sorted(resolved, key=lambda x: x[1], reverse=True)
        label = RANGE_LABELS.get(range_key, range_key)
        pages = build_appeals_pages(sorted_data, label)
        await interaction.edit_original_response(embed=pages[0], view=HistoryPageView(pages))

    @discord.ui.button(label="Last 7 Days",   style=discord.ButtonStyle.secondary, emoji=EMOJI_MC_CLOCK)
    async def last_7(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "7d")

    @discord.ui.button(label="Last 30 Days",  style=discord.ButtonStyle.secondary, emoji=EMOJI_COMPASS)
    async def last_30(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "30d")

    @discord.ui.button(label="Last 90 Days",  style=discord.ButtonStyle.secondary, emoji=EMOJI_MAP)
    async def last_90(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "90d")

    @discord.ui.button(label="Last 180 Days", style=discord.ButtonStyle.secondary, emoji=EMOJI_HOURGLASS)
    async def last_180(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "180d")

    @discord.ui.button(label="Last 365 Days", style=discord.ButtonStyle.secondary, emoji=EMOJI_ENDER_PEARL)
    async def last_365(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "365d")

    @discord.ui.button(label="All Time",      style=discord.ButtonStyle.secondary, emoji=EMOJI_NETHER_STAR)
    async def all_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "all")

    @discord.ui.button(label="This Week",     style=discord.ButtonStyle.primary,   emoji=EMOJI_BOOK)
    async def this_week(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "this_week")


class Stats(discord.ui.View):
    """Persistent stats panel pinned in the channel."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        emoji=EMOJI_SCROLL,
        label="Server Tickets",
        style=discord.ButtonStyle.secondary,
        custom_id="stats_refresh",
    )
    async def refresh_stat(self, interaction: discord.Interaction, button: discord.ui.Button):
        total_tickets     = 0
        total_unclaimed   = 0
        category_data: dict[str, dict] = {}

        for category_id in category_ids:
            category = interaction.guild.get_channel(category_id)
            if not category or not isinstance(category, discord.CategoryChannel):
                continue
            name = category.name.replace("➥ ", "")
            total    = len(category.channels)
            unclaimed = sum(1 for ch in category.channels if "⭕" in ch.name)
            total_tickets   += total
            total_unclaimed += unclaimed
            category_data[name] = {"total": total, "unclaimed": unclaimed, "id": category_id}

        embed = discord.Embed(
            title=f"{EMOJI_MAP} Server Ticket Stats",
            description=(
                f"> {EMOJI_EMERALD} **Total Tickets:** `{total_tickets}`\n"
                f"> {EMOJI_REDSTONE} **Unclaimed:** `{total_unclaimed}`\n"
            ),
            color=COLOR_INFO,
        )
        for cat_name, data in category_data.items():
            emoji = CATEGORY_EMOJIS_MAP.get(cat_name.lower(), EMOJI_BOOK)
            embed.add_field(
                name=f"{emoji} {cat_name}",
                value=(
                    f"-# {EMOJI_EMERALD} Total: `{data['total']}`\n"
                    f"-# {EMOJI_REDSTONE} Unclaimed: `{data['unclaimed']}`"
                ),
                inline=True,
            )

        embed.set_footer(text="Panel was last refreshed")
        embed.timestamp = datetime.now(timezone.utc)
        await interaction.response.edit_message(embed=embed, view=Stats())

    @discord.ui.button(
        emoji=EMOJI_SPYGLASS,
        label="My Stats",
        style=discord.ButtonStyle.secondary,
        custom_id="stats_my_stats",
    )
    async def check_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        ref            = db.reference("/Staff Claim")
        claim_database = ref.get() or {}
        now            = int(time.time())
        ts_list        = []

        for val in claim_database.values():
            if val["User ID"] == interaction.user.id:
                ts_list = val.get("List", [])
                break

        last_7d   = sum(1 for ts in ts_list if ts > now - 604800)
        last_30d  = sum(1 for ts in ts_list if ts > now - 2592000)
        last_180d = sum(1 for ts in ts_list if ts > now - 15552000)
        total     = len(ts_list)

        embed = discord.Embed(
            title=f"{EMOJI_SCROLL} My Ticket Stats",
            description=f"{EMOJI_STEVE} Believe it or not, we actually keep track of your ticket contributions. Here's a brief summary of your stats:",
            color=COLOR_INFO,
        )
        embed.add_field(name=f"{EMOJI_HOURGLASS} Last 7 Days",   value=f"`{last_7d}` tickets",   inline=True)
        embed.add_field(name=f"{EMOJI_HOURGLASS} Last 30 Days",  value=f"`{last_30d}` tickets",  inline=True)
        embed.add_field(name=f"{EMOJI_HOURGLASS} Last 180 Days", value=f"`{last_180d}` tickets", inline=True)
        embed.add_field(name=f"{EMOJI_NETHER_STAR} All Time",    value=f"`{total}` tickets",     inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(
        emoji=EMOJI_BOOK,
        label="My Active Tickets",
        style=discord.ButtonStyle.secondary,
        custom_id="stats_my_tickets",
    )
    async def my_tickets(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        active: list[dict] = []

        for category_id in category_ids:
            category = interaction.guild.get_channel(category_id)
            if not category or not isinstance(category, discord.CategoryChannel):
                continue
            for channel in category.channels:
                if not isinstance(channel, discord.TextChannel) or channel.name.startswith("🚫"):
                    continue
                participated = False
                async for msg in channel.history(limit=None):
                    if msg.author == interaction.user and not msg.is_system():
                        participated = True
                        break
                if not participated:
                    continue
                try:
                    user_id = int(channel.topic.replace("🚫", "").strip())
                    member  = interaction.guild.get_member(user_id)
                    mention = member.mention if member else f"Unknown User (`{user_id}`)"
                except Exception:
                    mention = "Unknown User"
                active.append({
                    "channel":    channel,
                    "user":       mention,
                    "created_at": channel.created_at,
                })

        if not active:
            await interaction.followup.send(
                embed=embed_info("No Active Tickets", f"You have no active tickets right now. {EMOJI_EMERALD}"),
                ephemeral=True,
            )
            return

        lines = []
        for idx, ticket in enumerate(active, 1):
            lines.append(
                f"{EMOJI_SCROLL} **{idx}.** {ticket['user']}'s ticket\n"
                f"-# <:reply:1036792837821435976> {EMOJI_MC_CLOCK} Created <t:{int(ticket['created_at'].timestamp())}:R>  •  "
                f"[Jump]({ticket['channel'].jump_url})"
            )

        embed = discord.Embed(
            title=f"{EMOJI_BOOK} My Active Tickets",
            description="\n\n".join(lines),
            color=COLOR_INFO,
        )
        embed.set_footer(text=f"{len(active)} active ticket{'s' if len(active) != 1 else ''}")
        await interaction.followup.send(embed=embed, ephemeral=True)


@app_commands.guild_only()
class StatsCommand(commands.GroupCog, name="stats"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="tickets", description="Show the staff ticket leaderboard")
    async def stats_tickets(self, interaction: discord.Interaction) -> None:
        if not await check_for_manager(interaction):
            return await interaction.response.send_message(
                embed=embed_error("Permission Denied", f"{EMOJI_BARRIER} You need Manager+ permissions to use this command."),
                ephemeral=True,
            )
        await interaction.response.defer(ephemeral=True)
        support_guild = interaction.client.get_guild(SERVER_IDS["support"])
        stats = await get_all_staff_ticket_stats(guild=support_guild)

        embed = discord.Embed(
            title=f"{EMOJI_SCROLL} Staff Ticket Leaderboard",
            description=(
                f"{EMOJI_SPYGLASS} Select a time range below to view the leaderboard.\n"
                f"-# <:reply:1036792837821435976> Counts the number of tickets helped in the support server."
            ),
            color=COLOR_INFO,
        )
        await interaction.followup.send(embed=embed, view=TicketRangeView(stats), ephemeral=True)

    @app_commands.command(name="testers", description="Show the tierlist tester leaderboard")
    async def stats_testers(self, interaction: discord.Interaction) -> None:
        if not await check_for_manager(interaction):
            return await interaction.response.send_message(
                embed=embed_error("Permission Denied", f"{EMOJI_BARRIER} You need Manager+ permissions to use this command."),
                ephemeral=True,
            )
        await interaction.response.defer(ephemeral=True)
        tierlist_guild = interaction.client.get_guild(SERVER_IDS["tierlist"])
        stats = await get_all_tester_stats(guild_tierlist=tierlist_guild)

        embed = discord.Embed(
            title=f"{EMOJI_NETHER_STAR} Tester Leaderboard",
            description=(
                f"{EMOJI_SPYGLASS} Select a time range below to view the leaderboard.\n"
                f"-# <:reply:1036792837821435976> Counts the number of tests performed in the tierlist server."
            ),
            color=COLOR_INFO,
        )
        await interaction.followup.send(embed=embed, view=TesterRangeView(stats), ephemeral=True)

    @app_commands.command(name="punishments", description="Show the punishment log leaderboard")
    async def stats_punishments(self, interaction: discord.Interaction) -> None:
        if not await check_for_manager(interaction):
            return await interaction.response.send_message(
                embed=embed_error("Permission Denied", f"{EMOJI_BARRIER} You need Manager+ permissions to use this command."),
                ephemeral=True,
            )
        await interaction.response.defer(ephemeral=True)
        channel = interaction.client.get_channel(PUNISHMENT_LOG_CHANNEL_ID)
        if not channel:
            return await interaction.followup.send(
                embed=embed_error("Channel Not Found", "Could not find the punishment log channel."),
            )

        embed = discord.Embed(
            title=f"{EMOJI_BARRIER} Punishment Leaderboard",
            description=(
                f"{EMOJI_SPYGLASS} Select a time range below.\n"
                f"-# <:reply:1036792837821435976> Counts bans, mutes, and warns from <#{PUNISHMENT_LOG_CHANNEL_ID}>."
            ),
            color=COLOR_ERROR,
        )
        await interaction.followup.send(embed=embed, view=PunishmentRangeView(channel, interaction.guild), ephemeral=True)

    @app_commands.command(name="appeals", description="Show the appeal actions leaderboard")
    async def stats_appeals(self, interaction: discord.Interaction) -> None:
        if not await check_for_manager(interaction):
            return await interaction.response.send_message(
                embed=embed_error("Permission Denied", f"{EMOJI_BARRIER} You need Manager+ permissions to use this command."),
                ephemeral=True,
            )
        await interaction.response.defer(ephemeral=True)
        channel = interaction.client.get_channel(APPEAL_LOG_CHANNEL_ID)
        if not channel:
            return await interaction.followup.send(
                embed=embed_error("Channel Not Found", "Could not find the appeal log channel."),
            )

        embed = discord.Embed(
            title=f"{EMOJI_ENDER_PEARL} Appeal Actions Leaderboard",
            description=(
                f"{EMOJI_SPYGLASS} Select a time range below.\n"
                f"-# <:reply:1036792837821435976> Counts accepted and rejected appeals from <#{APPEAL_LOG_CHANNEL_ID}>."
            ),
            color=COLOR_WARNING,
        )
        await interaction.followup.send(
            embed=embed,
            view=AppealRangeView(channel, interaction.guild),
            ephemeral=True,
        )

    @app_commands.command(name="checkup", description="Generate weekly checkups for all staff members")
    async def stats_checkup(self, interaction: discord.Interaction) -> None:
        if not await check_for_manager(interaction):
            return await interaction.response.send_message(
                embed=embed_error("Permission Denied", f"{EMOJI_BARRIER} You need Manager+ permissions to use this command."),
                ephemeral=True,
            )
        await interaction.response.defer(thinking=True, ephemeral=True)

        role_requirements = {
            1290409277638311947: {"mutes": 10, "bans": 3},  # Sr. Admin
            1090330479179350037: {"mutes": 5,  "bans": 3},  # Admin
            1232591866281852959: {"mutes": 6,  "bans": 2},  # Sr. Moderator
            1066298183879229490: {"mutes": 5,  "bans": 2},  # Moderator
            1172834016412569610: {"warns": 3,  "mutes": 5}, # Helper
        }
        higher_roles = {1290409277638311947, 1090330479179350037, 1232591866281852959}

        logs_channel = interaction.guild.get_channel(SM_LOGS_CHANNEL_ID)
        if not logs_channel:
            return await interaction.followup.send(
                embed=embed_error("Channel Not Found", "Could not find the sm-logs channel."),
            )

        messages: list[discord.Message] = []
        try:
            async for msg in logs_channel.history(limit=10):
                if "Playtime" in msg.content:
                    messages.append(msg)
                    if len(messages) == 2:
                        break
        except discord.Forbidden:
            return await interaction.followup.send(
                embed=embed_error("No Access", f"{EMOJI_BARRIER} I can't read the sm-logs channel."),
            )

        if len(messages) < 2:
            return await interaction.followup.send(
                embed=embed_error("Not Enough Data", "Need at least 2 playtime log messages to calculate differences."),
            )

        current_week  = await self.parse_playtime_message(messages[0].content)
        previous_week = await self.parse_playtime_message(messages[1].content)

        playtime_diffs: dict[int, dict] = {}
        for user_id, curr in current_week.items():
            if user_id in previous_week:
                prev = previous_week[user_id]
                playtime_diffs[user_id] = {
                    "lifesteal": curr["lifesteal"] - prev["lifesteal"],
                    "vanilla":   curr["vanilla"]   - prev["vanilla"],
                    "practice":  curr["practice"]  - prev["practice"],
                }

        ticket_counts     = await self.get_ticket_counts(7)
        punishment_counts = await self.get_punishment_counts(interaction, 7)
        appeal_counts     = await self.get_appeal_counts(interaction, 7)

        sent_count = 0
        for user_id, diffs in playtime_diffs.items():
            member = interaction.guild.get_member(user_id)
            if not member:
                continue

            notebook_channel = next(
                (ch for ch in interaction.guild.text_channels if ch.topic and str(user_id) in ch.topic),
                None,
            )
            if not notebook_channel:
                continue

            role_ids     = {r.id for r in member.roles}
            punishments  = punishment_counts.get(user_id, {"total": 0, "bans": 0, "mutes": 0, "warns": 0})
            tickets      = ticket_counts.get(user_id, 0)
            appeals      = appeal_counts.get(user_id, 0)
            total_playtime = diffs["lifesteal"] + diffs["vanilla"] + diffs["practice"]

            unmet: list[str] = []
            for role_id, reqs in role_requirements.items():
                if role_id not in role_ids:
                    continue
                if role_id == 1172834016412569610:   # Helper
                    if punishments["warns"]  < reqs.get("warns",  0): unmet.append(f"Warns ({punishments['warns']}/{reqs['warns']})")
                    if punishments["mutes"]  < reqs.get("mutes",  0): unmet.append(f"Mutes ({punishments['mutes']}/{reqs['mutes']})")
                else:
                    if punishments["mutes"]  < reqs.get("mutes",  0): unmet.append(f"Mutes ({punishments['mutes']}/{reqs['mutes']})")
                    if punishments["bans"]   < reqs.get("bans",   0): unmet.append(f"Bans ({punishments['bans']}/{reqs['bans']})")
                break

            req_line = (
                f"\n\n{EMOJI_EMERALD} Met the minimum requirement!"
                if not unmet else
                f"\n\n{EMOJI_GOLD_INGOT} **Did not meet minimum requirement:**\n" +
                "\n".join(f"-# {EMOJI_REDSTONE} {r}" for r in unmet)
            )

            is_higher = bool(role_ids & higher_roles)

            embed = discord.Embed(
                title=f"{EMOJI_SCROLL} Weekly Checkup",
                color=COLOR_INFO,
            )
            embed.description = (
                f"{EMOJI_BARRIER} **Punishments:** `{punishments['total']}` total \n"
                f"-# <:reply:1036792837821435976> `{punishments['bans']}` bans  •  `{punishments['mutes']}` mutes  •  `{punishments['warns']}` warns\n"
                f"{EMOJI_BOOK} **Tickets claimed:** `{tickets}`\n"
            )
            if is_higher:
                embed.description += f"{EMOJI_ENDER_PEARL} **Appeals resolved:** `{appeals}`\n"
            embed.description += (
                f"{EMOJI_COMPASS} **Playtime this week:** `{total_playtime}h`\n"
                f"-# <:reply:1036792837821435976> Lifesteal `{diffs['lifesteal']}h`  •  "
                f"Vanilla `{diffs['vanilla']}h`  •  Practice `{diffs['practice']}h`"
                f"{req_line}"
            )

            try:
                await notebook_channel.send(embed=embed)
                sent_count += 1
                await asyncio.sleep(1)
            except discord.Forbidden:
                continue

        await interaction.followup.send(
            embed=embed_success(
                "Checkups Sent",
                f"{EMOJI_EMERALD} Weekly checkup embeds sent to **{sent_count}** staff notebook channel{'s' if sent_count != 1 else ''}.",
            ),
        )

    async def parse_playtime_message(self, content: str) -> dict[int, dict]:
        playtimes: dict[int, dict] = {}
        for line in content.split("\n"):
            if "-->" not in line or "<@" not in line:
                continue
            user_match = re.search(r"<@!?(\d+)>", line)
            time_match = re.search(r"--> (.+)$", line)
            if not user_match or not time_match:
                continue
            user_id    = int(user_match.group(1))
            time_parts = time_match.group(1).split("|")
            if len(time_parts) != 3:
                continue
            modes = ["lifesteal", "vanilla", "practice"]
            data: dict[str, int] = {}
            for i, part in enumerate(time_parts):
                part = part.strip().replace("t", "d")
                days  = int(m.group(1)) if (m := re.search(r"(\d+)d", part)) else 0
                hours = int(m.group(1)) if (m := re.search(r"(\d+)h", part)) else 0
                data[modes[i]] = days * 24 + hours
            playtimes[user_id] = data
        return playtimes

    async def get_ticket_counts(self, days: int) -> dict[int, int]:
        ref            = db.reference("/Staff Claim")
        claim_database = ref.get() or {}
        since          = int(time.time()) - days * 86400
        return {
            val["User ID"]: sum(1 for ts in val.get("List", []) if ts > since)
            for val in claim_database.values()
        }

    async def get_punishment_counts(self, interaction: discord.Interaction, days: int) -> dict[int, dict]:
        channel = interaction.client.get_channel(PUNISHMENT_LOG_CHANNEL_ID)
        if not channel:
            return {}
        since = discord.utils.utcnow() - timedelta(days=days)
        return await fetch_punishment_counts(channel, since)

    async def get_appeal_counts(self, interaction: discord.Interaction, days: int) -> dict[int, int]:
        channel = interaction.client.get_channel(APPEAL_LOG_CHANNEL_ID)
        if not channel:
            return {}
        since = discord.utils.utcnow() - timedelta(days=days)
        return await fetch_appeal_counts(channel, since)


class StatsMsg(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.client = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.client.user or message.author.bot or not message.guild:
            return

        support_categories = set(CATEGORY_IDS.get(SERVER_IDS["support"], {}).values())
        if (
            hasattr(message.channel, "category")
            and message.channel.category
            and message.channel.category.id in support_categories
        ):
            try:
                async for msg in message.channel.history(limit=None):
                    if msg.author == message.author and msg != message:
                        return

                ref            = db.reference("/Staff Claim")
                claim_database = ref.get() or {}
                ts_list        = []

                for key, val in claim_database.items():
                    if val["User ID"] == message.author.id:
                        ts_list = val.get("List", [])
                        db.reference("/Staff Claim").child(key).delete()
                        break

                ts_list.append(int(time.time()))
                ref.push().set({"User ID": message.author.id, "List": ts_list})

            except Exception as e:
                print(f"[StatsMsg] Error tracking staff contribution: {e}")

        if message.content == "mc!panel":
            embed = discord.Embed(
                title=f"{EMOJI_MAP} Staff Stats Panel",
                description=(
                    f"{EMOJI_SPYGLASS} Use the buttons below to check ticket stats, active tickets, or refresh the live server count.\n"
                    f"-# {EMOJI_EMERALD} Data updates in real-time."
                ),
                color=COLOR_INFO,
            )
            await message.channel.send(embed=embed, view=Stats())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StatsCommand(bot))
    await bot.add_cog(StatsMsg(bot))