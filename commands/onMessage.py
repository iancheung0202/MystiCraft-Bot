import discord
import datetime
import re
import time
import asyncio

from discord.ext import commands
from firebase_admin import db
from discord.ui import Button, View, Select, UserSelect

STAFF_SERVER_ID = 1064570075304177734
STAFF_SERVER_ROLES = [
    1064570857537667193,  # owner
    1064571049410318336,  # executive
    1064571207627853844,  # manager
    1290409277638311947,  # senior admin
    1090330479179350037,  # admin
    1064571463409082408,  # developer
    1232591866281852959,  # senior mod
    1066298183879229490,  # mod
    1172834016412569610,  # helper
]

MAIN_SERVER_ID = 1136662635039952988
MAIN_SERVER_ROLES = [
    1136672543466598592,  # owner
    1136672547270819900,  # executive
    1136672551729381418,  # manager
    1290543539368759429,  # senior admin
    1136672556322128034,  # admin
    1136672555214852106,  # developer
    1232589300428832820,  # senior mod
    1136672558469615748,  # mod
    1172845504414097439,  # helper
]

SUPPORT_SERVER_ID = 1373869107484688436
SUPPORT_SERVER_ROLES = [
    1373893342169137202,  # owner
    1374975813891395784,  # executive
    1373892851745685524,  # manager
    1373891660471210024,  # senior admin
    1373890838496673852,  # admin
    1373890109216129155,  # developer
    1373889160833798274,  # senior mod
    1373887662842183801,  # mod
    1373883332492001341,  # helper
]

EMOTES = [
    "<:mystcraft_owner:1267018399293243523>",
    "<:mysticraft_executive:1267015078675222548>",
    "<:mysticraft_manager:1267012427946393641>",
    "<:mysticraft_sradmin:1294524850542739496>",
    "<:mysticraft_admin:1267020293134614620>",
    "<:mysticraft_dev:1267019102200008704>",
    "<:mysticraft_srmod:1267014449844457564>",
    "<:mysticraft_mod:1267004112332001303>",  # mod
    "<:mysticraft_helper:1267016346584223836>",
]

# Base staff role per server
STAFF_BASE_ROLES = {
    STAFF_SERVER_ID: 1066298571000909975,
    MAIN_SERVER_ID: 1136672562307412079,
    SUPPORT_SERVER_ID: 1373882802084511754,
}

# Abbreviations by staff index
ABBREVIATIONS = [
    "Owner",      # 0
    "Executive",  # 1
    "Manager",    # 2
    "Sr Admin",   # 3
    "Admin",      # 4
    "Dev",        # 5
    "Sr Mod",     # 6
    "Mod",        # 7
    "Helper",     # 8
]

def format_nickname(abbreviation: str, display_name: str) -> str:
    """Format nickname as 'Abbreviation | Name'."""
    # Strip existing bracketed prefix if any
    if "|" in display_name:
        display_name = display_name.split("|", 1)[-1].strip()
    return f"{abbreviation} | {display_name}"


