import discord
import os
import firebase_admin
import datetime
import asyncio
import logging
import sys
import pytz
import aiomysql

from discord.ext import commands
from firebase_admin import credentials

from commands.Tickets.tickets import CloseTicketButton, TicketAdminButtons, ConfirmCloseTicketButtons, CreateTicketButtonView, StaffAppDelete, AcceptRejectButton, ApplyForStaff, MediaAcceptRejectButton, ResolveFlagView, AppealCloseTicketButton, SelectView
from commands.Tierlist.waitlist import WaitlistSelectionView, JoinQueueButtonView
from commands.Tierlist.ht_waitlist import HTWaitlistSelectionView, ApproveDenyView, HTSkipView, FindTicketView
from commands.Help.help import HelpPanel
from commands.onMessage import RefreshStaffView, SelfRoles, RefreshStaffV2View
from commands.Tickets.summary import Stats
from commands.Utility.registration import RegistrationButtonView

cred = credentials.Certificate(
    "REMOVED"
)
default_app = firebase_admin.initialize_app(
    cred, {"databaseURL": "REMOVED"}
)

class MystiCraft(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        intents.presences = False
        super().__init__(
            command_prefix="mc!",
            intents=intents,
            application_id=1078152278399262731,
            help_command=None,
            activity=discord.CustomActivity(f"Welcome to MystiCraft")
        )

    async def setup_hook(self):
        for path, subdirs, files in os.walk("commands"):
            for name in files:
                if name.endswith(".py"):
                    extension = os.path.join(path, name).replace("/", ".")[:-3]
                    await self.load_extension(extension)
                    print(f"Loaded {extension} in MystiCraft")
        await bot.tree.sync()

        bot.tlresults_pool = await aiomysql.create_pool(
            host='172.18.0.1',
            port=3306,
            user='REMOVED',
            password='REMOVED',
            db='REMOVED',
            autocommit=True
        )

        bot.tllink_pool = await aiomysql.create_pool(
            host='172.18.0.1',
            port=3306,
            user='REMOVED',
            password='REMOVED',
            db='REMOVED',
            autocommit=True
        )

        self.add_view(CloseTicketButton())
        self.add_view(TicketAdminButtons())
        self.add_view(ConfirmCloseTicketButtons())
        self.add_view(StaffAppDelete())
        self.add_view(AcceptRejectButton())
        self.add_view(MediaAcceptRejectButton())
        self.add_view(ApplyForStaff())
        self.add_view(CreateTicketButtonView())
        self.add_view(ResolveFlagView())
        self.add_view(SelectView())
        self.add_view(WaitlistSelectionView())
        self.add_view(JoinQueueButtonView())
        self.add_view(HTWaitlistSelectionView())
        self.add_view(HTSkipView())
        self.add_view(ApproveDenyView())
        list = await bot.tree.fetch_commands()
        self.add_view(HelpPanel(list))
        self.add_view(RefreshStaffView())
        self.add_view(SelfRoles())
        self.add_view(Stats())
        self.add_view(AppealCloseTicketButton())
        self.add_view(RegistrationButtonView())
        self.add_view(RefreshStaffV2View())
        self.add_view(FindTicketView())

    async def logging(self):
        def pacific_time_converter(*args):
            utc_dt = datetime.datetime.now(datetime.UTC).replace(tzinfo=pytz.utc)
            pacific_dt = utc_dt.astimezone(pytz.timezone("America/Los_Angeles"))
            return pacific_dt.timetuple()

        logging.Formatter.converter = pacific_time_converter
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        file_handler = logging.FileHandler("console_output.log")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])

        class PrintLogger:
            def __init__(self):
                self.stdout = sys.stdout

            def write(self, message):
                if message.strip():
                    logging.info(message.strip())

            def flush(self):
                pass

        sys.stdout = PrintLogger()

        def log_uncaught_exceptions(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            logging.error(
                "Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback)
            )

        sys.excepthook = log_uncaught_exceptions

    async def status_task(self):
        timeout = 5
        while True:
            await asyncio.sleep(timeout)
            await self.change_presence(
                status=discord.Status.dnd,
                activity=discord.Activity(
                    type=discord.ActivityType.playing, name="Visiting mysticraft.xyz"
                ),
            )
            await asyncio.sleep(timeout)
            await self.change_presence(
                status=discord.Status.idle,
                activity=discord.Activity(
                    type=discord.ActivityType.playing, name="Ordering store.mysticraft.xyz"
                ),
            )
            await asyncio.sleep(timeout)
            await self.change_presence(
                status=discord.Status.online,
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"Browsing tierlist.mysticraft.xyz",
                ),
            )

    async def on_ready(self):
        print(f"{self.user} has connected to Discord! ({self.user.id})")
        self.loop.create_task(self.status_task())
        self.loop.create_task(self.logging())

bot = MystiCraft()
bot.run("REMOVED")
