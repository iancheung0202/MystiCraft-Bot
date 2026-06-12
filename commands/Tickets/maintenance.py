import discord
import datetime
import asyncio
import re
import os
import hashlib

from discord.ext import commands
from firebase_admin import db
from discord.ui import Button, View

from constants import CATEGORY_IDS, FLAG_CHANNEL_IDS, SERVER_IDS

async def delete_flags(guild, channel_id):
    """Delete all flagged messages referencing this ticket from flag channels"""
    flag_channel_ids = []
    for role_name, channels in FLAG_CHANNEL_IDS.items():
        if isinstance(channels, dict) and guild.id in channels:
            flag_channel_ids.append(channels[guild.id])

    if not flag_channel_ids:
        return
    
    for flag_channel_id in flag_channel_ids:
        try:
            flag_channel = guild.get_channel(flag_channel_id)
            if not flag_channel:
                continue
            
            async for message in flag_channel.history(limit=100):
                try:
                    if message.embeds:
                        for embed in message.embeds:
                            if embed.description and f"<#{channel_id}>" in embed.description:
                                await message.delete()
                                break
                            if embed.footer and embed.footer.text and f"Ticket ID: {channel_id}" in embed.footer.text:
                                await message.delete()
                                break
                except Exception:
                    pass
        except Exception:
            pass


async def close_ticket(interaction):
    """Reusable ticket close routine."""
    channel = interaction.channel
    guild = interaction.guild
    closer = interaction.user

    left = False
    userObject = None
    try:
        user = guild.get_member(int(channel.topic)).name
        userObject = guild.get_member(int(channel.topic))
    except Exception:
        user = "[LEFT SERVER]"
        left = True

    ref = db.reference("/Tickets")
    tickets = ref.get()
    LOGCHANNEL_ID = None
    if tickets:
        for key, value in tickets.items():
            if value.get("Server ID") == guild.id:
                LOGCHANNEL_ID = value.get("Log Channel ID")
                break
    log = guild.get_channel(LOGCHANNEL_ID) if LOGCHANNEL_ID else None
    
    await delete_flags(guild, channel.id)
    
    from commands.Tickets.transcript import get_transcript
    f, user, usersInvolved, staff_message_counts = await get_transcript(interaction, channel)

    if left == False and userObject is not None:
        embed = discord.Embed(
            title="Ticket closed",
            description=f"Ticket created by {userObject.mention} is closed by {closer.mention}",
            color=0xE44D41,
        )
        try:
            embed.set_author(name=f"{userObject.name}", icon_url=userObject.avatar.url)
        except Exception:
            embed.set_author(name=f"{userObject.name}")
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        embed.set_footer(text=f"Channel ID: {channel.id}")
    else:
        embed = discord.Embed(
            title="Ticket closed",
            description=f"Ticket created by a member who has left the server is closed by {closer.mention}",
            color=0xE44D41,
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)

    staff_list = "\n".join(f"- {u.mention} `({staff_message_counts[u]})`" for u in usersInvolved) if usersInvolved else "`None`"
    embed.add_field(name="Staff Involved", value=staff_list, inline=True)

    try:
        ticket_topic = [message async for message in channel.history(oldest_first=True)][0].embeds[0].title
    except Exception:
        ticket_topic = "Others"
    
    embed.add_field(name="Ticket Topic", value=ticket_topic)

    log_message = None
    if log:
        try:
            log_message = await log.send(embed=embed, file=discord.File(f"./commands/Tickets/transcript/{channel.id}.html"))
        except Exception:
            log_message = None

        try:
            with open(f"./commands/Tickets/transcript/{channel.id}.html", "rb") as f:
                file_content = f.read()
            checksum = hashlib.sha256(file_content + str(log.id).encode()).hexdigest()[:20]
            token = f"{log.id}-{log_message.id}-{checksum}"
            url = f"https://ticket.mysticraft.xyz/logs/{token}"
            embed.add_field(name="Transcript Link", value=url, inline=False)
            if log_message:
                await log_message.edit(embed=embed)
        except Exception:
            pass

    try:
        os.remove(f"./commands/Tickets/transcript/{channel.id}.html")
    except Exception:
        pass

    transcript_button = Button(
        style=discord.ButtonStyle.link,
        label="Transcript Link",
        emoji="📜",
        url=(url if log and log_message else "https://ticket.mysticraft.xyz/")
    )
    user_view = View()
    user_view.add_item(transcript_button)

    embed = discord.Embed(
        title="Ticket closed",
        description=f"Your ticket in **{guild.name}** is now closed. \n-# Visit https://ticket.mysticraft.xyz/ to see your previous tickets",
        color=0xE44D41,
    )
    embed.add_field(name="Ticket Topic", value=ticket_topic)
    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    embed.set_footer(text=f"You can always create a new ticket for additional assistance!")
    try:
        user_member = userObject if userObject is not None else None
        if user_member:
            await user_member.send(embed=embed, view=user_view)
            await channel.set_permissions(user_member, send_messages=False, read_messages=False, attach_files=False)
    except Exception:
        pass

    try:
        await channel.send(embed=discord.Embed(title=f"Ticket Closed", description=f"Ticket is closed by {closer.mention} and is no longer visible to the member {user.mention if not left else 'Unknown'}", color=0xE44D41))
    except Exception:
        pass

    embed = discord.Embed(title="", description="""```STAFF CONTROLS PANEL```""", color=0xE44D41)
    try:
        from commands.Tickets.tickets import TicketAdminButtons
        view = TicketAdminButtons()
        view.add_item(transcript_button)
        await channel.send(embed=embed, view=view)
    except Exception:
        try:
            await channel.send(embed=embed)
        except Exception:
            pass

    try:
        await channel.edit(topic=f":no_entry_sign: {channel.topic}")
    except Exception:
        pass

    try:
        newName = f"🚫{channel.name[1:]}"
        await channel.edit(topic=f"🚫 {userObject.id if userObject is not None else 'Unknown member'}", name=newName)
    except Exception:
        pass
    
    try:
        ref = db.reference(f"/Ticket Mention Violations/{channel.id}")
        ref.delete()
    except Exception as e:
        print(f"[Mention Enforcement] Failed to reset violations for channel {channel.id}: {e}")


