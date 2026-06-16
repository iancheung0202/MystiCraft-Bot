import discord
import datetime
import re

from discord.ui import Button, View, Select, UserSelect

from constants import ROLE_IDS, SERVER_IDS, EMOTES

ORDERED_STAFF_KEYS = ["owner", "manager", "senior_admin", "admin", "developer", "senior_mod", "mod", "helper"]

ABBREVIATIONS = {
    "owner": "Owner",
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

        self.user_select = UserSelect(placeholder="Select staff member", custom_id="user_select")
        self.user_select.callback = self.user_callback
        self.add_item(self.user_select)

        role_options = []
        for key in ORDERED_STAFF_KEYS:
            role_id = ROLE_IDS[SERVER_IDS["staff"]]["roles"][key]
            role_name = self.get_role_name(role_id)
            display_name = role_name.split("•")[1].strip() if "•" in role_name else role_name
            role_options.append(
                discord.SelectOption(label=display_name, value=str(role_id), emoji=EMOTES[key])
            )
        role_options.append(discord.SelectOption(label="Member", value="member", emoji="👤"))
        self.role_select = Select(placeholder="Select new rank", options=role_options, custom_id="role_select")
        self.role_select.callback = self.role_callback
        self.add_item(self.role_select)

        self.submit_button = Button(label="Submit", style=discord.ButtonStyle.green, disabled=True, custom_id="rank_submit")
        self.submit_button.callback = self.submit_callback
        self.add_item(self.submit_button)

    def get_role_name(self, role_id):
        guild = self.bot.get_guild(SERVER_IDS["staff"])
        role = guild.get_role(role_id) if guild else None
        return role.name if role else f"Role {role_id}"

    def current_rank(self, user_id: int) -> str:
        """Return a display string for the member's current highest staff rank, or 'Member'."""
        guild = self.bot.get_guild(SERVER_IDS["staff"])
        if not guild:
            return "Unknown"
        member = guild.get_member(user_id)
        if not member:
            return "Not in staff server"
        member_role_ids = {r.id for r in member.roles}
        for key in ORDERED_STAFF_KEYS:
            rid = ROLE_IDS[SERVER_IDS["staff"]]["roles"][key]
            if rid in member_role_ids:
                return ABBREVIATIONS.get(key, key.title())
        return "Member"

    def build_preview(self) -> str:
        """Build the ephemeral message content reflecting current selection state."""
        lines = ["Please select a staff member and assign their new rank using the dropdowns below."]

        if self.target_user:
            current_rank = self.current_rank(self.target_user.id)
            lines.append(f"\n**Selected:** {self.target_user.mention}")
            lines.append(f"-# <:reply:1036792837821435976> Current rank: **{current_rank}**")

        if self.target_user and self.role_value:
            if self.role_value == "member":
                new_rank_label = "Member"
            else:
                new_role_index = STAFF_SERVER_ROLES.index(int(self.role_value))
                new_rank_label = ABBREVIATIONS.get(ORDERED_STAFF_KEYS[new_role_index], "Unknown")

            current_rank = self.current_rank(self.target_user.id)

            current_index = None
            guild = self.bot.get_guild(SERVER_IDS["staff"])
            if guild:
                member = guild.get_member(self.target_user.id)
                if member:
                    for key in ORDERED_STAFF_KEYS:
                        if ROLE_IDS[SERVER_IDS["staff"]]["roles"][key] in {r.id for r in member.roles}:
                            current_index = ORDERED_STAFF_KEYS.index(key)
                            break

            if self.role_value == "member":
                new_index = len(ORDERED_STAFF_KEYS)  # below all ranks
            else:
                new_index = STAFF_SERVER_ROLES.index(int(self.role_value))

            if current_index is None:
                action_label = "promote" if self.role_value != "member" else "no change"
            elif new_index < current_index:
                action_label = "promote"
            elif new_index > current_index:
                action_label = "demote"
            else:
                action_label = "no change"

            action_icon = {"promote": "⬆️", "demote": "⬇️", "no change": "↔️"}.get(action_label, "")
            lines.append(f"-# <:reply:1036792837821435976> New rank: **{new_rank_label}** {action_icon} *(will {action_label})*")

        elif self.role_value and not self.target_user:
            lines.append("\n*Select a staff member as well.*")

        return "\n".join(lines)

    async def role_callback(self, interaction: discord.Interaction):
        self.role_value = self.role_select.values[0] if self.role_select.values else None
        self.submit_button.disabled = not (self.target_user and self.role_value)
        await interaction.response.edit_message(content=self.build_preview(), view=self)

    async def user_callback(self, interaction: discord.Interaction):
        self.target_user = self.user_select.values[0] if self.user_select.values else None
        self.submit_button.disabled = not (self.target_user and self.role_value)
        await interaction.response.edit_message(content=self.build_preview(), view=self)

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
            f"✅ **{action.title()}** {staff_member.mention} to **{new_role_mention}**. \n"
            f"<:reply:1048779043287351408> **Please click `Sync` to update the staff list and sync roles on the Discord servers!**",
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
        if user_highest_index is None or user_highest_index > 1:
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

        guild_tierlist = interaction.client.get_guild(SERVER_IDS["tierlist"])
        tierlist_staff_role_id = ROLE_IDS[SERVER_IDS["tierlist"]]["roles"]["staff"]
        tierlist_staff_role = guild_tierlist.get_role(tierlist_staff_role_id) if guild_tierlist else None

        staff_server_tierlist_role_id = ROLE_IDS[SERVER_IDS["staff"]]["tierlist_staff"]
        guild_staff = interaction.client.get_guild(SERVER_IDS["staff"])
        staff_server_tierlist_role = guild_staff.get_role(staff_server_tierlist_role_id) if guild_staff else None

        if guild_tierlist and tierlist_staff_role and staff_server_tierlist_role and guild_staff:
            tierlist_member_ids = {m.id for m in tierlist_staff_role.members}
            staff_member_in_staff_server = guild_staff.get_member(member.id)
            if staff_member_in_staff_server:
                has_tierlist_staff = member.id in tierlist_member_ids
                has_role_currently = staff_server_tierlist_role in staff_member_in_staff_server.roles
                if has_tierlist_staff and not has_role_currently:
                    await staff_member_in_staff_server.add_roles(staff_server_tierlist_role, reason="Tierlist staff role sync")
                elif not has_tierlist_staff and has_role_currently:
                    await staff_member_in_staff_server.remove_roles(staff_server_tierlist_role, reason="No longer tierlist staff")

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
    

class EditTierlistStaffView(View):
    def __init__(self, bot):
        super().__init__(timeout=120)
        self.bot = bot
        self.target_user = None

        self.user_select = UserSelect(placeholder="Select a member", custom_id="tierlist_user_select")
        self.user_select.callback = self.user_callback
        self.add_item(self.user_select)

        self.submit_button = Button(label="Submit", style=discord.ButtonStyle.green, disabled=True, custom_id="tierlist_submit")
        self.submit_button.callback = self.submit_callback
        self.add_item(self.submit_button)

    def get_tierlist_status(self, user_id: int) -> tuple[bool, bool]:
        """Return (has_staff_server_role, has_tierlist_server_role)."""
        guild_staff = self.bot.get_guild(SERVER_IDS["staff"])
        guild_tierlist = self.bot.get_guild(SERVER_IDS["tierlist"])

        has_staff_role = False
        if guild_staff:
            sm = guild_staff.get_member(user_id)
            if sm:
                ts_role_id = ROLE_IDS[SERVER_IDS["staff"]]["tierlist_staff"]
                has_staff_role = any(r.id == ts_role_id for r in sm.roles)

        has_tierlist_role = False
        if guild_tierlist:
            tm = guild_tierlist.get_member(user_id)
            if tm:
                tl_role_id = ROLE_IDS[SERVER_IDS["tierlist"]]["roles"]["staff"]
                has_tierlist_role = any(r.id == tl_role_id for r in tm.roles)

        return has_staff_role, has_tierlist_role

    async def user_callback(self, interaction: discord.Interaction):
        self.target_user = self.user_select.values[0] if self.user_select.values else None

        if self.target_user:
            self.submit_button.disabled = False
            has_staff_role, has_tierlist_role = self.get_tierlist_status(self.target_user.id)
            is_tierlist_staff = has_staff_role or has_tierlist_role

            status_lines = []
            if has_staff_role:
                status_lines.append(f"-# <:reply:1036792837821435976> Currently **has** <@&{ROLE_IDS[SERVER_IDS['staff']]['tierlist_staff']}> role in the **staff server**")
            else:
                status_lines.append(f"-# <:reply:1036792837821435976> Currently **does not have** <@&{ROLE_IDS[SERVER_IDS['staff']]['tierlist_staff']}> role in the **staff server**")
            if has_tierlist_role:
                status_lines.append("-# <:reply:1036792837821435976> Currently **has** `@Staff` role in the **tierlist server**")
            else:
                status_lines.append("-# <:reply:1036792837821435976> Currently **does not have** `@Staff` role in the **tierlist server**")

            action_word = "**removed as** tierlist staff" if is_tierlist_staff else "**added as** tierlist staff"
            status_text = "\n".join(status_lines)

            await interaction.response.edit_message(
                content=(
                    f"Please select a staff member to toggle their tierlist staff status using the dropdown below.\n\n"
                    f"{self.target_user.mention} will be {action_word}.\n"
                    f"{status_text}"
                ),
                view=self
            )
        else:
            self.submit_button.disabled = True
            await interaction.response.edit_message(
                content=(
                    "Please select a staff member to toggle their tierlist staff status using the dropdown below."
                ),
                view=self
            )

    async def submit_callback(self, interaction: discord.Interaction):
        if not self.target_user:
            await interaction.response.send_message("❌ No user selected.", ephemeral=True)
            return

        user_roles = [r.id for r in interaction.user.roles]
        user_highest_index = None
        for idx, role_id in enumerate(STAFF_SERVER_ROLES):
            if role_id in user_roles:
                if user_highest_index is None or idx < user_highest_index:
                    user_highest_index = idx
        if user_highest_index is None or user_highest_index > 1:
            await interaction.response.send_message(
                "❌ You need Manager+ permissions to edit tierlist staff.",
                ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True, ephemeral=True)

        guild_staff = interaction.client.get_guild(SERVER_IDS["staff"])
        guild_tierlist = interaction.client.get_guild(SERVER_IDS["tierlist"])

        has_staff_role, has_tierlist_role = self.get_tierlist_status(self.target_user.id)
        is_currently_tierlist_staff = has_staff_role or has_tierlist_role

        if is_currently_tierlist_staff:
            if guild_staff:
                sm = guild_staff.get_member(self.target_user.id)
                if sm:
                    ts_role = guild_staff.get_role(ROLE_IDS[SERVER_IDS["staff"]]["tierlist_staff"])
                    if ts_role and ts_role in sm.roles:
                        await sm.remove_roles(ts_role, reason="Removed as tierlist staff")

            if guild_tierlist:
                tm = guild_tierlist.get_member(self.target_user.id)
                if tm:
                    all_tierlist_role_ids = set(ROLE_IDS[SERVER_IDS["tierlist"]]["roles"].values())
                    roles_to_remove = [r for r in tm.roles if r.id in all_tierlist_role_ids]
                    if roles_to_remove:
                        await tm.remove_roles(*roles_to_remove, reason="Removed as tierlist staff")

            action = "removed as"
        else:
            if guild_staff:
                sm = guild_staff.get_member(self.target_user.id)
                if sm:
                    ts_role = guild_staff.get_role(ROLE_IDS[SERVER_IDS["staff"]]["tierlist_staff"])
                    if ts_role and ts_role not in sm.roles:
                        await sm.add_roles(ts_role, reason="Added as tierlist staff")

            if guild_tierlist:
                tm = guild_tierlist.get_member(self.target_user.id)
                if tm:
                    tl_staff_role = guild_tierlist.get_role(ROLE_IDS[SERVER_IDS["tierlist"]]["roles"]["staff"])
                    if tl_staff_role and tl_staff_role not in tm.roles:
                        await tm.add_roles(tl_staff_role, reason="Added as tierlist staff")

            action = "added as"

        channel_id = 1066300810889273345
        log_channel = interaction.client.get_channel(channel_id)
        if log_channel:
            embed = discord.Embed(
                title="<:mysticraftlogo:1263829753366974535> MystiCraft Team Update",
                description=f"{self.target_user.mention} has been **{action}** <@&{ROLE_IDS[SERVER_IDS['staff']]['tierlist_staff']}>!",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Updated by {interaction.user.name}")
            embed.timestamp = datetime.datetime.utcnow()
            await log_channel.send(embed=embed)

        action_past = "added to" if action == "added as" else "removed from"
        await interaction.followup.send(
            f"✅ {self.target_user.mention} has been **{action_past}** Tierlist Staff.\n"
            f"<:reply:1048779043287351408> **Please click `Sync` to update the staff list and sync roles on the Discord servers!**",
            ephemeral=True
        )


class RefreshStaffView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="View Raw List", style=discord.ButtonStyle.blurple, custom_id="raw_v3", emoji="🗒️")
    async def raw(self, interaction: discord.Interaction, button: discord.ui.Button):
        content = interaction.message.embeds[0].description
        cleaned_content = re.sub(r"`\(\d+\)`", "", content)
        await interaction.response.send_message(f"{cleaned_content}", ephemeral=True)

    @discord.ui.button(label="Sync", style=discord.ButtonStyle.grey, custom_id="refresh_v3", emoji="<:refresh:1048779043287351408>")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild_staff = interaction.client.get_guild(SERVER_IDS["staff"])
        guild_tierlist = interaction.client.get_guild(SERVER_IDS["tierlist"])
        
        msgs = []
        
        tierlist_members: dict[int, discord.Member] = {}
        
        if guild_staff:
            ts_role = guild_staff.get_role(ROLE_IDS[SERVER_IDS["staff"]]["tierlist_staff"])
            if ts_role:
                for m in ts_role.members:
                    tierlist_members[m.id] = m

        if guild_tierlist:
            tl_role = guild_tierlist.get_role(ROLE_IDS[SERVER_IDS["tierlist"]]["roles"]["staff"])
            if tl_role:
                for m in tl_role.members:
                    if m.id not in tierlist_members:
                        staff_member = guild_staff.get_member(m.id) if guild_staff else None
                        tierlist_members[m.id] = staff_member or m

        seen_tierlist_ids = set()

        for key in ORDERED_STAFF_KEYS:
            role_id = ROLE_IDS[SERVER_IDS["staff"]]["roles"][key]
            role = guild_staff.get_role(role_id) if guild_staff else None
            if not role:
                continue
                
            msg = f"{EMOTES[key]} **[{len(role.members)}] {role.name.split('•')[1].strip()}**\n"
            if not role.members:
                msg += "N/A\n"
            else:
                for member in role.members:
                    if member.id in tierlist_members:
                        msg += f"- {member.mention} `({member.id})` <:mysticrafttierlist:1460527955309498550>\n"
                        seen_tierlist_ids.add(member.id)
                    else:
                        msg += f"- {member.mention} `({member.id})`\n"
            msgs.append(msg)

        tierlist_only_members = [m for m_id, m in tierlist_members.items() if m_id not in seen_tierlist_ids]

        tierlist_msg = f"<:mysticrafttierlist:1460527955309498550> **[{len(tierlist_only_members)}] Tierlist Staff Only**\n"
        if not tierlist_only_members:
            tierlist_msg += "N/A\n"
        else:
            for m in tierlist_only_members:
                tierlist_msg += f"- {m.mention} `({m.id})` <:mysticrafttierlist:1460527955309498550>\n"

        msgs.append(tierlist_msg)

        await self.sync_all_servers(interaction)
        new_view = RefreshStaffView()
        
        embed = discord.Embed(
            title="<:mysticraftlogo:1141390665842970644> MystiCraft Staff List",
            description="\n".join(msgs),
            color=0x13C6F0
        )
        
        await interaction.message.edit(embed=embed, view=new_view)
        await interaction.followup.send(
            f"<:refresh:1048779043287351408> Staff list refreshed, main staff roles synced between **main/support/staff** servers, and tierlist staff roles synced between **tierlist/staff** servers!",
            ephemeral=True
        )

    @discord.ui.button(label="Edit Staff Rank", style=discord.ButtonStyle.red, custom_id="edit_staff", emoji="✏️")
    async def edit_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        allowed_roles = STAFF_SERVER_ROLES[:3]  # Owner, Executive, Manager
        user_roles = [r.id for r in interaction.user.roles]
        if not any(role in allowed_roles for role in user_roles):
            await interaction.response.send_message("❌ Only Managers+ can edit staff roles", ephemeral=True)
            return
            
        try:
            view = EditStaffView(interaction.client)
            await interaction.response.send_message(
                view.build_preview(),
                view=view,
                ephemeral=True
            )
        except Exception as e:
            print(e)
            await interaction.response.send_message(
                ":x: Please try **syncing** the staff list first before trying again. If this issue persists, DM <@692254240290242601>.",
                ephemeral=True
            )

    @discord.ui.button(label="Edit Tierlist Staff", style=discord.ButtonStyle.blurple, custom_id="edit_tierlist_staff", emoji="<:mysticrafttierlist:1460527955309498550>")
    async def edit_tierlist_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        allowed_roles = STAFF_SERVER_ROLES[:3]  # Owner, Executive, Manager
        user_roles = [r.id for r in interaction.user.roles]
        if not any(role in allowed_roles for role in user_roles):
            await interaction.response.send_message("❌ Only Managers+ can edit tierlist staff", ephemeral=True)
            return

        await interaction.response.send_message(
            "Please select a staff member to toggle their tierlist staff status using the dropdown below.",
            view=EditTierlistStaffView(interaction.client),
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

        guild_tierlist = interaction.client.get_guild(SERVER_IDS["tierlist"])
        tierlist_staff_role_id = ROLE_IDS[SERVER_IDS["tierlist"]]["roles"]["staff"]
        tierlist_staff_role = guild_tierlist.get_role(tierlist_staff_role_id) if guild_tierlist else None

        staff_server_tierlist_role_id = ROLE_IDS[SERVER_IDS["staff"]]["tierlist_staff"]
        staff_server_tierlist_role = guild_staff.get_role(staff_server_tierlist_role_id)

        if guild_tierlist and tierlist_staff_role and staff_server_tierlist_role:
            tierlist_member_ids = {m.id for m in tierlist_staff_role.members}
            message += f"\n**Synced tierlist staff → staff server `tierlist_staff` role:**\n"

            for member_id in tierlist_member_ids:
                staff_member = guild_staff.get_member(member_id)
                if staff_member and staff_server_tierlist_role not in staff_member.roles:
                    print(f"[TIERLIST] {staff_member}: adding tierlist_staff role in staff server")
                    await staff_member.add_roles(staff_server_tierlist_role, reason="Tierlist staff role sync")
                    message += f"-# `[ADD]` {staff_member} given tierlist_staff role in staff server\n"

            for staff_member in staff_server_tierlist_role.members:
                if staff_member.id not in tierlist_member_ids:
                    print(f"[TIERLIST] {staff_member}: removing tierlist_staff role (not in tierlist server)")
                    await staff_member.remove_roles(staff_server_tierlist_role, reason="No longer tierlist staff")
                    message += f"-# `[REMOVE]` {staff_member} lost tierlist_staff role (removed from tierlist staff)\n"

        return message

async def setup(bot):
    pass