import os
import io
import re
import json
import time
import aiohttp
import asyncio
import discord

from discord.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFont

EMOJI_ONLINE = "<:emerald:1518031176730804244>"
EMOJI_OFFLINE = "<:redstone_dust:1518031324588539986>"
EMOJI_STALE = "<:gold_ingot:1518031441248653433>"
EMOJI_PLAYERS = "<:steve:1518031537814110382>"
EMOJI_PEAK_TODAY = "<:gold_ingot:1518031441248653433>" # same intentionally
EMOJI_PEAK_ALLTIME = "<:nether_star:1518033504120606771>"
EMOJI_AVG = "<a:compass:1518032475803226214>"
EMOJI_REFRESH = "<:ender_pearl:1518033866995269763>"  # kept for reuse later, button removed
EMOJI_SERVER = "<a:command_block:1518032605692297256>"
EMOJI_CLOCK = "<:mc_clock:1518027805361967104>"
EMOJI_CONNECT = "<:lodestone:1518038285354795158>"
EMOJI_WEBSITE = "<:map:1518038367521210499>"
EMOJI_TICKET = "<:book:1518051136488214549>"
EMOJI_TIERLIST = "<:crystal:1518050761010057290>"

SERVER_THUMBNAIL_URL = "https://mysticraft.xyz/images/logo-96.png"
SERVER_BANNER_URL = "https://mysticraft.xyz/uploads/banner_1779506940878_931a1c5b.png"
SERVER_IP = "play.mysticraft.xyz"
SERVER_PORT = "19132"
REFRESH_INTERVAL_MINUTES = 5

STATUS_CHANNEL_ID = 1518003660515442728
STATUS_MESSAGE_STATE_PATH = "./assets/status_message_state.json"

BANNER_W, BANNER_H = 1371, 807

FONT_REGULAR_PATH = "./assets/Minecraft.otf"
FONT_BOLD_PATH = "./assets/Minecraft-Bold.otf"

COLOR_WHITE = (255, 255, 255, 255)
COLOR_GREEN = (85, 230, 110, 255)
COLOR_RED = (235, 90, 90, 255)
COLOR_YELLOW = (235, 200, 90, 255)
COLOR_GREY = (200, 203, 212, 255)
COLOR_SHADOW = (0, 0, 0, 190)

BANNER_OUTPUT_FILENAME = "status_banner.png"

_EMOJI_PATTERN = re.compile(r"<a?:([a-zA-Z0-9_]+):(\d+)>")


async def fetch_stats() -> dict:
    server_status = {}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://mysticraft.xyz/api/server-status",
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status != 200:
                    print(f"[Server Status] API returned HTTP {resp.status}, keeping existing status.")
                    server_status = {}
                else:
                    server_status = await resp.json()
                    if not isinstance(server_status, dict):
                        print(f"[Server Status] API returned non-object JSON, keeping existing status.")
                        server_status = {}
    except asyncio.TimeoutError:
        print("[Server Status] API fetch timed out, keeping existing status.")
        server_status = {}
    except Exception as e:
        print(f"[Server Status] API fetch error: {e}, keeping existing status.")
        server_status = {}

    server_analytics = {}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://mysticraft.xyz/api/admin/server-analytics",
                headers={"x-api-key": os.environ.get("BOT_ACCESS_API_KEY")},
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status != 200:
                    print(f"[Server Analytics] API returned HTTP {resp.status}, keeping existing status.")
                    server_analytics = {}
                else:
                    server_analytics = await resp.json()
                    if not isinstance(server_analytics, dict):
                        print(f"[Server Analytics] API returned non-object JSON, keeping existing status.")
                        server_analytics = {}
    except asyncio.TimeoutError:
        print("[Server Analytics] API fetch timed out, keeping existing status.")
        server_analytics = {}
    except Exception as e:
        print(f"[Server Analytics] API fetch error: {e}, keeping existing status.")
        server_analytics = {}

    return {
        "status": server_status,
        "analytics": server_analytics
    }


