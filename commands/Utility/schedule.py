import discord, time
from discord import app_commands
from discord.ext import commands
import datetime
import pytz
from firebase_admin import db

# Session cache for UI state
user_sessions = {}

def save_user_slots_to_db(user_id: int, slots: list, timezone: str):
    """Writes the final selected slots to Firebase Realtime Database."""
    ref = db.reference(f"Schedules/{user_id}")
    ref.set({
        "slots": slots,
        "timezone": timezone,
        "updated_at": int(time.time())
    })

class ScheduleSession:
    def __init__(self, user_id, tz):
        self.user_id = user_id
        self.timezone = tz
        self.selections = {}  # date_str -> set(hours)

class ConfirmView(discord.ui.View):
    def __init__(self, session: ScheduleSession):
        super().__init__(timeout=120)
        self.session = session

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = DateSelectView(self.session)
        await interaction.response.edit_message(content="Select a date you're available for an interview:", view=view)

    @discord.ui.button(label="No, let me choose another timezone", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_sessions.pop(self.session.user_id, None)
        await interaction.response.edit_message(content="Scheduling cancelled. You can use </schedule:1391942820440572046> again!", view=None)

class SubmitButton(discord.ui.Button):
    def __init__(self, session: ScheduleSession):
        super().__init__(label="Submit", style=discord.ButtonStyle.blurple, custom_id="submit_dates")
        self.session = session

    async def callback(self, interaction: discord.Interaction):
        slots = []
        grouped = {}

        for date_str, hours in self.session.selections.items():
            for hour in sorted(hours):
                # Local datetime
                local_dt = datetime.datetime.fromisoformat(f"{date_str}T{hour:02d}:00:00")
                tz = pytz.timezone(self.session.timezone)
                local_dt = tz.localize(local_dt)

                # UTC timestamp
                utc_dt = local_dt.astimezone(pytz.UTC)
                timestamp = int(utc_dt.timestamp())
                slots.append(timestamp)

                # Group for display
                pretty_date = local_dt.strftime("%B %-d")  # e.g., July 8
                grouped.setdefault(pretty_date, []).append(f"<t:{timestamp}:t>")  # Show only time

        # Build grouped string
        lines = ["**✅ We've recorded your availability preferences! You will receive a DM confirming your interview time shortly.**\n"]
        for date, times in sorted(grouped.items()):
            lines.append(f"**{date}**\n-# " + ", ".join(times))

        message = "\n".join(lines)
        save_user_slots_to_db(self.session.user_id, slots, self.session.timezone)
        await interaction.response.edit_message(content=message, view=None)
        await interaction.guild.get_channel(1391959304822718464).send(f"{interaction.user.mention} just submitted a new availabilty preference. Use </view_schedule:1391952451820584973> to view it.")
        user_sessions.pop(self.session.user_id, None)


class DateSelectView(discord.ui.View):
    def __init__(self, session: ScheduleSession):
        super().__init__(timeout=600)
        self.session = session
        now = datetime.datetime.now(pytz.timezone(session.timezone))
        self.dates = [(now + datetime.timedelta(days=i)).date() for i in range(7)]
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        for date in self.dates:
            date_str = date.isoformat()
            label = date.strftime("%b %d")
            style = (discord.ButtonStyle.green
                     if date_str in self.session.selections and self.session.selections[date_str]
                     else discord.ButtonStyle.secondary)
            self.add_item(DateButton(label, date_str, style))
        self.add_item(SubmitButton(self.session))

class DateButton(discord.ui.Button):
    def __init__(self, label, date_str, style):
        super().__init__(label=label, style=style, custom_id=f"date:{date_str}")
        self.date_str = date_str

    async def callback(self, interaction: discord.Interaction):
        session = user_sessions.get(interaction.user.id)
        session.selections.setdefault(self.date_str, set())
        view = TimeSelectView(session, self.date_str)
        await interaction.response.edit_message(content=f"Select your available hours on **{datetime.datetime.fromisoformat(self.date_str).strftime('%B %d')}** in your timezone.\n-# The interview will only take less than 30 minutes.", view=view)

class BackButton(discord.ui.Button):
    def __init__(self, session: ScheduleSession, date_str: str):
        super().__init__(label="Back", style=discord.ButtonStyle.blurple, custom_id="back_to_dates")
        self.session = session
        self.date_str = date_str

    async def callback(self, interaction: discord.Interaction):
        view = DateSelectView(self.session)
        await interaction.response.edit_message(content=f"Select a date you're available for an interview:", view=view)

class TimeSelectView(discord.ui.View):
    def __init__(self, session: ScheduleSession, date_str: str, page: int = 0):
        super().__init__(timeout=600)
        self.session = session
        self.date_str = date_str
        now = datetime.datetime.now(pytz.timezone(session.timezone))
        if now.date().isoformat() == date_str:
            start = now.hour + 1
        else:
            start = 0
        self.hours = list(range(start, 24))
        self.page = page
        self.build_view()

    def build_view(self):
        self.clear_items()
        per_page = 25
        start_idx = self.page * per_page
        end_idx = start_idx + per_page
        for hour in self.hours[start_idx:end_idx]:
            label = f"{hour:02d}:00"
            selected = hour in self.session.selections.get(self.date_str, set())
            style = discord.ButtonStyle.green if selected else discord.ButtonStyle.secondary
            self.add_item(TimeButton(label, self.date_str, hour, style))
        if start_idx > 0:
            self.add_item(discord.ui.Button(label="Prev", style=discord.ButtonStyle.grey, custom_id="time_prev"))
        if end_idx < len(self.hours):
            self.add_item(discord.ui.Button(label="Next", style=discord.ButtonStyle.grey, custom_id="time_next"))
        self.add_item(BackButton(self.session, self.date_str))

class TimeButton(discord.ui.Button):
    def __init__(self, label, date_str, hour, style):
        super().__init__(label=label, style=style, custom_id=f"time:{date_str}:{hour}")
        self.date_str = date_str
        self.hour = hour

    async def callback(self, interaction: discord.Interaction):
        session = user_sessions.get(interaction.user.id)
        hours = session.selections.setdefault(self.date_str, set())
        if self.hour in hours:
            hours.remove(self.hour)
        else:
            hours.add(self.hour)
        view = TimeSelectView(session, self.date_str)
        await interaction.response.edit_message(content=f"Select your available hours on **{datetime.datetime.fromisoformat(self.date_str).strftime('%B %d')}** in your timezone.\n-# The interview will only take less than 30 minutes.", view=view)

# ----------------- INTERVIEWER ----------------- 

class ScheduleDateSelectView(discord.ui.View):
    def __init__(self, grouped: dict, applicant: discord.Member, applicant_tz: str, interviewer_tz: str):
        super().__init__(timeout=600)
        self.grouped = grouped
        self.applicant = applicant
        self.applicant_tz = applicant_tz
        self.interviewer_tz = interviewer_tz
        for date, ts_list in grouped.items():
            self.add_item(ScheduleDateButton(label=date, ts_list=ts_list, applicant=applicant, applicant_tz=applicant_tz, interviewer_tz=interviewer_tz))

class ScheduleDateButton(discord.ui.Button):
    def __init__(self, label: str, ts_list: list[int], applicant: discord.Member, applicant_tz: str, interviewer_tz: str):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.ts_list = ts_list
        self.applicant = applicant
        self.applicant_tz = applicant_tz
        self.interviewer_tz = interviewer_tz

    async def callback(self, interaction: discord.Interaction):
        # Pass grouped dict to the time selection view for Back button usage
        grouped = self._view.grouped
        await interaction.response.edit_message(
            content=f"Select a time for **{self.label}**:",
            view=ScheduleTimeSelectView(self.ts_list, self.applicant, self.applicant_tz, self.interviewer_tz, grouped=grouped)
        )

class BackToDateButton(discord.ui.Button):
    def __init__(self, grouped: dict, applicant: discord.Member, applicant_tz: str, interviewer_tz: str):
        super().__init__(label="⬅️ Back to Dates", style=discord.ButtonStyle.grey)
        self.grouped = grouped
        self.applicant = applicant
        self.applicant_tz = applicant_tz
        self.interviewer_tz = interviewer_tz

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content="Select a date:",
            view=ScheduleDateSelectView(self.grouped, self.applicant, self.applicant_tz, self.interviewer_tz)
        )

