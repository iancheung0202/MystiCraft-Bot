import discord
import datetime
import asyncio
import emoji
import re

from firebase_admin import db
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View

from constants import ROLE_IDS, SERVER_IDS, CATEGORY_IDS, TICKET_COOLDOWNS, FLAG_CHANNEL_IDS, SUPPORT_ROLE_IDS, LOG_CHANNEL_IDS, COOLDOWN_BYPASS_USER_IDS
from commands.Tickets.maintenance import delete_flags, close_ticket


async def check_for_manager(interaction):
    server_config = ROLE_IDS.get(interaction.guild.id)
    roles_map = server_config["roles"]
    allowed_keys = ["owner", "executive", "manager"]
    allowed_role_ids = {int(roles_map[key]) for key in allowed_keys if key in roles_map}
    user_role_ids = {role.id for role in interaction.user.roles}
    if not user_role_ids.intersection(allowed_role_ids):
        return await interaction.response.send_message("This action can only be done by Manager+ only.", ephemeral=True)

def check_for_staff(guild: discord.Guild, member: discord.Member) -> bool:
    if guild.id not in ROLE_IDS:
        return False
        
    allowed_role_ids = set(ROLE_IDS[guild.id]["roles"].values())
    member_role_ids = {role.id for role in member.roles}
    return not member_role_ids.isdisjoint(allowed_role_ids)

def get_ticket_owner_id(channel):
    try:
        if channel.topic and channel.topic.strip().isdigit():
            return int(channel.topic.strip())
        match = re.search(r"(\d{6,})", str(channel.topic or ""))
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return None


class Select(discord.ui.Select):
    def __init__(self, placeholder, options):
        # options=options
        super().__init__(placeholder=placeholder, max_values=1, min_values=1, options=options, custom_id="ticketcreation")

    async def callback(self, interaction: discord.Interaction):
        selectedValue = self.values[0]
        embed = discord.Embed(
            title="Confirm Ticket",
            description=f"Are you sure you want to make a ticket about **{selectedValue}**?",
            colour=0x4F545B,
        )
        embed.add_field(name="<:warn:1459986909911842846> Review These Guidelines First", value="-# - Be respectful and civil. **Rudeness or impatience won't speed things up.**\n-# - **You are forbidden to ping any staff.** They will help you as soon as they're available.")
        try:
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url)
        except Exception:
            embed.set_author(name=interaction.user.name)
        embed.set_footer(icon_url=interaction.guild.icon.url, text=f"{interaction.guild.name} • #{interaction.channel.name}",)
        await interaction.response.send_message(embed=embed, view=CreateTicketButtonView(), ephemeral=True)


class SelectView(discord.ui.View):
    def __init__(self, placeholder=None, options=None, *, timeout=None):
        super().__init__(timeout=timeout)
        self.add_item(Select(placeholder, options))


