import discord
import io
import aiohttp
import asyncio

from PIL import Image, ImageDraw, ImageFont
from urllib.parse import quote_plus
from discord import app_commands
from discord.ext import commands

BASE_URL = "https://tierlist.mysticraft.xyz"
FONT_PATH = "assets/MinecraftTen-VGORe.ttf" 
CANVAS_SIZE = (1000, 500) 

COLORS = {
    "bg_primary": (15, 15, 20, 255),
    "bg_secondary": (25, 25, 35, 255),
    "text_white": (255, 255, 255, 255),
    "text_gray": (140, 140, 150, 255),
    "text_highlight": (255, 255, 255, 255),
}

DISCORD_ICON_URL = "https://pngimg.com/d/discord_PNG3.png"

TIER_GRADIENTS = {
    1: ["#d4af37", "#ffdf80", "#aa8c2c"], # Gold
    2: ["#9ca3af", "#e2e8f0", "#64748b"], # Silver
    3: ["#a0522d", "#cd853f", "#8b4513"], # Bronze
    4: ["#991b1b", "#f87171", "#7f1d1d"], # Red
    5: ["#334155", "#64748b", "#1e293b"], # Slate/Dark
}

TITLE_META = {
    "Combat Grandmaster": {"icon": "images/grandmaster.png?v=1", "color": "#fb5a24"},
    "Combat Master":      {"icon": "images/master.png?v=1",      "color": "#fb8124"},
    "Combat Ace":         {"icon": "images/ace.png?v=1",          "color": "#efb044"},
    "Combat Specialist":  {"icon": "images/specialist.png?v=1",   "color": "#c087fc"},
    "Combat Cadet":       {"icon": "images/cadet.png?v=1",        "color": "#d8b4fe"},
    "Combat Novice":      {"icon": "images/novice.png?v=1",       "color": "#e9d5ff"},
    "Newbie":             {"icon": "images/newbie.png?v=1",        "color": "#9ca3af"}
}

GAMEMODE_CONFIG = {
    "NPOT":    {"icon": "images/npot.png"},
    "DPOT":    {"icon": "images/dpot.png"},
    "SMP":     {"icon": "images/smp.png"},
    "SWORD":   {"icon": "images/sword.png"},
    "CRYSTAL": {"icon": "images/crystal.png"},
    "AXE":     {"icon": "images/axe.png"},
    "MACE":    {"icon": "images/mace.png"},
    "UHC":     {"icon": "images/uhc.png"}
}

# --- HELPER FUNCTIONS ---

def load_font(size: int):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()

def hex_to_rgb(hex_val):
    hex_val = hex_val.lstrip('#')
    return tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))

async def fetch_image(session, url: str, resize: tuple = None) -> Image.Image:
    if not url: return None
    try:
        async with session.get(url, timeout=5) as resp:
            if resp.status == 200:
                data = await resp.read()
                img = Image.open(io.BytesIO(data)).convert("RGBA")
                if resize:
                    img = img.resize(resize, Image.Resampling.LANCZOS)
                return img
    except Exception:
        return None
    return None

