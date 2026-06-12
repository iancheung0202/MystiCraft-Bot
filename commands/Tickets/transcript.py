import re
import aiohttp

from groq import Groq


async def generate(prompt):
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

async def setup(bot):
    pass