class CreateTicketButton(discord.ui.Button):
    def __init__(self, title, emoji, color):
        super().__init__(label=title, emoji=emoji, style=color, custom_id="create")

    async def callback(self, interaction: discord.Interaction):
        try:
            embed = interaction.message.embeds[0]
            category_raw = embed.description.split('**')[1].strip()
            category_name = category_raw.lower()
        except Exception:
            category_raw = "Unknown"
            category_name = "unknown"
            
        guild_id = interaction.guild.id
        category_id = None
        log_channel_id = None
        
        if guild_id in CATEGORY_IDS and category_name in CATEGORY_IDS[guild_id]:
            category_id = CATEGORY_IDS[guild_id][category_name]
            log_channel_id = LOG_CHANNEL_IDS.get(guild_id)
        else:
            ref = db.reference("/Tickets").get() or {} # Database fallback if not in constants
            for key, value in ref.items():
                if value.get("Server ID") == guild_id:
                    category_id = value.get("Category ID")
                    log_channel_id = value.get("Log Channel ID")
                    break

        if not category_id or not log_channel_id:
            error_embed = discord.Embed(
                title="Ticket not enabled!",
                description="This server does not have a ticket category or a log channel. Please ask the server admin to use </ticket setup:1033188985587109910> to setup tickets!",
                colour=0xFF0000,
            )
            error_embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            return await interaction.response.send_message(embed=error_embed, ephemeral=True)

        category_channel = interaction.guild.get_channel(category_id)

        if category_channel:
            for channel in category_channel.channels:
                if get_ticket_owner_id(channel) == interaction.user.id:
                    return await interaction.response.send_message(
                        content=f"You already had your ticket created at <#{channel.id}>.",
                        ephemeral=True,
                    )
                
        if db.reference(f"/Ticket Blacklist/{interaction.user.id}").get():
            return await interaction.response.send_message("<:no:1036810470860013639> You are blacklisted from creating tickets.", ephemeral=True)

        cooldown_map = {
            "punishment appeals": "appeal",
            "password reset": "password_reset",
            "high testing": "high_testing",
            "staff application": "staff_app_tierlist"
        }
        ticket_category = cooldown_map.get(category_name, "normal")
        cooldown_ref = db.reference(f"/Ticket Cooldown/{interaction.user.id}/{ticket_category}")
        
        last_ts = cooldown_ref.get()
        current_ts = int(interaction.created_at.timestamp())
        
        if last_ts:
            time_diff = current_ts - last_ts
            cooldown_duration = TICKET_COOLDOWNS.get(ticket_category, 21600)
            
            if time_diff < cooldown_duration and interaction.user.id not in COOLDOWN_BYPASS_USER_IDS:
                next_time = last_ts + cooldown_duration
                cooldown_messages = {
                    "appeal": "You can only create a new appeal ticket every 14 days.",
                    "password_reset": "You can only create a password reset ticket every 7 days.",
                    "high_testing": "You can only create a high tier testing ticket every 30 days.",
                    "staff_app_tierlist": "You can only create a tierlist staff application ticket every 30 days."
                }
                msg_prefix = cooldown_messages.get(ticket_category, "You are on a cooldown.")
                return await interaction.response.send_message(content=f"{msg_prefix} Try again <t:{next_time}:R>", ephemeral=True)

        correct_interaction = interaction
        answer_embed = None
        ping_role = None  # Pings at the end of support tree
        
        if guild_id == SERVER_IDS["tierlist"]:
            linked_role_id = ROLE_IDS[guild_id]["linked"]
            
            # Account linking requirement
            if category_name != "general support" and linked_role_id not in [role.id for role in interaction.user.roles] and interaction.user.id not in COOLDOWN_BYPASS_USER_IDS:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        title="<:warn:1459986909911842846> **Account Linking Required for Non-Support Tickets**",
                        description=f"> To create a **{category_raw}** ticket, you must follow the instructions in <#1460525451368861818> to get linked. Once completed, you will automatically receive the <@&{linked_role_id}> role and be able to create this type of ticket.",
                        color=discord.Colour.red(),
                    ).set_footer(text="'General Support' tickets do not require account linking."),
                    ephemeral=True,
                )
            
            # Role gated tickets
            if category_name == "tester application":
                if not any(tier in role.name for role in interaction.user.roles if "[" not in role.name and "]" not in role.name for tier in ["LT3", "HT3", "LT2", "HT2"]):
                    return await interaction.response.send_message(content="❌ You must have at least a LT3+ gamemode role to create this type of ticket.", ephemeral=True)
            
            if category_name == "high testing":
                if not any(tier in role.name for role in interaction.user.roles if "[" not in role.name and "]" not in role.name for tier in ["HT3", "LT2", "HT2"]):
                    return await interaction.response.send_message(content="❌ You must have at least a HT3+ gamemode role to create this type of ticket.\nIf you have LT3 and want to test for HT3, head over to <#1467965604257595442> instead.", ephemeral=True)
            
            from commands.Tickets.tree import TicketQuestionsModal
            modal = TicketQuestionsModal(f"{category_raw} Tierlist")
            await interaction.response.send_modal(modal)
            await modal.wait()
            correct_interaction = modal.on_submit_interaction
            
            answer_embed = discord.Embed(color=0x22aef5)
            for key, value in modal.answers.items():
                answer_embed.add_field(name=key, value=value, inline=False)
            answer_embed.set_footer(text="You can add followup information in this channel.")
            ping_role = interaction.guild.get_role(SUPPORT_ROLE_IDS[guild_id])
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)

        chn = await interaction.guild.create_text_channel(f"⭕️-{interaction.user.name}", category=category_channel)
        await chn.edit(topic=str(interaction.user.id))
        await chn.set_permissions(interaction.user, send_messages=True, read_messages=True, attach_files=True)

        open_tickets = 0
        if guild_id in CATEGORY_IDS and isinstance(CATEGORY_IDS[guild_id], dict):
            for cat_id in CATEGORY_IDS[guild_id].values():
                cat_obj = interaction.guild.get_channel(cat_id)
                if cat_obj:
                    open_tickets += len([c for c in cat_obj.channels if isinstance(c, discord.TextChannel)])

        log_channel = interaction.guild.get_channel(log_channel_id)
        if log_channel:
            log_embed = discord.Embed(
                title="Ticket created",
                description=f"**{interaction.user.mention} created a new ticket <t:{int(chn.created_at.timestamp())}:R>!**",
                color=discord.Colour.green(),
            )
            try:
                log_embed.set_author(name=f"{interaction.user.name}", icon_url=interaction.user.avatar.url)
            except Exception:
                log_embed.set_author(name=f"{interaction.user.name}")
                
            log_embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            log_embed.set_footer(text=f"User ID: {interaction.user.id}")

            view = View()
            view.add_item(Button(style=discord.ButtonStyle.link, label="View Ticket", url=f"https://discord.com/channels/{guild_id}/{chn.id}"))
            await log_channel.send(embed=log_embed, view=view)

        roles = list(interaction.user.roles)
        roles.reverse()

        initial_embed = discord.Embed(
            title=category_raw,
            description=f"> Thank you for contacting the {interaction.guild.name} team.\n> Please describe your issue and wait for a response.\n\n-# There are currently **`{open_tickets}`** tickets open. Please be patient.\n-# <:warn:1459986909911842846> **DO NOT ping any staff** as it will only delay our response.",
            color=0x22aef5
        )
        initial_embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        initial_embed.add_field(name="User Mention", value=f"{interaction.user.mention}", inline=True)
        initial_embed.add_field(name="User ID", value=f"{interaction.user.id}", inline=True)
        initial_embed.add_field(name="Highest Role", value=f"{roles[0].mention}", inline=True)
        initial_embed.add_field(name="Ticket Created", value=f"<t:{int(chn.created_at.timestamp())}:R>", inline=True)
        initial_embed.add_field(name="Server Joined", value=f"<t:{int(interaction.user.joined_at.timestamp())}:R>", inline=True)
        initial_embed.add_field(name="Account Created", value=f"<t:{int(interaction.user.created_at.timestamp())}:R>", inline=True)

        if guild_id == SERVER_IDS["tierlist"]:
            linked_ign = "None"
            try:
                async with interaction.client.tllink_pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute("SHOW TABLES")
                        tb_res = await cursor.fetchone()
                        link_table = tb_res[0] if tb_res else "mystilinking"
                        await cursor.execute(f"SELECT player_name FROM {link_table} WHERE discord_id = %s", (str(interaction.user.id),))
                        link_res = await cursor.fetchone()
                        if link_res:
                            linked_ign = link_res[0]
            except Exception as e:
                print(f"Error fetching linked IGN for thread: {e}")

            async with interaction.client.tlresults_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT region FROM tlresults WHERE player_user_id = %s ORDER BY timestamp DESC LIMIT 1", (interaction.user.id,))
                    result = await cursor.fetchone()
                    
            recorded_region = result[0] if result else "Unknown"
            current_rank_roles = [r for r in interaction.user.roles if any(tier in r.name for tier in ["HT", "LT"])]

            initial_embed.add_field(name="Linked IGN", value=f"[{linked_ign}](https://tierlist.mysticraft.xyz/?player={linked_ign})" if linked_ign != "None" else "<:no:1036810470860013639> Not Linked", inline=True)
            initial_embed.add_field(name="Region", value=recorded_region, inline=True)
            initial_embed.add_field(name="Current Tiers", value=", ".join([r.mention for r in current_rank_roles]) if current_rank_roles else "None", inline=True)
            
        elif guild_id == SERVER_IDS["support"]:
            initial_embed.set_footer(text="You cannot type in tickets before answering all the questions first.")

        welcome_msg = f"**{interaction.user.mention}, welcome!** {('||' + ping_role.mention + '||') if ping_role else ''}"
        
        if answer_embed is None:
            view = CloseTicketButton() if guild_id != SERVER_IDS["support"] else None
            await chn.send(welcome_msg, embed=initial_embed, view=view)
        else:
            await chn.send(welcome_msg, embed=initial_embed)
            await chn.send(embed=answer_embed, view=CloseTicketButton())
            
        if guild_id == SERVER_IDS["support"]:
            from commands.Tickets.tree import start_support_tree
            await start_support_tree(interaction, chn, category_name)
                
        await correct_interaction.followup.send(content=f"Ticket created at <#{chn.id}>.", ephemeral=True)
        cooldown_ref.set(int(interaction.created_at.timestamp()))


