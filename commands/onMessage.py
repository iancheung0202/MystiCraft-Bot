import discord
import datetime

from discord.ext import commands
from discord.ui import Button, View, Select, UserSelect

from constants import ROLE_IDS, SERVER_IDS, EMOTES

ORDERED_STAFF_KEYS = [
    "owner", "executive", "manager", "senior_admin", 
    "admin", "developer", "senior_mod", "mod", "helper"
]

ABBREVIATIONS = {
    "owner": "Owner",
    "executive": "Executive",
    "manager": "Manager",
    "senior_admin": "Sr Admin",
    "admin": "Admin",
    "developer": "Dev",
    "senior_mod": "Sr Mod",
    "mod": "Mod",
    "helper": "Helper"
}

STAFF_SERVER_ROLES = [ROLE_IDS[SERVER_IDS["staff"]]["roles"][k] for k in ORDERED_STAFF_KEYS]
MAIN_SERVER_ROLES = [ROLE_IDS[SERVER_IDS["main"]]["roles"][k] for k in ORDERED_STAFF_KEYS]
SUPPORT_SERVER_ROLES = [ROLE_IDS[SERVER_IDS["support"]]["roles"][k] for k in ORDERED_STAFF_KEYS]
EMOTES_LIST = [EMOTES[k] for k in ORDERED_STAFF_KEYS]


