import sys
import platform
import psutil
import discord
import firebase_admin

from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from firebase_admin import credentials, db

class Select(discord.ui.Select):
    def __init__(self, commands_list):
        self.commands_list = commands_list

        utility = ""
        ticket = ""
        waitlist = ""

        for command in self.commands_list:
            # Ticket commands
            if "ticket" in command.name:
                for subcommand in command.options:
                    if subcommand.type == discord.AppCommandOptionType.subcommand:
                        ticket += (
                            f"\n\n</{command.name} {subcommand.name}:{command.id}>\n"
                            f"<:reply:1036792837821435976> {subcommand.description}"
                        )
                    else:
                        ticket += (
                            f"\n\n<:blank:1036792889121980426>"
                            f"<:reply:1036792837821435976> "
                            f"`{subcommand.name}` - {subcommand.description}"
                        )

            # Waitlist commands
            elif "waitlist" in command.name:
                for subcommand in command.options:
                    if subcommand.type == discord.AppCommandOptionType.subcommand:
                        waitlist += (
                            f"\n\n</{command.name} {subcommand.name}:{command.id}>\n"
                            f"<:reply:1036792837821435976> {subcommand.description}"
                        )
                    else:
                        waitlist += (
                            f"\n\n<:blank:1036792889121980426>"
                            f"<:reply:1036792837821435976> "
                            f"`{subcommand.name}` - {subcommand.description}"
                        )

            # Utility commands
            else:
                utility += (
                    f"\n\n{command.mention}\n"
                    f"<:reply:1036792837821435976> {command.description}"
                )

                for subcommand in command.options:
                    if subcommand.type == discord.AppCommandOptionType.subcommand:
                        utility += (
                            f"\n</{command.name} {subcommand.name}:{command.id}>\n"
                            f"<:reply:1036792837821435976> {subcommand.description}"
                        )
                        for option in subcommand.options:
                            utility += (
                                f"\n<:blank:1036792889121980426>"
                                f"<:reply:1036792837821435976> "
                                f"`{option.name}` - {option.description}"
                            )
                    else:
                        utility += (
                            f"\n<:blank:1036792889121980426>"
                            f"<:reply:1036792837821435976> "
                            f"`{subcommand.name}` - {subcommand.description}"
                        )

        self.sections = [
            [
                utility,
                "Utility Commands",
                "🛠️",
                "The following slash commands are used for basic functions that many bots "
                "offer. These commands are accessible to everyone in the server."
            ],
            [
                ticket,
                "Ticket System",
                "🎫",
                "The following commands are used to setup and deal with tickets. To start "
                "using tickets instantly, use </ticket setup:1078362594705948760>. "
                "Note that these commands are only available to members with Administrator "
                "permission."
            ],
            [
                waitlist,
                "Waitlist System",
                "👥",
                "**This function only works in MystiCraft Tierlist server**. Do not enable "
                "this function in other servers. Refer to <#1338547476897992826>."
            ],
        ]

        options = [
            discord.SelectOption(label=section[1], emoji=section[2])
            for section in self.sections
        ]

        super().__init__(
            placeholder="Browse Commands",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="browsecommands",
        )

    async def callback(self, interaction: discord.Interaction):
        for section in self.sections:
            if self.values[0] == section[1]:
                intro = discord.Embed(
                    title=f"{section[2]} {section[1]}",
                    description=section[3],
                    color=0xFFFF00,
                )
                body = discord.Embed(
                    description=section[0],
                    color=discord.Color.blurple(),
                )

                await interaction.response.edit_message(
                    embeds=[intro, body],
                    view=HelpPanel(self.commands_list),
                )
                break


