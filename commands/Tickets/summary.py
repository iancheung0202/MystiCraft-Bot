import discord
import time
import asyncio
import re
import aiohttp

from discord import app_commands
from discord.ext import commands
from google import genai
from firebase_admin import db
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from groq import Groq

from commands.Tickets.tickets import check_for_manager

category_ids = {
    1500604708987994342: "Password Issues", # password issues
    1374959236420730890: "Server Questions",  # other questions
    1374959248806510662: "Billing Support",  # billing support
    1374959224752312362: "Appeals",  # appeal
    1374959260458287125: "Player Reports",  # player report
    1374959285716647947: "Bug Reports",  # bug report
    1374959273930391592: "Staff Reports",  # staff report
}

category_emojis = {
    "Appeals": "✍️",
    "Password Issues": "🖥️",
    "Other Questions": "❓",
    "Billing Support": "💰",
    "Player Reports": "⚠️",
    "Staff Reports": "👤",
    "Bug Reports": "🐛",
}

class Stats(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(emoji="💼", label="My Active Tickets", style=discord.ButtonStyle.green, custom_id='my_tickets')
    async def my_tickets(self, interaction: discord.Interaction, button: discord.ui.Button):
        active_tickets = []
        await interaction.response.defer(ephemeral=True, thinking=True)

        for category_id in category_ids:
            category = interaction.guild.get_channel(category_id)
            if not category or not isinstance(category, discord.CategoryChannel):
                continue

            for channel in category.channels:
                if isinstance(channel, discord.TextChannel) and not channel.name.startswith("🚫"):
                    has_participated = False
                    async for msg in channel.history(limit=None):
                        if msg.author == interaction.user and not msg.is_system():
                            has_participated = True
                            break

                    if has_participated:
                        try:
                            user_id = int(channel.topic.replace("🚫", "").strip())
                            user = interaction.guild.get_member(user_id)
                            user_mention = user.mention if user else f"Unknown User ({user_id})"
                        except:
                            user_mention = "Unknown User"

                        active_tickets.append({
                            "channel": channel,
                            "user": user_mention,
                            "created_at": channel.created_at
                        })

        if not active_tickets:
            await interaction.followup.send("You have no active tickets.", ephemeral=True)
            return

        description_lines = []
        for idx, ticket in enumerate(active_tickets, 1):
            line = (
                f"**{idx}.** {ticket['user']}'s ticket\n"
                f"Created <t:{int(ticket['created_at'].timestamp())}:R>\n"
                f"[Jump to Ticket]({ticket['channel'].jump_url})\n"
            )
            description_lines.append(line)

        embed = discord.Embed(
            title="🎫 Your Active Tickets",
            description="\n\n".join(description_lines),
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)

    @discord.ui.button(emoji="📊", label="Check my own Stats", style=discord.ButtonStyle.grey, custom_id='check_stats')
    async def check_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        ref = db.reference("/Staff Claim")
        claim_database = ref.get()
        timestamps = []
        if claim_database:
            for key, val in claim_database.items():
                if val['User ID'] == interaction.user.id:
                    timestamps = val["List"]
                    break

        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        thirty_days_ago_ts = int(thirty_days_ago.timestamp())
        this_month = sum(1 for ts in timestamps if ts > thirty_days_ago_ts)
        last_7_days = sum(1 for ts in timestamps if ts > int(time.time()) - 604800)
        last_180_days = sum(1 for ts in timestamps if ts > int(time.time()) - 15552000)
        total = len(timestamps)

        embed = discord.Embed(
            title="📊 Staff Ticket Stats",
            description=f"Here are {interaction.user.mention}'s current ticket statistics:",
            color=0x00B2FF
        )

        embed.add_field(name="🗓️ Last 30 Days", value=f"`{this_month}` tickets helped", inline=False)
        embed.add_field(name="📅 Last 7 Days", value=f"`{last_7_days}` tickets helped", inline=False)
        embed.add_field(name="🕰️ Last 180 Days", value=f"`{last_180_days}` tickets helped", inline=False)
        embed.add_field(name="📦 Total Tickets", value=f"`{total}` tickets helped", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

        
    @discord.ui.button(emoji="<:refresh:1048779043287351408>", style=discord.ButtonStyle.blurple, custom_id='refresh_stat')
    async def refresh_stat(self, interaction: discord.Interaction, button: discord.ui.Button):
        
        total_channels = 0
        total_unclaimed_channels = 0
        
        category_channel_data = {}

        for category_id in category_ids:
            category = interaction.guild.get_channel(category_id)
            if category:
                category_channel_data[category.name] = {
                    "total": 0,
                    "unclaimed": 0
                }

                for channel in category.channels:
                    total_channels += 1
                    category_channel_data[category.name]["total"] += 1
                    if "⭕" in channel.name:
                        total_unclaimed_channels += 1
                        category_channel_data[category.name]["unclaimed"] += 1
                        
        embed = discord.Embed(
            title="📊 Server Ticket Stats",
            description="Here are the current ticket statistics:",
            color=0x00B2FF
        )
        
        for category_name, data in category_channel_data.items():
            categoryName = category_name.replace("➥ ", "")
            category_id = [id for id, name in category_ids.items() if name == categoryName][0]  
            
            emoji = category_emojis.get(categoryName, "📂")  
            embed.add_field(
                name=f"{emoji} {categoryName}",
                value=f"Total: `{data['total']}`\nUnclaimed: `{data['unclaimed']}`\n⸺⸺⸺⸺",
                inline=True
            )
            
        embed.add_field(
            name=f"🎟️ **Total Tickets**",
            value=f"`{total_channels}`\n\n⸺⸺⸺⸺",
            inline=True
        )
            
        embed.add_field(
            name=f"⭕ **Total Unclaimed Tickets**",
            value=f"`{total_unclaimed_channels}`\n\n⸺⸺⸺⸺",
            inline=True
        )

        await interaction.response.edit_message(embed=embed, view=Stats())
        

async def generate(prompt):
    # ai = genai.Client(api_key="AIzaSyBlLfNh_MwQeZdvmUxSKTBWu9IEVyff0TM")
    # return ai.models.generate_content(
        # model="gemini-2.0-flash",
        # contents=prompt,
    # ).text
    client = Groq(api_key="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")

    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.1-8b-instant",
    )

    return chat_completion.choices[0].message.content

async def parse_mentions(interaction, text):
    member_cache = {}

    async def replace_users_async(text):
        result = ""
        last_end = 0
        
        for match in re.finditer(r"<@!?([0-9]+)>", text):
            uid = int(match.group(1))
            member = interaction.guild.get_member(uid)
            if not member:
                if uid in member_cache:
                    member = member_cache[uid]
                else:
                    member = await interaction.client.fetch_user(uid)
                    member_cache[uid] = member
            name = member.name if member else f"UnknownUser:{uid}"
            result += text[last_end:match.start()] + f"<span class='mention'>@{name}</span>"
            last_end = match.end()
            
        return result + text[last_end:]
    
    text = await replace_users_async(text)

    def replace_role(match):
        rid = int(match.group(1))
        role = interaction.guild.get_role(rid)
        color = f"rgb{role.color.to_rgb()}" if role and role.color else "#ccc"
        name = role.name if role else f"UnknownRole:{rid}"
        return f"<span style='color: {color};'>@{name}</span>"

    def replace_channel(match):
        cid = int(match.group(1))
        channel = interaction.guild.get_channel(cid)
        name = channel.name if channel else f"unknown-channel-{cid}"
        return f"<span class='mention'>#{name}</span>"

    def replace_command(match):
        command_name = match.group(1)
        return f"<span class='mention'>/{command_name}</span>"

    text = re.sub(r"<@&([0-9]+)>", replace_role, text)
    text = re.sub(r"<#([0-9]+)>", replace_channel, text)
    text = re.sub(r"</([A-Za-z\- ]+):[0-9]+>", replace_command, text)

    return text



def parse_markdown(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.*?)__', r'<u>\1</u>', text)
    text = re.sub(r'[\*_](.*?)[\*_]', r'<em>\1</em>', text)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    text = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', text, flags=re.DOTALL)
    text = re.sub(r'^#\s+(.*?)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+(.*?)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^###\s+(.*?)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'-#\s+(.*?)$', r'<small>\1</small>', text, flags=re.MULTILINE)
    text = re.sub(r'\|\|(.*?)\|\|', r'<span class="spoiler">\1</span>', text, flags=re.DOTALL)
    
    def replace_timestamp(match):
        timestamp = int(match.group(1))
        style = match.group(2) if match.group(2) else None
        return f"<span class='discord-timestamp' data-timestamp='{timestamp}' data-style='{style}'></span>"
    text = re.sub(r'<t:(\d+)(?::([a-zA-Z]))?>', replace_timestamp, text)
    
    lines = text.split('\n')
    in_blockquote = False
    new_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('>'):
            content = re.sub(r'^>\s*', '', stripped)
            if not in_blockquote:
                new_lines.append('<blockquote>')
                in_blockquote = True
            new_lines.append(content)
        else:
            if in_blockquote:
                new_lines.append('</blockquote>')
                in_blockquote = False
            new_lines.append(line)
    if in_blockquote:
        new_lines.append('</blockquote>')
    text = '\n'.join(new_lines)
    
    return text

async def get_transcript(interaction, channel):
    messages = [
        message async for message in channel.history(limit=None)
    ]
    try:
        user = await interaction.client.fetch_user(int(channel.topic.split(":")[2].strip()))
    except Exception:
        user = await interaction.client.fetch_user(int(channel.topic.replace("🚫", "").strip()))
        
    f = open(f"./commands/Tickets/transcript/{interaction.channel.id}.html", "w", encoding="utf-8")

    iconURL = interaction.guild.icon.url if interaction.guild.icon else "https://discord.com/assets/5d6a5e9d7d77ac29116e.png"
    f.write(f"""<Server-Info>
    Server: {interaction.guild.name} ({interaction.guild.id})
    Channel: #{interaction.channel.name} ({interaction.channel.id})
    Ticket Owner: {user} ({user.id})
    Messages: {len(messages)}
    Attachments: {sum(1 for message in messages if message.attachments)}
    
""")
    f.write(f"</Server-Info><!DOCTYPE html> <html> <head> <title>{user}</title> <script data-cfasync='false'> function formatDiscordTimestamps() {{ document.querySelectorAll('.discord-timestamp').forEach(element => {{ const timestamp = parseInt(element.dataset.timestamp); const style = element.dataset.style; const date = new Date(timestamp * 1000); let formatted; switch (style) {{ case 't': formatted = date.toLocaleTimeString('en-US', {{ hour: 'numeric', minute: '2-digit', hour12: true }}); break; case 'T': formatted = date.toLocaleTimeString('en-US', {{ hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true }}); break; case 'd': formatted = date.toLocaleDateString('en-US', {{ month: 'numeric', day: 'numeric', year: 'numeric' }}); break; case 'D': formatted = date.toLocaleDateString('en-US', {{ month: 'long', day: 'numeric', year: 'numeric' }}); break; case 'f': formatted = date.toLocaleDateString('en-US', {{ month: 'long', day: 'numeric', year: 'numeric' }}) + ' ' + date.toLocaleTimeString('en-US', {{ hour: 'numeric', minute: '2-digit', hour12: true }}); break; case 'F': formatted = date.toLocaleDateString('en-US', {{ weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }}) + ' ' + date.toLocaleTimeString('en-US', {{ hour: 'numeric', minute: '2-digit', hour12: true }}); break; case 'R': const now = new Date(); const diff = now - date; const seconds = Math.floor(diff / 1000); const intervals = {{ year: 31536000, month: 2592000, week: 604800, day: 86400, hour: 3600, minute: 60, second: 1 }}; for (const [unit, secondsInUnit] of Object.entries(intervals)) {{ const count = Math.floor(seconds / secondsInUnit); if (count >= 1) {{ formatted = `${{count}} ${{unit}}${{count !== 1 ? 's' : ''}} ago`; break; }} }} break; default: formatted = date.toLocaleDateString('en-US', {{ month: 'long', day: 'numeric', year: 'numeric' }}) + ' ' + date.toLocaleTimeString('en-US', {{ hour: 'numeric', minute: '2-digit', hour12: true }}); }} element.textContent = formatted; }}); }} function initializeSpoilers() {{ document.querySelectorAll('.spoiler').forEach(spoiler => {{ spoiler.addEventListener('click', () => {{ spoiler.classList.toggle('revealed'); }}); }}); }} window.addEventListener('DOMContentLoaded', () => {{ formatDiscordTimestamps(); initializeSpoilers(); }}); </script> <style> Server-Info {{visibility: hidden}} body {{ background-color: #2c2f33; color: white; font-family: 'Segoe UI', sans-serif; padding: 20px; }} .chat-container {{ max-width: 800px; margin: auto; }} .message {{ display: flex; gap: 12px; }} .message.grouped {{ margin-bottom: 6px; }} .message.not-grouped {{ margin: 20px 0 6px 0; }} .avatar {{ border-radius: 50%; width: 40px; height: 40px; }} .content {{ flex: 1; }} .username {{ font-weight: 600; }} .userid {{ font-size: 0.8em; color: #999; margin-left: 5px; }} .text {{ padding: 2px 0px; white-space: pre-wrap; margin-top: 2px; }} .attachment-img {{ max-width: 300px; border-radius: 6px; margin-top: 6px; }} .media-file {{ background-color: #4f545c; padding: 10px; border-radius: 8px; display: inline-flex; align-items: center; gap: 8px; color: white; margin-top: 6px; text-decoration: none; }} .embed {{ background-color: #2f3136; padding: 10px 15px; border-left: 6px solid #7289da; border-radius: 8px; margin-top: 6px; }} .embed-title {{ font-weight: bold; color: white; }} .embed-description {{ color: #ccc; font-size: 0.95em; }} .header-container {{ display: flex; gap: 20px; margin-bottom: 30px; align-items: center; }} .header-container img {{ width: 80px; border-radius: 20px; }} .header-info div {{ margin-bottom: 5px; }} .app-badge {{ display: inline-flex; align-items: center; background-color: #5a5df0; color: white; font-weight: 600; font-family: sans-serif; border-radius: 5px; padding: 2px 8px; font-size: 12px; margin-left: 4px; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2); }} .mention {{ background-color: rgb(65,68,112); color: rgb(183,195,234); padding: 2px 4px; border-radius: 3px; font-weight: 500; }} .embed-fields {{ margin-top: 10px; display: flex; flex-direction: column; gap: 10px;}} .embed-field {{ background-color: rgba(255, 255, 255, 0.05); padding: 8px 12px; border-radius: 6px; }} .embed-field-name {{ font-weight: bold; color: #fff; margin-bottom: 4px; font-size: 0.95em; }} .embed-field-value {{ color: #ccc; font-size: 0.95em; white-space: pre-wrap; }} blockquote {{ border-left: 3px solid rgb(101, 101, 108); padding-left: 10px; margin-left: 5px; color: #dcddde; }} .spoiler {{ position: relative; cursor: pointer; display: inline-block; }} .spoiler::after {{ content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(101, 101, 108); border-radius: 3px; transition: opacity 0.2s; }} .spoiler.revealed::after {{ opacity: 0; }} </style> </head> <body> <div class='chat-container'> <div class='header-container'> <img src='{iconURL}' /> <div class='header-info'> <div><strong>Server:</strong> {interaction.guild.name} ({interaction.guild.id})</div> <div><strong>Channel:</strong> #{interaction.channel.name} ({interaction.channel.id})</div> <div><strong>Ticket Owner:</strong> {user} ({user.id})</div> </div> </div>")
    
    
    from collections import defaultdict
    staff_message_counts = defaultdict(int)
    usersInvolved = []
    lastUser = None

    async with aiohttp.ClientSession() as session:
        for msg in reversed(messages):
            if msg.author != user and msg.author != interaction.client.user:
                staff_message_counts[msg.author] += 1
                if msg.author not in usersInvolved:
                    usersInvolved.append(msg.author)

            avatarURL = msg.author.avatar.url if hasattr(msg.author, 'avatar') and msg.author.avatar else "https://discord.com/assets/5d6a5e9d7d77ac29116e.png"
            userColor = msg.author.color if hasattr(msg.author, 'color') and msg.author.color != '#000000' else '#dfe0e2'
            username = msg.author.name
            userId = msg.author.id
            isBot = msg.author.bot if hasattr(msg.author, 'bot') else False

            show_user_info = lastUser != msg.author.id
            message_class = "message not-grouped" if show_user_info else "message grouped"

            f.write(f"<div class='{message_class}'>")
            f.write(f"<img class='avatar' src='{avatarURL}' />" if show_user_info else "<div style='width: 40px;'></div>")
            f.write("<div class='content'>")

            if show_user_info:
                f.write(f"<div><span class='username' style='color: {userColor};'>{username}</span>")
                if isBot:
                    f.write("<div class='app-badge' data-toggle='tooltip' title='Verified Bot'>BOT</div>")
                f.write(f"<code class='userid'>({userId})</code></div>")

            if msg.content:
                content = await parse_mentions(interaction, parse_markdown(msg.content))
                f.write(f"<div class='text'>{content}</div>")

            for attachment in msg.attachments:
                if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    f.write(f'<img class="attachment-img" src="{attachment.url}" />')
                elif attachment.filename.lower().endswith(('.mp4', '.mov', '.webm', '.mkv')):
                    f.write(f'<video class="attachment-media" controls> <source src="{attachment.url}" type="video/mp4"> Your browser doesn\'t support embedded videos. </video>')
                elif attachment.filename.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                    f.write(f'<audio class="attachment-media" controls> <source src="{attachment.url}" type="audio/mpeg"> Your browser doesn\'t support embedded audio. </audio>')
                else:
                    f.write(f"<a href='{attachment.url}' download class='media-file'> <img src='https://cdn.discordapp.com/attachments/1026904121237831700/1129787805381423265/file.png' height='20'> <span>{attachment.filename}</span> </a>")

            for embed in msg.embeds:
                if embed.title or embed.description or embed.fields:
                    embedColor = embed.color if embed.color else '#7289da'
                    f.write(f"<div class='embed' style='border-left-color: {embedColor};'>")
                    if embed.title:
                        f.write(f"<div class='embed-title'>{embed.title}</div>")
                    if embed.description:
                        description = await parse_mentions(interaction, parse_markdown(embed.description))
                        f.write(f"<div class='embed-description'>{description}</div>")
                    if embed.fields:
                        f.write("<div class='embed-fields'>")
                        for field in embed.fields:
                            f.write("<div class='embed-field'>")
                            f.write(f"<div class='embed-field-name'>{parse_markdown(field.name)}</div>")
                            f.write(f"<div class='embed-field-value'>{await parse_mentions(interaction, parse_markdown(field.value))}</div>")
                            f.write("</div>")
                        f.write("</div>")
                    f.write("</div>")

            f.write("</div></div>")
            lastUser = msg.author.id

        f.write("</div></body></html>")
        f.close()

    return (open(f"./commands/Tickets/transcript/{channel.id}.html", "r"), user, usersInvolved, staff_message_counts)

async def get_staff_ticket_embeds(interaction, stats_list, sort_by="this_month", reverse=True):
    if not stats_list:
        return [discord.Embed(title="No ticket data available.")]

    sort_map = {
        "total": "Total",
        "this_month": "Last 30 Days",
        "last_7_days": "Last 7 Days",
        "last_180_days": "Last 180 Days",
    }

    sorted_stats = sorted(stats_list, key=lambda x: x[sort_by], reverse=reverse)
    pages = []
    per_page = 3
    count = 1

    for page_start in range(0, len(sorted_stats), per_page):
        embed = discord.Embed(
            title="📊 Staff Ticket Leaderboard",
            description=f"Shows the number of tickets a staff member has helped in.\n",
            color=0x00B2FF
        )

        for entry in sorted_stats[page_start:page_start + per_page]:
            await asyncio.sleep(1)
            embed.description = (
                f"{embed.description}\n"
                f"{count}. <@{entry['user_id']}>\n"
                f"-# — **Total:** `{entry['total']}` tickets\n"
                f"-# — **Last 7 Days:** `{entry['last_7_days']}` tickets\n"
                f"-# — **Last 30 Days:** `{entry['this_month']}` tickets\n"
                f"-# — **Last 180 Days:** `{entry['last_180_days']}` tickets"
            )
            count += 1

        embed.set_footer(text=f"Page {len(pages)+1} of {(len(sorted_stats) + per_page - 1) // per_page} | Sorted by {sort_map[sort_by]} ({'high → low' if reverse else 'low → high'})")
        pages.append(embed)

    return pages

async def get_tester_ticket_embeds(interaction, stats_list, sort_by="this_month", reverse=True):
    if not stats_list:
        return [discord.Embed(title="No tester data available.")]

    sort_map = {
        "total": "Total",
        "this_month": "Last 30 Days",
        "last_7_days": "Last 7 Days",
        "last_180_days": "Last 180 Days",
    }

    sorted_stats = sorted(stats_list, key=lambda x: x[sort_by], reverse=reverse)
    pages = []
    per_page = 3
    count = 1

    for page_start in range(0, len(sorted_stats), per_page):
        embed = discord.Embed(
            title="📊 Tester Leaderboard",
            description=f"Shows the number of tests a tester has completed.\n",
            color=0x00B2FF
        )

        for entry in sorted_stats[page_start:page_start + per_page]:
            await asyncio.sleep(1)
            high_total = entry.get("high_total", 0)
            high_last_7 = entry.get("high_last_7_days", 0)
            high_this_month = entry.get("high_this_month", 0)
            high_last_180 = entry.get("high_last_180_days", 0)
            embed.description = (
                f"{embed.description}\n"
                f"{count}. <@{entry['user_id']}>\n"
                f"-# — **Total:** `{entry['total']}` tests | `{high_total}` high tests\n"
                f"-# — **Last 7 Days:** `{entry['last_7_days']}` tests | `{high_last_7}` high tests\n"
                f"-# — **Last 30 Days:** `{entry['this_month']}` tests | `{high_this_month}` high tests\n"
                f"-# — **Last 180 Days:** `{entry['last_180_days']}` tests | `{high_last_180}` high tests"
            )
            count += 1

        embed.set_footer(text=f"Page {len(pages)+1} of {(len(sorted_stats) + per_page - 1) // per_page} | Sorted by {sort_map[sort_by]} ({'high → low' if reverse else 'low → high'})")
        pages.append(embed)

    return pages


async def get_all_staff_ticket_stats():
    ref = db.reference("/Staff Claim")
    claim_database = ref.get()
    now = datetime.now()
    now_timestamp = int(time.time())
    thirty_days_ago = now - timedelta(days=30)
    thirty_days_ago_ts = int(thirty_days_ago.timestamp())

    result = []
    if claim_database:
        for val in claim_database.values():
            timestamps = val.get("List", [])
            entry = {
                "user_id": val["User ID"],
                "this_month": sum(1 for ts in timestamps if ts > thirty_days_ago_ts),
                "last_7_days": sum(1 for ts in timestamps if ts > now_timestamp - 604800),
                "last_180_days": sum(1 for ts in timestamps if ts > now_timestamp - 15552000),
                "total": len(timestamps)
            }
            result.append(entry)
    return result

async def get_all_tester_stats():
    ref = db.reference("/Tierlist Tester Stats")
    claim_database = ref.get()
    now = datetime.now()
    now_timestamp = int(time.time())
    thirty_days_ago = now - timedelta(days=30)
    thirty_days_ago_ts = int(thirty_days_ago.timestamp())

    result = []
    if claim_database:
        for user_id_str, val in claim_database.items():
            user_id = int(user_id_str)
            timestamps = val.get("timestamps", [])
            count = val.get("count", len(timestamps))
            high_timestamps = val.get("high_timestamps", [])
            high_count = val.get("high_count", len(high_timestamps))
            entry = {
                "user_id": user_id,
                "this_month": sum(1 for ts in timestamps if ts > thirty_days_ago_ts),
                "last_7_days": sum(1 for ts in timestamps if ts > now_timestamp - 604800),
                "last_180_days": sum(1 for ts in timestamps if ts > now_timestamp - 15552000),
                "total": count,
                "high_total": high_count,
                "high_this_month": sum(1 for ts in high_timestamps if ts > thirty_days_ago_ts),
                "high_last_7_days": sum(1 for ts in high_timestamps if ts > now_timestamp - 604800),
                "high_last_180_days": sum(1 for ts in high_timestamps if ts > now_timestamp - 15552000),
            }
            result.append(entry)
    return result


class StaffSortView(discord.ui.View):
    def __init__(self, pages, default="Sort by This Month", timeout=None):
        super().__init__(timeout=timeout)
        self.page = 0
        self.pages = pages

    @discord.ui.button(label="<<", style=discord.ButtonStyle.blurple)
    async def go_first(self, interaction: discord.Interaction, _):
        self.page = 0
        await interaction.response.edit_message(embed=self.pages[self.page])

    @discord.ui.button(label="<", style=discord.ButtonStyle.blurple)
    async def go_prev(self, interaction: discord.Interaction, _):
        self.page = (self.page - 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.page])

    @discord.ui.button(label=">", style=discord.ButtonStyle.blurple)
    async def go_next(self, interaction: discord.Interaction, _):
        self.page = (self.page + 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.page])

    @discord.ui.button(label=">>", style=discord.ButtonStyle.blurple)
    async def go_last(self, interaction: discord.Interaction, _):
        self.page = len(self.pages) - 1
        await interaction.response.edit_message(embed=self.pages[self.page])