def format_nickname(abbreviation: str, display_name: str) -> str:
    """Format nickname as 'Abbreviation | Name'."""
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
        for i, key in enumerate(ORDERED_STAFF_KEYS):
            role_id = ROLE_IDS[SERVER_IDS["staff"]]["roles"][key]
            role_name = self.get_role_name(role_id)
            if "•" in role_name:
                display_name = role_name.split("•")[1].strip()
            else:
                display_name = role_name
            role_options.append(
                discord.SelectOption(
                    label=display_name,
                    value=str(role_id),
                    emoji=EMOTES[key]
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
        guild = self.bot.get_guild(SERVER_IDS["staff"])
        role = guild.get_role(role_id) if guild else None
        return role.name if role else f"Role {role_id}"

    async def role_callback(self, interaction: discord.Interaction):
        self.role_value = self.role_select.values[0] if self.role_select.values else None
        await interaction.response.defer()

    async def user_callback(self, interaction: discord.Interaction):
        self.target_user = self.user_select.values[0] if self.user_select.values else None
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
        
        guild_staff = interaction.client.get_guild(SERVER_IDS["staff"])
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
            await staff_member.remove_roles(*current_staff_roles, reason="Staff role removal")
            await staff_member.kick(reason="Demoted to member")
            new_role_mention = "`Member`"
            new_staff_position = 0
        else:
            new_role_id = int(self.role_value)
            new_role = guild_staff.get_role(new_role_id)
            if not new_role:
                await interaction.response.send_message("❌ Invalid role selected", ephemeral=True)
                return
            new_staff_position = new_role.position
            
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
        user_roles = [r.id for r in user.roles]
        user_highest_index = None
        
        for idx, role_id in enumerate(STAFF_SERVER_ROLES):
            if role_id in user_roles:
                if user_highest_index is None or idx < user_highest_index:
                    user_highest_index = idx
                    
        # Only managers+ can edit (Manager index is 2)
        if user_highest_index is None or user_highest_index > 2:
            await interaction.response.send_message(
                "❌ You need Manager+ permissions to edit staff roles",
                ephemeral=True
            )
            return False

        if user.id == self.target_user.id:
            await interaction.response.send_message("❌ You cannot edit your own roles", ephemeral=True)
            return False

        target_roles = [r.id for r in self.target_user.roles]
        target_highest_index = None
        for idx, role_id in enumerate(STAFF_SERVER_ROLES):
            if role_id in target_roles:
                if target_highest_index is None or idx < target_highest_index:
                    target_highest_index = idx

        if target_highest_index is not None and target_highest_index < user_highest_index:
            await interaction.response.send_message(
                "❌ You cannot edit staff with higher rank than you",
                ephemeral=True
            )
            return False

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
        """Sync staff roles for a member across all primary structural servers"""
        current_staff_role_idx = None
        for role in member.roles:
            if role.id in STAFF_SERVER_ROLES:
                role_index = STAFF_SERVER_ROLES.index(role.id)
                if current_staff_role_idx is None or role_index < current_staff_role_idx:
                    current_staff_role_idx = role_index
        
        servers = [
            (SERVER_IDS["main"], MAIN_SERVER_ROLES),
            (SERVER_IDS["support"], SUPPORT_SERVER_ROLES),
            (SERVER_IDS["staff"], STAFF_SERVER_ROLES)
        ]
        
        for server_id, server_roles in servers:
            guild = member.guild if member.guild.id == server_id else interaction.client.get_guild(server_id)
            if not guild:
                continue
                
            target_member = guild.get_member(member.id)
            if not target_member:
                continue
                
            roles_to_remove = [guild.get_role(rid) for rid in server_roles]
            roles_to_remove = [r for r in roles_to_remove if r and r in target_member.roles]
            if roles_to_remove:
                await target_member.remove_roles(*roles_to_remove, reason="Staff role sync")
            
            if current_staff_role_idx is not None:
                new_role_id = server_roles[current_staff_role_idx]
                new_role = guild.get_role(new_role_id)
                if new_role and new_role not in target_member.roles:
                    await target_member.add_roles(new_role, reason="Staff role sync")
                    
                base_role_id = ROLE_IDS.get(server_id, {}).get("base")
                if base_role_id:
                    base_role = guild.get_role(base_role_id)
                    if base_role and base_role not in target_member.roles:
                        await target_member.add_roles(base_role, reason="Staff base role sync")
                        
                role_key = ORDERED_STAFF_KEYS[current_staff_role_idx]
                abbreviation = ABBREVIATIONS[role_key]
                new_nick = format_nickname(abbreviation, target_member.display_name)
                if target_member.nick != new_nick:
                    try:
                        await target_member.edit(nick=new_nick, reason="Update staff nickname format")
                    except discord.Forbidden:
                        pass
            else:
                base_role_id = ROLE_IDS.get(server_id, {}).get("base")
                if base_role_id:
                    base_role = guild.get_role(base_role_id)
                    if base_role and base_role in target_member.roles:
                        await target_member.remove_roles(base_role, reason="No longer staff")

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


class RefreshStaffView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="View Raw List", style=discord.ButtonStyle.blurple, custom_id="raw_v3", emoji="🗒️")
    async def raw(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"{interaction.message.embeds[0].description}", ephemeral=True)

    @discord.ui.button(label="Sync", style=discord.ButtonStyle.grey, custom_id="refresh_v3", emoji="<:refresh:1048779043287351408>")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild = interaction.client.get_guild(SERVER_IDS["staff"])
        msgs = []
        
        for key in ORDERED_STAFF_KEYS:
            role_id = ROLE_IDS[SERVER_IDS["staff"]]["roles"][key]
            role = guild.get_role(role_id)
            if not role:
                continue
                
            msg = f"{EMOTES[key]} **[{len(role.members)}] {role.name.split('•')[1].strip()}**\n"
            if not role.members:
                msg += "N/A\n"
            else:
                for member in role.members:
                    msg += f"- {member.mention} `({member.id})`\n"
            msgs.append(msg)

        await self.sync_all_servers(interaction)
        new_view = RefreshStaffView()
        
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

    @discord.ui.button(label="Edit Staff", style=discord.ButtonStyle.red, custom_id="edit_staff_v3", emoji="✏️")
    async def edit_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        allowed_roles = STAFF_SERVER_ROLES[:3]  # Owner, Executive, Manager
        user_roles = [r.id for r in interaction.user.roles]
        if not any(role in allowed_roles for role in user_roles):
            await interaction.response.send_message("❌ Only Managers+ can edit staff roles", ephemeral=True)
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
        """Sync roles across all servers based on staff server map tracking"""
        guild_staff = interaction.client.get_guild(SERVER_IDS["staff"])
        if not guild_staff:
            return

        message = "\n"
        active_staff = {}
        
        for key in ORDERED_STAFF_KEYS:
            role_id = ROLE_IDS[SERVER_IDS["staff"]]["roles"][key]
            role = guild_staff.get_role(role_id)
            if role:
                for member in role.members:
                    existing = active_staff.get(member.id)
                    index = ORDERED_STAFF_KEYS.index(key)
                    if existing is None or index < existing:
                        active_staff[member.id] = index

        servers = [
            (SERVER_IDS["main"], MAIN_SERVER_ROLES),
            (SERVER_IDS["support"], SUPPORT_SERVER_ROLES),
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

                    roles_to_remove = [r for r in current_roles if r.id != highest_role_id]
                    if roles_to_remove:
                        names = ", ".join(r.name for r in roles_to_remove)
                        print(f"[CLEANUP] {member} in {guild.name}: removing {names}")
                        await member.remove_roles(*roles_to_remove, reason="Keep only highest staff role")
                        message += f"-# `[CLEANUP]` {member} had multiple roles, removed: {names}\n"

                    if highest_role and highest_role not in member.roles:
                        print(f"[ADD] {member} in {guild.name}: adding {highest_role.name}")
                        await member.add_roles(highest_role, reason="Ensure correct highest staff role")
                        message += f"-# `[ADD]` {member} was missing highest role, added: {highest_role.name}\n"
                else:
                    for role in current_roles:
                        print(f"[REMOVE] {member} is not active staff, removing {role.name} in {guild.name}")
                        await member.remove_roles(role, reason="User not in staff server")
                        message += f"-# `[REMOVE]` {member} is not active staff, removing {role.name} in {guild.name}\n"

        return message


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
                    ).set_footer(text="Bypass this filter by not uploading 4 images at a time.")
                    await message.channel.send(content=message.author.mention, embed=shame_embed)
                except Exception as e:
                    print(f"Error handling MrBeast scam spam: {e}")
                return
        
        if message.content.lower() == "mc!guilds":
            guild_list = "\n".join([f"- {g.name} (`{g.id}`)" for g in self.client.guilds])
            await message.channel.send(f"**Guilds I'm in:**\n{guild_list}")

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
                
        if message.content == "mc!staff":
            guild = self.client.get_guild(SERVER_IDS["staff"])
            msgs = []
            
            for key in ORDERED_STAFF_KEYS:
                role_id = ROLE_IDS[SERVER_IDS["staff"]]["roles"][key]
                role = guild.get_role(role_id)
                if not role:
                    continue

                msg = f"{EMOTES[key]} **[{len(role.members)}] {role.name.split('•')[1].strip()}**\n"
                if not role.members:
                    msg += "N/A\n"
                else:
                    for member in role.members:
                        msg += f"- {member.mention} `({member.id})`\n"
                msgs.append(msg)

            new_view = RefreshStaffView()
            embed = discord.Embed(
                title="<:mysticraftlogo:1141390665842970644> MystiCraft Staff List",
                description="\n".join(msgs),
                color=0x13C6F0
            )

            msg = await message.channel.send(embed=embed, view=new_view)
            new_view.message = msg

        if (
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

        elif (
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

        elif (
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

        elif (
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