class CreateTicketButtonView(discord.ui.View):
    def __init__(self, title="Create Ticket", emoji="🎫", color=discord.ButtonStyle.green, *, timeout=None):
        super().__init__(timeout=timeout)
        self.add_item(CreateTicketButton(title, emoji, color))


class CloseTicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.red,
        custom_id="close",
        emoji="🔒",
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.channel.topic and ":no_entry_sign:" in interaction.channel.topic:
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
        await interaction.response.send_message(
            embed=embed, view=ConfirmCloseTicketButtons(), ephemeral=True
        )


class TicketAdminButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Reopen Ticket",
        style=discord.ButtonStyle.grey,
        custom_id="reopen",
        emoji="🔓",
    )
    async def reopen(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.guild.get_member(
            int(interaction.channel.topic.replace("🚫", "").replace(":no_entry_sign:", "").strip())
        )
        newName = f"🟡{interaction.channel.name[1:]}"
        await interaction.channel.edit(topic=user.id, name=newName)
        await interaction.channel.set_permissions(
            user, send_messages=True, read_messages=True, attach_files=True
        )

        ref = db.reference("/Tickets")
        tickets = ref.get()
        for key, value in tickets.items():
            if value["Server ID"] == interaction.guild.id:
                LOGCHANNEL_ID = value["Log Channel ID"]
                break
        log = interaction.guild.get_channel(LOGCHANNEL_ID)

        embed = discord.Embed(
            title="Ticket reopened",
            description=f"Ticket created by {user.mention} is reopened by {interaction.user.mention}",
            color=0xFFFF00,
        )
        try:
            embed.set_author(
                name=user.name, icon_url=user.avatar.url
            )
        except Exception:
            embed.set_author(name=user.name)
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        embed.set_footer(text=f"User ID: {user.id}")
        button = Button(
            style=discord.ButtonStyle.link,
            label="View Ticket",
            url=f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}",
        )
        view = View()
        view.add_item(button)
        await log.send(embed=embed, view=view)
        embed = discord.Embed(
            title="Ticket reopened",
            description=f"Your ticket is reopened.",
            color=0xE44D41,
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        button = Button(
            style=discord.ButtonStyle.link,
            label="Head over to your ticket",
            emoji="🎫",
            url=f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}",
        )
        view = View()
        view.add_item(button)
        try:
            await user.send(embed=embed, view=view)
        except Exception:
            pass
        embed = discord.Embed(
            title="🔓 Ticket Reopened",
            description="Ticket is again visible to the member.",
            color=0xFFFF00,
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await interaction.message.delete()
        await interaction.channel.send(embed=embed, view=CloseTicketButton())
        await interaction.response.send_message("Ticket is reopened.", ephemeral=True)

    @discord.ui.button(
        label="Delete Ticket",
        style=discord.ButtonStyle.grey,
        custom_id="delete",
        emoji="✉️",
    )
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="Deleting Ticket...",
            description="Ticket will be deleted in 5 seconds",
            color=0xFF0000,
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await interaction.message.delete()
        await interaction.channel.send(embed=embed)
        await asyncio.sleep(5)
        await interaction.channel.delete()


class ConfirmCloseTicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green, custom_id="yes")
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=discord.Embed(description="✅ Ticket Closure Confirmed", color=discord.Color.green()), 
            view=None
        )
        await close_ticket(interaction)

    @discord.ui.button(label="No", style=discord.ButtonStyle.red, custom_id="no")
    async def red(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="Action Cancelled",
            description=f"Alright {interaction.user.mention}! I will not close the ticket!",
            color=0xFF0000,
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await interaction.response.edit_message(embed=embed, view=None)


class ResolveFlagView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(
        label="Mark Resolved",
        style=discord.ButtonStyle.green,
        custom_id="resolve_flag_view:resolve"
    )
    async def resolve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            channel = interaction.client.get_channel(int(interaction.message.embeds[0].footer.text.split(":")[1].strip()))
            await interaction.message.delete()
            await interaction.response.send_message("✅ Ticket marked as resolved!", ephemeral=True)
            newName = f"🟢{channel.name[1:]}"
            await channel.edit(topic=channel.topic, name=newName)
        except Exception as e:
            await interaction.response.send_message(f"❗ `{e}`", ephemeral=True)


class Ticket(commands.GroupCog, name="ticket"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()
        
    @app_commands.command(name="blacklist", description="View all blacklisted users or blacklist a user")
    @app_commands.describe(user="User to blacklist (leave empty to view all blacklisted users)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_blacklist(self, interaction: discord.Interaction, user: discord.Member = None):
        if user is None:
            ref = db.reference(f"/Ticket Blacklist")
            blacklisted_users = ref.get()

            if not blacklisted_users:
                embed = discord.Embed(
                    description="No users are currently blacklisted from creating tickets.",
                    color=0x00FF00
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            user_list = []
            for user_id in blacklisted_users.keys():
                user = interaction.guild.get_member(int(user_id))
                if user:
                    user_list.append(f"- {user.mention} (`{user_id}`)")
                else:
                    user_list.append(f"- `{user_id}` (User not in server)")

            embed = discord.Embed(
                title=f"Blacklisted Users ({len(user_list)})",
                description="\n".join(user_list),
                color=0xFF0000
            )
            embed.set_footer(text=f"Requested by {interaction.user.name}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            ref = db.reference(f"/Ticket Blacklist/{user.id}")
            ref.set(True)
            embed = discord.Embed(description=f"{user.mention} has been blacklisted from creating tickets in all **MystiCraft** networks.", color=0x00FF00)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
    @app_commands.command(name="unblacklist", description="Unblacklist a user from creating tickets")
    @app_commands.describe(user="User to unblacklist")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_unblacklist(self, interaction: discord.Interaction, user: discord.Member):
        ref = db.reference(f"/Ticket Blacklist/{user.id}")
        ref.delete()
        embed = discord.Embed(description=f"{user.mention} has been unblacklisted from **MystiCraft** networks.", color=0x00FF00)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @app_commands.command(name="add", description="Add a user to the current ticket channel")
    @app_commands.describe(user="The user to add to this ticket")
    async def ticket_add(self, interaction: discord.Interaction, user: discord.Member):
        guild, channel = interaction.guild, interaction.channel

        if not channel.topic or not channel.topic.isdigit():
            embed = discord.Embed(description="❌ This command can only be used in ticket channels.", color=0xFF0000)
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        if not check_for_staff(guild, interaction.user):
            embed = discord.Embed(description="You cannot run this command as you do not have permission to manage tickets.", color=0xFF0000)
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        ticket_owner_id = int(channel.topic)
        if user.id == ticket_owner_id:
            embed = discord.Embed(description="❌ This user is the ticket owner and already has access to this channel.", color=0xFF0000)
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        current_perms = channel.permissions_for(user)
        if current_perms.read_messages and current_perms.send_messages:
            embed = discord.Embed(description=f"❌ {user.mention} already has access to this ticket channel.", color=0xFF0000)
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        try:
            await channel.set_permissions(user, send_messages=True, read_messages=True, attach_files=True)
            
            embed = discord.Embed(
                description=f"✅ {user.mention} has been added to this ticket by {interaction.user.mention}.",
                color=0x00FF00
            )
            await interaction.response.send_message(content=user.mention, embed=embed)
            
            try:
                dm_embed = discord.Embed(title="You have been added to a ticket channel!", description=f"You have been added to a ticket channel in **{guild.name}** by {interaction.user.mention}.", color=discord.Color.green())
                button = Button(style=discord.ButtonStyle.link, label="View Ticket", url=f"https://discord.com/channels/{guild.id}/{channel.id}")
                view = View()
                view.add_item(button)
                await user.send(embed=dm_embed, view=view)
            except Exception:
                pass

        except Exception as e:
            embed = discord.Embed(title="❌ Error", description=f"An error occurred while adding the user: {str(e)}", color=0xFF0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="reset", description="Reset the settings of ticket in the server")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_reset(self, interaction: discord.Interaction) -> None:
        tickets = db.reference("/Tickets").get()
        found = False
        for key, val in tickets.items():
            if val["Server ID"] == interaction.guild.id:
                db.reference("/Tickets").child(key).delete()
                found = True
                break
        if found:
            embed = discord.Embed(
                title="Ticket successfully reset",
                description=f"You can use </ticket setup:1033188985587109910> at anytime to setup the ticket function again.",
                colour=0xFFFF00,
            )
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="We could not find your server",
                description=f"Maybe you have already reset the ticket function in your server, or you have never enabled ticket function. Anyways, no records found in our system.",
                colour=0xFF0000,
            )
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setup", description="Setup ticket function in the server")
    @app_commands.describe(
        category="The category to hold all the tickets (If you do not specify, we will create one for you)",
        log_channel="The channel to log all future tickets (If you do not specify, we will create one for you)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_setup(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel = None,
        log_channel: discord.TextChannel = None,
    ) -> None:
        ref = db.reference("/Tickets")
        tickets = ref.get()
        for key, value in tickets.items():
            if value["Server ID"] == interaction.guild.id:
                embed = discord.Embed(
                    title="Ticket already enabled!",
                    description=f'The category is already set as <#{value["Category ID"]}> `({value["Category ID"]})` and the ticket log channel is already set as <#{value["Log Channel ID"]}> `({value["Log Channel ID"]})`\n\nPlease use </ticket button:1033188985587109910> or </ticket dropdown:1033188985587109910> to create your own customized ticket panel.\n\nIf you wish to reset the settings of tickets, please use </ticket reset:1033188985587109910>.',
                    colour=0xFF0000,
                )
                embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
                return await interaction.response.send_message(embed=embed, ephemeral=True)

        if not category:
            category = await interaction.guild.create_category("Tickets")
        if not log_channel:
            log_channel = await interaction.guild.create_text_channel(
                f"ticket-log", category=category
            )

        embed = discord.Embed(
            title="What is this?",
            description=f"This channel logs all ticket deletion and creation events! It clearly provides server admins a list of past tickets. ",
            colour=discord.Color.blurple(),
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await log_channel.send(embed=embed)

        await category.set_permissions(interaction.guild.default_role, read_messages=False)
        await log_channel.set_permissions(interaction.guild.default_role, read_messages=False)

        data = {
            interaction.guild.name: {
                "Server Name": interaction.guild.name,
                "Server ID": interaction.guild.id,
                "Category ID": category.id,
                "Log Channel ID": log_channel.id,
            }
        }

        for key, value in data.items():
            ref.push().set(value)

        embed = discord.Embed(
            title="Ticket successfully enabled!",
            description=f"The category is set as <#{category.id}> `({category.id})` and the ticket log channel is set as <#{log_channel.id}> `({log_channel.id})`. \n\n**All administrators can by default view the tickets. If you wish to let staff without administrator permission to do so as well, please use </ticket addrole:1033188985587109910> and add roles of your own choice. Use </ticket removerole:1033188985587109910> for vice versa.**\n\nPlease use </ticket button:1033188985587109910> or </ticket dropdown:1033188985587109910> to create your own customized ticket panel.",
            colour=0x00FF00,
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="addrole", description="Add a role that can see and manage tickets")
    @app_commands.describe(role="The role at your own choice that can see and manage tickets")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_addrole(self, interaction: discord.Interaction, role: discord.Role) -> None:
        ref = db.reference("/Tickets")
        tickets = ref.get()
        found = False
        for key, value in tickets.items():
            if value["Server ID"] == interaction.guild.id:
                CATEGORY_ID = value["Category ID"]
                LOGCHANNEL_ID = value["Log Channel ID"]
                found = True
                break

        if found:
            category = interaction.guild.get_channel(CATEGORY_ID)
            log_channel = interaction.guild.get_channel(LOGCHANNEL_ID)
            await category.set_permissions(role, read_messages=True, send_messages=True, attach_files=True, manage_channels=True, manage_messages=True, read_message_history=True)
            await log_channel.set_permissions(role, read_messages=True, send_messages=True, attach_files=True, manage_channels=True, manage_messages=True, read_message_history=True)
            for channel in category.channels:
                await channel.set_permissions(role, read_messages=True, send_messages=True, attach_files=True, manage_channels=True, manage_messages=True, read_message_history=True)
            embed = discord.Embed(
                title="Role Added!",
                description=f"{role.mention} now has the following permissions in all ticket-related channels:\n\n`- Read Messages`\n`- Send Messages`\n`- Attach Files`\n`- Manage Channels`\n`- Manage Messages`\n`- Read Message History`",
                colour=0x00FF00,
            )
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title="Ticket not enabled!", description=f"This server does not have a ticket category or a log channel. Please ask the server admin to use </ticket setup:1033188985587109910> to setup tickets!", colour=0xFF0000)
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="removerole", description="Remove a role that can see and manage tickets")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(role="The role at your own choice that can no longer see and manage tickets")
    async def ticket_removerole(self, interaction: discord.Interaction, role: discord.Role) -> None:
        ref = db.reference("/Tickets")
        tickets = ref.get()
        found = False
        for key, value in tickets.items():
            if value["Server ID"] == interaction.guild.id:
                CATEGORY_ID = value["Category ID"]
                LOGCHANNEL_ID = value["Log Channel ID"]
                found = True
                break

        if found:
            category = interaction.guild.get_channel(CATEGORY_ID)
            log_channel = interaction.guild.get_channel(LOGCHANNEL_ID)
            await category.set_permissions(role, read_messages=None, send_messages=None, attach_files=None, manage_channels=None, manage_messages=None, read_message_history=None)
            await log_channel.set_permissions(role, read_messages=None, send_messages=None, attach_files=None, manage_channels=None, manage_messages=None, read_message_history=None)
            for channel in category.channels:
                await channel.set_permissions(role, read_messages=None, send_messages=None, attach_files=None, manage_channels=None, manage_messages=None, read_message_history=None)
            embed = discord.Embed(
                title="Role Removed!",
                description=f"{role.mention} no longer has elevated permissions in ticket-related channels.",
                colour=0x00FF00,
            )
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title="Ticket not enabled!", description=f"This server does not have a ticket category or a log channel. Please ask the server admin to use </ticket setup:1033188985587109910> to setup tickets!", colour=0xFF0000)
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="notify", description="Send a DM to the ticket author notifying the ticket needs their attention")
    @app_commands.describe(message="Optional message you could include in the DMs")
    async def ticket_notify(self, interaction: discord.Interaction, message: str = None) -> None:
        if message is None:
            message = " "
        else:
            message = f"\n\n> {message}"
        try:
            user = interaction.guild.get_member(int(interaction.channel.topic))
        except Exception:
            pass
        embed = discord.Embed(
            title="⚠️ Notification ⚠️",
            description=f"The ticket you previously opened in **{interaction.guild.name}** needs your attention! Please kindly respond.{message}\n\nIf you no longer need assistance or your issue has been resolved, **please still let us know in the ticket** so we can help close the ticket.",
            color=0xE44D41,
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        try:
            button = Button(style=discord.ButtonStyle.link, label="Head over to your ticket", emoji="🎫", url=f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}")
            view = View()
            view.add_item(button)
            await user.send(embed=embed, view=view)
            await interaction.response.send_message(f"{user.mention} received a DM notification.")
        except Exception:
            await interaction.response.send_message("Unable to DM user!", ephemeral=True)
            
    @app_commands.command(name="tldr", description="Get ticket summary")
    async def ticket_tldr(self, interaction: discord.Interaction):
        await interaction.response.defer()
        channel = interaction.channel
        from commands.Tickets.transcript import generate, get_transcript
        f, user, _, _ = await get_transcript(interaction, channel)
        prompt = f"Summarize this ticket in 3 short bullet points: {f.read()}"
        summary = await generate(prompt)
        embed = discord.Embed(title=f"TL;DR for {channel.name}", description=summary, color=discord.Color.blue())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="flag", description="Flag a ticket for special attention")
    @app_commands.describe(flag_type="Select a flag type", notes="Provide additional context (optional)")
    @app_commands.choices(flag_type=[
        app_commands.Choice(name="Owner Needed", value="owner"),
        app_commands.Choice(name="Manager Needed", value="manager"),
        app_commands.Choice(name="Mod Needed", value="mod"),
        app_commands.Choice(name="Resolved", value="resolved"),
    ])
    async def ticket_flag(self, interaction: discord.Interaction, flag_type: app_commands.Choice[str], notes: str = None):
        guild, channel = interaction.guild, interaction.channel
        val = flag_type.value

        if val == "resolved":
            await delete_flags(guild, channel.id, FLAG_CHANNEL_IDS)
            await channel.edit(name=f"🟢{channel.name[1:]}")
            return await interaction.response.send_message("✅ Ticket marked as resolved.", ephemeral=True)

        flag_info = FLAG_CHANNEL_IDS.get(val, {})
        target_channel_id = flag_info.get(guild.id)
        emoji = flag_info.get("emoji", "❓")

        if not target_channel_id or not (target_channel := guild.get_channel(target_channel_id)):
            return await interaction.response.send_message("❌ Flag destination channel not found or misconfigured for this server.", ephemeral=True)

        embed = discord.Embed(
            title=f"Ticket Flagged - {flag_type.name}",
            description=f"Ticket: {channel.mention}\nNotes: {notes or 'None'}\nFlagged by: {interaction.user.mention}",
            color=discord.Color.red()
        ).set_footer(text=f"Ticket ID: {channel.id}")

        try:
            await target_channel.send(embed=embed, view=ResolveFlagView())
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Bot lacks permissions to send messages in the target channel.", ephemeral=True)

        await channel.edit(name=f"{emoji}{channel.name[1:]}")
        await interaction.response.send_message(f"✅ Flag posted to {target_channel.mention}", ephemeral=True)
        
    @app_commands.command(name="response", description="Generate a AI-drafted response with the context of the ticket")
    @app_commands.describe(response_type="Select a response template or choose 'Custom'", context="Provide additional context/reason/notes to customize your response")
    @app_commands.choices(response_type=[
        app_commands.Choice(name="Appeal Rejected", value="appeal_reject"),
        app_commands.Choice(name="Appeal Accepted", value="appeal_accept"),
        app_commands.Choice(name="Need More Time", value="more_time"),
        app_commands.Choice(name="Bug Acknowledged", value="bug_ack"),
        app_commands.Choice(name="Known Bug", value="known_bug"),
        app_commands.Choice(name="Cannot Reproduce Bug", value="cannot_reproduce"),
        app_commands.Choice(name="Report Investigating", value="report_investigating"),
        app_commands.Choice(name="Report Action Taken", value="report_action"),
        app_commands.Choice(name="Report No Action Taken", value="report_no_action"),
        app_commands.Choice(name="Resolved", value="resolved"),
        app_commands.Choice(name="Custom", value="custom"),
    ])
    async def ticket_response(self, interaction: discord.Interaction, response_type: app_commands.Choice[str], context: str = None):
        prompts = {
            "appeal_reject": "informing the user that their appeal has been rejected. Reason: {context}",
            "appeal_accept": "informing the user that their appeal has been accepted. Details: {context}",
            "more_time": "explaining that we need more time to investigate or return an answer. Details: {context}",
            "bug_ack": "acknowledging the reported bug and confirming it has been forwarded to the development team. Context: {context}",
            "known_bug": "confirming the reported bug is already known and being worked on. Context: {context}",
            "cannot_reproduce": "explaining that we could not reproduce the bug and need more information. Context: {context}",
            "report_investigating": "confirming that the report has been received and will be investigated. Context: {context}",
            "report_action": "confirming that appropriate action has been taken regarding the report. Context: {context}",
            "report_no_action": "explaining that no action was taken. Context: {context}",
            "resolved": "stating that the issue appears to be resolved and the ticket will now be closed. Context: {context}",
            "custom": "based on: {context}"
        }
        prompt = prompts[response_type.value].format(context=context or "")
        from commands.Tickets.transcript import generate, get_transcript
        f, user, usersInvolved, staff_message_counts = await get_transcript(interaction, interaction.channel)
        response = await generate(f"Generate a short, professional, and concise response directly addressing the user for the following ticket as a staff member, {prompt}\n{f.read()}")
        await interaction.response.send_message(response, ephemeral=True)
        
    @app_commands.command(name="button", description="Creates a ticket panel with buttons (only for applications)")
    @app_commands.describe(title="Makes the title of the embed", description="Makes the description of the embed", color="Sets the color of the embed", thumbnail="Please provide a URL for the thumbnail of the embed (upper-right hand corner image)", image="Please provide a URL for the image of the embed (appears at the bottom of the embed)", footer="Sets the footer of the embed that appears at the bottom of the embed as small texts", footer_time="Shows the time of the embed being sent?")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_button(self, interaction: discord.Interaction, title: str = None, description: str = None, color: str = None, thumbnail: str = None, image: str = None, footer: str = None, footer_time: bool = None) -> None:
        if color is not None:
            try:
                color = await commands.ColorConverter().convert(interaction, color)
            except:
                color = None
        if color is None:
            color = discord.Color.default()
        embed = discord.Embed(color=color)
        if title is not None:
            embed.title = title
        if description is not None:
            embed.description = description
        if thumbnail is not None:
            embed.set_thumbnail(url=thumbnail)
        if image is not None:
            embed.set_image(url=image)
        if footer is not None:
            embed.set_footer(text=footer)
        if footer_time is not None or footer_time == True:
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        from commands.Tickets.application import ApplicationView
        await interaction.channel.send(embed=embed, view=ApplicationView())
        embed = discord.Embed(title="✅ Custom Ticket Panel Sent", description="All members who have access to this channel can create a ticket by clicking the button below the panel!", color=0x00FF00)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="dropdown", description="Creates a ticket panel with dropdown menu")
    @app_commands.describe(title="Makes the title of the embed", description="Makes the description of the embed", color="Sets the color of the embed", thumbnail="Please provide a URL for the thumbnail of the embed (upper-right hand corner image)", image="Please provide a URL for the image of the embed (appears at the bottom of the embed)", footer="Sets the footer of the embed that appears at the bottom of the embed as small texts", dropdown_placeholder="Sets the placeholder of the dropdown menu", dropdown1_emoji="Sets the emoji of the first option", dropdown1_title="Sets the text of the first option (title | description)", dropdown2_emoji="Sets the emoji of the second option", dropdown2_title="Sets the text of the second option (title | description)", dropdown3_emoji="Sets the emoji of the third option", dropdown3_title="Sets the text of the third option (title | description)", dropdown4_emoji="Sets the emoji of the fourth option", dropdown4_title="Sets the text of the fourth option (title | description)", dropdown5_emoji="Sets the emoji of the fifth option", dropdown5_title="Sets the text of the fifth option (title | description)", dropdown6_emoji="Sets the emoji of the sixth option", dropdown6_title="Sets the text of the sixth option (title | description)", dropdown7_emoji="Sets the emoji of the seventh option", dropdown7_title="Sets the text of the seventh option (title | description)")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_dropdown(self, interaction: discord.Interaction, title: str = None, description: str = None, color: str = None, thumbnail: str = None, image: str = None, footer: str = None, dropdown_placeholder: str = "Select a Category", dropdown1_emoji: str = None, dropdown1_title: str = None, dropdown2_emoji: str = None, dropdown2_title: str = None, dropdown3_emoji: str = None, dropdown3_title: str = None, dropdown4_emoji: str = None, dropdown4_title: str = None, dropdown5_emoji: str = None, dropdown5_title: str = None, dropdown6_emoji: str = None, dropdown6_title: str = None, dropdown7_emoji: str = None, dropdown7_title: str = None) -> None:
        if color is not None:
            try:
                color = await commands.ColorConverter().convert(interaction, color)
            except:
                color = None
        if color is None:
            color = discord.Color.default()
        embed = discord.Embed(color=color)
        if title is not None:
            embed.title = title
        if description is not None:
            embed.description = description
        if thumbnail is not None:
            embed.set_thumbnail(url=thumbnail)
        if image is not None:
            embed.set_image(url=image)
        if footer is not None:
            embed.set_footer(text=footer)

        options = []
        list = [
            [dropdown1_emoji, dropdown1_title], [dropdown2_emoji, dropdown2_title],
            [dropdown3_emoji, dropdown3_title], [dropdown4_emoji, dropdown4_title],
            [dropdown5_emoji, dropdown5_title], [dropdown6_emoji, dropdown6_title],
            [dropdown7_emoji, dropdown7_title],
        ]

        for item in list:
            if item[1] is None and (item[0] is not None):
                embed = discord.Embed(title="Dropdown Menu Option's Title Missing", description="You must include a title for every option!", color=0xFF0000)
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            if item[0] is not None and item[1] is not None:
                emote = emoji.emojize(item[0].strip())
                if "|" in item[1]:
                    title = item[1].split("|")[0].strip()
                    description = item[1].split("|")[1].strip()
                else:
                    title = item[1].strip()
                    description = None
                options.append(discord.SelectOption(label=title, value=title, description=description, emoji=emote))
            elif item[0] is None and item[1] is not None:
                if "|" in item[1]:
                    title = item[1].split("|")[0].strip()
                    description = item[1].split("|")[1].strip()
                else:
                    title = item[1].strip()
                    description = None
                options.append(discord.SelectOption(label=title, value=title, description=description))

        await interaction.channel.send(embed=embed, view=SelectView(dropdown_placeholder, options))
        embed = discord.Embed(title="✅ Custom Ticket Panel Sent", description="All members who have access to this channel can create a ticket by selecting the dropdown menu below the panel!", color=0x00FF00)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Ticket(bot))