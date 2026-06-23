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

NEGATIVE_OFFSETS = [f"UTC{i}" for i in range(-12, 0)]
POSITIVE_OFFSETS = [f"UTC+{i}" for i in range(0, 15)]

LOA_LOG_CHANNEL = 1517598730973609984
APPROVAL_ROLE = 1165675275821002835
RECORDS_PER_PAGE = 5

COLOR_SUCCESS = 0x2ecc71
COLOR_ERROR   = 0xe74c3c
COLOR_INFO    = 0x1ec7f1
COLOR_WARNING = 0xf1c40f

EMOJI_EMERALD       = "<:emerald:1518031176730804244>" 
EMOJI_REDSTONE      = "<:redstone_dust:1518031324588539986>"
EMOJI_GOLD_INGOT    = "<:gold_ingot:1518031441248653433>"
EMOJI_STEVE         = "<:steve:1518031537814110382>" 
EMOJI_NETHER_STAR   = "<:nether_star:1518033504120606771>"
EMOJI_COMPASS       = "<a:compass:1518032475803226214>" 
EMOJI_ENDER_PEARL   = "<:ender_pearl:1518033866995269763>" 
EMOJI_MC_CLOCK      = "<:mc_clock:1518027805361967104>" 
EMOJI_MAP           = "<:map:1518038367521210499>" 
EMOJI_BOOK          = "<:book:1518051136488214549>" 
EMOJI_SCROLL        = "<:parchment:1518454271719510297>"
EMOJI_FEATHER       = "<:feather:1518454349053952150>"
EMOJI_BARRIER       = "<:barrier:1518454369887195228>"
EMOJI_SPYGLASS      = "<:spyglass:1518454328480891083>"
EMOJI_HOURGLASS     = "<:hourglass:1518454206162538546>"
EMOJI_LOGO          = "<:mysticraftlogo:1263811799237787789>"


def embed_success(title: str, description: str = None) -> discord.Embed:
    return discord.Embed(title=f"{EMOJI_EMERALD} {title}", description=description, color=COLOR_SUCCESS)

def embed_error(title: str, description: str = None) -> discord.Embed:
    return discord.Embed(title=f"{EMOJI_REDSTONE} {title}", description=description, color=COLOR_ERROR)

def embed_info(title: str, description: str = None) -> discord.Embed:
    return discord.Embed(title=f"{EMOJI_MAP} {title}", description=description, color=COLOR_INFO)

def embed_warning(title: str, description: str = None) -> discord.Embed:
    return discord.Embed(title=f"{EMOJI_GOLD_INGOT} {title}", description=description, color=COLOR_WARNING)


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
    now = int(time.time())
    all_loas = get_loas(status_filter="active")
    return [l for l in all_loas if l.get("end") >= now]

def get_pending_loas() -> list[dict]:
    return get_loas(status_filter="pending")

def get_user_loas(user_id: int, status_filter: str = None) -> list[dict]:
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
    return sorted(history, key=lambda x: x.get("start", 0), reverse=True)

def format_date_plain(ts: int, offset_str: str = "UTC+0") -> str:
    try:
        hours = int(re.search(r"([+-]?\d+)", offset_str).group(1))
    except:
        hours = 0
    tz = pytz.FixedOffset(hours * 60)
    dt = datetime.datetime.fromtimestamp(ts, tz)
    return dt.strftime("%Y-%m-%d")

def get_display_status(rec: dict) -> str:
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
    loas = get_active_loas()
    embed = discord.Embed(
        title=f"{EMOJI_BOOK} Staff Leave of Absence",
        color=COLOR_INFO
    )
    if not loas:
        embed.description = f"{EMOJI_EMERALD} The server is fully staffed. There are no active or upcoming LOAs right now."
        return embed

    now = int(time.time())
    active_loas = sorted([l for l in loas if l['start'] <= now], key=lambda x: x['start'])
    upcoming_loas = sorted([l for l in loas if l['start'] > now], key=lambda x: x['start'])

    if active_loas:
        lines = []
        for rec in active_loas:
            lines.append(
                f"{EMOJI_REDSTONE} <@{rec['user_id']}> — **{rec.get('reason', 'No reason')}**\n"
                f"-# <:reply:1036792837821435976> {EMOJI_MC_CLOCK} <t:{rec['start']}:D> → <t:{rec['end']}:D> *(back <t:{rec['end']}:R>)*"
            )
        embed.add_field(
            name=f"Currently Away",
            value="\n".join(lines) or "None",
            inline=False
        )

    if upcoming_loas:
        lines = []
        for rec in upcoming_loas:
            lines.append(
                f"{EMOJI_GOLD_INGOT} <@{rec['user_id']}> — **{rec.get('reason', 'No reason')}**\n"
                f"-# <:reply:1036792837821435976> {EMOJI_MC_CLOCK} <t:{rec['start']}:D> → <t:{rec['end']}:D> *(starts <t:{rec['start']}:R>)*"
            )
        embed.add_field(
            name=f"Heading Out Soon",
            value="\n".join(lines) or "None",
            inline=False
        )

    if not active_loas and not upcoming_loas:
        embed.description = f"{EMOJI_EMERALD} The server is fully staffed. There are no active or upcoming LOAs right now."

    embed.set_footer(text="Fill out the form below if you are planning to be away for 24 hours or more.")
    return embed