class EditStaffView(View):
    def __init__(self, bot):
        super().__init__(timeout=120)
        self.bot = bot
        self.role_value = None
        self.target_user = None
        
        # User selection
        self.user_select = UserSelect(placeholder="Select staff member", custom_id="user_select")
        self.user_select.callback = self.user_callback
        self.add_item(self.user_select)
        
        # Role selection dropdown
        role_options = []
        for i, emote in enumerate(EMOTES):
            role_id = STAFF_SERVER_ROLES[i]
            role_name = self.get_role_name(role_id)
            if "•" in role_name:
                display_name = role_name.split("•")[1].strip()
            else:
                display_name = role_name
            role_options.append(
                discord.SelectOption(
                    label=display_name,
                    value=str(role_id),
                    emoji=emote
                )
            )
        role_options.append(discord.SelectOption(label="Member", value="member", emoji="👤"))
        self.role_select = Select(placeholder="Select staff role", options=role_options, custom_id="role_select")
        self.role_select.callback = self.role_callback
        self.add_item(self.role_select)
        
        # Submit button
        self.submit_button = Button(label="Submit", style=discord.ButtonStyle.green, disabled=False)
        self.submit_button.callback = self.submit_callback
        self.add_item(self.submit_button)

    def get_role_name(self, role_id):
        guild = self.bot.get_guild(STAFF_SERVER_ID)
        role = guild.get_role(role_id)
        return role.name if role else f"Role {role_id}"

    async def role_callback(self, interaction: discord.Interaction):
        self.role_value = self.role_select.values[0] if self.role_select.values else None
        print(self.role_value)
        print(self.target_user)
        await interaction.response.defer()

    async def user_callback(self, interaction: discord.Interaction):
        self.target_user = self.user_select.values[0] if self.user_select.values else None
        print(self.role_value)
        print(self.target_user)
        await interaction.response.defer()

    async def submit_callback(self, interaction: discord.Interaction):
        if not self.role_value or not self.target_user:
            await interaction.response.send_message(
                "❌ Please select both a staff member and a role before submitting.",
                ephemeral=True
            )
            return
        if not await self.check_permissions(interaction):
            return
        
        guild_staff = interaction.client.get_guild(STAFF_SERVER_ID)
        staff_member = guild_staff.get_member(self.target_user.id)
        
        if not staff_member:
            await interaction.response.send_message("❌ User not found in staff server", ephemeral=True)
            return

        current_staff_roles = [r for r in staff_member.roles if r.id in STAFF_SERVER_ROLES]
        try:
            highest_staff_position = current_staff_roles[-1].position
        except Exception:
            highest_staff_position = 0
        if self.role_value == "member":
            # Remove all staff roles
            await staff_member.remove_roles(*current_staff_roles, reason="Staff role removal")
            await staff_member.kick(reason="Demoted to member")
            new_role_mention = "`Member`"
            new_staff_position = 0
        else:
            # Remove existing staff roles and add new one
            new_role_id = int(self.role_value)
            new_role = guild_staff.get_role(new_role_id)
            new_staff_position = new_role.position
            if not new_role:
                await interaction.response.send_message("❌ Invalid role selected", ephemeral=True)
                return
            
            await staff_member.remove_roles(*current_staff_roles, reason="Staff role update")
            await staff_member.add_roles(new_role, reason="Staff role update")
            new_role_mention = new_role.mention
        
        if highest_staff_position < new_staff_position:
            action = "promoted"
        elif highest_staff_position > new_staff_position:
            action = "demoted"
        else:
            action = None
        
        await interaction.response.defer(thinking=True, ephemeral=True)

        if action is None:
            await interaction.followup.send(
                f"**No changes made to {staff_member.mention}.** They are already a **{new_role_mention}!",
                ephemeral=True
            )
            return
        
        await self.sync_member_roles(staff_member, interaction)
        await self.send_edit_notification(interaction, staff_member, new_role_mention, action)
        await interaction.followup.send(
            f"✅ **{action.title()}** {staff_member.mention} to **{new_role_mention}**. \n**Please click `Sync` to update the staff list and sync roles on the Discord servers!**",
            ephemeral=True
        )

    async def check_permissions(self, interaction: discord.Interaction):
        user = interaction.user
        guild = interaction.guild
        
        # Get user's highest staff role
        user_roles = [r.id for r in user.roles]
        user_highest_index = None
        for idx, role_id in enumerate(STAFF_SERVER_ROLES):
            if role_id in user_roles:
                if user_highest_index is None or idx < user_highest_index:
                    user_highest_index = idx
                    
        # Only managers+ can edit
        if user_highest_index is None or user_highest_index > 2:  # 2=manager index
            await interaction.response.send_message(
                "❌ You need Manager+ permissions to edit staff roles",
                ephemeral=True
            )
            return False

        # Check if editing self
        if user.id == self.target_user.id:
            await interaction.response.send_message(
                "❌ You cannot edit your own roles",
                ephemeral=True
            )
            return False

        # Get target user's highest role
        target_roles = [r.id for r in self.target_user.roles]
        target_highest_index = None
        for idx, role_id in enumerate(STAFF_SERVER_ROLES):
            if role_id in target_roles:
                if target_highest_index is None or idx < target_highest_index:
                    target_highest_index = idx

        # Prevent editing higher-ranked staff
        if target_highest_index is not None and target_highest_index < user_highest_index:
            await interaction.response.send_message(
                "❌ You cannot edit staff with higher rank than you",
                ephemeral=True
            )
            return False

        # Prevent assigning equal/higher rank
        if self.role_value != "member":
            new_role_index = STAFF_SERVER_ROLES.index(int(self.role_value))
            if new_role_index <= user_highest_index:
                await interaction.response.send_message(
                    "❌ You cannot assign roles at or above your rank",
                    ephemeral=True
                )
                return False

        return True

    async def sync_member_roles(self, member, interaction):
        """Sync staff roles for a member across all servers"""
        # Get member's current staff role in staff server
        current_staff_role = None
        for role in member.roles:
            if role.id in STAFF_SERVER_ROLES:
                role_index = STAFF_SERVER_ROLES.index(role.id)
                if current_staff_role is None or role_index < current_staff_role:
                    current_staff_role = role_index
        
        # Process each server
        servers = [
            (MAIN_SERVER_ID, MAIN_SERVER_ROLES),
            (SUPPORT_SERVER_ID, SUPPORT_SERVER_ROLES),
            (STAFF_SERVER_ID, STAFF_SERVER_ROLES)
        ]
        
        for server_id, server_roles in servers:
            guild = member.guild if member.guild.id == server_id else interaction.client.get_guild(server_id)
            if not guild:
                continue
                
            target_member = guild.get_member(member.id)
            if not target_member:
                continue
                
            # Remove all staff roles
            roles_to_remove = [guild.get_role(rid) for rid in server_roles]
            roles_to_remove = [r for r in roles_to_remove if r and r in target_member.roles]
            if roles_to_remove:
                await target_member.remove_roles(*roles_to_remove, reason="Staff role sync")
            
            # Add new role if applicable
            if current_staff_role is not None:
                new_role_id = server_roles[current_staff_role]
                new_role = guild.get_role(new_role_id)
                if new_role and new_role not in target_member.roles:
                    await target_member.add_roles(new_role, reason="Staff role sync")
                    
                # Add staff base role if missing
                base_role_id = STAFF_BASE_ROLES.get(server_id)
                if base_role_id:
                    base_role = guild.get_role(base_role_id)
                    if base_role and base_role not in target_member.roles:
                        await target_member.add_roles(base_role, reason="Staff base role sync")
                        
                # Format nickname to match Abbreviation | Name
                abbreviation = ABBREVIATIONS[current_staff_role]
                new_nick = format_nickname(abbreviation, target_member.display_name)
                if target_member.nick != new_nick:
                    try:
                        await target_member.edit(nick=new_nick, reason="Update staff nickname format")
                    except discord.Forbidden:
                        pass
            else:
                # Member is not staff anymore
                base_role_id = STAFF_BASE_ROLES.get(server_id)
                if base_role_id:
                    base_role = guild.get_role(base_role_id)
                    if base_role and base_role in target_member.roles:
                        await target_member.remove_roles(base_role, reason="No longer staff")

                # Remove staff abbreviation from nickname if present
                if target_member.nick and target_member.nick.startswith("["):
                    try:
                        base_name = target_member.display_name.split("|", 1)[-1].strip()
                        await target_member.edit(nick=base_name, reason="Clear staff nickname")
                    except discord.Forbidden:
                        pass

    async def send_edit_notification(self, interaction, member, new_role_mention, action):
        """Send edit notification to log channel"""
        channel_id = 1066300810889273345
        log_channel = interaction.client.get_channel(channel_id)
        if not log_channel:
            return
            
        embed = discord.Embed(
            title="<:mysticraftlogo:1263829753366974535> MystiCraft Team Update",
            description=f"{member.mention} has been **{action}** to {new_role_mention}!",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"{action.title()} by {interaction.user.name}")
        embed.timestamp = datetime.datetime.utcnow()
        
        await log_channel.send(embed=embed)