def draw_rounded_rect(draw, box, radius, fill, outline=None, width=0):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def create_gradient_border(size, colors, border_width=2, radius=10):
    w, h = size
    mask = Image.new("L", (w, h), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
    draw_mask.rounded_rectangle((border_width, border_width, w-border_width, h-border_width), radius=radius-border_width, fill=0)
    
    c1 = hex_to_rgb(colors[0])
    c2 = hex_to_rgb(colors[1])
    c3 = hex_to_rgb(colors[2])
    
    gradient = Image.new("RGBA", (w, h), (0,0,0,0))
    draw_g = ImageDraw.Draw(gradient)
    
    steps = w + h
    for i in range(steps):
        t = i / steps
        if t < 0.5:
            ratio = t * 2
            r = int(c1[0] + (c2[0] - c1[0]) * ratio)
            g = int(c1[1] + (c2[1] - c1[1]) * ratio)
            b = int(c1[2] + (c2[2] - c1[2]) * ratio)
        else:
            ratio = (t - 0.5) * 2
            r = int(c2[0] + (c3[0] - c2[0]) * ratio)
            g = int(c2[1] + (c3[1] - c2[1]) * ratio)
            b = int(c2[2] + (c3[2] - c2[2]) * ratio)
        draw_g.line([(0, i), (i, 0)], fill=(r,g,b,255), width=2)

    result = Image.new("RGBA", (w, h), (0,0,0,0))
    result.paste(gradient, (0,0), mask)
    return result

def get_text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def draw_dynamic_text(draw, pos, text, max_width, initial_font_size, fill):
    font_size = initial_font_size
    font = load_font(font_size)
    w, h = get_text_size(draw, text, font)
    while w > max_width and font_size > 10:
        font_size -= 2
        font = load_font(font_size)
        w, h = get_text_size(draw, text, font)
    draw.text(pos, text, font=font, fill=fill)
    return h

# --- CORE LOGIC ---

async def generate_tier_card(discord_username: str, player_name: str, data: dict) -> bytes:
    img = Image.new("RGBA", CANVAS_SIZE, COLORS["bg_primary"])
    draw = ImageDraw.Draw(img)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        # 1. Gather URLs
        avatar_url = f"https://render.crafty.gg/3d/bust/{quote_plus(player_name)}"
        
        # Determine Title Icon URL
        title = data.get('title') or 'Newbie'
        title_meta = TITLE_META.get(title, TITLE_META['Newbie'])
        title_icon_url = f"{BASE_URL}/{title_meta.get('icon', '')}"

        # 2. Start Async Downloads
        icon_tasks = {mode: fetch_image(session, f"{BASE_URL}/{cfg['icon']}", resize=(40, 40)) 
                  for mode, cfg in GAMEMODE_CONFIG.items()}
        
        avatar_task = fetch_image(session, avatar_url, resize=(180, 180))
        title_icon_task = fetch_image(session, title_icon_url, resize=(20, 20))
        discord_icon_task = fetch_image(session, DISCORD_ICON_URL, resize=(28, 28))
        
        # Top-right site logo
        site_logo_task = fetch_image(session, f"{BASE_URL}/images/logo.png", resize=(64, 64))

        # 3. Await All
        avatar_img = await avatar_task
        title_icon_img = await title_icon_task
        discord_icon_img = await discord_icon_task
        site_logo_img = await site_logo_task
        mode_icons = await asyncio.gather(*icon_tasks.values())
        mode_icons_map = dict(zip(icon_tasks.keys(), mode_icons))

        # --- DRAWING ---
        padding = 40
        
        # A. Avatar
        avatar_x, avatar_y = padding, padding
        draw.ellipse((avatar_x, avatar_y, avatar_x+180, avatar_y+180), fill=COLORS["bg_secondary"])
        if avatar_img:
            mask = Image.new("L", (180, 180), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 180, 180), fill=255)
            img.paste(avatar_img, (avatar_x, avatar_y), mask)
        
        # B. User Info
        info_x = avatar_x + 180 + 30
        curr_y = padding + 10
        
        # Name
        name_h = draw_dynamic_text(draw, (info_x, curr_y), player_name, 600, 48, COLORS["text_white"])
        curr_y += name_h + 12

        # Title Pill
        title_hex = title_meta.get('color', '#9ca3af')
        try:
            r, g, b = tuple(int(title_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            title_color = (r, g, b, 255)
        except:
            title_color = COLORS["text_gray"]

        title_font = load_font(20)
        t_text = title.upper()
        tw, th = get_text_size(draw, t_text, title_font)
        
        # Calculate Pill Width (Icon + Gap + Text)
        pill_height = th + 14
        icon_w = 20 if title_icon_img else 0
        icon_gap = 8 if title_icon_img else 0
        pill_width = 30 + icon_w + icon_gap + tw

        # Draw Pill
        draw_rounded_rect(draw, (info_x, curr_y, info_x + pill_width, curr_y + pill_height), 8, COLORS["bg_secondary"], outline=title_color, width=2)
        
        # Draw Title Icon & Text
        content_x = info_x + 15
        if title_icon_img:
            img.paste(title_icon_img, (content_x, curr_y + (pill_height - 20)//2), title_icon_img)
            content_x += 20 + icon_gap
        
        draw.text((content_x, curr_y + 5), t_text, font=title_font, fill=title_color)
        
        # Region Pill (Right of Title)
        region = data.get('region') or 'Unknown'
        region_x = info_x + pill_width + 15
        region_font = load_font(20)
        rw, rh = get_text_size(draw, region, region_font)
        draw_rounded_rect(draw, (region_x, curr_y, region_x + rw + 30, curr_y + pill_height), 8, (40, 44, 52, 255))
        draw.text((region_x + 15, curr_y + 5), region, font=region_font, fill=COLORS["text_gray"])

        curr_y += pill_height + 20

        # C. Stats (Multi-color)
        stats_font = load_font(22)
        points = str(data.get('total_points', 0))
        rank_num = f"#{data.get('global_rank', 'Unranked')}"
        
        # Draw "Points:" (Gray)
        draw.text((info_x, curr_y), "Points: ", font=stats_font, fill=COLORS["text_gray"])
        w_p_lbl, _ = get_text_size(draw, "Points: ", stats_font)
        
        # Draw Value (White)
        draw.text((info_x + w_p_lbl, curr_y), points, font=stats_font, fill=COLORS["text_white"])
        w_p_val, _ = get_text_size(draw, points, stats_font)
        
        # Draw Separator
        sep_x = info_x + w_p_lbl + w_p_val + 20
        draw.text((sep_x, curr_y), "•", font=stats_font, fill=COLORS["text_gray"])
        
        # Draw "Global Rank:" (Gray)
        r_lbl_x = sep_x + 20
        draw.text((r_lbl_x, curr_y), "Global Rank: ", font=stats_font, fill=COLORS["text_gray"])
        w_r_lbl, _ = get_text_size(draw, "Global Rank: ", stats_font)
        
        # Draw Value (White)
        draw.text((r_lbl_x + w_r_lbl, curr_y), rank_num, font=stats_font, fill=COLORS["text_white"])
        
        curr_y += 40 # Space for Discord line

        # D. Discord Username
        disc_icon_size = 28
        disc_font = load_font(20)
        # Draw Icon
        if discord_icon_img:
            img.paste(discord_icon_img, (info_x, curr_y + 2), discord_icon_img)
            disc_text_x = info_x + disc_icon_size + 8
        else:
            disc_text_x = info_x

        # Draw @username (moved 8px down for vertical alignment with icon)
        draw.text((disc_text_x, curr_y + 7), f"{discord_username}", font=disc_font, fill=(114, 137, 218, 255)) # Blurple-ish

        # Top-right logo + watermark text
        try:
            if site_logo_img:
                logo_w, logo_h = site_logo_img.size
                logo_x = CANVAS_SIZE[0] - padding - logo_w
                logo_y = padding
                img.paste(site_logo_img, (logo_x, logo_y), site_logo_img)

                # watermark_text = "MystiCraft Tierlist"
                # wm_font = load_font(16)
                # tw, th = get_text_size(draw, watermark_text, wm_font)
                # # Draw the watermark text to the left of the logo with subtle opacity
                # text_x = logo_x - 10 - tw
                # text_y = logo_y + (logo_h - th) // 2
                # draw.text((text_x, text_y), watermark_text, font=wm_font, fill=(255, 255, 255, 120))
        except Exception:
            pass

        # E. Badges Grid
        grid_start_y = 280
        grid_start_x = padding
        badge_w, badge_h = 210, 80 
        gap_x, gap_y = 20, 20
        
        ranks = data.get('ranks', {})
        modes = list(GAMEMODE_CONFIG.keys())

        for i, mode in enumerate(modes):
            col = i % 4
            row = i // 4
            bx = grid_start_x + col * (badge_w + gap_x)
            by = grid_start_y + row * (badge_h + gap_y)

            rank_data = ranks.get(mode)
            
            # Draw Background (Uniform for Ranked and Unranked now)
            draw_rounded_rect(draw, (bx, by, bx + badge_w, by + badge_h), 10, COLORS["bg_secondary"])

            if not rank_data:
                # UNRANKED: No border, Faded Icon, Dash
                icon = mode_icons_map.get(mode)
                if icon:
                    icon_faded = icon.copy()
                    icon_faded.putalpha(100) 
                    img.paste(icon_faded, (bx + 15, by + 20), icon_faded)

                draw.text((bx + 70, by + 15), mode, font=load_font(14), fill=COLORS["text_gray"])
                draw.text((bx + 70, by + 35), "-", font=load_font(24), fill=COLORS["text_gray"])
            else:
                # RANKED: Gradient Border, Bright Icon, Value
                t_tier = 0
                label = ""
                if isinstance(rank_data, dict):
                    t_type = rank_data.get('type', '')
                    t_tier = rank_data.get('tier', 0)
                    label = f"{t_type}{t_tier}"
                else:
                    label = str(rank_data)

                # Gradient Border
                grad_colors = TIER_GRADIENTS.get(t_tier, TIER_GRADIENTS[5])
                border_img = create_gradient_border((badge_w, badge_h), grad_colors, border_width=3, radius=10)
                img.paste(border_img, (bx, by), border_img)

                # Icon
                icon = mode_icons_map.get(mode)
                if icon:
                    img.paste(icon, (bx + 15, by + 20), icon)

                # Labels
                font_rank_val = load_font(26) 
                draw.text((bx + 70, by + 15), mode, font=load_font(14), fill=COLORS["text_gray"])
                draw.text((bx + 70, by + 35), label, font=font_rank_val, fill=COLORS["text_highlight"])

    out = io.BytesIO()
    img.save(out, format='PNG')
    out.seek(0)
    return out.read()


class TierCmd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tier", description="Show a linked user's tier profile card")
    @app_commands.describe(
        user="Select a user other than you to view",
    )
    async def tier(self, interaction: discord.Interaction, user: discord.Member = None):
        await interaction.response.defer()
        if user is None:
            user = interaction.user

        player_name = None
        try:
            async with self.bot.tllink_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SHOW TABLES")
                    tables = await cursor.fetchall()
                    link_table = tables[0][0] if tables else "mystilinking"

                    await cursor.execute(
                        f"SELECT player_name FROM {link_table} WHERE discord_id = %s",
                        (str(user.id),)
                    )
                    row = await cursor.fetchone()
                    if row:
                        player_name = row[0]
        except Exception as e:
            return await interaction.followup.send(f"❌ Database error: {e}", ephemeral=True)

        if not player_name:
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> Could not find linked account in database.", 
                ephemeral=True
            )

        api_url = f"{BASE_URL}/api/player/{quote_plus(player_name)}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                if resp.status != 200:
                    return await interaction.followup.send(f"❌ Failed to fetch API data (Status: {resp.status})", ephemeral=True)
                data = await resp.json()

        try:
            img_bytes = await generate_tier_card(user.name, player_name, data)
            file = discord.File(io.BytesIO(img_bytes), filename=f"{player_name}_tier.png")
            
            view = discord.ui.View()
            url = f"https://tierlist.mysticraft.xyz/?player={quote_plus(player_name)}"
            view.add_item(discord.ui.Button(label="Open on web", url=url, style=discord.ButtonStyle.link))

            await interaction.followup.send(file=file, view=view)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ Image generation failed: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TierCmd(bot))