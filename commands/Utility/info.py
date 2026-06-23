import discord
import time

from discord.ext import commands
from discord import app_commands

EMOJI_LOGO          = "<:mysticraftlogo:1263811799237787789>"
EMOJI_MC_CLOCK      = "<:mc_clock:1518027805361967104>"
EMOJI_EMERALD       = "<:emerald:1518031176730804244>"
EMOJI_REDSTONE      = "<:redstone_dust:1518031324588539986>"
EMOJI_GOLD_INGOT    = "<:gold_ingot:1518031441248653433>"
EMOJI_STEVE         = "<:steve:1518031537814110382>"
EMOJI_NETHER_STAR   = "<:nether_star:1518033504120606771>"
EMOJI_COMPASS       = "<a:compass:1518032475803226214>"
EMOJI_ENDER_PEARL   = "<:ender_pearl:1518033866995269763>"
EMOJI_MAP           = "<:map:1518038367521210499>"
EMOJI_BOOK          = "<:book:1518051136488214549>"
EMOJI_SCROLL        = "<:parchment:1518454271719510297>"
EMOJI_FEATHER       = "<:feather:1518454349053952150>"
EMOJI_BARRIER       = "<:barrier:1518454369887195228>"
EMOJI_SPYGLASS      = "<:spyglass:1518454328480891083>"
EMOJI_HOURGLASS     = "<:hourglass:1518454206162538546>"
EMOJI_STORE         = "<:shop:1518114830501023935>"
EMOJI_CRYSTAL       = "<:crystal:1518050761010057290>"
EMOJI_CONNECT       = "<:lodestone:1518038285354795158>"
EMOJI_COMMAND_BLOCK = "<a:command_block:1518032605692297256>"
EMOJI_WOOD          = "<:wood:1518486506703163402>"
EMOJI_STONE         = "<:stone:1518477821679505468>"
EMOJI_IRON          = "<:iron:1518477842373935174>"
EMOJI_GOLD          = "<:gold:1518477859679633539>"
EMOJI_DIAMOND       = "<:diamond:1518477882958151690>"
EMOJI_NETHERITE     = "<:netherite:1518477903568830524>"
EMOJI_BOOSTER       = "<:Booster_Logo:1154871576047657051>"
EMOJI_YOUTUBE       = "<:youtube:1141391526195368067>"
EMOJI_TWITTER       = "<:twitter:1518478905261031444>"
EMOJI_INSTAGRAM     = "<:instagram:1518478993144287323>"
EMOJI_TIKTOK        = "<:tiktok:1518479385420894384>"
EMOJI_REPLY         = "<:reply:1036792837821435976>"
EMOJI_ARROW         = "<a:arightarrow:1518483846130040853>"
EMOJI_TIERLIST      = "<:mysticrafttierlist:1460527955309498550>"
EMOJI_MONEY         = "<:Minecraft_Money:1190896453967679518>"

BANNER_URL = (
    "https://media.discordapp.net/attachments/1079100558507520001/1518473153507102861/"
    "banner.png?ex=6a3a0bd3&is=6a38ba53&hm=687c972febd74d7112134a3af88fd177f8735cabf55b4c3f89c5b5f70da641fc"
)

ABOUT_US_TEXT = (
    f"## {EMOJI_LOGO} About MystiCraft\n"
    f"{EMOJI_COMPASS} **MystiCraft** is a cracked, free-to-play Minecraft network supporting both "
    "**Java & Bedrock** with version support from **1.16 to the latest**.\n\n"
    f"{EMOJI_MAP} We currently offer four main gamemodes: **Lifesteal**, **Survival**, **Practice**, and **Vanilla**. "
    f"Join us on <#1136672646151544862> or <#1136672648714268823> and become part of the adventure!"
)

SOCIALS_HEADER_TEXT = (
    f"## {EMOJI_YOUTUBE} Social Links\n"
    f"Stay connected with MystiCraft across all platforms! {EMOJI_SCROLL} "
)

WEBSITE_HEADER_TEXT = (
    f"## {EMOJI_EMERALD} Website\n"
    f"Visit our official website for more information, news, and updates about MystiCraft! {EMOJI_COMMAND_BLOCK} "
)

