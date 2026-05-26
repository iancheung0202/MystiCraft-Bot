import discord

from firebase_admin import db
from discord import app_commands
from discord.ext import commands

class StaffApp(commands.GroupCog, name="application"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(
        name="accept",
        description="Notify an accepted user via DM and invite them to the staff server"
    )
    @app_commands.describe(user="The user to accept")
    async def accept(
        self,
        interaction: discord.Interaction,
        user: discord.User
    ) -> None:
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(f":x: You do not have permission to use this command.", ephemeral=True)
        try:
            invite = (
                await interaction.client.get_guild(1064570075304177734)
                .text_channels[0]
                .create_invite(max_age=604800, max_uses=1)
            )
            embed = discord.Embed(
                title="MystiCraft Staff Application Update 🎉",
                description=(
                    f"🎉 Congratulations! You have passed the interview process and are now officially invited to our Staff Team.\n\n"
                    f"📌 **Please use this [one-time invite]({invite}) to join our staff server!** We’re excited to have you on board!"
                ),
                color=0x00FF00,
            )
            await user.send(embed=embed)
            await interaction.response.send_message(
                content=f"✅ Successfully accepted {user.mention} and sent them this DM.",
                embed=embed,
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                content=f"❌ Could not DM {user.mention}. They may have DMs disabled.",
                ephemeral=True
            )

    @app_commands.command(
        name="reject",
        description="Notify a rejected user via DM"
    )
    @app_commands.describe(user="The user to reject")
    async def reject(
        self,
        interaction: discord.Interaction,
        user: discord.User
    ) -> None:
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(f":x: You do not have permission to use this command.", ephemeral=True)
        try:
            embed = discord.Embed(
                title="MystiCraft Staff Application Update :pensive:",
                description="Thank you so much for applying for staff and attending the interview. Unfortunately, we aren't able to accept you at this time. \n\nWe are unable to give everyone who applies a specific reason for denial, but do note that the review process is a separate, manual process done one-by-one by our management team with the server owner. During the review process, there are a lot of factors that get considered for each application. \n\nDon't fret – you're always welcome to reapply in the future. In order to reapply, you'll have to wait 14 days from today. Applications sent from you during the waiting period will be ignored.\n\nOnce again, due to the high volume of applications, we're currently unable to provide any more details or specifics about the nature of your application. We really hope you're not too discouraged by the news, and remember; this decision in no way speaks to the value, joy, and belonging you bring to your community every day.",
                color=0xFF0000,
            )
            await user.send(embed=embed)
            await interaction.response.send_message(
                content=f"🛑 Successfully rejected {user.mention} and sent them this DM.",
                embed=embed,
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                content=f"❌ Could not DM {user.mention}. They may have DMs disabled.",
                ephemeral=True
            )

    @app_commands.command(
        name="toggle",
        description="Toggle the status of staff application (open/closed)"
    )
    async def toggle(self, interaction: discord.Interaction) -> None:
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(f":x: You do not have permission to use this command.", ephemeral=True)
        
        ref = db.reference("/Staff App")
        status = ref.get()
        staffAppStatus = "Closed"

        if status:
            for key, value in status.items():
                staffAppStatus = value.get("Status", "Closed")
                db.reference("/Staff App").child(key).delete()
                break
        
        if staffAppStatus == "Open":
            new = "Closed"
            data = {
                interaction.guild.name: {
                    "Status": new,
                }
            }
            for key, value in data.items():
                ref.push().set(value)
        else:
            new = "Open"
            data = {
                interaction.guild.name: {
                    "Status": new,
                }
            }
            for key, value in data.items():
                ref.push().set(value)

        await interaction.response.send_message(f"**Staff Application Status:** {new}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StaffApp(bot))