class ScheduleTimeSelectView(discord.ui.View):
    def __init__(self, ts_list: list[int], applicant: discord.Member, applicant_tz: str, interviewer_tz: str, grouped: dict):
        super().__init__(timeout=600)
        self.applicant = applicant
        self.applicant_tz = applicant_tz
        self.interviewer_tz = interviewer_tz
        self.grouped = grouped

        for ts in ts_list:
            dt = datetime.datetime.fromtimestamp(ts, pytz.UTC).astimezone(pytz.timezone(interviewer_tz))
            label = dt.strftime("%H:%M")  # 24-hour format
            self.add_item(ScheduleTimeButton(ts, label, applicant, applicant_tz, interviewer_tz))

        self.add_item(BackToDateButton(grouped, applicant, applicant_tz, interviewer_tz))

class ScheduleTimeButton(discord.ui.Button):
    def __init__(self, timestamp: int, label: str, applicant: discord.Member, applicant_tz: str, interviewer_tz: str):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.timestamp = timestamp
        self.applicant = applicant
        self.applicant_tz = applicant_tz
        self.interviewer_tz = interviewer_tz

    async def callback(self, interaction: discord.Interaction):
        dt_interviewer = datetime.datetime.fromtimestamp(self.timestamp, pytz.UTC).astimezone(pytz.timezone(self.interviewer_tz))
        dt_applicant = datetime.datetime.fromtimestamp(self.timestamp, pytz.UTC).astimezone(pytz.timezone(self.applicant_tz))

        msg = (
            f"🕒 Are you sure you want to schedule the interview at:\n\n"
            f"- <t:{self.timestamp}>\n"
            f"- `{dt_interviewer.strftime('%B %d, %H:%M')} (Your Time: {self.interviewer_tz})`\n"
            f"- `{dt_applicant.strftime('%B %d, %H:%M')} (Applicant Time: {self.applicant_tz})`"
        )

        await interaction.response.edit_message(
            content=msg,
            view=ScheduleConfirmView(self.timestamp, self.applicant, self.applicant_tz, self.interviewer_tz)
        )