class RefreshStaffV2View(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="View Raw List",
        style=discord.ButtonStyle.blurple,
        custom_id="raw_v3",
        emoji="🗒️"
    )
    async def raw(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"{interaction.message.embeds[0].description}", ephemeral=True)

    @discord.ui.button(
        label="Sync",
        style=discord.ButtonStyle.grey,
        custom_id="refresh_v3",
        emoji="<:refresh:1048779043287351408>"
    )
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild = interaction.client.get_guild(STAFF_SERVER_ID)
        msgs = []
        for i, role_id in enumerate(STAFF_SERVER_ROLES):
            role = guild.get_role(role_id)
            if not role:
                continue
                
            msg = f"{EMOTES[i]} **[{len(role.members)}] {role.name.split('•')[1].strip()}**\n"
            if not role.members:
                msg += "N/A\n"
            else:
                for member in role.members:
                    msg += f"- {member.mention} `({member.id})`\n"
            msgs.append(msg)

        # Sync roles across servers
        updates = await self.sync_all_servers(interaction)
        
        # Update message
        new_view = RefreshStaffV2View()
        
        # Create embed
        embed = discord.Embed(
            title="<:mysticraftlogo:1141390665842970644> MystiCraft Staff List",
            description="\n".join(msgs),
            color=0x13C6F0
        )
        
        await interaction.message.edit(embed=embed, view=new_view)
        await interaction.followup.send(
            f"<:refresh:1048779043287351408> Staff list refreshed and roles synced in **3** servers!",
            ephemeral=True
        )

    @discord.ui.button(
        label="Edit Staff",
        style=discord.ButtonStyle.red,
        custom_id="edit_staff_v3",
        emoji="✏️"
    )
    async def edit_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Basic permission check
        allowed_roles = STAFF_SERVER_ROLES[:3]  # Owner, Executive, Manager
        user_roles = [r.id for r in interaction.user.roles]
        if not any(role in allowed_roles for role in user_roles):
            await interaction.response.send_message(
                "❌ Only Managers+ can edit staff roles",
                ephemeral=True
            )
            return
            
        try:
            await interaction.response.send_message(
                "Please select a staff member and assign their new rank using the dropdowns below.",
                view=EditStaffView(interaction.client),
                ephemeral=True
            )
        except Exception as e:
            print(e)
            await interaction.response.send_message(
                ":x: Please try **syncing** the staff list first before trying again. If this issue persists, DM <@692254240290242601>.",
                ephemeral=True
            )

    async def sync_all_servers(self, interaction):
        """Sync roles across all servers based on staff server"""
        guild_staff = interaction.client.get_guild(STAFF_SERVER_ID)
        if not guild_staff:
            return

        message = "\n"

        # Get active staff members from staff server
        active_staff = {}
        for role_id in STAFF_SERVER_ROLES:
            role = guild_staff.get_role(role_id)
            if role:
                for member in role.members:
                    existing = active_staff.get(member.id)
                    index = STAFF_SERVER_ROLES.index(role_id)
                    if existing is None or index < existing:
                        active_staff[member.id] = index  # keep highest staff rank

        # Process MAIN and SUPPORT servers
        servers = [
            (MAIN_SERVER_ID, MAIN_SERVER_ROLES),
            (SUPPORT_SERVER_ID, SUPPORT_SERVER_ROLES),
        ]

        for server_id, role_ids in servers:
            guild = interaction.client.get_guild(server_id)
            if not guild:
                continue

            print(f"\n[SYNC] Processing server: {guild.name} ({server_id})")
            message += f"\n**Synced `{guild.name}` staff roles:**\n"

            for member in guild.members:
                current_roles = [r for r in member.roles if r.id in role_ids]
                if not current_roles and member.id not in active_staff:
                    continue

                if member.id in active_staff:
                    highest_index = active_staff[member.id]
                    highest_role_id = role_ids[highest_index]
                    highest_role = guild.get_role(highest_role_id)

                    # Remove all incorrect staff roles
                    roles_to_remove = [r for r in current_roles if r.id != highest_role_id]
                    if roles_to_remove:
                        names = ", ".join(r.name for r in roles_to_remove)
                        print(f"[CLEANUP] {member} in {guild.name}: removing {names}")
                        await member.remove_roles(*roles_to_remove, reason="Keep only highest staff role")
                        message += f"-# `[CLEANUP]` {member} had multiple roles, removed: {names}\n"

                    # Add highest role if missing
                    if highest_role and highest_role not in member.roles:
                        print(f"[ADD] {member} in {guild.name}: adding {highest_role.name}")
                        await member.add_roles(highest_role, reason="Ensure correct highest staff role")
                        message += f"-# `[ADD]` {member} was missing highest role, added: {highest_role.name}\n"
                else:
                    # Member should not have any staff roles
                    for role in current_roles:
                        print(f"[REMOVE] {member} is not active staff, removing {role.name} in {guild.name}")
                        await member.remove_roles(role, reason="User not in staff server")
                        message += f"-# `[REMOVE]` {member} is not active staff, removing {role.name} in {guild.name}\n"

        return message


