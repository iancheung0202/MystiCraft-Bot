import discord
import datetime

from discord import app_commands
from discord.ext import commands
from firebase_admin import db
from discord.ui import Button

from constants import APPEAL_LOG_CHANNEL_ID


class AddPunishment(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(
            style=discord.ButtonStyle.link,
            label="Log New Punishment",
            url=f"https://discord.com/channels/1064570075304177734/1155910232204128256",
        ))
        
        
class History(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        
    def parse_manual_appeal(self, text: str, ign: str, staff) -> dict:
        """Parse manual appeal entries from text"""
        data = {}
        ign_found = False
        
        # Normalize text for easier parsing
        text = text.lower().replace('>>', ':').replace(';', ':').replace('--', ':')
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        for line in lines:
            # Check for IGN match (case-insensitive)
            if ign.lower() in line:
                ign_found = True
                
            # Extract key-value pairs
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if 'ign' in key:
                    data['ign'] = value
                elif 'punishment' in key:
                    data['punishment'] = value.title()
                elif 'determination' in key or 'decision' in key:
                    data['determination'] = value.title()
                elif 'info' in key or 'notes' in key:
                    data['info'] = value
                data['staff'] = staff.mention
        
        return data if ign_found and data else None

    def parse_embed_appeal(self, embed: discord.Embed, ign: str) -> dict:
        """Parse bot-generated appeal embeds"""
        # Check if it's an appeal embed
        if not embed.title or "appeal" not in embed.title.lower():
            return None
            
        # Check if IGN matches
        ign_match = False
        data = {}
        
        # Extract fields from description
        if embed.description:
            lines = embed.description[2:].split('\n')
            for line in lines:
                if '**' in line:
                    key, value = line.split('**:', 1) if '**:' in line else line.split('**', 1)
                    key = key.replace('**', '').strip().lower()
                    value = value.strip()
                    
                    if 'staff' in key:
                        data['staff'] = value
                    if 'ign' in key and ign.lower() in value.lower():
                        ign_match = True
                    if 'punishment' in key:
                        data['punishment'] = value
                    if 'determination' in key:
                        data['determination'] = value
                    if 'info' in key:
                        data['info'] = value
        
        return data if ign_match else None

    @app_commands.command(name="history", description="View a player's in-game punishment history")
    @app_commands.describe(
        ign="The player's IGN",
    )
    async def history(
        self,
        interaction: discord.Interaction,
        ign: str,
    ) -> None:
        if interaction.guild.id != 1064570075304177734:
            return await interaction.response.send_message(":x: Only staff can use this command in the staff server.", ephemeral=True)
        ign_lower = ign.strip().lower()
        from commands.Tickets.appeals import sanitize_firebase_key
        ign_sanitized = sanitize_firebase_key(ign_lower)

        PUNISHMENT_LOG_CHANNEL = interaction.client.get_channel(1320053091650764812)
        EVIDENCE_LOG_CHANNEL = interaction.client.get_channel(1155910232204128256)

        await interaction.response.send_message(embed=discord.Embed(description=f"-# <a:loading:1026905298088243240>ㅤLooking up `{ign}`. **This may take a few seconds!**", color=0xFFFF00))

        db_root = db.reference("/")
        sync_ref = db_root.child("Last Punishments Sync")
        last_sync_ts = sync_ref.get()

        if last_sync_ts and last_sync_ts > 0:
            after = datetime.datetime.fromtimestamp(last_sync_ts, tz=datetime.timezone.utc)
            history_kwargs = {"after": after}
        else:
            history_kwargs = {}

        new_messages = [
            msg async for msg in PUNISHMENT_LOG_CHANNEL.history(limit=None, **history_kwargs)
        ]

        if new_messages:
            latest_timestamp = max(int(msg.created_at.timestamp()) for msg in new_messages)
            sync_ref.set(latest_timestamp)

        for msg in new_messages:
            if not msg.embeds:
                continue

            # If the embed has more than zero fields, Polar Punishment
            if len(msg.embeds[0].fields) > 0:
                original_ign = msg.content.split(" ")[1].strip().lower()
                action = "Banned" if "ban" in msg.content.lower() else "Unknown"
                sanitized_key = sanitize_firebase_key(original_ign)
                punishment_time = int(msg.created_at.timestamp())
                new_details = [f"**Reason**: {msg.content.split(" ")[5]}"]
            else:
                embed = msg.embeds[0]
                desc = embed.description
                try:
                    original_ign = desc.split(" ")[0].strip().lower()
                    sanitized_key = sanitize_firebase_key(original_ign)
                except Exception:
                    continue

                punishment_time = int(msg.created_at.timestamp())
                action = embed.title or "Unknown"
                details = embed.description.split("\n")
                new_details = []

                for line in details:
                    if '•' in line and ':' in line:
                        try:
                            line = line.replace('•', '-')
                            key, value = line.split(':', 1)
                            dash, label = key.split('-', 1)
                            formatted = f"**{label.strip()}**: {value.strip()}"
                            new_details.append(formatted)
                        except Exception:
                            continue

            punishment_entry = {
                "ign": original_ign,
                "action": action,
                "timestamp": punishment_time,
                "log_url": msg.jump_url,
                "details": new_details
            }

            user_ref = db.reference(f"Punishments/{sanitized_key}")
            user_ref.push(punishment_entry)

        punishments_ref = db.reference(f"Punishments/{ign_sanitized}")
        user_data = punishments_ref.get()

        message_batches = []
        current_batch = []
        current_batch_len = 0
        
        def add_embed_to_batch(embed):
            nonlocal current_batch, current_batch_len, message_batches
            embed_len = len(embed.title or "") + len(embed.description or "")
            for field in embed.fields:
                embed_len += len(field.name) + len(field.value)
                
            if current_batch_len + embed_len > 5500 or len(current_batch) >= 10:
                message_batches.append(current_batch)
                current_batch = []
                current_batch_len = 0
            
            current_batch.append(embed)
            current_batch_len += embed_len

        if not user_data:
            p_embed = discord.Embed(
                title=f"Punishment History for {ign}",
                description=f"No previous punishments found for `{ign}`.", 
                color=0xFF0000
            )
            add_embed_to_batch(p_embed)
        else:
            sorted_entries = sorted(user_data.values(), key=lambda x: x["timestamp"], reverse=True)
            
            p_embed = discord.Embed(title=f"Punishment History for {ign}", color=0xFFFF00)
            p_embed.description = f"We found `{len(user_data)}` past punishment{'s' if len(user_data) > 1 else ''}."
            
            for entry in sorted_entries:
                if len(p_embed.fields) >= 20:
                    add_embed_to_batch(p_embed)
                    p_embed = discord.Embed(title=f"Punishment History for {ign} (Continued)", color=0xFFFF00)

                timestamp = entry["timestamp"]
                evidence_links = []

                start_time = datetime.datetime.fromtimestamp(timestamp) - datetime.timedelta(hours=12)
                end_time = datetime.datetime.fromtimestamp(timestamp) + datetime.timedelta(hours=12)

                async for evidence_msg in EVIDENCE_LOG_CHANNEL.history(limit=200, after=start_time, before=end_time):
                    if ign_lower in evidence_msg.content.lower():
                        evidence_links.append(evidence_msg.jump_url)
                        continue
                    for embed in evidence_msg.embeds:
                        embed_text = " ".join(filter(None, [embed.title or '', embed.description or '', " ".join(f.name + f.value for f in embed.fields)])).lower()
                        if ign_lower in embed_text:
                            evidence_links.append(evidence_msg.jump_url)
                            break

                evidence_text = " | ".join(f"[Evidence {i+1}]({link})" for i, link in enumerate(evidence_links)) or "No evidence found"
                lines = [f"-# - {line}" for line in entry["details"]]
                description = f"<t:{timestamp}:R>\n" + "\n".join(lines)
                description += f"\n-# [Log]({entry['log_url']}) | {evidence_text}"

                p_embed.add_field(name=f"{entry['action']} - <t:{timestamp}:d>", value=description, inline=True)
            
            if p_embed.fields or p_embed.description:
                add_embed_to_batch(p_embed)

        APPEAL_LOG_CHANNEL = interaction.client.get_channel(APPEAL_LOG_CHANNEL_ID)
        appeal_history = []
        
        async for message in APPEAL_LOG_CHANNEL.history():
            if not message.embeds and message.content:
                entries = message.content.split('---')
                for entry in entries:
                    appeal_data = self.parse_manual_appeal(entry, ign, message.author)
                    if appeal_data:
                        appeal_history.append({**appeal_data, "timestamp": message.created_at, "message_url": message.jump_url})
            elif message.embeds:
                for embed in message.embeds:
                    appeal_data = self.parse_embed_appeal(embed, ign)
                    if appeal_data:
                        appeal_history.append({**appeal_data, "timestamp": message.created_at, "message_url": message.jump_url})
        
        appeal_history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        if not appeal_history:
            a_embed = discord.Embed(
                title=f"Appeal History for {ign}",
                description=f"No appeal history found for `{ign}`",
                color=discord.Color.orange()
            )
            add_embed_to_batch(a_embed)
        else:
            a_embed = discord.Embed(title=f"Appeal History for {ign}", color=discord.Color.blue())
            a_embed.description = f"We found `{len(appeal_history)}` past appeal decision{'s' if len(appeal_history) > 1 else ''}."
            
            for i, appeal in enumerate(appeal_history):
                if len(a_embed.fields) >= 20:
                    add_embed_to_batch(a_embed)
                    a_embed = discord.Embed(title=f"Appeal History for {ign} (Continued)", color=discord.Color.blue())

                status_emoji = "✅" if "accept" in appeal["determination"].lower() or "accept" in appeal["info"].lower() else "❌"
                field_value = (
                    f"<t:{int(appeal['timestamp'].timestamp())}:R>\n"
                    f"-# **Punishment:** {appeal['punishment']}\n"
                    f"-# **Decision:** {status_emoji} {appeal['determination']}\n"
                    f"-# **Info:** {appeal['info']}\n"
                    f"-# **Staff:** {appeal.get('staff', 'Unknown')}\n"
                    f"-# [View Log Message]({appeal['message_url']})"
                )
                a_embed.add_field(
                    name=f"Appeal #{i+1} - {appeal['timestamp'].strftime('%Y-%m-%d')}",
                    value=field_value,
                    inline=False
                )
            
            if a_embed.fields or a_embed.description:
                add_embed_to_batch(a_embed)

        if current_batch:
            message_batches.append(current_batch)

        if not message_batches:
            fallback = discord.Embed(description="No data gathered.", color=discord.Color.greyple())
            message_batches = [[fallback]]

        first_view = AddPunishment() if len(message_batches) == 1 else None
        await interaction.edit_original_response(content=None, embeds=message_batches[0], view=first_view)

        for batch in message_batches[1:]:
            await interaction.followup.send(embeds=batch, ephemeral=False)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(History(bot))