@app_commands.guild_only()
class StatsCommand(commands.GroupCog, name="stats"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()
        
    @app_commands.command(name="checkup", description="Generate weekly checkups for all staff members")
    async def stats_checkup(self, interaction: discord.Interaction):
        await check_for_manager(interaction)
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        role_requirements = {
            1290409277638311947: {"mutes": 10, "bans": 3},  # Sr. Admin (no warns)
            1090330479179350037: {"mutes": 5, "bans": 3},  # Admin (no warns)
            1232591866281852959: {"mutes": 6, "bans": 2},   # Sr. Moderator (no warns)
            1066298183879229490: {"mutes": 5, "bans": 2},    # Moderator (no warns)
            1172834016412569610: {"warns": 3, "mutes": 5}   # Helper (warns + mutes, no bans)
        }

        # Get sm-logs channel
        logs_channel = interaction.guild.get_channel(1353556989497704460)
        if not logs_channel:
            return await interaction.followup.send("❌ Could not find sm-logs channel.")

        # Get last two weeks of messages
        two_weeks_ago = discord.utils.utcnow() - timedelta(days=21)
        messages = []

        try:
            async for msg in logs_channel.history(limit=2):
                if "Playtime" in msg.content:
                    messages.append(msg)
        except discord.Forbidden:
            return await interaction.followup.send("❌ I don't have permission to read the sm-logs channel.")

        if len(messages) < 2:
            print(len(messages))
            return await interaction.followup.send("❌ Not enough playtime logs found (need at least 2 weeks of data).")

        # Parse current and previous week playtimes
        current_week = await self.parse_playtime_message(messages[0].content)
        previous_week = await self.parse_playtime_message(messages[1].content)

        # Calculate differences
        playtime_diffs = {}
        for user_id, current_data in current_week.items():
            if user_id in previous_week:
                prev_data = previous_week[user_id]
                diff = {
                    'lifesteal': current_data['lifesteal'] - prev_data['lifesteal'],
                    'vanilla': current_data['vanilla'] - prev_data['vanilla'],
                    'practice': current_data['practice'] - prev_data['practice']
                }
                playtime_diffs[user_id] = diff

        # Get other stats
        ticket_counts = await self.get_ticket_counts(7)  # Last 7 days
        punishment_counts = await self.get_punishment_counts(interaction, 7)  # Last 7 days
        appeal_counts = await self.get_appeal_counts(interaction, 7)  # Last 7 days

        # Send checkups to notebook channels
        sent_count = 0
        for user_id in playtime_diffs:
            member = interaction.guild.get_member(user_id)
            if not member:
                continue

            # Find notebook channel
            notebook_channel = None
            for channel in interaction.guild.text_channels:
                if channel.topic and str(user_id) in channel.topic:
                    notebook_channel = channel
                    break

            if not notebook_channel:
                continue
                
            # Check if member meets role requirements
            warning_message = f"\n\n<:yes:1036811164891480194> You met the minimum requirement!"
            for role_id, requirements in role_requirements.items():
                if role_id in [role.id for role in member.roles]:
                    user_punishments = punishment_counts.get(user_id, {})

                    # Check each requirement based on role type
                    unmet_requirements = []

                    # Helpers: check warns and mutes
                    if role_id == 1172834016412569610:
                        if user_punishments.get('warns', 0) < requirements['warns']:
                            unmet_requirements.append(f"Warns ({user_punishments.get('warns', 0)}/{requirements['warns']})")
                        if user_punishments.get('mutes', 0) < requirements['mutes']:
                            unmet_requirements.append(f"Mutes ({user_punishments.get('mutes', 0)}/{requirements['mutes']})")

                    # Mod and above: check mutes and bans only
                    else:
                        if user_punishments.get('mutes', 0) < requirements['mutes']:
                            unmet_requirements.append(f"Mutes ({user_punishments.get('mutes', 0)}/{requirements['mutes']})")
                        if user_punishments.get('bans', 0) < requirements['bans']:
                            unmet_requirements.append(f"Bans ({user_punishments.get('bans', 0)}/{requirements['bans']})")

                    if unmet_requirements:
                        warning_message = f"\n\n⚠️ **Warning:** Did not meet minimum req for <@&{role_id}>\n" + "\n".join([f"-# - {req}" for req in unmet_requirements])
                    break

            # Calculate total playtime difference
            total_diff = (
                playtime_diffs[user_id]['lifesteal'] + 
                playtime_diffs[user_id]['vanilla'] + 
                playtime_diffs[user_id]['practice']
            )

            # Determine message format based on roles
            role_ids = [role.id for role in member.roles]
            higher_roles = [1290409277638311947, 1090330479179350037, 1232591866281852959]  # Sr. Admin, Admin, Sr. Mod

            if any(role in role_ids for role in higher_roles):
                # Sr. Mod → Admin → Sr. Admin format
                embed = discord.Embed(title="📃 Weekly Checkup", color=0x18B4F2)
                embed.description = (
                    f"> Total Logs: {punishment_counts.get(user_id, {}).get('total', 0)}\n"
                    f"> Bans: {punishment_counts.get(user_id, {}).get('bans', 0)}, "
                    f"Mutes: {punishment_counts.get(user_id, {}).get('mutes', 0)}, "
                    f"Warns: {punishment_counts.get(user_id, {}).get('warns', 0)}\n"
                    f"> Tickets resolved: {ticket_counts.get(user_id, 0)}\n"
                    f"> Appeals Resolved: {appeal_counts.get(user_id, 0)}\n"
                    f"> Playtime: {total_diff}h"
                )
            else:
                # Helper → Moderator format
                embed = discord.Embed(title="📃 Weekly Checkup", color=0x18B4F2)
                embed.description = (
                    f"> Total logs: {punishment_counts.get(user_id, {}).get('total', 0)}\n"
                    f"> Bans: {punishment_counts.get(user_id, {}).get('bans', 0)}, "
                    f"Mutes: {punishment_counts.get(user_id, {}).get('mutes', 0)}, "
                    f"Warns: {punishment_counts.get(user_id, {}).get('warns', 0)}\n"
                    f"> Tickets resolved: {ticket_counts.get(user_id, 0)}\n"
                    f"> Playtime: {total_diff}h"
                )
            embed.description += warning_message

            try:
                await notebook_channel.send(embed=embed)
                sent_count += 1
                await asyncio.sleep(1)  # Rate limiting
            except discord.Forbidden:
                continue

        await interaction.followup.send(f"✅ Weekly checkups sent to {sent_count} staff members.")

    async def parse_playtime_message(self, content):
        """Parse playtime message and return user_id -> playtime mapping"""
        playtimes = {}
        lines = content.split('\n')

        for line in lines:
            if '-->' in line and '<@' in line:
                # Extract user ID
                user_match = re.search(r'<@!?(\d+)>', line)
                if not user_match:
                    continue

                user_id = int(user_match.group(1))

                # Extract playtime data
                time_match = re.search(r'--> (.+)$', line)
                if not time_match:
                    continue

                time_parts = time_match.group(1).split('|')
                if len(time_parts) != 3:
                    continue

                # Parse each time segment
                playtime_data = {}
                modes = ['lifesteal', 'vanilla', 'practice']

                for i, part in enumerate(time_parts):
                    part = part.strip()

                    # Handle typos like "1t2h" by replacing 't' with 'd'
                    part = part.replace('t', 'd')

                    # Extract days and hours
                    days = 0
                    hours = 0

                    # Match days
                    d_match = re.search(r'(\d+)d', part)
                    if d_match:
                        days = int(d_match.group(1))

                    # Match hours
                    h_match = re.search(r'(\d+)h', part)
                    if h_match:
                        hours = int(h_match.group(1))

                    playtime_data[modes[i]] = days * 24 + hours

                playtimes[user_id] = playtime_data

        return playtimes

    async def get_ticket_counts(self, days):
        """Get ticket counts for each staff member in the last specified days"""
        ref = db.reference("/Staff Claim")
        claim_database = ref.get()
        since_timestamp = int(time.time()) - (days * 86400)

        ticket_counts = {}

        if claim_database:
            for val in claim_database.values():
                user_id = val["User ID"]
                timestamps = val.get("List", [])
                count = sum(1 for ts in timestamps if ts > since_timestamp)
                ticket_counts[user_id] = count

        return ticket_counts

    async def get_punishment_counts(self, interaction, days):
        """Get punishment counts for each staff member in the last specified days"""
        channel_id = 1155910232204128256
        channel = interaction.client.get_channel(channel_id)
        since = discord.utils.utcnow() - timedelta(days=days)

        punishments = defaultdict(lambda: {"total": 0, "bans": 0, "mutes": 0, "warns": 0})

        try:
            async for msg in channel.history(limit=None, after=since, oldest_first=False):
                if not msg.author.bot and "reason" in msg.content.lower():
                    content_lower = msg.content.lower()
                    author_id = msg.author.id

                    punishments[author_id]["total"] += 1
                    if "ban" in content_lower:
                        punishments[author_id]["bans"] += 1
                    if "mute" in content_lower:
                        punishments[author_id]["mutes"] += 1
                    if "warn" in content_lower:
                        punishments[author_id]["warns"] += 1
        except:
            pass

        return punishments

    async def get_appeal_counts(self, interaction, days):
        """Get appeal counts for each staff member in the last specified days"""
        channel_id = 1286031597845614625
        channel = interaction.client.get_channel(channel_id)
        since = discord.utils.utcnow() - timedelta(days=days)

        appeal_counts = defaultdict(int)

        try:
            async for msg in channel.history(limit=None, after=since, oldest_first=True):
                if not msg.author.bot or not msg.embeds:
                    continue

                embed = msg.embeds[0]
                if embed.title not in ("Appeal Accepted", "Appeal Rejected"):
                    continue

                try:
                    staff_id = int(embed.description.split("<@")[1].split(">")[0])
                    appeal_counts[staff_id] += 1
                except:
                    continue
        except:
            pass

        return appeal_counts
        
    @app_commands.command(name="tickets", description="Show the staff ticket stats")
    @app_commands.describe(
        sorting="Select a sorting",
    )
    @app_commands.choices(sorting=[
        app_commands.Choice(name="Sort by Total", value="total"),
        app_commands.Choice(name="Sort by Last 7 Days", value="last_7_days"),
        app_commands.Choice(name="Sort by Last 30 Days", value="this_month"),
        app_commands.Choice(name="Sort by Last 180 Days", value="last_180_days"),
    ])
    async def stats_tickets(self, interaction: discord.Interaction, sorting: app_commands.Choice[str]) -> None:
        await check_for_manager(interaction)
        await interaction.response.defer(ephemeral=True)
        stats = await get_all_staff_ticket_stats()
        pages = await get_staff_ticket_embeds(interaction, stats, sort_by=sorting.value, reverse=True)
        view = StaffSortView(pages=pages)
        await interaction.followup.send(embed=pages[0], view=view, ephemeral=True)

    @app_commands.command(name="testers", description="Show the tester stats")
    @app_commands.describe(
        sorting="Select a sorting",
    )
    @app_commands.choices(sorting=[
        app_commands.Choice(name="Sort by Total", value="total"),
        app_commands.Choice(name="Sort by Last 7 Days", value="last_7_days"),
        app_commands.Choice(name="Sort by Last 30 Days", value="this_month"),
        app_commands.Choice(name="Sort by Last 180 Days", value="last_180_days"),
    ])
    async def stats_testers(self, interaction: discord.Interaction, sorting: app_commands.Choice[str]) -> None:
        await check_for_manager(interaction)
        await interaction.response.defer(ephemeral=True)
        stats = await get_all_tester_stats()
        pages = await get_tester_ticket_embeds(interaction, stats, sort_by=sorting.value, reverse=True)
        view = StaffSortView(pages=pages)
        await interaction.followup.send(embed=pages[0], view=view, ephemeral=True)

    @app_commands.command(name="punishments", description="Count staff punishment logs in the past 7 days")
    async def stats_punishments(self, interaction: discord.Interaction):
        await check_for_manager(interaction)
        await interaction.response.defer(thinking=True, ephemeral=True)

        channel_id = 1155910232204128256
        channel = interaction.client.get_channel(channel_id)

        if not channel:
            return await interaction.followup.send("⚠️ Channel not found or I don't have access to it.")

        one_week_ago = discord.utils.utcnow() - timedelta(days=7)

        punishments = defaultdict(lambda: {"total": 0, "bans": 0, "mutes": 0, "warns": 0})

        try:
            async for msg in channel.history(limit=None, after=one_week_ago, oldest_first=False):
                if not msg.author.bot and "reason" in msg.content.lower():
                    content_lower = msg.content.lower()
                    author = msg.author

                    punishments[author]["total"] += 1
                    if "ban" in content_lower:
                        punishments[author]["bans"] += 1
                    if "mute" in content_lower:
                        punishments[author]["mutes"] += 1
                    if "warn" in content_lower:
                        punishments[author]["warns"] += 1

        except discord.Forbidden:
            return await interaction.followup.send("❌ I don't have permission to read message history in that channel.")
        except discord.HTTPException:
            return await interaction.followup.send("⚠️ Failed to fetch messages due to an API error.")

        if not punishments:
            return await interaction.followup.send("No punishments found from the last week.")

        # Sort by total punishments
        sorted_data = sorted(punishments.items(), key=lambda x: x[1]["total"], reverse=True)

        # Format leaderboard
        lines = [
            f"**{i+1}. {user.mention}** — `{data['total']} total`\n"
            f" 🔨 `{data['bans']} bans` 🔇 `{data['mutes']} mutes` ⚠️ `{data['warns']} warns`"
            for i, (user, data) in enumerate(sorted_data)
        ]
        leaderboard = "\n\n".join(lines)

        embed = discord.Embed(
            title="📊 Weekly Punishment Leaderboard",
            description=f"From <#{channel_id}> in the past 7 days:\n\n{leaderboard}",
            color=discord.Color.red()
        )
        embed.set_footer(text="Data fetched from channel history.")

        await interaction.followup.send(embed=embed)
        
    @app_commands.command(name="appeals", description="Count staff appeal actions in the last 7 days.")
    async def stats_appeals(self, interaction: discord.Interaction):
        await check_for_manager(interaction)
        await interaction.response.defer(thinking=True, ephemeral=True)

        channel_id = 1286031597845614625
        channel = interaction.client.get_channel(channel_id)

        if not channel:
            return await interaction.followup.send("⚠️ Could not find the appeal log channel.")

        one_week_ago = discord.utils.utcnow() - timedelta(days=7)
        staff_counts = defaultdict(int)

        try:
            async for msg in channel.history(limit=None, after=one_week_ago, oldest_first=True):
                if not msg.author.bot or not msg.embeds:
                    continue

                embed = msg.embeds[0]
                if embed.title not in ("Appeal Accepted", "Appeal Rejected"):
                    continue

                staff_id = int(embed.description.split("<@")[1].split(">")[0])
                staff = interaction.guild.get_member(staff_id).mention
                staff_counts[staff] += 1

        except discord.Forbidden:
            return await interaction.followup.send("❌ I don't have permission to read that channel's messages.")
        except discord.HTTPException:
            return await interaction.followup.send("⚠️ Error while fetching messages.")

        if not staff_counts:
            return await interaction.followup.send("No staff actions found in the past week.")

        sorted_counts = sorted(staff_counts.items(), key=lambda x: x[1], reverse=True)
        lines = [
            f"**{i+1}. {name}** — `{count}` actions"
            for i, (name, count) in enumerate(sorted_counts)
        ]

        leaderboard = "\n".join(lines)
        embed = discord.Embed(
            title="📅 Weekly Staff Appeal Actions",
            description=f"Appeal logs from <#{channel_id}> in the past 7 days:\n\n{leaderboard}",
            color=discord.Color.dark_gold()
        )
        embed.set_footer(text="Data fetched from channel history.")

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StatsCommand(bot))
