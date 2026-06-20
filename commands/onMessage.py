import discord
import re

from discord.ext import commands
from discord.ui import Button, View

from constants import SERVER_IDS

class SelfRoles(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Events", style=discord.ButtonStyle.grey, custom_id="events", emoji="🎮"
    )
    async def events(self, interaction: discord.Interaction, button: discord.ui.Button):
        alreadyHave = False
        for role in interaction.user.roles:
            if "Events" == role.name:
                alreadyHave = True
        role = discord.utils.get(interaction.guild.roles, name="Events")
        if alreadyHave:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(
                "You **no longer** have the <@&1136672595706646548> role.",
                ephemeral=True,
            )
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(
                "You have **obtained** the <@&1136672595706646548> role.",
                ephemeral=True,
            )

    @discord.ui.button(
        label="Giveaways",
        style=discord.ButtonStyle.grey,
        custom_id="giveaways",
        emoji="🎉",
    )
    async def giveaways(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        alreadyHave = False
        for role in interaction.user.roles:
            if "Giveaways" == role.name:
                alreadyHave = True
        role = discord.utils.get(interaction.guild.roles, name="Giveaways")
        if alreadyHave:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(
                "You **no longer** have the <@&1136672596470018111> role.",
                ephemeral=True,
            )
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(
                "You have **obtained** the <@&1136672596470018111> role.",
                ephemeral=True,
            )

    @discord.ui.button(
        label="Updates",
        style=discord.ButtonStyle.grey,
        custom_id="updates",
        emoji="👀",
    )
    async def sneakpeak(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        alreadyHave = False
        for role in interaction.user.roles:
            if "Updates" == role.name:
                alreadyHave = True
        role = discord.utils.get(interaction.guild.roles, name="Updates")
        if alreadyHave:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(
                "You **no longer** have the <@&1144344504590151700> role.",
                ephemeral=True,
            )
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(
                "You have **obtained** the <@&1144344504590151700> role.",
                ephemeral=True,
            )

    @discord.ui.button(
        label="Polls", style=discord.ButtonStyle.grey, custom_id="polls", emoji="🗳️"
    )
    async def polls(self, interaction: discord.Interaction, button: discord.ui.Button):
        alreadyHave = False
        for role in interaction.user.roles:
            if "Polls" == role.name:
                alreadyHave = True
        role = discord.utils.get(interaction.guild.roles, name="Polls")
        if alreadyHave:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(
                "You **no longer** have the <@&1136672598210662461> role.",
                ephemeral=True,
            )
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(
                "You have **obtained** the <@&1136672598210662461> role.",
                ephemeral=True,
            )


class onMsg(commands.Cog):
    def __init__(self, bot):
        self.client = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.client.user or message.author.bot == True or not message.guild:
            return
        
        if (
            len(message.attachments) >= 4 
            or len(re.findall(r'https?://[^\s]*discordapp[^\s]*attachment[^\s]*', message.content.lower())) >= 4 
            or "check my bio" in message.content.lower()
        ):
            # if all(attachment.filename == "image.jpeg" for attachment in message.attachments):
                try:
                    await message.delete()
                    shame_embed = discord.Embed(
                        description=f"🚨 {message.author.mention}'s account likely got hacked. Deleted spam message.\nDon't click on suspicious links, even if they come from your friends!",
                        color=discord.Color.red()
                    ).set_footer(text="Bypass this filter by not uploading 4 images at a time.")
                    await message.channel.send(content=message.author.mention, embed=shame_embed)
                except Exception as e:
                    print(f"Error handling MrBeast scam spam: {e}")
                return
        
        if message.content.lower() == "mc!guilds":
            guild_list = "\n".join([f"- {g.name} (`{g.id}`)" for g in self.client.guilds])
            await message.channel.send(f"**Guilds I'm in:**\n{guild_list}")

        if "mc!staff" in message.content and message.guild.id == SERVER_IDS["staff"]:
            from commands.Utility.staff import RefreshStaffView
            embed = discord.Embed(
                title="MystiCraft Staff Management Panel",
                description=(
                    "Welcome to the MystiCraft Staff Management Panel! This interface is designed to streamline staff role management across our network. "
                    "Click the `Refresh Staff Directory` button below to synchronize staff roles and ensure everyone is in their correct positions across all servers."
                ),
                color=0x3779F5,
            )
            await message.channel.send(embed=embed, view=RefreshStaffView())

        if "mc!selfroles" in message.content and message.guild.id == SERVER_IDS["main"]:
            embed = discord.Embed(
                title="<:mysticraftlogo:1263829753366974535> Choose your Ping Roles",
                description=(
                    "> Stay in the loop by only selecting the roles that matter to you. "
                    "React below to receive pings for:\n"
                    "\n**🎮 Events**\n-# <:reply:1036792837821435976> Never miss out on our fun events and activities!\n"
                    "\n**🎉 Giveaways**\n-# <:reply:1036792837821435976> Be the first to know about our exciting giveaways!\n"
                    "\n**👀 Updates**\n-# <:reply:1036792837821435976> Get exclusive early access to upcoming features and changes!\n"
                    "\n**📊 Polls**\n-# <:reply:1036792837821435976> Have your voice heard in server polls and decisions!"
                ),
                color=0x13C6F0,
            )
            embed.set_footer(text="Click again to remove the role from you.")

            await message.channel.send(embed=embed, view=SelfRoles())

        if (
            message.content.lower() == "ip"
            or message.content.lower() == "port"
            or message.content.lower() == "info"
        ):
            embed = discord.Embed(
                title="To connect to MystiCraft, use the following:",
                color=0x3779F5,
                description="""➥ IP: **play.mysticraft.xyz**
      ➥ Port: **19132**
      ➥ Version: `1:16 - latest`
      
      If you have any issues connecting to the server, feel free to open a ticket at <#1136672651209871541>.""",
            )
            await message.channel.send(embed=embed)

        elif (
            message.content.lower() == "store" or message.content.lower() == "shop"
        ):
            embed = discord.Embed(
                description="**Store: https://store.mysticraft.xyz/**", color=0x3779F5
            )
            button = Button(
                label="MystiCraft Shop",
                style=discord.ButtonStyle.link,
                url="https://store.mysticraft.xyz/",
            )
            view = View()
            view.add_item(button)
            await message.channel.send(embed=embed, view=view)

        elif (
            message.content.lower() == "support" or message.content.lower() == "help"
        ):
            if message.guild.id == SERVER_IDS["main"]:
                url = "https://discord.com/channels/1136662635039952988/1136672651209871541"
            elif message.guild.id == SERVER_IDS["tierlist"]:
                url = "https://discord.com/channels/1304829305443844096/1338567467076685885"
            else:
                return
            embed = discord.Embed(
                description="Looking for support? Don't worry, we got your back!",
                color=0x3779F5,
            )
            button = Button(
                label="Head over to #🎫〡support channel",
                style=discord.ButtonStyle.link,
                url=url,
            )
            view = View()
            view.add_item(button)
            await message.channel.send(embed=embed, view=view)

        elif (
            message.content.lower() == "link" or message.content.lower() == "verify"
        ):
            if message.guild.id == SERVER_IDS["main"]:
                url = "https://discord.com/channels/1136662635039952988/1518004795275874405"
            elif message.guild.id == SERVER_IDS["tierlist"]:
                url = "https://discord.com/channels/1304829305443844096/1460525451368861818"
            else:
                return
            embed = discord.Embed(
                description="To link your Minecraft account, please follow the steps below.",
                color=0x3779F5,
            )
            button = Button(
                label="Head over to #🔑〡how-to-link channel",
                style=discord.ButtonStyle.link,
                url=url,
            )
            view = View()
            view.add_item(button)
            await message.channel.send(embed=embed, view=view)

        elif (
            message.content.lower() == "socials"
        ):
            embed = discord.Embed(color=0x3779F5)
            embed.title = "MystiCraft Social Links"
            embed.description = """The following are the links to our social media! Make sure to drop a follow!"""
            twitter = Button(
                label="Twitter",
                style=discord.ButtonStyle.link,
                url="https://twitter.com/playmysticraft",
                emoji="<:Twitter:1078760886447128587>",
            )
            instagram = Button(
                label="Instagram",
                style=discord.ButtonStyle.link,
                url="https://instagram.com/playmysticraft",
                emoji="<:Instagram:1078761149836832838>",
            )
            tiktok = Button(
                label="TikTok",
                style=discord.ButtonStyle.link,
                url="https://www.tiktok.com/@mysticraftnetwork",
                emoji="<:TikTok:1078761557850333194>",
            )
            website = Button(
                label="Website",
                style=discord.ButtonStyle.link,
                url="https://mysticraft.xyz/",
                emoji="<:website:1078761962000896120>",
            )
            discordlink = Button(
                label="Discord",
                style=discord.ButtonStyle.link,
                url="https://discord.mysticraft.xyz",
                emoji="<:discord:1078762369473335397>",
            )
            ytlink = Button(
                label="YouTube",
                style=discord.ButtonStyle.link,
                url="https://youtube.com/@ninjamcyt",
                emoji="<:youtube:1147246329622442044>",
            )
            view = View()
            view.add_item(twitter)
            view.add_item(instagram)
            view.add_item(tiktok)
            view.add_item(website)
            view.add_item(discordlink)
            view.add_item(ytlink)
            await message.channel.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(onMsg(bot))
