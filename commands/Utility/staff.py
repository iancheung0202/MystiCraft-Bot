import discord
import datetime
import re

from discord.ui import Button, View, Select, UserSelect

from constants import ROLE_IDS, SERVER_IDS, EMOTES

ORDERED_STAFF_KEYS = ["owner", "manager", "senior_admin", "admin", "developer", "senior_mod", "mod", "helper"]
ABBREVIATIONS = {"owner": "Owner", "manager": "Manager", "senior_admin": "Sr Admin", "admin": "Admin", "developer": "Dev", "senior_mod": "Sr Mod", "mod": "Mod", "helper": "Helper"}
STAFF_SERVER_ROLES = [ROLE_IDS[SERVER_IDS["staff"]]["roles"][k] for k in ORDERED_STAFF_KEYS]
MAIN_SERVER_ROLES = [ROLE_IDS[SERVER_IDS["main"]]["roles"][k] for k in ORDERED_STAFF_KEYS]
SUPPORT_SERVER_ROLES = [ROLE_IDS[SERVER_IDS["support"]]["roles"][k] for k in ORDERED_STAFF_KEYS]
EMOTES_LIST = [EMOTES[k] for k in ORDERED_STAFF_KEYS]

def format_nickname(abbreviation: str, display_name: str) -> str:
    """Format nickname as 'Abbreviation | Name'."""
    if "|" in display_name:
        display_name = display_name.split("|", 1)[-1].strip()
    return f"{abbreviation} | {display_name}"

async def check_permissions(interaction, target_user=None, new_role_value=None):
    user_role_ids = {r.id for r in interaction.user.roles}
    user_highest_index = None
    for idx, role_id in enumerate(STAFF_SERVER_ROLES):
        if role_id in user_role_ids:
            if user_highest_index is None or idx < user_highest_index:
                user_highest_index = idx

    if user_highest_index is None or user_highest_index > 1:
        await interaction.response.send_message("❌ You need Manager+ permissions to use this panel.", ephemeral=True)
        return False

    if target_user is not None:
        if interaction.user.id == target_user.id:
            await interaction.response.send_message("❌ You cannot edit your own roles.", ephemeral=True)
            return False

        target_role_ids = {r.id for r in target_user.roles}
        target_highest_index = None
        for idx, role_id in enumerate(STAFF_SERVER_ROLES):
            if role_id in target_role_ids:
                if target_highest_index is None or idx < target_highest_index:
                    target_highest_index = idx

        if target_highest_index is not None and target_highest_index < user_highest_index:
            await interaction.response.send_message("❌ You cannot edit staff with a higher rank than you.", ephemeral=True)
            return False

        if new_role_value is not None and new_role_value != "member":
            new_role_index = STAFF_SERVER_ROLES.index(int(new_role_value))
            if new_role_index <= user_highest_index:
                await interaction.response.send_message("❌ You cannot assign roles at or above your rank.", ephemeral=True)
                return False

    return True