class HelpPanel(View):
    def __init__(self, commands_list=None):
        super().__init__(timeout=None)
        self.commands_list = commands_list
        self.add_item(
            Button(
                label="Visit Website",
                style=discord.ButtonStyle.link,
                url="https://mysticraft.xyz/",
            )
        )
        self.add_item(Select(self.commands_list))

    @discord.ui.button(
        label="Overview",
        style=discord.ButtonStyle.blurple,
        custom_id="overview",
    )
    async def overview(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        embed = discord.Embed(
            title="MystiCraft Help",
            description=(
                "MystiCraft Core is a versatile Discord bot offering utility, moderation, "
                "and ticket commands to enhance server functionality and support."
            ),
            color=0x1DBCEB,
        )

        embed.add_field(
            name="<:mysticraft:1078363938623860827> Support Server",
            value="Visit our [support server](https://discord.gg/mysticraft) for "
                  "suggestions, questions, or bug reports.",
            inline=True,
        )
        embed.add_field(
            name="<:slash:1037445915348324505> Command Usage",
            value="This bot uses slash commands. Type `/` to view available commands.",
            inline=True,
        )

        await interaction.response.edit_message(
            embed=embed,
            view=HelpPanel(self.commands_list),
        )

    @discord.ui.button(
        label="Statistics",
        style=discord.ButtonStyle.blurple,
        custom_id="statistics",
    )
    async def statistics(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        mem = psutil.virtual_memory()

        embed = discord.Embed(
            title="MystiCraft Bot Statistics",
            color=0x1DBCEB,
        )

        embed.add_field(
            name="<:info:1037445870469267638> Package Info",
            value=(
                f"```"
                f"OS - {platform.system()}\n"
                f"Python - {platform.python_version()}\n"
                f"discord.py - {discord.__version__}\n"
                f"Firebase - {firebase_admin.__version__}"
                f"```"
            ),
            inline=False,
        )

        embed.add_field(
            name="<:dev:1037445830749204624> Bot Metadata",
            value=(
                f"> Application ID: `{interaction.client.application_id}`\n"
                f"> Servers: `{len(interaction.client.guilds)}`\n"
                f"> Latency: `{int(interaction.client.latency * 1000)}ms`"
            ),
            inline=True,
        )

        embed.add_field(
            name="📊 Process Usage",
            value=(
                f"> CPU: `{psutil.cpu_percent(0.1)}%`\n"
                f"> RAM: `{mem.used / (1024**3):.2f} / "
                f"{mem.total / (1024**3):.2f} GB`\n"
                f"> Free: `{100 - mem.percent}%`"
            ),
            inline=True,
        )

        await interaction.response.edit_message(embed=embed, view=HelpPanel(self.commands_list))

    @discord.ui.button(
        label="View Server Configuration",
        style=discord.ButtonStyle.blurple,
        custom_id="serverconfig",
    )
    async def server_config(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        embed = discord.Embed(
            title="Server Configuration",
            description=f"Configuration for **{interaction.guild.name}**:",
            color=0x1DBCEB,
        )

        ref = db.reference("/Tickets")
        tickets = ref.get() or {}

        for data in tickets.values():
            if data["Server ID"] == interaction.guild.id:
                embed.add_field(
                    name="Ticket System",
                    value=(
                        "<:yes:1036811164891480194> Enabled\n"
                        f"<:reply:1036792837821435976> "
                        f"**Category:** <#{data['Category ID']}>\n"
                        f"<:reply:1036792837821435976> "
                        f"**Log Channel:** <#{data['Log Channel ID']}>"
                    ),
                    inline=True,
                )
                break
        else:
            embed.add_field(
                name="Ticket System",
                value="<:no:1036810470860013639> Disabled",
                inline=True,
            )
        await interaction.response.edit_message(embed=embed, view=HelpPanel(self.commands_list))


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="View all available bot commands",
    )
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        commands_list = await self.bot.tree.fetch_commands()
        embed = discord.Embed(
            title="MystiCraft Help",
            description=(
                "MystiCraft Core is a versatile Discord bot offering utility, moderation, "
                "and ticket commands to improve your server experience."
            ),
            color=0x1DBCEB,
        )
        embed.add_field(
            name="<:mysticraft:1078363938623860827> Support Server",
            value="Join our [support server](https://discord.gg/mysticraft).",
            inline=True,
        )
        embed.add_field(
            name="<:slash:1037445915348324505> Command Usage",
            value="Type `/` to view available commands.",
            inline=True,
        )
        await interaction.followup.send(embed=embed, view=HelpPanel(commands_list))

async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
