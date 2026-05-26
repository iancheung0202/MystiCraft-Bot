import datetime
import discord

from discord.ext import commands

class OnCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_app_command_completion(
        self,
        interaction: discord.Interaction,
        command: discord.app_commands.Command,
    ):
        log_channel = self.bot.get_channel(1030892842308091987)
        if not log_channel:
            return

        server_invite = "https://example.com"
        embed = discord.Embed(
            description=(
                f"**Slash Command:** `/{command.qualified_name}`\n"
                f"**Used at:** <t:{int(interaction.created_at.timestamp())}:R>\n\n"
                f"**User Name:** {interaction.user}\n"
                f"**User ID:** `{interaction.user.id}`\n"
                f"**User Created:** <t:{int(interaction.user.created_at.timestamp())}:R>\n\n"
                f"**Guild Name:** [{interaction.guild.name}]({server_invite})\n"
                f"**Guild ID:** `{interaction.guild.id}`\n"
                f"**Member Count:** {interaction.guild.member_count}\n\n"
                f"**Channel Name:** [#{interaction.channel.name}]({server_invite})\n"
                f"**Channel ID:** `{interaction.channel.id}`\n"
                f"**Channel Mention:** {interaction.channel.mention}"
            ),
            color=discord.Color.blurple(),
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await log_channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(OnCommand(bot))