async def global_sync(client: discord.Client, member: discord.Member | None = None) -> str:
    """Sync roles, nicknames, and tierlist status across all servers."""
    guild_staff = client.get_guild(SERVER_IDS["staff"])
    if not guild_staff:
        return "❌ Error: Staff server not found."

    changes_performed: list[str] = []

    staff_server_tierlist_role_id = ROLE_IDS[SERVER_IDS["staff"]]["tierlist_staff"]

    if member is not None:
        sm = guild_staff.get_member(member.id)
        if sm is None:
            active_staff: dict[int, any] = {}
            target_ids = {member.id}
        else:
            active_staff = {}
            for role in sm.roles:
                if role.id in STAFF_SERVER_ROLES:
                    idx = STAFF_SERVER_ROLES.index(role.id)
                    existing = active_staff.get(sm.id)
                    if existing is None or (isinstance(existing, int) and idx < existing):
                        active_staff[sm.id] = idx
            
            if sm.id not in active_staff and any(r.id == staff_server_tierlist_role_id for r in sm.roles):
                active_staff[sm.id] = "tierlist_only"
                
            target_ids = {member.id}
    else:
        active_staff = {}
        for key in ORDERED_STAFF_KEYS:
            role_id = ROLE_IDS[SERVER_IDS["staff"]]["roles"][key]
            role = guild_staff.get_role(role_id)
            if role:
                for m in role.members:
                    idx = ORDERED_STAFF_KEYS.index(key)
                    existing = active_staff.get(m.id)
                    if existing is None or idx < existing:
                        active_staff[m.id] = idx
                        
        ts_role = guild_staff.get_role(staff_server_tierlist_role_id)
        if ts_role:
            for m in ts_role.members:
                if m.id not in active_staff:
                    active_staff[m.id] = "tierlist_only"
        target_ids = None  # means "all"

    ### Sync roles & nicknames on staff, main, and support servers
    servers = [
        (SERVER_IDS["staff"], STAFF_SERVER_ROLES),
        (SERVER_IDS["main"], MAIN_SERVER_ROLES),
        (SERVER_IDS["support"], SUPPORT_SERVER_ROLES),
    ]

    for server_id, role_ids in servers:
        guild = client.get_guild(server_id)
        if not guild:
            continue

        if target_ids is not None:
            members_to_check = [guild.get_member(mid) for mid in target_ids]
            members_to_check = [m for m in members_to_check if m is not None]
        else:
            role_id_set = set(role_ids)
            members_with_roles = {m.id for m in guild.members if any(r.id in role_id_set for r in m.roles)}
            all_ids = members_with_roles | set(active_staff.keys())
            members_to_check = [guild.get_member(mid) for mid in all_ids]
            members_to_check = [m for m in members_to_check if m is not None]

        for target_member in members_to_check:
            current_staff_roles = [r for r in target_member.roles if r.id in role_ids]

            if target_member.id in active_staff:
                highest_index = active_staff[target_member.id]
                
                if isinstance(highest_index, int):
                    correct_role_id = role_ids[highest_index]
                    correct_role = guild.get_role(correct_role_id)

                    roles_to_remove = [r for r in current_staff_roles if r.id != correct_role_id]
                    if roles_to_remove:
                        names = ", ".join(r.name for r in roles_to_remove)
                        await target_member.remove_roles(*roles_to_remove, reason="Staff role sync: keep highest only")
                        changes_performed.append(
                            f"[-] {target_member.display_name} ({guild.name}): Removed obsolete roles [{names}]"
                        )

                    roles_to_add = []
                    added_names = []
                    if correct_role and correct_role not in target_member.roles:
                        roles_to_add.append(correct_role)
                        added_names.append(correct_role.name)

                    base_role_id = ROLE_IDS.get(server_id, {}).get("base")
                    if base_role_id:
                        base_role = guild.get_role(base_role_id)
                        if base_role and base_role not in target_member.roles:
                            roles_to_add.append(base_role)
                            added_names.append(base_role.name)

                    if roles_to_add:
                        await target_member.add_roles(*roles_to_add, reason="Staff role sync")
                        changes_performed.append(
                            f"[+] {target_member.display_name} ({guild.name}): Added roles [{', '.join(added_names)}]"
                        )
                else:
                    if current_staff_roles:
                        for role in current_staff_roles:
                            await target_member.remove_roles(role, reason="Tierlist-only staff cleaning")
                            changes_performed.append(f"[x] {target_member.display_name} ({guild.name}): Removed core staff role [{role.name}]")

                if highest_index == "tierlist_only":
                    abbreviation = "Tierlist"
                else:
                    role_key = ORDERED_STAFF_KEYS[highest_index]
                    abbreviation = ABBREVIATIONS[role_key]

                new_nick = format_nickname(abbreviation, target_member.display_name)
                if target_member.nick != new_nick:
                    try:
                        await target_member.edit(nick=new_nick, reason="Staff nickname sync")
                        changes_performed.append(f"[ ] {target_member.display_name} ({guild.name}): Changed nickname to '{new_nick}'")
                    except discord.Forbidden:
                        pass

            else:
                if current_staff_roles:
                    for role in current_staff_roles:
                        await target_member.remove_roles(role, reason="User not in staff server")
                        changes_performed.append(f"[x] {target_member.display_name} ({guild.name}): Removed staff role [{role.name}] (Not in Staff Server)")

                base_role_id = ROLE_IDS.get(server_id, {}).get("base")
                if base_role_id:
                    base_role = guild.get_role(base_role_id)
                    if base_role and base_role in target_member.roles:
                        await target_member.remove_roles(base_role, reason="No longer staff")
                        changes_performed.append(f"[x] {target_member.display_name} ({guild.name}): Removed base role [{base_role.name}]")

                if target_member.nick and ("|" in target_member.nick or target_member.nick.startswith("[")):
                    try:
                        base_name = target_member.nick.split("|", 1)[-1].strip()
                        await target_member.edit(nick=base_name, reason="Clear staff nickname")
                        changes_performed.append(f"[ ] {target_member.display_name} ({guild.name}): Reset nickname to '{base_name}'")
                    except discord.Forbidden:
                        pass

    ### Sync tierlist staff roles/nicknames on staff and tierlist servers
    guild_tierlist = client.get_guild(SERVER_IDS["tierlist"])
    tierlist_staff_role_id = ROLE_IDS[SERVER_IDS["tierlist"]]["roles"]["staff"]
    tierlist_staff_role = guild_tierlist.get_role(tierlist_staff_role_id) if guild_tierlist else None

    staff_server_tierlist_role_id = ROLE_IDS[SERVER_IDS["staff"]]["tierlist_staff"]
    staff_server_tierlist_role = guild_staff.get_role(staff_server_tierlist_role_id)

    base_role_id = ROLE_IDS.get(SERVER_IDS["staff"], {}).get("base")
    staff_base_role = guild_staff.get_role(base_role_id) if base_role_id else None

    if guild_tierlist and tierlist_staff_role and staff_server_tierlist_role:
        authoritative_tierlist_ids = {m.id for m in staff_server_tierlist_role.members}

        if target_ids is not None:
            tierlist_check_ids = target_ids | {m.id for m in tierlist_staff_role.members}
        else:
            tierlist_check_ids = authoritative_tierlist_ids | {m.id for m in tierlist_staff_role.members}

        for mid in tierlist_check_ids:
            should_be_tierlist = mid in authoritative_tierlist_ids

            tierlist_member = guild_tierlist.get_member(mid)
            if tierlist_member is not None:
                has_tierlist_server_role = tierlist_staff_role in tierlist_member.roles
                if should_be_tierlist:
                    if not has_tierlist_server_role:
                        await tierlist_member.add_roles(tierlist_staff_role, reason="Tierlist staff role sync")
                        changes_performed.append(
                            f"[+] {tierlist_member.display_name} (Tierlist Server): Added role [{tierlist_staff_role.name}]"
                        )
                    
                    current_nick = tierlist_member.nick or ""
                    has_staff_format = "|" in current_nick
                    
                    if not has_staff_format:
                        new_tl_nick = format_nickname("Staff", tierlist_member.display_name)
                        if tierlist_member.nick != new_tl_nick:
                            try:
                                await tierlist_member.edit(nick=new_tl_nick, reason="Tierlist staff nickname sync")
                                changes_performed.append(
                                    f"[ ] {tierlist_member.display_name} (Tierlist Server): Changed nickname to '{new_tl_nick}'"
                               )
                            except discord.Forbidden:
                                pass
                                
                elif not should_be_tierlist:
                    if has_tierlist_server_role:
                        await tierlist_member.remove_roles(tierlist_staff_role, reason="No longer tierlist staff")
                        changes_performed.append(
                            f"[x] {tierlist_member.display_name} (Tierlist Server): Removed role [{tierlist_staff_role.name}] (Not in Staff Server tierlist role)"
                        )
                    
                    if tierlist_member.nick and "|" in tierlist_member.nick:
                        try:
                            base_name = tierlist_member.nick.split("|", 1)[-1].strip()
                            await tierlist_member.edit(nick=base_name, reason="Clear tierlist staff nickname")
                            changes_performed.append(
                                f"[ ] {tierlist_member.display_name} (Tierlist Server): Reset nickname to '{base_name}'"
                            )
                        except discord.Forbidden:
                            pass

            staff_member = guild_staff.get_member(mid)
            if staff_member is not None:
                has_ranked_staff = any(r.id in STAFF_SERVER_ROLES for r in staff_member.roles)
                if should_be_tierlist:
                    if staff_base_role and staff_base_role not in staff_member.roles:
                        await staff_member.add_roles(staff_base_role, reason="Tierlist staff: grant base role")
                        changes_performed.append(f"[+] {staff_member.display_name} (Staff Server): Added base role [{staff_base_role.name}]")
                else:
                    if not has_ranked_staff:
                        try:
                            await staff_member.kick(reason="No longer tierlist staff and holds no core staff ranks")
                            changes_performed.append(f"[x] {staff_member.display_name} (Staff Server): Kicked from server (No longer Tierlist or Core staff)")
                        except discord.Forbidden:
                            pass
                    else:
                        if staff_base_role and staff_base_role in staff_member.roles:
                            pass

    if not changes_performed:
        if member is not None:
            return "No role or nickname changes were necessary for this user."
        return "No role changes were necessary. All servers are perfectly synchronized!"

    return f"The following `{len(changes_performed)}` operations were performed:\n```diff\n" + "\n".join(changes_performed) + "\n```"


