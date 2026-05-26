from commands.Tickets.tier import COLORS, load_font, fetch_image, draw_rounded_rect, DISCORD_ICON_URL
import discord
import io
import aiohttp
import datetime
import time

from firebase_admin import db
from PIL import Image, ImageDraw, ImageFont
from urllib.parse import quote_plus
from discord import app_commands
from discord.ext import commands
import discord.ui

CANVAS_SIZE = (1000, 300) 

def get_text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

# --- CORE LOGIC ---

async def generate_rep_card(discord_username: str, player_name: str | None, stats: dict) -> bytes:
    """Generate a tester rep card. `stats` is a dict containing counts and breakdowns."""
    img = Image.new("RGBA", CANVAS_SIZE, COLORS["bg_primary"])
    draw = ImageDraw.Draw(img)
    
    # Layout Constants
    padding = 40
    avatar_size = 120 # Slightly smaller to give more room
    
    # --- ASSET FETCHING ---
    avatar_url = f"https://render.crafty.gg/3d/bust/{quote_plus(player_name)}" if player_name else None
    avatar_img = None
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # URL Constants
    # rank_icon_url = "https://art.pixilart.com/699fb46a495e3d1.png"
    rank_icon_url = "https://media.forgecdn.net/avatars/thumbnails/996/649/256/256/638513665912639588.png"

    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = []
        if avatar_url:
            avatar_img = await fetch_image(session, avatar_url, resize=(avatar_size, avatar_size))
        
        rank_icon_img = await fetch_image(session, rank_icon_url, resize=(48, 48))
        discord_icon_img = await fetch_image(session, DISCORD_ICON_URL, resize=(24, 24))

    # --- DRAW AVATAR (Top Left) ---
    avatar_x, avatar_y = padding, padding
    
    # Avatar Background Circle
    draw.ellipse((avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size), fill=COLORS["bg_secondary"])
    
    if avatar_img:
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
        img.paste(avatar_img, (avatar_x, avatar_y), mask)

    # --- HEADER INFO (Right of Avatar) ---
    info_x = avatar_x + avatar_size + 30
    curr_y = padding + 10
    
    # 1. Main Display Name
    name_font = load_font(36)
    display_name = player_name if player_name else discord_username
    draw.text((info_x, curr_y), display_name, font=name_font, fill=COLORS["text_white"])
    curr_y += 45

    # 2. Discord Handle
    disc_font = load_font(18)
    if discord_icon_img:
        img.paste(discord_icon_img, (info_x, curr_y + 2), discord_icon_img)
        draw.text((info_x + 32, curr_y + 4), discord_username, font=disc_font, fill=(114, 137, 218, 255))
    else:
        draw.text((info_x, curr_y + 4), discord_username, font=disc_font, fill=(114, 137, 218, 255))
    curr_y += 40

    # 3. Lifetime Stats (Under Discord Name)
    # Grouping Normal and High tests here looks cleaner than splitting them across the screen
    stats_font = load_font(16)
    normal_v = stats.get("total", 0)
    high_v = stats.get("high_total", 0)
    
    # Draw "Lifetime:" label
    draw.text((info_x, curr_y), "Lifetime:", font=stats_font, fill=COLORS["text_gray"])
    
    # Draw Normal count
    offset_x = info_x + 80
    draw.text((offset_x, curr_y), f"Normal: {normal_v}", font=stats_font, fill=COLORS["text_white"])
    
    # Draw High count
    offset_x += 120
    draw.text((offset_x, curr_y), f"High: {high_v}", font=stats_font, fill=COLORS["text_highlight"])

    # --- TOP RIGHT BOXES (Rep & Rank) ---
    # These stay at the top right but are aligned strictly
    box_w = 200
    box_h = 85
    box_gap = 15
    
    right_anchor = CANVAS_SIZE[0] - padding
    rank_box_x = right_anchor - box_w
    rep_box_x = rank_box_x - box_w - box_gap
    box_y = padding + 10

    # Calculate Rep Total
    rep_total = normal_v + (2 * high_v)
    rank_val = stats.get("rep_rank", "—")

    # Load rep tiers image and crop the appropriate icon
    tiers_img = Image.open("assets/rep_tiers.png")
    thresholds = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 120, 140, 160, 190, 220, 250, 290, 330, 370, 420, 470, 500]
    tier_names = [
        "Leather I", "Leather II", "Leather III",
        "Iron I", "Iron II", "Iron III",
        "Gold I", "Gold II", "Gold III",
        "Diamond I", "Diamond II", "Diamond III",
        "Emerald I", "Emerald II", "Emerald III",
        "Amethyst I", "Amethyst II", "Amethyst III",
        "Crimson I", "Crimson II", "Crimson III",
        "Crown Tier"
    ]
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
    tier_index = 0
    for i, thresh in enumerate(thresholds):
        if rep_total >= thresh:
            tier_index = i
        else:
            break
    x = (tier_index % 5) * 100
    y = (tier_index // 5) * 100
    rep_icon_img = tiers_img.crop((x, y, x + 100, y + 100)).resize((48, 48))

    # Helper to draw a stat box with centered label and value
    def draw_stat_box(x, y, icon, label, value):
        draw_rounded_rect(draw, (x, y, x + box_w, y + box_h), 12, COLORS["bg_secondary"])
        
        # 1. Define the content area
        # If there's an icon, the text area starts after the icon (roughly x + 60)
        icon_space = 60 if icon else 15
        text_area_center_x = x + icon_space + (box_w - icon_space) // 2
        
        # 2. Draw Icon
        if icon:
            img.paste(icon, (x + 12, y + (box_h - 48) // 2), icon)
        
        # 3. Label (Centered in text area)
        s_font = load_font(14)
        lw, lh = get_text_size(draw, label, s_font)
        # Center X = Area Center - (Label Width / 2)
        draw.text((text_area_center_x - (lw // 2), y + 15), label, font=s_font, fill=COLORS["text_gray"])
        
        # 4. Value (Centered under Label)
        b_font = load_font(32)
        val_str = str(value)
        vw, vh = get_text_size(draw, val_str, b_font)
        # Center X = Area Center - (Value Width / 2)
        draw.text((text_area_center_x - (vw // 2), y + 40), val_str, font=b_font, fill=COLORS["text_white"])

    draw_stat_box(rep_box_x, box_y, rep_icon_img, "Reputation", rep_total)
    draw_stat_box(rank_box_x, box_y, rank_icon_img, "Server Rank", rank_val)

    # --- BOTTOM ROW: BREAKDOWN BOXES ---
    # We create a new row below the avatar for the 3 period stats
    
    periods = [
        ("Last 7 Days", "last_7_days", "high_last_7_days"),
        ("Last 30 Days", "this_month", "high_this_month"),
        ("Last 180 Days", "last_180_days", "high_last_180_days"),
    ]

    # Calculate dynamic width to fit full width minus padding
    row_y = padding + avatar_size + 20 # Start below avatar
    total_width_avail = CANVAS_SIZE[0] - (padding * 2)
    gap = 20
    # width = (total - 2 gaps) / 3
    p_box_w = (total_width_avail - (gap * 2)) // 3
    p_box_h = 70
    
    current_x = padding

    for title, key_norm, key_high in periods:
        draw_rounded_rect(draw, (current_x, row_y, current_x + p_box_w, row_y + p_box_h), 12, COLORS["bg_secondary"])
        
        # Title
        t_font = load_font(15)
        draw.text((current_x + 15, row_y + 10), title, font=t_font, fill=COLORS["text_gray"])
        
        # Values
        norm_val = stats.get(key_norm, 0)
        high_val = stats.get(key_high, 0)
        
        v_font = load_font(20)
        
        # Draw Normal
        draw.text((current_x + 15, row_y + 35), f"Normal: {norm_val}", font=v_font, fill=COLORS["text_white"])
        
        # Draw High (aligned to right side of its box)
        high_str = f"High: {high_val}"
        hw, _ = get_text_size(draw, high_str, v_font)
        draw.text((current_x + p_box_w - 15 - hw, row_y + 35), high_str, font=v_font, fill=COLORS["text_highlight"])
        
        current_x += p_box_w + gap

    # --- FOOTER ---
    footer_font = load_font(12)
    footer_base = "1 normal test = 1 rep   •   1 high test = 2 rep"
    footer_tier = f" | {tier_names[tier_index]}"
    fw_base, _ = get_text_size(draw, footer_base, footer_font)
    fw_tier, _ = get_text_size(draw, footer_tier, footer_font)
    total_w = fw_base + fw_tier
    start_x = (CANVAS_SIZE[0] - total_w) / 2
    draw.text((start_x, CANVAS_SIZE[1] - 25), footer_base, font=footer_font, fill=COLORS["text_gray"])
    draw.text((start_x + fw_base, CANVAS_SIZE[1] - 25), footer_tier, font=footer_font, fill=tier_colors[tier_index])

    out = io.BytesIO()
    img.save(out, format='PNG')
    out.seek(0)
    return out.read()


class TopRepView(discord.ui.View):
    def __init__(self, pages, user_rank, total_pages):
        super().__init__(timeout=300)
        self.pages = pages
        self.current_page = 0
        self.user_rank = user_rank
        self.total_pages = total_pages

    @discord.ui.button(label="<<", style=discord.ButtonStyle.blurple)
    async def first_page(self, interaction: discord.Interaction, button):
        self.current_page = 0
        embed = self.pages[self.current_page]
        embed.set_footer(text=f"Page {self.current_page+1} of {self.total_pages} | Your rank: {self.user_rank} (Page {self.get_page_for_rank()})")
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="<", style=discord.ButtonStyle.blurple)
    async def prev_page(self, interaction: discord.Interaction, button):
        if self.current_page > 0:
            self.current_page -= 1
        embed = self.pages[self.current_page]
        embed.set_footer(text=f"Page {self.current_page+1} of {self.total_pages} | Your rank: {self.user_rank} (Page {self.get_page_for_rank()})")
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label=">", style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction: discord.Interaction, button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
        embed = self.pages[self.current_page]
        embed.set_footer(text=f"Page {self.current_page+1} of {self.total_pages} | Your rank: {self.get_page_for_rank()})")
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label=">>", style=discord.ButtonStyle.blurple)
    async def last_page(self, interaction: discord.Interaction, button):
        self.current_page = self.total_pages - 1
        embed = self.pages[self.current_page]
        embed.set_footer(text=f"Page {self.current_page+1} of {self.total_pages} | Your rank: {self.user_rank} (Page {self.get_page_for_rank()})")
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Jump to Page", style=discord.ButtonStyle.green)
    async def jump_to_page(self, interaction: discord.Interaction, button):
        modal = JumpToPageModal(self)
        await interaction.response.send_modal(modal)

    def get_page_for_rank(self):
        if self.user_rank == 0:
            return 1
        return (self.user_rank - 1) // 10 + 1


class JumpToPageModal(discord.ui.Modal, title="Jump to Page"):
    page_input = discord.ui.TextInput(label="Enter page number", placeholder="1", required=True, min_length=1, max_length=5)

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            page = int(self.page_input.value) - 1
            if 0 <= page < self.view.total_pages:
                self.view.current_page = page
                embed = self.view.pages[page]
                embed.set_footer(text=f"Page {page+1} of {self.view.total_pages} | Your rank: {self.view.user_rank} (Page {self.view.get_page_for_rank()})")
                await interaction.response.edit_message(embed=embed)
            else:
                await interaction.response.send_message("Invalid page number.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Please enter a valid number.", ephemeral=True)


class RepCmd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rep", description="Show a tester rep card for a user")
    @app_commands.describe(user="The Discord user to view (defaults to you)")
    async def rep(self, interaction: discord.Interaction, user: discord.Member = None):
        await interaction.response.defer()
        target = user or interaction.user

        # Fetch linked player name if available
        player_name = None
        try:
            async with self.bot.tllink_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SHOW TABLES")
                    tables = await cursor.fetchall()
                    link_table = tables[0][0] if tables else "mystilinking"
                    await cursor.execute(f"SELECT player_name FROM {link_table} WHERE discord_id = %s", (str(target.id),))
                    row = await cursor.fetchone()
                    if row:
                        player_name = row[0]
        except Exception:
            player_name = None

        # Fetch tester stats from Firebase
        ref = db.reference("/Tierlist Tester Stats")
        node = ref.child(str(target.id)).get() or {}
        now_ts = int(time.time())
        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        thirty_days_ago_ts = int(thirty_days_ago.timestamp())

        # Compute live rep leaderboard rank
        try:
            all_nodes = ref.get() or {}
            scores = []
            for uid_str, v in all_nodes.items():
                try:
                    uid = int(uid_str)
                except Exception:
                    continue
                if interaction.guild.get_member(uid) is None:
                    continue
                cnt = v.get("count", len(v.get("timestamps", [])))
                high_cnt = v.get("high_count", len(v.get("high_timestamps", [])))
                total_rep_score = cnt + (2 * high_cnt)
                scores.append((uid, total_rep_score))
            scores.sort(key=lambda x: x[1], reverse=True)
            rank = None
            for idx, (uid, sc) in enumerate(scores, start=1):
                if uid == target.id:
                    rank = idx
                    break
            if rank is None and scores:
                rank = len(scores) + 1
                print("User not found in scores, assigned rank at end.")
            elif rank is None:
                rank = "—"
                print("No scores found for rank computation.")
        except Exception as e:
            print(f"Error computing rank: {e}")
            rank = "—"

        stats = {
            "total": node.get("count", len(node.get("timestamps", []))),
            "high_total": node.get("high_count", len(node.get("high_timestamps", []))),
            "last_7_days": sum(1 for ts in node.get("timestamps", []) if ts > now_ts - 604800),
            "this_month": sum(1 for ts in node.get("timestamps", []) if ts > thirty_days_ago_ts),
            "last_180_days": sum(1 for ts in node.get("timestamps", []) if ts > now_ts - 15552000),
            "high_last_7_days": sum(1 for ts in node.get("high_timestamps", []) if ts > now_ts - 604800),
            "high_this_month": sum(1 for ts in node.get("high_timestamps", []) if ts > thirty_days_ago_ts),
            "high_last_180_days": sum(1 for ts in node.get("high_timestamps", []) if ts > now_ts - 15552000),
            "rep_rank": rank,
        }

        img_bytes = await generate_rep_card(target.name, player_name, stats)
        file = discord.File(io.BytesIO(img_bytes), filename=f"{target.name}_rep.png")
        await interaction.followup.send(file=file)

    @app_commands.command(name="toprep", description="Show the reputation leaderboard")
    async def toprep(self, interaction: discord.Interaction):
        await interaction.response.defer()
        ref = db.reference("/Tierlist Tester Stats")
        data = ref.get() or {}
        reps = []
        for uid_str, v in data.items():
            try:
                uid = int(uid_str)
            except:
                continue
            if interaction.guild.get_member(uid) is None:
                continue
            normal = v.get("count", len(v.get("timestamps", [])))
            high = v.get("high_count", len(v.get("high_timestamps", [])))
            rep = normal + 2 * high
            reps.append((uid, rep))
        reps.sort(key=lambda x: x[1], reverse=True)
        # Find user rank
        user_rank = None
        for idx, (uid, _) in enumerate(reps, start=1):
            if uid == interaction.user.id:
                user_rank = idx
                break
        if user_rank is None and reps:
            user_rank = len(reps) + 1
        elif not reps:
            user_rank = 0
        # Create pages
        pages = []
        per_page = 10
        for page_start in range(0, len(reps), per_page):
            embed = discord.Embed(
                title="Reputation Leaderboard",
                description="> **Climb the leaderboard to become among the top MystiCraft Tierlist testers!** Use </rep:1467286878435938406> to check a user's reputation.\n\n",
                color=0x00B2FF
            )
            for i, (uid, rep) in enumerate(reps[page_start:page_start + per_page], start=page_start + 1):
                embed.description += f"{i}. <@{uid}> - `{rep}` rep\n"
            pages.append(embed)
        total_pages = len(pages)
        if not pages:
            embed = discord.Embed(title="No data available.")
            pages = [embed]
            total_pages = 1
        view = TopRepView(pages, user_rank, total_pages)
        embed = pages[0]
        embed.set_footer(text=f"Page 1 of {total_pages} | Your rank: {user_rank} (Page {view.get_page_for_rank()})")
        await interaction.followup.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(RepCmd(bot))