def meta_custom_id(record_id: str, old_record_id: str = None) -> str:
    if old_record_id:
        return f"loa_meta:{record_id}:{old_record_id}"
    return f"loa_meta:{record_id}"

def parse_meta_button(message: discord.Message) -> tuple[str | None, bool, str | None]:
    for row in message.components:
        for component in row.children:
            if isinstance(component, discord.Button) and component.custom_id and component.custom_id.startswith("loa_meta:"):
                parts = component.custom_id.split(":")
                record_id = parts[1] if len(parts) > 1 else None
                old_record_id = parts[2] if len(parts) > 2 else None
                is_edit = old_record_id is not None
                return record_id, is_edit, old_record_id
    return None, False, None

def parse_user_id(embed: discord.Embed) -> int | None:
    if not embed or not embed.description:
        return None
    match = re.search(r"<@(\d+)>", embed.description)
    return int(match.group(1)) if match else None


class MetaButton(discord.ui.Button):
    def __init__(self, record_id: str, old_record_id: str = None):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji=EMOJI_LOGO,
            custom_id=meta_custom_id(record_id, old_record_id),
            disabled=True,
        )

    async def callback(self, interaction: discord.Interaction):
        pass


class ApprovalView(discord.ui.View):
    def __init__(self, record_id: str = None, old_record_id: str = None):
        super().__init__(timeout=None)
        if record_id is not None:
            self.add_item(MetaButton(record_id, old_record_id))

    def resolve(self, interaction: discord.Interaction):
        embed0 = interaction.message.embeds[0] if interaction.message.embeds else None
        user_id = parse_user_id(embed0)
        record_id, is_edit, old_record_id = parse_meta_button(interaction.message)
        return user_id, record_id, is_edit, old_record_id

    @discord.ui.button(
        label="Approve",
        style=discord.ButtonStyle.gray,
        emoji=EMOJI_EMERALD,
        custom_id="loa_approve",
    )
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_manager(interaction.user):
            await interaction.response.send_message(
                embed=embed_error("Permission Denied", f"{EMOJI_BARRIER} Only Managers+ can approve LOAs."),
                ephemeral=True,
            )
            return
        
        embed0 = interaction.message.embeds[0] if interaction.message.embeds else None

        user_id, record_id, is_edit, old_record_id = self.resolve(interaction)
        if not user_id or not record_id:
            await interaction.response.send_message(
                embed=embed_error("Parse Error", "Couldn't read request details from this message."),
                ephemeral=True,
            )
            return

        ref = db.reference(f"LOA/{user_id}/{record_id}")
        rec = ref.get()
        if not rec:
            await interaction.response.send_message(embed=embed_error("Not Found", "This LOA record no longer exists."), ephemeral=True)
            return
        if rec.get("status") != "pending":
            await interaction.response.send_message(
                embed=embed_error("Already Resolved", f"This LOA is already marked as **{rec.get('status')}**."),
                ephemeral=True,
            )
            return

        if is_edit and old_record_id:
            old_ref = db.reference(f"LOA/{user_id}/{old_record_id}")
            old_rec = old_ref.get()
            if old_rec:
                old_ref.update({
                    "start": rec["start"],
                    "end": rec["end"],
                    "timezone_offset": rec["timezone_offset"],
                    "reason": rec["reason"],
                    "additional": rec["additional"],
                    "status": "active",
                    "updated_at": int(time.time()),
                })
                ref.delete()
                result_embed = discord.Embed(
                    title=f"{EMOJI_EMERALD} Edit Approved",
                    description=(
                        f"{EMOJI_FEATHER} The edit for <@{user_id}>'s LOA was approved by <@{interaction.user.id}>."
                    ),
                    color=COLOR_SUCCESS,
                )
                post_view = PostDecisionView()
                post_view.add_item(MetaButton(record_id))
                await interaction.response.edit_message(content=None, embeds=[result_embed, embed0], view=post_view)
                try:
                    user = await interaction.client.fetch_user(user_id)
                    await user.send(embed=discord.Embed(
                        title=f"{EMOJI_EMERALD} LOA Edit Approved",
                        description=(
                            f"Your edit request has been **approved**!\n\n"
                            f"{EMOJI_BOOK} **Reason:** {rec['reason']}\n"
                            f"{EMOJI_MC_CLOCK} **From:** <t:{rec['start']}:D>\n"
                            f"{EMOJI_MC_CLOCK} **To:** <t:{rec['end']}:D>"
                        ),
                        color=COLOR_SUCCESS,
                    ))
                except Exception:
                    pass
                return

        replaces_id = rec.get("replaces")
        if not is_edit and replaces_id:
            old_ref = db.reference(f"LOA/{user_id}/{replaces_id}")
            old_rec = old_ref.get()
            if old_rec and old_rec.get("status") == "active":
                old_ref.update({
                    "status": "replaced",
                    "replaced_by": record_id,
                    "replaced_at": int(time.time()),
                })

        ref.update({
            "status": "active",
            "approved_by": interaction.user.id,
            "approved_at": int(time.time()),
        })
        result_embed = discord.Embed(
            title=f"{EMOJI_EMERALD} LOA Approved",
            description=(
                f"{EMOJI_STEVE} <@{user_id}>'s LOA was approved by <@{interaction.user.id}>."
                + (f"\n{EMOJI_ENDER_PEARL} *Previous LOA has been replaced.*" if replaces_id else "")
            ),
            color=COLOR_SUCCESS,
        )
        post_view = PostDecisionView()
        post_view.add_item(MetaButton(record_id))
        await interaction.response.edit_message(content=None, embeds=[result_embed, embed0], view=post_view)
        try:
            user = await interaction.client.fetch_user(user_id)
            msg = (
                f"Your LOA request has been **approved**! You may log off and rest up during this time. ⛏️\n\n"
                f"{EMOJI_BOOK} **Reason:** {rec['reason']}\n"
                f"{EMOJI_MC_CLOCK} **From:** <t:{rec['start']}:D>\n"
                f"{EMOJI_MC_CLOCK} **To:** <t:{rec['end']}:D>"
            )
            if replaces_id:
                msg += f"\n{EMOJI_ENDER_PEARL} *Your previous LOA has been replaced.*"
            await user.send(embed=discord.Embed(
                title=f"{EMOJI_EMERALD} LOA Approved",
                description=msg,
                color=COLOR_SUCCESS,
            ))
        except Exception:
            pass

    @discord.ui.button(
        label="Reject",
        style=discord.ButtonStyle.gray,
        emoji=EMOJI_REDSTONE,
        custom_id="loa_reject",
    )
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_manager(interaction.user):
            await interaction.response.send_message(
                embed=embed_error("Permission Denied", f"{EMOJI_BARRIER} Only Managers+ can reject LOAs."),
                ephemeral=True,
            )
            return

        embed0 = interaction.message.embeds[0] if interaction.message.embeds else None
        user_id, record_id, is_edit, old_record_id = self.resolve(interaction)
        if not user_id or not record_id:
            await interaction.response.send_message(
                embed=embed_error("Parse Error", "Couldn't read request details from this message."),
                ephemeral=True,
            )
            return

        ref = db.reference(f"LOA/{user_id}/{record_id}")
        rec = ref.get()
        if not rec:
            await interaction.response.send_message(embed=embed_error("Not Found", "This LOA record no longer exists."), ephemeral=True)
            return
        if rec.get("status") != "pending":
            await interaction.response.send_message(
                embed=embed_error("Already Resolved", f"This LOA is already marked as **{rec.get('status')}**."),
                ephemeral=True,
            )
            return

        if is_edit and old_record_id:
            ref.delete()
            result_embed = discord.Embed(
                title=f"{EMOJI_REDSTONE} Edit Rejected",
                description=(
                    f"{EMOJI_FEATHER} The edit request for <@{user_id}> was **rejected** by <@{interaction.user.id}>. "
                    f"The original LOA remains unchanged."
                ),
                color=COLOR_ERROR,
            )
            post_view = PostDecisionView()
            post_view.add_item(MetaButton(record_id))
            await interaction.response.edit_message(content=None, embeds=[result_embed, embed0], view=post_view)
            try:
                user = await interaction.client.fetch_user(user_id)
                await user.send(embed=discord.Embed(
                    title=f"{EMOJI_REDSTONE} LOA Edit Rejected",
                    description=(
                        f"Your request to edit your LOA was **rejected** by <@{interaction.user.id}>.\n"
                        f"Your original LOA remains active. If you go inactive during this period it may affect your staff rank."
                    ),
                    color=COLOR_ERROR,
                ))
            except Exception:
                pass
            return

        ref.update({
            "status": "rejected",
            "rejected_by": interaction.user.id,
            "rejected_at": int(time.time()),
        })
        result_embed = discord.Embed(
            title=f"{EMOJI_REDSTONE} LOA Rejected",
            description=(
                f"{EMOJI_STEVE} <@{user_id}>'s LOA was **rejected** by <@{interaction.user.id}>."
            ),
            color=COLOR_ERROR,
        )
        post_view = PostDecisionView()
        post_view.add_item(MetaButton(record_id))
        await interaction.response.edit_message(content=None, embeds=[result_embed, embed0], view=post_view)
        try:
            user = await interaction.client.fetch_user(user_id)
            await user.send(embed=discord.Embed(
                title=f"{EMOJI_REDSTONE} LOA Rejected",
                description=(
                    f"Your LOA request was **rejected**. If you go inactive during this period it may affect your staff rank.\n\n"
                    f"{EMOJI_BOOK} **Reason:** {rec['reason']}\n"
                    f"{EMOJI_MC_CLOCK} **From:** <t:{rec['start']}:D>\n"
                    f"{EMOJI_MC_CLOCK} **To:** <t:{rec['end']}:D>\n\n"
                    f"If you believe this is a mistake, please reach out to your Mentor."
                ),
                color=COLOR_ERROR,
            ))
        except Exception:
            pass

    @discord.ui.button(
        label="History",
        style=discord.ButtonStyle.secondary,
        emoji=EMOJI_BOOK,
        custom_id="loa_history",
    )
    async def view_history(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_manager(interaction.user):
            await interaction.response.send_message(
                embed=embed_error("Permission Denied", f"{EMOJI_BARRIER} Only Managers+ can view LOA history."),
                ephemeral=True,
            )
            return

        embed0 = interaction.message.embeds[0] if interaction.message.embeds else None
        user_id, _, _, _ = self.resolve(interaction)
        if not user_id:
            await interaction.response.send_message(
                embed=embed_error("Parse Error", "Couldn't determine the user from this message."),
                ephemeral=True,
            )
            return

        history = get_user_loa_history(user_id)
        if not history:
            await interaction.response.send_message(
                embed=embed_info("No Records", f"No LOA history on file for <@{user_id}>."),
                ephemeral=True,
            )
            return

        pages = build_history_pages(user_id, history)
        await interaction.response.send_message(
            embed=pages[0],
            view=HistoryPageView(pages),
            ephemeral=True,
        )


class DeleteConfirmView(discord.ui.View):
    def __init__(self, user_id: int, record_id: str, ref, original_message: discord.Message):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.record_id = record_id
        self.ref = ref
        self.original_message = original_message

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.gray, emoji=EMOJI_BARRIER)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        rec = self.ref.get()
        if not rec:
            await interaction.response.edit_message(
                embed=embed_error("Not Found", "This LOA record no longer exists."),
                view=None,
            )
            return

        self.ref.delete()
        result_embed = discord.Embed(
            title=f"{EMOJI_BARRIER} LOA Deleted",
            description=(
                f"{EMOJI_FEATHER} The LOA record for <@{self.user_id}> was deleted by <@{interaction.user.id}>."
            ),
            color=COLOR_ERROR,
        )
        await interaction.response.edit_message(embed=result_embed, view=None)

        try:
            original_view = discord.ui.View.from_message(self.original_message, timeout=None)
            for item in original_view.children:
                if isinstance(item, discord.ui.Button) and item.custom_id == "loa_post_delete":
                    item.label = "Record Deleted"
                    item.style = discord.ButtonStyle.danger
                    item.disabled = True
                    item.emoji = ""
                    break
            await self.original_message.edit(view=original_view)
        except Exception:
            pass

    async def on_timeout(self):
        pass


class PostDecisionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def resolve(self, interaction: discord.Interaction):
        """Return (user_id, record_id) from the message."""
        embed0 = interaction.message.embeds[0] if interaction.message.embeds else None
        user_id = parse_user_id(embed0)
        record_id, _, _ = parse_meta_button(interaction.message)
        return user_id, record_id

    @discord.ui.button(
        label="Delete Record",
        style=discord.ButtonStyle.gray,
        emoji=EMOJI_BARRIER,
        custom_id="loa_post_delete",
    )
    async def delete_record(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_manager(interaction.user):
            await interaction.response.send_message(
                embed=embed_error("Permission Denied", f"{EMOJI_BARRIER} Only Managers+ can delete LOA records."),
                ephemeral=True,
            )
            return

        user_id, record_id = self.resolve(interaction)
        if not user_id or not record_id:
            await interaction.response.send_message(
                embed=embed_error("Parse Error", "Couldn't read record details from this message."),
                ephemeral=True,
            )
            return

        ref = db.reference(f"LOA/{user_id}/{record_id}")
        rec = ref.get()
        if not rec:
            await interaction.response.send_message(
                embed=embed_error("Not Found", "This LOA record no longer exists."),
                ephemeral=True,
            )
            return

        now = int(time.time())
        status = rec.get("status", "unknown")
        start_ts = rec.get("start", 0)
        end_ts = rec.get("end", 0)
        is_active = status == "active" and start_ts <= now <= end_ts
        is_upcoming = status == "active" and start_ts > now

        impact_lines = [
            f"{EMOJI_STEVE} **User:** <@{user_id}>",
            f"{EMOJI_BOOK} **Reason:** {rec.get('reason', 'No reason')}",
            f"{EMOJI_MC_CLOCK} **Period:** <t:{start_ts}:D> → <t:{end_ts}:D>",
            f"{EMOJI_HOURGLASS} **Status:** {status.title()}",
        ]
        if is_active:
            impact_lines.append(f"\n{EMOJI_GOLD_INGOT} **Warning:** This LOA is **currently active**. Deleting it will remove them from the active LOA list immediately.")
        elif is_upcoming:
            impact_lines.append(f"\n{EMOJI_GOLD_INGOT} **Warning:** This LOA is **upcoming**. The staff member will not be notified of this deletion.")
        else:
            impact_lines.append(f"\n{EMOJI_EMERALD} This record is no longer active. Deletion will only affect history.")

        confirm_embed = discord.Embed(
            title=f"{EMOJI_BARRIER} Confirm Deletion",
            description="\n".join(impact_lines),
            color=COLOR_WARNING,
        )
        confirm_embed.set_footer(text="This action is permanent and cannot be undone.")

        await interaction.response.send_message(
            embed=confirm_embed,
            view=DeleteConfirmView(user_id, record_id, ref, interaction.message),
            ephemeral=True,
        )

    @discord.ui.button(
        label="History",
        style=discord.ButtonStyle.secondary,
        emoji=EMOJI_BOOK,
        custom_id="loa_post_history",
    )
    async def view_history(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_manager(interaction.user):
            await interaction.response.send_message(
                embed=embed_error("Permission Denied", f"{EMOJI_BARRIER} Only Managers+ can view LOA history."),
                ephemeral=True,
            )
            return

        user_id, _ = self.resolve(interaction)
        if not user_id:
            await interaction.response.send_message(
                embed=embed_error("Parse Error", "Couldn't determine the user from this message."),
                ephemeral=True,
            )
            return

        history = get_user_loa_history(user_id)
        if not history:
            await interaction.response.send_message(
                embed=embed_info("No Records", f"No LOA history on file for <@{user_id}>."),
                ephemeral=True,
            )
            return

        pages = build_history_pages(user_id, history)
        await interaction.response.send_message(
            embed=pages[0],
            view=HistoryPageView(pages),
            ephemeral=True,
        )

def status(rec: dict) -> tuple[str, str]:
    now = int(time.time())
    status = rec.get("status", "unknown")
    if status == "active":
        if rec.get("start", 0) > now:
            return EMOJI_GOLD_INGOT, "Upcoming"
        elif rec.get("end", 0) >= now:
            return EMOJI_EMERALD, "Active"
        else:
            return EMOJI_COMPASS, "Ended"
    elif status == "pending":
        return EMOJI_GOLD_INGOT, "Pending"
    elif status == "rejected":
        return EMOJI_REDSTONE, "Rejected"
    elif status == "replaced":
        return EMOJI_ENDER_PEARL, "Replaced"
    else:
        return EMOJI_NETHER_STAR, status.title()


def build_history_pages(user_id: int, history: list[dict], title_suffix: str = "") -> list[discord.Embed]:
    STATUS_COLORS = {
        "active":   COLOR_SUCCESS,
        "pending":  COLOR_WARNING,
        "rejected": COLOR_ERROR,
        "replaced": COLOR_INFO,
    }

    counts: dict[str, int] = {}
    for rec in history:
        s = rec.get("status", "unknown")
        counts[s] = counts.get(s, 0) + 1

    summary_parts = []
    if counts.get("active"):
        summary_parts.append(f"{EMOJI_EMERALD} {counts['active']} active")
    if counts.get("pending"):
        summary_parts.append(f"{EMOJI_GOLD_INGOT} {counts['pending']} pending")
    if counts.get("rejected"):
        summary_parts.append(f"{EMOJI_REDSTONE} {counts['rejected']} rejected")
    if counts.get("replaced"):
        summary_parts.append(f"{EMOJI_ENDER_PEARL} {counts['replaced']} replaced")
    summary_line = "  •  ".join(summary_parts) if summary_parts else "No records"

    record_lines: list[str] = []
    for rec in history:
        emoji, label = status(rec)
        duration_days = max(1, (rec.get("end", rec.get("start", 0)) - rec.get("start", 0)) // 86400 + 1)
        day_word = "day" if duration_days == 1 else "days"
        additional = rec.get("additional", "").strip()
        line = (
            f"{emoji} **{rec.get('reason', 'No reason')}** — *{label}*\n"
            f"-# <:reply:1036792837821435976> {EMOJI_MC_CLOCK} <t:{rec['start']}:D> → <t:{rec['end']}:D>  "
            f"({duration_days} {day_word})"
        )
        if additional:
            line += f"\n-# {EMOJI_BOOK} {additional}"
        record_lines.append(line)

    chunks = [record_lines[i:i + RECORDS_PER_PAGE] for i in range(0, len(record_lines), RECORDS_PER_PAGE)]
    total_pages = len(chunks)
    embed_color = STATUS_COLORS.get(history[0].get("status", "active"), COLOR_INFO)

    pages: list[discord.Embed] = []
    for page_idx, chunk in enumerate(chunks):
        header = (
            f"-# <@{user_id}>  •  {len(history)} record{'s' if len(history) != 1 else ''}  •  "
            f"newest first\n{summary_line}\n"
        )
        embed = discord.Embed(
            title=f"{EMOJI_BOOK} LOA History{title_suffix}",
            description=header + "\n" + "\n\n".join(chunk),
            color=embed_color,
        )
        embed.set_footer(text=f"Page {page_idx + 1} of {total_pages}  •  Records sorted newest → oldest")
        pages.append(embed)

    return pages


class HistoryPageView(discord.ui.View):
    def __init__(self, pages: list[discord.Embed]):
        super().__init__(timeout=180)
        self.pages = pages
        self.page = 0
        if len(pages) <= 1:
            for item in self.children:
                item.disabled = True

    def update_embed(self) -> discord.Embed:
        return self.pages[self.page]

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji="<:fastbackward:1351972112696479824>")
    async def super_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 0
        await interaction.response.edit_message(embed=self.update_embed(), view=self)

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji="<:backarrow:1351972111010369618>")
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page - 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.update_embed(), view=self)

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji="<:rightarrow:1351972116819480616>")
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page + 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.update_embed(), view=self)

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji="<:fastforward:1351972114433048719>")
    async def super_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = len(self.pages) - 1
        await interaction.response.edit_message(embed=self.update_embed(), view=self)


class LOAPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Request LOA", style=discord.ButtonStyle.primary, custom_id="loa_submit", emoji=EMOJI_SCROLL, row=0)
    async def submit_loa(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message(embed=embed_error("Access Denied", "You are not a staff member."), ephemeral=True)
            return

        existing = get_user_loas(interaction.user.id, status_filter="active")
        now = int(time.time())
        existing = [l for l in existing if l.get("end") >= now]
        if existing:
            view = ReplaceOrNewView(interaction.user.id, existing)
            await interaction.response.send_message(
                embed=embed_warning(
                    "You've Already Got One!",
                    f"{EMOJI_ENDER_PEARL} You already have an active or upcoming LOA.\n"
                    "Want to **replace it** with a new one, or **add a separate LOA** on top?"
                ),
                view=view,
                ephemeral=True
            )
        else:
            view = DateRangeSelectView(interaction.user.id)
            await interaction.response.send_message(
                embed=embed_info(
                    "Pick Your Dates",
                    f"{EMOJI_MC_CLOCK} Select the **start** and **end** dates of your LOA. "
                    "Please choose based on **your local calendar**. You'll pick your timezone next."
                ),
                view=view,
                ephemeral=True
            )

    @discord.ui.button(label="Edit LOA", style=discord.ButtonStyle.blurple, custom_id="loa_edit", emoji=EMOJI_FEATHER, row=0)
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
        await interaction.response.send_message(
            embed=embed_info(
                "Select LOA to Edit",
                f"{EMOJI_FEATHER} Choose the LOA you want to edit:"
            ),
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="Sync", style=discord.ButtonStyle.grey, custom_id="loa_sync", emoji=EMOJI_COMPASS, row=0)
    async def sync(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_loa_embed(), view=self)

    @discord.ui.button(label="Check User", style=discord.ButtonStyle.secondary, custom_id="loa_check", emoji=EMOJI_SPYGLASS, row=0)
    async def check_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_manager(interaction.user):
            await interaction.response.send_message(embed=embed_error("Permission Denied", "Only Managers+ can check other users' LOA history."), ephemeral=True)
            return
        view = UserSelectView()
        await interaction.response.send_message(
            embed=embed_info("Lookup Player", f"{EMOJI_SPYGLASS} Select a staff member to pull up their LOA records:"),
            view=view,
            ephemeral=True
        )


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
        super().__init__(placeholder=f"Choose which LOA to edit...", options=options[:25])
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
            default=format_date_plain(current_data['start'], current_data.get('timezone_offset', 'UTC+0')),
            required=True
        )
        self.add_item(self.start_date)

        self.end_date = discord.ui.TextInput(
            label="New End Date (YYYY-MM-DD)",
            placeholder="e.g., 2026-07-05",
            default=format_date_plain(current_data['end'], current_data.get('timezone_offset', 'UTC+0')),
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
                title=f"{EMOJI_FEATHER} LOA Edit Request",
                description=f"{EMOJI_STEVE} <@{self.user_id}> wants to update their LOA details.",
                color=COLOR_WARNING,
            )
            embed.add_field(
                name=f"{EMOJI_REDSTONE} Original LOA",
                value=f"> **{self.current_data.get('reason', 'No reason')}**\n-# <:reply:1036792837821435976> {EMOJI_MC_CLOCK} <t:{self.current_data['start']}:D> → <t:{self.current_data['end']}:D>",
                inline=False
            )
            embed.add_field(
                name=f"{EMOJI_EMERALD} Requested Changes",
                value=f"> **{self.reason.value}**\n-# <:reply:1036792837821435976> {EMOJI_MC_CLOCK} <t:{start_ts}:D> → <t:{end_ts}:D>",
                inline=False
            )
            if self.additional.value:
                embed.add_field(name=f"{EMOJI_FEATHER} Additional Info", value=self.additional.value, inline=False)

            view = ApprovalView(new_record_id, self.record_id)
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
        super().__init__(placeholder=f"{EMOJI_ENDER_PEARL} Choose LOA to replace...", options=options[:25])
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        record_id = self.values[0]
        self.parent_view.replace_record_id = record_id
        view = DateRangeSelectView(self.parent_view.user_id, replace_record_id=record_id)
        await interaction.response.edit_message(
            embed=embed_info(
                "Pick New Dates",
                f"{EMOJI_ENDER_PEARL} Select the new **start** and **end** dates for your replacement LOA."
            ),
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
        embed = embed_info("Pick Your Dates", "").set_footer(text="Start and end can be the same day for a 1-day LOA.")
        desc = (
            f"{EMOJI_MC_CLOCK} Select the **start** (green) and **end** (red) dates for your LOA. "
            "Please choose based on **your local calendar**. You'll pick your timezone next.\n\n"
        )
        if self.start_date:
            desc += f"-# **Start:** {self.start_date.strftime('%Y-%m-%d')}\n"
        if self.end_date:
            desc += f"-# **End:** {self.end_date.strftime('%Y-%m-%d')}\n"
            duration = (self.end_date - self.start_date).days + 1
            desc += f"-# **Duration:** {duration} day{'s' if duration != 1 else ''}\n"
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
        super().__init__(label="Confirm Dates", style=discord.ButtonStyle.success, row=row, emoji=EMOJI_MC_CLOCK)
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
                "Set Your Timezone",
                f"{EMOJI_MC_CLOCK} Pick your **closest timezone** from one of the dropdowns. "
                "This defines where your calendar day starts and ends (midnight to midnight). "
                "Dates shown in the panel will auto-convert to everyone's own local time.\n"
            ),
            view=view
        )