class StaffReasonModal(discord.ui.Modal):
    def __init__(self, parent_view):
        super().__init__(title="Set Action Reason")
        self.parent_view = parent_view

        self.reason_input = discord.ui.TextInput(
            label="Reason",
            style=discord.TextStyle.paragraph,
            placeholder="Type the reason for this action here...",
            required=True,
            max_length=500,
            default=self.parent_view.reason_text,
        )
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.parent_view.reason_text = self.reason_input.value
        self.parent_view.dm_select.disabled = False
        await interaction.response.edit_message(content=None, embed=self.parent_view.build_preview(), view=self.parent_view)

class ReasonView:
    def add_reason_components(self, dm_custom_id: str, reason_custom_id: str, submit_custom_id: str):
        self.reason_text = None
        self.dm_choice = "no_dm"

        self.dm_select = Select(
            placeholder="Select DM behavior",
            options=[
                discord.SelectOption(label="Do not DM member", value="no_dm", emoji="🤫"),
                discord.SelectOption(label="DM member but without reason", value="dm_no_reason", emoji="✉️"),
                discord.SelectOption(label="DM member with reason", value="dm_with_reason", emoji="📝"),
            ],
            disabled=True,
            custom_id=dm_custom_id,
        )
        self.dm_select.callback = self.dm_callback
        self.add_item(self.dm_select)

        self.reason_button = Button(
            label="Set Reason",
            style=discord.ButtonStyle.blurple,
            disabled=True,
            custom_id=reason_custom_id,
        )
        self.reason_button.callback = self.reason_button_callback
        self.add_item(self.reason_button)

        self.submit_button = Button(
            label="Submit",
            style=discord.ButtonStyle.green,
            disabled=True,
            custom_id=submit_custom_id,
        )
        self.submit_button.callback = self.submit_callback
        self.add_item(self.submit_button)

    async def dm_callback(self, interaction: discord.Interaction):
        self.dm_choice = self.dm_select.values[0]
        await interaction.response.edit_message(content=None, embed=self.build_preview(), view=self)

    async def reason_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(StaffReasonModal(self))

    def preview_lines(self) -> list[str]:
        lines = []
        if self.reason_text:
            lines.append(f"-# <:reply:1036792837821435976> **Reason:** *\"{self.reason_text}\"*")
            dm_labels = {
                "no_dm": "Do not DM member",
                "dm_no_reason": "DM member but without reason",
                "dm_with_reason": "DM member with reason",
            }
            lines.append(f"-# <:reply:1036792837821435976> {dm_labels.get(self.dm_choice)}")
        return lines


