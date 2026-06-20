import discord
import datetime
import pytz
import time
import re

from discord import app_commands
from discord.ext import commands
from firebase_admin import db

from constants import ROLE_IDS, SERVER_IDS

STAFF_SERVER_ROLES = [ROLE_IDS[SERVER_IDS["staff"]]["roles"][k] for k in ["owner", "manager", "senior_admin", "admin", "developer", "senior_mod", "mod", "helper"]]
MANAGER_ROLES = [ROLE_IDS[SERVER_IDS["staff"]]["roles"]["owner"], ROLE_IDS[SERVER_IDS["staff"]]["roles"]["manager"]]

# Timezone offsets (UTC-12 to UTC+14, whole hours)
NEGATIVE_OFFSETS = [f"UTC{i}" for i in range(-12, 0)]
POSITIVE_OFFSETS = [f"UTC+{i}" for i in range(0, 15)]  # includes UTC+0

LOA_LOG_CHANNEL = 1517598730973609984
APPROVAL_ROLE = 1165675275821002835

# Embed colours
COLOR_SUCCESS = 0x2ecc71
COLOR_ERROR   = 0xe74c3c
COLOR_INFO    = 0x1ec7f1
COLOR_WARNING = 0xf1c40f

# ----------------------------------------------------------------------
# Embed helper functions
# ----------------------------------------------------------------------

def embed_success(title: str, description: str = None) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=COLOR_SUCCESS)

def embed_error(title: str, description: str = None) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=COLOR_ERROR)

def embed_info(title: str, description: str = None) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=COLOR_INFO)

def embed_warning(title: str, description: str = None) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=COLOR_WARNING)

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------

def is_staff(member: discord.Member) -> bool:
    if not member.guild:
        return False
    guild = member.guild
    staff_role_ids = STAFF_SERVER_ROLES
    member_role_ids = {r.id for r in member.roles}
    return any(rid in member_role_ids for rid in staff_role_ids)

def is_manager(member: discord.Member) -> bool:
    if not member.guild:
        return False
    member_role_ids = {r.id for r in member.roles}
    return any(rid in member_role_ids for rid in MANAGER_ROLES)

def get_loas(status_filter: str = None) -> list[dict]:
    """Return all LOA records, optionally filtered by status."""
    records = db.reference("LOA").get() or {}
    result = []
    for uid, user_records in records.items():
        for record_id, rec in user_records.items():
            if status_filter and rec.get("status") != status_filter:
                continue
            result.append({
                "user_id": int(uid),
                "record_id": record_id,
                **rec
            })
    return result

def get_active_loas() -> list[dict]:
    """Return LOAs with status='active' and end>=now."""
    now = int(time.time())
    all_loas = get_loas(status_filter="active")
    return [l for l in all_loas if l.get("end") >= now]

def get_pending_loas() -> list[dict]:
    """Return all pending LOAs."""
    return get_loas(status_filter="pending")

def get_user_loas(user_id: int, status_filter: str = None) -> list[dict]:
    """Get a user's LOAs, optionally filtered by status."""
    records = db.reference("LOA").child(str(user_id)).get() or {}
    result = []
    for record_id, rec in records.items():
        if status_filter and rec.get("status") != status_filter:
            continue
        result.append({
            "record_id": record_id,
            **rec
        })
    return sorted(result, key=lambda x: x.get("start", 0))

def get_user_loa_history(user_id: int, start_ts: int = None, end_ts: int = None) -> list[dict]:
    """Get all LOA records for a user, optionally filtered by date range."""
    records = db.reference("LOA").child(str(user_id)).get() or {}
    history = []
    for record_id, rec in records.items():
        if start_ts and rec.get("start") < start_ts:
            continue
        if end_ts and rec.get("end") > end_ts:
            continue
        history.append({
            "record_id": record_id,
            **rec
        })
    return sorted(history, key=lambda x: x.get("start", 0))

def format_date_plain(ts: int, offset_str: str = "UTC+0") -> str:
    """Return a plain date string (no Discord timestamp) for dropdown labels."""
    try:
        hours = int(re.search(r"([+-]?\d+)", offset_str).group(1))
    except:
        hours = 0
    tz = pytz.FixedOffset(hours * 60)
    dt = datetime.datetime.fromtimestamp(ts, tz)
    return dt.strftime("%Y-%m-%d")

def get_display_status(rec: dict) -> str:
    """Return 'Active', 'Upcoming', or 'Ended' based on the current time."""
    now = int(time.time())
    start = rec.get('start', 0)
    end = rec.get('end', 0)
    if start <= now <= end:
        return "Active"
    elif start > now:
        return "Upcoming"
    else:
        return "Ended"