async def _download_bytes(url: str) -> bytes | None:
    """Generic async download helper. Returns None on any failure so
    callers can fall back gracefully instead of crashing image generation."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    print(f"[Banner] Failed to download {url}: HTTP {resp.status}")
                    return None
                return await resp.read()
    except Exception as e:
        print(f"[Banner] Failed to download {url}: {e}")
        return None


def _emoji_cdn_url(emoji_string: str) -> str | None:
    """Extracts the ID from a <:name:id> or <a:name:id> custom emoji string
    and returns its Discord CDN image URL. Returns None if emoji_string
    isn't a custom emoji (e.g. a plain unicode emoji fallback)."""
    match = _EMOJI_PATTERN.match(emoji_string.strip())
    if not match:
        return None
    emoji_id = match.group(2)
    return f"https://cdn.discordapp.com/emojis/{emoji_id}.png?size=96"


async def _load_emoji_icon(emoji_string: str) -> Image.Image | None:
    """Downloads a custom emoji's image from Discord's CDN and returns it
    as an RGBA Pillow image, or None if it can't be fetched (e.g. it's a
    plain unicode emoji, or the network call failed)."""
    url = _emoji_cdn_url(emoji_string)
    if url is None:
        return None
    raw = await _download_bytes(url)
    if raw is None:
        return None
    try:
        return Image.open(io.BytesIO(raw)).convert("RGBA")
    except Exception as e:
        print(f"[Banner] Failed to decode emoji image: {e}")
        return None


def _build_vignette_mask(w: int, h: int) -> Image.Image:
    """Builds a single-channel darkness mask: a horizontal fade across a
    left-hand strip (for the status/players/connect text) plus a soft
    radial vignette in the bottom-right corner (for the stats block).
    Returned mask is later used as the alpha channel of a solid black
    overlay composited on top of the banner photo."""
    import numpy as np

    left_mask = Image.new("L", (w, h), 0)
    lm_draw = ImageDraw.Draw(left_mask)
    left_strip_width = int(w * 0.60)   # wider — fade reaches more toward center
    left_max_alpha = 235               # slightly darker
    for x in range(left_strip_width):
        t = x / left_strip_width
        alpha = int(left_max_alpha * (1 - t) ** 1.6)
        lm_draw.line([(x, 0), (x, h)], fill=alpha)

    corner_mask = Image.new("L", (w, h), 0)
    cm_draw = ImageDraw.Draw(corner_mask)
    corner_max_alpha = 225             # slightly darker
    cx, cy = w * 0.95, h * 0.98       # origin pulled more toward center
    max_radius = w * 0.58             # slightly tighter radius → more central
    step = 2
    for y0 in range(int(h * 0.30), h, step):   # start higher up
        for x0 in range(int(w * 0.38), w, step):  # start further left
            dist = ((x0 - cx) ** 2 + (y0 - cy) ** 2) ** 0.5
            t = max(0.0, 1 - dist / max_radius)
            if t <= 0:
                continue
            alpha = int(corner_max_alpha * (t ** 1.3))
            cm_draw.rectangle([x0, y0, x0 + step, y0 + step], fill=alpha)

    from PIL import ImageFilter
    corner_mask = corner_mask.filter(ImageFilter.GaussianBlur(18))

    left_arr = np.array(left_mask, dtype=np.int16)
    corner_arr = np.array(corner_mask, dtype=np.int16)
    combined = np.maximum(left_arr, corner_arr).astype("uint8")
    return Image.fromarray(combined, mode="L")


def _draw_text_shadowed(draw: ImageDraw.ImageDraw, pos, text, font,
                         fill=COLOR_WHITE, shadow_offset=3):
    x, y = pos
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=COLOR_SHADOW)
    draw.text((x, y), text, font=font, fill=fill)


def _paste_icon(base: Image.Image, icon: Image.Image | None, pos, size: int):
    """Pastes a downloaded emoji icon at the given top-left position,
    resized to a square of `size`. If icon is None (download failed),
    silently skips so layout doesn't break."""
    if icon is None:
        return
    resized = icon.resize((size, size), Image.LANCZOS)
    base.paste(resized, pos, resized)