class EditStaffView(ReasonView, View):
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

        self.add_reason_components("rank_dm", "rank_reason", "rank_submit")

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

    def build_preview(self) -> discord.Embed:
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
                new_index = len(ORDERED_STAFF_KEYS)
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

        lines.extend(self.preview_lines())

        embed = discord.Embed(title="Edit Staff Rank Panel", description="\n".join(lines), color=discord.Color.blue())
        return embed

    async def role_callback(self, interaction: discord.Interaction):
        self.role_value = self.role_select.values[0] if self.role_select.values else None
        has_requirements = bool(self.target_user and self.role_value)
        self.submit_button.disabled = not has_requirements
        self.reason_button.disabled = not has_requirements
        if not has_requirements:
            self.dm_select.disabled = True
        await interaction.response.edit_message(content=None, embed=self.build_preview(), view=self)

    async def user_callback(self, interaction: discord.Interaction):
        self.target_user = self.user_select.values[0] if self.user_select.values else None
        has_requirements = bool(self.target_user and self.role_value)
        self.submit_button.disabled = not has_requirements
        self.reason_button.disabled = not has_requirements
        if not has_requirements:
            self.dm_select.disabled = True
        await interaction.response.edit_message(content=None, embed=self.build_preview(), view=self)

    async def submit_callback(self, interaction: discord.Interaction):
        if not self.role_value or not self.target_user:
            await interaction.response.send_message("❌ Please select both a staff member and a role before submitting.", ephemeral=True)
            return
        
        if not await check_permissions(interaction, self.target_user, self.role_value):
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
            await interaction.followup.send(f"**No changes made to {staff_member.mention}.** They are already a **{new_role_mention}!", ephemeral=True)
            return

        audit_log_report = await global_sync(interaction.client, staff_member)
        await self.send_edit_notification(interaction, staff_member, new_role_mention, action, self.reason_text)

        able_to_dm = True
        if self.dm_choice != "no_dm":
            try:
                dm_embed = discord.Embed(
                    title="MystiCraft Staff Team Status Update",
                    description=f"Your staff status has been updated in MystiCraft. You have been **{action}** to {new_role_mention}.",
                    color=0x1ec7f1,
                )
                if self.dm_choice == "dm_with_reason" and self.reason_text:
                    dm_embed.add_field(name="Reason", value=self.reason_text, inline=False)
                await staff_member.send(embed=dm_embed)
            except discord.Forbidden:
                able_to_dm = False

        success_description = (
            f"**{action.title()}** {staff_member.mention} to **{new_role_mention}**. "
            f"{'*Their DMs are closed, no notification sent.*' if not able_to_dm else ''}\n\n"
            f"{audit_log_report}\n"
            f"<:reply:1048779043287351408>  Please click `Sync` on the panel to update the main listing embed."
        )

        followup = embed = discord.Embed(title="<:refresh:1048779043287351408> Staff Member Updated", description=success_description, color=0x1ec7f1)
        await interaction.followup.send(embed=followup, ephemeral=True)

    async def send_edit_notification(self, interaction, member, new_role_mention, action, reason=None):
        channel_id = 1066300810889273345
        log_channel = interaction.client.get_channel(channel_id)
        if not log_channel:
            return

        embed = discord.Embed(
            title="<:mysticraftlogo:1263829753366974535> MystiCraft Team Update",
            description=f"{member.mention} has been **{action}** to {new_role_mention}!",
            color=0x1ec7f1,
        )
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)

        embed.set_footer(text=f"{action.title()} by {interaction.user.name}")
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await log_channel.send(embed=embed)