async def ticket_maintenance_cycle(bot):
    """Run a single maintenance cycle scanning ticket channels."""
    now = datetime.datetime.now(datetime.timezone.utc)
    now_ts = int(now.timestamp())

    try:
        all_states = await asyncio.to_thread(db.reference("/Ticket Auto Notify").get) or {}
    except Exception as e:
        print(f"Ticket maintenance failed to fetch states: {e}")
        all_states = {}

    updates = {}

    for guild in bot.guilds:
        for channel in guild.text_channels:
            try:
                if not channel.category or channel.category.id not in [cat_id for server_id, categories in CATEGORY_IDS.items() if server_id != "application" for cat_id in categories.values()]:
                    continue
                if not channel.topic:
                    continue

                topic = channel.topic.strip()
                m = re.search(r"(\d{6,})", topic)
                if not m:
                    continue
                try:
                    ticket_user_id = int(m.group(1))
                except Exception:
                    continue

                msgs = [m async for m in channel.history(limit=200)]
                if not msgs:
                    continue

                last_nonbot = None
                for msg in msgs:
                    if not msg.author.bot:
                        last_nonbot = msg
                        break
                if not last_nonbot:
                    continue

                last_author_id = last_nonbot.author.id
                age = (datetime.datetime.now(datetime.timezone.utc) - last_nonbot.created_at.replace(tzinfo=datetime.timezone.utc)).total_seconds()
                state = all_states.get(str(channel.id), {})

                if last_author_id != ticket_user_id and not last_nonbot.author.bot:
                    try:
                        if channel.name and channel.name[0] in ("⚠️", "⭕"):
                            await channel.edit(name=("🟡" + channel.name[1:]))
                    except Exception:
                        pass

                    if age > 24 * 3600:
                        last_notify = state.get("last_notify_ts")
                        if not last_notify:
                            try:
                                user = bot.get_user(ticket_user_id) or await bot.fetch_user(ticket_user_id)
                                embed = discord.Embed(
                                    title="⚠️ Automatic Notification ⚠️",
                                    description=(
                                        f"We haven't heard from you in a while regarding the ticket you previously opened in **{channel.guild.name}**. To prevent your ticket from being automatically closed, please **respond within 24 hours.**\n\n"
                                        "If you no longer need assistance or your issue has been resolved, **please still let us know in the ticket** so we can help close the ticket."
                                    ),
                                    color=0xE44D41,
                                )
                                embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
                                try:
                                    button = Button(style=discord.ButtonStyle.link, label="Head over to your ticket", emoji="🎫", url=f"https://discord.com/channels/{channel.guild.id}/{channel.id}")
                                    view = View()
                                    view.add_item(button)
                                    await user.send(embed=embed, view=view)
                                except Exception:
                                    pass
                                try:
                                    await channel.send(f"<@{ticket_user_id}> This is an auto reminder to please respond within 24 hours to avoid your ticket being closed.")
                                except Exception:
                                    pass
                                updates[f"{channel.id}/last_notify_ts"] = now_ts
                            except Exception:
                                pass
                        elif now_ts - int(last_notify) >= 24 * 3600:
                            if not state.get("auto_closed"):
                                try:
                                    from types import SimpleNamespace
                                    closer = channel.guild.get_member(bot.user.id) or bot.user
                                    interaction_like = SimpleNamespace(guild=channel.guild, channel=channel, user=closer, client=bot)
                                    await close_ticket(interaction_like)
                                except Exception:
                                    pass
                                finally:
                                    updates[f"{channel.id}/auto_closed"] = True
                                    updates[f"{channel.id}/auto_closed_ts"] = now_ts
                    else:
                        if "last_notify_ts" in state and state["last_notify_ts"] is not None:
                            updates[f"{channel.id}/last_notify_ts"] = None
                    
                    if state.get("auto_closed"):
                        auto_closed_ts = state.get("auto_closed_ts")
                        if auto_closed_ts and not state.get("auto_deleted"):
                            if now_ts - int(auto_closed_ts) >= 6 * 3600:
                                try:
                                    await channel.delete(reason="Auto-delete after 6 hours of auto-close")
                                    updates[f"{channel.id}/auto_deleted"] = True
                                except Exception as e:
                                    print(f"Ticket maintenance failed to auto-delete channel {channel.id}: {e}")

                else:
                    if "last_notify_ts" in state and state["last_notify_ts"] is not None:
                        updates[f"{channel.id}/last_notify_ts"] = None
                    if age > 24 * 3600:
                        try:
                            if channel.name and channel.name.startswith("🟡"):
                                remainder = channel.name[1:] if len(channel.name) > 1 else channel.name
                                await channel.edit(name=("⚠️" + remainder))
                                updates[f"{channel.id}/warned_ts"] = now_ts
                        except Exception:
                            pass
                    else:
                        try:
                            if channel.name and channel.name.startswith("⚠️"):
                                await channel.edit(name=("🟡" + channel.name[1:]))
                                updates[f"{channel.id}/warned_ts"] = None
                        except Exception:
                            pass

            except Exception as e:
                print(f"Ticket maintenance error on channel {getattr(channel,'id',None)}: {e}")

    if updates:
        try:
            await asyncio.to_thread(db.reference("/Ticket Auto Notify").update, updates)
        except Exception as e:
            print(f"Ticket maintenance failed to apply updates: {e}")