class RefreshStaffView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="View Raw List",
        style=discord.ButtonStyle.blurple,
        custom_id="raw",
        emoji="🗒️",
    )
    async def raw(self, interaction: discord.Interaction, button: discord.ui.Button):
        message = f"{interaction.message.embeds[0].title}\n{interaction.message.embeds[0].description}"
        pattern = r"`.*?`"
        cleaned_message = re.sub(pattern, "", message, flags=re.DOTALL)
        await interaction.response.send_message(cleaned_message, ephemeral=True)

    @discord.ui.button(
        label="Refresh",
        style=discord.ButtonStyle.grey,
        custom_id="refresh",
        emoji="<:refresh:1048779043287351408>",
    )
    async def refresh(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        guild = interaction.client.get_guild(1136662635039952988)
        roles = [
            1136672543466598592,  # owner
            1136672547270819900,  # executive
            1136672551729381418,  # manager
            1290543539368759429,  # senior admin
            1136672556322128034,  # admin
            1136672555214852106,  # developer
            1232589300428832820,  # senior mod
            1136672558469615748,  # mod
            1172845504414097439,  # helper
        ]
        emotes = [
            "<:mysticraft_owner:1267004112332001303>",
            "<:mysticraft_executive:1267015078675222548>",
            "<:mysticraft_manager:1267012427946393641>",
            "<:mysticraft_sradmin:1294524850542739496>",
            "<:mysticraft_admin:1267020293134614620>",
            "<:mysticraft_dev:1267019102200008704>",
            "<:mysticraft_srmod:1267014449844457564>",
            "<:mysticraftlogo:1263829753366974535>",  # mod
            "<:mysticraft_helper:1267016346584223836>",
        ]
        msg = ""

        for roleID in roles:
            role = guild.get_role(roleID)
            index = roles.index(roleID)
            roleName = role.name
            msg = f"{msg}\n{emotes[index]} **[{len(role.members)}] {roleName}**\n"
            if len(role.members) == 0:
                msg = f"{msg}N/A\n"
                continue
            for member in role.members:
                msg = f"{msg}- {member.mention} `({member.id})`\n"

        embed = discord.Embed(
            title="<:mysticraftlogo:1141390665842970644> Staff List <:mysticraftlogo:1141390665842970644> ",
            description=f"---------------------------\n{msg}",
            colour=0x13C6F0,
        )
        embed.set_footer(
            text='If some of the users look like <@692254240290242601> to you, click "View Raw List".'
        )
        await interaction.message.edit(embed=embed, view=RefreshStaffView())
        await interaction.response.send_message(
            "<:refresh:1048779043287351408> The staff list is successfully refreshed!",
            ephemeral=True,
        )


class ServerLeaveButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Leave", style=discord.ButtonStyle.green, custom_id="leaveserver"
    )
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            serverID = int(interaction.message.embeds[0].description.split("**")[4])
            server = interaction.client.get_guild(serverID)
            await server.leave()
            await interaction.response.send_message(f"I left {server.name}")
        except Exception as e:
            await interaction.response.send_message(
                f"Something went wrong...\n```{e}```", ephemeral=True
            )


