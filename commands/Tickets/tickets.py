import discord
import datetime
import asyncio
import time
import emoji
import random
import string
import hashlib
import re
import os
from types import SimpleNamespace

from firebase_admin import db
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View

OWNER_ROLE_ID = 1373893342169137202
CO_OWNER_ROLE_ID = 1374977572248748032
EXECUTIVE_ROLE_ID = 1374975813891395784
MANAGER_ROLE_ID = 1373892851745685524
ADMIN_ROLE_ID = 1373890838496673852
DEV_ROLE_ID = 1373890109216129155
SR_MOD_ROLE_ID = 1373889160833798274
MOD_ROLE_ID = 1373887662842183801
HELPER_ROLE_ID = 1373883332492001341

TIERLIST_OWNER_ROLE_ID = 1304848576190484553
TIERLIST_MANAGER_ROLE_ID = 1460312013535318077
TIERLIST_ADMIN_ROLE_ID = 1304851740226748556
TIERLIST_REGULATOR_ROLE_ID = 1339144441583370251
TIERLIST_STAFF_ROLE_ID = 1305573653332754533

PING_ROLE_ID = 1375131045589946518 # SUPPORT PING
LINKED_ROLE_ID = 1459863162223595656 # TIERLIST LINKED ROLE

MAIN_SERVER_ID = 1136662635039952988
SUPPORT_SERVER_ID = 1373869107484688436
TIERLIST_SERVER_ID = 1304829305443844096

STAFF_APPS_CATEGORY = 1374959644727840899
MEDIA_APPS_CATEGORY = 1374959657310748745

PASSWORD_RESET_CATEGORY_ID = 1500604708987994342
SERVER_QUESTIONS_CATEGORY_ID = 1374959236420730890
BILLING_SUPPORT_CATEGORY_ID = 1374959248806510662
APPEAL_CATEGORY_ID = 1374959224752312362
PLAYER_REPORT_CATEGORY_ID = 1374959260458287125
BUG_REPORT_CATEGORY_ID = 1374959285716647947
STAFF_REPORT_CATEGORY_ID = 1374959273930391592

GENERAL_SUPPORT_TIERLIST_CATEGORY_ID = 1462026697024213024
TESTER_APPLICATION_TIERLIST_CATEGORY_ID = 1462026742486011934
HIGH_TESTING_TIERLIST_CATEGORY_ID = 1462026779823833211
TIER_MIGRATION_TIERLIST_CATEGORY_ID = 1462026806335897725
STAFF_APPLICATION_TIERLIST_CATEGORY_ID = 1462957616534655103

# TICKET COOLDOWNS (in seconds)
TICKET_COOLDOWNS = {
    "normal": 21600,  # 6 hours
    "password_reset": 86400 * 7,  # 7 days
    "appeal": 86400 * 14,  # 14 days
    "high_testing": 86400 * 30,  # 30 days
    "staff_app_tierlist": 86400 * 30,  # 30 days
}

# FLAGGING
support_channel_map = {
    "owner": 1374962834210951259,
    "manager": 1374962875998670860,
    "mod": 1374962893451165856,
}
tierlist_channel_map = {
    "owner": 1452375067538362540,
    "manager": 1452375111431753748,
    "mod": 1452375122823479336,
}
emoji_map = {
    "owner": "⚫️",
    "manager": "🟠",
    "mod": "🟣",
}

async def check_for_manager(interaction):
    if (
        interaction.guild.get_role(OWNER_ROLE_ID) # Support Server
        not in interaction.user.roles
        and interaction.guild.get_role(EXECUTIVE_ROLE_ID)
        not in interaction.user.roles
        and interaction.guild.get_role(CO_OWNER_ROLE_ID)
        not in interaction.user.roles
        and interaction.guild.get_role(MANAGER_ROLE_ID)
        not in interaction.user.roles
        and interaction.guild.get_role(1064570857537667193) # Staff Server
        not in interaction.user.roles
        and interaction.guild.get_role(1064571049410318336)
        not in interaction.user.roles
        and interaction.guild.get_role(1064571207627853844)
        not in interaction.user.roles
        and interaction.guild.get_role(1136672543466598592) # Main Server
        not in interaction.user.roles
        and interaction.guild.get_role(1136672547270819900) 
        not in interaction.user.roles
        and interaction.guild.get_role(1136672551729381418)
        not in interaction.user.roles
        and interaction.guild.get_role(1304848576190484553) # Tierlist Server
        not in interaction.user.roles
        and interaction.guild.get_role(1304851740226748556)
        not in interaction.user.roles
        and interaction.guild.get_role(1460312013535318077)
        not in interaction.user.roles
    ):
        return await interaction.response.send_message(
            "This action can only be done by Manager+ only.", ephemeral=True
        )


async def is_linked(user, client=None):
    """Return (linked, ign) for a member using the linking table or main-server nickname fallback."""
    try:
        async with client.tllink_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT player_name FROM mystilinking WHERE discord_id = %s",
                    (str(user.id),),
                )
                row = await cursor.fetchone()
                if row and row[0]:
                    return True, row[0]
    except Exception:
        pass

    try:
        if client is None:
            return False, None

        main_guild = client.get_guild(MAIN_SERVER_ID)
        if main_guild is None:
            return False, None

        member = main_guild.get_member(user.id)
        if member is None:
            member = await main_guild.fetch_member(user.id)

        if member is None:
            return False, None

        linked_role = main_guild.get_role(1275144456122929152)
        if linked_role is None or linked_role not in member.roles:
            return False, None

        nickname = member.nick or member.display_name or ""
        match = re.search(r"\[(.+?)\]$", nickname)
        if match:
            return True, match.group(1).strip()
    except Exception:
        pass

    return False, None

class StaffAppDelete(discord.ui.View):
    def __init__(self, typeOfApp=None):
        self.typeOfApp = typeOfApp
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Delete Channel",
        style=discord.ButtonStyle.blurple,
        custom_id="deletea",
        emoji="✉️",
    )
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await check_for_manager(interaction)
        embed = discord.Embed(
            title="Deleting Ticket...",
            description="Ticket will be deleted in 5 seconds",
            color=0xFF0000,
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await interaction.message.delete()
        await interaction.channel.send(embed=embed)
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(
        label="Add to Channel",
        style=discord.ButtonStyle.grey,
        custom_id="lingeringaddapplicant",
    )
    async def lingeringaddapplicant(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await check_for_manager(interaction)
        user = interaction.guild.get_member(
            int(interaction.message.content.split("`")[1])
        )
        await interaction.channel.set_permissions(
            user, send_messages=True, read_messages=True, attach_files=True
        )
        embed = discord.Embed(
            title="You have been added to a ticket channel!",
            description=f"An administrator or manager has added you to this channel to discuss your **{self.typeOfApp if self.typeOfApp is not None else ''} application** further. Thank you for your interest in joining the {self.typeOfApp} team!",
            color=discord.Color.yellow(),
        )
        button = Button(
            style=discord.ButtonStyle.link,
            label="View Ticket",
            url=f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}",
        )
        view = View()
        view.add_item(button)
        await user.send(embed=embed, view=view)
        msg = await interaction.channel.send(user.mention)
        await msg.delete()
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Applicant Added to This Channel",
                description=f"{user.mention} has been notified via DM if they have DMs open. They can now send messages, read previous discussions, and attach files. Use this space to discuss their application further before making a final decision.",
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )


class AcceptRejectButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Accept", style=discord.ButtonStyle.green, custom_id="accept"
    )
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await check_for_manager(interaction)
        user = interaction.guild.get_member(
            int(interaction.message.content.split("`")[1])
        )
        invite = (
            await interaction.client.get_guild(1391091143059701810)
            .text_channels[0]
            .create_invite(max_age=604800, max_uses=1)
        )
        embed = discord.Embed(
            title="MystiCraft Staff Application Update 🎉",
            description=(
                f"Thank you for applying for a staff position at **MystiCraft**! After reviewing your application, "
                f"we are pleased to inform you that you have **passed the application process** and are invited to an interview. 🎊\n\n"
                f"📌 **Please use this [one-time invite]({invite}) to join our interview server** and set up a time when you are available to talk."
            ),
            color=0x00FF00,
        )
        await user.send(content=invite, embed=embed)
        await interaction.message.edit(
            content=f"✅ Applicant ID: `{user.id}`", view=StaffAppDelete("staff")
        )
        await interaction.response.send_message(ephemeral=True)

    @discord.ui.button(
        label="Reject", style=discord.ButtonStyle.red, custom_id="reject"
    )
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await check_for_manager(interaction)
        user = interaction.guild.get_member(
            int(interaction.message.content.split("`")[1])
        )
        embed = discord.Embed(
            title="You are rejected! :pensive:",
            description="Thank you so much for applying for staff. We receive numerous incredible applications every single day and unfortunately, we aren't able to accept you at this time. \n\nWe are unable to give everyone who applies a specific reason for denial, but do note that the review process is a separate, manual process done one-by-one by our management team with the server owner. During the review process, there are a lot of factors that get considered for each application. \n\nDon't fret - you're always welcome to reapply in the future. In order to reapply, you'll have to wait 7 days from today. Applications sent from you during the waiting period will be ignored.\n\nOnce again, due to the high volume of applications, we're currently unable to provide any more details or specifics about the nature of your application. We really hope you're not too discouraged by the news, and remember; this decision in no way speaks to the value, joy, and belonging you bring to your community every day.",
            color=0xFF0000,
        )
        await user.send(embed=embed)
        await interaction.message.edit(
            content=f":x: Applicant ID: `{user.id}`", view=StaffAppDelete("staff")
        )
        await interaction.response.send_message(ephemeral=True)

    @discord.ui.button(
        label="Add to Channel", style=discord.ButtonStyle.grey, custom_id="addapplicant"
    )
    async def addapplicant(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await check_for_manager(interaction)
        user = interaction.guild.get_member(
            int(interaction.message.content.split("`")[1])
        )
        await interaction.channel.set_permissions(
            user, send_messages=True, read_messages=True, attach_files=True
        )
        embed = discord.Embed(
            title="You have been added to a ticket channel!",
            description="An administrator or manager has added you to this channel to discuss your **staff application** further. Thank you for your interest in joining the staff team!",
            color=discord.Color.yellow(),
        )
        button = Button(
            style=discord.ButtonStyle.link,
            label="View Ticket",
            url=f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}",
        )
        view = View()
        view.add_item(button)
        await user.send(embed=embed, view=view)
        msg = await interaction.channel.send(user.mention)
        await msg.delete()
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Applicant Added to This Channel",
                description=f"{user.mention} has been notified via DM if they have DMs open. They can now send messages, read previous discussions, and attach files. Use this space to discuss their application further before making a final decision.",
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )


class MediaAcceptRejectButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Accept", style=discord.ButtonStyle.green, custom_id="mediaaccept"
    )
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await check_for_manager(interaction)
        user = interaction.guild.get_member(
            int(interaction.message.content.split("`")[1])
        )
        embed = discord.Embed(
            title="You are accepted! :tada:",
            description="Congratulations! Your media application is accepted by the server owners!",
            color=0x00FF00,
        )
        await user.send(embed=embed)
        await interaction.message.edit(
            content=f"✅ Applicant ID: `{user.id}`", view=StaffAppDelete("media")
        )
        await interaction.response.send_message(ephemeral=True)

    @discord.ui.button(
        label="Reject", style=discord.ButtonStyle.red, custom_id="mediareject"
    )
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await check_for_manager(interaction)
        user = interaction.guild.get_member(
            int(interaction.message.content.split("`")[1])
        )
        embed = discord.Embed(
            title="You are rejected! :pensive:",
            description="Thank you so much for applying for the media position. Unfortunately, we aren't able to accept you at this time. \n\nWe are unable to give everyone who applies a specific reason for denial, but do note that the review process is a separate, manual process done one-by-one by our management team with the server owner. During the review process, there are a lot of factors that get considered for each application. \n\nDon't fret - you're always welcome to reapply in the future. In order to reapply, you'll have to wait 30 days from today. Applications sent from you during the waiting period will be ignored.\n\nWe really hope you're not too discouraged by the news, and remember; this decision in no way speaks to the value, joy, and belonging you bring to your community every day.",
            color=0xFF0000,
        )
        await user.send(embed=embed)
        await interaction.message.edit(
            content=f":x: Applicant ID: `{user.id}`", view=StaffAppDelete("media")
        )
        await interaction.response.send_message(ephemeral=True)

    @discord.ui.button(
        label="Add to Channel",
        style=discord.ButtonStyle.grey,
        custom_id="addapplicantmedia",
    )
    async def mediaaddapplicant(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await check_for_manager(interaction)
        user = interaction.guild.get_member(
            int(interaction.message.content.split("`")[1])
        )
        await interaction.channel.set_permissions(
            user, send_messages=True, read_messages=True, attach_files=True
        )
        embed = discord.Embed(
            title="You have been added to a ticket channel!",
            description="An administrator or manager has added you to this channel to discuss your **media application** further. Thank you for your interest in joining the media team!",
            color=discord.Color.yellow(),
        )
        button = Button(
            style=discord.ButtonStyle.link,
            label="View Ticket",
            url=f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}",
        )
        view = View()
        view.add_item(button)
        await user.send(embed=embed, view=view)
        msg = await interaction.channel.send(user.mention)
        await msg.delete()
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Applicant Added to This Channel",
                description=f"{user.mention} has been notified via DM if they have DMs open. They can now send messages, read previous discussions, and attach files. Use this space to discuss their application further before making a final decision.",
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )


class ApplyForStaff(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Staff Application",
        style=discord.ButtonStyle.grey,
        custom_id="staffapp",
        emoji="📝",
    )
    async def startapp(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        ref = db.reference("/Staff App")
        status = ref.get()
        for key, value in status.items():
            staffAppStatus = value["Status"]
        if staffAppStatus == "Closed":
            return await interaction.response.send_message(
                ":x: Staff application is currently **closed** for now. Stay tuned for announcements regarding staff applications in <#1136672659975975056>.",
                ephemeral=True,
            )

        ref = db.reference("/Staff App Cooldown")
        ticketcooldown = ref.get()
        for key, value in ticketcooldown.items():
            if value["User ID"] == interaction.user.id:
                LAST_CREATED = value["Timestamp"]
                if (
                    int(interaction.created_at.timestamp()) - int(LAST_CREATED)
                ) < 604800 and interaction.user.id not in [692254240290242601, 840972960793100309, 740750243808673895]:
                    return await interaction.response.send_message(
                        content=f"You are on a cooldown. Try again <t:{int(LAST_CREATED) + 604800}:R>",
                        ephemeral=True,
                    )
                db.reference("/Staff App Cooldown").child(key).delete()
                break

        try:
            embed = discord.Embed(
                title="MystiCraft Staff Application",
                description="Hello there! Thanks for applying for staff in our server. Please answer them as fully and accurately as possible.",
                color=discord.Color.blurple(),
            )
            await interaction.user.send(embed=embed)
            ableToDM = True
        except Exception:
            await interaction.response.send_message(
                "Please turn on Direct Messages to access the application.",
                ephemeral=True,
            )
            ableToDM = False

        if ableToDM:
            await interaction.response.send_message(
                ":envelope_with_arrow: Please proceed to your DMs to finish the application.",
                ephemeral=True,
            )
            cancelNotice = 'All answers will be kept confidential. Type "cancel" to stop the application.'

            def check(message):
                if (
                    message.content.lower() == "cancel"
                    and message.author == interaction.user
                    and isinstance(message.channel, discord.DMChannel)
                ):
                    raise Exception("Staff application cancelled")
                return message.author == interaction.user and isinstance(
                    message.channel, discord.DMChannel
                )

            embed = discord.Embed(
                description="""**Here are some of the requirements that you must fufill:**
      
- You must be able to speak in calls confidently.
- You must have a working microphone.
- You must be able to screen record and screenshot on your device.
- You must take responsibility for your actions 
- You must be **at least 14 years of age**.
- You must have a premium Minecraft account**

If you believe you are qualified for staff member, go ahead and answer the following questions. If not, you may type \"cancel\" to terminate your application. Your answers will not be saved.
""",
                color=discord.Color.blurple(),
            )
            await interaction.user.send(embed=embed)

            questions = [
                "What is your Minecraft IGN (In-game Name)?",
                "What is your Discord username and Discord ID?",
                "What is your age?",
                "What country do you live in and what is your timezone?",
                "Do you have a premium Minecraft account?",
                "How long have you been playing Minecraft?",
                "What is your favourite realm on MystiCraft?",
                "Do you have a working microphone, and are you able to screen share/screen record gameplay?",
                "Do you have previous staff experience? If so, Please list them.",
                "Do you have experience with screensharing tools (Ocean, Echo, Paladin, etc.)?",
                "Do you have experience with world editors like WorldEdit or WorldPainter?",
                "What is your greatest strength as a staff member?",
                "What are your weaknesses as a staff member?",
                "Explain what a good staff member is (50+ words).",
                "Why do you want to become a staff member on MystiCraft, and how many hours per week can you dedicate?",
                "Before we submit your application, are there anything else you would like us to know?"
            ]
            answers = []

            for question in questions:
                embed = discord.Embed(
                    title=f"Question #{questions.index(question)+1}",
                    description=question,
                    color=0xADD8E6,
                )
                embed.set_footer(text=cancelNotice)
                await interaction.user.send(embed=embed)
                answer = await interaction.client.wait_for("message", check=check)
                answer = answer.content
                answers.append(answer)

            embed = discord.Embed(
                title="Application Submitting...",
                description="Hang tight... your answers are being submitted... :coffee:",
                color=0xFFFF00,
            )
            waitmsg = await interaction.user.send(embed=embed)

            ref = db.reference("/Tickets")
            tickets = ref.get()
            found = False
            for key, value in tickets.items():
                if value["Server ID"] == interaction.guild.id:
                    CATEGORY_ID = value["Category ID"]
                    LOGCHANNEL_ID = value["Log Channel ID"]
                    found = True
                    break

            if not found:
                embed = discord.Embed(
                    title="Ticket not enabled!",
                    description=f"This server does not have a ticket category or a log channel. Please ask the server admin to use </ticket setup:1033188985587109910> to setup tickets!",
                    colour=0xFF0000,
                )
                embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
                return await interaction.followup.send(embed=embed, ephemeral=True)

            category = interaction.guild.get_channel(CATEGORY_ID)

            if interaction.guild.id == SUPPORT_SERVER_ID:
                category = interaction.guild.get_channel(STAFF_APPS_CATEGORY)
            chn = await interaction.guild.create_text_channel(
                f"{interaction.user.name}", category=category
            )
            await chn.edit(topic=f"Applicant ID: {interaction.user.id}")
            # Bad roles
            await chn.set_permissions(
                interaction.guild.default_role,
                send_messages=False,
                read_messages=False,
                attach_files=False,
            )
            await chn.set_permissions(
                interaction.guild.get_role(ADMIN_ROLE_ID), # ROLE
                send_messages=False,
                read_messages=False,
                attach_files=False,
            )
            await chn.set_permissions(
                interaction.guild.get_role(DEV_ROLE_ID),
                send_messages=False,
                read_messages=False,
                attach_files=False,
            )
            await chn.set_permissions(
                interaction.guild.get_role(SR_MOD_ROLE_ID),
                send_messages=False,
                read_messages=False,
                attach_files=False,
            )
            await chn.set_permissions(
                interaction.guild.get_role(MOD_ROLE_ID),
                send_messages=False,
                read_messages=False,
                attach_files=False,
            )
            await chn.set_permissions(
                interaction.guild.get_role(HELPER_ROLE_ID),
                send_messages=False,
                read_messages=False,
                attach_files=False,
            )
            log = interaction.guild.get_channel(1391586125839077447)
            embed = discord.Embed(
                title="Staff Application",
                description=f"{interaction.user.mention} submitted a new **staff** application <t:{int(chn.created_at.timestamp())}:R>!",
                color=discord.Colour.green(),
            )
            try:
                embed.set_author(
                    name=f"{interaction.user.name}",
                    icon_url=interaction.user.avatar.url,
                )
            except Exception:
                embed.set_author(name=f"{interaction.user.name}")
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            embed.set_footer(text=f"User ID: {interaction.user.id}")
            
            filename = f"./commands/Tickets/transcript/Staff_Application_{interaction.user.id}_{''.join(random.choices(string.ascii_letters + string.digits, k=10))}.txt"
            
            with open(filename, "w") as f:
                count = 0
                for answer in answers:
                    f.write(f"{count + 1}. {questions[count]}\n\n{answer}\n\n")
                    count += 1
                    
            view = View()
            button = Button(
                style=discord.ButtonStyle.link,
                label="View Application",
                url=f"https://discord.com/channels/{interaction.guild.id}/{chn.id}",
            )
            view.add_item(button)
            await log.send(file=discord.File(filename), embed=embed, view=view)
            try:
                os.remove(filename)
            except Exception:
                pass

            roles = interaction.user.roles
            roles.reverse()

            embed = discord.Embed(
                title=f"New STAFF Application",
                description=f"This ticket is not visible to the applicant.",
                color=discord.Colour.gold(),
            )
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            embed.add_field(
                name="User Mention", value=f"{interaction.user.mention}", inline=True
            )
            embed.add_field(name="User ID", value=f"{interaction.user.id}", inline=True)
            embed.add_field(
                name="Highest Role", value=f"{roles[0].mention}", inline=True
            )
            embed.add_field(
                name="Ticket Created",
                value=f"<t:{int(chn.created_at.timestamp())}:R>",
                inline=True,
            )
            embed.add_field(
                name="Server Joined",
                value=f"<t:{int(interaction.user.joined_at.timestamp())}:R>",
                inline=True,
            )
            embed.add_field(
                name="Account Created",
                value=f"<t:{int(interaction.user.created_at.timestamp())}:R>",
                inline=True,
            )
            await chn.send(f"**Applicant: {interaction.user.mention}**", embed=embed)

            count = 0
            for answer in answers:
                embed = discord.Embed(
                    description=f"**{count + 1}. {questions[count]}**```{answer}```",
                    color=0xFFFF00,
                )
                await chn.send(embed=embed)
                count += 1

            await chn.send(
                f"## Staff Application\nApplicant: {interaction.user.mention}\nApplicant ID: `{interaction.user.id}`",
                view=AcceptRejectButton(),
            )
            await waitmsg.delete()
            embed = discord.Embed(
                title="Application Submitted",
                description="All done! You will be notified shortly after our management team has finished reviewing your application! Thank you for applying, and stay tuned!",
                color=0x00FF00,
            )
            await interaction.user.send(embed=embed)

            data = {
                interaction.guild.name: {
                    "User ID": interaction.user.id,
                    "Timestamp": int(interaction.created_at.timestamp()),
                }
            }
            ref = db.reference("/Staff App Cooldown")
            for key, value in data.items():
                ref.push().set(value)

    @discord.ui.button(
        label="Media Application",
        style=discord.ButtonStyle.grey,
        custom_id="mediaapp",
        emoji="📝",
    )
    async def mediaapp(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        ref = db.reference("/Staff App")
        status = ref.get()
        for key, value in status.items():
            staffAppStatus = value["Status"]
        if staffAppStatus == "Closed":
            return await interaction.response.send_message(
                ":x: Media application is currently **closed** for now. Stay tuned for announcements regarding media applications in <#1136672659975975056>.",
                ephemeral=True,
            )

        ref = db.reference("/Media App Cooldown")
        ticketcooldown = ref.get()
        for key, value in ticketcooldown.items():
            if value["User ID"] == interaction.user.id:
                LAST_CREATED = value["Timestamp"]
                if (
                    int(interaction.created_at.timestamp()) - int(LAST_CREATED)
                ) < 604800 and interaction.user.id not in [692254240290242601, 840972960793100309, 740750243808673895]:
                    return await interaction.response.send_message(
                        content=f"You are on a cooldown. Try again <t:{int(LAST_CREATED) + 604800}:R>",
                        ephemeral=True,
                    )
                db.reference("/Media App Cooldown").child(key).delete()
                break

        try:
            embed = discord.Embed(
                title="MystiCraft Media Application",
                description="Hello there! Thanks for applying for media position in our server.",
                color=discord.Color.blurple(),
            )
            await interaction.user.send(embed=embed)
            ableToDM = True
        except Exception:
            await interaction.response.send_message(
                "Please turn on Direct Messages to access the application.",
                ephemeral=True,
            )
            ableToDM = False

        if ableToDM:
            await interaction.response.send_message(
                ":envelope_with_arrow: Please proceed to your DMs to finish the application.",
                ephemeral=True,
            )
            cancelNotice = 'All answers will be kept confidential. Type "cancel" to stop the application.'

            def check(message):
                if (
                    message.content.lower() == "cancel"
                    and message.author == interaction.user
                    and isinstance(message.channel, discord.DMChannel)
                ):
                    raise Exception()
                return message.author == interaction.user and isinstance(
                    message.channel, discord.DMChannel
                )

            embed = discord.Embed(
                description="""Please answer the following questions to complete your application. If you wish to terminate your application, you may type \"cancel\". Your answers will not be saved.\n\n**You may paste in links of websites/images in your application, but DO NOT upload directly on Discord and send it.**
""",
                color=discord.Color.blurple(),
            )
            await interaction.user.send(embed=embed)

            questions = [
                "What is your name?",
                "What is your discord username? (*example: ninjamc*)",
                "What is your discord id? (*example: 1084715109865246771*)",
                "On which platform, are you most comfortable to make videos on? (*example: YouTube, Twitch etc.*)",
                "What do you appreciate about our Minecraft community server, and what motivated you to apply for a media role here?",
                "How much time can you commit to creating and managing media content for the server on a weekly basis?",
                "Mention the amount of initial audience base you currently have.",
                "Please give us a rough idea of average views per long and short form video uploaded.",
                "Can you assure us that your uploads would benefit our community positively?",
                "You abide by all the rules, do you?",
                "Can you provide us with a link of the platform channel/profile you will be uploading content on?",
                "Anything else you would like us to know?",
            ]

            answers = []

            for question in questions:
                embed = discord.Embed(
                    title=f"Question #{questions.index(question)+1}",
                    description=question,
                    color=0xADD8E6,
                )
                embed.set_footer(text=cancelNotice)
                await interaction.user.send(embed=embed)
                answer = await interaction.client.wait_for("message", check=check)
                answer = answer.content
                answers.append(answer)

            embed = discord.Embed(
                title="Application Submitting...",
                description="Hang tight... your answers are being submitted... :coffee:",
                color=0xFFFF00,
            )
            waitmsg = await interaction.user.send(embed=embed)

            ref = db.reference("/Tickets")
            tickets = ref.get()
            found = False
            for key, value in tickets.items():
                if value["Server ID"] == interaction.guild.id:
                    CATEGORY_ID = value["Category ID"]
                    LOGCHANNEL_ID = value["Log Channel ID"]
                    found = True
                    break

            if not found:
                embed = discord.Embed(
                    title="Ticket not enabled!",
                    description=f"This server does not have a ticket category or a log channel. Please ask the server admin to use </ticket setup:1033188985587109910> to setup tickets!",
                    colour=0xFF0000,
                )
                embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
                return await interaction.followup.send(embed=embed, ephemeral=True)

            category = interaction.guild.get_channel(CATEGORY_ID)

            if interaction.guild.id == SUPPORT_SERVER_ID:
                category = interaction.guild.get_channel(MEDIA_APPS_CATEGORY)
            chn = await interaction.guild.create_text_channel(
                f"{interaction.user.name}", category=category
            )
            await chn.edit(topic=f"Applicant ID: {interaction.user.id}")
            # Bad roles
            await chn.set_permissions(
                interaction.guild.default_role,
                send_messages=False,
                read_messages=False,
                attach_files=False,
            )
            await chn.set_permissions(
                interaction.guild.get_role(ADMIN_ROLE_ID), # ROLE
                send_messages=False,
                read_messages=False,
                attach_files=False,
            )
            await chn.set_permissions(
                interaction.guild.get_role(DEV_ROLE_ID),
                send_messages=False,
                read_messages=False,
                attach_files=False,
            )
            await chn.set_permissions(
                interaction.guild.get_role(SR_MOD_ROLE_ID),
                send_messages=False,
                read_messages=False,
                attach_files=False,
            )
            await chn.set_permissions(
                interaction.guild.get_role(MOD_ROLE_ID),
                send_messages=False,
                read_messages=False,
                attach_files=False,
            )
            await chn.set_permissions(
                interaction.guild.get_role(HELPER_ROLE_ID),
                send_messages=False,
                read_messages=False,
                attach_files=False,
            )
            log = interaction.guild.get_channel(1391586125839077447)
            embed = discord.Embed(
                title="Media Application",
                description=f"{interaction.user.mention} submitted a new **media** application <t:{int(chn.created_at.timestamp())}:R>!",
                color=discord.Colour.green(),
            )
            try:
                embed.set_author(
                    name=f"{interaction.user.name}",
                    icon_url=interaction.user.avatar.url,
                )
            except Exception:
                embed.set_author(name=f"{interaction.user.name}")
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            embed.set_footer(text=f"User ID: {interaction.user.id}")
            
            filename = f"./commands/Tickets/transcript/Media_Application_{interaction.user.id}_{''.join(random.choices(string.ascii_letters + string.digits, k=10))}.txt"
            
            with open(filename, "w") as f:
                count = 0
                for answer in answers:
                    f.write(f"{count + 1}. {questions[count]}\n\n{answer}\n\n")
                    count += 1
                    
            view = View()
            button = Button(
                style=discord.ButtonStyle.link,
                label="View Application",
                url=f"https://discord.com/channels/{interaction.guild.id}/{chn.id}",
            )
            view.add_item(button)
            await log.send(file=discord.File(filename), embed=embed, view=view)
            try:
                os.remove(filename)
            except Exception:
                pass

            roles = interaction.user.roles
            roles.reverse()

            embed = discord.Embed(
                title=f"New MEDIA Application",
                description=f"This ticket is not visible to the applicant.",
                color=discord.Colour.gold(),
            )
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            embed.add_field(
                name="User Mention", value=f"{interaction.user.mention}", inline=True
            )
            embed.add_field(name="User ID", value=f"{interaction.user.id}", inline=True)
            embed.add_field(
                name="Highest Role", value=f"{roles[0].mention}", inline=True
            )
            embed.add_field(
                name="Ticket Created",
                value=f"<t:{int(chn.created_at.timestamp())}:R>",
                inline=True,
            )
            embed.add_field(
                name="Server Joined",
                value=f"<t:{int(interaction.user.joined_at.timestamp())}:R>",
                inline=True,
            )
            embed.add_field(
                name="Account Created",
                value=f"<t:{int(interaction.user.created_at.timestamp())}:R>",
                inline=True,
            )
            await chn.send(f"**Applicant: {interaction.user.mention}**", embed=embed)

            count = 0
            for answer in answers:
                embed = discord.Embed(
                    description=f"**{count + 1}. {questions[count]}**```{answer}```",
                    color=0xFFFF00,
                )
                await chn.send(embed=embed)
                count += 1

            await chn.send(
                f"## Media Application\nApplicant: {interaction.user.mention}\nApplicant ID: `{interaction.user.id}`",
                view=MediaAcceptRejectButton(),
            )
            embed = discord.Embed(
                title="Application Submitted",
                description="All done! You will be notified shortly after our management team has finished reviewing your application! Thank you for applying, and stay tuned!",
                color=0x00FF00,
            )
            await waitmsg.delete()
            await interaction.user.send(embed=embed)

            data = {
                interaction.guild.name: {
                    "User ID": interaction.user.id,
                    "Timestamp": int(interaction.created_at.timestamp()),
                }
            }
            ref = db.reference("/Media App Cooldown")
            for key, value in data.items():
                ref.push().set(value)


class StaffRoaster(commands.Cog):
    def __init__(self, bot):
        self.client = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.client.user or message.author.bot == True:
            return

        if message.guild.id == 775815873775665173 and message.content == "m!staff":
            roles = [
                753869940162953357,
                1000968269836058694,
                748840161240023040,
                748778830910586970,
                828624806839844965,
                814390209034321920,
            ]
            msg = ""

            for roleID in roles:
                role = message.guild.get_role(roleID)
                msg = f"{msg}\n{role.mention} ({len(role.members)})\n"
                for member in role.members:
                    msg = f"{msg}» {member.mention} `({member.id})`\n"

            embed = discord.Embed(
                title="Staff Roaster", description=msg, colour=0x5A76D8
            )

            embed.set_image(
                url="https://media.discordapp.net/attachments/837554879194202172/932930016717721620/StaffRoaster.jpg"
            )
            await message.channel.send(embed=embed)

        elif message.guild.id == 775815873775665173 and message.content == "m!staffapp":
            embed = discord.Embed(
                title="Join Our Team in MystiCraft",
                description="If you think you are worthy for joining our team, you can start applying by clicking the buttons below (make sure your DMs are open).\n\n",
                color=0xFFA500,
            )
            await message.channel.send(embed=embed, view=ApplyForStaff())


class TicketQuestionsModal(discord.ui.Modal, title="Ticket Information"):
    def __init__(self, category: str):
        super().__init__()
        self.category = category
        questions = {
            # Support Server
            "General Support": [
                ("IGN (case-sensitive)", "What is your in-game name?", True),
                ("Platform", "What platform are you on?", True),
                ("Issue", "Describe your issue in detail", True),
            ],
            "Billing Support": [
                ("IGN (case-sensitive)", "What is your in-game name?", True),
                ("Item", "What did you purchase?", True),
                ("Transaction ID", "Transaction ID/Email", True),
            ],
            "Appeals": [
                ("IGN (case-sensitive)", "What is your in-game name?", True),
                ("Punishment ID", "What is the punishment ID (if known)?", False),
                ("Punishment Reason", "Why were your punished? Was it fair?", True),
                ("Appeal Reason", "Why should we remove your punishment?", True),
            ],
            "Player Reports": [
                ("IGN (case-sensitive)", "What is your in-game name?", True),
                ("Offender", "Offending player's in-game name", True),
                ("Reason", "What did they do?", True),
                ("Proof", "Links to screenshots/videos (required)", True),
            ],
            "Staff Reports": [
                ("Offender", "Who are you reporting?", True),
                ("Reason", "What did they do?", True),
                ("Proof", "Links to screenshots/videos (required)", True),
            ],
            "Bug Reports": [
                ("IGN (case-sensitive)", "What is your in-game name?", True),
                ("Bug", "Describe the bug and how to reproduce it", True),
                ("Media", "Links to screenshots/videos (if any)", False),
            ],
            # Tierlist Server
            "General Support Tierlist": [
                ("Issue", "Describe your issue in detail", True),
            ],
            "Tester Application Tierlist": [
                ("Gamemode", "Which gamemode(s) are you applying for?", True),
                ("Account Status", "Are you using a cracked/premium account?", True),
            ],
            "High Testing Tierlist": [
                ("Gamemode", "Which gamemode are you testing? Enter 1 only.", True),
            ],
            "Tier Migration Tierlist": [
                ("Server", "Which tierlist are you migrating from?", True),
                ("Result Message", "Share the result link, or forward message", False),
            ],
            "Staff Application Tierlist": [
                ("Age", "How old are you?", True),
                ("Country & Timezone", "Where do you live? Timezone?", True),
                ("Account Status", "Are you using a cracked/premium account?", True),
                ("Staff Experience", "List your previous staff experience", True),
                ("Hours Per Week", "How many hours per week can you dedicate?", True),
            ],
        }
        
        for field in questions.get(category, []):
            self.add_item(discord.ui.TextInput(
                label=field[1],
                placeholder=field[0],
                required=field[2],
                custom_id=field[0]
            ))

    async def on_submit(self, interaction: discord.Interaction):
        self.answers = {item.custom_id: item.value for item in self.children}
        self.on_submit_interaction = interaction
        await interaction.response.defer(ephemeral=True, thinking=True)


class Select(discord.ui.Select):
    def __init__(self, placeholder, options):
        # options=options
        super().__init__(
            placeholder=placeholder,
            max_values=1,
            min_values=1,
            options=options,
            custom_id="ticketcreation",
        )

    async def callback(self, interaction: discord.Interaction):

        selectedValue = self.values[0]
        embed = discord.Embed(
            title="Confirm Ticket",
            description=f"Are you sure you want to make a ticket about **{selectedValue}**?",
            colour=0x4F545B,
        )
        embed.add_field(name="<:warn:1459986909911842846> Review These Guidelines First", value="-# - Be respectful and civil. **Rudeness or impatience won't speed things up.**\n-# - **You are forbidden to ping any staff.** They will help you as soon as they're available.")
        try:
            embed.set_author(
                name=interaction.user.name, icon_url=interaction.user.avatar.url
            )
        except Exception:
            embed.set_author(name=interaction.user.name)
        embed.set_footer(
            icon_url=interaction.guild.icon.url,
            text=f"{interaction.guild.name} • #{interaction.channel.name}",
        )
        await interaction.response.send_message(
            embed=embed, view=CreateTicketButtonView(), ephemeral=True
        )


class SelectView(discord.ui.View):
    def __init__(self, placeholder=None, options=None, *, timeout=None):
        super().__init__(timeout=timeout)
        self.add_item(Select(placeholder, options))


class CreateTicketButton(discord.ui.Button):
    def __init__(self, title, emoji, color):
        super().__init__(label=title, emoji=emoji, style=color, custom_id="create")

    async def callback(self, interaction: discord.Interaction):
        

        try:
            embed = interaction.message.embeds[0]
            x = f"({embed.description.split('**')[1]})"
            z = embed.description.split('**')[1]
        except Exception:
            x = " "
            z = " "
        
        # Determine ticket category for cooldown
        if "appeal" in x.lower():
            ticket_category = "appeal"
        elif "password" in x.lower():
            ticket_category = "password_reset"
        elif "high testing" in x.lower():
            ticket_category = "high_testing"
        elif "staff application" in x.lower():
            ticket_category = "staff_app_tierlist"
        else:
            ticket_category = "normal"
        
        cooldown_ref = db.reference(f"/Ticket Cooldown/{interaction.user.id}/{ticket_category}")
        
        ref = db.reference("/Tickets")
        tickets = ref.get()
        found = False
        for key, value in tickets.items():
            if value["Server ID"] == interaction.guild.id:
                CATEGORY_ID = value["Category ID"]
                LOGCHANNEL_ID = value["Log Channel ID"]
                found = True
                break

        if not found:
            embed = discord.Embed(
                title="Ticket not enabled!",
                description=f"This server does not have a ticket category or a log channel. Please ask the server admin to use </ticket setup:1033188985587109910> to setup tickets!",
                colour=0xFF0000,
            )
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        category = interaction.guild.get_channel(CATEGORY_ID)

        for channel in category.channels:
            if get_ticket_owner_id(channel) == interaction.user.id:
                return await interaction.response.send_message(
                    content=f"You already had your ticket created at <#{channel.id}>.",
                    ephemeral=True,
                )
                
        blacklist_ref = db.reference(f"/Ticket Blacklist/{interaction.user.id}").get()
        if blacklist_ref:
            await interaction.response.send_message(f"<:no:1036810470860013639> You are blacklisted from creating tickets.", ephemeral=True)
            return

        # Check cooldown for the specific category
        last_ts = cooldown_ref.get()
        current_ts = int(interaction.created_at.timestamp())
        if last_ts:
            time_diff = current_ts - last_ts
            cooldown_duration = TICKET_COOLDOWNS[ticket_category]
            if time_diff < cooldown_duration and interaction.user.id not in [692254240290242601, 840972960793100309, 740750243808673895]:
                next_time = last_ts + cooldown_duration
                if ticket_category == "appeal":
                    msg = f"You can only create a new appeal ticket every 14 days. Try again <t:{next_time}:R>"
                elif ticket_category == "password_reset":
                    msg = f"You can only create a password reset ticket every 7 days. Try again <t:{next_time}:R>"
                elif ticket_category == "high_testing":
                    msg = f"You can only create a high tier testing ticket every 30 days. Try again <t:{next_time}:R>"
                elif ticket_category == "staff_app_tierlist":
                    msg = f"You can only create a tierlist staff application ticket every 30 days. Try again <t:{next_time}:R>"
                else:
                    msg = f"You are on a cooldown. Try again <t:{next_time}:R>"
                return await interaction.response.send_message(content=msg, ephemeral=True)
                
        categories = []
        blacklisted_roles = None
        
        categories = []
        blacklisted_roles = None
        if interaction.guild.id == SUPPORT_SERVER_ID:
            await interaction.response.defer(ephemeral=True, thinking=True)

            if "question" in x.lower():
                category_id = SERVER_QUESTIONS_CATEGORY_ID
            elif "password" in x.lower():
                category_id = PASSWORD_RESET_CATEGORY_ID
            elif "billing" in x.lower():
                category_id = BILLING_SUPPORT_CATEGORY_ID
            elif "appeal" in x.lower():
                category_id = APPEAL_CATEGORY_ID
            elif "player" in x.lower():
                category_id = PLAYER_REPORT_CATEGORY_ID
            elif "bug" in x.lower():
                category_id = BUG_REPORT_CATEGORY_ID
            elif "staff" in x.lower():
                category_id = STAFF_REPORT_CATEGORY_ID
            else:
                category_id = CATEGORY_ID

            categories = [SERVER_QUESTIONS_CATEGORY_ID, PASSWORD_RESET_CATEGORY_ID, BILLING_SUPPORT_CATEGORY_ID, APPEAL_CATEGORY_ID, PLAYER_REPORT_CATEGORY_ID, BUG_REPORT_CATEGORY_ID, STAFF_REPORT_CATEGORY_ID]
            category = interaction.guild.get_channel(category_id)
            chn = await interaction.guild.create_text_channel(
                f"⭕️-{interaction.user.name}", category=category
            )
            ping_role = None
            open_tickets = 0
            for cat_id in categories:
                category = interaction.guild.get_channel(cat_id)
                open_tickets += len([c for c in category.channels if isinstance(c, discord.TextChannel)])
            answerEmbed = None
            correct_interaction = interaction
            
        elif interaction.guild.id == TIERLIST_SERVER_ID: # Tierlist
            if not "support" in x.lower(): # Must link account for non-support tickets
                if LINKED_ROLE_ID not in [role.id for role in interaction.user.roles] and interaction.user.id != 692254240290242601:
                    return await interaction.response.send_message(
                        embed=discord.Embed(
                            title="<:warn:1459986909911842846> **Account Linking Required for Non-Support Tickets**",
                            description=f"> To create a **{z}** ticket, you must follow the instructions in <#1460525451368861818> to get linked. Once completed, you will automatically receive the <@&{LINKED_ROLE_ID}> role and be able to create this type of ticket.",
                            color=discord.Colour.red(),
                        ).set_footer(text="'General Support' tickets do not require account linking."),
                        ephemeral=True,
                    )
            
            if "tester application" in x.lower():
                allowed = False
                for role in interaction.user.roles:
                    name = role.name
                    if "[" in name or "]" in name:
                        continue
                    if any(tier in name for tier in ["LT3", "HT3", "LT2", "HT2"]):
                        allowed = True
                        break

                if not allowed:
                    return await interaction.response.send_message(
                        content="❌ You must have at least a LT3+ gamemode role to create this type of ticket.",
                        ephemeral=True,
                    )
            
            if "high testing" in x.lower():
                allowed = False
                for role in interaction.user.roles:
                    name = role.name
                    if "[" in name or "]" in name:
                        continue
                    if any(tier in name for tier in ["HT3", "LT2", "HT2"]):
                        allowed = True
                        break

                if not allowed:
                    return await interaction.response.send_message(
                        content="❌ You must have at least a HT3+ gamemode role to create this type of ticket.\nIf you have LT3 and want to test for HT3, head over to <#1467965604257595442> instead.",
                        ephemeral=True,
                    )
                
            modal = TicketQuestionsModal(f"{z} Tierlist")
            await interaction.response.send_modal(modal)
            await modal.wait()
            if "support" in x.lower():
                category_id = GENERAL_SUPPORT_TIERLIST_CATEGORY_ID 
            elif "tester application" in x.lower():
                category_id = TESTER_APPLICATION_TIERLIST_CATEGORY_ID 
            elif "high testing" in x.lower():
                category_id = HIGH_TESTING_TIERLIST_CATEGORY_ID  
            elif "tier migration" in x.lower():
                category_id = TIER_MIGRATION_TIERLIST_CATEGORY_ID 
            elif "staff application" in x.lower():
                category_id = STAFF_APPLICATION_TIERLIST_CATEGORY_ID 

            categories = [GENERAL_SUPPORT_TIERLIST_CATEGORY_ID, TESTER_APPLICATION_TIERLIST_CATEGORY_ID, HIGH_TESTING_TIERLIST_CATEGORY_ID, TIER_MIGRATION_TIERLIST_CATEGORY_ID, STAFF_APPLICATION_TIERLIST_CATEGORY_ID]
            category = interaction.guild.get_channel(category_id)
            chn = await interaction.guild.create_text_channel(
                f"⭕️-{interaction.user.name}", category=category
            )
            ping_role = interaction.guild.get_role(1460537858388398121)  # Tierlist support ping role
            open_tickets = 0
            for cat_id in categories:
                category = interaction.guild.get_channel(cat_id)
                open_tickets += len([c for c in category.channels if isinstance(c, discord.TextChannel)])
            answerEmbed = discord.Embed(color=0x22aef5)
            for key, value in modal.answers.items():
                answerEmbed.add_field(name=key, value=value, inline=False)
            answerEmbed.set_footer(text="You can add followup information in this channel.")
            correct_interaction = modal.on_submit_interaction
                
        await chn.edit(topic=interaction.user.id)
        await chn.set_permissions(interaction.user, send_messages=interaction.guild.id != SUPPORT_SERVER_ID, read_messages=True, attach_files=True)
        
        if blacklisted_roles:
            for roleID in blacklisted_roles:
                await chn.set_permissions(
                    interaction.guild.get_role(roleID), send_messages=False, read_messages=False, attach_files=False
                )

        log = interaction.guild.get_channel(LOGCHANNEL_ID)
        embed = discord.Embed(
            title="Ticket created",
            description=f"**{interaction.user.mention} created a new ticket <t:{int(chn.created_at.timestamp())}:R>!**",
            color=discord.Colour.green(),
        )
        try:
            embed.set_author(
                name=f"{interaction.user.name}", icon_url=interaction.user.avatar.url
            )
        except Exception:
            embed.set_author(name=f"{interaction.user.name}")
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        embed.set_footer(text=f"User ID: {interaction.user.id}")

        button = Button(
            style=discord.ButtonStyle.link,
            label="View Ticket",
            url=f"https://discord.com/channels/{interaction.guild.id}/{chn.id}",
        )
        view = View()
        view.add_item(button)
        await log.send(embed=embed, view=view)

        roles = interaction.user.roles
        roles.reverse()

        initial_embed = discord.Embed(
            title=z,
            description=f"> Thank you for contacting the {interaction.guild.name} team.\n> Please describe your issue and wait for a response.\n\n-# There are currently **`{open_tickets}`** tickets open. Please be patient.\n-# <:warn:1459986909911842846> **DO NOT ping any staff** as it will only delay our response.",
            color=0x22aef5
        )
        initial_embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        initial_embed.add_field(
            name="User Mention", value=f"{interaction.user.mention}", inline=True
        )
        initial_embed.add_field(name="User ID", value=f"{interaction.user.id}", inline=True)
        initial_embed.add_field(name="Highest Role", value=f"{roles[0].mention}", inline=True)
        initial_embed.add_field(
            name="Ticket Created",
            value=f"<t:{int(chn.created_at.timestamp())}:R>",
            inline=True,
        )
        initial_embed.add_field(
            name="Server Joined",
            value=f"<t:{int(interaction.user.joined_at.timestamp())}:R>",
            inline=True,
        )
        initial_embed.add_field(
            name="Account Created",
            value=f"<t:{int(interaction.user.created_at.timestamp())}:R>",
            inline=True,
        )
        if interaction.guild.id == TIERLIST_SERVER_ID:
            linked_ign = "None"
            try:
                async with interaction.client.tllink_pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute("SHOW TABLES")
                        tb_res = await cursor.fetchone()
                        link_table = tb_res[0] if tb_res else "mystilinking"
                        await cursor.execute(f"SELECT player_name FROM {link_table} WHERE discord_id = %s", (str(interaction.user.id),))
                        link_res = await cursor.fetchone()
                        if link_res:
                            linked_ign = link_res[0]
            except Exception as e:
                print(f"Error fetching linked IGN for thread: {e}")

            async with interaction.client.tlresults_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT region FROM tlresults WHERE player_user_id = %s ORDER BY timestamp DESC LIMIT 1", (interaction.user.id,))
                    result = await cursor.fetchone()
                    
            recorded_region = result[0] if result else "Unknown"

            current_rank_roles = []
            for role in interaction.user.roles:
                if any(tier in role.name for tier in ["HT", "LT"]):
                    current_rank_roles.append(role)

            initial_embed.add_field(name="Linked IGN", value=f"[{linked_ign}](https://tierlist.mysticraft.xyz/?player={linked_ign})" if linked_ign != "None" else "<:no:1036810470860013639> Not Linked", inline=True)
            initial_embed.add_field(name="Region", value=recorded_region, inline=True)
            initial_embed.add_field(name="Current Tiers", value=", ".join([role.mention for role in current_rank_roles]) if current_rank_roles else "None", inline=True)
        elif interaction.guild.id == SUPPORT_SERVER_ID:
            initial_embed.set_footer(text="You cannot type in tickets before answering all the questions first.")

        if answerEmbed is None:
            await chn.send(
                f"**{interaction.user.mention}, welcome!** {('||' + ping_role.mention + '||') if ping_role is not None else ''}",
                embed=initial_embed,
                view=CloseTicketButton() if interaction.guild.id != SUPPORT_SERVER_ID else None
            )
        else:
            await chn.send(
                f"**{interaction.user.mention}, welcome!** {('||' + ping_role.mention + '||') if ping_role is not None else ''}",
                embed=initial_embed,
            )
            await chn.send(embed=answerEmbed, view=CloseTicketButton())
            
        if interaction.guild.id == SUPPORT_SERVER_ID:
            await start_support_tree(interaction, chn, x, z)
                
        await correct_interaction.followup.send(
            content=f"Ticket created at <#{chn.id}>.",
            ephemeral=True,
        )
        
        # Set cooldown for this ticket category
        cooldown_ref.set(int(interaction.created_at.timestamp()))

            
class AppealModal(discord.ui.Modal):
    def __init__(self, ign, title, user):
        self.user = user
        self.shorttitle = title
        super().__init__(title=f"Appeal {self.shorttitle} Modal")
        self.ign = ign
        
        self.ignfield = discord.ui.TextInput(label="In-game name", style=discord.TextStyle.short, placeholder="", max_length=256, required=True, default=self.ign)
        self.add_item(self.ignfield)
        
        self.punishment = discord.ui.TextInput(label="Original Punishment", style=discord.TextStyle.short, placeholder="", max_length=256, required=True)
        self.add_item(self.punishment)
        
        self.determination = discord.ui.TextInput(label="Determination (Add Short Details)", style=discord.TextStyle.short, placeholder="", max_length=256, required=True, default=f"{self.shorttitle}ed")
        self.add_item(self.determination)
        
        self.info = discord.ui.TextInput(label="Additional Info", style=discord.TextStyle.paragraph, placeholder=f"Reason for {self.shorttitle} & Notes", max_length=2000, required=True)
        self.add_item(self.info)

    async def on_submit(self, interaction: discord.Interaction):
        # Get input values correctly using .value
        ign = self.ignfield.value.strip()
        punishment = self.punishment.value.strip()
        determination = self.determination.value.strip()
        info = self.info.value.strip()
        APPEAL_LOG_CHANNEL = interaction.client.get_channel(1286031597845614625)
        embed = discord.Embed(
            title=f"Appeal {self.shorttitle}ed",
            description=f"**Staff:** {interaction.user.mention}\n**IGN**: `{ign}`\n**Punishment**: {punishment}\n**Determination**: {determination}\n**Info**: {info}",
            color=0xFF0000 if self.shorttitle == "Reject" else 0x00FF00
        )
        embed.set_footer(text=f"Ticket Channel ID: {interaction.channel.id}")
        msg = await APPEAL_LOG_CHANNEL.send(embed=embed)
        await interaction.response.send_message(content=f"Message sent in {msg.jump_url}", embed=embed, ephemeral=True)
        final = discord.Embed(
            description=f"Appeal {self.shorttitle}ed{'. You may reappeal in 14 days or wait out your punishment.' if self.shorttitle == 'Reject' else ''}", 
            color=0xFF0000 if self.shorttitle == 'Reject' else 0x00FF00
        )
        await interaction.channel.send(embed=final)
        await self.user.send(embed=final)
        

def sanitize_firebase_key(key: str) -> str:
    key = re.sub(r"[.$#[\]/]", "", key)
    if key.startswith("."):
        key = key[1:]
    return key


def get_ticket_owner_id(channel):
    try:
        if channel.topic and channel.topic.strip().isdigit():
            return int(channel.topic.strip())
        match = re.search(r"(\d{6,})", str(channel.topic or ""))
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return None


def is_ticket_staff_whitelisted(guild: discord.Guild, member: discord.Member) -> bool:
    if guild.id == SUPPORT_SERVER_ID:
        allowed_role_ids = {
            OWNER_ROLE_ID,
            CO_OWNER_ROLE_ID,
            EXECUTIVE_ROLE_ID,
            MANAGER_ROLE_ID,
            ADMIN_ROLE_ID,
            DEV_ROLE_ID,
            SR_MOD_ROLE_ID,
            MOD_ROLE_ID,
            HELPER_ROLE_ID,
        }
    elif guild.id == TIERLIST_SERVER_ID:
        allowed_role_ids = {
            TIERLIST_OWNER_ROLE_ID,
            TIERLIST_MANAGER_ROLE_ID,
            TIERLIST_ADMIN_ROLE_ID,
            TIERLIST_REGULATOR_ROLE_ID,
            TIERLIST_STAFF_ROLE_ID,
        }
    else:
        return False

    return any(role.id in allowed_role_ids for role in member.roles)


class SupportActionButton(discord.ui.Button):
    def __init__(self, *, label: str, custom_id: str,
                 style: discord.ButtonStyle = discord.ButtonStyle.grey,
                 emoji=None, opens_modal: bool = False):
        super().__init__(label=label, style=style, emoji=emoji, custom_id=custom_id)
        # opens_modal is only used at construction time to build the view;
        # at persistence-reload time we look it up from the registry instead.
        self._opens_modal = opens_modal

    async def callback(self, interaction: discord.Interaction):
        entry = SUPPORT_HANDLER_REGISTRY.get(self.custom_id)
        if not entry:
            return
        handler, opens_modal = entry

        if opens_modal:
            await handler(interaction)
        else:
            # Collapse the view to show only the selected button
            selected_view = discord.ui.View()
            selected_view.add_item(discord.ui.Button(
                label=self.label, style=self.style, emoji=self.emoji, disabled=True
            ))
            try:
                await interaction.response.edit_message(view=selected_view)
            except Exception:
                try:
                    await interaction.response.defer(ephemeral=True, thinking=False)
                    await interaction.message.edit(view=selected_view)
                except Exception:
                    pass
            await handler(interaction)


class SupportChoiceView(discord.ui.View):
    def __init__(self, buttons=None):
        super().__init__(timeout=None)   # timeout=None is required for persistence
        if buttons:
            for button in buttons:
                self.add_item(button)


class SupportFormModal(discord.ui.Modal):
    def __init__(self, title: str, fields, submit_handler, source_message: discord.Message = None):
        super().__init__(title=title)
        self.submit_handler = submit_handler
        self.source_message = source_message

        for field in fields:
            label, placeholder, required = field
            item = discord.ui.TextInput(
                label=label,
                placeholder=placeholder,
                required=required,
                max_length=2000,
            )
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        answers = {}
        for item in self.children:
            if isinstance(item, discord.ui.TextInput):
                answers[item.label] = item.value.strip()
        await self.submit_handler(interaction, answers)
        if self.source_message is not None:
            try:
                await self.source_message.edit(view=discord.ui.View())
            except Exception:
                pass


async def post_support_outcome(
    interaction,
    *,
    title: str,
    description: str,
    color=0x4F9EF5,
    view=None,
    fields=None,
    unlock: bool = False,
    ping_staff: bool = False,
    ping_everyone: bool = False,
):
    channel = interaction.channel
    owner_id = get_ticket_owner_id(channel)
    owner = interaction.guild.get_member(owner_id) if owner_id else interaction.user
    ping_role = interaction.guild.get_role(PING_ROLE_ID) if ping_staff else None

    embed = discord.Embed(title=title, description=description, color=color)
    if fields:
        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

    if view is None:
        view = CloseTicketButton()

    if unlock and owner is not None:
        await channel.set_permissions(owner, send_messages=True, read_messages=True, attach_files=True)
        embed.set_footer(text="You can now type in the ticket and send any followup information")
    
    content = "@everyone" if ping_everyone else (ping_role.mention if ping_role is not None else None)
    await channel.send(content=content, embed=embed, view=view)



async def post_support_prompt(
    interaction,
    *,
    title: str,
    description: str,
    view,
    color=0x4F9EF5,
):
    embed = discord.Embed(title=title, description=description, color=color)
    if _LINK_INSTRUCTIONS in description:
        embed.set_image(url="https://media.discordapp.net/attachments/741540685852835871/1500668562178572428/Screenshot_20260503-182038.Discord.png?ex=69f94602&is=69f7f482&hm=6d563648ab50f0c3b00dcae99d02b55f6b5cbece7c2ef3131ef9b4ae2a38a136&=")
        embed.set_footer(text="DM the code to one of these bots depending on which gamemode you use /link in")
    await interaction.channel.send(embed=embed, view=view)

async def _st_owner_only(interaction: discord.Interaction) -> bool:
    owner_id = get_ticket_owner_id(interaction.channel)
    if owner_id is not None and interaction.user.id != owner_id:
        msg = "Only the ticket opener can use these buttons."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
        return False
    return True


async def _st_send_close(interaction, title: str, description: str, *, color: int = 0xFF0000):
    await post_support_outcome(
        interaction, title=title, description=description,
        color=color, view=CloseTicketButton(), unlock=False, ping_staff=False,
    )


async def _st_send_final(interaction, title: str, description: str, data: dict, *, view=None, color: int = 0x4F9EF5, ping_everyone: bool = False):
    await post_support_outcome(
        interaction, title=title, description=description,
        color=color, view=view or CloseTicketButton(),
        fields=list(data.items()) if data is not None else None, unlock=True, ping_staff=not ping_everyone, ping_everyone=ping_everyone,
    )


async def _st_send_instructions(interaction, title: str, description: str, view: discord.ui.View):
    close_view = CloseTicketButton()
    for item in close_view.children:
        view.add_item(item)
    await post_support_prompt(interaction, title=title, description=description, view=view, color=0x4F9EF5)


_LINK_INSTRUCTIONS = (
    "1. Join the [main Discord server](https://discord.gg/mysticraft) if you haven't already\n"
    "2. Use `/link` in any gamemodes (Lifesteal/Practice/Survival/Vanilla) to get a code\n"
    "3. DM the **4-digit code** to the corresponding Discord bot.\n"
    "4. Once linked, staff will reset your password within 1-3 days."
)


async def _st_password_reset_start(interaction):
    linked, ign = await is_linked(interaction.user, interaction.client)
    if linked:
        await _st_send_final(interaction, "Password Reset",
            f"Wow! Your account is already linked (`{ign}`). Staff will reset your password within 1–3 days.", data=None,
            color=0x00FF00)
    else:
        await _st_send_instructions(interaction, "Password Reset",
            "Your account is not linked. Can you currently log in to your account?",
            SupportChoiceView([
                SupportActionButton(label="Yes, I can log in",  custom_id="pr_can_login",    style=discord.ButtonStyle.green),
                SupportActionButton(label="No, I cannot log in", custom_id="pr_cannot_login", style=discord.ButtonStyle.red),
            ]))


async def _st_pr_show_link_instructions(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_instructions(interaction, "Password Reset (Linking Instructions)", _LINK_INSTRUCTIONS,
        SupportChoiceView([
            SupportActionButton(label="I've finished linking", custom_id="pr_verify", style=discord.ButtonStyle.green),
        ]))


async def _st_pr_verify(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    linked, ign = await is_linked(interaction.user, interaction.client)
    if linked:
        await _st_send_final(interaction, "Password Reset",
            f"Great! Your account is now linked (`{ign}`). Staff will reset your password within 1–3 days.", data=None,
            color=0x00FF00)
    else:
        await _st_send_instructions(interaction, "Still Not Linked",
            "We couldn't detect a link yet. Please try these steps again:\n\n" + _LINK_INSTRUCTIONS,
                SupportChoiceView([
                SupportActionButton(label="Verify Again", custom_id="pr_verify_again", style=discord.ButtonStyle.green),
            ]))


async def _st_pr_reject(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_close(interaction, "Password Reset",
        "Unfortunately, verification is impossible without a prior link to your account. Please continue to play on MystiCraft with an alt account.")


async def _st_server_questions_root(interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_instructions(interaction, "Server Questions", "Choose a topic that you need help with. If you have a question not listed here, select **Other Questions**.",
        SupportChoiceView([
            SupportActionButton(label="How to Link Account",              custom_id="sq_link"),
            SupportActionButton(label="Switching from Cracked to Premium", custom_id="sq_cracked"),
            SupportActionButton(label="Other Questions",                   custom_id="sq_other"),
        ]))


async def _st_sq_link(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_close(interaction, "How to Link Your Account", _LINK_INSTRUCTIONS, color=0x4F9EF5)


async def _st_sq_cracked(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_close(interaction, "Switching from Cracked to Premium",
        "Log in with your cracked account, run `/premium <yourpassword>`, log out, "
        "then log back in with your premium account.\n\n"
        "Your premium account must have the **exact same username** as your cracked "
        "account, and the cracked account will no longer be used after migration.",
        color=0x4F9EF5)


async def _st_sq_other(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_instructions(interaction, "Other Questions or Issues",
        "Are you reporting a player/staff member, reporting a bug, or appealing for a punishment?",
        SupportChoiceView([
            SupportActionButton(label="Yes", custom_id="sq_other_yes", style=discord.ButtonStyle.green),
            SupportActionButton(label="No",  custom_id="sq_other_no",  style=discord.ButtonStyle.red, opens_modal=True),
        ]))


async def _st_sq_other_wrong_cat(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_close(interaction, "Wrong Category",
        "You created the wrong type of ticket. Please close this ticket and create a new ticket with the correct category in <#1373881299651268710>.")


async def _st_sq_other_modal(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    async def submit(obj, data):
        await _st_send_final(obj, "Server Questions", "Thanks! Staff will review your question shortly.", data)
    await interaction.response.send_modal(SupportFormModal(
        title="Server Question",
        fields=[("IGN", "What is your in-game name?", True), ("Question", "What would you like to ask?", True)],
        submit_handler=submit, source_message=interaction.message,
    ))


async def _st_billing_root(interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_instructions(interaction, "Billing Support",
        "Choose the billing issue that best matches your request.",
        SupportChoiceView([
            SupportActionButton(label="I haven't received my purchase", custom_id="billing_purchase",  opens_modal=True),
            SupportActionButton(label="I want to request a refund",     custom_id="billing_refund",    opens_modal=True),
            SupportActionButton(label="I want to transfer a rank",      custom_id="billing_transfer"),
        ]))


async def _st_billing_modal(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    async def submit(obj, data):
        await _st_send_final(obj, "Billing Support", "Thanks! Staff will review your billing request shortly.", data)
    await interaction.response.send_modal(SupportFormModal(
        title="Billing Support",
        fields=[
            ("IGN", "What is your in-game name?", True),
            ("Transaction ID/Email", "Transaction ID or email used", True),
            ("Description/Reason", "Describe the issue or reason for refund", True),
        ],
        submit_handler=submit, source_message=interaction.message,
    ))


async def _st_billing_transfer(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_close(interaction, "Rank Transfer", "Purchases, ranks, and perks are **non-transferable**.")


async def _st_appeals_root(interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_instructions(interaction, "Punishment Appeal",
        "Choose the appeal type that matches your case. Be sincere and talk about how you were unfairly punished or deserve a second chance.",
        SupportChoiceView([
            SupportActionButton(label="My in-game punishment", custom_id="appeal_mc",     opens_modal=True),
            SupportActionButton(label="My Discord punishment", custom_id="appeal_dc",     opens_modal=True),
            SupportActionButton(label="My friend's punishment", custom_id="appeal_friend"),
        ]))


async def _st_appeal_minecraft(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    async def submit(obj, data):
        await _st_send_final(obj, "Minecraft Punishment Appeal",
            "Your appeal has been submitted. Staff will review it shortly. We do not guarantee that we will accept your appeal. Our decision is final (meaning you cannot appeal your appeal decision), and you can appeal again in 14 days if it is rejected.", data, view=AppealCloseTicketButton())
    await interaction.response.send_modal(SupportFormModal(
        title="Minecraft Appeal",
        fields=[
            ("IGN", "What is your in-game name?", True),
            ("Punishment Reason/ID", "Reason or ID of the punishment", True),
            ("Appeal Statement", "Why should the punishment be removed?", True),
        ],
        submit_handler=submit, source_message=interaction.message,
    ))


async def _st_appeal_discord(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    async def submit(obj, data):
        await _st_send_final(obj, "Discord Punishment Appeal",
            "Your appeal has been submitted. Staff will review it shortly. We do not guarantee that we will accept your appeal. Our decision is final (meaning you cannot appeal your appeal decision), and you can appeal again in 14 days if it is rejected.", data)
    await interaction.response.send_modal(SupportFormModal(
        title="Discord Appeal",
        fields=[
            ("Discord Username", "Your Discord username", True),
            ("Reason", "Reason for the punishment", True),
            ("Appeal Statement", "Why should the punishment be removed?", True),
        ],
        submit_handler=submit, source_message=interaction.message,
    ))


async def _st_appeal_friend(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_close(interaction, "Appeal Rejected", "We do not process appeals initiated for other people.")


async def _st_player_reports_root(interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_instructions(interaction, "Player Report", "Choose the type of behaviour you want to report.",
        SupportChoiceView([
            SupportActionButton(label="Cheating / Hacking",  custom_id="player_cheat"),
            SupportActionButton(label="Chat Misbehavior",    custom_id="player_chat"),
        ]))


async def _st_pr_cheating(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_instructions(interaction, "Player Report (Cheating)", "Do you have clear video evidence?",
        SupportChoiceView([
            SupportActionButton(label="Yes", custom_id="pr_cheat_yes", style=discord.ButtonStyle.green, opens_modal=True),
            SupportActionButton(label="No",  custom_id="pr_cheat_no",  style=discord.ButtonStyle.red),
        ]))


async def _st_pr_cheat_modal(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    async def submit(obj, data):
        await _st_send_final(obj, "Player Report", "Thanks! Staff will review the report shortly. Whether or not we take action is up to the discretion of our staff.", data)
    await interaction.response.send_modal(SupportFormModal(
        title="Player Report",
        fields=[
            ("Offender IGN", "Offending player's in-game name", True),
            ("Description", "Describe what happened", True),
            ("Link to Video Proof", "Paste the video link", True),
        ],
        submit_handler=submit, source_message=interaction.message,
    ))


async def _st_pr_cheat_no(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_close(interaction, "Player Report",
        "Unfortunately, without video proof we cannot take action against any players. Please try to screen record future encounters.")


async def _st_pr_chat(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_close(interaction, "Player Report (Chat Misbehavior)",
        "Unfortunately, our time window for chat punishments is 5 minutes, meaning "
        "moderators are only allowed to take action on chat misbehaviour that occurred "
        "in the last 5 minutes. By the time you created a ticket and a moderator comes "
        "online, that window has likely passed. Therefore, **we won't process chat reports "
        "in tickets.** Next time, you are encouraged to use the `/report` command "
        "in-game to send moderators a notification so we can take action immediately.")


async def _st_bug_report_root(interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_instructions(interaction, "Bug / Glitch Report", "Do you have clear video evidence?",
        SupportChoiceView([
            SupportActionButton(label="Yes", custom_id="bug_yes", style=discord.ButtonStyle.green),
            SupportActionButton(label="No",  custom_id="bug_no",  style=discord.ButtonStyle.red),
        ]))


async def _st_bug_no_evidence(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_close(interaction, "Bug / Glitch Report",
        "Without video proof or reproduction steps, we cannot fix bugs or restore items.")


async def _st_bug_has_evidence(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_instructions(interaction, "Bug / Glitch Report",
        "Choose the kind of bug report you are submitting.",
        SupportChoiceView([
            SupportActionButton(label="Reporting a bug (no items lost)", custom_id="bug_no_items",   opens_modal=True),
            SupportActionButton(label="Lost items due to a bug",          custom_id="bug_lost_items", opens_modal=True),
            SupportActionButton(label="Lost items due to lag / combat log", custom_id="bug_lag"),
        ]))


_BUG_FIELDS = [
    ("IGN", "What is your in-game name?", True),
    ("Bug Description", "Describe the bug and how to reproduce it", True),
    ("Link to Video Proof of Bug", "Paste the video link", True),
]


async def _st_bug_no_items_modal(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    async def submit(obj, data):
        await _st_send_final(obj, "Bug / Glitch Report", "Thanks! Our owner will review the bug report shortly.", data)
    await interaction.response.send_modal(SupportFormModal(title="Bug Report", fields=_BUG_FIELDS,
        submit_handler=submit, source_message=interaction.message))


async def _st_bug_lost_items_modal(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    async def submit(obj, data):
        await _st_send_final(obj, "Bug / Glitch Report (Item Loss)", "Thanks! Our owner will review the bug report shortly.", data)
    await interaction.response.send_modal(SupportFormModal(title="Bug / Item Loss", fields=_BUG_FIELDS,
        submit_handler=submit, source_message=interaction.message))


async def _st_bug_lag(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_close(interaction, "Bug / Glitch Report",
        "Sorry, we do not restore items lost to lag, despawns, or combat disconnects.")


async def _st_staff_report_root(interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_instructions(interaction, "Staff Report",
        "Did the staff member unfairly **punish** you?",
        SupportChoiceView([
            SupportActionButton(label="Yes", custom_id="sr_punish_yes", style=discord.ButtonStyle.green),
            SupportActionButton(label="No",  custom_id="sr_punish_no",  style=discord.ButtonStyle.red),
        ]))


async def _st_sr_wrong_cat(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_close(interaction, "Staff Report",
        "Please create an **Appeal** ticket instead. "
        "Staff reports are for behaviour issues (e.g. racism, hacking), not punishment disputes.")


async def _st_sr_ask_proof(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_instructions(interaction, "Staff Report", "Do you have proof of the staff member's behaviour (screenshots/videos)?",
        SupportChoiceView([
            SupportActionButton(label="Yes", custom_id="sr_proof_yes", style=discord.ButtonStyle.green, opens_modal=True),
            SupportActionButton(label="No",  custom_id="sr_proof_no",  style=discord.ButtonStyle.red),
        ]))


async def _st_sr_modal(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    async def submit(obj, data):
        await _st_send_final(obj, "Staff Report", "Thanks! Our managers and owners will review the report shortly.", data, ping_everyone=True)
    await interaction.response.send_modal(SupportFormModal(
        title="Staff Report",
        fields=[
            ("Your IGN", "What is your in-game name?", True),
            ("Staff IGN", "Who are you reporting?", True),
            ("Incident Description", "Describe what happened", True),
            ("Proof Link", "Paste the proof link", True),
        ],
        submit_handler=submit, source_message=interaction.message,
    ))


async def _st_sr_no_proof(interaction: discord.Interaction):
    if not await _st_owner_only(interaction): return
    await _st_send_close(interaction, "Staff Report", "Unfortunately, we cannot investigate any staff report without concrete evidence and proof.")


# Registry: custom_id → (handler, opens_modal) 
SUPPORT_HANDLER_REGISTRY: dict[str, tuple] = {
    # Password reset
    "pr_can_login":       (_st_pr_show_link_instructions, False),
    "pr_cannot_login":    (_st_pr_reject,                 False),
    "pr_verify":          (_st_pr_verify,                 False),
    "pr_verify_again":    (_st_pr_verify,                 False),
    # Server questions
    "sq_link":            (_st_sq_link,            False),
    "sq_cracked":         (_st_sq_cracked,         False),
    "sq_other":           (_st_sq_other,           False),
    "sq_other_yes":       (_st_sq_other_wrong_cat, False),
    "sq_other_no":        (_st_sq_other_modal,     True),
    # Billing
    "billing_purchase":   (_st_billing_modal,    True),
    "billing_refund":     (_st_billing_modal,    True),
    "billing_transfer":   (_st_billing_transfer, False),
    # Appeals
    "appeal_mc":          (_st_appeal_minecraft, True),
    "appeal_dc":          (_st_appeal_discord,   True),
    "appeal_friend":      (_st_appeal_friend,    False),
    # Player reports
    "player_cheat":       (_st_pr_cheating,    False),
    "player_chat":        (_st_pr_chat,        False),
    "pr_cheat_yes":       (_st_pr_cheat_modal, True),
    "pr_cheat_no":        (_st_pr_cheat_no,    False),
    # Bug reports
    "bug_yes":            (_st_bug_has_evidence,    False),
    "bug_no":             (_st_bug_no_evidence,     False),
    "bug_no_items":       (_st_bug_no_items_modal,  True),
    "bug_lost_items":     (_st_bug_lost_items_modal, True),
    "bug_lag":            (_st_bug_lag,             False),
    # Staff reports
    "sr_punish_yes":      (_st_sr_wrong_cat,  False),
    "sr_punish_no":       (_st_sr_ask_proof,  False),
    "sr_proof_yes":       (_st_sr_modal,      True),
    "sr_proof_no":        (_st_sr_no_proof,   False),
}

async def start_support_tree(
    interaction: discord.Interaction,
    ticket_channel: discord.TextChannel,
    selected_key: str,
    selected_label: str,
):
    # Wrap in a SimpleNamespace so helpers can use .channel / .guild / etc.
    ns = SimpleNamespace(
        channel=ticket_channel,
        guild=interaction.guild,
        client=interaction.client,
        user=interaction.user,
    )
    key = selected_key.lower()
    if "password" in key:
        await _st_password_reset_start(ns)
    elif "question" in key:
        await _st_server_questions_root(ns)
    elif "billing" in key:
        await _st_billing_root(ns)
    elif "appeal" in key:
        await _st_appeals_root(ns)
    elif "player" in key:
        await _st_player_reports_root(ns)
    elif "bug" in key:
        await _st_bug_report_root(ns)
    elif "staff" in key:
        await _st_staff_report_root(ns)


class CreateTicketButtonView(discord.ui.View):
    def __init__(
        self,
        title="Create Ticket",
        emoji="🎫",
        color=discord.ButtonStyle.green,
        *,
        timeout=None,
    ):
        super().__init__(timeout=timeout)
        self.add_item(CreateTicketButton(title, emoji, color))


class CloseTicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.red,
        custom_id="close",
        emoji="🔒",
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.channel.topic == None:
            t = "None"
        else:
            t = interaction.channel.topic
        if ":no_entry_sign:" in t:
            embed = discord.Embed(
                title="Ticket already closed :no_entry_sign:",
                description="This ticket is already closed.",
                color=0xFF0000,
            )
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        embed = discord.Embed(
            title="Are you sure about that?",
            description="Only moderators and administrators can reopen the ticket.",
            color=0xFF0000,
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await interaction.response.send_message(
            embed=embed, view=ConfirmCloseTicketButtons(), ephemeral=True
        )
        
        
class AppealCloseTicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.red,
        custom_id="appealclose",
        emoji="🔒",
    )
    async def appealclose(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.channel.topic == None:
            t = "None"
        else:
            t = interaction.channel.topic
        if ":no_entry_sign:" in t:
            embed = discord.Embed(
                title="Ticket already closed :no_entry_sign:",
                description="This ticket is already closed.",
                color=0xFF0000,
            )
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        embed = discord.Embed(
            title="Are you sure about that?",
            description="Only moderators and administrators can reopen the ticket.",
            color=0xFF0000,
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await interaction.response.send_message(
            embed=embed, view=ConfirmCloseTicketButtons(), ephemeral=True
        )

    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        custom_id="appealinfo",
        emoji="🔧",
    )
    async def appealinfo(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.get_role(1373882802084511754) not in interaction.user.roles:
            return await interaction.response.send_message("You cannot click this button", ephemeral=True)

        ign, punishment_id = interaction.message.embeds[0].fields[0].value, interaction.message.embeds[0].fields[1].value
        ign_lower = ign.strip().lower()
        ign_sanitized = sanitize_firebase_key(ign_lower)

        PUNISHMENT_LOG_CHANNEL = interaction.client.get_channel(1320053091650764812)
        EVIDENCE_LOG_CHANNEL = interaction.client.get_channel(1155910232204128256)

        await interaction.response.send_message(embed=discord.Embed(
            description=f"-# <a:loading:1026905298088243240>ㅤLooking up `{ign}`. **This may take a few seconds!**", 
            color=0xFFFF00), ephemeral=True)

        # === Firebase Setup ===
        db_root = db.reference("/")
        sync_ref = db_root.child("Last Punishments Sync")
        last_sync_ts = sync_ref.get()

        if last_sync_ts and last_sync_ts > 0:
            after = datetime.datetime.fromtimestamp(last_sync_ts, tz=datetime.timezone.utc)
            history_kwargs = {"after": after}
        else:
            history_kwargs = {}

        new_messages = [
            msg async for msg in PUNISHMENT_LOG_CHANNEL.history(limit=None, **history_kwargs)
        ]

        if new_messages:
            sync_ref.set(int(time.time()))

        # === Parse new messages ===
        for msg in new_messages:
            if not msg.embeds:
                continue

            # If the embed has more than zero fields, Polar Punishment
            if len(msg.embeds[0].fields) > 0:
                original_ign = msg.content.split(" ")[1].strip().lower()
                action = "Banned" if "ban" in msg.content.lower() else "Unknown"
                sanitized_key = sanitize_firebase_key(original_ign)
                punishment_time = int(msg.created_at.timestamp())
                new_details = [f"**Reason**: {msg.content.split(' ')[5]}"]
            else:
                embed = msg.embeds[0]
                desc = embed.description
                try:
                    original_ign = desc.split(" ")[0].strip().lower()
                    sanitized_key = sanitize_firebase_key(original_ign)
                except Exception:
                    continue

                punishment_time = int(msg.created_at.timestamp())
                action = embed.title or "Unknown"
                details = embed.description.split("\n")
                new_details = []

                for line in details:
                    if '•' in line and ':' in line:
                        try:
                            line = line.replace('•', '-')
                            key, value = line.split(':', 1)
                            dash, label = key.split('-', 1)
                            formatted = f"**{label.strip()}**: {value.strip()}"
                            new_details.append(formatted)
                        except Exception:
                            continue

            punishment_entry = {
                "ign": original_ign,
                "action": action,
                "timestamp": punishment_time,
                "log_url": msg.jump_url,
                "details": new_details
            }

            user_ref = db.reference(f"Punishments/{sanitized_key}")
            user_ref.push(punishment_entry)

        # === Read punishments for the requested IGN ===
        punishments_ref = db.reference(f"Punishments/{ign_sanitized}")
        user_data = punishments_ref.get()

        if not user_data:
            return await interaction.edit_original_response(content=None, embed=discord.Embed(
                description=f"No punishments found for `{ign}`.", color=0xFF0000))

        punishment_embed = discord.Embed(
            title=f"Punishment History for {ign}",
            description=f"We found `{len(user_data)}` past punishment{'s' if len(user_data) > 1 else ''}.",
            color=0xFFFF00
        )

        # === Format & add each punishment ===
        for entry in sorted(user_data.values(), key=lambda x: x["timestamp"], reverse=True):
            timestamp = entry["timestamp"]
            evidence_links = []

            start_time = datetime.datetime.fromtimestamp(timestamp) - datetime.timedelta(hours=12)
            end_time = datetime.datetime.fromtimestamp(timestamp) + datetime.timedelta(hours=12)

            async for evidence_msg in EVIDENCE_LOG_CHANNEL.history(limit=200, after=start_time, before=end_time):
                if ign_lower in evidence_msg.content.lower():
                    evidence_links.append(evidence_msg.jump_url)
                    continue
                for embed in evidence_msg.embeds:
                    embed_text = " ".join(
                        filter(None, [
                            embed.title or '',
                            embed.description or '',
                            " ".join(f.name + f.value for f in embed.fields)
                        ])
                    ).lower()
                    if ign_lower in embed_text:
                        evidence_links.append(evidence_msg.jump_url)
                        break

            evidence_text = " | ".join(f"[Evidence {i+1}]({link})" for i, link in enumerate(evidence_links)) or "No evidence found"
            lines = [f"-# - {line}" for line in entry["details"]]
            description = f"<t:{timestamp}:R>\n" + "\n".join(lines)
            description += f"\n-# [Log]({entry['log_url']}) | {evidence_text}"

            punishment_embed.add_field(name=f"{entry['action']} - <t:{timestamp}:d>", value=description, inline=True)

        await interaction.edit_original_response(content=None, embed=punishment_embed)


    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        custom_id="appealhistory",
        emoji="📖",
    )
    async def appealhistory(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.get_role(1373882802084511754) not in interaction.user.roles:
            return await interaction.response.send_message("You cannot click this button", ephemeral=True)
        
        ign, punishment_id = interaction.message.embeds[0].fields[0].value, interaction.message.embeds[0].fields[1].value
        
        await interaction.response.defer(ephemeral=True, thinking=True)
        APPEAL_LOG_CHANNEL = interaction.client.get_channel(1286031597845614625)
        
        # Fetch and process appeal history
        appeal_history = []
        async for message in APPEAL_LOG_CHANNEL.history():
            # Process manual entries (text messages)
            if not message.embeds and message.content:
                entries = message.content.split('---')
                for entry in entries:
                    appeal_data = self.parse_manual_appeal(entry, ign, message.author)
                    if appeal_data:
                        appeal_history.append({
                            **appeal_data,
                            "timestamp": message.created_at,
                            "message_url": message.jump_url
                        })
                        
            # Process bot-generated embeds
            elif message.embeds:
                for embed in message.embeds:
                    appeal_data = self.parse_embed_appeal(embed, ign)
                    if appeal_data:
                        appeal_history.append({
                            **appeal_data,
                            "timestamp": message.created_at,
                            "message_url": message.jump_url
                        })
        
        # Sort by timestamp (newest first)
        appeal_history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Create embed with appeal history
        if not appeal_history:
            embed = discord.Embed(
                description=f"No appeal history found for `{ign}`",
                color=discord.Color.orange()
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)
        
        embed = discord.Embed(
            title=f"Appeal History for {ign}",
            description=f"We found `{len(appeal_history)}` past appeal decision{'s' if len(appeal_history) > 1 else ''}.",
            color=discord.Color.blue()
        )
        
        for i, appeal in enumerate(appeal_history[:5]):  # Show max 5 most recent
            status_emoji = "✅" if "accept" in appeal["determination"].lower() or "accept" in appeal["info"].lower() else "❌"
            field_value = (
                f"<t:{int(appeal['timestamp'].timestamp())}:R>\n"
                f"-# **Punishment:** {appeal['punishment']}\n"
                f"-# **Decision:** {status_emoji} {appeal['determination']}\n"
                f"-# **Info:** {appeal['info']}\n"
                f"-# **Staff:** {appeal.get('staff', 'Unknown')}\n"
                f"-# [View Log Message]({appeal['message_url']})"
            )
            embed.add_field(
                name=f"Appeal #{i+1} - {appeal['timestamp'].strftime('%Y-%m-%d')}",
                value=field_value,
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    def parse_manual_appeal(self, text: str, ign: str, staff) -> dict:
        """Parse manual appeal entries from text"""
        data = {}
        ign_found = False
        
        # Normalize text for easier parsing
        text = text.lower().replace('>>', ':').replace(';', ':').replace('--', ':')
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        for line in lines:
            # Check for IGN match (case-insensitive)
            if ign.lower() in line:
                ign_found = True
                
            # Extract key-value pairs
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if 'ign' in key:
                    data['ign'] = value
                elif 'punishment' in key:
                    data['punishment'] = value.title()
                elif 'determination' in key or 'decision' in key:
                    data['determination'] = value.title()
                elif 'info' in key or 'notes' in key:
                    data['info'] = value
                data['staff'] = staff.mention
        
        return data if ign_found and data else None

    def parse_embed_appeal(self, embed: discord.Embed, ign: str) -> dict:
        """Parse bot-generated appeal embeds"""
        # Check if it's an appeal embed
        if not embed.title or "appeal" not in embed.title.lower():
            return None
            
        # Check if IGN matches
        ign_match = False
        data = {}
        
        # Extract fields from description
        if embed.description:
            lines = embed.description[2:].split('\n')
            for line in lines:
                if '**' in line:
                    key, value = line.split('**:', 1) if '**:' in line else line.split('**', 1)
                    key = key.replace('**', '').strip().lower()
                    value = value.strip()
                    
                    if 'staff' in key:
                        data['staff'] = value
                    if 'ign' in key and ign.lower() in value.lower():
                        ign_match = True
                    if 'punishment' in key:
                        data['punishment'] = value
                    if 'determination' in key:
                        data['determination'] = value
                    if 'info' in key:
                        data['info'] = value
        
        return data if ign_match else None
        
    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        custom_id="appealaccept",
        emoji="<:yes:1036811164891480194>",
    )
    async def appealaccept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.get_role(1373882802084511754) not in interaction.user.roles:
            return await interaction.response.send_message("You cannot click this button", ephemeral=True)
        
        ign, punishment_id = interaction.message.embeds[0].fields[0].value, interaction.message.embeds[0].fields[1].value
        try:
            user = interaction.guild.get_member(int(interaction.channel.topic))
        except Exception:
            user = None
        await interaction.response.send_modal(AppealModal(ign, "Accept", user))
        
    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        custom_id="appealreject",
        emoji="<:no:1036810470860013639>",
    )
    async def appealreject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.get_role(1373882802084511754) not in interaction.user.roles:
            return await interaction.response.send_message("You cannot click this button", ephemeral=True)
        
        ign, punishment_id = interaction.message.embeds[0].fields[0].value, interaction.message.embeds[0].fields[1].value
        try:
            user = interaction.guild.get_member(int(interaction.channel.topic))
        except Exception:
            user = None
        await interaction.response.send_modal(AppealModal(ign, "Reject", user))


class TicketAdminButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Reopen Ticket",
        style=discord.ButtonStyle.grey,
        custom_id="reopen",
        emoji="🔓",
    )
    async def reopen(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.guild.get_member(
            int(interaction.channel.topic.replace("🚫", "").replace(":no_entry_sign:", "").strip())
        )
        newName = f"🟡{interaction.channel.name[1:]}"
        await interaction.channel.edit(topic=user.id, name=newName)
        await interaction.channel.set_permissions(
            user, send_messages=True, read_messages=True, attach_files=True
        )

        ref = db.reference("/Tickets")
        tickets = ref.get()
        for key, value in tickets.items():
            if value["Server ID"] == interaction.guild.id:
                LOGCHANNEL_ID = value["Log Channel ID"]
                break
        log = interaction.guild.get_channel(LOGCHANNEL_ID)

        embed = discord.Embed(
            title="Ticket reopened",
            description=f"Ticket created by {user.mention} is reopened by {interaction.user.mention}",
            color=0xFFFF00,
        )
        try:
            embed.set_author(
                name=user.name, icon_url=user.avatar.url
            )
        except Exception:
            embed.set_author(name=user.name)
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        embed.set_footer(text=f"User ID: {user.id}")
        button = Button(
            style=discord.ButtonStyle.link,
            label="View Ticket",
            url=f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}",
        )
        view = View()
        view.add_item(button)
        await log.send(embed=embed, view=view)
        embed = discord.Embed(
            title="Ticket reopened",
            description=f"Your ticket is reopened.",
            color=0xE44D41,
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        button = Button(
            style=discord.ButtonStyle.link,
            label="Head over to your ticket",
            emoji="🎫",
            url=f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}",
        )
        view = View()
        view.add_item(button)
        try:
            await user.send(embed=embed, view=view)
        except Exception:
            pass
        embed = discord.Embed(
            title="🔓 Ticket Reopened",
            description="Ticket is again visible to the member.",
            color=0xFFFF00,
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await interaction.message.delete()
        await interaction.channel.send(embed=embed, view=CloseTicketButton())
        await interaction.response.send_message("Ticket is reopened.", ephemeral=True)

    @discord.ui.button(
        label="Delete Ticket",
        style=discord.ButtonStyle.grey,
        custom_id="delete",
        emoji="✉️",
    )
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="Deleting Ticket...",
            description="Ticket will be deleted in 5 seconds",
            color=0xFF0000,
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await interaction.message.delete()
        await interaction.channel.send(embed=embed)
        await asyncio.sleep(5)
        await interaction.channel.delete()


async def delete_flagged_messages_for_ticket(guild, channel_id, support_channels, tierlist_channels):
    """Delete all flagged messages referencing this ticket from flag channels."""
    if guild.id == SUPPORT_SERVER_ID:
        flag_channels = support_channels.values()
    elif guild.id == TIERLIST_SERVER_ID:
        flag_channels = tierlist_channels.values()
    else:
        return
    
    for flag_channel_id in flag_channels:
        try:
            flag_channel = guild.get_channel(flag_channel_id)
            if not flag_channel:
                continue
            
            async for message in flag_channel.history(limit=100):
                try:
                    if message.embeds:
                        for embed in message.embeds:
                            if embed.description and f"<#{channel_id}>" in embed.description:
                                await message.delete()
                                break
                            if embed.footer and embed.footer.text and f"Ticket ID: {channel_id}" in embed.footer.text:
                                await message.delete()
                                break
                except discord.Forbidden:
                    pass
                except Exception:
                    pass
        except Exception:
            pass


async def close_ticket_channel(interaction):
    """Reusable ticket close routine. Accepts an interaction-like object with `.guild`, `.channel`, `.user`, and `.client`."""
    channel = interaction.channel
    guild = interaction.guild
    closer = interaction.user

    left = False
    userObject = None
    try:
        user = guild.get_member(int(channel.topic)).name
        userObject = guild.get_member(int(channel.topic))
    except Exception:
        user = "[LEFT SERVER]"
        left = True

    ref = db.reference("/Tickets")
    tickets = ref.get()
    LOGCHANNEL_ID = None
    if tickets:
        for key, value in tickets.items():
            if value.get("Server ID") == guild.id:
                LOGCHANNEL_ID = value.get("Log Channel ID")
                break
    log = guild.get_channel(LOGCHANNEL_ID) if LOGCHANNEL_ID else None
    
    await delete_flagged_messages_for_ticket(guild, channel.id, support_channel_map, tierlist_channel_map)
    
    from commands.Tickets.summary import get_transcript, generate
    f, user, usersInvolved, staff_message_counts = await get_transcript(interaction, channel)

    if left == False and userObject is not None:
        embed = discord.Embed(
            title="Ticket closed",
            description=f"Ticket created by {userObject.mention} is closed by {closer.mention}",
            color=0xE44D41,
        )
        try:
            embed.set_author(name=f"{userObject.name}", icon_url=userObject.avatar.url)
        except Exception:
            embed.set_author(name=f"{userObject.name}")
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        embed.set_footer(text=f"Channel ID: {channel.id}")
    else:
        embed = discord.Embed(
            title="Ticket closed",
            description=f"Ticket created by a member who has left the server is closed by {closer.mention}",
            color=0xE44D41,
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)

    staff_list = "\n".join(f"- {u.mention} `({staff_message_counts[u]})`" for u in usersInvolved) if usersInvolved else "`None`"
    embed.add_field(name="Staff Involved", value=staff_list, inline=True)

    # try:
    #     summary = await generate(
    #         f"The following is the entire history of the ticket in a Discord server for a user. "
    #         "Please summarise the entire interaction into 1 sentence. "
    #         "Only give 1 response option. Do not output additional text such as 'Here is the summary:'. "
    #         f"Do not include any metadata or user info. Only focus on the conversation content.\n\n"
    #         "Full transcript:\n"
    #         f"{f.read().split('<!DOCTYPE html>')[1]}"
    #     )
    # except Exception as e:
    #     print(e)
    #     summary = "`AI Summary Temporarily Unavailable`"

    try:
        ticket_topic = [message async for message in channel.history(oldest_first=True)][0].embeds[0].title
    except Exception:
        ticket_topic = "Others"
    
    embed.add_field(name="Ticket Topic", value=ticket_topic)

    log_message = None
    if log:
        try:
            log_message = await log.send(
                embed=embed,
                file=discord.File(f"./commands/Tickets/transcript/{channel.id}.html")
            )
        except Exception:
            log_message = None

        try:
            with open(f"./commands/Tickets/transcript/{channel.id}.html", "rb") as f:
                file_content = f.read()
            checksum = hashlib.sha256(file_content + str(log.id).encode()).hexdigest()[:20]
            token = f"{log.id}-{log_message.id}-{checksum}"
            url = f"https://ticket.mysticraft.xyz/logs/{token}"
            embed.add_field(name="Transcript Link", value=url, inline=False)
            # embed.add_field(name="Ticket Summary", value=summary)
            if log_message:
                await log_message.edit(embed=embed)
        except Exception:
            pass

    try:
        os.remove(f"./commands/Tickets/transcript/{channel.id}.html")
    except Exception:
        pass

    transcript_button = Button(
        style=discord.ButtonStyle.link,
        label="Transcript Link",
        emoji="📜",
        url=(url if log and log_message else "https://ticket.mysticraft.xyz/")
    )
    user_view = View()
    user_view.add_item(transcript_button)

    embed = discord.Embed(
        title="Ticket closed",
        description=f"Your ticket in **{guild.name}** is now closed. \n-# Visit https://ticket.mysticraft.xyz/ to see your previous tickets",
        color=0xE44D41,
    )
    embed.add_field(name="Ticket Topic", value=ticket_topic)
    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    embed.set_footer(text=f"You can always create a new ticket for additional assistance!")
    try:
        user_member = userObject if userObject is not None else None
        if user_member:
            await user_member.send(embed=embed, view=user_view)
            await channel.set_permissions(user_member, send_messages=False, read_messages=False, attach_files=False)
    except Exception:
        pass

    try:
        await channel.send(embed=discord.Embed(title=f"Ticket Closed", description=f"Ticket is closed by {closer.mention} and is no longer visible to the member {user.mention if not left else 'Unknown'}", color=0xE44D41))
    except Exception:
        pass

    embed = discord.Embed(title="", description="""```STAFF CONTROLS PANEL```""", color=0xE44D41)
    try:
        view = TicketAdminButtons()
        view.add_item(transcript_button)
        await channel.send(embed=embed, view=view)
    except Exception:
        try:
            await channel.send(embed=embed)
        except Exception:
            pass

    try:
        await channel.edit(topic=f":no_entry_sign: {channel.topic}")
    except Exception:
        pass

    try:
        newName = f"🚫{channel.name[1:]}"
        await channel.edit(topic=f"🚫 {userObject.id if userObject is not None else 'Unknown member'}", name=newName)
    except Exception:
        pass
    
    try:
        ref = db.reference(f"/Ticket Mention Violations/{channel.id}")
        ref.delete()
    except Exception as e:
        print(f"[Mention Enforcement] Failed to reset violations for channel {channel.id}: {e}")


class ConfirmCloseTicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green, custom_id="yes")
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=discord.Embed(description="✅ Ticket Closure Confirmed", color=discord.Color.green()), 
            view=None
        )
        await close_ticket_channel(interaction)

    @discord.ui.button(label="No", style=discord.ButtonStyle.red, custom_id="no")
    async def red(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="Action Cancelled",
            description=f"Alright {interaction.user.mention}! I will not close the ticket!",
            color=0xFF0000,
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await interaction.response.edit_message(embed=embed, view=None)


class ResolveFlagView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(
        label="Mark Resolved",
        style=discord.ButtonStyle.green,
        custom_id="resolve_flag_view:resolve"
    )
    async def resolve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            channel = interaction.client.get_channel(int(interaction.message.embeds[0].footer.text.split(":")[1].strip()))
            await interaction.message.delete()
            await interaction.response.send_message("✅ Ticket marked as resolved!", ephemeral=True)
            newName = f"🟢{channel.name[1:]}"
            await channel.edit(topic=channel.topic, name=newName)
        except Exception as e:
            await interaction.response.send_message(f"❗ `{e}`", ephemeral=True)


class Ticket(commands.GroupCog, name="ticket"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()
        
    @app_commands.command(name="blacklist", description="View all blacklisted users or blacklist a user")
    @app_commands.describe(user="User to blacklist (leave empty to view all blacklisted users)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_blacklist(self, interaction: discord.Interaction, user: discord.Member = None):
        if user is None:
            ref = db.reference(f"/Ticket Blacklist")
            blacklisted_users = ref.get()

            if not blacklisted_users:
                embed = discord.Embed(
                    description="No users are currently blacklisted from creating tickets.",
                    color=0x00FF00
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            user_list = []
            for user_id in blacklisted_users.keys():
                user = interaction.guild.get_member(int(user_id))
                if user:
                    user_list.append(f"- {user.mention} (`{user_id}`)")
                else:
                    user_list.append(f"- `{user_id}` (User not in server)")

            embed = discord.Embed(
                title=f"Blacklisted Users ({len(user_list)})",
                description="\n".join(user_list),
                color=0xFF0000
            )
            embed.set_footer(text=f"Requested by {interaction.user.name}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            ref = db.reference(f"/Ticket Blacklist/{user.id}")
            ref.set(True)
            embed = discord.Embed(description=f"{user.mention} has been blacklisted from creating tickets in all **MystiCraft** networks.", color=0x00FF00)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
    @app_commands.command(name="unblacklist", description="Unblacklist a user from creating tickets")
    @app_commands.describe(user="User to unblacklist")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_unblacklist(self, interaction: discord.Interaction, user: discord.Member):
        ref = db.reference(f"/Ticket Blacklist/{user.id}")
        ref.delete()
        embed = discord.Embed(description=f"{user.mention} has been unblacklisted from **MystiCraft** networks.", color=0x00FF00)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @app_commands.command(name="add", description="Add a user to the current ticket channel")
    @app_commands.describe(user="The user to add to this ticket")
    async def ticket_add(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.channel.topic or not interaction.channel.topic.isdigit():
            embed = discord.Embed(
                description="❌ This command can only be used in ticket channels.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        ticket_owner_id = int(interaction.channel.topic)
        
        SUPPORT_SERVER_ROLES = [
            1373893342169137202,  # owner
            1374975813891395784,  # executive
            1373892851745685524,  # manager
            1373891660471210024,  # senior admin
            1373890838496673852,  # admin
            1373890109216129155,  # developer
            1373889160833798274,  # senior mod
            1373887662842183801,  # mod
            1373883332492001341,  # helper
            ### TIERLIST ROLES BELOW
            1304848576190484553,  # owner
            1304851740226748556,  # admin
            1339144441583370251,  # regulator
            1305573653332754533,  # staff
        ]
        if not any(role.id in SUPPORT_SERVER_ROLES for role in interaction.user.roles):
            embed = discord.Embed(
                description="You cannot run this command as you do not have permission to manage tickets.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if user.id == ticket_owner_id:
            embed = discord.Embed(
                description="❌ This user is the ticket owner and already has access to this channel.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        current_perms = interaction.channel.permissions_for(user)
        if current_perms.read_messages and current_perms.send_messages:
            embed = discord.Embed(
                description=f"❌ {user.mention} already has access to this ticket channel.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await interaction.channel.set_permissions(
                user, 
                send_messages=True, 
                read_messages=True, 
                attach_files=True
            )
            
            embed = discord.Embed(
                description=f"✅  {user.mention} has been added to this ticket by {interaction.user.mention}.",
                color=0x00FF00
            )
            
            await interaction.response.send_message(content=user.mention, embed=embed)
            
            try:
                dm_embed = discord.Embed(
                    title="You have been added to a ticket channel!",
                    description=f"You have been added to a ticket channel in **{interaction.guild.name}** by {interaction.user.mention}.",
                    color=discord.Color.green(),
                )
                button = Button(
                    style=discord.ButtonStyle.link,
                    label="View Ticket",
                    url=f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}",
                )
                view = View()
                view.add_item(button)
                await user.send(embed=dm_embed, view=view)
            except:
                pass
                
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to modify channel permissions. Please contact an administrator.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred while adding the user: {str(e)}",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="reset", description="Reset the settings of ticket in the server")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_reset(self, interaction: discord.Interaction) -> None:
        tickets = db.reference("/Tickets").get()
        found = False
        for key, val in tickets.items():
            if val["Server ID"] == interaction.guild.id:
                db.reference("/Tickets").child(key).delete()
                found = True
                break
        if found:
            embed = discord.Embed(
                title="Ticket successfully reset",
                description=f"You can use </ticket setup:1033188985587109910> at anytime to setup the ticket function again.",
                colour=0xFFFF00,
            )
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="We could not find your server",
                description=f"Maybe you have already reset the ticket function in your server, or you have never enabled ticket function. Anyways, no records found in our system.",
                colour=0xFF0000,
            )
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setup", description="Setup ticket function in the server")
    @app_commands.describe(
        category="The category to hold all the tickets (If you do not specify, we will create one for you)",
        log_channel="The channel to log all future tickets (If you do not specify, we will create one for you)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_setup(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel = None,
        log_channel: discord.TextChannel = None,
    ) -> None:
        ref = db.reference("/Tickets")
        tickets = ref.get()
        for key, value in tickets.items():
            if value["Server ID"] == interaction.guild.id:
                embed = discord.Embed(
                    title="Ticket already enabled!",
                    description=f'The category is already set as <#{value["Category ID"]}> `({value["Category ID"]})` and the ticket log channel is already set as <#{value["Log Channel ID"]}> `({value["Log Channel ID"]})`\n\nPlease use </ticket button:1033188985587109910> or </ticket dropdown:1033188985587109910> to create your own customized ticket panel.\n\nIf you wish to reset the settings of tickets, please use </ticket reset:1033188985587109910>.',
                    colour=0xFF0000,
                )
                embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
                return await interaction.response.send_message(embed=embed, ephemeral=True)

        if not category:
            category = await interaction.guild.create_category("Tickets")
        if not log_channel:
            log_channel = await interaction.guild.create_text_channel(
                f"ticket-log", category=category
            )

        embed = discord.Embed(
            title="What is this?",
            description=f"This channel logs all ticket deletion and creation events! It clearly provides server admins a list of past tickets. ",
            colour=discord.Color.blurple(),
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await log_channel.send(embed=embed)

        await category.set_permissions(interaction.guild.default_role, read_messages=False)
        await log_channel.set_permissions(interaction.guild.default_role, read_messages=False)

        data = {
            interaction.guild.name: {
                "Server Name": interaction.guild.name,
                "Server ID": interaction.guild.id,
                "Category ID": category.id,
                "Log Channel ID": log_channel.id,
            }
        }

        for key, value in data.items():
            ref.push().set(value)

        embed = discord.Embed(
            title="Ticket successfully enabled!",
            description=f"The category is set as <#{category.id}> `({category.id})` and the ticket log channel is set as <#{log_channel.id}> `({log_channel.id})`. \n\n**All administrators can by default view the tickets. If you wish to let staff without administrator permission to do so as well, please use </ticket addrole:1033188985587109910> and add roles of your own choice. Use </ticket removerole:1033188985587109910> for vice versa.**\n\nPlease use </ticket button:1033188985587109910> or </ticket dropdown:1033188985587109910> to create your own customized ticket panel.",
            colour=0x00FF00,
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="addrole", description="Add a role that can see and manage tickets")
    @app_commands.describe(role="The role at your own choice that can see and manage tickets")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_addrole(self, interaction: discord.Interaction, role: discord.Role) -> None:
        ref = db.reference("/Tickets")
        tickets = ref.get()
        found = False
        for key, value in tickets.items():
            if value["Server ID"] == interaction.guild.id:
                CATEGORY_ID = value["Category ID"]
                LOGCHANNEL_ID = value["Log Channel ID"]
                found = True
                break

        if found:
            category = interaction.guild.get_channel(CATEGORY_ID)
            log_channel = interaction.guild.get_channel(LOGCHANNEL_ID)
            await category.set_permissions(role, read_messages=True, send_messages=True, attach_files=True, manage_channels=True, manage_messages=True, read_message_history=True)
            await log_channel.set_permissions(role, read_messages=True, send_messages=True, attach_files=True, manage_channels=True, manage_messages=True, read_message_history=True)
            for channel in category.channels:
                await channel.set_permissions(role, read_messages=True, send_messages=True, attach_files=True, manage_channels=True, manage_messages=True, read_message_history=True)
            embed = discord.Embed(
                title="Role Added!",
                description=f"{role.mention} now has the following permissions in all ticket-related channels:\n\n`- Read Messages`\n`- Send Messages`\n`- Attach Files`\n`- Manage Channels`\n`- Manage Messages`\n`- Read Message History`",
                colour=0x00FF00,
            )
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title="Ticket not enabled!", description=f"This server does not have a ticket category or a log channel. Please ask the server admin to use </ticket setup:1033188985587109910> to setup tickets!", colour=0xFF0000)
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="removerole", description="Remove a role that can see and manage tickets")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(role="The role at your own choice that can no longer see and manage tickets")
    async def ticket_removerole(self, interaction: discord.Interaction, role: discord.Role) -> None:
        ref = db.reference("/Tickets")
        tickets = ref.get()
        found = False
        for key, value in tickets.items():
            if value["Server ID"] == interaction.guild.id:
                CATEGORY_ID = value["Category ID"]
                LOGCHANNEL_ID = value["Log Channel ID"]
                found = True
                break

        if found:
            category = interaction.guild.get_channel(CATEGORY_ID)
            log_channel = interaction.guild.get_channel(LOGCHANNEL_ID)
            await category.set_permissions(role, read_messages=None, send_messages=None, attach_files=None, manage_channels=None, manage_messages=None, read_message_history=None)
            await log_channel.set_permissions(role, read_messages=None, send_messages=None, attach_files=None, manage_channels=None, manage_messages=None, read_message_history=None)
            for channel in category.channels:
                await channel.set_permissions(role, read_messages=None, send_messages=None, attach_files=None, manage_channels=None, manage_messages=None, read_message_history=None)
            embed = discord.Embed(
                title="Role Removed!",
                description=f"{role.mention} no longer has elevated permissions in ticket-related channels.",
                colour=0x00FF00,
            )
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title="Ticket not enabled!", description=f"This server does not have a ticket category or a log channel. Please ask the server admin to use </ticket setup:1033188985587109910> to setup tickets!", colour=0xFF0000)
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="notify", description="Send a DM to the ticket author notifying the ticket needs their attention")
    @app_commands.describe(message="Optional message you could include in the DMs")
    async def ticket_notify(self, interaction: discord.Interaction, message: str = None) -> None:
        if message is None:
            message = " "
        else:
            message = f"\n\n> {message}"
        try:
            user = interaction.guild.get_member(int(interaction.channel.topic))
        except Exception:
            pass
        embed = discord.Embed(
            title="⚠️ Notification ⚠️",
            description=f"The ticket you previously opened in **{interaction.guild.name}** needs your attention! Please kindly respond.{message}\n\nIf you no longer need assistance or your issue has been resolved, **please still let us know in the ticket** so we can help close the ticket.",
            color=0xE44D41,
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        try:
            button = Button(style=discord.ButtonStyle.link, label="Head over to your ticket", emoji="🎫", url=f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}")
            view = View()
            view.add_item(button)
            await user.send(embed=embed, view=view)
            await interaction.response.send_message(f"{user.mention} received a DM notification.")
        except Exception:
            await interaction.response.send_message("Unable to DM user!", ephemeral=True)
            
    @app_commands.command(name="tldr", description="Get ticket summary")
    async def ticket_tldr(self, interaction: discord.Interaction):
        await interaction.response.defer()
        channel = interaction.channel
        from commands.Tickets.summary import generate, get_transcript
        f, user, _, _ = await get_transcript(interaction, channel)
        prompt = f"Summarize this ticket in 3 short bullet points: {f.read()}"
        summary = await generate(prompt)
        embed = discord.Embed(title=f"TL;DR for {channel.name}", description=summary, color=discord.Color.blue())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="flag", description="Flag a ticket for special attention")
    @app_commands.describe(flag_type="Select a flag type", notes="Provide additional context (optional)")
    @app_commands.choices(flag_type=[
        app_commands.Choice(name="Owner Needed", value="owner"),
        app_commands.Choice(name="Manager Needed", value="manager"),
        app_commands.Choice(name="Mod Needed", value="mod"),
        app_commands.Choice(name="Resolved", value="resolved"),
    ])
    async def ticket_flag(self, interaction: discord.Interaction, flag_type: app_commands.Choice[str], notes: str = None):
        if flag_type.value == "resolved":
            await delete_flagged_messages_for_ticket(interaction.guild, interaction.channel.id, support_channel_map, tierlist_channel_map)
            newName = f"🟢{interaction.channel.name[1:]}"
            await interaction.channel.edit(topic=interaction.channel.topic, name=newName)
            await interaction.response.send_message("✅ Ticket marked as resolved.", ephemeral=True)
            return
        
        if interaction.guild.id == SUPPORT_SERVER_ID:
            channel_map = support_channel_map
        elif interaction.guild.id == TIERLIST_SERVER_ID:
            channel_map = tierlist_channel_map
        else:
            return

        target_channel_id = channel_map.get(flag_type.value)
        if not target_channel_id:
            await interaction.response.send_message("❌ Invalid flag type.", ephemeral=True)
            return

        target_channel = interaction.guild.get_channel(target_channel_id)
        if not target_channel:
            await interaction.response.send_message("❌ Destination channel not found.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Ticket Flagged - {flag_type.name}",
            description=f"Ticket: {interaction.channel.mention}\nNotes: {notes or 'None'}\nFlagged by: {interaction.user.mention}",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Ticket ID: {interaction.channel.id}")

        view = ResolveFlagView()
        try:
            await target_channel.send(embed=embed, view=view)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Bot lacks permissions to send messages in the target channel.", ephemeral=True)
            return

        await interaction.response.send_message(f"✅ Flag posted to {target_channel.mention}", ephemeral=True)
        newName = f"{emoji_map[flag_type.value]}{interaction.channel.name[1:]}"
        await interaction.channel.edit(topic=interaction.channel.topic, name=newName)
        
    @app_commands.command(name="response", description="Generate a AI-drafted response with the context of the ticket")
    @app_commands.describe(response_type="Select a response template or choose 'Custom'", context="Provide additional context/reason/notes to customize your response")
    @app_commands.choices(response_type=[
        app_commands.Choice(name="Appeal Rejected", value="appeal_reject"),
        app_commands.Choice(name="Appeal Accepted", value="appeal_accept"),
        app_commands.Choice(name="Need More Time", value="more_time"),
        app_commands.Choice(name="Bug Acknowledged", value="bug_ack"),
        app_commands.Choice(name="Known Bug", value="known_bug"),
        app_commands.Choice(name="Cannot Reproduce Bug", value="cannot_reproduce"),
        app_commands.Choice(name="Report Investigating", value="report_investigating"),
        app_commands.Choice(name="Report Action Taken", value="report_action"),
        app_commands.Choice(name="Report No Action Taken", value="report_no_action"),
        app_commands.Choice(name="Resolved", value="resolved"),
        app_commands.Choice(name="Custom", value="custom"),
    ])
    async def ticket_response(self, interaction: discord.Interaction, response_type: app_commands.Choice[str], context: str = None):
        prompts = {
            "appeal_reject": "informing the user that their appeal has been rejected. Reason: {context}",
            "appeal_accept": "informing the user that their appeal has been accepted. Details: {context}",
            "more_time": "explaining that we need more time to investigate or return an answer. Details: {context}",
            "bug_ack": "acknowledging the reported bug and confirming it has been forwarded to the development team. Context: {context}",
            "known_bug": "confirming the reported bug is already known and being worked on. Context: {context}",
            "cannot_reproduce": "explaining that we could not reproduce the bug and need more information. Context: {context}",
            "report_investigating": "confirming that the report has been received and will be investigated. Context: {context}",
            "report_action": "confirming that appropriate action has been taken regarding the report. Context: {context}",
            "report_no_action": "explaining that no action was taken. Context: {context}",
            "resolved": "stating that the issue appears to be resolved and the ticket will now be closed. Context: {context}",
            "custom": "based on: {context}"
        }
        prompt = prompts[response_type.value].format(context=context or "")
        from commands.Tickets.summary import generate, get_transcript
        f, user, usersInvolved, staff_message_counts = await get_transcript(interaction, interaction.channel)
        response = await generate(f"Generate a short, professional, and concise response directly addressing the user for the following ticket as a staff member, {prompt}\n{f.read()}")
        await interaction.response.send_message(response, ephemeral=True)
        
    @app_commands.command(name="button", description="Creates a ticket panel with buttons (only for applications)")
    @app_commands.describe(title="Makes the title of the embed", description="Makes the description of the embed", color="Sets the color of the embed", thumbnail="Please provide a URL for the thumbnail of the embed (upper-right hand corner image)", image="Please provide a URL for the image of the embed (appears at the bottom of the embed)", footer="Sets the footer of the embed that appears at the bottom of the embed as small texts", footer_time="Shows the time of the embed being sent?")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_button(self, interaction: discord.Interaction, title: str = None, description: str = None, color: str = None, thumbnail: str = None, image: str = None, footer: str = None, footer_time: bool = None) -> None:
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
        if footer_time is not None or footer_time == True:
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await interaction.channel.send(embed=embed, view=ApplyForStaff())
        embed = discord.Embed(title="✅ Custom Ticket Panel Sent", description="All members who have access to this channel can create a ticket by clicking the button below the panel!", color=0x00FF00)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="dropdown", description="Creates a ticket panel with dropdown menu")
    @app_commands.describe(title="Makes the title of the embed", description="Makes the description of the embed", color="Sets the color of the embed", thumbnail="Please provide a URL for the thumbnail of the embed (upper-right hand corner image)", image="Please provide a URL for the image of the embed (appears at the bottom of the embed)", footer="Sets the footer of the embed that appears at the bottom of the embed as small texts", dropdown_placeholder="Sets the placeholder of the dropdown menu", dropdown1_emoji="Sets the emoji of the first option", dropdown1_title="Sets the text of the first option (title | description)", dropdown2_emoji="Sets the emoji of the second option", dropdown2_title="Sets the text of the second option (title | description)", dropdown3_emoji="Sets the emoji of the third option", dropdown3_title="Sets the text of the third option (title | description)", dropdown4_emoji="Sets the emoji of the fourth option", dropdown4_title="Sets the text of the fourth option (title | description)", dropdown5_emoji="Sets the emoji of the fifth option", dropdown5_title="Sets the text of the fifth option (title | description)", dropdown6_emoji="Sets the emoji of the sixth option", dropdown6_title="Sets the text of the sixth option (title | description)", dropdown7_emoji="Sets the emoji of the seventh option", dropdown7_title="Sets the text of the seventh option (title | description)")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_dropdown(self, interaction: discord.Interaction, title: str = None, description: str = None, color: str = None, thumbnail: str = None, image: str = None, footer: str = None, dropdown_placeholder: str = "Select a Category", dropdown1_emoji: str = None, dropdown1_title: str = None, dropdown2_emoji: str = None, dropdown2_title: str = None, dropdown3_emoji: str = None, dropdown3_title: str = None, dropdown4_emoji: str = None, dropdown4_title: str = None, dropdown5_emoji: str = None, dropdown5_title: str = None, dropdown6_emoji: str = None, dropdown6_title: str = None, dropdown7_emoji: str = None, dropdown7_title: str = None) -> None:
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
            [dropdown1_emoji, dropdown1_title], [dropdown2_emoji, dropdown2_title],
            [dropdown3_emoji, dropdown3_title], [dropdown4_emoji, dropdown4_title],
            [dropdown5_emoji, dropdown5_title], [dropdown6_emoji, dropdown6_title],
            [dropdown7_emoji, dropdown7_title],
        ]

        for item in list:
            if item[1] is None and (item[0] is not None):
                embed = discord.Embed(title="Dropdown Menu Option's Title Missing", description="You must include a title for every option!", color=0xFF0000)
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            if item[0] is not None and item[1] is not None:
                emote = emoji.emojize(item[0].strip())
                if "|" in item[1]:
                    title = item[1].split("|")[0].strip()
                    description = item[1].split("|")[1].strip()
                else:
                    title = item[1].strip()
                    description = None
                options.append(discord.SelectOption(label=title, value=title, description=description, emoji=emote))
            elif item[0] is None and item[1] is not None:
                if "|" in item[1]:
                    title = item[1].split("|")[0].strip()
                    description = item[1].split("|")[1].strip()
                else:
                    title = item[1].strip()
                    description = None
                options.append(discord.SelectOption(label=title, value=title, description=description))

        await interaction.channel.send(embed=embed, view=SelectView(dropdown_placeholder, options))
        embed = discord.Embed(title="✅ Custom Ticket Panel Sent", description="All members who have access to this channel can create a ticket by selecting the dropdown menu below the panel!", color=0x00FF00)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    def _is_ticket_channel(self, channel: discord.TextChannel) -> bool:
        if hasattr(channel, 'category'):
            if channel.category is None:
                return False
            else:
                return channel.category.id in TARGET_TICKET_CATEGORY_IDS
        return False

    async def _get_mention_violation_count(self, channel_id: int) -> int:
        try:
            ref = db.reference(f"/Ticket Mention Violations/{channel_id}")
            count = ref.get()
            return count if count is not None else 0
        except Exception as e:
            print(f"[Mention Enforcement] Error getting violation count for {channel_id}: {e}")
            return 0

    async def _increment_mention_violations(self, channel_id: int) -> int:
        try:
            ref = db.reference(f"/Ticket Mention Violations/{channel_id}")
            current = await self._get_mention_violation_count(channel_id)
            new_count = current + 1
            ref.set(new_count)
            return new_count
        except Exception as e:
            print(f"[Mention Enforcement] Error incrementing violations for {channel_id}: {e}")
            return 0

    async def _reset_mention_violations(self, channel_id: int) -> None:
        try:
            ref = db.reference(f"/Ticket Mention Violations/{channel_id}")
            ref.delete()
        except Exception as e:
            print(f"[Mention Enforcement] Error resetting violations for {channel_id}: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Enforce no-mention policy in ticket channels."""
        if message.author == self.bot.user or message.author.bot:
            return
        if not self._is_ticket_channel(message.channel):
            return
        if message.channel.topic is None or message.channel.topic.strip() == "":
            return
        if ":no_entry_sign:" in message.channel.topic or "🚫" in message.channel.topic:
            return
        try:
            topic_parts = message.channel.topic.split()
            ticket_author_id = None
            for part in topic_parts:
                if part.isdigit():
                    ticket_author_id = int(part)
                    break
            if ticket_author_id is None:
                return
        except (ValueError, IndexError, AttributeError):
            return
        if message.author.id != ticket_author_id or is_ticket_staff_whitelisted(message.guild, message.author):
            return
        has_mentions = bool(re.search(r'<@!?\d+>|<@&\d+>|<#\d+>', message.content))
        if not has_mentions:
            return
        violation_count = await self._get_mention_violation_count(message.channel.id)
        try:
            await message.delete()
        except Exception as e:
            print(f"[Mention Enforcement] Failed to delete message: {e}")
            return
        if violation_count == 0:
            embed = discord.Embed(title="⚠️ No Mentioning in Tickets", description="Please do not mention staff members in tickets. Staff will assist you when available.", color=0xFF0000)
            embed.set_footer(text="This is your first warning. Further violations will result in a timeout and ticket closure.")
            try:
                await message.channel.send(embed=embed)
            except Exception as e:
                print(f"[Mention Enforcement] Failed to send first warning: {e}")
            await self._increment_mention_violations(message.channel.id)
        elif violation_count == 1:
            embed = discord.Embed(title="⚠️ Final Warning", description=f"You have been warned once already. Mentioning staff members is not allowed in tickets. You are now being timed out for 1 hour.", color=0xFFAA00)
            embed.set_footer(text="This is your final warning before ticket closure.")
            try:
                await message.channel.send(embed=embed)
            except Exception as e:
                print(f"[Mention Enforcement] Failed to send second warning: {e}")
            try:
                timeout_duration = datetime.timedelta(hours=1)
                await message.author.timeout(timeout_duration, reason="Mentioning in ticket channel after warning")
            except Exception as e:
                print(f"[Mention Enforcement] Failed to timeout user {message.author.id}: {e}")
            await self._increment_mention_violations(message.channel.id)
        else:
            embed = discord.Embed(title="🚫 Ticket Closed", description="You have violated the no-mention rule after multiple warnings. This ticket will now be closed.", color=0xFF0000)
            try:
                await message.channel.send(embed=embed)
            except Exception as e:
                print(f"[Mention Enforcement] Failed to send closure notice: {e}")
            class FakeInteraction:
                def __init__(self, channel, user, guild, client):
                    self.channel = channel
                    self.user = user
                    self.guild = guild
                    self.client = client
            fake_interaction = FakeInteraction(message.channel, message.author, message.guild, self.bot)
            try:
                await close_ticket_channel(fake_interaction)
            except Exception as e:
                print(f"[Mention Enforcement] Failed to close ticket: {e}")
            await self._reset_mention_violations(message.channel.id)


TARGET_TICKET_CATEGORY_IDS = [
    1374959236420730890,
    1374959248806510662,
    1374959224752312362,
    1374959260458287125,
    1374959285716647947,
    1374959273930391592,
    1338567301427101726,
    1462026697024213024,
    1462026742486011934,
    1462026779823833211,
    1462026806335897725,
]

async def ticket_maintenance_cycle(bot):
    """Run a single maintenance cycle scanning ticket channels."""
    now = datetime.datetime.now(datetime.timezone.utc)
    now_ts = int(now.timestamp())

    try:
        all_states = await asyncio.to_thread(db.reference("/Ticket Auto Notify").get) or {}
    except Exception as e:
        print(f"[ticket_maintenance] failed to fetch states: {e}")
        all_states = {}

    updates = {}

    for guild in bot.guilds:
        for channel in guild.text_channels:
            try:
                if not channel.category or channel.category.id not in TARGET_TICKET_CATEGORY_IDS:
                    continue
                if not channel.topic:
                    continue

                topic = channel.topic.strip()
                m = re.search(r"(\d{6,})", topic)
                if not m:
                    continue
                try:
                    ticket_user_id = int(m.group(1))
                except Exception:
                    continue

                msgs = [m async for m in channel.history(limit=200)]
                if not msgs:
                    continue

                last_nonbot = None
                for msg in msgs:
                    if not msg.author.bot:
                        last_nonbot = msg
                        break
                if not last_nonbot:
                    continue

                last_author_id = last_nonbot.author.id
                age = (datetime.datetime.now(datetime.timezone.utc) - last_nonbot.created_at.replace(tzinfo=datetime.timezone.utc)).total_seconds()
                state = all_states.get(str(channel.id), {})

                if last_author_id != ticket_user_id and not last_nonbot.author.bot:
                    try:
                        if channel.name and channel.name[0] in ("⚠️", "⭕"):
                            await channel.edit(name=("🟡" + channel.name[1:]))
                    except Exception:
                        pass

                    if age > 24 * 3600:
                        last_notify = state.get("last_notify_ts")
                        if not last_notify:
                            try:
                                user = bot.get_user(ticket_user_id) or await bot.fetch_user(ticket_user_id)
                                embed = discord.Embed(
                                    title="⚠️ Automatic Notification ⚠️",
                                    description=(
                                        f"We haven't heard from you in a while regarding the ticket you previously opened in **{channel.guild.name}**. To prevent your ticket from being automatically closed, please **respond within 24 hours.**\n\n"
                                        "If you no longer need assistance or your issue has been resolved, **please still let us know in the ticket** so we can help close the ticket."
                                    ),
                                    color=0xE44D41,
                                )
                                embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
                                try:
                                    button = Button(style=discord.ButtonStyle.link, label="Head over to your ticket", emoji="🎫", url=f"https://discord.com/channels/{channel.guild.id}/{channel.id}")
                                    view = View()
                                    view.add_item(button)
                                    await user.send(embed=embed, view=view)
                                except Exception:
                                    pass
                                try:
                                    await channel.send(f"<@{ticket_user_id}> This is an auto reminder to please respond within 24 hours to avoid your ticket being closed.")
                                except Exception:
                                    pass
                                updates[f"{channel.id}/last_notify_ts"] = now_ts
                            except Exception:
                                pass
                        elif now_ts - int(last_notify) >= 24 * 3600:
                            if not state.get("auto_closed"):
                                try:
                                    from types import SimpleNamespace
                                    closer = channel.guild.get_member(bot.user.id) or bot.user
                                    interaction_like = SimpleNamespace(guild=channel.guild, channel=channel, user=closer, client=bot)
                                    await close_ticket_channel(interaction_like)
                                except Exception:
                                    pass
                                finally:
                                    updates[f"{channel.id}/auto_closed"] = True
                                    updates[f"{channel.id}/auto_closed_ts"] = now_ts
                    else:
                        if "last_notify_ts" in state and state["last_notify_ts"] is not None:
                            updates[f"{channel.id}/last_notify_ts"] = None
                    
                    if state.get("auto_closed"):
                        auto_closed_ts = state.get("auto_closed_ts")
                        if auto_closed_ts and not state.get("auto_deleted"):
                            if now_ts - int(auto_closed_ts) >= 6 * 3600:
                                try:
                                    await channel.delete(reason="Auto-delete after 6 hours of auto-close")
                                    updates[f"{channel.id}/auto_deleted"] = True
                                except Exception as e:
                                    print(f"[ticket_maintenance] failed to auto-delete channel {channel.id}: {e}")

                else:
                    if "last_notify_ts" in state and state["last_notify_ts"] is not None:
                        updates[f"{channel.id}/last_notify_ts"] = None
                    if age > 24 * 3600:
                        try:
                            if channel.name and channel.name.startswith("🟡"):
                                remainder = channel.name[1:] if len(channel.name) > 1 else channel.name
                                await channel.edit(name=("⚠️" + remainder))
                                updates[f"{channel.id}/warned_ts"] = now_ts
                        except Exception:
                            pass
                    else:
                        try:
                            if channel.name and channel.name.startswith("⚠️"):
                                await channel.edit(name=("🟡" + channel.name[1:]))
                                updates[f"{channel.id}/warned_ts"] = None
                        except Exception:
                            pass

            except Exception as e:
                print(f"[ticket_maintenance] error on channel {getattr(channel,'id',None)}: {e}")

    if updates:
        try:
            await asyncio.to_thread(db.reference("/Ticket Auto Notify").update, updates)
        except Exception as e:
            print(f"[ticket_maintenance] failed to apply updates: {e}")


async def ticket_maintenance_task(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            await ticket_maintenance_cycle(bot)
        except Exception as e:
            print(f"[ticket_maintenance_task] cycle error: {e}")
        await asyncio.sleep(30 * 60)  # 30 minutes


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Ticket(bot))
    try:
        bot.loop.create_task(ticket_maintenance_task(bot))
    except Exception as e:
        print(f"Failed to start ticket maintenance task: {e}")

    all_ids = list(SUPPORT_HANDLER_REGISTRY.keys())
    for i in range(0, len(all_ids), 25):
        chunk = all_ids[i:i + 25]
        persistent_view = SupportChoiceView() 
        for custom_id in chunk:
            persistent_view.add_item(SupportActionButton(label="Ghost", custom_id=custom_id))
        bot.add_view(persistent_view)