async def ticket_maintenance_task(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            await ticket_maintenance_cycle(bot)
        except Exception as e:
            print(f"Ticket maintenance task cycle error: {e}")
        await asyncio.sleep(30 * 60)  # 30 minutes


class MentionViolation(commands.Cog):
    def __init__(self, bot):
        self.client = bot

    def is_ticket_channel(self, channel: discord.TextChannel) -> bool:
        if hasattr(channel, 'category'):
            if channel.category is None:
                return False
            else:
                return channel.category.id in [cat_id for server_id, categories in CATEGORY_IDS.items() if server_id != "application" for cat_id in categories.values()]
        return False

    async def get_mention_violation_count(self, channel_id: int) -> int:
        try:
            ref = db.reference(f"/Ticket Mention Violations/{channel_id}")
            count = ref.get()
            return count if count is not None else 0
        except Exception as e:
            print(f"[Mention Enforcement] Error getting violation count for {channel_id}: {e}")
            return 0

    async def increment_mention_violations(self, channel_id: int) -> int:
        try:
            ref = db.reference(f"/Ticket Mention Violations/{channel_id}")
            current = await self.get_mention_violation_count(channel_id)
            new_count = current + 1
            ref.set(new_count)
            return new_count
        except Exception as e:
            print(f"[Mention Enforcement] Error incrementing violations for {channel_id}: {e}")
            return 0

    async def reset_mention_violations(self, channel_id: int) -> None:
        try:
            ref = db.reference(f"/Ticket Mention Violations/{channel_id}")
            ref.delete()
        except Exception as e:
            print(f"[Mention Enforcement] Error resetting violations for {channel_id}: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Enforce no-mention policy in ticket channels."""
        if message.author == self.client.user or message.author.bot:
            return
        if not self.is_ticket_channel(message.channel):
            return
        if message.channel.topic is None or message.channel.topic.strip() == "":
            return
        if ":no_entry_sign:" in message.channel.topic or "🚫" in message.channel.topic:
            return
        try:
            topic_parts = message.channel.topic.split()
            ticket_author_id = None
            for part in topic_parts:
                if part.isdigit():
                    ticket_author_id = int(part)
                    break
            if ticket_author_id is None:
                return
        except (ValueError, IndexError, AttributeError):
            return
        from commands.Tickets.tickets import check_for_staff
        if message.author.id != ticket_author_id or check_for_staff(message.guild, message.author):
            return
        has_mentions = bool(re.search(r'<@!?\d+>|<@&\d+>|<#\d+>', message.content))
        if not has_mentions:
            return
        violation_count = await self.get_mention_violation_count(message.channel.id)
        try:
            await message.delete()
        except Exception as e:
            print(f"[Mention Enforcement] Failed to delete message: {e}")
            return
        if violation_count == 0:
            embed = discord.Embed(title="⚠️ No Mentioning in Tickets", description="Please do not mention staff members in tickets. Staff will assist you when available.", color=0xFF0000)
            embed.set_footer(text="This is your first warning. Further violations will result in a timeout and ticket closure.")
            try:
                await message.channel.send(embed=embed)
            except Exception as e:
                print(f"[Mention Enforcement] Failed to send first warning: {e}")
            await self.increment_mention_violations(message.channel.id)
        elif violation_count == 1:
            embed = discord.Embed(title="⚠️ Final Warning", description=f"You have been warned once already. Mentioning staff members is not allowed in tickets. You are now being timed out for 1 hour.", color=0xFFAA00)
            embed.set_footer(text="This is your final warning before ticket closure.")
            try:
                await message.channel.send(embed=embed)
            except Exception as e:
                print(f"[Mention Enforcement] Failed to send second warning: {e}")
            try:
                timeout_duration = datetime.timedelta(hours=1)
                await message.author.timeout(timeout_duration, reason="Mentioning in ticket channel after warning")
            except Exception as e:
                print(f"[Mention Enforcement] Failed to timeout user {message.author.id}: {e}")
            await self.increment_mention_violations(message.channel.id)
        else:
            embed = discord.Embed(title="🚫 Ticket Closed", description="You have violated the no-mention rule after multiple warnings. This ticket will now be closed.", color=0xFF0000)
            try:
                await message.channel.send(embed=embed)
            except Exception as e:
                print(f"[Mention Enforcement] Failed to send closure notice: {e}")
            class FakeInteraction:
                def __init__(self, channel, user, guild, client):
                    self.channel = channel
                    self.user = user
                    self.guild = guild
                    self.client = client
            fake_interaction = FakeInteraction(message.channel, message.author, message.guild, self.client)
            try:
                await close_ticket(fake_interaction)
            except Exception as e:
                print(f"[Mention Enforcement] Failed to close ticket: {e}")
            await self.reset_mention_violations(message.channel.id)


class EmoteMaintenance(commands.Cog):
    def __init__(self, bot):
        self.client = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.client.user or message.author.bot == True or not message.guild:
            return
                
        if hasattr(message.channel, 'category') and message.channel.category.id in (list(CATEGORY_IDS.get(SERVER_IDS["support"], {}).values()) + list(CATEGORY_IDS.get(SERVER_IDS["tierlist"], {}).values())):
            try:
                if message.channel.name.startswith("🚫"):
                    return

                user = message.guild.get_member(int(message.channel.topic.replace("🚫", "").strip()))
                if message.author == user or message.author.bot:
                    return
                
                if message.channel.name.startswith("⭕") or message.channel.name.startswith("⭕️") or message.channel.name.startswith("⚠️"): # Support server + Tierlist server
                    newName = f"🟡{message.channel.name[1:]}"
                    await message.channel.edit(topic=message.channel.topic, name=newName)

            except Exception as e:
                pass


async def setup(bot):
    await bot.add_cog(MentionViolation(bot))
    await bot.add_cog(EmoteMaintenance(bot))
    bot.loop.create_task(ticket_maintenance_task(bot))