class SelfRoles(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Events", style=discord.ButtonStyle.grey, custom_id="events", emoji="🎮"
    )
    async def events(self, interaction: discord.Interaction, button: discord.ui.Button):
        alreadyHave = False
        for role in interaction.user.roles:
            if "Events" == role.name:
                alreadyHave = True
        role = discord.utils.get(interaction.guild.roles, name="Events")
        if alreadyHave:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(
                "You **no longer** have the <@&1136672595706646548> role.",
                ephemeral=True,
            )
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(
                "You have **obtained** the <@&1136672595706646548> role.",
                ephemeral=True,
            )

    @discord.ui.button(
        label="Giveaways",
        style=discord.ButtonStyle.grey,
        custom_id="giveaways",
        emoji="🎉",
    )
    async def giveaways(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        alreadyHave = False
        for role in interaction.user.roles:
            if "Giveaways" == role.name:
                alreadyHave = True
        role = discord.utils.get(interaction.guild.roles, name="Giveaways")
        if alreadyHave:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(
                "You **no longer** have the <@&1136672596470018111> role.",
                ephemeral=True,
            )
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(
                "You have **obtained** the <@&1136672596470018111> role.",
                ephemeral=True,
            )

    @discord.ui.button(
        label="Updates",
        style=discord.ButtonStyle.grey,
        custom_id="updates",
        emoji="👀",
    )
    async def sneakpeak(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        alreadyHave = False
        for role in interaction.user.roles:
            if "Updates" == role.name:
                alreadyHave = True
        role = discord.utils.get(interaction.guild.roles, name="Updates")
        if alreadyHave:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(
                "You **no longer** have the <@&1144344504590151700> role.",
                ephemeral=True,
            )
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(
                "You have **obtained** the <@&1144344504590151700> role.",
                ephemeral=True,
            )

    @discord.ui.button(
        label="Polls", style=discord.ButtonStyle.grey, custom_id="polls", emoji="🗳️"
    )
    async def polls(self, interaction: discord.Interaction, button: discord.ui.Button):
        alreadyHave = False
        for role in interaction.user.roles:
            if "Polls" == role.name:
                alreadyHave = True
        role = discord.utils.get(interaction.guild.roles, name="Polls")
        if alreadyHave:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(
                "You **no longer** have the <@&1136672598210662461> role.",
                ephemeral=True,
            )
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(
                "You have **obtained** the <@&1136672598210662461> role.",
                ephemeral=True,
            )


class onMsg(commands.Cog):
    def __init__(self, bot):
        self.client = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.client.user or message.author.bot == True or not message.guild:
            return
        
        # MrBeast scam detection: 4 attachments all named "image.jpeg"
        if len(message.attachments) >= 4 or "check my bio" in message.content.lower():
            # if all(attachment.filename == "image.jpeg" for attachment in message.attachments):
                try:
                    await message.delete()
                    shame_embed = discord.Embed(
                        description=f"🚨 {message.author.mention}'s account likely got hacked. Deleted spam message.\nDon't click on suspicious links, even if they come from your friends!",
                        color=discord.Color.red()
                    ).set_footer(text="Bypass this filter by uploading images one at a time.")
                    await message.channel.send(content=message.author.mention, embed=shame_embed)
                except Exception as e:
                    print(f"Error handling MrBeast scam spam: {e}")
                return

        if message.content == "mc!ticketmove":
            source_cat_id = 1338567301427101726

            # Define the category mapping
            mapping = {
                "support": 1462026697024213024,
                "application": 1462026742486011934,
                "testing": 1462026779823833211,
                "migration": 1462026806335897725
            }

            # Find the source category object
            source_category = discord.utils.get(message.guild.categories, id=source_cat_id)

            if not source_category:
                return await message.channel.send("❌ Source category not found.")

            # 1. Get channels sorted by their position in the list
            # 2. Skip the first channel using [1:]
            channels = sorted(source_category.channels, key=lambda c: c.position)
            to_process = channels[1:]

            moved_count = 0

            for channel in to_process:
                x = channel.name.lower()

                # Skip if "flag" is in the name
                if "flag" in x:
                    continue

                target_id = None

                # Match keywords for category selection
                if "support" in x:
                    target_id = mapping["support"]
                elif "application" in x:
                    target_id = mapping["application"]
                elif "testing" in x:
                    target_id = mapping["testing"]
                elif "migration" in x:
                    target_id = mapping["migration"]

                if target_id:
                    target_category = message.guild.get_channel(target_id)

                    if target_category:
                        # Rename logic: remove everything from the first dash onwards
                        # e.g., "ticket-1234" becomes "ticket"
                        new_name = channel.name.split('-')[0]

                        try:
                            await channel.edit(
                                name=new_name,
                                category=target_category,
                                sync_permissions=True
                            )
                            moved_count += 1
                        except discord.Forbidden:
                            print(f"Missing permissions to move {channel.name}")
                        except Exception as e:
                            print(f"Error: {e}")

            await message.channel.send(f"✅ Successfully moved and renamed {moved_count} channels.")
            
        if message.content == "mc!fixnames":
            # List of all target category IDs to check
            target_category_ids = [
                1462026697024213024, # General Support
                1462026742486011934, # Tester Application
                1462026779823833211, # High Tier Testing
                1462026806335897725  # Tier Migration
            ]

            fixed_count = 0
            error_count = 0

            for cat_id in target_category_ids:
                category = message.guild.get_channel(cat_id)
                if not category or not isinstance(category, discord.CategoryChannel):
                    continue

                for channel in category.text_channels:
                    # Check if there is a description (topic) to read the ID from
                    if not channel.topic:
                        continue

                    # Attempt to find a User ID in the description
                    # This assumes the ID is either the whole topic or clearly present
                    try:
                        # Logic: Extracting numbers from the topic string
                        import re
                        user_ids = re.findall(r'\d{17,19}', channel.topic)

                        if user_ids:
                            user_id = int(user_ids[0])
                            user = await self.client.fetch_user(user_id)

                            # New name logic: "currentname-username"
                            new_name = f"{channel.name}-{user.name}"

                            await channel.edit(name=new_name)
                            fixed_count += 1
                        else:
                            print(f"No ID found in topic for {channel.name}")

                    except Exception as e:
                        print(f"Could not fix {channel.name}: {e}")
                        error_count += 1

            await message.channel.send(f"🛠 Fix complete! Renamed {fixed_count} channels. (Errors: {error_count})")
        
        if message.content.lower() == "mc!listguilds":
            guild_list = "\n".join([f"- {g.name} (`{g.id}`)" for g in self.client.guilds])
            await message.channel.send(f"**Guilds I'm in:**\n{guild_list}")
                
        if (
            message.author.id == 692254240290242601
            and message.content == "mc!leaveservers"
        ):
            for guild in self.client.guilds:
                name = guild.name

                if "mysticraft" not in name.lower() and guild.id != 783528750474199041:
                    await guild.leave()

                    await message.channel.send(f"Left **{name}**", delete_after=10)
        
        if hasattr(message.channel, 'category') and message.channel.category.id in [1374959236420730890, 1374959248806510662, 1374959224752312362, 1374959260458287125, 1374959285716647947, 1374959273930391592, 1338567301427101726, 1462026697024213024, 1462026742486011934, 1462026779823833211, 1462026806335897725]:
            try:
                if message.channel.name.startswith("🚫"):
                    return

                user = message.guild.get_member(int(message.channel.topic.replace("🚫", "").strip()))
                if message.author == user or message.author.bot:
                    return
                
                if message.channel.category.id != 1338567301427101726: # Support server
                    async for msg in message.channel.history(limit=None):
                        if msg.author == message.author and msg != message:
                            return

                    ref = db.reference("/Staff Claim")
                    claim_database = ref.get()
                    timestamps = []

                    if claim_database:
                        for key, val in claim_database.items():
                            if val['User ID'] == message.author.id:
                                timestamps = val["List"]
                                db.reference('/Staff Claim').child(key).delete()
                                break

                    timestamps.append(int(time.time()))
                    data = {
                        "contributions": {
                            "User ID": message.author.id,
                            "List": timestamps
                        }
                    }

                    for key, value in data.items():
                        ref.push().set(value)
                    
                if message.channel.name.startswith("⭕") or message.channel.name.startswith("⭕️") or message.channel.name.startswith("⚠️"): # Support server + Tierlist server
                    newName = f"🟡{message.channel.name[1:]}"
                    await message.channel.edit(topic=message.channel.topic, name=newName)

            except Exception as e:
                print(f"Error tracking staff contribution: {e}")
                
        if message.author.id in [692254240290242601, 840972960793100309] and "mc!getDMs" in message.content:
            uid = int(message.content.split(" ")[1].strip())
            # await message.channel.send("Loading...")

            member = await self.client.fetch_user(uid)
            await member.create_dm()

            # Fetch all DMs
            messages = [msg async for msg in member.dm_channel.history(limit=None)]

            # Create the HTML file
            filename = f"./commands/Tickets/transcript/DMs_{member.id}.html"
            with open(filename, "w") as f:
                f.write(
                    f"<title>{member.name}</title>"
                    f"<body style='background-color: #303338; color: white; font-family: sans-serif, Arial; padding: 10px;'>"
                )

                last_user_id = None
                for msg in reversed(messages):  # Oldest first
                    avatar = ""
                    if msg.author.id != last_user_id:
                        avatar = (
                            f"<img src='{msg.author.avatar.url}' height='50px' style='border-radius: 50%'> "
                            f"<span style='position: relative;top: -30px;color:{msg.author.color};'>"
                            f"{msg.author.name} <code>({msg.author.id})</code></span>"
                        )
                        last_user_id = msg.author.id

                    # Add message content
                    if msg.content:
                        f.write(
                            f"{avatar}<p style='position: relative;left: 54px;top:-37px;'>{msg.content}</p>"
                        )

                    # Add attachments
                    for attachment in msg.attachments:
                        if any(ext in attachment.proxy_url for ext in [".png", ".jpg", ".gif"]):
                            f.write(
                                f"{avatar}<p style='position: relative;left: 50px;'>"
                                f"<img src='{attachment.proxy_url}' width='25%'></p>"
                            )
                        elif any(ext in attachment.proxy_url for ext in [".mp4", ".mov", ".mp3", ".wav", ".m4a", ".wma", ".wmv"]):
                            f.write(
                                f"{avatar}<br><br><div style='background-color: #a9a9a9;padding: 6px;border-radius: 2px;width:20%;"
                                f"vertical-align:middle;position: relative;left: 50px;'>"
                                f"<a href='{attachment.proxy_url}' download style='color: white;text-decoration:none'>"
                                f"<img src='https://i.pinimg.com/originals/d0/78/22/d078228e50c848f289e39872dcadf49d.png' height='20px'>&nbsp;&nbsp;&nbsp;&nbsp;"
                                f"{attachment.filename}</a></div>"
                            )
                        else:
                            f.write(
                                f"{avatar}<p style='position: relative;left: 50px;'>"
                                f"<i>Attachment with unsupported file format</i></p>"
                            )

                    # Add embeds
                    for embed in msg.embeds:
                        if embed.title or embed.description:
                            f.write(avatar)
                        if embed.title:
                            f.write(
                                f"<p style='position: relative;left: 50px;border-left: 8px solid {embed.color};padding-left:4px;'>"
                                f"<b>{embed.title}</b></p>"
                            )
                        if embed.description:
                            f.write(
                                f"<p style='position: relative;left: 50px;border-left: 8px solid {embed.color};padding-left:4px;'>"
                                f"<small>{embed.description}</small></p>"
                            )

                await message.channel.send(f"Transcript saved as `DMs_{member.id}.html`.", file=discord.File(filename))
                
        elif message.content == "mc!panel":
            from commands.Tickets.summary import Stats
            await message.channel.send(view=Stats())

                
        mod_log_channel_id = 1373894426811826288  # Channel to send the extra log to
        target_role_id = 1373882802084511754  # Role ID to check
        guild_id = 1373869107484688436  # Guild ID check

        if len(message.raw_mentions) > 0 and message.guild.id == guild_id:
            for mentionedUserID in message.raw_mentions:
                user = message.guild.get_member(mentionedUserID)
                if message.guild.get_role(target_role_id) in user.roles and message.channel.topic and message.channel.topic.isdigit():
                    await message.delete()

                    warning_embed = discord.Embed(
                        title=":warning: Please **DO NOT** ping the staff team in tickets!",
                        description=(
                            "Unnecessary and excessive pings will only **delay response times** rather than speeding them up. "
                            "Your ticket will be 🚫 **closed** and :no_entry: **blacklisted** if you continue to do so. "
                            "Rest assured, your ticket will be handled as soon as our staff members are available. Thank you for your patience."
                        ),
                        color=discord.Color.red()
                    )
                    await message.channel.send(embed=warning_embed, delete_after=30)

                    # Build and send log embed
                    log_channel = message.guild.get_channel(mod_log_channel_id)
                    log_embed = discord.Embed(
                        description=(
                            f"**Message sent by** {message.author.mention} deleted in {message.channel.mention}\n"
                            f"{message.content}"
                        ),
                        color=0x1ec7f1
                    )
                    log_embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url if message.author.avatar else None)
                    log_embed.add_field(name="Author ID", value=f"{message.author.id}", inline=False)
                    log_embed.add_field(name="Ticket ID", value=f"{message.channel.id}", inline=False)
                    log_embed.timestamp = datetime.datetime.now(datetime.timezone.utc)

                    await log_channel.send(embed=log_embed)
                    break

        if "mc!selfroles" in message.content:
            embed = discord.Embed(
                title="✨ Choose your Ping Roles",
                description=(
                    "Stay in the loop by selecting the roles that matter to you. "
                    "React below to receive pings for:\n\n"
                    "🎮 **Events** – Never miss out on our fun events and activities!\n"
                    "🎉 **Giveaways** – Be the first to know about our exciting giveaways!\n"
                    "👀 **Updates** – Get exclusive early access to upcoming features and changes!\n"
                    "📊 **Polls** – Have your voice heard in server polls and decisions!"
                ),
                color=0x13C6F0,
            )
            embed.set_footer(text="Click again to remove the role from you.")

            await message.channel.send(embed=embed, view=SelfRoles())
            
        
                
        if message.content == "mc!staffv2":
            guild = self.client.get_guild(STAFF_SERVER_ID)
            msgs = []
            for i, role_id in enumerate(STAFF_SERVER_ROLES):
                role = guild.get_role(role_id)
                if not role:
                    continue

                msg = f"{EMOTES[i]} **[{len(role.members)}] {role.name.split('•')[1].strip()}**\n"
                if not role.members:
                    msg += "N/A\n"
                else:
                    for member in role.members:
                        msg += f"- {member.mention} `({member.id})`\n"
                msgs.append(msg)

            # Update message
            new_view = RefreshStaffV2View()

            # Create embed
            embed = discord.Embed(
                title="<:mysticraftlogo:1141390665842970644> MystiCraft Staff List",
                description="\n".join(msgs),
                color=0x13C6F0
            )

            msg = await message.channel.send(embed=embed, view=new_view)
            new_view.message = msg


        if message.content == "mc!staff":
            guild = self.client.get_guild(1136662635039952988)
            roles = [
                1136672543466598592,  # owner
                1136672547270819900,  # executive
                1136672551729381418,  # manager
                1290543539368759429,  # senior admin
                1136672556322128034,  # admin
                1136672555214852106,  # developer
                1232589300428832820,  # senior mod
                1136672558469615748,  # mod
                1172845504414097439,  # helper
            ]
            emotes = [
                "<:mysticraft_owner:1267004112332001303>",
                "<:mysticraft_executive:1267015078675222548>",
                "<:mysticraft_manager:1267012427946393641>",
                "<:mysticraft_sradmin:1294524850542739496>",
                "<:mysticraft_admin:1267020293134614620>",
                "<:mysticraft_dev:1267019102200008704>",
                "<:mysticraft_srmod:1267014449844457564>",
                "<:mysticraftlogo:1263829753366974535>",  # mod
                "<:mysticraft_helper:1267016346584223836>",
            ]
            msg = ""

            for roleID in roles:
                role = guild.get_role(roleID)
                index = roles.index(roleID)
                roleName = role.name
                msg = f"{msg}\n{emotes[index]} **[{len(role.members)}] {roleName}**\n"
                if len(role.members) == 0:
                    msg = f"{msg}N/A\n"
                    continue
                for member in role.members:
                    msg = f"{msg}- {member.mention} `({member.id})`\n"

            embed = discord.Embed(
                title="<:mysticraftlogo:1141390665842970644> Staff List <:mysticraftlogo:1141390665842970644> ",
                description=f"---------------------------\n{msg}",
                colour=0x13C6F0,
            )

            embed.set_footer(
                text='If some of the users look like <@692254240290242601> to you, click "View Raw List".'
            )

            await message.channel.send(embed=embed, view=RefreshStaffView())

        if (
            message.author.id == 692254240290242601
            and message.content == "mc!allservers"
        ):
            for guild in self.client.guilds:
                embed = discord.Embed(
                    description=f"""
        **Server Name:** {guild.name}
        **Server ID:** {guild.id}
        **Members Count:** {len(guild.members)}
        """,
                    colour=0x2DC6F9,
                )
                try:
                    embed.set_footer(icon_url=guild.icon.url, text=guild.name)
                except Exception:
                    pass
                embed.timestamp = datetime.datetime.utcnow()
                try:
                    server_invite = await guild.text_channels[0].create_invite(
                        max_age=0, max_uses=0
                    )
                    await message.channel.send(
                        f"{server_invite}", embed=embed, view=ServerLeaveButton()
                    )
                except Exception:
                    await message.channel.send(
                        f"`SERVER DISABLED INVITE CREATION`", embed=embed
                    )

        if (
            message.author.id == 692254240290242601
            and message.content == "mc!removeserverinvites"
        ):
            for server in self.client.guilds:
                try:
                    invites = await server.invites()
                    for invite in invites:
                        if invite.inviter.id == 732422232273584198:
                            await invite.delete()
                            await message.channel.send(
                                f"Deleted `{invite.code}` in **{server.name}**"
                            )
                except Exception as e:
                    await message.channel.send(f"```{e}```")

        if message.guild.id in [1136662635039952988, 1304829305443844096] and (
            message.content.lower() == "ip"
            or message.content.lower() == "port"
            or message.content.lower() == "info"
        ):
            embed = discord.Embed(
                title="To connect to MystiCraft, use the following:",
                color=0x3779F5,
                description="""➥ IP: **play.mysticraft.xyz**
      ➥ Port: **19132**
      ➥ Version: `1:16 - latest`
      
      If you have any issues connecting to the server, feel free to open a ticket at <#1136672651209871541>.""",
            )
            await message.channel.send(embed=embed)

        elif message.guild.id in [1136662635039952988, 1304829305443844096] and (
            message.content.lower() == "store" or message.content.lower() == "shop"
        ):
            embed = discord.Embed(
                description="**Store: https://store.mysticraft.xyz/**", color=0x3779F5
            )
            button = Button(
                label="MystiCraft Shop",
                style=discord.ButtonStyle.link,
                url="https://store.mysticraft.xyz/",
            )
            view = View()
            view.add_item(button)
            await message.channel.send(embed=embed, view=view)

        elif message.guild.id in [1136662635039952988, 1304829305443844096] and (
            message.content.lower() == "support" or message.content.lower() == "help"
        ):
            embed = discord.Embed(
                description="Looking for support? Don't worry, we got your back!",
                color=0x3779F5,
            )
            button = Button(
                label="Head over to #🎫〡support channel",
                style=discord.ButtonStyle.link,
                url="https://discord.com/channels/1136662635039952988/1136672651209871541",
            )
            view = View()
            view.add_item(button)
            await message.channel.send(embed=embed, view=view)

        elif message.guild.id in [1136662635039952988, 1304829305443844096] and (
            message.content.lower() == "socials"
        ):
            embed = discord.Embed(color=0x3779F5)
            embed.title = "MystiCraft Social Links"
            embed.description = """The following are the links to our social media! Make sure to drop a follow!"""
            twitter = Button(
                label="Twitter",
                style=discord.ButtonStyle.link,
                url="https://twitter.com/playmysticraft",
                emoji="<:Twitter:1078760886447128587>",
            )
            instagram = Button(
                label="Instagram",
                style=discord.ButtonStyle.link,
                url="https://instagram.com/playmysticraft",
                emoji="<:Instagram:1078761149836832838>",
            )
            tiktok = Button(
                label="TikTok",
                style=discord.ButtonStyle.link,
                url="https://www.tiktok.com/@mysticraftnetwork",
                emoji="<:TikTok:1078761557850333194>",
            )
            website = Button(
                label="Website",
                style=discord.ButtonStyle.link,
                url="https://mysticraft.xyz/",
                emoji="<:website:1078761962000896120>",
            )
            discordlink = Button(
                label="Discord",
                style=discord.ButtonStyle.link,
                url="https://discord.mysticraft.xyz",
                emoji="<:discord:1078762369473335397>",
            )
            ytlink = Button(
                label="YouTube",
                style=discord.ButtonStyle.link,
                url="https://youtube.com/@ninjamcyt",
                emoji="<:youtube:1147246329622442044>",
            )
            view = View()
            view.add_item(twitter)
            view.add_item(instagram)
            view.add_item(tiktok)
            view.add_item(website)
            view.add_item(discordlink)
            view.add_item(ytlink)
            await message.channel.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(onMsg(bot))