class EditTierlistStaffView(ReasonView, View):
    def __init__(self, bot):
        super().__init__(timeout=120)
        self.bot = bot
        self.target_user = None

        self.user_select = UserSelect(placeholder="Select a member", custom_id="tierlist_user_select")
        self.user_select.callback = self.user_callback
        self.add_item(self.user_select)

        self.add_reason_components("tierlist_dm", "tierlist_reason", "tierlist_submit")

    def get_tierlist_status(self, user_id):
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
        has_user = bool(self.target_user)
        self.submit_button.disabled = not has_user
        self.reason_button.disabled = not has_user
        if not has_user:
            self.dm_select.disabled = True
        await interaction.response.edit_message(content=None, embed=self.build_preview(), view=self)

    def build_preview(self) -> discord.Embed:
        if not self.target_user:
            return discord.Embed(
                title="Edit Tierlist Staff Panel",
                description="Please select a staff member to toggle their tierlist staff status using the dropdown below.",
                color=0x1ec7f1,
            )

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
        content = (
            f"Please select a staff member to toggle their tierlist staff status using the dropdown below.\n\n"
            f"{self.target_user.mention} will be {action_word}.\n"
            + "\n".join(status_lines)
        )

        dm_lines = self.preview_lines()
        if dm_lines:
            content += "\n" + "\n".join(dm_lines)

        return discord.Embed(title="Edit Tierlist Staff Panel", description=content, color=0x1ec7f1)

    async def submit_callback(self, interaction: discord.Interaction):
        if not self.target_user:
            await interaction.response.send_message("❌ No user selected.", ephemeral=True)
            return

        if not await check_permissions(interaction, self.target_user):
            return

        await interaction.response.defer(thinking=True, ephemeral=True)

        guild_staff = interaction.client.get_guild(SERVER_IDS["staff"])
        guild_tierlist = interaction.client.get_guild(SERVER_IDS["tierlist"])

        base_role_id = ROLE_IDS.get(SERVER_IDS["staff"], {}).get("base")
        staff_base_role = guild_staff.get_role(base_role_id) if guild_staff and base_role_id else None

        has_staff_role, has_tierlist_role = self.get_tierlist_status(self.target_user.id)
        is_currently_tierlist_staff = has_staff_role or has_tierlist_role

        changes_performed = []

        if is_currently_tierlist_staff:
            if guild_staff:
                sm = guild_staff.get_member(self.target_user.id)
                if sm:
                    ts_role = guild_staff.get_role(ROLE_IDS[SERVER_IDS["staff"]]["tierlist_staff"])
                    roles_to_remove = []
                    removed_names = []

                    if ts_role and ts_role in sm.roles:
                        roles_to_remove.append(ts_role)
                        removed_names.append(ts_role.name)

                    has_other_staff_roles = any(r.id in STAFF_SERVER_ROLES for r in sm.roles)
                    if staff_base_role and staff_base_role in sm.roles and not has_other_staff_roles:
                        roles_to_remove.append(staff_base_role)
                        removed_names.append(staff_base_role.name)

                    if roles_to_remove:
                        await sm.remove_roles(*roles_to_remove, reason="Removed as tierlist staff")
                        changes_performed.append(f"[x] {sm.display_name} ({guild_staff.name}): Removed roles [{', '.join(removed_names)}] (No longer Tierlist Staff)")

            if guild_tierlist:
                tm = guild_tierlist.get_member(self.target_user.id)
                if tm:
                    all_tierlist_role_ids = set(ROLE_IDS[SERVER_IDS["tierlist"]]["roles"].values())
                    roles_to_remove = [r for r in tm.roles if r.id in all_tierlist_role_ids]
                    if roles_to_remove:
                        await tm.remove_roles(*roles_to_remove, reason="Removed as tierlist staff")
                        names = ", ".join(r.name for r in roles_to_remove)
                        changes_performed.append(f"[-] {tm.display_name} ({guild_tierlist.name}): Removed roles [{names}]")

            action = "removed as"
        else:
            if guild_staff:
                sm = guild_staff.get_member(self.target_user.id)
                if sm:
                    ts_role = guild_staff.get_role(ROLE_IDS[SERVER_IDS["staff"]]["tierlist_staff"])
                    roles_to_add = []
                    added_names = []

                    if ts_role and ts_role not in sm.roles:
                        roles_to_add.append(ts_role)
                        added_names.append(ts_role.name)
                    if staff_base_role and staff_base_role not in sm.roles:
                        roles_to_add.append(staff_base_role)
                        added_names.append(staff_base_role.name)

                    if roles_to_add:
                        await sm.add_roles(*roles_to_add, reason="Added as tierlist staff")
                        changes_performed.append(f"[+] {sm.display_name} ({guild_staff.name}): Added roles [{', '.join(added_names)}]")

            if guild_tierlist:
                tm = guild_tierlist.get_member(self.target_user.id)
                if tm:
                    tl_staff_role = guild_tierlist.get_role(ROLE_IDS[SERVER_IDS["tierlist"]]["roles"]["staff"])
                    if tl_staff_role and tl_staff_role not in tm.roles:
                        await tm.add_roles(tl_staff_role, reason="Added as tierlist staff")
                        changes_performed.append(f"[+] {tm.display_name} ({guild_tierlist.name}): Added role [{tl_staff_role.name}]")

            action = "added as"

        sync_report = await global_sync(interaction.client, guild_staff.get_member(self.target_user.id) if guild_staff else None)

        if changes_performed:
            local_report = f"The following `{len(changes_performed)}` tierlist operations were performed:\n```diff\n" + "\n".join(changes_performed) + "\n```\n"
        else:
            local_report = ""

        channel_id = 1066300810889273345
        log_channel = interaction.client.get_channel(channel_id)
        if log_channel:
            embed = discord.Embed(
                title="<:mysticraftlogo:1263829753366974535> MystiCraft Team Update",
                description=f"{self.target_user.mention} has been **{action}** <@&{ROLE_IDS[SERVER_IDS['staff']]['tierlist_staff']}>!",
                color=discord.Color.blue(),
            )
            if self.reason_text:
                embed.add_field(name="Reason", value=self.reason_text, inline=False)
            embed.set_footer(text=f"Updated by {interaction.user.name}")
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            await log_channel.send(embed=embed)

        able_to_dm = True
        if self.dm_choice != "no_dm":
            try:
                target_member = guild_staff.get_member(self.target_user.id) if guild_staff else self.target_user
                action_display = "removed from" if action == "removed as" else "added to"
                dm_embed = discord.Embed(
                    title="MystiCraft Tierlist Staff Status Update",
                    description=f"Your staff status has been updated. You have been **{action_display}** the Tierlist Staff Team.",
                    color=0x1ec7f1,
                )
                if self.dm_choice == "dm_with_reason" and self.reason_text:
                    dm_embed.add_field(name="Reason", value=self.reason_text, inline=False)
                await target_member.send(embed=dm_embed)
            except discord.Forbidden:
                able_to_dm = False

        action_past = "added to" if action == "added as" else "removed from"

        success_description = (
            f"{self.target_user.mention} has been **{action_past}** Tierlist Staff. "
            f"{'*Their DMs are closed, no notification sent.*' if not able_to_dm else ''}\n\n"
            f"{local_report}"
            f"{sync_report}\n"
            f"<:reply:1048779043287351408>  Please click `Sync` on the panel to update the main listing embed."
        )

        followup = discord.Embed(title="<:refresh:1048779043287351408> Tierlist Staff Updated", description=success_description, color=0x1ec7f1)
        await interaction.followup.send(embed=followup, ephemeral=True)


