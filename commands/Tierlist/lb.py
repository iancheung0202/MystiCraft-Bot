import discord
import time
from discord import app_commands
from discord.ext import commands
from firebase_admin import db
from datetime import datetime, timedelta
from constants import SERVER_IDS

EMOJI_EMERALD       = "<:emerald:1518031176730804244>"
EMOJI_REDSTONE      = "<:redstone_dust:1518031324588539986>"
EMOJI_GOLD_INGOT    = "<:gold_ingot:1518031441248653433>"
EMOJI_NETHER_STAR   = "<:nether_star:1518033504120606771>"
EMOJI_COMPASS       = "<a:compass:1518032475803226214>"
EMOJI_ENDER_PEARL   = "<:ender_pearl:1518033866995269763>"
EMOJI_MC_CLOCK      = "<:mc_clock:1518027805361967104>"
EMOJI_MAP           = "<:map:1518038367521210499>"
EMOJI_BOOK          = "<:book:1518051136488214549>"
EMOJI_REPLY         = "<:reply:1036792837821435976>"
EMOJI_TIERLIST      = "<:mysticrafttierlist:1460527955309498550>"
EMOJI_RANK          = "<:Trophy:1523013568067539044>"
EMOJI_GOLD          = "<:gold:1518477859679633539>"
EMOJI_CRYSTAL       = "<:crystal:1518050761010057290>"
EMOJI_HOURGLASS     = "<:hourglass:1518454206162538546>"

EMOJI_FAST_BACKWARD = "<:fastbackward:1351972112696479824>"
EMOJI_BACK_ARROW    = "<:backarrow:1351972111010369618>"
EMOJI_RIGHT_ARROW   = "<:rightarrow:1351972116819480616>"
EMOJI_FAST_FORWARD  = "<:fastforward:1351972114433048719>"

TIERLIST_TESTER_ROLE_ID = 1305918277549162586
PER_PAGE = 15
COLOR_TROPHY = 0xf1c40f

LB_STORE = "/TesterLB/messages"

def _week_start() -> int:
    now = datetime.now()
    ds = (now.weekday() + 1) % 7
    s = now - timedelta(days=ds)
    return int(s.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())

RANGE_CFG = [
    ("7d",        "Last 7 Days",     EMOJI_MC_CLOCK,    "7d",   "h7d"),
    ("30d",       "Last 30 Days",    EMOJI_COMPASS,     "30d",  "h30d"),
    ("90d",       "Last 90 Days",    EMOJI_MAP,         "90d",  "h90d"),
    ("180d",      "Last 180 Days",   EMOJI_HOURGLASS,   "180d", "h180d"),
    ("365d",      "Last 365 Days",   EMOJI_ENDER_PEARL, "365d", "h365d"),
    ("this_week", "This Week",       EMOJI_BOOK,        "w",    "hw"),
    ("all",       "All Time",        EMOJI_NETHER_STAR, "all",  "hall"),
]

async def fetch_stats(guild_tl: discord.Guild | None) -> list[dict]:
    ref = db.reference("/Tierlist Tester Stats")
    data = ref.get() or {}
    now = int(time.time())
    ws = _week_start()

    tids: set[int] = set()
    if guild_tl is not None:
        r = guild_tl.get_role(TIERLIST_TESTER_ROLE_ID)
        if r:
            tids.update(m.id for m in r.members)

    out = []
    for uid_str, v in data.items():
        uid = int(uid_str)
        if guild_tl is not None and uid not in tids:
            continue
        ts = v.get("timestamps", [])
        hs = v.get("high_timestamps", [])
        out.append({
            "uid": uid,
            "7d": sum(1 for t in ts if t > now - 604800),
            "30d": sum(1 for t in ts if t > now - 2592000),
            "90d": sum(1 for t in ts if t > now - 7776000),
            "180d": sum(1 for t in ts if t > now - 15552000),
            "365d": sum(1 for t in ts if t > now - 31536000),
            "w": sum(1 for t in ts if t >= ws),
            "all": v.get("count", len(ts)),
            "h7d": sum(1 for t in hs if t > now - 604800),
            "h30d": sum(1 for t in hs if t > now - 2592000),
            "h90d": sum(1 for t in hs if t > now - 7776000),
            "h180d": sum(1 for t in hs if t > now - 15552000),
            "h365d": sum(1 for t in hs if t > now - 31536000),
            "hw": sum(1 for t in hs if t >= ws),
            "hall": v.get("high_count", len(hs)),
        })
    return out