async def generate_status_banner(stats: dict) -> io.BytesIO:
    """Builds the full status panel as a single PNG image: the server's
    banner photo, darkened on the left strip and bottom-right corner,
    with all status/player/connection/stat info drawn on top in a
    Minecraft-style pixel font, plus small custom-emoji icons fetched
    live from Discord's CDN. Returns an in-memory PNG buffer."""

    status = stats.get("status") or {}
    analytics = stats.get("analytics") or {}

    online = status.get("online", False)
    stale = status.get("stale", False)
    players = status.get("players", 0)
    max_players = status.get("maxPlayers", 0)

    peaks = analytics.get("peaks", {})
    daily_peak = peaks.get("daily", {})
    alltime_peak = peaks.get("allTime", {})
    avg_24h = analytics.get("avgPlayers24h")

    if not status:
        indicator_emoji, indicator_color = EMOJI_OFFLINE, COLOR_RED
        status_label, status_sub = "STATUS UNAVAILABLE", "Couldn't reach the server"
    elif stale:
        indicator_emoji, indicator_color = EMOJI_STALE, COLOR_YELLOW
        status_label, status_sub = "STATUS STALE", "Last known data, may be outdated"
    elif online:
        indicator_emoji, indicator_color = EMOJI_ONLINE, COLOR_GREEN
        status_label, status_sub = "SERVER ONLINE", "Players can connect right now"
    else:
        indicator_emoji, indicator_color = EMOJI_OFFLINE, COLOR_RED
        status_label, status_sub = "SERVER OFFLINE", "The server is currently down"

    # Fetch banner photo + all emoji icons concurrently
    banner_bytes_task = _download_bytes(SERVER_BANNER_URL)
    indicator_icon_task = _load_emoji_icon(indicator_emoji)
    players_icon_task = _load_emoji_icon(EMOJI_PLAYERS)
    connect_icon_task = _load_emoji_icon(EMOJI_CONNECT)
    peak_today_icon_task = _load_emoji_icon(EMOJI_PEAK_TODAY)
    peak_alltime_icon_task = _load_emoji_icon(EMOJI_PEAK_ALLTIME)
    avg_icon_task = _load_emoji_icon(EMOJI_AVG)

    (banner_bytes, indicator_icon, players_icon, connect_icon,
     peak_today_icon, peak_alltime_icon, avg_icon) = await asyncio.gather(
        banner_bytes_task, indicator_icon_task, players_icon_task, connect_icon_task,
        peak_today_icon_task, peak_alltime_icon_task, avg_icon_task
    )

    if banner_bytes is not None:
        try:
            base = Image.open(io.BytesIO(banner_bytes)).convert("RGBA")
            base = base.resize((BANNER_W, BANNER_H), Image.LANCZOS)
        except Exception as e:
            print(f"[Banner] Failed to decode banner photo: {e}")
            base = Image.new("RGBA", (BANNER_W, BANNER_H), (30, 32, 40, 255))
    else:
        base = Image.new("RGBA", (BANNER_W, BANNER_H), (30, 32, 40, 255))

    # Darken the left strip + bottom-right corner
    mask = _build_vignette_mask(BANNER_W, BANNER_H)
    black = Image.new("RGBA", (BANNER_W, BANNER_H), (8, 9, 13, 255))
    black.putalpha(mask)
    base = Image.alpha_composite(base, black)

    draw = ImageDraw.Draw(base)

    def font_bold(size):
        return ImageFont.truetype(FONT_BOLD_PATH, size)

    def font_reg(size):
        return ImageFont.truetype(FONT_REGULAR_PATH, size)

    PAD_LEFT = 56
    y = 90 

    # Server name
    _draw_text_shadowed(draw, (PAD_LEFT, y), "MYSTICRAFT", font_bold(66))
    y += 100

    # Status icon + label
    if indicator_icon is not None:
        icon_size_indicator = 44
        icon_cy = y + 26
        _paste_icon(base, indicator_icon,
                    (PAD_LEFT, icon_cy - icon_size_indicator // 2),
                    size=icon_size_indicator)
        label_x = PAD_LEFT + icon_size_indicator + 16
    else:
        # Fallback to a plain colored dot if the emoji failed to download
        dot_r = 14
        dot_cy = y + 26
        draw.ellipse([PAD_LEFT - 1, dot_cy - dot_r - 1,
                      PAD_LEFT + dot_r * 2 - 1, dot_cy + dot_r - 1],
                     fill=(0, 0, 0, 170))
        draw.ellipse([PAD_LEFT, dot_cy - dot_r,
                      PAD_LEFT + dot_r * 2, dot_cy + dot_r], fill=indicator_color)
        label_x = PAD_LEFT + dot_r * 2 + 20
    _draw_text_shadowed(draw, (label_x, y),
                        status_label, font_bold(50), fill=indicator_color)
    y += 74
    _draw_text_shadowed(draw, (PAD_LEFT, y), status_sub, font_reg(27), fill=COLOR_GREY)
    y += 82

    # Player count
    if max_players:
        players_line = f"{players} / {max_players}"
    else:
        players_line = f"{players}"
    icon_size_players = 68             # bigger steve icon
    _paste_icon(base, players_icon, (PAD_LEFT, y + 4), size=icon_size_players)
    _draw_text_shadowed(draw, (PAD_LEFT + icon_size_players + 14, y),
                        players_line, font_bold(58))
    y += 72
    _draw_text_shadowed(draw, (PAD_LEFT + icon_size_players + 14, y),
                        "PLAYERS ONLINE", font_reg(26), fill=COLOR_GREY)

    # Connection info — anchored to bottom-left
    connect_bottom_y = BANNER_H - 80
    ip_line       = f"IP: {SERVER_IP}"
    port_line     = f"PORT: {SERVER_PORT}"
    platform_line = "JAVA / BEDROCK"
    icon_size_connect = 40

    ip_h       = draw.textbbox((0, 0), ip_line,       font=font_reg(28))[3]
    port_h     = draw.textbbox((0, 0), port_line,     font=font_reg(28))[3]
    platform_h = draw.textbbox((0, 0), platform_line, font=font_reg(22))[3]
    hdr_bbox   = draw.textbbox((0, 0), "HOW TO CONNECT", font=font_bold(30))
    hdr_h      = hdr_bbox[3] - hdr_bbox[1]
    sep_gap    = 30

    port_y     = connect_bottom_y - port_h
    ip_y       = port_y - ip_h - 10
    platform_y = ip_y - platform_h - 14
    hdr_y      = platform_y - hdr_h - 22
    sep_y      = hdr_y - sep_gap

    draw.rectangle([PAD_LEFT, sep_y, PAD_LEFT + 380, sep_y + 2],
                   fill=(120, 120, 125, 255))
    icon_y = hdr_y + (hdr_h - icon_size_connect) // 2
    _paste_icon(base, connect_icon, (PAD_LEFT, icon_y), size=icon_size_connect)
    _draw_text_shadowed(draw, (PAD_LEFT + icon_size_connect + 12, hdr_y),
                        "HOW TO CONNECT", font_bold(30))
    _draw_text_shadowed(draw, (PAD_LEFT, platform_y), platform_line, font_reg(22), fill=COLOR_GREY)
    _draw_text_shadowed(draw, (PAD_LEFT, ip_y),   ip_line,   font_reg(28))
    _draw_text_shadowed(draw, (PAD_LEFT, port_y), port_line, font_reg(28))

    # Bottom-right stats 
    stat_right_x = BANNER_W - 80 
    stat_icon_size = 44
    icon_gap = 14

    rows = []
    if daily_peak:
        rows.append((peak_today_icon,   "TODAY'S PEAK",  f"{daily_peak.get('players', 0)} players"))
    if alltime_peak:
        rows.append((peak_alltime_icon, "ALL-TIME PEAK", f"{alltime_peak.get('players', 0)} players"))
    if avg_24h is not None:
        rows.append((avg_icon,          "24H AVERAGE",   f"{avg_24h} players"))

    row_h = 80
    start_y = BANNER_H - 50 - (row_h * len(rows))
    yy = start_y
    for icon, label, value in rows:
        vf = font_bold(33)
        lf = font_reg(19)

        # right-align: icon flush to stat_right_x, text to its left
        icon_x = stat_right_x - stat_icon_size
        text_x = icon_x - icon_gap

        vbbox = draw.textbbox((0, 0), value, font=vf)
        vw = vbbox[2] - vbbox[0]
        _draw_text_shadowed(draw, (text_x - vw, yy), value, vf)
        _paste_icon(base, icon, (icon_x, yy - 4), size=stat_icon_size)

        lbbox = draw.textbbox((0, 0), label, font=lf)
        lw = lbbox[2] - lbbox[0]
        _draw_text_shadowed(draw, (text_x - lw, yy + 38), label, lf, fill=COLOR_GREY)
        yy += row_h

    buffer = io.BytesIO()
    base.convert("RGB").save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


class StatusContainer(discord.ui.Container):
    """A thin V2 container that holds only the generated banner image.
    The image is passed in as a discord.File; the caller must also pass
    that same File to send()/edit() so Discord attaches the bytes to the
    message before the component references them via attachment://<name>."""

    def __init__(self, banner_file: discord.File, timestamp: int):
        super().__init__()

        # Full-width banner image (the generated PNG with all status info)
        self.banner = discord.ui.MediaGallery(
            discord.MediaGalleryItem(banner_file)
        )
        self.add_item(self.banner)

        # Only text remaining: live-ticking "last updated" timestamp
        self.footer = discord.ui.TextDisplay(
            f"-# {EMOJI_CLOCK} Last updated <t:{timestamp}:R>"
        )
        self.add_item(self.footer)


class StatusView(discord.ui.LayoutView):
    """LayoutView that wraps the generated banner and the Visit Website button.
    Because discord.py doesn't auto-extract discord.File objects out of
    component trees, callers must manually pass view.banner_file to
    send(files=[...]) / edit(attachments=[...])."""

    def __init__(self, banner_file: discord.File, timestamp: int):
        super().__init__(timeout=None)
        self.banner_file = banner_file   # expose so callers can attach it

        self.container = StatusContainer(banner_file, timestamp)
        self.add_item(self.container)

        self.action_row = discord.ui.ActionRow()
        website_button = discord.ui.Button(
            label="Website",
            emoji=EMOJI_WEBSITE,
            style=discord.ButtonStyle.link,
            url="https://mysticraft.xyz"
        )
        self.action_row.add_item(website_button)
        ticket_button = discord.ui.Button(
            label="Tickets",
            emoji=EMOJI_TICKET,
            style=discord.ButtonStyle.link,
            url="https://discord.gg/W735Rtgy4D"
        )
        self.action_row.add_item(ticket_button)
        tierlist_button = discord.ui.Button(
            label="Tierlist",
            emoji=EMOJI_TIERLIST,
            style=discord.ButtonStyle.link,
            url="https://tierlist.mysticraft.xyz"
        )
        self.action_row.add_item(tierlist_button)
        self.add_item(self.action_row)

    @classmethod
    async def create(cls) -> "StatusView":
        """Fetch live stats, generate the banner image, and return a ready view."""
        stats = await fetch_stats()
        png_buffer = await generate_status_banner(stats)
        banner_file = discord.File(png_buffer, filename=BANNER_OUTPUT_FILENAME)
        timestamp = int(time.time())
        return cls(banner_file, timestamp)


def _load_saved_message_id() -> int | None:
    """Reads the persisted status-panel message ID from disk, if any.
    This is what makes the auto-refresh loop survive a restart: without
    it, the bot has no reliable way to relocate the panel it posted in
    a previous process (channel.history() scanning is a fragile fallback,
    not a substitute), so the loop would just find nothing and quietly
    do nothing forever."""
    try:
        with open(STATUS_MESSAGE_STATE_PATH, "r") as f:
            data = json.load(f)
        message_id = data.get("message_id")
        return int(message_id) if message_id is not None else None
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"[Server Status] Failed to read saved message id: {e}")
        return None


