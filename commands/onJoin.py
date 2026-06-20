import discord

from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from constants import ROLE_IDS, SERVER_IDS
from commands.Tickets.tree import is_linked

async def create_welcome_image(
    user: discord.Member,
    background_path: str = "./assets/image.png",
    output_path: str = "./assets/welcome.png",
) -> str:
    # Save user avatar
    avatar_path = "./assets/avatar.png"
    if user.avatar:
        await user.avatar.with_static_format("png").with_size(256).save(avatar_path)
    else:
        avatar_path = "./assets/DefaultIcon.png"

    base_img = Image.open(background_path).convert("RGBA")
    avatar_img = Image.open(avatar_path).convert("RGBA")

    # Create circular mask for avatar
    size = avatar_img.size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size[0], size[1]), fill=255)
    avatar_img.putalpha(mask)

    # Paste avatar
    base_img.paste(avatar_img, (384, 50), avatar_img)

    draw = ImageDraw.Draw(base_img)
    white = (255, 255, 255)

    # Fonts
    title_font = ImageFont.truetype("./assets/MinecraftTen-VGORe.ttf", 75)
    name_font = ImageFont.truetype("./assets/MinecraftTen-VGORe.ttf", 35)

    # Text
    draw.text((350, 330), "Welcome", font=title_font, fill=white)

    username = user.name
    text_width = len(username) * 20
    draw.text(
        ((1024 / 2) - (text_width / 2), 410),
        username,
        font=name_font,
        fill=white,
    )

    base_img.save(output_path)
    return output_path

def ordinal(n: int) -> str:
    return f"{n}{'th' if 4 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


class OnMemberJoin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id == 1391091143059701810:
            role = member.guild.get_role(1391097203023679508)
            if role is not None:
                try:
                    await member.add_roles(role, reason="Auto-assign Applicant role")
                except discord.Forbidden:
                    pass

        if member.guild.id == SERVER_IDS["main"]:
            welcome_channel = self.bot.get_channel(1139141336541429841)
            image_channel = self.bot.get_channel(1026904121237831700)

            if not welcome_channel or not image_channel:
                return

            member_count = member.guild.member_count

            # Generate welcome image
            image_path = await create_welcome_image(member)
            image_message = await image_channel.send(file=discord.File(image_path))
            image_url = image_message.attachments[0].proxy_url

            if await is_linked(member, self.bot):
                await member.add_roles(member.guild.get_role(ROLE_IDS[SERVER_IDS["main"]]["linked"]), reason="Auto-assign Linked role")
                msg = "You have been automatically assigned the Linked role since you have linked your account before."
            else:
                msg = ""

            # Embed
            embed = discord.Embed(
                title=f"Welcome to {member.guild.name}!",
                description=(
                    f"Hey there {member.mention}, thanks for joining us! {msg}"
                    f"Here are some channels to get you started!\n\n"
                    f"[#📄〡rules](https://discord.com/channels/1136662635039952988/1136672661859217489) "
                    f"・ Read the rules carefully!\n"
                    f"[#🎉〡giveaways](https://discord.com/channels/1136662635039952988/1136672668297461840) "
                    f"・ Look out for ongoing giveaways!\n"
                    f"[#💬〡chat](https://discord.com/channels/1136662635039952988/1136672676476358686) "
                    f"・ Chat with other community members!"
                ),
                color=0x0EB1E1,
            )

            embed.set_image(url=image_url)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(
                text=f"You are the {ordinal(member_count)} member in the server.",
                icon_url=member.guild.icon.url,
            )

            await welcome_channel.send(embed=embed)

            try:
                await member.send(embed=embed)
            except discord.Forbidden:
                pass
            
        elif member.guild.id == SERVER_IDS["tierlist"]:
            welcome_channel = self.bot.get_channel(1473944522030452919)
            if not welcome_channel:
                return
            member_count = member.guild.member_count

            if await is_linked(member, self.bot):
                await member.add_roles(member.guild.get_role(ROLE_IDS[SERVER_IDS["tierlist"]]["linked"]), reason="Auto-assign Linked role")
                msg = "You have been automatically assigned the Linked role since you have linked your account before. "
            else:
                msg = "Verify yourself by following <#1460525451368861818>"
            embed = discord.Embed(
                title=f"Welcome to {member.guild.name}!",
                description=f"Hello {member.mention}, thanks for joining us! \n\n- {msg}\n- Join the testing waitlist for all gamemodes at <#1304842299376799857>\n- Need help? Reach out in <#1338567467076685885>",
                color=0x0EB1E1,
            ).set_footer(
                text=f"You are the {ordinal(member_count)} member in the server.",
                icon_url=member.guild.icon.url,
            )
            await welcome_channel.send(content=member.mention, embed=embed)
            try:
                await member.send(embed=embed)
            except discord.Forbidden:
                pass
            

async def setup(bot: commands.Bot):
    await bot.add_cog(OnMemberJoin(bot))