class ScheduleConfirmView(discord.ui.View):
    def __init__(self, timestamp: int, applicant: discord.Member, applicant_tz: str, interviewer_tz: str):
        super().__init__(timeout=60)
        self.timestamp = timestamp
        self.applicant = applicant
        self.applicant_tz = applicant_tz
        self.interviewer_tz = interviewer_tz

    @discord.ui.button(label="Confirm & Send DM", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        dt_applicant = datetime.datetime.fromtimestamp(self.timestamp, pytz.UTC).astimezone(pytz.timezone(self.applicant_tz))

        try:
            await self.applicant.send(
                f"📅 Your MystiCraft staff interview has been scheduled at the following time!\n"
                f"# <t:{self.timestamp}>\n"
                f"-# `{dt_applicant.strftime('%B %d, %H:%M')} (Your Time: {self.applicant_tz})`\n"
                "\nPlease kindly join <#1391101179165020280> **10 minutes** before your interview starts."
            )
        except discord.Forbidden:
            await interaction.followup.send("⚠️ Could not DM the applicant.", ephemeral=True)
            
        await interaction.guild.get_channel(1391959304822718464).send(f"{self.applicant.mention}'s interview has been scheduled at <t:{self.timestamp}> by {interaction.user.mention}.")

        await interaction.response.edit_message(
            content="✅ Interview time confirmed and the applicant has been notified!",
            view=None
        )


timezones = ['America/Araguaina', 'America/Argentina/Buenos_Aires', 'America/Argentina/Catamarca', 'America/Argentina/Cordoba', 'America/Argentina/Jujuy', 'America/Argentina/La_Rioja', 'America/Argentina/Mendoza', 'America/Argentina/Rio_Gallegos', 'America/Argentina/Salta', 'America/Argentina/San_Juan', 'America/Argentina/San_Luis', 'America/Argentina/Tucuman', 'America/Argentina/Ushuaia', 'America/Asuncion', 'America/Bahia', 'America/Belem', 'America/Boa_Vista', 'America/Bogota', 'America/Campo_Grande', 'America/Caracas', 'America/Cayenne', 'America/Cuiaba', 'America/Eirunepe', 'America/Fortaleza', 'America/Guayaquil', 'America/Guyana', 'America/La_Paz', 'America/Lima', 'America/Maceio', 'America/Manaus', 'America/Montevideo', 'America/Noronha', 'America/Paramaribo', 'America/Porto_Velho', 'America/Punta_Arenas', 'America/Recife', 'America/Rio_Branco', 'America/Santarem', 'America/Santiago', 'America/Sao_Paulo', 'Antarctica/Palmer', 'Atlantic/South_Georgia', 'Atlantic/Stanley', 'Pacific/Easter', 'Pacific/Galapagos', 'America/Adak', 'America/Anchorage', 'America/Bahia_Banderas', 'America/Barbados', 'America/Belize', 'America/Boise', 'America/Cambridge_Bay', 'America/Cancun', 'America/Chicago', 'America/Chihuahua', 'America/Ciudad_Juarez', 'America/Costa_Rica', 'America/Dawson', 'America/Dawson_Creek', 'America/Denver', 'America/Detroit', 'America/Edmonton', 'America/El_Salvador', 'America/Fort_Nelson', 'America/Glace_Bay', 'America/Goose_Bay', 'America/Grand_Turk', 'America/Guatemala', 'America/Halifax', 'America/Havana', 'America/Hermosillo', 'America/Indiana/Indianapolis', 'America/Indiana/Knox', 'America/Indiana/Marengo', 'America/Indiana/Petersburg', 'America/Indiana/Tell_City', 'America/Indiana/Vevay', 'America/Indiana/Vincennes', 'America/Indiana/Winamac', 'America/Inuvik', 'America/Iqaluit', 'America/Jamaica', 'America/Juneau', 'America/Kentucky/Louisville', 'America/Kentucky/Monticello', 'America/Los_Angeles', 'America/Managua', 'America/Martinique', 'America/Matamoros', 'America/Mazatlan', 'America/Menominee', 'America/Merida', 'America/Metlakatla', 'America/Mexico_City', 'America/Miquelon', 'America/Moncton', 'America/Monterrey', 'America/New_York', 'America/Nome', 'America/North_Dakota/Beulah', 'America/North_Dakota/Center', 'America/North_Dakota/New_Salem', 'America/Ojinaga', 'America/Panama', 'America/Phoenix', 'America/Port-au-Prince', 'America/Puerto_Rico', 'America/Rankin_Inlet', 'America/Regina', 'America/Resolute', 'America/Santo_Domingo', 'America/Sitka', 'America/St_Johns', 'America/Swift_Current', 'America/Tegucigalpa', 'America/Tijuana', 'America/Toronto', 'America/Vancouver', 'America/Whitehorse', 'America/Winnipeg', 'America/Yakutat', 'Atlantic/Bermuda', 'Pacific/Honolulu', 'Africa/Ceuta', 'America/Danmarkshavn', 'America/Nuuk', 'America/Scoresbysund', 'Scoresbysund/Ittoqqortoormiit', 'America/Thule', 'Thule/Pituffik', 'Asia/Anadyr', 'Asia/Barnaul', 'Asia/Chita', 'Asia/Irkutsk', 'Asia/Kamchatka', 'Asia/Khandyga', 'Asia/Krasnoyarsk', 'Asia/Magadan', 'Asia/Novokuznetsk', 'Asia/Novosibirsk', 'Asia/Omsk', 'Asia/Sakhalin', 'Asia/Srednekolymsk', 'Asia/Tomsk', 'Asia/Ust-Nera', 'Asia/Vladivostok', 'Asia/Yakutsk', 'Asia/Yekaterinburg', 'Atlantic/Azores', 'Atlantic/Canary', 'Atlantic/Faroe', 'Atlantic/Madeira', 'Europe/Andorra', 'Europe/Astrakhan', 'Europe/Athens', 'Europe/Belgrade', 'Europe/Berlin', 'Europe/Brussels', 'Europe/Bucharest', 'Europe/Budapest', 'Europe/Chisinau', 'Europe/Dublin', 'Europe/Gibraltar', 'Europe/Helsinki', 'Europe/Istanbul', 'Europe/Kaliningrad', 'Europe/Kirov', 'Europe/Kyiv', 'Europe/Lisbon', 'Europe/London', 'Europe/Madrid', 'Europe/Malta', 'Europe/Minsk', 'Europe/Moscow', 'Europe/Paris', 'Europe/Prague', 'Europe/Riga', 'Europe/Rome', 'Europe/Samara', 'Europe/Saratov', 'Europe/Simferopol', 'Europe/Sofia', 'Europe/Tallinn', 'Europe/Tirane', 'Europe/Ulyanovsk', 'Europe/Vienna', 'Europe/Vilnius', 'Europe/Volgograd', 'Europe/Warsaw', 'Europe/Zurich', 'Antarctica/Macquarie', 'Australia/Adelaide', 'Australia/Brisbane', 'Australia/Broken_Hill', 'Australia/Darwin', 'Australia/Eucla', 'Australia/Hobart', 'Australia/Lindeman', 'Australia/Lord_Howe', 'Australia/Melbourne', 'Australia/Perth', 'Australia/Sydney', 'Pacific/Apia', 'Pacific/Auckland', 'Pacific/Bougainville', 'Pacific/Chatham', 'Pacific/Efate', 'Pacific/Fakaofo', 'Pacific/Fiji', 'Pacific/Gambier', 'Pacific/Guadalcanal', 'Pacific/Guam', 'Pacific/Kanton', 'Pacific/Kiritimati', 'Pacific/Kosrae', 'Pacific/Kwajalein', 'Pacific/Marquesas', 'Pacific/Nauru', 'Pacific/Niue', 'Pacific/Norfolk', 'Pacific/Noumea', 'Pacific/Pago_Pago', 'Pacific/Palau', 'Pacific/Pitcairn', 'Pacific/Port_Moresby', 'Pacific/Rarotonga', 'Pacific/Tahiti', 'Pacific/Tarawa', 'Pacific/Tongatapu', 'Asia/Almaty', 'Asia/Amman', 'Asia/Aqtau', 'Mangghystaū/Mankistau', 'Asia/Aqtobe', 'Aqtöbe/Aktobe', 'Asia/Ashgabat', 'Asia/Atyrau', "Atyraū/Atirau/Gur'yev", 'Asia/Baghdad', 'Asia/Baku', 'Asia/Bangkok', 'Asia/Beirut', 'Asia/Bishkek', 'Asia/Choibalsan', 'Asia/Colombo', 'Asia/Damascus', 'Asia/Dhaka', 'Asia/Dili', 'Asia/Dubai', 'Asia/Dushanbe', 'Asia/Famagusta', 'Asia/Gaza', 'Asia/Hebron', 'Asia/Ho_Chi_Minh', 'Asia/Hong_Kong', 'Asia/Hovd', 'Asia/Jakarta', 'Asia/Jayapura', 'New Guinea (West Papua / Irian Jaya), Malukus/Moluccas', 'Asia/Jerusalem', 'Asia/Kabul', 'Asia/Karachi', 'Asia/Kathmandu', 'Asia/Kolkata', 'Asia/Kuching', 'Asia/Macau', 'Asia/Makassar', 'Asia/Manila', 'Asia/Nicosia', 'Asia/Oral', 'Asia/Pontianak', 'Asia/Pyongyang', 'Asia/Qatar', 'Asia/Qostanay', 'Qostanay/Kostanay/Kustanay', 'Asia/Qyzylorda', 'Qyzylorda/Kyzylorda/Kzyl-Orda', 'Asia/Riyadh', 'Asia/Samarkand', 'Asia/Seoul', 'Asia/Shanghai', 'Asia/Singapore', 'Asia/Taipei', 'Asia/Tashkent', 'Asia/Tbilisi', 'Asia/Tehran', 'Asia/Thimphu', 'Asia/Tokyo', 'Asia/Ulaanbaatar', 'Asia/Urumqi', 'Asia/Yangon', 'Asia/Yerevan', 'Indian/Chagos', 'Indian/Maldives', 'Antarctica/Casey', 'Antarctica/Davis', 'Antarctica/Mawson', 'Antarctica/Rothera', 'Antarctica/Troll', 'Antarctica/Vostok', 'Africa/Abidjan', 'Africa/Algiers', 'Africa/Bissau', 'Africa/Cairo', 'Africa/Casablanca', 'Africa/El_Aaiun', 'Africa/Johannesburg', 'Africa/Juba', 'Africa/Khartoum', 'Africa/Lagos', 'Africa/Maputo', 'Africa/Monrovia', 'Africa/Nairobi', 'Africa/Ndjamena', 'Africa/Sao_Tome', 'Africa/Tripoli', 'Africa/Tunis', 'Africa/Windhoek', 'Atlantic/Cape_Verde', 'Indian/Mauritius']

async def timezone_autocomplete(
    interaction: discord.Interaction,
    current: str,
):
    if current == "":
        return [
            app_commands.Choice(name=timezones[x], value=timezones[x])
            for x in range(25)
        ]
    else:
        list = []
        for tz in timezones:
            if current.lower() in tz.lower():
                list.append(tz)
        list = list[:25]
        return [app_commands.Choice(name=x, value=x) for x in list]
    
class ScheduleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="schedule", description="Schedule your availability via buttons.")
    @app_commands.describe(timezone="Your timezone (choose from autocomplete)")
    @app_commands.autocomplete(timezone=timezone_autocomplete)
    async def schedule(self, interaction: discord.Interaction, timezone: str):
        if interaction.guild.id != 1391091143059701810:
            return await interaction.response.send_message("⛔ This command is only usable in the **MystiCraft Interviews** server.", ephemeral=True)
        session = ScheduleSession(interaction.user.id, timezone)
        user_sessions[interaction.user.id] = session
        now = datetime.datetime.now(pytz.timezone(timezone))
        content = f"Confirm if your current date/time is **{now.strftime('%B %d %H:%M')}**."
        view = ConfirmView(session)
        await interaction.response.send_message(content, view=view, ephemeral=True)

    @app_commands.command(name="view_schedule", description="View an applicant's schedule preferences")
    @app_commands.describe(
        applicant="The Discord user who submitted their availability",
        timezone="Your own timezone"
    )
    @app_commands.autocomplete(timezone=timezone_autocomplete)
    async def view_schedule(self, interaction: discord.Interaction, applicant: discord.Member, timezone: str):
        if interaction.guild.id != 1391091143059701810:
            return await interaction.response.send_message("⛔ This command is only usable in the **MystiCraft Interviews** server.", ephemeral=True)

        user_roles = [r.id for r in interaction.user.roles if r.id != interaction.guild.id]  # exclude @everyone
        if len(user_roles) == 0 or (len(user_roles) == 1 and 1391097203023679508 in user_roles):
            return await interaction.response.send_message(
                "⛔ You do not have permission to use this command.", ephemeral=True)
 
        ref = db.reference(f"Schedules/{applicant.id}")
        data = ref.get()

        if not data or "slots" not in data or not data["slots"]:
            return await interaction.response.send_message(
                f"⚠️ No schedule data found for {applicant.mention}.", ephemeral=True)

        # Use interviewer's timezone if provided; otherwise use applicant's
        target_timezone = timezone or data.get("timezone")
        if not target_timezone:
            return await interaction.response.send_message(
                "⚠️ Could not determine a timezone to display.", ephemeral=True)

        tz = pytz.timezone(target_timezone)
        grouped = {}

        for ts in sorted(data["slots"]):
            dt = datetime.datetime.fromtimestamp(ts, pytz.UTC).astimezone(tz)
            date_label = dt.strftime("%B %-d")
            grouped.setdefault(date_label, []).append(f"<t:{ts}:t>")

        lines = [f"**🗓️ Schedule Availability for {applicant.mention} (shown in `{target_timezone}`):**\n"]
        for date, times in grouped.items():
            lines.append(f"**{date}**\n-# " + ", ".join(times))

        # Show when the applicant submitted this
        if updated_at := data.get("updated_at"):
            lines.append(f"\n-# <a:clock:1382887924273774754> Submitted: <t:{updated_at}:R>")
        if applicant_timezone := data.get("timezone"):
            lines.append(f"-# <:channel:1069401720238657587> Applicant Timezone: `{applicant_timezone}`")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

        # Build grouped dict: date string -> list of timestamps
        grouped_ts = {}
        for ts in sorted(data["slots"]):
            dt = datetime.datetime.fromtimestamp(ts, pytz.UTC).astimezone(pytz.timezone(target_timezone))
            date_label = dt.strftime("%B %-d")
            grouped_ts.setdefault(date_label, []).append(ts)

        await interaction.followup.send(
            f"👇 Click a date to schedule an interview with {applicant.mention} based on their availability:",
            view=ScheduleDateSelectView(grouped_ts, applicant, data["timezone"], target_timezone),
            ephemeral=True
        )



async def setup(bot):
    await bot.add_cog(ScheduleCog(bot))
