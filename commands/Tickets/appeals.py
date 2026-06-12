import re
import discord
import datetime
import time

from firebase_admin import db

from constants import APPEAL_LOG_CHANNEL_ID

def sanitize_firebase_key(key: str) -> str:
    key = re.sub(r"[.$#[\]/]", "", key)
    if key.startswith("."):
        key = key[1:]
    return key

class AppealModal(discord.ui.Modal):
    def __init__(self, ign, title, user):
        self.user = user
        self.shorttitle = title
        self.ign = ign
        super().__init__(title=f"Appeal {self.shorttitle} Modal")
        
        self.ignfield = discord.ui.TextInput(label="In-game name", style=discord.TextStyle.short, placeholder="", max_length=256, required=True, default=self.ign)
        self.add_item(self.ignfield)
        
        self.punishment = discord.ui.TextInput(label="Original Punishment", style=discord.TextStyle.short, placeholder="", max_length=256, required=True)
        self.add_item(self.punishment)
        
        self.determination = discord.ui.TextInput(label="Determination (Add Short Details)", style=discord.TextStyle.short, placeholder="", max_length=256, required=True, default=f"{self.shorttitle}ed")
        self.add_item(self.determination)
        
        self.info = discord.ui.TextInput(label="Additional Info", style=discord.TextStyle.paragraph, placeholder=f"Reason for {self.shorttitle} & Notes", max_length=2000, required=True)
        self.add_item(self.info)

    async def on_submit(self, interaction: discord.Interaction):
        ign = self.ignfield.value.strip()
        punishment = self.punishment.value.strip()
        determination = self.determination.value.strip()
        info = self.info.value.strip()
        appeal_log_channel = interaction.client.get_channel(APPEAL_LOG_CHANNEL_ID)
        embed = discord.Embed(
            title=f"Appeal {self.shorttitle}ed",
            description=f"**Staff:** {interaction.user.mention}\n**IGN**: `{ign}`\n**Punishment**: {punishment}\n**Determination**: {determination}\n**Info**: {info}",
            color=0xFF0000 if self.shorttitle == "Reject" else 0x00FF00
        )
        embed.set_footer(text=f"Ticket Channel ID: {interaction.channel.id}")
        msg = await appeal_log_channel.send(embed=embed)
        await interaction.response.send_message(content=f"Message sent in {msg.jump_url}", embed=embed, ephemeral=True)
        final = discord.Embed(
            description=f"Appeal {self.shorttitle}ed{'. You may reappeal in 14 days or wait out your punishment.' if self.shorttitle == 'Reject' else ''}", 
            color=0xFF0000 if self.shorttitle == 'Reject' else 0x00FF00
        )
        await interaction.channel.send(embed=final)
        await self.user.send(embed=final)


class AppealCloseTicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.red,
        custom_id="appealclose",
        emoji="🔒",
    )
    async def appealclose(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.channel.topic == None:
            t = "None"
        else:
            t = interaction.channel.topic
        if ":no_entry_sign:" in t:
            embed = discord.Embed(
                title="Ticket already closed :no_entry_sign:",
                description="This ticket is already closed.",
                color=0xFF0000,
            )
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        embed = discord.Embed(
            title="Are you sure about that?",
            description="Only moderators and administrators can reopen the ticket.",
            color=0xFF0000,
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        from commands.Tickets.tickets import ConfirmCloseTicketButtons
        await interaction.response.send_message(
            embed=embed, view=ConfirmCloseTicketButtons(), ephemeral=True
        )

    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        custom_id="appealinfo",
        emoji="🔧",
    )
    async def appealinfo(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.get_role(1373882802084511754) not in interaction.user.roles:
            return await interaction.response.send_message("You cannot click this button", ephemeral=True)

        ign, punishment_id = interaction.message.embeds[0].fields[0].value, interaction.message.embeds[0].fields[1].value
        ign_lower = ign.strip().lower()
        ign_sanitized = sanitize_firebase_key(ign_lower)

        PUNISHMENT_LOG_CHANNEL = interaction.client.get_channel(1320053091650764812)
        EVIDENCE_LOG_CHANNEL = interaction.client.get_channel(1155910232204128256)

        await interaction.response.send_message(embed=discord.Embed(
            description=f"-# <a:loading:1026905298088243240>ㅤLooking up `{ign}`. **This may take a few seconds!**", 
            color=0xFFFF00), ephemeral=True)

        db_root = db.reference("/")
        sync_ref = db_root.child("Last Punishments Sync")
        last_sync_ts = sync_ref.get()

        if last_sync_ts and last_sync_ts > 0:
            after = datetime.datetime.fromtimestamp(last_sync_ts, tz=datetime.timezone.utc)
            history_kwargs = {"after": after}
        else:
            history_kwargs = {}

        new_messages = [msg async for msg in PUNISHMENT_LOG_CHANNEL.history(limit=None, **history_kwargs)]
        if new_messages:
            sync_ref.set(int(time.time()))

        for msg in new_messages:
            if not msg.embeds:
                continue

            # If the embed has more than zero fields, Polar Punishment
            if len(msg.embeds[0].fields) > 0:
                original_ign = msg.content.split(" ")[1].strip().lower()
                action = "Banned" if "ban" in msg.content.lower() else "Unknown"
                sanitized_key = sanitize_firebase_key(original_ign)
                punishment_time = int(msg.created_at.timestamp())
                new_details = [f"**Reason**: {msg.content.split(' ')[5]}"]
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

        if not user_data:
            return await interaction.edit_original_response(content=None, embed=discord.Embed(
                description=f"No punishments found for `{ign}`.", color=0xFF0000))

        punishment_embeds = []
        sorted_entries = sorted(user_data.values(), key=lambda x: x["timestamp"], reverse=True)

        for index, entry in enumerate(sorted_entries):
            if index % 25 == 0:
                chunk_num = (index // 25) + 1
                title_suffix = f" (Part {chunk_num})" if len(user_data) > 25 else ""
                
                p_embed = discord.Embed(
                    title=f"Punishment History for {ign}{title_suffix}",
                    color=0xFFFF00
                )
                if index == 0:
                    p_embed.description = f"We found `{len(user_data)}` past punishment{'s' if len(user_data) > 1 else ''}."
                
                punishment_embeds.append(p_embed)

            timestamp = entry["timestamp"]
            evidence_links = []

            start_time = datetime.datetime.fromtimestamp(timestamp) - datetime.timedelta(hours=12)
            end_time = datetime.datetime.fromtimestamp(timestamp) + datetime.timedelta(hours=12)

            async for evidence_msg in EVIDENCE_LOG_CHANNEL.history(limit=200, after=start_time, before=end_time):
                if ign_lower in evidence_msg.content.lower():
                    evidence_links.append(evidence_msg.jump_url)
                    continue
                for embed in evidence_msg.embeds:
                    embed_text = " ".join(
                        filter(None, [
                            embed.title or '',
                            embed.description or '',
                            " ".join(f.name + f.value for f in embed.fields)
                        ])
                    ).lower()
                    if ign_lower in embed_text:
                        evidence_links.append(evidence_msg.jump_url)
                        break

            evidence_text = " | ".join(f"[Evidence {i+1}]({link})" for i, link in enumerate(evidence_links)) or "No evidence found"
            lines = [f"-# - {line}" for line in entry["details"]]
            description = f"<t:{timestamp}:R>\n" + "\n".join(lines)
            description += f"\n-# [Log]({entry['log_url']}) | {evidence_text}"

            punishment_embeds[-1].add_field(name=f"{entry['action']} - <t:{timestamp}:d>", value=description, inline=True)

        message_batches = []
        current_batch = []
        current_batch_len = 0

        for embed in punishment_embeds:
            embed_len = len(embed.title or "") + len(embed.description or "")
            for field in embed.fields:
                embed_len += len(field.name) + len(field.value)
                
            if current_batch_len + embed_len > 5500 or len(current_batch) >= 10:
                message_batches.append(current_batch)
                current_batch = []
                current_batch_len = 0
                
            current_batch.append(embed)
            current_batch_len += embed_len
            
        if current_batch:
            message_batches.append(current_batch)

        await interaction.edit_original_response(content=None, embeds=message_batches[0])

        for batch in message_batches[1:]:
            await interaction.followup.send(embeds=batch, ephemeral=True)


    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        custom_id="appealhistory",
        emoji="📖",
    )
    async def appealhistory(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.get_role(1373882802084511754) not in interaction.user.roles:
            return await interaction.response.send_message("You cannot click this button", ephemeral=True)
        
        ign, punishment_id = interaction.message.embeds[0].fields[0].value, interaction.message.embeds[0].fields[1].value
        
        await interaction.response.defer(ephemeral=True, thinking=True)
        appeal_log_channel = interaction.client.get_channel(APPEAL_LOG_CHANNEL_ID)
        
        appeal_history = []
        async for message in appeal_log_channel.history():
            # Process manual entries (text messages)
            if not message.embeds and message.content:
                entries = message.content.split('---')
                for entry in entries:
                    appeal_data = self.parse_manual_appeal(entry, ign, message.author)
                    if appeal_data:
                        appeal_history.append({
                            **appeal_data,
                            "timestamp": message.created_at,
                            "message_url": message.jump_url
                        })
                        
            # Process bot-generated embeds
            elif message.embeds:
                for embed in message.embeds:
                    appeal_data = self.parse_embed_appeal(embed, ign)
                    if appeal_data:
                        appeal_history.append({
                            **appeal_data,
                            "timestamp": message.created_at,
                            "message_url": message.jump_url
                        })
        
        appeal_history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        if not appeal_history:
            embed = discord.Embed(
                description=f"No appeal history found for `{ign}`",
                color=discord.Color.orange()
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)
        
        appeal_embeds = []
        for i, appeal in enumerate(appeal_history):
            if i % 25 == 0:
                chunk_num = (i // 25) + 1
                title_suffix = f" (Part {chunk_num})" if len(appeal_history) > 25 else ""
                
                a_embed = discord.Embed(
                    title=f"Appeal History for {ign}{title_suffix}",
                    color=discord.Color.blue()
                )
                if i == 0:
                    a_embed.description = f"We found `{len(appeal_history)}` past appeal decision{'s' if len(appeal_history) > 1 else ''}."
                
                appeal_embeds.append(a_embed)

            status_emoji = "✅" if "accept" in appeal["determination"].lower() or "accept" in appeal["info"].lower() else "❌"
            field_value = (
                f"<t:{int(appeal['timestamp'].timestamp())}:R>\n"
                f"-# **Punishment:** {appeal['punishment']}\n"
                f"-# **Decision:** {status_emoji} {appeal['determination']}\n"
                f"-# **Info:** {appeal['info']}\n"
                f"-# **Staff:** {appeal.get('staff', 'Unknown')}\n"
                f"-# [View Log Message]({appeal['message_url']})"
            )
            appeal_embeds[-1].add_field(
                name=f"Appeal #{i+1} - {appeal['timestamp'].strftime('%Y-%m-%d')}",
                value=field_value,
                inline=False
            )
        
        message_batches = []
        current_batch = []
        current_batch_len = 0

        for embed in appeal_embeds:
            embed_len = len(embed.title or "") + len(embed.description or "")
            for field in embed.fields:
                embed_len += len(field.name) + len(field.value)
                
            if current_batch_len + embed_len > 5500 or len(current_batch) >= 10:
                message_batches.append(current_batch)
                current_batch = []
                current_batch_len = 0
                
            current_batch.append(embed)
            current_batch_len += embed_len
            
        if current_batch:
            message_batches.append(current_batch)

        for batch in message_batches:
            await interaction.followup.send(embeds=batch, ephemeral=True)

    def parse_manual_appeal(self, text: str, ign: str, staff) -> dict:
        """Parse manual appeal entries from text"""
        data = {}
        ign_found = False
        
        text = text.lower().replace('>>', ':').replace(';', ':').replace('--', ':')
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        for line in lines:
            if ign.lower() in line:
                ign_found = True
                
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
        if not embed.title or "appeal" not in embed.title.lower():
            return None
            
        ign_match = False
        data = {}
        
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
        
    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        custom_id="appealaccept",
        emoji="<:yes:1036811164891480194>",
    )
    async def appealaccept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.get_role(1373882802084511754) not in interaction.user.roles:
            return await interaction.response.send_message("You cannot click this button", ephemeral=True)
        
        ign, punishment_id = interaction.message.embeds[0].fields[0].value, interaction.message.embeds[0].fields[1].value
        try:
            user = interaction.guild.get_member(int(interaction.channel.topic))
        except Exception:
            user = None
        await interaction.response.send_modal(AppealModal(ign, "Accept", user))
        
    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        custom_id="appealreject",
        emoji="<:no:1036810470860013639>",
    )
    async def appealreject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.get_role(1373882802084511754) not in interaction.user.roles:
            return await interaction.response.send_message("You cannot click this button", ephemeral=True)
        
        ign, punishment_id = interaction.message.embeds[0].fields[0].value, interaction.message.embeds[0].fields[1].value
        try:
            user = interaction.guild.get_member(int(interaction.channel.topic))
        except Exception:
            user = None
        await interaction.response.send_modal(AppealModal(ign, "Reject", user))

async def setup(bot):
    pass