def create_loa_embed() -> discord.Embed:
    """Create the embed for the LOA panel (active + upcoming)."""
    loas = get_active_loas()
    embed = discord.Embed(
        title="📋 Staff Leave of Absence (LOA) Panel",
        color=COLOR_INFO
    )
    if not loas:
        embed.description = "There are currently **no active or upcoming LOAs**."
        return embed

    now = int(time.time())
    active_loas = sorted([l for l in loas if l['start'] <= now], key=lambda x: x['start'])
    upcoming_loas = sorted([l for l in loas if l['start'] > now], key=lambda x: x['start'])

    if active_loas:
        lines = []
        for rec in active_loas:
            lines.append(
                f"<@{rec['user_id']}> – **{rec.get('reason', 'No reason')}**\n"
                f"-# <t:{rec['start']}:D> → <t:{rec['end']}:D> (<t:{rec['end']}:R>)"
            )
        embed.add_field(name="🟢 Active LOAs", value="\n".join(lines) or "None", inline=False)

    if upcoming_loas:
        lines = []
        for rec in upcoming_loas:
            lines.append(
                f"<@{rec['user_id']}> – **{rec.get('reason', 'No reason')}**\n"
                f"-# <t:{rec['start']}:D> → <t:{rec['end']}:D> (<t:{rec['end']}:R>)"
            )
        embed.add_field(name="⏳ Upcoming LOAs", value="\n".join(lines) or "None", inline=False)

    if not active_loas and not upcoming_loas:
        embed.description = "There are currently **no active or upcoming LOAs**."

    embed.set_footer(text="Use the buttons below to manage LOAs.")
    return embed

# ----------------------------------------------------------------------
# Approval Log View
# ----------------------------------------------------------------------