def build_pages(data: list[dict], cfg_idx: int) -> list[discord.Embed]:
    _, label, _emoji, skey, hkey = RANGE_CFG[cfg_idx]

    entries = []
    for d in data:
        n = d[skey]
        h = d[hkey]
        entries.append((d["uid"], n, h, n + 2 * h))

    entries.sort(key=lambda x: x[3], reverse=True)

    if not entries:
        return [discord.Embed(
            title=f"{EMOJI_TIERLIST} MystiTiers Tester Leaderboard *({label})* {EMOJI_RANK}",
            description=f"{EMOJI_REDSTONE} No data for this period.",
            color=COLOR_TROPHY,
        )]

    total = max(1, (len(entries) + PER_PAGE - 1) // PER_PAGE)
    pages = []

    for pi, start in enumerate(range(0, len(entries), PER_PAGE)):
        chunk = entries[start:start + PER_PAGE]
        lines = []
        for rank, (uid, n, h, rep) in enumerate(chunk, start=start + 1):
            badge = {1: "\U0001f947", 2: "\U0001f948", 3: "\U0001f949"}.get(rank, f"`#{rank}`")
            lines.append(
                f"{badge} <@{uid}>\n"
                f"-# {EMOJI_REPLY} {EMOJI_GOLD_INGOT} **{rep} rep**  \u2022  {EMOJI_MC_CLOCK} {n} tests  \u2022  {EMOJI_CRYSTAL} {h} high"
            )

        embed = discord.Embed(
            title=f"{EMOJI_TIERLIST} MystiTiers Tester Leaderboard *({label})* {EMOJI_RANK}",
            description="> A tester is considered active if they have **`16`** or more tests every week!\n\n" + "\n".join(lines),
            color=COLOR_TROPHY,
        )
        embed.set_footer(text=f"Page {pi + 1} / {total}  \u2022  {label}")
        pages.append(embed)

    return pages


class RangeSelect(discord.ui.Select):
    def __init__(self):
        opts = [
            discord.SelectOption(label=label, value=str(i), emoji=emoji)
            for i, (_, label, emoji, _, _) in enumerate(RANGE_CFG)
        ]
        super().__init__(custom_id="testerlb:range", placeholder="Select a time range\u2026", options=opts, row=0)

    async def callback(self, interaction: discord.Interaction):
        view: TesterLBView = self.view
        await view.ensure()
        idx = int(self.values[0])
        view.range_idx = idx
        view.page = 0
        view.pages = build_pages(view.data, idx)
        db.reference(f"{LB_STORE}/{view._msg_id}").update({"range_idx": idx})
        await interaction.response.edit_message(embed=view.pages[0], view=view)


class TesterLBView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.data = None
        self.tl_guild_id = None
        self._msg_id = None
        self.range_idx = 6
        self.pages = [discord.Embed(title=f"{EMOJI_RANK} Tester Leaderboard", description=f"{EMOJI_HOURGLASS} Loading\u2026", color=COLOR_TROPHY)]
        self.page = 0
        self.add_item(RangeSelect())

    async def ensure(self):
        if self.data is None:
            guild = self.bot.get_guild(self.tl_guild_id) if hasattr(self, "bot") else None
            if guild is None:
                return
            self.data = await fetch_stats(guild)
            self.pages = build_pages(self.data, self.range_idx)
            self.page = min(self.page, len(self.pages) - 1)

    @discord.ui.button(emoji=EMOJI_FAST_BACKWARD, style=discord.ButtonStyle.grey, custom_id="testerlb:first", row=1)
    async def first_pg(self, i: discord.Interaction, b: discord.ui.Button):
        await self.ensure()
        self.page = 0
        await i.response.edit_message(embed=self.pages[0], view=self)

    @discord.ui.button(emoji=EMOJI_BACK_ARROW, style=discord.ButtonStyle.grey, custom_id="testerlb:prev", row=1)
    async def prev_pg(self, i: discord.Interaction, b: discord.ui.Button):
        await self.ensure()
        self.page = (self.page - 1) % len(self.pages)
        await i.response.edit_message(embed=self.pages[self.page], view=self)

    @discord.ui.button(emoji=EMOJI_RIGHT_ARROW, style=discord.ButtonStyle.grey, custom_id="testerlb:next", row=1)
    async def next_pg(self, i: discord.Interaction, b: discord.ui.Button):
        await self.ensure()
        self.page = (self.page + 1) % len(self.pages)
        await i.response.edit_message(embed=self.pages[self.page], view=self)

    @discord.ui.button(emoji=EMOJI_FAST_FORWARD, style=discord.ButtonStyle.grey, custom_id="testerlb:last", row=1)
    async def last_pg(self, i: discord.Interaction, b: discord.ui.Button):
        await self.ensure()
        self.page = len(self.pages) - 1
        await i.response.edit_message(embed=self.pages[-1], view=self)

    @discord.ui.button(emoji=EMOJI_COMPASS, label="Refresh", style=discord.ButtonStyle.secondary, custom_id="testerlb:refresh", row=1)
    async def refresh_btn(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.defer()
        self.data = await fetch_stats(i.client.get_guild(self.tl_guild_id))
        self.pages = build_pages(self.data, self.range_idx)
        self.page = min(self.page, len(self.pages) - 1)
        await i.edit_original_response(embed=self.pages[self.page], view=self)


class TestLBCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        ref = db.reference(LB_STORE)
        records = ref.get() or {}
        for msg_id_str, val in records.items():
            try:
                msg_id = int(msg_id_str)
                view = TesterLBView()
                view.tl_guild_id = val["guild_id"]
                view._msg_id = msg_id
                view.range_idx = val.get("range_idx", 6)
                view.bot = self.bot
                self.bot.add_view(view, message_id=msg_id)
            except Exception as e:
                print(f"[TesterLB] Failed to restore view for message {msg_id_str}: {e}")

    @app_commands.command(name="testerlb", description="Post a public tester leaderboard with rep scores")
    async def testlb(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        tl = interaction.client.get_guild(SERVER_IDS["tierlist"])
        data = await fetch_stats(tl)
        msg = await interaction.channel.send(embed=discord.Embed(
            title=f"{EMOJI_RANK} Tester Leaderboard",
            description=f"{EMOJI_HOURGLASS} Loading\u2026",
            color=COLOR_TROPHY,
        ))
        view = TesterLBView()
        view.data = data
        view.tl_guild_id = SERVER_IDS["tierlist"]
        view._msg_id = msg.id
        view.pages = build_pages(data, 6)
        view.bot = self.bot
        db.reference(f"{LB_STORE}/{msg.id}").set({
            "guild_id": interaction.guild_id,
            "channel_id": interaction.channel_id,
            "range_idx": 6,
        })
        await msg.edit(embed=view.pages[0], view=view)
        await interaction.followup.send(f"{EMOJI_EMERALD} Leaderboard posted!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(TestLBCog(bot))
