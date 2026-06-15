import discord
import datetime
import re
import emoji
import time
import asyncio
import io
import random
import pytz

from discord import app_commands
from discord.ext import commands
from firebase_admin import db

# Tier definitions for rep roles
TIER_THRESHOLDS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 120, 140, 160, 190, 220, 250, 290, 330, 370, 420, 470, 500]
TIER_NAMES = [
    "Leather I", "Leather II", "Leather III",
    "Iron I", "Iron II", "Iron III",
    "Gold I", "Gold II", "Gold III",
    "Diamond I", "Diamond II", "Diamond III",
    "Emerald I", "Emerald II", "Emerald III",
    "Amethyst I", "Amethyst II", "Amethyst III",
    "Crimson I", "Crimson II", "Crimson III",
    "Crown Tier"
]
TIER_ROLES = {
    0: 1467403902667460775, 1: 1467403902667460775, 2: 1467403902667460775,  # Leather
    3: 1467403910196232408, 4: 1467403910196232408, 5: 1467403910196232408,  # Iron
    6: 1467403910724587571, 7: 1467403910724587571, 8: 1467403910724587571,  # Gold
    9: 1467403911433293928, 10: 1467403911433293928, 11: 1467403911433293928,  # Diamond
    12: 1467403911882084412, 13: 1467403911882084412, 14: 1467403911882084412,  # Emerald
    15: 1467404857047515177, 16: 1467404857047515177, 17: 1467404857047515177,  # Amethyst
    18: 1467404939251679437, 19: 1467404939251679437, 20: 1467404939251679437,  # Crimson
    21: 1467404979709939927  # Crown
}
MAIN_TIERS = ["Leather", "Iron", "Gold", "Diamond", "Emerald", "Amethyst", "Crimson", "Crown"]
TIER_TO_MAIN = {
    0: 0, 1: 0, 2: 0,
    3: 1, 4: 1, 5: 1,
    6: 2, 7: 2, 8: 2,
    9: 3, 10: 3, 11: 3,
    12: 4, 13: 4, 14: 4,
    15: 5, 16: 5, 17: 5,
    18: 6, 19: 6, 20: 6,
    21: 7
}

tier_colors = {
        0: (139, 69, 19), 1: (139, 69, 19), 2: (139, 69, 19),  # Leather brown
        3: (128, 128, 128), 4: (128, 128, 128), 5: (128, 128, 128),  # Iron gray
        6: (255, 215, 0), 7: (255, 215, 0), 8: (255, 215, 0),  # Gold yellow
        9: (0, 191, 255), 10: (0, 191, 255), 11: (0, 191, 255),  # Diamond blue
        12: (0, 128, 0), 13: (0, 128, 0), 14: (0, 128, 0),  # Emerald green
        15: (128, 0, 128), 16: (128, 0, 128), 17: (128, 0, 128),  # Amethyst purple
        18: (220, 20, 60), 19: (220, 20, 60), 20: (220, 20, 60),  # Crimson red
        21: (255, 215, 0)  # Crown gold
    }

def get_tier_index(rep_total):
    for i, thresh in enumerate(TIER_THRESHOLDS):
        if rep_total >= thresh:
            continue
        else:
            return i - 1 if i > 0 else 0
    return len(TIER_THRESHOLDS) - 1  # Max tier


def return_item(obj):
    # HT Waitlist Role ID, HT Waitlist Channel ID, Eligible HT Tester Role IDs
    if "npot" in obj:
        item = [1467960692375027853, 1467954769506074646, [1304846692096671834, 1304847150760460409, 1304847441857613834]]
    elif "dpot" in obj:
        item = [1467960696527655127, 1467954803270226032, [1338240051309580288, 1338240943031320718, 1338241525863284836]]
    elif "smp" in obj:
        item = [1467960703515099177, 1467954948552658944, [1304846892060115025, 1304847357208432700, 1304847712671371345]]
    elif "sword" in obj:
        item = [1467960708124905733, 1467954842357203067, [1304846965594652693, 1304847399088554045, 1304847767964749906]]
    elif "crystal" in obj:
        item = [1467960908168036443, 1467955000461361205, [1304846803883266069, 1304847259367637002, 1304847608870604873]]
    elif "axe" in obj:
        item = [1467960923741225074, 1467955033533448394, [1338240132548919407, 1338240866732740609, 1338241445680644178]]
    elif "mace" in obj:
        item = [1467960939444961422, 1467955070359572533, [1304846753580847164, 1304847218766778398, 1304847550465048719]]
    elif "uhc" in obj:
        item = [1467960956423503954, 1467955097840517314, [1304846846979604580, 1304847311351840903, 1304847667989581918]]
    return item

AUTHORIZED_USERS = [692254240290242601, 840972960793100309]
LINKED_ROLE_ID = 1459863162223595656
LINKED_LOG_CHANNEL_ID = 1460005738897473706
RESTRICTED_ROLE_ID = 1340417478857068564

ht_user_sessions = {}

class HTScheduleSession:
    def __init__(self, user_id, tz, thread_id, tester_id):
        self.user_id = user_id
        self.timezone = tz
        self.thread_id = thread_id
        self.tester_id = tester_id
        self.selections = {}  # date_str -> set(hours)


def _has_restricted_role(member: discord.Member | discord.User | None) -> bool:
    return bool(member and getattr(member, "roles", None) and any(role.id == RESTRICTED_ROLE_ID for role in member.roles))


async def _deny_if_restricted(interaction: discord.Interaction, *members, message: str = "<:cross1:1339153202859474956> This user is restricted from using HT waitlist actions.") -> bool:
    if any(_has_restricted_role(member) for member in members if member is not None):
        await interaction.response.send_message(message, ephemeral=True)
        return True
    return False