class ApprovalView(discord.ui.View):
    def __init__(self, record_id: str, user_id: int, is_edit: bool = False, old_record_id: str = None):
        super().__init__(timeout=86400)  # 24 hours
        self.record_id = record_id
        self.user_id = user_id
        self.is_edit = is_edit
        self.old_record_id = old_record_id

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_manager(interaction.user):
            await interaction.response.send_message(embed=embed_error("Permission Denied", "You don't have permission to approve LOAs."), ephemeral=True)
            return

        ref = db.reference(f"LOA/{self.user_id}/{self.record_id}")
        rec = ref.get()
        if not rec:
            await interaction.response.send_message(embed=embed_error("Not Found", "This LOA record no longer exists."), ephemeral=True)
            return

        if rec.get("status") != "pending":
            await interaction.response.send_message(embed=embed_error("Invalid Status", f"This LOA is already **{rec.get('status')}**."), ephemeral=True)
            return

        # Handle edit requests
        if self.is_edit and self.old_record_id:
            old_ref = db.reference(f"LOA/{self.user_id}/{self.old_record_id}")
            old_rec = old_ref.get()
            if old_rec:
                # Update old record with new data
                old_ref.update({
                    "start": rec["start"],
                    "end": rec["end"],
                    "timezone_offset": rec["timezone_offset"],
                    "reason": rec["reason"],
                    "additional": rec["additional"],
                    "status": "active",
                    "updated_at": int(time.time())
                })
                # Delete the pending edit record
                ref.delete()
                await interaction.response.edit_message(
                    content=None,
                    embed=embed_success("Edit Approved", f"Edit applied to <@{self.user_id}>'s LOA by <@{interaction.user.id}>."),
                    view=None
                )
                # Notify user
                try:
                    user = await interaction.client.fetch_user(self.user_id)
                    if user:
                        await user.send(embed=embed_success(
                            "LOA Edit Approved",
                            f"**New LOA:** {rec['reason']}\n"
                            f"**From:** <t:{rec['start']}:D>\n"
                            f"**To:** <t:{rec['end']}:D>"
                        ))
                except:
                    pass
                return
            else:
                # Old record not found, fallback to normal approval
                pass

        # Handle replacement (new LOA that replaces an old one)
        replaces_id = rec.get("replaces")
        if not self.is_edit and replaces_id:
            # Deactivate the old LOA
            old_ref = db.reference(f"LOA/{self.user_id}/{replaces_id}")
            old_rec = old_ref.get()
            if old_rec and old_rec.get("status") == "active":
                old_ref.update({
                    "status": "replaced",
                    "replaced_by": self.record_id,
                    "replaced_at": int(time.time())
                })
                # Optionally adjust end date to new start - 1 day? Not necessary, but we mark as replaced.

        # Normal approval (new LOA or edit fallback)
        ref.update({
            "status": "active",
            "approved_by": interaction.user.id,
            "approved_at": int(time.time())
        })
        await interaction.response.edit_message(
            content=None,
            embed=embed_success("LOA Approved", f"LOA for <@{self.user_id}> has been **approved** by <@{interaction.user.id}>."),
            view=None
        )
        # Notify user
        try:
            user = await interaction.client.fetch_user(self.user_id)
            if user:
                msg = f"**LOA:** {rec['reason']}\n**From:** <t:{rec['start']}:D>\n**To:** <t:{rec['end']}:D>"
                if replaces_id:
                    msg += "\n*Your previous LOA has been replaced.*"
                await user.send(embed=embed_success("LOA Approved", msg))
        except:
            pass

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_manager(interaction.user):
            await interaction.response.send_message(embed=embed_error("Permission Denied", "You don't have permission to reject LOAs."), ephemeral=True)
            return

        ref = db.reference(f"LOA/{self.user_id}/{self.record_id}")
        rec = ref.get()
        if not rec:
            await interaction.response.send_message(embed=embed_error("Not Found", "This LOA record no longer exists."), ephemeral=True)
            return

        if rec.get("status") != "pending":
            await interaction.response.send_message(embed=embed_error("Invalid Status", f"This LOA is already **{rec.get('status')}**."), ephemeral=True)
            return

        if self.is_edit and self.old_record_id:
            # Just delete the pending edit request
            ref.delete()
            await interaction.response.edit_message(
                content=None,
                embed=embed_error("Edit Rejected", f"Edit request for <@{self.user_id}> has been **rejected** and removed by <@{interaction.user.id}>."),
                view=None
            )
            try:
                user = await interaction.client.fetch_user(self.user_id)
                if user:
                    await user.send(embed=embed_error("LOA Edit Rejected", f"Your request to edit your LOA has been **rejected** by <@{interaction.user.id}>. If you go inactive during this time, it may affect your staff rank in the future"))
            except:
                pass
            return

        ref.update({
            "status": "rejected",
            "rejected_by": interaction.user.id,
            "rejected_at": int(time.time())
        })
        await interaction.response.edit_message(
            content=None,
            embed=embed_error("LOA Rejected", f"LOA for <@{self.user_id}> has been **rejected** by <@{interaction.user.id}>. If you go inactive during this time, it may affect your staff rank in the future"),
            view=None
        )
        try:
            user = await interaction.client.fetch_user(self.user_id)
            if user:
                await user.send(embed=embed_error(
                    "LOA Rejected",
                    f"**LOA:** {rec['reason']}\n"
                    f"**From:** <t:{rec['start']}:D>\n"
                    f"**To:** <t:{rec['end']}:D>"
                ))
        except:
            pass

    @discord.ui.button(label="View History", style=discord.ButtonStyle.secondary, emoji="📜")
    async def view_history(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_manager(interaction.user):
            await interaction.response.send_message(embed=embed_error("Permission Denied", "You don't have permission to view this."), ephemeral=True)
            return

        history = get_user_loa_history(self.user_id)
        if not history:
            await interaction.response.send_message(embed=embed_info("History", f"No LOA history found for <@{self.user_id}>."), ephemeral=True)
            return

        lines = []
        for rec in history:
            status = rec.get("status", "unknown")
            emoji = "🟢" if status == "active" else "⏳" if status == "pending" else "🔴" if status == "rejected" else "⚪" if status == "replaced" else "⚪"
            lines.append(
                f"{emoji} **{rec['reason']}** ({status})\n"
                f"-# <t:{rec['start']}:D> → <t:{rec['end']}:D>"
            )
        embed = discord.Embed(
            title=f"📜 LOA History for {interaction.client.get_user(self.user_id)}",
            description="\n".join(lines),
            color=COLOR_INFO
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ----------------------------------------------------------------------
# Views for the LOA Panel
# ----------------------------------------------------------------------

class LOAPanelView(discord.ui.View):
    """Persistent view for the LOA management panel."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Submit LOA", style=discord.ButtonStyle.primary, custom_id="loa_submit", emoji="📝", row=0)
    async def submit_loa(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message(embed=embed_error("Access Denied", "You are not a staff member."), ephemeral=True)
            return

        # Check if user already has an active/upcoming LOA
        existing = get_user_loas(interaction.user.id, status_filter="active")
        now = int(time.time())
        existing = [l for l in existing if l.get("end") >= now]
        if existing:
            view = ReplaceOrNewView(interaction.user.id, existing)
            await interaction.response.send_message(
                embed=embed_warning(
                    "Existing LOA Detected",
                    "You already have an active or upcoming LOA. Would you like to **replace** it or **add a new separate LOA**?"
                ),
                view=view,
                ephemeral=True
            )
        else:
            view = DateRangeSelectView(interaction.user.id)
            await interaction.response.send_message(
                embed=embed_info(
                    "Select Dates",
                    "Please select the **start** and **end** dates of your LOA.\n"
                    "These dates are based on your local calendar. You will choose your timezone next to define the exact day boundaries."
                ),
                view=view,
                ephemeral=True
            )

    @discord.ui.button(label="Edit LOA", style=discord.ButtonStyle.blurple, custom_id="loa_edit", emoji="✏️", row=0)
    async def edit_loa(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message(embed=embed_error("Access Denied", "You are not a staff member."), ephemeral=True)
            return

        active_loas = get_user_loas(interaction.user.id, status_filter="active")
        pending_loas = get_user_loas(interaction.user.id, status_filter="pending")
        editable = active_loas + [l for l in pending_loas if l.get("start") >= int(time.time())]

        if not editable:
            await interaction.response.send_message(embed=embed_info("No Editable LOAs", "You don't have any active or upcoming LOAs to edit."), ephemeral=True)
            return

        view = EditLOASelectView(interaction.user.id, editable)
        await interaction.response.send_message(embed=embed_info("Select LOA to Edit", "Choose the LOA you want to edit:"), view=view, ephemeral=True)

    @discord.ui.button(label="Sync", style=discord.ButtonStyle.grey, custom_id="loa_sync", emoji="<:refresh:1048779043287351408>", row=1)
    async def sync(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_loa_embed(), view=self)

    @discord.ui.button(label="Check User", style=discord.ButtonStyle.secondary, custom_id="loa_check", emoji="🔍", row=1)
    async def check_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_manager(interaction.user):
            await interaction.response.send_message(embed=embed_error("Permission Denied", "Only Managers+ can check other users' LOA history."), ephemeral=True)
            return
        view = UserSelectView()
        await interaction.response.send_message(embed=embed_info("Select User", "Select a user to view their LOA history:"), view=view, ephemeral=True)


class EditLOASelectView(discord.ui.View):
    def __init__(self, user_id, loas):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.loas = loas
        options = []
        for rec in loas:
            start_plain = format_date_plain(rec['start'], rec.get('timezone_offset', 'UTC+0'))
            end_plain = format_date_plain(rec['end'], rec.get('timezone_offset', 'UTC+0'))
            status_display = get_display_status(rec)
            label = f"{rec['reason']} ({status_display})"
            description = f"{start_plain} → {end_plain}"
            options.append(discord.SelectOption(label=label[:100], value=rec['record_id'], description=description[:100]))
        self.add_item(EditLOASelect(options, self))


class EditLOASelect(discord.ui.Select):
    def __init__(self, options, parent_view):
        super().__init__(placeholder="Choose a LOA to edit", options=options[:25])
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        record_id = self.values[0]
        rec = db.reference(f"LOA/{self.parent_view.user_id}/{record_id}").get()
        if not rec:
            await interaction.response.send_message(embed=embed_error("Not Found", "That LOA no longer exists."), ephemeral=True)
            return

        modal = EditLOAModal(self.parent_view.user_id, record_id, rec)
        await interaction.response.send_modal(modal)


class EditLOAModal(discord.ui.Modal):
    def __init__(self, user_id, record_id, current_data):
        super().__init__(title="✏️ Edit LOA")
        self.user_id = user_id
        self.record_id = record_id
        self.current_data = current_data

        self.start_date = discord.ui.TextInput(
            label="New Start Date (YYYY-MM-DD)",
            placeholder="e.g., 2026-07-01",
            default=datetime.datetime.fromtimestamp(current_data['start']).strftime("%Y-%m-%d"),
            required=True
        )
        self.add_item(self.start_date)

        self.end_date = discord.ui.TextInput(
            label="New End Date (YYYY-MM-DD)",
            placeholder="e.g., 2026-07-05",
            default=datetime.datetime.fromtimestamp(current_data['end']).strftime("%Y-%m-%d"),
            required=True
        )
        self.add_item(self.end_date)

        self.reason = discord.ui.TextInput(
            label="Reason for LOA",
            style=discord.TextStyle.short,
            default=current_data.get('reason', ''),
            required=True,
            max_length=100
        )
        self.add_item(self.reason)

        self.additional = discord.ui.TextInput(
            label="Additional Info (optional)",
            style=discord.TextStyle.paragraph,
            default=current_data.get('additional', ''),
            required=False,
            max_length=500
        )
        self.add_item(self.additional)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            start_date = datetime.datetime.strptime(self.start_date.value, "%Y-%m-%d").date()
            end_date = datetime.datetime.strptime(self.end_date.value, "%Y-%m-%d").date()
            if end_date < start_date:
                await interaction.response.send_message(embed=embed_error("Invalid Dates", "End date cannot be before start date."), ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message(embed=embed_error("Invalid Format", "Invalid date format. Use YYYY-MM-DD."), ephemeral=True)
            return

        tz_offset = self.current_data.get("timezone_offset", "UTC+0")
        try:
            hours = int(re.search(r"([+-]?\d+)", tz_offset).group(1))
        except:
            hours = 0
        tz = pytz.FixedOffset(hours * 60)

        start_naive = datetime.datetime.combine(start_date, datetime.time.min)
        end_naive = datetime.datetime.combine(end_date + datetime.timedelta(days=1), datetime.time.min) - datetime.timedelta(seconds=1)
        start_local = tz.localize(start_naive)
        end_local = tz.localize(end_naive)
        start_ts = int(start_local.astimezone(pytz.UTC).timestamp())
        end_ts = int(end_local.astimezone(pytz.UTC).timestamp())

        new_record = {
            "start": start_ts,
            "end": end_ts,
            "timezone_offset": tz_offset,
            "reason": self.reason.value,
            "additional": self.additional.value or "",
            "submitted_at": int(time.time()),
            "status": "pending",
            "is_edit": True,
            "edits_record": self.record_id
        }
        ref = db.reference(f"LOA/{self.user_id}").push(new_record)
        new_record_id = ref.key

        log_channel = interaction.guild.get_channel(LOA_LOG_CHANNEL)
        if log_channel:
            embed = discord.Embed(
                title="✏️ LOA Edit Request",
                description=f"<@{self.user_id}> has requested to edit their LOA.",
                color=COLOR_WARNING,
            )
            embed.add_field(
                name="Original LOA",
                value=f"**{self.current_data.get('reason', 'No reason')}**\n<t:{self.current_data['start']}:D> → <t:{self.current_data['end']}:D>",
                inline=False
            )
            embed.add_field(
                name="New LOA",
                value=f"**{self.reason.value}**\n<t:{start_ts}:D> → <t:{end_ts}:D>",
                inline=False
            )
            embed.add_field(name="Additional Info", value=self.additional.value or "None", inline=False)
            embed.set_footer(text=f"User ID: {self.user_id} | Record ID: {new_record_id}")

            view = ApprovalView(new_record_id, self.user_id, is_edit=True, old_record_id=self.record_id)
            await log_channel.send(f"<@&{APPROVAL_ROLE}>", embed=embed, view=view)

        await interaction.response.send_message(
            embed=embed_success("Edit Submitted", "Your edit request has been submitted for approval. You will be notified once it is reviewed."),
            ephemeral=True
        )


class ReplaceOrNewView(discord.ui.View):
    def __init__(self, user_id, existing_loas):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.existing_loas = existing_loas

        options = []
        for rec in existing_loas:
            start_plain = format_date_plain(rec['start'], rec.get('timezone_offset', 'UTC+0'))
            end_plain = format_date_plain(rec['end'], rec.get('timezone_offset', 'UTC+0'))
            label = f"{rec['reason']} ({start_plain} → {end_plain})"
            options.append(discord.SelectOption(label=label[:100], value=rec['record_id']))
        if options:
            self.add_item(ReplaceSelect(options, self))

        self.add_item(discord.ui.Button(label="Add New (Separate)", style=discord.ButtonStyle.secondary, custom_id="add_new"))


class ReplaceSelect(discord.ui.Select):
    def __init__(self, options, parent_view):
        super().__init__(placeholder="Choose LOA to replace", options=options[:25])
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        record_id = self.values[0]
        self.parent_view.replace_record_id = record_id
        view = DateRangeSelectView(self.parent_view.user_id, replace_record_id=record_id)
        await interaction.response.edit_message(
            embed=embed_info("Select New Dates", "Please select the new **start** and **end** dates for your replacement LOA."),
            view=view
        )


class DateRangeSelectView(discord.ui.View):
    def __init__(self, user_id: int, offset: int = 0, start_date=None, end_date=None, replace_record_id=None):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.offset = offset
        self.start_date = start_date
        self.end_date = end_date
        self.replace_record_id = replace_record_id
        self.build_view()

    def build_view(self):
        self.clear_items()
        today = datetime.datetime.now().date()
        dates = [today + datetime.timedelta(days=i + self.offset) for i in range(14)]

        for i, date_obj in enumerate(dates):
            label = date_obj.strftime("%b %d")
            style = discord.ButtonStyle.secondary
            if self.start_date and date_obj == self.start_date:
                style = discord.ButtonStyle.green
            if self.end_date and date_obj == self.end_date:
                style = discord.ButtonStyle.red
            disabled = bool(self.start_date and self.end_date)
            row = i // 5
            self.add_item(DayButton(date_obj, label, style, disabled, self, row=row))

        self.add_item(PrevButton(self, row=3))
        self.add_item(NextButton(self, row=3))

        status = "Select start date."
        if self.start_date and not self.end_date:
            status = f"Start: {self.start_date.strftime('%Y-%m-%d')}. Select end date."
        if self.start_date and self.end_date:
            duration = (self.end_date - self.start_date).days + 1
            status = f"Start: {self.start_date.strftime('%Y-%m-%d')}, End: {self.end_date.strftime('%Y-%m-%d')} ({duration} day{'s' if duration != 1 else ''})."
        self.add_item(StatusLabel(status, row=3))

        confirm = ConfirmDatesButton(self, row=4)
        confirm.disabled = not (self.start_date and self.end_date)
        self.add_item(confirm)
        self.add_item(CancelButton(row=4))

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="📅 Select Dates",
            color=COLOR_INFO
        )
        desc = "Choose the **start** (green) and **end** (red) dates for your LOA.\n"
        if self.start_date:
            desc += f"**Start:** {self.start_date.strftime('%Y-%m-%d')}\n"
        if self.end_date:
            desc += f"**End:** {self.end_date.strftime('%Y-%m-%d')}\n"
            duration = (self.end_date - self.start_date).days + 1
            desc += f"**Duration:** {duration} day{'s' if duration != 1 else ''}\n"
        embed.description = desc
        return embed

    def update(self):
        self.build_view()


class DayButton(discord.ui.Button):
    def __init__(self, date_obj, label, style, disabled, parent_view, row):
        super().__init__(label=label, style=style, disabled=disabled, row=row)
        self.date_obj = date_obj
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        parent = self.parent_view
        if not parent.start_date:
            parent.start_date = self.date_obj
        elif not parent.end_date:
            if self.date_obj < parent.start_date:
                parent.start_date, parent.end_date = self.date_obj, parent.start_date
            else:
                parent.end_date = self.date_obj
        else:
            await interaction.response.defer()
            return
        parent.update()
        await interaction.response.edit_message(embed=parent.get_embed(), view=parent)


class PrevButton(discord.ui.Button):
    def __init__(self, parent_view, row):
        super().__init__(label="Previous", style=discord.ButtonStyle.grey, row=row, emoji="<:backarrow:1351972111010369618>")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.offset -= 14
        self.parent_view.update()
        await interaction.response.edit_message(embed=self.parent_view.get_embed(), view=self.parent_view)


class NextButton(discord.ui.Button):
    def __init__(self, parent_view, row):
        super().__init__(label="Next", style=discord.ButtonStyle.grey, row=row, emoji="<:rightarrow:1351972116819480616>")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.offset += 14
        self.parent_view.update()
        await interaction.response.edit_message(embed=self.parent_view.get_embed(), view=self.parent_view)


class StatusLabel(discord.ui.Button):
    def __init__(self, label, row):
        super().__init__(label=label, style=discord.ButtonStyle.grey, disabled=True, row=row)


class ConfirmDatesButton(discord.ui.Button):
    def __init__(self, parent_view, row):
        super().__init__(label="Confirm Dates", style=discord.ButtonStyle.success, row=row)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if not self.parent_view.start_date or not self.parent_view.end_date:
            await interaction.response.send_message(embed=embed_error("Incomplete", "Please select both start and end dates."), ephemeral=True)
            return
        view = TimezoneSelectView(
            self.parent_view.start_date,
            self.parent_view.end_date,
            interaction.user.id,
            offset=self.parent_view.offset,
            replace_record_id=self.parent_view.replace_record_id
        )
        await interaction.response.edit_message(
            embed=embed_info(
                "Select Timezone",
                "Now, choose your **timezone offset**.\n"
                "This offset defines the **day boundaries** (midnight to midnight) for your LOA.\n"
                "All dates shown in the panel will automatically appear in your own local timezone – you only need this to tell the system where your calendar day starts/ends.\n"
                "Select an offset from one of the dropdowns below."
            ),
            view=view
        )


class CancelButton(discord.ui.Button):
    def __init__(self, row):
        super().__init__(label="Cancel", style=discord.ButtonStyle.danger, row=row)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            embed=embed_info("Cancelled", "LOA submission cancelled."),
            view=None
        )

# ----------------------------------------------------------------------
# Timezone selection
# ----------------------------------------------------------------------

class TimezoneSelectView(discord.ui.View):
    def __init__(self, start_date, end_date, user_id, offset=0, replace_record_id=None):
        super().__init__(timeout=300)
        self.start_date = start_date
        self.end_date = end_date
        self.user_id = user_id
        self.offset = offset
        self.replace_record_id = replace_record_id
        self.selected_offset = None

        self.neg_select = TimezoneSelectNegative(self)
        self.pos_select = TimezoneSelectPositive(self)
        self.add_item(self.neg_select)
        self.add_item(self.pos_select)
        self.add_item(BackToDateButton(self))
        self.next_button = NextButtonAfterTimezone(self)
        self.next_button.disabled = True
        self.add_item(self.next_button)

    def update_selection(self, offset: str):
        self.selected_offset = offset
        self.neg_select.disabled = True
        self.pos_select.disabled = True
        self.next_button.disabled = False


class TimezoneSelectNegative(discord.ui.Select):
    def __init__(self, parent_view):
        options = [discord.SelectOption(label=tz, value=tz) for tz in NEGATIVE_OFFSETS]
        super().__init__(placeholder="UTC-12 to UTC-1", options=options)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        offset = self.values[0]
        hours = int(re.search(r"([+-]?\d+)", offset).group(1))
        tz = pytz.FixedOffset(hours * 60)

        start_naive = datetime.datetime.combine(self.parent_view.start_date, datetime.time.min)
        end_naive = datetime.datetime.combine(self.parent_view.end_date + datetime.timedelta(days=1), datetime.time.min) - datetime.timedelta(seconds=1)
        start_local = tz.localize(start_naive)
        end_local = tz.localize(end_naive)
        start_ts = int(start_local.astimezone(pytz.UTC).timestamp())
        end_ts = int(end_local.astimezone(pytz.UTC).timestamp())

        now_utc = datetime.datetime.now(pytz.UTC)
        now_local = now_utc.astimezone(tz)
        time_str = now_local.strftime("%H:%M")

        self.parent_view.update_selection(offset)
        embed = discord.Embed(
            title="Timezone Selected",
            description=f"✅ Selected timezone: **{offset}** (current time there: **{time_str}**).\n\n"
                        f"Your LOA will be recorded from **<t:{start_ts}:D>** to **<t:{end_ts}:D>**.\n"
                        f"(These dates will appear in **your own local timezone** when viewed in the panel.)\n\n"
                        f"Please confirm by clicking **Next**.",
            color=COLOR_INFO
        )
        await interaction.response.edit_message(embed=embed, view=self.parent_view)


class TimezoneSelectPositive(discord.ui.Select):
    def __init__(self, parent_view):
        options = [discord.SelectOption(label=tz, value=tz) for tz in POSITIVE_OFFSETS]
        super().__init__(placeholder="UTC+0 to UTC+14", options=options)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        offset = self.values[0]
        hours = int(re.search(r"([+-]?\d+)", offset).group(1))
        tz = pytz.FixedOffset(hours * 60)

        start_naive = datetime.datetime.combine(self.parent_view.start_date, datetime.time.min)
        end_naive = datetime.datetime.combine(self.parent_view.end_date + datetime.timedelta(days=1), datetime.time.min) - datetime.timedelta(seconds=1)
        start_local = tz.localize(start_naive)
        end_local = tz.localize(end_naive)
        start_ts = int(start_local.astimezone(pytz.UTC).timestamp())
        end_ts = int(end_local.astimezone(pytz.UTC).timestamp())

        now_utc = datetime.datetime.now(pytz.UTC)
        now_local = now_utc.astimezone(tz)
        time_str = now_local.strftime("%H:%M")

        self.parent_view.update_selection(offset)
        embed = discord.Embed(
            title="Timezone Selected",
            description=f"✅ Selected timezone: **{offset}** (current time there: **{time_str}**).\n\n"
                        f"Your LOA will be recorded from **<t:{start_ts}:D>** to **<t:{end_ts}:D>**.\n"
                        f"(These dates will appear in **your own local timezone** when viewed in the panel.)\n\n"
                        f"Please confirm by clicking **Next**.",
            color=COLOR_INFO
        )
        await interaction.response.edit_message(embed=embed, view=self.parent_view)


class NextButtonAfterTimezone(discord.ui.Button):
    def __init__(self, parent_view):
        super().__init__(label="Next", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if not self.parent_view.selected_offset:
            await interaction.response.send_message(embed=embed_error("No Timezone", "Please select a timezone from one of the dropdowns first."), ephemeral=True)
            return
        modal = LOAModal(
            self.parent_view.start_date,
            self.parent_view.end_date,
            self.parent_view.selected_offset,
            self.parent_view.user_id,
            replace_record_id=self.parent_view.replace_record_id
        )
        await interaction.response.send_modal(modal)


class BackToDateButton(discord.ui.Button):
    def __init__(self, parent_view):
        super().__init__(label="Back", style=discord.ButtonStyle.grey)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        view = DateRangeSelectView(
            self.parent_view.user_id,
            offset=self.parent_view.offset,
            start_date=self.parent_view.start_date,
            end_date=self.parent_view.end_date,
            replace_record_id=self.parent_view.replace_record_id
        )
        await interaction.response.edit_message(
            embed=embed_info(
                "Select Dates",
                "Please select the **start** and **end** dates of your LOA.\n"
                "These dates are based on your local calendar. You will choose your timezone next to define the exact day boundaries."
            ),
            view=view
        )

# ----------------------------------------------------------------------
# LOA Modal
# ----------------------------------------------------------------------

class LOAModal(discord.ui.Modal):
    def __init__(self, start_date, end_date, tz_offset, user_id, replace_record_id=None):
        super().__init__(title="📝 Leave of Absence Details")
        self.start_date = start_date
        self.end_date = end_date
        self.tz_offset = tz_offset
        self.user_id = user_id
        self.replace_record_id = replace_record_id

        self.reason = discord.ui.TextInput(
            label="Reason for LOA",
            style=discord.TextStyle.short,
            placeholder="e.g., Personal, Medical, Vacation",
            required=True,
            max_length=100
        )
        self.add_item(self.reason)

        self.additional = discord.ui.TextInput(
            label="Additional Info (optional)",
            style=discord.TextStyle.paragraph,
            placeholder="Any extra details...",
            required=False,
            max_length=500
        )
        self.add_item(self.additional)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            hours = int(re.search(r"([+-]?\d+)", self.tz_offset).group(1))
        except:
            hours = 0
        tz = pytz.FixedOffset(hours * 60)

        start_naive = datetime.datetime.combine(self.start_date, datetime.time.min)
        end_naive = datetime.datetime.combine(self.end_date + datetime.timedelta(days=1), datetime.time.min) - datetime.timedelta(seconds=1)
        start_local = tz.localize(start_naive)
        end_local = tz.localize(end_naive)
        start_ts = int(start_local.astimezone(pytz.UTC).timestamp())
        end_ts = int(end_local.astimezone(pytz.UTC).timestamp())

        duration_days = (self.end_date - self.start_date).days + 1
        warning = ""
        if duration_days > 7:
            warning = "\n⚠️ **Note:** This LOA exceeds 7 days, which may require additional approval steps."

        record = {
            "start": start_ts,
            "end": end_ts,
            "timezone_offset": self.tz_offset,
            "reason": self.reason.value,
            "additional": self.additional.value or "",
            "submitted_at": int(time.time()),
            "status": "pending"
        }

        if self.replace_record_id:
            record["replaces"] = self.replace_record_id

        ref = db.reference(f"LOA/{self.user_id}").push(record)
        record_id = ref.key

        log_channel = interaction.guild.get_channel(LOA_LOG_CHANNEL)
        if log_channel:
            embed = discord.Embed(
                title="📋 New LOA Request",
                description=f"<@{self.user_id}> has submitted a new LOA request.",
                color=COLOR_WARNING,
            )
            embed.add_field(name="Reason", value=self.reason.value, inline=False)
            embed.add_field(name="Start Date", value=f"<t:{start_ts}:D>", inline=True)
            embed.add_field(name="End Date", value=f"<t:{end_ts}:D>", inline=True)
            embed.add_field(name="Duration", value=f"{duration_days} day{'s' if duration_days != 1 else ''}", inline=True)
            embed.add_field(name="Timezone Offset", value=self.tz_offset, inline=True)
            embed.add_field(name="Additional Info", value=self.additional.value or "None", inline=False)
            if self.replace_record_id:
                embed.add_field(name="Replaces", value=f"<t:{self.replace_record_id}> (old LOA ID)", inline=False)
            embed.set_footer(text=f"User ID: {self.user_id} | Record ID: {record_id}")

            view = ApprovalView(record_id, self.user_id, is_edit=False)
            await log_channel.send(f"<@&{APPROVAL_ROLE}>", embed=embed, view=view)

        await interaction.response.send_message(
            embed=embed_success(
                "LOA Submitted",
                f"Your LOA request has been submitted for approval. You will be notified once it is reviewed.{warning}"
            ),
            ephemeral=True
        )

# ----------------------------------------------------------------------
# User history check
# ----------------------------------------------------------------------

class UserSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(UserSelectDropdown())

class UserSelectDropdown(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="Select a staff member", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        user = self.values[0]
        view = HistoryRangeView(user)
        await interaction.response.edit_message(
            embed=embed_info(f"History for {user.display_name}", "Select a time range:"),
            view=view
        )

class HistoryRangeView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=120)
        self.user = user

    @discord.ui.button(label="Last 30 Days", style=discord.ButtonStyle.secondary)
    async def last30(self, interaction: discord.Interaction, button: discord.ui.Button):
        end = int(time.time())
        start = end - 30*86400
        await self.show_history(interaction, start, end)

    @discord.ui.button(label="Last 90 Days", style=discord.ButtonStyle.secondary)
    async def last90(self, interaction: discord.Interaction, button: discord.ui.Button):
        end = int(time.time())
        start = end - 90*86400
        await self.show_history(interaction, start, end)

    @discord.ui.button(label="All", style=discord.ButtonStyle.secondary)
    async def all_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_history(interaction, None, None)

    @discord.ui.button(label="Custom", style=discord.ButtonStyle.primary)
    async def custom(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CustomRangeModal(self.user)
        await interaction.response.send_modal(modal)

    async def show_history(self, interaction, start_ts, end_ts):
        history = get_user_loa_history(self.user.id, start_ts, end_ts)
        if not history:
            await interaction.response.send_message(embed=embed_info("No Records", f"No LOA records found for {self.user.mention} in that period."), ephemeral=True)
            return

        now = int(time.time())
        lines = []
        for rec in history:
            if now < rec['start']:
                status = "⏳ Upcoming"
            elif now <= rec['end']:
                status = "🟢 Active"
            else:
                status = "🔴 Ended"
            lines.append(
                f"{status}: **{rec['reason']}**\n"
                f"-# <t:{rec['start']}:D> → <t:{rec['end']}:D> | Additional: {rec.get('additional', 'N/A')}"
            )
        embed = discord.Embed(
            title=f"📜 LOA History for {self.user.display_name}",
            description="\n\n".join(lines),
            color=COLOR_INFO
        )
        await interaction.response.edit_message(content=None, embed=embed, view=None)

class CustomRangeModal(discord.ui.Modal):
    def __init__(self, user):
        super().__init__(title="Custom Date Range")
        self.user = user

        self.start = discord.ui.TextInput(
            label="Start Date (YYYY-MM-DD)",
            placeholder="e.g., 2025-01-01",
            required=True
        )
        self.add_item(self.start)

        self.end = discord.ui.TextInput(
            label="End Date (YYYY-MM-DD)",
            placeholder="e.g., 2025-01-31",
            required=True
        )
        self.add_item(self.end)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            start_dt = datetime.datetime.strptime(self.start.value, "%Y-%m-%d")
            end_dt = datetime.datetime.strptime(self.end.value, "%Y-%m-%d")
            start_ts = int(start_dt.timestamp())
            end_ts = int(end_dt.timestamp())
        except ValueError:
            await interaction.response.send_message(embed=embed_error("Invalid Format", "Invalid date format. Use YYYY-MM-DD."), ephemeral=True)
            return
        history = get_user_loa_history(self.user.id, start_ts, end_ts)
        if not history:
            await interaction.response.send_message(embed=embed_info("No Records", f"No LOA records found for {self.user.mention} in that period."), ephemeral=True)
            return
        now = int(time.time())
        lines = []
        for rec in history:
            if now < rec['start']:
                status = "⏳ Upcoming"
            elif now <= rec['end']:
                status = "🟢 Active"
            else:
                status = "🔴 Ended"
            lines.append(
                f"{status}: **{rec['reason']}**\n"
                f"-# <t:{rec['start']}:D> → <t:{rec['end']}:D> | Additional: {rec.get('additional', 'N/A')}"
            )
        embed = discord.Embed(
            title=f"📜 LOA History for {self.user.display_name}",
            description="\n\n".join(lines),
            color=COLOR_INFO
        )
        await interaction.response.edit_message(content=None, embed=embed, view=None)

# ----------------------------------------------------------------------
# Cog
# ----------------------------------------------------------------------

class LOACog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="loa", description="Send the LOA management panel to this channel.")
    async def loa_panel(self, interaction: discord.Interaction):
        if interaction.guild.id != SERVER_IDS["staff"]:
            return await interaction.response.send_message(embed=embed_error("Wrong Server", "This command can only be used in the staff server."), ephemeral=True)
        if not is_manager(interaction.user):
            return await interaction.response.send_message(embed=embed_error("Permission Denied", "You need Manager+ permissions to send this panel."), ephemeral=True)
        embed = create_loa_embed()
        view = LOAPanelView()
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message(embed=embed_success("Panel Sent", "LOA panel sent!"), ephemeral=True)

async def setup(bot):
    await bot.add_cog(LOACog(bot))