class CancelButton(discord.ui.Button):
    def __init__(self, row):
        super().__init__(label="Cancel", style=discord.ButtonStyle.danger, row=row)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            embed=embed_error("Cancelled", "LOA submission successfully cancelled."),
            view=None
        )


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
            title=f"{EMOJI_MC_CLOCK} Timezone Set",
            description=(
                f"{EMOJI_EMERALD} Locked in: **{offset}** (your local time right now: **{time_str}**)\n\n"
                f"Your LOA will run from **<t:{start_ts}:D>** to **<t:{end_ts}:D>**.\n"
                f"-# Dates display in everyone's local timezone in the panel.\n\n"
                f"Click **Next** to fill in the details, or **Back** to change your dates."
            ),
            color=COLOR_INFO,
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
            title=f"{EMOJI_MC_CLOCK} Timezone Set",
            description=(
                f"{EMOJI_EMERALD} Locked in: **{offset}** (your local time right now: **{time_str}**)\n\n"
                f"Your LOA will run from **<t:{start_ts}:D>** to **<t:{end_ts}:D>**.\n"
                f"-# Dates display in everyone's local timezone in the panel.\n\n"
                f"Click **Next** to fill in the details, or **Back** to change your dates."
            ),
            color=COLOR_INFO,
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
        await interaction.response.edit_message(embed=view.get_embed(), view=view)


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
            placeholder="Any extra details before sending off",
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
            warning = f"\n{EMOJI_GOLD_INGOT} **Note:** This LOA is longer than 7 days. Your Mentor may reach out for more details before it's approved."

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
                title=f"{EMOJI_SCROLL} New LOA Request",
                description=f"{EMOJI_STEVE} <@{self.user_id}> is heading out and needs some time away.",
                color=COLOR_WARNING,
            )
            embed.add_field(name=f"{EMOJI_BOOK} Reason", value=self.reason.value, inline=False)
            embed.add_field(name=f"{EMOJI_MC_CLOCK} Start Date", value=f"<t:{start_ts}:D>", inline=True)
            embed.add_field(name=f"{EMOJI_MC_CLOCK} End Date", value=f"<t:{end_ts}:D>", inline=True)
            embed.add_field(name=f"{EMOJI_HOURGLASS} Duration", value=f"{duration_days} day{'s' if duration_days != 1 else ''}", inline=True)
            embed.add_field(name=f"{EMOJI_COMPASS} Timezone", value=self.tz_offset, inline=True)
            if self.additional.value:
                embed.add_field(name=f"{EMOJI_FEATHER} Additional Info", value=self.additional.value, inline=False)
            if self.replace_record_id:
                embed.add_field(name=f"{EMOJI_ENDER_PEARL} Replaces", value=f"Record `{self.replace_record_id}` (previous LOA)", inline=False)
            # embed.set_footer(text=f"Record ID: {record_id}")

            view = ApprovalView(record_id)
            await log_channel.send(f"<@&{APPROVAL_ROLE}>", embed=embed, view=view)

        await interaction.response.send_message(
            embed=embed_success(
                "LOA Submitted",
                f"Your leave request is in! A manager will review it shortly. {EMOJI_COMPASS}\n"
                f"You'll get a DM once it's approved or rejected.{warning}"
            ),
            ephemeral=True
        )


class UserSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(UserSelectDropdown())

class UserSelectDropdown(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder=f"Choose a staff member to look up...", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        user = self.values[0]
        view = HistoryRangeView(user)
        await interaction.response.edit_message(
            embed=discord.Embed(
                title=f"{EMOJI_SPYGLASS} Choose a Time Range",
                description=f"Pulling records for {user.mention}. How far back do you want to look?",
                color=COLOR_INFO,
            ),
            view=view
        )

class HistoryRangeView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=120)
        self.user = user

    @discord.ui.button(label="Last 30 Days", style=discord.ButtonStyle.secondary, emoji=EMOJI_MC_CLOCK)
    async def last30(self, interaction: discord.Interaction, button: discord.ui.Button):
        end = int(time.time())
        start = end - 30*86400
        await self.show_history(interaction, start, end, "Last 30 Days")

    @discord.ui.button(label="Last 90 Days", style=discord.ButtonStyle.secondary, emoji=EMOJI_COMPASS)
    async def last90(self, interaction: discord.Interaction, button: discord.ui.Button):
        end = int(time.time())
        start = end - 90*86400
        await self.show_history(interaction, start, end, "Last 90 Days")

    @discord.ui.button(label="All Time", style=discord.ButtonStyle.secondary, emoji=EMOJI_NETHER_STAR)
    async def all_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_history(interaction, None, None, "All Time")

    @discord.ui.button(label="Custom Range", style=discord.ButtonStyle.primary, emoji=EMOJI_FEATHER)
    async def custom(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CustomRangeModal(self.user)
        await interaction.response.send_modal(modal)

    async def show_history(self, interaction, start_ts, end_ts, range_label: str = ""):
        history = get_user_loa_history(self.user.id, start_ts, end_ts)
        if not history:
            await interaction.response.edit_message(
                embed=embed_info(
                    "No Records Found",
                    f"No LOA records on file for {self.user.mention} in that period.\n\n"
                    f"-# They've been loyally grinding away! {EMOJI_EMERALD}"
                ),
                view=None,
            )
            return
        suffix = f" of {self.user.display_name}" + (f" ({range_label})" if range_label else "")
        pages = build_history_pages(self.user.id, history, title_suffix=suffix)
        await interaction.response.edit_message(
            content=None,
            embed=pages[0],
            view=HistoryPageView(pages),
        )

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
            await interaction.response.edit_message(
                embed=embed_info(
                    "No Records Found",
                    f"No LOA records on file for {self.user.mention} in that date range.\n"
                    f"-# Nothing to see here, keep mining! {EMOJI_EMERALD}"
                ),
                view=None,
            )
            return
        suffix = f" of {self.user.display_name} ({self.start.value} → {self.end.value})"
        pages = build_history_pages(self.user.id, history, title_suffix=suffix)
        await interaction.response.edit_message(
            content=None,
            embed=pages[0],
            view=HistoryPageView(pages),
        )


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