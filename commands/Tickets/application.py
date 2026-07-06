import discord
import datetime
import asyncio
import random
import string
import os

from firebase_admin import db
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View

from commands.Tickets.tickets import check_for_admin
from constants import SERVER_IDS, CATEGORY_IDS, COOLDOWN_BYPASS_USER_IDS, ROLE_IDS, LOG_CHANNEL_IDS

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
                await interaction.client.get_guild(SERVER_IDS["staff"])
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
        description="Toggle whether a specific application should be open or closed"
    )
    @app_commands.describe(
        server="The server to toggle the application for",
        application="The application type to toggle"
    )
    @app_commands.choices(server=[
        app_commands.Choice(name="Support Server", value="support"),
        app_commands.Choice(name="Tierlist Server", value="tierlist")
    ], application=[
        app_commands.Choice(name="Staff Application", value="staff"),
        app_commands.Choice(name="Other Application (Media/Tester)", value="other")
    ])
    async def toggle_application(
        self,
        interaction: discord.Interaction,
        server: app_commands.Choice[str],
        application: app_commands.Choice[str]
    ) -> None:
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                f":x: You do not have permission to use this command.", 
                ephemeral=True
            )

        ref = db.reference(f"Application Status/{server.value}/{application.value}")
        
        current_status = ref.get()
        if current_status is None:
            current_status = True 
            
        new_status = not current_status
        ref.set(new_status)

        status_text = "🟢 **OPEN**" if new_status else "🔴 **CLOSED**"
        
        embed = discord.Embed(
            title="Application Status Updated",
            description=f"The **{application.name}** for the **{server.name.lower()}** is now {status_text}.",
            color=discord.Color.green() if new_status else discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ApplicationDelete(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Delete Channel",
        style=discord.ButtonStyle.blurple,
        custom_id="delete_channel",
        emoji="✉️",
    )
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_for_admin(interaction):
            return await interaction.response.send_message("❌ You don't have permission to use this button.", ephemeral=True)
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
        custom_id="add_applicant",
    )
    async def add_applicant(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not await check_for_admin(interaction):
            return await interaction.response.send_message("❌ You don't have permission to use this button.", ephemeral=True)
        user = interaction.guild.get_member(
            int(interaction.message.embeds[0].description.split("`")[1])
        )
        await interaction.channel.set_permissions(
            user, send_messages=True, read_messages=True, attach_files=True
        )
        embed = discord.Embed(
            title="You have been added to a ticket channel!",
            description=f"MystiCraft Management Team has added you to this ticket channel to discuss your application further. Please respond timely.",
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
        label="Accept", style=discord.ButtonStyle.green, custom_id="accept_app"
    )
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_for_admin(interaction):
            return await interaction.response.send_message("❌ You don't have permission to use this button.", ephemeral=True)
        if len(interaction.message.embeds) == 0:
            user = interaction.guild.get_member(int(interaction.message.content.split("`")[1]))
        else:
            user = interaction.guild.get_member(int(interaction.message.embeds[0].description.split("`")[1]))

        if "staff" in interaction.message.embeds[0].title.lower():
            if interaction.guild.id == SERVER_IDS["support"]:
                invite = (
                    await interaction.client.get_guild(SERVER_IDS["interview"])
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
            else:
                invite = (
                    await interaction.client.get_guild(SERVER_IDS["staff"])
                    .text_channels[0]
                    .create_invite(max_age=604800, max_uses=1)
                )
                embed = discord.Embed(
                    title="MystiTiers Staff Application Update 🎉",
                    description=(
                        f"Thank you for applying for a staff position at **MystiTiers**! After reviewing your application, "
                        f"we are pleased to inform you that you have **passed the application process** and are now officially invited to our Staff Team. 🎊\n\n"
                        f"📌 **Please use this [one-time invite]({invite}) to join our staff server**!"
                    ),
                    color=0x00FF00,
                )
                await user.send(embed=embed)
        else:
            app_type = "media application" if interaction.guild.id == SERVER_IDS["support"] else "tierlist tester application"
            embed = discord.Embed(
                title="You are accepted! :tada:",
                description=f"Congratulations! Your {app_type} is accepted by the management team! Please check any pings you receive to receive next steps and further instructions.",
                color=0x00FF00,
            )
            await user.send(embed=embed)

        update_embed = interaction.message.embeds[0]
        update_embed.color = discord.Color.green()
        await interaction.message.edit(
            content=f"✅ Accepted by {interaction.user.mention}", embed=update_embed, view=ApplicationDelete()
        )
        await interaction.response.send_message("Application accepted.", ephemeral=True)

    @discord.ui.button(
        label="Reject", style=discord.ButtonStyle.red, custom_id="reject_app"
    )
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_for_admin(interaction):
            return await interaction.response.send_message("❌ You don't have permission to use this button.", ephemeral=True)
        if len(interaction.message.embeds) == 0:
            user = interaction.guild.get_member(int(interaction.message.content.split("`")[1]))
        else:
            user = interaction.guild.get_member(int(interaction.message.embeds[0].description.split("`")[1]))

        if "staff" in interaction.message.embeds[0].title.lower():
            embed = discord.Embed(
                title="You are rejected! :pensive:",
                description="Thank you so much for applying for staff. We receive numerous incredible applications every single day and unfortunately, we aren't able to accept you at this time. \n\nWe are unable to give everyone who applies a specific reason for denial, but do note that the review process is a separate, manual process done one-by-one by our management team with the server owner. During the review process, there are a lot of factors that get considered for each application. \n\nDon't fret - you're always welcome to reapply in the future. In order to reapply, you'll have to wait 30 days from today. Applications sent from you during the waiting period will be ignored.\n\nOnce again, due to the high volume of applications, we're currently unable to provide any more details or specifics about the nature of your application. We really hope you're not too discouraged by the news, and remember; this decision in no way speaks to the value, joy, and belonging you bring to your community every day.",
                color=0xFF0000,
            )
        else:
            app_type = "media application" if interaction.guild.id == SERVER_IDS["support"] else "tierlist tester application"
            embed = discord.Embed(
                title="You are rejected! :pensive:",
                description=f"Thank you so much for submitting your {app_type}. Unfortunately, we aren't able to accept you at this time. \n\nWe are unable to give everyone who applies a specific reason for denial, but do note that the review process is a separate, manual process done one-by-one by our management team with the server owner. During the review process, there are a lot of factors that get considered for each application. \n\nDon't fret - you're always welcome to reapply in the future. In order to reapply, you'll have to wait 30 days from today. Applications sent from you during the waiting period will be ignored.\n\nWe really hope you're not too discouraged by the news, and remember; this decision in no way speaks to the value, joy, and belonging you bring to your community every day.",
                color=0xFF0000,
            )
            
        await user.send(embed=embed)

        update_embed = interaction.message.embeds[0]
        update_embed.color = discord.Color.red()
        await interaction.message.edit(
            content=f":x: Rejected by {interaction.user.mention}", embed=update_embed, view=ApplicationDelete()
        )
        await interaction.response.send_message("Application rejected.", ephemeral=True)

    @discord.ui.button(
        label="Add to Channel", style=discord.ButtonStyle.grey, custom_id="add_applicant_to_channel"
    )
    async def add_applicant(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_for_admin(interaction):    
            return await interaction.response.send_message("❌ You don't have permission to use this button.", ephemeral=True)
        user = interaction.guild.get_member(int(interaction.message.embeds[0].description.split("`")[1]))
        application = "staff application" if "staff" in interaction.message.embeds[0].title.lower() else "media application"
        await interaction.channel.set_permissions(user, send_messages=True, read_messages=True, attach_files=True)
        
        embed = discord.Embed(
            title="You have been added to a ticket channel!",
            description=f"An administrator or manager has added you to this channel to discuss your **{application}** further. Thank you for your interest!",
            color=discord.Color.yellow(),
        )
        
        link_button = Button(
            style=discord.ButtonStyle.link,
            label="View Ticket",
            url=f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}",
        )
        view = View()
        view.add_item(link_button)
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

class ApplicationCancelled(Exception):
    pass

class ApplicationButton(discord.ui.Button):
    def __init__(self, label, style, custom_id, emoji, callback):
        super().__init__(label=label, style=style, custom_id=custom_id, emoji=emoji)
        self.callback_func = callback

    async def callback(self, interaction: discord.Interaction):
        await self.callback_func(interaction)

class ApplicationView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)

        if guild_id == SERVER_IDS["support"]:
            staff_label = "Staff Application"
            other_label = "Media Application"
        elif guild_id == SERVER_IDS["tierlist"]:
            staff_label = "Staff Application"
            other_label = "Tester Application"

        self.add_item(
            ApplicationButton(
                label=staff_label,
                style=discord.ButtonStyle.grey,
                custom_id="staffapp",
                emoji="📝",
                callback=self.process_application,
            )
        )
        self.add_item(
            ApplicationButton(
                label=other_label,
                style=discord.ButtonStyle.grey,
                custom_id="otherapp",
                emoji="📝",
                callback=self.process_application,
            )
        )

    async def process_application(self, interaction: discord.Interaction):
        is_staff = "staffapp" in interaction.data["custom_id"]
        status_ref = db.reference(f"Application Status/{'support' if interaction.guild.id == SERVER_IDS['support'] else 'tierlist'}/{'staff' if is_staff else 'other'}")
        is_open = status_ref.get()

        if is_open is False:
            return await interaction.response.send_message(
                content="❌ Sorry! This application is currently closed. Please check back later!",
                ephemeral=True
            )
        
        if interaction.guild.id == SERVER_IDS["support"]:
            app_type = "staff" if is_staff else "media"
            db_cooldown_path = "/Staff App Cooldown" if is_staff else "/Media App Cooldown"
            category_key = "staff" if is_staff else "media"
            log_title = "Staff Application" if is_staff else "Media Application"
            cooldown_days = 30
            
            if is_staff:
                requirements = (
                    "### <:mysticraftlogo:1263829753366974535> **Here are some of the requirements that you must fufill:**\n"
                    "*You must meet all requirements to qualify, though meeting them does not guarantee acceptance*\n\n"
                    "- You must be able to speak in calls confidently.\n"
                    "- You must have a working microphone.\n"
                    "- You must be able to screen record and screenshot on your device.\n"
                    "- You must take responsibility for your actions \n"
                    "- You must be **at least 14 years of age**.\n"
                    "- You must have a premium Minecraft account\n\n"
                    "-# If you believe you are qualified for staff member, go ahead and answer the following questions."""
                )
                questions = [
                    "What is your Minecraft in-game name?",
                    "What is your age?",
                    "What country do you live in and what is your timezone?",
                    "Do you have a premium or cracked Minecraft account?",
                    "How long have you been playing Minecraft?",
                    "What is your favourite realm on MystiCraft?",
                    "Do you have a working microphone, and are you able to screen share/screen record gameplay?",
                    "Do you have previous staff experience? If so, Please list them.",
                    "Do you have experience with screensharing tools (Ocean, Echo, Paladin, etc.)?",
                    "Do you have experience with world editors like WorldEdit or WorldPainter?",
                    "What is your greatest strength you would bring as a staff member?",
                    "What is your biggest weakness, and how do you work on it?",
                    "Explain what a good staff member is (50+ words).",
                    "Why do you want to become a staff member on MystiCraft, and how many hours per week can you dedicate?",
                    "Before we submit your application, is there anything else you would like us to know?"
                ]
            else:
                requirements = (
                    "### <:mysticraftlogo:1263829753366974535> **Here are some of the requirements that you must fufill:**\n"
                    "*Only one requirement is needed to qualify, though meeting them does not guarantee acceptance*\n\n"
                    "- **10** average live concurrent viewers on a **Twitch** or **YouTube longform** livestream (no boosted raids)\n"
                    "- **10** average live concurrent viewers on a **TikTok** or **YouTube Shorts** livestream\n"
                    "- **500** views on a **YouTube** video\n"
                    "- **3,000** views on a **TikTok **video\n"
                    "- **3,000** views on a **YouTube** Short\n"
                    "- **1,500** views on an **Instagram** Reel\n\n"
                    "-# If you meet at least one of the above requirements, go ahead and answer the following questions."
                )
                questions = [
                    "On which platform are you most comfortable to make videos on? (*example: YouTube, Twitch etc.*)",
                    "Provide us with a link of the platform channel/profile you will be uploading content on.",
                    "List the amount of audience base/followers/subscribers you currently have.",
                    "What do you appreciate about our Minecraft community server, and what motivated you to apply for a media role here?",
                    "How much time can you commit to creating and managing media content for the server on a weekly basis?",
                    "Estimate your average views per long and short form video uploaded, as well as your total amount of views.",
                    "What will you create content about? Do you have any content ideas in mind that you would like to share with us?",
                    "Before we submit your application, is there anything else you would like us to know?",
                ]
        elif interaction.guild.id == SERVER_IDS["tierlist"]:
            app_type = "staff" if is_staff else "tester"
            db_cooldown_path = "/Staff App Cooldown" if is_staff else "/Tester App Cooldown"
            category_key = "staff" if is_staff else "tester"
            log_title = "Tierlist Staff Application" if is_staff else "Tester Application"
            cooldown_days = 30 if is_staff else 7
            
            if is_staff:
                requirements = (
                    "### <:mysticraftlogo:1263829753366974535> **Here are some of the requirements that you must fufill:**\n"
                    "*You must meet all requirements to qualify, though meeting them does not guarantee acceptance*\n\n"
                    "- You must take responsibility for your actions \n"
                    "- You must be **at least 14 years of age**.\n\n"
                    "-# If you believe you are qualified for staff member, go ahead and answer the following questions."""
                )
                questions = [
                    "What is your Minecraft in-game name?",
                    "What is your age?",
                    "What country do you live in and what is your timezone?",
                    "Do you have a premium or cracked Minecraft account?",
                    "How long have you been playing Minecraft?",
                    "Why do you want to join the MystiTiers staff team? Why do you believe you would be a good fit for this position?",
                    "Do you have previous staff experience? If so, Please list them.",
                    "How would you handle a difficult or toxic player?",
                    "What would you do if two players were involved in a dispute and both claimed to be correct?",
                    "How would you respond if you witnessed another staff member breaking the rules?",
                    "What would you do if a friend broke the rules?",
                    "In general, how do you handle stressful situations while moderating?",
                    "What is your greatest strength you would bring as a staff member?",
                    "What is your biggest weakness, and how do you work on it?",
                    "Explain what a good staff member is (50+ words).",
                    "How many hours per week can you dedicate on MystiTiers?",
                    "Before we submit your application, is there anything else you would like us to know?"
                ]
            else:
                requirements = (
                    "### <:mysticraftlogo:1263829753366974535> **Here are some of the requirements that you must fufill:**\n"
                    "*You must meet all requirements to qualify, though meeting them does not guarantee acceptance*\n\n"
                    "- You must take responsibility for your actions \n"
                    "- You must be LT3+ in your preferred gamemode (MystiTiers, MCTiers, or PvPTiers) \n"
                    "- You must be **at least 14 years of age**.\n\n"
                    "-# If you believe you are qualified for tester role, go ahead and answer the following questions."""
                )
                questions = [
                    "What is your Minecraft in-game name?",
                    "What is your age?",
                    "What country do you live in and what is your timezone?",
                    "Do you have a premium or cracked Minecraft account?",
                    "How long have you been playing Minecraft?",
                    "Which gamemodes do you wish to become a tester for? (You must be LT3 in the gamemode to qualify)",
                    "Why do you want to become a tester for MystiTiers?",
                    "How many hours per week can you dedicate on MystiTiers?",
                    "Before we submit your application, is there anything else you would like us to know?",
                ]

                if not any(tier in role.name for role in interaction.user.roles if "[" not in role.name and "]" not in role.name for tier in ["LT3", "HT3", "LT2", "HT2"]):
                    return await interaction.response.send_message(content="❌ You must have at least a LT3+ gamemode role to apply for a tester position.", ephemeral=True)

        ref = db.reference(db_cooldown_path)
        ticketcooldown = ref.get() or {}
        for key, value in ticketcooldown.items():
            if value.get("User ID") == interaction.user.id:
                LAST_CREATED = value["Timestamp"]
                if (int(interaction.created_at.timestamp()) - int(LAST_CREATED)) < cooldown_days * 86400 and interaction.user.id not in COOLDOWN_BYPASS_USER_IDS:
                    return await interaction.response.send_message(
                        content=f"You are on a cooldown. Try again <t:{int(LAST_CREATED) + cooldown_days * 86400}:R>",
                        ephemeral=True,
                    )
                db.reference(db_cooldown_path).child(key).delete()
                break

        try:
            embed = discord.Embed(title=f"{'MystiCraft' if interaction.guild.id == SERVER_IDS['support'] else 'MystiTiers'} {app_type.capitalize()} Application", description=(
                f"Hello there! Thanks for applying for {app_type} positions in our server. Please answer them as fully and accurately as possible.\n\n"
                f"1. **Avoid using generative AI tools** and be as concise as possible.\n"
                f"2. You can enter links in your answers, but DO NOT upload files directly on Discord.\n"
                f"3. Maximum character limit per question: `1000` characters"
            ), color=discord.Color.blurple())
            await interaction.user.send(embed=embed)
        except Exception:
            return await interaction.response.send_message("Please turn on Direct Messages to access the application. Try again!", ephemeral=True)

        await interaction.response.send_message(":envelope_with_arrow: Please proceed to your DMs to finish the application.", ephemeral=True)
        cancelNotice = 'All answers will be kept confidential. Type "cancel" to stop the application.'

        def check(message):
            if message.content.lower() == "cancel" and message.author == interaction.user and isinstance(message.channel, discord.DMChannel):
                raise ApplicationCancelled()
            return message.author == interaction.user and isinstance(message.channel, discord.DMChannel)

        embed = discord.Embed(description=f"{requirements} Otherwise, you may type \"cancel\" to terminate your application. Your answers will not be saved.", color=discord.Color.blurple())
        await interaction.user.send(embed=embed)

        print(f"Application started for {interaction.user} ({interaction.user.id}) - {app_type} application")

        answers = []
        try:
            for index, question in enumerate(questions):
                while True:
                    embed = discord.Embed(title=f"Question #{index + 1}", description=question, color=0xADD8E6)
                    embed.set_footer(text=cancelNotice)
                    await interaction.user.send(embed=embed)
                    answer_msg = await interaction.client.wait_for("message", check=check, timeout=15*60)
                    if len(answer_msg.content) <= 1000:
                        answers.append(answer_msg.content)
                        break
                    await answer_msg.reply(embed=discord.Embed(description=f"Your answer is too long (**`{len(answer_msg.content)}`** / `1000` characters). Please shorten your response and try again.", color=discord.Color.red()))
        except ApplicationCancelled:
            await interaction.user.send(embed=discord.Embed(title="Application Cancelled", description="Your application has been cancelled and your answers have not been saved. If this was a mistake, feel free to start a new application just like how you did before.", color=0xFF0000))
            print(f"Application cancelled for {interaction.user} ({interaction.user.id}) - {app_type} application")
            return
        except asyncio.TimeoutError:
            await interaction.user.send(embed=discord.Embed(title="Application Timed Out", description="Your application has been cancelled due to inactivity. Your answers have not been saved. Please start a new application just like how you did before if you still wish to apply.", color=0xFF0000))
            print(f"Application timed out for {interaction.user} ({interaction.user.id}) - {app_type} application")
            return
        
        embed = discord.Embed(title="Application Submitting...", description="Hang tight... your answers are being submitted... :coffee:", color=0xFFFF00)
        waitmsg = await interaction.user.send(embed=embed)

        ref = db.reference("/Tickets")
        tickets = ref.get() or {}
        found = False
        for key, value in tickets.items():
            if value.get("Server ID") == interaction.guild.id:
                CATEGORY_ID = value["Category ID"]
                found = True
                break

        if not found:
            embed = discord.Embed(
                title="Ticket not enabled!",
                description="This server does not have a ticket category or a log channel. Please ask the server admin to use </ticket setup:1033188985587109910> to setup tickets!",
                colour=0xFF0000,
            )
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            return await interaction.followup.send(embed=embed, ephemeral=True)

        category = interaction.guild.get_channel(CATEGORY_IDS[f'{interaction.guild.id} application'][category_key])

        chn = await interaction.guild.create_text_channel(f"{interaction.user.name}", category=category)
        await chn.edit(topic=f"Applicant ID: {interaction.user.id}")

        log = interaction.guild.get_channel(LOG_CHANNEL_IDS[f'{interaction.guild.id} application'])
        embed = discord.Embed(
            title=log_title,
            description=f"{interaction.user.mention} submitted a new **{app_type}** application <t:{int(chn.created_at.timestamp())}:R>!",
            color=discord.Colour.green(),
        )
        try:
            embed.set_author(name=f"{interaction.user.name}", icon_url=interaction.user.avatar.url)
        except Exception:
            embed.set_author(name=f"{interaction.user.name}")
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        embed.set_footer(text=f"User ID: {interaction.user.id}")
        
        filename = f"./commands/Tickets/transcript/{app_type.title()}_Application_{interaction.user.id}_{''.join(random.choices(string.ascii_letters + string.digits, k=10))}.txt"
        
        with open(filename, "w") as f:
            for i, answer in enumerate(answers):
                f.write(f"{i + 1}. {questions[i]}\n\n{answer}\n\n")
                
        view = View()
        view.add_item(Button(style=discord.ButtonStyle.link, label="View Application", url=f"https://discord.com/channels/{interaction.guild.id}/{chn.id}"))
        await log.send(file=discord.File(filename), embed=embed, view=view)
        
        try:
            os.remove(filename)
        except Exception:
            pass

        roles = interaction.user.roles
        roles.reverse()

        overview_embed = discord.Embed(
            title=f"New {app_type.capitalize()} Application", 
            description="This ticket is not visible to the applicant. You can add them to this channel using the button below if you want to ask them follow-up questions.", 
            color=discord.Colour.gold()
        )
        overview_embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        overview_embed.add_field(name="User Mention", value=f"{interaction.user.mention}", inline=True)
        overview_embed.add_field(name="User ID", value=f"{interaction.user.id}", inline=True)
        overview_embed.add_field(name="Highest Role", value=f"{roles[0].mention}", inline=True)
        overview_embed.add_field(name="Ticket Created", value=f"<t:{int(chn.created_at.timestamp())}:R>", inline=True)
        overview_embed.add_field(name="Server Joined", value=f"<t:{int(interaction.user.joined_at.timestamp())}:R>", inline=True)
        overview_embed.add_field(name="Account Created", value=f"<t:{int(interaction.user.created_at.timestamp())}:R>", inline=True)

        if interaction.guild.id == SERVER_IDS["tierlist"]:
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
            current_rank_roles = [r for r in interaction.user.roles if any(tier in r.name for tier in ["HT", "LT"])]

            overview_embed.add_field(name="Linked IGN", value=f"[{linked_ign}](https://tierlist.mysticraft.xyz/?player={linked_ign})" if linked_ign != "None" else "<:no:1036810470860013639> Not Linked", inline=True)
            overview_embed.add_field(name="Region", value=recorded_region, inline=True)
            overview_embed.add_field(name="Current Tiers", value=", ".join([r.mention for r in current_rank_roles]) if current_rank_roles else "None", inline=True)

        await chn.send(f"**Applicant: {interaction.user.mention}**", embed=overview_embed)

        response_embed = discord.Embed(title=f"{app_type.capitalize()} Application Responses", color=0xFFFF00)
        characters = len(response_embed.title) 

        for i, answer in enumerate(answers):
            field_name = f"{i + 1}. {questions[i]}"
            field_value = f"{answer}"
            if len(field_name) > 256 or len(field_value) > 1024:
                field_name = field_name[:253] + "..." if len(field_name) > 256 else field_name
                field_value = field_value[:1015] + "...```" if len(field_value) > 1024 else field_value
            if len(response_embed.fields) >= 25 or (characters + len(field_name) + len(field_value)) > 5500:
                await chn.send(embed=response_embed)
                response_embed = discord.Embed(color=0xFFFF00)
                characters = len(response_embed.title) if response_embed.title else 0
            response_embed.add_field(name=field_name, value=field_value, inline=False)
            characters += len(field_name) + len(field_value)

        if len(response_embed.fields) > 0:
            await chn.send(embed=response_embed)

        action_embed = discord.Embed(
            title=f"{log_title} Review Panel",
            description=f"Applicant: {interaction.user.mention} (ID: `{interaction.user.id}`)",
            color=0x1ec7f1
        )

        if is_staff:
            if interaction.guild.id == SERVER_IDS["support"]:
                accept_value = "-# DMs the user an one-time invite link to the interview server. If they pass their interview, use </application accept:1459793478358667480>."
            else:
                accept_value = "-# DMs the user a congratulatory message with an one-time invite link to the staff server."
        else:
            accept_value = "-# DMs the user a congratulatory message with no additional information. You will need to onboard them properly."
        
        action_embed.add_field(
            name="Accept", 
            value=accept_value, 
            inline=True
        )
        action_embed.add_field(
            name="Reject", 
            value="-# DMs the user a warm rejection message, where they can reapply after 30 days.", 
            inline=True
        )
        action_embed.add_field(
            name="Add to Channel", 
            value="-# Adds the applicant directly into this ticket channel to ask them follow-up questions.", 
            inline=True
        )
        
        action_embed.set_footer(text="This channel can be deleted after accepting or rejecting the applicant.")
        await chn.send(embed=action_embed, view=AcceptRejectButton())

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
        ref = db.reference(db_cooldown_path)
        for key, value in data.items():
            ref.push().set(value)

        print(f"Application submitted for {interaction.user} ({interaction.user.id}) - {app_type} application")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StaffApp(bot))