LEVEL_ROLES_TEXT = (
    f"## {EMOJI_SPYGLASS} Level Roles\n"
    f"Level up by chatting and staying active in the server! {EMOJI_BOOK} \n\n"
    f"{EMOJI_WOOD} **<@&1136672590304399520> (Level 1)** {EMOJI_ARROW} *Appear above normal members + add reactions*\n"
    f"{EMOJI_STONE} **<@&1136672589176111244> (Level 5)** {EMOJI_ARROW} *All above + attach files in <#1136672677927592027>*\n"
    f"{EMOJI_IRON} **<@&1136672587116712067> (Level 15)** {EMOJI_ARROW} *All above + attach files in <#1136672676476358686>*\n"
    f"{EMOJI_GOLD} **<@&1136672584499482624> (Level 25)** {EMOJI_ARROW} *All above + use external emojis*\n"
    f"{EMOJI_DIAMOND} **<@&1136672581592809612> (Level 35)** {EMOJI_ARROW} *All above + access to Diamond-tier giveaways*\n"
    f"{EMOJI_NETHERITE} **<@&1136672580187725854> (Level 50)** {EMOJI_ARROW} *All above + access to exclusive VIP chat*\n\n"
    f"-# {EMOJI_NETHER_STAR} **Note:** <@&1141377845671764018>, <@&1136672571442602024> and <@&1136672570096230481> members also unlock Diamond-tier giveaways."
)

BOOSTER_PERKS_TEXT = (
    f"## {EMOJI_BOOSTER} Booster Perks\n"
    f"Boost our Discord and earn exclusive rewards on **both Discord and in-game**! {EMOJI_MONEY} \n\n"
    f"{EMOJI_NETHER_STAR} **Server Booster** role on Discord above regular members\n"
    f"{EMOJI_REPLY} Upload files & media *(memes welcome)*\n"
    f"{EMOJI_REPLY} Permission to send embed links\n\n"
    f"{EMOJI_CRYSTAL} **Booster Rank in-game** if you linked your account (<#1518004795275874405>)\n"
    f"{EMOJI_REPLY} **VIP+** rank on Lifesteal\n"
    f"{EMOJI_REPLY} **Survival** rank on Survival\n"
    f"{EMOJI_REPLY} **Elite** rank on Vanilla"
)


def build_info_container(timestamp: int) -> discord.ui.Container:
    class InfoContainer(discord.ui.Container):
        banner = discord.ui.MediaGallery(discord.MediaGalleryItem(BANNER_URL))
        sep0 = discord.ui.Separator(visible=False, spacing=discord.SeparatorSpacing.small)
        about = discord.ui.TextDisplay(ABOUT_US_TEXT)
        sep1 = discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large)
        socials_header = discord.ui.TextDisplay(SOCIALS_HEADER_TEXT)
        row1 = discord.ui.ActionRow(
            discord.ui.Button(
                label="YouTube",
                emoji=EMOJI_YOUTUBE,
                style=discord.ButtonStyle.link,
                url="https://youtube.com/@ninjamcyt"
            ),
            discord.ui.Button(
                label="Twitter",
                emoji=EMOJI_TWITTER,
                style=discord.ButtonStyle.link,
                url="https://twitter.com/playmysticraft"
            ),
            discord.ui.Button(
                label="Instagram",
                emoji=EMOJI_INSTAGRAM,
                style=discord.ButtonStyle.link,
                url="https://instagram.com/playmysticraft"
            ),
            discord.ui.Button(
                label="TikTok",
                emoji=EMOJI_TIKTOK,
                style=discord.ButtonStyle.link,
                url="https://tiktok.com/@mysticraftnetwork"
            ),
        )
        sep2 = discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large)
        website_header = discord.ui.TextDisplay(WEBSITE_HEADER_TEXT)
        row2 = discord.ui.ActionRow(
            discord.ui.Button(
                label="Website",
                emoji=EMOJI_MAP,
                style=discord.ButtonStyle.link,
                url="https://mysticraft.xyz"
            ),
            discord.ui.Button(
                label="Store",
                emoji=EMOJI_STORE,
                style=discord.ButtonStyle.link,
                url="https://store.mysticraft.xyz"
            ),
            discord.ui.Button(
                label="Tierlist",
                emoji=EMOJI_TIERLIST,
                style=discord.ButtonStyle.link,
                url="https://tierlist.mysticraft.xyz"
            ),
            discord.ui.Button(
                label="Staff",
                emoji=EMOJI_STEVE,
                style=discord.ButtonStyle.link,
                url="https://mysticraft.xyz/staff"
            ),
        )
        sep3 = discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large)
        level_roles = discord.ui.TextDisplay(LEVEL_ROLES_TEXT)
        sep4 = discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large)
        booster_perks = discord.ui.TextDisplay(BOOSTER_PERKS_TEXT)
        sep5 = discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large)
        footer = discord.ui.TextDisplay(f"-# {EMOJI_MC_CLOCK} **Last updated:** <t:{timestamp}:R>")
    
    return InfoContainer(accent_color=0x1ec7f1)


class InfoView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.container = build_info_container(int(time.time()))
        self.add_item(self.container)


class InfoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="info",
        description="Post the MystiCraft server information panel."
    )
    @app_commands.default_permissions(manage_messages=True)
    async def info(self, interaction: discord.Interaction):
        view = InfoView() 
        await interaction.channel.send(view=view, allowed_mentions=discord.AllowedMentions(roles=False))
        await interaction.response.send_message(f"{EMOJI_EMERALD} Info panel posted!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(InfoCog(bot))