def _save_message_id(message_id: int) -> None:
    """Persists the status-panel message ID to disk so the next process
    restart can find it immediately via fetch_message, instead of relying
    on in-memory state or scanning channel history."""
    try:
        with open(STATUS_MESSAGE_STATE_PATH, "w") as f:
            json.dump({"message_id": message_id}, f)
    except Exception as e:
        print(f"[Server Status] Failed to save message id: {e}")


def _message_is_status_panel(message: discord.Message, bot_user) -> bool:
    """Identifies whether a given message is our status panel: posted by us,
    carrying a LayoutView-style container with a MediaGallery attachment.
    Used only as a fallback to relocate the panel if no message ID has
    been persisted to disk yet (e.g. very first run after this change)."""
    if message.author.id != bot_user.id:
        return False
    if not message.attachments:
        return False
    return any(att.filename == BANNER_OUTPUT_FILENAME for att in message.attachments)


class Status(commands.Cog):
    def __init__(self, bot):
        self.client = bot
        self.status_message: discord.Message | None = None
        self.maintain_status.start()

    def cog_unload(self):
        self.maintain_status.cancel()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.client.user or message.author.bot or not message.guild:
            return

        if message.content.lower() == "mc!status":
            view = await StatusView.create()
            # files= must be passed alongside view= so Discord attaches the PNG
            sent_message = await message.channel.send(files=[view.banner_file], view=view)
            self.status_message = sent_message
            _save_message_id(sent_message.id)

    @tasks.loop(minutes=REFRESH_INTERVAL_MINUTES)
    async def maintain_status(self):
        """Restart-proof refresh loop. The status-panel message ID is
        persisted to disk (see _save_message_id/_load_saved_message_id),
        so after a restart this fetches that exact message directly via
        fetch_message instead of depending on in-memory state. Falls back
        to scanning recent channel history only if no ID was ever saved
        (e.g. upgrading from a version that didn't persist it yet)."""
        channel = self.client.get_channel(STATUS_CHANNEL_ID)
        if channel is None:
            try:
                channel = await self.client.fetch_channel(STATUS_CHANNEL_ID)
            except Exception as e:
                print(f"[Server Status] Couldn't fetch status channel: {e}")
                return

        if self.status_message is None:
            saved_id = _load_saved_message_id()
            if saved_id is not None:
                try:
                    self.status_message = await channel.fetch_message(saved_id)
                except discord.NotFound:
                    print(f"[Server Status] Saved message {saved_id} no longer exists, will re-search.")
                except Exception as e:
                    print(f"[Server Status] Couldn't fetch saved message {saved_id}: {e}")

        if self.status_message is None:
            try:
                async for msg in channel.history(limit=50):
                    if _message_is_status_panel(msg, self.client.user):
                        self.status_message = msg
                        _save_message_id(msg.id)
                        break
            except Exception as e:
                print(f"[Server Status] Channel history search failed: {e}")
                return

        if self.status_message is None:
            # No existing panel found in the channel yet; nothing to maintain.
            print("[Server Status] No status panel found to maintain (none saved, none in recent history).")
            return

        try:
            new_view = await StatusView.create()
            # attachments= replaces the previous file so the new PNG is used
            await self.status_message.edit(attachments=[new_view.banner_file], view=new_view)
            print(f"[Server Status] Panel refreshed at {int(time.time())}.")
        except discord.NotFound:
            # Message was deleted; clear it so the next tick re-searches.
            self.status_message = None
        except Exception as e:
            print(f"[Server Status] Auto-refresh edit failed: {e}")

    @maintain_status.before_loop
    async def before_maintain_status(self):
        await self.client.wait_until_ready()

    @maintain_status.error
    async def maintain_status_error(self, error: BaseException):
        # tasks.loop silently kills the loop forever on an unhandled
        # exception (no log, no further ticks). This is what made the
        # auto-refresh appear to "completely stop" after a restart with
        # zero console output. Log it and restart the loop so a single
        # bad tick doesn't end auto-refresh permanently.
        print(f"[Server Status] maintain_status loop crashed: {error!r}")
        if not self.maintain_status.is_running():
            self.maintain_status.restart()


async def setup(bot):
    await bot.add_cog(Status(bot))