class HTTimezoneModal(discord.ui.Modal, title='Enter your Timezone'):
    timezone = discord.ui.TextInput(
        label='Your Timezone (e.g. America/New_York)',
        placeholder='Copy from https://mysticraft.xyz/timezone',
        required=True
    )

    def __init__(self, is_player: bool, thread_id: int, user_id: int, tester_id: int):
        super().__init__()
        self.is_player = is_player
        self.thread_id = thread_id
        self.user_id = user_id
        self.tester_id = tester_id

    async def on_submit(self, interaction: discord.Interaction):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        tz_str = self.timezone.value.strip()
        try:
            tz = pytz.timezone(tz_str)
        except pytz.UnknownTimeZoneError:
            try:
                tz = pytz.timezone(tz_str.upper())
            except pytz.UnknownTimeZoneError:
                return await interaction.response.send_message(f"Unknown timezone: `{tz_str}`. Please use a valid TZ database name like `America/New_York`, `Europe/London`, or `UTC`. Check your timezone at https://mysticraft.xyz/timezone", ephemeral=True)
        
        if self.is_player:
            session = HTScheduleSession(self.user_id, tz.zone, self.thread_id, self.tester_id)
            ht_user_sessions[interaction.user.id] = session
            view = HTDateSelectView(session)
            embed = discord.Embed(
                title="📅 Step 1: Select Dates",
                description=(
                    "Please select the dates you are available to take the test.\n\n"
                    "**Instructions:**\n"
                    "1. Click on a date below.\n"
                    "2. Select **all** the hours you are available on that date.\n"
                    "3. Click **Back** to select more dates if needed.\n"
                    "4. Once you have selected all your available times across all dates, click **Submit**.\n\n"
                    f"**Your Timezone:** `{session.timezone}`\n\n"
                    "-# Please choose as many time slots as possible to maximize your chances of not getting skipped."
                ),
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            ref = db.reference(f"/HT Schedules/{self.thread_id}")
            data = ref.get()
            grouped_ts = {}
            for ts in sorted(data["slots"]):
                dt = datetime.datetime.fromtimestamp(ts, pytz.UTC).astimezone(tz)
                date_label = dt.strftime("%B %-d")
                grouped_ts.setdefault(date_label, []).append(ts)
            
            view = HTScheduleDateSelectView(grouped_ts, self.user_id, data["player_tz"], tz.zone, self.thread_id)
            embed = discord.Embed(
                title="📅 Schedule Test: Select Date",
                description=(
                    f"Please select a date to schedule the test with <@{self.user_id}>.\n\n"
                    f"**Your Timezone:** `{tz.zone}`\n\n"
                    "The time slots are displayed in your timezone. Please pick a date/time that works best for you, then click **Submit** to confirm the schedule.\n\n"
                ),
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class HTDateSelectView(discord.ui.View):
    def __init__(self, session: HTScheduleSession):
        super().__init__(timeout=600)
        self.session = session
        now = datetime.datetime.now(pytz.timezone(session.timezone))
        self.dates = [(now + datetime.timedelta(days=i)).date() for i in range(14)]
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        for date in self.dates:
            date_str = date.isoformat()
            label = date.strftime("%b %d")
            style = (discord.ButtonStyle.green
                     if date_str in self.session.selections and self.session.selections[date_str]
                     else discord.ButtonStyle.secondary)
            self.add_item(HTDateButton(label, date_str, style))
        self.add_item(HTSubmitButton(self.session))

class HTDateButton(discord.ui.Button):
    def __init__(self, label, date_str, style):
        super().__init__(label=label, style=style, custom_id=f"ht_date:{date_str}")
        self.date_str = date_str

    async def callback(self, interaction: discord.Interaction):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        session = ht_user_sessions.get(interaction.user.id)
        if not session:
            return await interaction.response.send_message("Session expired. Please click Schedule Test again.", ephemeral=True)
        session.selections.setdefault(self.date_str, set())
        view = HTTimeSelectView(session, self.date_str)
        date_formatted = datetime.datetime.fromisoformat(self.date_str).strftime('%B %d')
        embed = discord.Embed(
            title=f"⏰ Step 2: Select Times for {date_formatted}",
            description=(
                f"Select **all** the hours you are available on **{date_formatted}**.\n\n"
                "**Instructions:**\n"
                "1. Click the buttons below to toggle your availability for each hour.\n"
                "2. Green buttons indicate selected times.\n"
                "3. Click **Back** when you are done with this date to select other dates or to **Submit**.\n\n"
                f"**Your Timezone:** `{session.timezone}`\n\n"
                "-# Please choose as many time slots as possible to maximize your chances of not getting skipped."
            ),
            color=discord.Color.green()
        )
        await interaction.response.edit_message(content=None, embed=embed, view=view)

class HTBackButton(discord.ui.Button):
    def __init__(self, session: HTScheduleSession, date_str: str):
        super().__init__(label="Back", style=discord.ButtonStyle.blurple, custom_id="ht_back_to_dates")
        self.session = session
        self.date_str = date_str

    async def callback(self, interaction: discord.Interaction):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        view = HTDateSelectView(self.session)
        embed = discord.Embed(
            title="📅 Step 1: Select Dates",
            description=(
                "Please select the dates you are available to take the test.\n\n"
                "**Instructions:**\n"
                "1. Click on a date below.\n"
                "2. Select **all** the hours you are available on that date.\n"
                "3. Click **Back** to select more dates if needed.\n"
                "4. Once you have selected all your available times across all dates, click **Submit**.\n\n"
                f"**Your Timezone:** `{self.session.timezone}`\n\n"
                "-# Please choose as many time slots as possible to maximize your chances of not getting skipped."
            ),
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(content=None, embed=embed, view=view)

class HTTimeSelectView(discord.ui.View):
    def __init__(self, session: HTScheduleSession, date_str: str):
        super().__init__(timeout=600)
        self.session = session
        self.date_str = date_str
        now = datetime.datetime.now(pytz.timezone(session.timezone))
        if now.date().isoformat() == date_str:
            start = now.hour + 1
        else:
            start = 0
        self.hours = list(range(start, 24))
        self.build_view()

    def build_view(self):
        self.clear_items()
        for hour in self.hours:
            label = f"{hour:02d}:00"
            selected = hour in self.session.selections.get(self.date_str, set())
            style = discord.ButtonStyle.green if selected else discord.ButtonStyle.secondary
            self.add_item(HTTimeButton(label, self.date_str, hour, style))
        self.add_item(HTBackButton(self.session, self.date_str))

class HTTimeButton(discord.ui.Button):
    def __init__(self, label, date_str, hour, style):
        super().__init__(label=label, style=style, custom_id=f"ht_time:{date_str}:{hour}")
        self.date_str = date_str
        self.hour = hour

    async def callback(self, interaction: discord.Interaction):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        session = ht_user_sessions.get(interaction.user.id)
        if not session:
            return await interaction.response.send_message("Session expired. Please click Schedule Test again.", ephemeral=True)
        hours = session.selections.setdefault(self.date_str, set())
        if self.hour in hours:
            hours.remove(self.hour)
        else:
            hours.add(self.hour)
        view = HTTimeSelectView(session, self.date_str)
        date_formatted = datetime.datetime.fromisoformat(self.date_str).strftime('%B %d')
        embed = discord.Embed(
            title=f"⏰ Step 2: Select Times for {date_formatted}",
            description=(
                f"Select **all** the hours you are available on **{date_formatted}**.\n\n"
                "**Instructions:**\n"
                "1. Click the buttons below to toggle your availability for each hour.\n"
                "2. Green buttons indicate selected times.\n"
                "3. Click **Back** when you are done with this date to select other dates or to **Submit**.\n\n"
                f"**Your Timezone:** `{session.timezone}`\n\n"
                "-# Please choose as many time slots as possible to maximize your chances of not getting skipped."
            ),
            color=discord.Color.green()
        )
        await interaction.response.edit_message(content=None, embed=embed, view=view)

class HTSubmitButton(discord.ui.Button):
    def __init__(self, session: HTScheduleSession):
        super().__init__(label="Submit", style=discord.ButtonStyle.blurple, custom_id="ht_submit_dates")
        self.session = session

    async def callback(self, interaction: discord.Interaction):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        slots = []
        grouped = {}

        for date_str, hours in self.session.selections.items():
            for hour in sorted(hours):
                local_dt = datetime.datetime.fromisoformat(f"{date_str}T{hour:02d}:00:00")
                tz = pytz.timezone(self.session.timezone)
                local_dt = tz.localize(local_dt)

                utc_dt = local_dt.astimezone(pytz.UTC)
                timestamp = int(utc_dt.timestamp())
                slots.append(timestamp)

                pretty_date = local_dt.strftime("%B %-d")
                grouped.setdefault(pretty_date, []).append(f"<t:{timestamp}:t>")

        if not slots:
            return await interaction.response.send_message("You must select at least one time slot.", ephemeral=True)

        ref = db.reference(f"/HT Schedules/{self.session.thread_id}")
        existing_data = ref.get()
        is_edit = existing_data is not None and existing_data.get("slots") is not None

        ref.update({
            "player_id": self.session.user_id,
            "tester_id": self.session.tester_id,
            "player_tz": self.session.timezone,
            "slots": slots,
            "updated_at": int(time.time())
        })

        lines = ["**<:checkmark:1339153448926580818> We've recorded your availability preferences!**\n"]
        for date, times in sorted(grouped.items()):
            lines.append(f"**{date}**\n-# " + ", ".join(times))

        message = "\n".join(lines)
        await interaction.response.edit_message(content=None, embed=discord.Embed(description=message), view=None)
        
        if is_edit:
            await interaction.channel.send(f"<@{self.session.tester_id}> The player <@{self.session.user_id}> has updated their availability schedule. Please review and reschedule if necessary.", embed=discord.Embed(description=message))
        else:
            await interaction.channel.send(f"<@{self.session.tester_id}> The player <@{self.session.user_id}> has submitted their availability schedule. You can now click **Schedule Test** to pick a time.", embed=discord.Embed(description=message))
                
        ht_user_sessions.pop(self.session.user_id, None)

class HTScheduleDateSelectView(discord.ui.View):
    def __init__(self, grouped: dict, player_id: int, player_tz: str, tester_tz: str, thread_id: int):
        super().__init__(timeout=600)
        self.grouped = grouped
        self.player_id = player_id
        self.player_tz = player_tz
        self.tester_tz = tester_tz
        self.thread_id = thread_id
        for date, ts_list in grouped.items():
            self.add_item(HTScheduleDateButton(label=date, ts_list=ts_list, player_id=player_id, player_tz=player_tz, tester_tz=tester_tz, thread_id=thread_id))

class HTScheduleDateButton(discord.ui.Button):
    def __init__(self, label: str, ts_list: list[int], player_id: int, player_tz: str, tester_tz: str, thread_id: int):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.ts_list = ts_list
        self.player_id = player_id
        self.player_tz = player_tz
        self.tester_tz = tester_tz
        self.thread_id = thread_id

    async def callback(self, interaction: discord.Interaction):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        grouped = self._view.grouped
        embed = discord.Embed(
            title=f"⏰ Schedule Test: Select Time for {self.label}",
            description=(
                f"Please select a time for the test on **{self.label}**.\n\n"
                f"**Your Timezone:** `{self.tester_tz}`\n\n"
                f"The time slots are displayed in your timezone. Please pick a time that works best for you, then click **Submit** to confirm the schedule."
            ),
            color=discord.Color.green()
        )
        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=HTScheduleTimeSelectView(self.ts_list, self.player_id, self.player_tz, self.tester_tz, grouped, self.thread_id)
        )

class HTBackToDateButton(discord.ui.Button):
    def __init__(self, grouped: dict, player_id: int, player_tz: str, tester_tz: str, thread_id: int):
        super().__init__(label="Back", style=discord.ButtonStyle.primary)
        self.grouped = grouped
        self.player_id = player_id
        self.player_tz = player_tz
        self.tester_tz = tester_tz
        self.thread_id = thread_id

    async def callback(self, interaction: discord.Interaction):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        embed = discord.Embed(
            title="📅 Schedule Test: Select Date",
            description=(
                f"Please select a date to schedule the test with <@{self.player_id}>.\n\n"
                f"**Your Timezone:** `{self.tester_tz}`\n\n"
                f"The time slots are displayed in your timezone. Please pick a date/time that works best for you, then click **Submit** to confirm the schedule.\n\n"
            ),
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=HTScheduleDateSelectView(self.grouped, self.player_id, self.player_tz, self.tester_tz, self.thread_id)
        )

class HTScheduleTimeSelectView(discord.ui.View):
    def __init__(self, ts_list: list[int], player_id: int, player_tz: str, tester_tz: str, grouped: dict, thread_id: int):
        super().__init__(timeout=600)
        self.player_id = player_id
        self.player_tz = player_tz
        self.tester_tz = tester_tz
        self.grouped = grouped
        self.thread_id = thread_id

        for ts in ts_list:
            dt = datetime.datetime.fromtimestamp(ts, pytz.UTC).astimezone(pytz.timezone(tester_tz))
            label = dt.strftime("%H:%M")
            self.add_item(HTScheduleTimeButton(ts, label, player_id, player_tz, tester_tz, thread_id))

        self.add_item(HTBackToDateButton(grouped, player_id, player_tz, tester_tz, thread_id))

class HTScheduleTimeButton(discord.ui.Button):
    def __init__(self, timestamp: int, label: str, player_id: int, player_tz: str, tester_tz: str, thread_id: int):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.timestamp = timestamp
        self.player_id = player_id
        self.player_tz = player_tz
        self.tester_tz = tester_tz
        self.thread_id = thread_id

    async def callback(self, interaction: discord.Interaction):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        dt_tester = datetime.datetime.fromtimestamp(self.timestamp, pytz.UTC).astimezone(pytz.timezone(self.tester_tz))
        dt_player = datetime.datetime.fromtimestamp(self.timestamp, pytz.UTC).astimezone(pytz.timezone(self.player_tz))

        embed = discord.Embed(
            title="❓ Confirm Schedule",
            description=(
                f"Are you sure you want to schedule the test at:\n\n"
                f"- <t:{self.timestamp}>\n"
                f"- `{dt_tester.strftime('%B %d, %H:%M')} (Your Time: {self.tester_tz})`\n"
                f"- `{dt_player.strftime('%B %d, %H:%M')} (Player Time: {self.player_tz})`"
            ),
            color=discord.Color.orange()
        )

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=HTScheduleConfirmView(self.timestamp, self.player_id, self.player_tz, self.tester_tz, self.thread_id)
        )

class HTScheduleConfirmView(discord.ui.View):
    def __init__(self, timestamp: int, player_id: int, player_tz: str, tester_tz: str, thread_id: int):
        super().__init__(timeout=60)
        self.timestamp = timestamp
        self.player_id = player_id
        self.player_tz = player_tz
        self.tester_tz = tester_tz
        self.thread_id = thread_id

    @discord.ui.button(label="Confirm Schedule", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        if await _deny_if_restricted(interaction, interaction.guild.get_member(self.player_id)):
            return
        ref = db.reference(f"/HT Schedules/{self.thread_id}")
        existing_data = ref.get()
        is_edit = existing_data is not None and existing_data.get("scheduled_time") is not None

        ref.update({
            "scheduled_time": self.timestamp,
            "tester_tz": self.tester_tz
        })

        dt_player = datetime.datetime.fromtimestamp(self.timestamp, pytz.UTC).astimezone(pytz.timezone(self.player_tz))
        
        if is_edit:
            await interaction.channel.send(content=f"<@{self.player_id}>", embed=discord.Embed(
                title="📅 Test Rescheduled",
                description=f"The tester <@{interaction.user.id}> has **rescheduled** your test to:\n# <t:{self.timestamp}> (<t:{self.timestamp}:R>)\n-# `{dt_player.strftime('%B %d, %H:%M')} (Your Time: {self.player_tz})`\n\nPlease make sure to show up at this new time!",
                color=discord.Color.orange()
            ))
        else:
            await interaction.channel.send(content=f"<@{self.player_id}>", embed=discord.Embed(
                title="📅 Test Scheduled",
                description=f"<@{self.player_id}> Your test has been scheduled by <@{interaction.user.id}> at:\n# <t:{self.timestamp}> (<t:{self.timestamp}:R>)\n-# `{dt_player.strftime('%B %d, %H:%M')} (Your Time: {self.player_tz})`\n\nPlease make sure to show up at this time!",
                color=discord.Color.green()
            ))

        await interaction.response.edit_message(
            content="<:checkmark:1339153448926580818> Test time confirmed and the player has been notified in the thread!",
            embed=None,
            view=None
        )

class HTSkipOptionsView(discord.ui.View):
    def __init__(self, user_id: int, tester_id: int, gamemode: str, original_message: discord.Message):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.tester_id = tester_id
        self.gamemode = gamemode
        self.original_message = original_message

    async def process_skip(self, interaction: discord.Interaction, days: int):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        if await _deny_if_restricted(
            interaction,
            interaction.guild.get_member(self.user_id),
            interaction.guild.get_member(self.tester_id),
        ):
            return
        await interaction.response.defer(ephemeral=True)
        
        if days > 0:
            # Add to firebase
            ref_unavailable = db.reference("/HT Unavailable Testers")
            expires_at = int(time.time()) + (days * 86400)
            ref_unavailable.child(str(self.tester_id)).set({
                "expires_at": expires_at,
                "reason": f"Skipped for {days} days"
            })
            await interaction.followup.send(f"You have been marked as unavailable for {days} days. Finding a new tester...", ephemeral=True)
        else:
            await interaction.followup.send("Skipping this test only. Finding a new tester...", ephemeral=True)

        # Disable the skip button on the original message
        view = discord.ui.View.from_message(self.original_message)
        for child in view.children:
            child.disabled = True
        try:
            await self.original_message.edit(view=view)
        except Exception:
            pass

        # Find a new tester
        item = return_item(self.gamemode.lower())
        eligible_testers = []
        for role_id in item[2]:
            role = interaction.guild.get_role(role_id)
            if role:
                for member in role.members:
                    if member.id != self.user_id and not member.bot:
                        eligible_testers.append(member)
        
        eligible_testers = list(set(eligible_testers))
        
        # Filter out unavailable testers
        ref_unavailable = db.reference("/HT Unavailable Testers")
        unavailable_data = ref_unavailable.get() or {}
        current_time = int(time.time())
        
        unavailable_tester_ids = [self.tester_id] # Always exclude the current tester
        for t_id, data in list(unavailable_data.items()):
            if data.get("expires_at", 0) > current_time:
                unavailable_tester_ids.append(int(t_id))
                
        eligible_testers = [m for m in eligible_testers if m.id not in unavailable_tester_ids]
        
        if not eligible_testers:
            await interaction.channel.send(f"<:cross1:1339153202859474956> There are currently no other eligible testers available for **{self.gamemode}**. Please wait for an admin to assist.")
            return
            
        new_tester = random.choice(eligible_testers)
        
        # Add new tester to thread
        try:
            await interaction.channel.add_user(new_tester)
            await interaction.channel.add_user(interaction.client.user)  # Add bot to thread
        except Exception:
            pass
            
        # Send new intro message
        deadline = int(time.time()) + 14 * 24 * 60 * 60
        intro_embed = discord.Embed(
            title=f"HT3 Test - {self.gamemode}",
            description=(
                f"Welcome <@{self.user_id}>! You have been reassigned to {new_tester.mention} for your **{self.gamemode}** test.\n\n"
                f"**Deadline:** <t:{deadline}:R> (<t:{deadline}:F>)\n\n"
                f"**Scheduling Instructions:**\n"
                f"1. Player must click **Schedule Test** to submit their availability within 24 hours, or the tester reserves the right to skip.\n"
                f"2. Please choose as many time slots as possible to maximize your chances of not getting skipped.\n"
                f"3. Tester will then select a time from your provided schedule.\n"
                f"4. You must show up at the designated time slot, or else you can be skipped.\n\n"
                f"If either party needs to change the schedule, click **Schedule Test** again to edit your choices. "
                f"If your tester is unavailable, they can skip this test using the **Skip Test** button."
            ),
            color=discord.Color.blue()
        )
        
        await interaction.channel.send(
            content=f"<@{self.user_id}> {new_tester.mention}",
            embed=intro_embed,
            view=HTSkipView()
        )
        
        # Remove old tester after 5 seconds
        await asyncio.sleep(5)
        try:
            old_tester = interaction.guild.get_member(self.tester_id)
            if old_tester:
                await interaction.channel.remove_user(old_tester)
        except Exception:
            pass

    @discord.ui.button(label="Skip this one only", style=discord.ButtonStyle.primary)
    async def skip_one(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_skip(interaction, 0)

    @discord.ui.button(label="Skip for 3 days", style=discord.ButtonStyle.grey)
    async def skip_3_days(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_skip(interaction, 3)

    @discord.ui.button(label="Skip for 7 days", style=discord.ButtonStyle.grey)
    async def skip_7_days(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_skip(interaction, 7)

    @discord.ui.button(label="Skip for 30 days", style=discord.ButtonStyle.danger)
    async def skip_30_days(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_skip(interaction, 30)


class HTSkipView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Schedule Test", style=discord.ButtonStyle.success, custom_id="ht_schedule_test_btn")
    async def schedule_test(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        match = re.findall(r'<@!?(\d+)>', interaction.message.content)
        if len(match) < 2:
            return await interaction.response.send_message("Could not determine user and tester.", ephemeral=True)
        user_id = int(match[0])
        tester_id = int(match[1])

        if await _deny_if_restricted(interaction, interaction.guild.get_member(user_id), interaction.guild.get_member(tester_id)):
            return
        
        if interaction.user.id == user_id:
            # Player flow
            ref = db.reference(f"/HT Schedules/{interaction.channel.id}")
            data = ref.get()
            
            if data and data.get("player_tz") and data.get("slots"):
                # Load existing session
                tz_str = data["player_tz"]
                session = HTScheduleSession(user_id, tz_str, interaction.channel.id, tester_id)
                
                # Populate selections from existing slots
                tz = pytz.timezone(tz_str)
                for ts in data["slots"]:
                    dt = datetime.datetime.fromtimestamp(ts, pytz.UTC).astimezone(tz)
                    date_str = dt.date().isoformat()
                    hour = dt.hour
                    session.selections.setdefault(date_str, set()).add(hour)
                    
                ht_user_sessions[interaction.user.id] = session
                view = HTDateSelectView(session)
                embed = discord.Embed(
                    title="📅 Step 1: Select Dates",
                    description=(
                        "Please select the dates you are available to take the test.\n\n"
                        "**Instructions:**\n"
                        "1. Click on a date below.\n"
                        "2. Select **all** the hours you are available on that date.\n"
                        "3. Click **Back** to select more dates if needed.\n"
                        "4. Once you have selected all your available times across all dates, click **Submit**.\n\n"
                        f"**Your Timezone:** `{session.timezone}`\n\n"
                        "-# Please choose as many time slots as possible to maximize your chances of not getting skipped."
                    ),
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            else:
                await interaction.response.send_modal(HTTimezoneModal(is_player=True, thread_id=interaction.channel.id, user_id=user_id, tester_id=tester_id))
        elif interaction.user.id == tester_id or interaction.user.guild_permissions.administrator:
            # Tester flow
            ref = db.reference(f"/HT Schedules/{interaction.channel.id}")
            data = ref.get()
            if not data or not data.get("slots"):
                return await interaction.response.send_message("The player has not submitted their availability yet.", ephemeral=True)
            await interaction.response.send_modal(HTTimezoneModal(is_player=False, thread_id=interaction.channel.id, user_id=user_id, tester_id=tester_id))
        else:
            await interaction.response.send_message("Only the assigned player or tester can use this button.", ephemeral=True)

    @discord.ui.button(label="Skip Test", style=discord.ButtonStyle.danger, custom_id="ht_skip_test_btn")
    async def skip_test(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        match = re.findall(r'<@!?(\d+)>', interaction.message.content)
        if len(match) < 2:
            return await interaction.response.send_message("Could not determine user and tester.", ephemeral=True)
        user_id = int(match[0])
        tester_id = int(match[1])

        if await _deny_if_restricted(interaction, interaction.guild.get_member(user_id), interaction.guild.get_member(tester_id)):
            return
        
        is_admin = interaction.user.guild_permissions.administrator
        if interaction.user.id != tester_id and not is_admin:
            return await interaction.response.send_message("Only the assigned tester or an admin can skip a test.", ephemeral=True)
            
        gamemode = interaction.message.embeds[0].title.replace("HT3 Test - ", "")
        
        await interaction.response.send_message(
            "Please select a skip option for the tester:",
            view=HTSkipOptionsView(user_id, tester_id, gamemode, interaction.message),
            ephemeral=True
        )

    @discord.ui.button(label="Finalize Results", style=discord.ButtonStyle.primary, custom_id="ht_finalize_results_btn")
    async def finalize_results(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        await interaction.response.send_message(
            "To finalize the results, please use the `/ht results` command in this thread. Fill in the required fields such as the user, region, scores, role they attempted, and whether they passed or failed.",
            ephemeral=True
        )


class HTWaitlistSelection(discord.ui.Select):
    def __init__(self, placeholder, options):
        super().__init__(
            placeholder=placeholder,
            max_values=1,
            min_values=1,
            options=options,
            custom_id="htwaitlistcreation",
        )

    async def callback(self, interaction: discord.Interaction):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        await interaction.response.defer()
        selectedValue = self.values[0]

        # Check if they already have ANY waitlist role
        gamemodes = ["npot", "dpot", "smp", "sword", "crystal", "axe", "mace", "uhc"]
        for gm in gamemodes:
            gm_item = return_item(gm)
            if any(role.id == gm_item[0] for role in interaction.user.roles):
                return await interaction.followup.send(
                    f"<:cross1:1339153202859474956> You already have an active HT3 test. You can only have one active test at a time.",
                    ephemeral=True,
                )

        ref = db.reference("/HT Waitlist Cooldown")
        ticketcooldown = ref.get()
        cooldown = None
        try:
            for key, value in ticketcooldown.items():
                if (value["User ID"] == interaction.user.id) and (
                    value["Gamemode"] == selectedValue
                ):
                    ogtimestamp = value["Last Tested"]
                    if (
                        int(interaction.created_at.timestamp()) - int(ogtimestamp)
                    ) < 86400 * 30:
                        cooldown = ogtimestamp
        except Exception:
            pass

        if cooldown != None:
            return await interaction.followup.send(
                f"<:cross1:1339153202859474956> You cannot join the **{selectedValue}** waitlist since you are on a cooldown. Try again <t:{cooldown + 86400 * 30}:R>.",
                ephemeral=True,
            )

        item = return_item(selectedValue.lower())

        # Check if they have LT3 Gamemode role by checking name in role "LT3 {selectedValue}"
        if not any(role.name == f"LT3 {selectedValue}" for role in interaction.user.roles):
            return await interaction.followup.send(
                f"<:cross1:1339153202859474956> You cannot join the **{selectedValue}** HT3 waitlist since you do not have the required rank role **(LT3 {selectedValue})**.",
                ephemeral=True,
            )
            
        if LINKED_ROLE_ID not in [role.id for role in interaction.user.roles]:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="<:warn:1459986909911842846> **Account Linking Required for Testing**",
                    description=f"> To be eligible for testing, you must follow the instructions in <#1460525451368861818> to get linked. Once completed, you will automatically receive the <@&{LINKED_ROLE_ID}> role and gain access to the queue.",
                    color=discord.Colour.red(),
                ),
                ephemeral=True,
            )

        # Find eligible testers
        eligible_testers = []
        for role_id in item[2]:
            role = interaction.guild.get_role(role_id)
            if role:
                for member in role.members:
                    if member.id != interaction.user.id and not member.bot:
                        eligible_testers.append(member)
        
        # Remove duplicates
        eligible_testers = list(set(eligible_testers))
        
        # Filter out unavailable testers
        ref_unavailable = db.reference("/HT Unavailable Testers")
        unavailable_data = ref_unavailable.get() or {}
        current_time = int(time.time())
        
        unavailable_tester_ids = []
        for t_id, data in list(unavailable_data.items()):
            if data.get("expires_at", 0) > current_time:
                unavailable_tester_ids.append(int(t_id))
            else:
                try:
                    ref_unavailable.child(t_id).delete()
                except Exception:
                    pass
                    
        eligible_testers = [m for m in eligible_testers if m.id not in unavailable_tester_ids]
        
        if not eligible_testers:
            return await interaction.followup.send(
                f"<:cross1:1339153202859474956> There are currently no eligible testers available for **{selectedValue}**.",
                ephemeral=True,
            )
            
        assigned_tester = random.choice(eligible_testers)
        
        # Add waitlist role
        await interaction.user.add_roles(interaction.guild.get_role(item[0]))
        
        # Create thread
        gamemodeChannel = interaction.guild.get_channel(item[1])
        try:
            thread = await gamemodeChannel.create_thread(
                name=f"{interaction.user.name} - {selectedValue}",
                type=discord.ChannelType.private_thread,
            )
        except Exception as e:
            return await interaction.followup.send(
                f"<:cross1:1339153202859474956> Failed to create thread: {e}",
                ephemeral=True,
            )
            
        # Add users to thread
        try:
            await thread.add_user(interaction.user)
            await thread.add_user(assigned_tester)
            await thread.add_user(interaction.client.user)  # Add bot to thread
        except Exception:
            pass
            
        # Send message in thread
        deadline = int(time.time()) + 14 * 24 * 60 * 60
        intro_embed = discord.Embed(
            title=f"HT3 Test - {selectedValue}",
            description=(
                f"Welcome {interaction.user.mention}! You have been assigned to {assigned_tester.mention} for your **{selectedValue}** test.\n\n"
                f"**Deadline:** <t:{deadline}:R> (<t:{deadline}:F>)\n\n"
                f"**Scheduling Instructions:**\n"
                f"1. Player must click **Schedule Test** to submit their availability within 24 hours, or the tester reserves the right to skip.\n"
                f"2. Please choose as many time slots as possible to maximize your chances of not getting skipped.\n"
                f"3. Tester will then select a time from your provided schedule.\n"
                f"4. You must show up at the designated time slot, or else you can be skipped.\n\n"
                f"If either party needs to change the schedule, click **Schedule Test** again to edit your choices. "
                f"If your tester is unavailable, they can skip this test using the **Skip Test** button."
            ),
            color=discord.Color.blue()
        )
        
        await thread.send(
            content=f"{interaction.user.mention} {assigned_tester.mention}",
            embed=intro_embed,
            view=HTSkipView()
        )
        
        embed = discord.Embed(
            title=f"You've been added to the {selectedValue} HT3 waitlist.",
            description=f"You have been assigned to {assigned_tester.mention} for your **{selectedValue}** test! Please check {thread.mention}.",
            colour=0x008000,
        )
        if interaction.user.avatar:
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url)
        else:
            embed.set_author(name=interaction.user.name)
            
        await interaction.followup.send(embed=embed, ephemeral=True)


class HTWaitlistSelectionView(discord.ui.View):
    def __init__(self, placeholder=None, options=None, *, timeout=None):
        super().__init__(timeout=timeout)
        self.add_item(HTWaitlistSelection(placeholder, options))


class HTHistoryPaginationView(discord.ui.View):
    def __init__(self, embeds, author_id):
        super().__init__(timeout=120)
        self.embeds = embeds
        self.author_id = author_id
        self.current_page = 0
        self.update_buttons()

    def update_buttons(self):
        self.previous_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page == len(self.embeds) - 1
        self.page_info.label = f"Page {self.current_page + 1}/{len(self.embeds)}"

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("You cannot use these buttons.", ephemeral=True)
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="Page 1/1", style=discord.ButtonStyle.grey, disabled=True)
    async def page_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
             return await interaction.response.send_message("You cannot use these buttons.", ephemeral=True)
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)


class FindTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Find My Ticket", style=discord.ButtonStyle.blurple, custom_id="ht_find_ticket")
    async def find_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await _deny_if_restricted(interaction, interaction.user):
            return
        await interaction.response.defer(ephemeral=True)
        
        found_threads = []
        user_name = interaction.user.name
        
        # Search only the current channel for threads with the user's name
        try:
            # Check active threads
            for thread in interaction.channel.threads:
                if user_name.lower() in thread.name.lower():
                    found_threads.append(thread)
            
            # Check archived private threads
            async for thread in interaction.channel.archived_threads(private=True):
                if user_name.lower() in thread.name.lower():
                    found_threads.append(thread)
        except Exception as e:
            pass
        
        if not found_threads:
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> No tickets found. Please create a new waitlist request in <#1467965604257595442> or create a ticket in <#1338567467076685885> if you need assistance.",
                ephemeral=True
            )
        
        if len(found_threads) == 1:
            thread = found_threads[0]
            embed = discord.Embed(
                title="<:checkmark:1339153448926580818> Found Your Ticket!",
                description=f"Here's your HT3 test thread: {thread.mention}",
                color=discord.Color.green()
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Multiple threads found
        thread_list = "\n".join([f"• {thread.mention}" for thread in found_threads])
        embed = discord.Embed(
            title="<:checkmark:1339153448926580818> Found Your Tickets!",
            description=f"We found {len(found_threads)} thread(s) with your name:\n\n{thread_list}",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


class ApproveDenyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, custom_id="ht_approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        allowed_roles = [1304851740226748556, 1460312013535318077, 1304848576190484553]
        if not any(role.id in allowed_roles for role in interaction.user.roles):
            return await interaction.response.send_message("You do not have permission to approve this result.", ephemeral=True)

        review_msg_id = interaction.message.id
        await interaction.response.defer(ephemeral=True)
        cog = interaction.client.get_cog('ht')
        if not cog:
            return await interaction.followup.send("Bot configuration error: Cog not found.", ephemeral=True)
        
        # Use finalize_pending_results instead of publish_and_record
        result = await cog.finalize_pending_results(review_msg_id, interaction)
        if not result:
            return
        
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(content=f"{interaction.message.content}\n\n<:checkmark:1339153448926580818> Approved by {interaction.user.mention}", view=self)
        # Finalize message already sent in finalize_pending_results if successful

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, custom_id="ht_deny")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        allowed_roles = [1304851740226748556, 1460312013535318077, 1304848576190484553]
        if not any(role.id in allowed_roles for role in interaction.user.roles):
            return await interaction.response.send_message("You do not have permission to deny this result.", ephemeral=True)

        review_msg_id = interaction.message.id
        try:
            db.reference("/Pending HT Results").child(str(review_msg_id)).delete()
        except Exception:
            pass
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(content=f"{interaction.message.content}\n\n⛔ Denied by {interaction.user.mention}", view=self)
        await interaction.response.send_message("Result denied.", ephemeral=True)


class HTWaitlistCmd(commands.GroupCog, name="ht"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()
        # Note: pending results are stored in Firebase under '/Pending HT Results'
        # to survive restarts.

    @app_commands.command(
        name="results", description="Finalize a high tier waitlist result"
    )
    @app_commands.describe(
        user="Specify the user",
        region="Specify the user's region",
        scores="Specify the score",
        attempted_rank="Specify the rank role they attempted (regardless of pass or fail)",
        tester="The tester who performed the test (defaults to you)",
        remarks="Optional remarks",
    )
    @app_commands.choices(
        region=[
            app_commands.Choice(name="Asia", value="AS"),
            app_commands.Choice(name="Australia", value="AU"),
            app_commands.Choice(name="North America", value="NA"),
            # app_commands.Choice(name="South America", value="SA"),
            app_commands.Choice(name="Europe", value="EU"),
        ]
    )
    @app_commands.choices(
        pass_or_fail=[
            app_commands.Choice(name="Pass", value="Pass"),
            app_commands.Choice(name="Fail", value="Fail"),
        ]
    )
    async def tl_results(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        region: str,
        scores: str,
        attempted_rank: discord.Role,
        pass_or_fail: app_commands.Choice[str],
        tester: discord.Member = None,
        remarks: str = None,
    ) -> None:
        if await _deny_if_restricted(interaction, interaction.user, user, tester):
            return
        await interaction.response.defer()

        allowed_roles = [1304851740226748556, 1460312013535318077, 1304848576190484553]
        has_manager_permission = any(role.id in allowed_roles for role in interaction.user.roles)

        # Allow eligible HT testers (from return_item) as well, but restrict them
        # to only grant HT3 and require approval from a manager.
        gamemode_name = attempted_rank.name.split(" ")[1] if len(attempted_rank.name.split(" ")) > 1 else None
        eligible_tester_role_ids = []
        if gamemode_name:
            try:
                eligible_tester_role_ids = return_item(gamemode_name.lower())[2]
            except Exception:
                eligible_tester_role_ids = []

        has_eligible_tester_role = any(role.id in eligible_tester_role_ids for role in interaction.user.roles)

        if not (has_manager_permission or has_eligible_tester_role):
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> You do not have permission to post high tier results.",
                ephemeral=True,
            )

        tester_user = tester or interaction.user

        # Check tester linking
        if LINKED_ROLE_ID not in [role.id for role in tester_user.roles]:
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> The specified tester must have their account linked to use this command.", 
                embed=discord.Embed(
                    title="<:warn:1459986909911842846> **Account Linking Required for Testing**",
                    description=f"> To be eligible for testing, you must follow the instructions in <#1460525451368861818> to get linked. Once completed, you will automatically receive the <@&{LINKED_ROLE_ID}> role and gain access to the queue.",
                    color=discord.Colour.red(),
                ),
                ephemeral=True
            )

        # Check linking
        if LINKED_ROLE_ID not in [role.id for role in user.roles]:
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> This player is not linked. They must link their account to receive results.",
                ephemeral=True
            )

        # If tester is an eligible tester (not a manager), restrict attempted_rank to HT3 only
        if has_eligible_tester_role and not has_manager_permission:
            if "HT3" not in attempted_rank.name:
                return await interaction.followup.send(
                    "<:cross1:1339153202859474956> As an eligible tester, you may only grant HT3 roles. Please select an HT3 role **(the rank they ATTEMPTED**). If they failed their HT3 test, please still choose `@HT3 Gamemode` role but choose `Fail`.",
                    ephemeral=True,
                )

        # Get Username from DB
        username = "Unknown"
        linked_uuid = None
        async with self.bot.tllink_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SHOW TABLES")
                result = await cursor.fetchone()
                link_table = result[0] if result else "mystilinking"
                await cursor.execute(f"SELECT player_name, uuid FROM {link_table} WHERE discord_id = %s", (str(user.id),))
                result = await cursor.fetchone()
                if result:
                    username = result[0]
                    try:
                        linked_uuid = result[1]
                    except Exception:
                        linked_uuid = None
                else:
                    return await interaction.followup.send(
                        "<:cross1:1339153202859474956> Could not find linked account in database despite having the linked role.",
                        ephemeral=True
                    )
        
        gamemode = attempted_rank.name.split(" ")[1]
        removeRole = None
        for role in user.roles:
            try:
                if role.name.split(" ")[1] == gamemode:
                    removeRole = role
            except Exception:
                continue
        if removeRole != None:
            await user.remove_roles(removeRole)
            previousRank = removeRole.name.split(" ")[0]
        else:
            previousRank = "N/A"

        if not (
            ("LT" in attempted_rank.name or "HT" in attempted_rank.name)
            and "tester" not in attempted_rank.name.lower()
        ):
            return await interaction.followup.send(
                "<:warn:1459986909911842846> Double check you selected the correct role!", ephemeral=True
            )
            
        if user.id == tester_user.id:
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> You cannot test yourself!", ephemeral=True
            )
        
        attempted_rank_str = attempted_rank.name.split(" ")[0]
        
        if not (
            attempted_rank_str == "HT3"
            or attempted_rank_str == "LT2"
            or attempted_rank_str == "HT2"
            or attempted_rank_str == "LT1"
            or attempted_rank_str == "HT1"
        ):
            return await interaction.followup.send(
                "<:cross1:1339153202859474956> This command is only for High Tier results (HT3, LT2, HT2, LT1, HT1). Use `/waitlist results` for other ranks.",
                ephemeral=True
            )

        ref = db.reference("/HT Waitlist Cooldown")
        ticketcooldown = ref.get()
        try:
            for key, value in ticketcooldown.items():
                if (value["User ID"] == user.id) and (
                    value["Gamemode"] == gamemode
                ):
                    db.reference("/HT Waitlist Cooldown").child(key).delete()
                    break
        except Exception:
            pass

        try:
            await interaction.channel.remove_user(user)
        except Exception:
            pass

        override_message = None
        
        if pass_or_fail.value.lower() == "fail":
            fail_map = {
                "HT3": "LT3",
                "HT2": "LT2",
                "LT2": "HT3",
            }
            
            target_rank = fail_map.get(attempted_rank_str)
            override_message = f"<@{user.id}> - {username} - **Failed {attempted_rank_str} {gamemode} Test**\n\n> {scores} vs <@{tester_user.id}>"

            if target_rank:
                fallback_role_name = f"{target_rank} {gamemode}"
                fallback_role = discord.utils.get(interaction.guild.roles, name=fallback_role_name)
                
                if fallback_role:
                    attempted_rank = fallback_role
                    fail_note = f"Failed {attempted_rank_str} Test"
                    remarks = f"{remarks} | {fail_note}" if remarks else fail_note
                else:
                    return await interaction.followup.send(
                        f"<:cross1:1339153202859474956> Player failed {attempted_rank_str}, but I could not find the fallback role `{fallback_role_name}` in the server.",
                        ephemeral=True
                    )
            else:
                fail_note = f"Failed {attempted_rank_str} Test"
                remarks = f"{remarks} | {fail_note}" if remarks else fail_note
                attempted_rank = None 

        new_rank = attempted_rank.name.split(" ")[0] if attempted_rank else "None"

        embed = discord.Embed(title=f"{username}'s Results :trophy:")
        embed.add_field(
            name="Tester",
            value=f"{tester_user.mention}",
            inline=True,
        )
        embed.add_field(name="Region", value=f"{region}", inline=True)
        embed.add_field(name="In-game Username", value=f"[{username}](https://tierlist.mysticraft.xyz/?player={username})", inline=True)
        embed.add_field(name="Gamemode", value=f"{gamemode}", inline=True)
        embed.add_field(name="Previous Rank", value=f"{previousRank}", inline=True)
        embed.add_field(name="New Rank", value=new_rank, inline=True)
        embed.add_field(name="Scores", value=scores, inline=True)
        if remarks is not None:
            embed.add_field(name="Remarks", value=remarks, inline=True)
        embed.set_thumbnail(url=f"https://render.crafty.gg/3d/bust/{username}")

        # Prepare Payload
        payload = {
            'player_discord_username': user.name,
            'player_user_id': user.id,
            'uuid': linked_uuid,
            'is_linked': True,
            'region': region,
            'in_game_username': username,
            'score': scores,
            'timestamp': int(interaction.created_at.timestamp()),
            'old_rank': previousRank,
            'new_rank': new_rank,
            'gamemode': gamemode,
            'remarks': remarks,
            'tester_discord_username': tester_user.name,
            'tester_user_id': tester_user.id,
            'attempted_rank_id': attempted_rank.id if attempted_rank else None,
            'attempted_rank_name': attempted_rank.name if attempted_rank else None,
            'submitted_by': interaction.user.id,
            'override_msg': override_message # Pass the text message to the publisher
        }

        # If eligible tester (non-manager), send to review channel
        if has_eligible_tester_role and not has_manager_permission:
            review_channel = interaction.guild.get_channel(1467967731625103505)
            # We still send the EMBED to the review channel so managers see the details clearly
            view = ApproveDenyView()
            thread_url = getattr(interaction.channel, "jump_url", f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}")
            view.add_item(discord.ui.Button(label="Go to Thread", style=discord.ButtonStyle.link, url=thread_url))
            review_msg = await review_channel.send(user.mention, embed=embed, view=view)
            
            try:
                db.reference('/Pending HT Results').child(str(review_msg.id)).set(payload)
            except Exception:
                pass
            await interaction.followup.send(f"<:checkmark:1339153448926580818> Result submitted for review: [Review Message]({review_msg.jump_url})", ephemeral=True)
            return

        # Manager flow: Execute immediately
        results = await self.publish_and_record(payload, interaction)
        if not results:
            return
        
        await interaction.followup.send(f"<:checkmark:1339153448926580818> [High Results sent]({results.jump_url})")

    async def finalize_pending_results(self, message_id, interaction: discord.Interaction):
        """
        Fetches pending result from firebase using the review message ID,
        then publishes it using publish_and_record, and finally deletes the pending entry.
        """
        try:
            ref = db.reference(f"/Pending HT Results/{message_id}")
            payload = ref.get()
            
            if not payload:
                return await interaction.followup.send("Pending result data not found or already processed.", ephemeral=True)

            player_id = int(payload.get("player_user_id")) if payload.get("player_user_id") else None
            tester_id = int(payload.get("tester_user_id")) if payload.get("tester_user_id") else None
            if await _deny_if_restricted(interaction, interaction.guild.get_member(player_id) if player_id else None, interaction.guild.get_member(tester_id) if tester_id else None):
                return
            
            result = await self.publish_and_record(payload, interaction)
            if result:
                ref.delete()
            return result
            
        except Exception as e:
            await interaction.followup.send(f"Error finalizing results: {e}", ephemeral=True)
            return None

    async def publish_and_record(self, payload: dict, interaction: discord.Interaction):
        """
        Shared function to publish a high-tier result and record it.
        Checks for `override_msg` in payload to send text instead of embed.
        """
        guild = interaction.guild
        player_id = int(payload.get('player_user_id'))
        tester_id = int(payload.get('tester_user_id'))
        attempted_rank_id = int(payload.get('attempted_rank_id')) if payload.get('attempted_rank_id') else None
        override_msg = payload.get('override_msg')

        # Fetch member objects
        player_member = guild.get_member(player_id)
        if player_member is None:
            try:
                player_member = await guild.fetch_member(player_id)
            except Exception:
                player_member = None

        tester_member = guild.get_member(tester_id)
        if tester_member is None:
            try:
                tester_member = await guild.fetch_member(tester_id)
            except Exception:
                tester_member = None

        if _has_restricted_role(player_member) or _has_restricted_role(tester_member):
            await interaction.followup.send("<:cross1:1339153202859474956> Restricted users cannot be processed by HT results commands.", ephemeral=True)
            return None

        # Try to add role to player (Even if they failed, they get the fallback role defined in payload)
        if player_member and attempted_rank_id:
            try:
                await player_member.add_roles(guild.get_role(attempted_rank_id))
            except Exception:
                pass

        # Post to high results channel
        high_channel = guild.get_channel(1338411690902945832)
        
        results_msg = None
        if override_msg:
            # === SEND FAIL TEXT MESSAGE ===
            results_msg = await high_channel.send(override_msg)
        else:
            # === SEND SUCCESS EMBED ===
            username = payload.get('in_game_username') or payload.get('player_discord_username') or 'Unknown'
            embed = discord.Embed(title=f"{username}'s Results :trophy:")
            embed.add_field(name="Tester", value=f"<@{tester_id}>", inline=True)
            embed.add_field(name="Region", value=f"{payload.get('region')}", inline=True)
            embed.add_field(name="In-game Username", value=f"[{username}](https://tierlist.mysticraft.xyz/?player={username})", inline=True)
            embed.add_field(name="Gamemode", value=f"{payload.get('gamemode')}", inline=True)
            embed.add_field(name="Previous Rank", value=f"{payload.get('old_rank')}", inline=True)
            embed.add_field(name="New Rank", value=f"{payload.get('new_rank')}", inline=True)
            embed.add_field(name="Scores", value=payload.get('score'), inline=True)
            if payload.get('remarks'):
                embed.add_field(name="Remarks", value=payload.get('remarks'), inline=True)
            embed.set_thumbnail(url=f"https://render.crafty.gg/3d/bust/{username}")
            
            results_msg = await high_channel.send(f"<@{player_id}>", embed=embed)
            try:
                await results_msg.add_reaction("🔥")
            except Exception:
                pass

        # Insert into DB
        async with self.bot.tlresults_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SHOW TABLES LIKE 'tlresults'")
                res = await cursor.fetchone()
                if not res:
                    await cursor.execute("""
                        CREATE TABLE tlresults (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            player_discord_username VARCHAR(255),
                            player_user_id BIGINT,
                            uuid VARCHAR(36),
                            is_linked BOOLEAN NOT NULL DEFAULT FALSE,
                            region VARCHAR(10),
                            in_game_username VARCHAR(255),
                            score VARCHAR(255),
                            timestamp BIGINT,
                            old_rank VARCHAR(50),
                            new_rank VARCHAR(50),
                            gamemode VARCHAR(50),
                            remarks TEXT,
                            tester_discord_username VARCHAR(255),
                            tester_user_id BIGINT
                        )
                    """)
                await cursor.execute("""
                    INSERT INTO tlresults (player_discord_username, player_user_id, uuid, is_linked, region, in_game_username, score, timestamp, old_rank, new_rank, gamemode, remarks, tester_discord_username, tester_user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (payload.get('player_discord_username'), payload.get('player_user_id'), payload.get('uuid'), payload.get('is_linked'), payload.get('region'), payload.get('in_game_username'), payload.get('score'), payload.get('timestamp'), payload.get('old_rank'), payload.get('new_rank'), payload.get('gamemode'), payload.get('remarks'), payload.get('tester_discord_username'), payload.get('tester_user_id')))
                await conn.commit()

        # Update firebase stats
        ref_stats = db.reference("/Tierlist Tester Stats")
        tester_id = payload.get('tester_user_id')
        existing = ref_stats.child(str(tester_id)).get() or {}
        old_rep = existing.get("count", 0) + 2 * existing.get("high_count", 0)
        old_tier = get_tier_index(old_rep)
        high_timestamps = existing.get("high_timestamps", [])
        high_timestamps.append(payload.get('timestamp'))
        high_count = len(high_timestamps)
        ref_stats.child(str(tester_id)).update({"high_count": high_count, "high_timestamps": high_timestamps})

        # Check for rank up
        new_existing = ref_stats.child(str(tester_id)).get()
        new_rep = new_existing.get("count", 0) + 2 * new_existing.get("high_count", 0)
        new_tier = get_tier_index(new_rep)
        if new_tier > old_tier:
            old_role_id = TIER_ROLES.get(old_tier)
            attempted_rank_id = TIER_ROLES[new_tier]
            try:
                if tester_member:
                    if old_role_id:
                        await tester_member.remove_roles(guild.get_role(old_role_id))
                    await tester_member.add_roles(guild.get_role(attempted_rank_id))
            except Exception:
                pass
            channel = guild.get_channel(1467403596780929055)
            embed_desc = f"<@{tester_id}> has reached **{TIER_THRESHOLDS[new_tier]}** reps and ranked up to `{TIER_NAMES[new_tier]}`!"
            if TIER_TO_MAIN[new_tier] > TIER_TO_MAIN.get(old_tier, -1):
                embed_desc += f"\nThey also earned the <@&{attempted_rank_id}> role!"
            rank_embed = discord.Embed(description=embed_desc, color=discord.Color.from_rgb(*tier_colors[new_tier]))
            await channel.send(content=f"<@{tester_id}>", embed=rank_embed)

        # push cooldown
        ref = db.reference("/HT Waitlist Cooldown")
        data = {
            guild.name: {
                "User ID": player_id,
                "Last Tested": payload.get('timestamp'),
                "Gamemode": payload.get('gamemode'),
            }
        }
        for key, value in data.items():
            ref.push().set(value)

        # remove waitlist role
        try:
            item = return_item(payload.get('gamemode').lower())
            if player_member:
                try:
                    await player_member.remove_roles(guild.get_role(item[0]))
                except Exception:
                    pass
        except Exception:
            pass

        return results_msg


    @app_commands.command(
        name="dropdown", description="Creates a waitlist panel with dropdown menu"
    )
    @app_commands.describe(
        title="Makes the title of the embed",
        description="Makes the description of the embed",
        color="Sets the color of the embed",
        thumbnail="Please provide a URL for the thumbnail of the embed (upper-right hand corner image)",
        image="Please provide a URL for the image of the embed (appears at the bottom of the embed)",
        footer="Sets the footer of the embed that appears at the bottom of the embed as small texts",
        dropdown_placeholder="Sets the placeholder of the dropdown menu",
        dropdown1_title="Format: Emoji | Title | Shortform",
        dropdown2_title="Format: Emoji | Title | Shortform",
        dropdown3_title="Format: Emoji | Title | Shortform",
        dropdown4_title="Format: Emoji | Title | Shortform",
        dropdown5_title="Format: Emoji | Title | Shortform",
        dropdown6_title="Format: Emoji | Title | Shortform",
        dropdown7_title="Format: Emoji | Title | Shortform",
        dropdown8_title="Format: Emoji | Title | Shortform",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def ht_dropdown(
        self,
        interaction: discord.Interaction,
        title: str = None,
        description: str = None,
        color: str = None,
        thumbnail: str = None,
        image: str = None,
        footer: str = None,
        dropdown_placeholder: str = "Select a Category",
        dropdown1_title: str = None,
        dropdown2_title: str = None,
        dropdown3_title: str = None,
        dropdown4_title: str = None,
        dropdown5_title: str = None,
        dropdown6_title: str = None,
        dropdown7_title: str = None,
        dropdown8_title: str = None,
    ) -> None:
        if await _deny_if_restricted(interaction, interaction.user):
            return
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
            [
                dropdown1_title.split("|")[0].strip(),
                dropdown1_title.split("|")[1].strip(),
                dropdown1_title.split("|")[2].strip(),
            ],
            [
                dropdown2_title.split("|")[0].strip(),
                dropdown2_title.split("|")[1].strip(),
                dropdown2_title.split("|")[2].strip(),
            ],
            [
                dropdown3_title.split("|")[0].strip(),
                dropdown3_title.split("|")[1].strip(),
                dropdown3_title.split("|")[2].strip(),
            ],
            [
                dropdown4_title.split("|")[0].strip(),
                dropdown4_title.split("|")[1].strip(),
                dropdown4_title.split("|")[2].strip(),
            ],
            [
                dropdown5_title.split("|")[0].strip(),
                dropdown5_title.split("|")[1].strip(),
                dropdown5_title.split("|")[2].strip(),
            ],
            [
                dropdown6_title.split("|")[0].strip(),
                dropdown6_title.split("|")[1].strip(),
                dropdown6_title.split("|")[2].strip(),
            ],
            [
                dropdown7_title.split("|")[0].strip(),
                dropdown7_title.split("|")[1].strip(),
                dropdown7_title.split("|")[2].strip(),
            ],
            [
                dropdown8_title.split("|")[0].strip(),
                dropdown8_title.split("|")[1].strip(),
                dropdown8_title.split("|")[2].strip(),
            ],
        ]

        for item in list:
            if item[0] is not None and item[1] is not None:  # Emoji + Title
                emote = emoji.emojize(item[0].strip())
                title = item[1].strip()
                options.append(
                    discord.SelectOption(
                        label=title,
                        value=item[2],
                        emoji=emote,
                        description=f"{title} HT3 Queue",
                    )
                )
            else:  # Title missing
                embed = discord.Embed(
                    title="Format incorrect",
                    description="Please double check!",
                    color=0xFF0000,
                )
                return await interaction.response.send_message(
                    embed=embed, ephemeral=True
                )

        await interaction.channel.send(
            embed=embed, view=HTWaitlistSelectionView(dropdown_placeholder, options)
        )
        embed = discord.Embed(
            title="<:checkmark:1339153448926580818> Custom Waitlist Panel Sent",
            description="All members who have access to this channel can submit a waitlist request by selecting the dropdown menu below the panel!",
            color=0x00FF00,
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.content == "mc!ht3test":
            if _has_restricted_role(message.author):
                return
            intro_embed = discord.Embed(
                title = "Welcome to the HT3 Testing Channel!",
                description = (
                    "Find your thread created for you to submit your availability and coordinate the test with the tester. If the assigned tester does not respond in 5 days, please ping a Manager/Owner in your thread."
                ),
                color=discord.Color.blue()
            ).set_image(url="https://media.discordapp.net/attachments/1079100558507520001/1496308462437535884/instructions.png?ex=69e96959&is=69e817d9&hm=09fc1f6ae47a84e7c5fbc355b3654c713b59a360f123282a158e0d52170f0315&=")
            await message.channel.send(embed=intro_embed, view=FindTicketView())
            await message.delete()


async def setup(bot):
    await bot.add_cog(HTWaitlistCmd(bot))