class RefreshStaffView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Edit Staff Rank", style=discord.ButtonStyle.red, custom_id="edit_staff", emoji="✏️", row=0)
    async def edit_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        allowed_roles = STAFF_SERVER_ROLES[:2]  # Owner, Manager
        user_roles = [r.id for r in interaction.user.roles]
        if not any(role in allowed_roles for role in user_roles):
            await interaction.response.send_message("❌ Only Managers+ can edit staff roles", ephemeral=True)
            return

        try:
            view = EditStaffView(interaction.client)
            await interaction.response.send_message(embed=view.build_preview(), view=view, ephemeral=True)
        except Exception as e:
            print(e)
            await interaction.response.send_message(":x: Please try **syncing** the staff list first before trying again. If this issue persists, DM <@692254240290242601>.", ephemeral=True)

    @discord.ui.button(label="Edit Tierlist Staff", style=discord.ButtonStyle.blurple, custom_id="edit_tierlist_staff", emoji="<:mysticrafttierlist:1460527955309498550>", row=0)
    async def edit_tierlist_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        allowed_roles = STAFF_SERVER_ROLES[:2]  # Owner, Manager
        user_roles = [r.id for r in interaction.user.roles]
        if not any(role in allowed_roles for role in user_roles):
            await interaction.response.send_message("❌ Only Managers+ can edit tierlist staff", ephemeral=True)
            return

        view = EditTierlistStaffView(interaction.client)
        await interaction.response.send_message(embed=view.build_preview(), view=view, ephemeral=True)

    @discord.ui.button(label="Sync",style=discord.ButtonStyle.green,custom_id="refresh_staff_list",emoji="<:refresh:1048779043287351408>",row=0)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild_staff = interaction.client.get_guild(SERVER_IDS["staff"])
        guild_tierlist = interaction.client.get_guild(SERVER_IDS["tierlist"])

        msgs = []
        tierlist_members = {}

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

        audit_log_report = await global_sync(interaction.client)
        new_view = RefreshStaffView()

        embed = discord.Embed(title="<:mysticraftlogo:1141390665842970644> MystiCraft Staff List", description="\n".join(msgs), color=0x13C6F0)
        await interaction.message.edit(embed=embed, view=new_view)

        followup = discord.Embed(title="<:refresh:1048779043287351408> Staff List Refreshed & Roles Synced", description=audit_log_report, color=0x1ec7f1)
        await interaction.followup.send(embed=followup, ephemeral=True)

    @discord.ui.button(label="View Raw List", style=discord.ButtonStyle.grey, custom_id="raw_staff_list", emoji="🗒️", row=1)
    async def raw(self, interaction: discord.Interaction, button: discord.ui.Button):
        content = interaction.message.embeds[0].description
        cleaned_content = re.sub(r"`\(\d+\)`", "", content)
        await interaction.response.send_message(f"{cleaned_content}", ephemeral=True)

    @discord.ui.button(label="Panel Information", style=discord.ButtonStyle.grey, custom_id="information_staff_list", emoji="<:config:1366940834628505650>", row=1)
    async def information(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="<:mysticraftlogo:1141390665842970644> MystiCraft Automated Staff Management System",
            description=(
                "Being one of the most unique features of any Discord server network, this custom panel handles cross-server **rank updates, role syncing, and nickname formatting**, all with a simple interface and few easy clicks.\n\n"
                "**This panel is always the single source of truth** for all staff ranks/roles. Editing ranks will first be applied to the staff server and will automatically be propagated to the main, support, and tierlist servers. "
                "**Never assign or remove roles in any server manually!** Always use this panel's buttons."
            ),
            color=0x1ec7f1,
        )

        embed.add_field(
            name="Additional Information",
            value=(
                "-# 1. Staff members can also be assigned exclusively to Tierlist roles without core staff ranks.\n"
                "-# 2. Demoting a staff to `Member` automatically removes staff roles from all servers and instantly kicks them from the Staff Server.\n"
                "-# 3. When modifying any staff member using the panel, you can choose to optionally send them a DM and provide a reason."
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    pass