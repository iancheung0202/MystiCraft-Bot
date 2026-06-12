import discord
import re

from types import SimpleNamespace

from constants import SUPPORT_ROLE_IDS, SERVER_IDS, ROLE_IDS

async def is_linked(user, client):
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
        main_guild = client.get_guild(SERVER_IDS["main"])
        member = main_guild.get_member(user.id)
        if member is None:
            member = await main_guild.fetch_member(user.id)

        if member is None:
            return False, None

        linked_role = main_guild.get_role(ROLE_IDS[SERVER_IDS["main"]]["linked"])
        if linked_role not in member.roles:
            return False, None

        nickname = member.nick or member.display_name or ""
        match = re.search(r"\[(.+?)\]$", nickname)
        if match:
            return True, match.group(1).strip()
    except Exception:
        pass

    return False, None

class SupportActionButton(discord.ui.Button):
    def __init__(self, *, label: str, custom_id: str, style: discord.ButtonStyle = discord.ButtonStyle.grey, emoji=None, opens_modal: bool = False):
        super().__init__(label=label, style=style, emoji=emoji, custom_id=custom_id)
        self._opens_modal = opens_modal

    async def callback(self, interaction: discord.Interaction):
        entry = SUPPORT_HANDLER_REGISTRY.get(self.custom_id)
        if not entry:
            return
        handler, opens_modal = entry

        if opens_modal:
            await handler(interaction)
        else:
            selected_view = discord.ui.View()
            selected_view.add_item(discord.ui.Button(label=self.label, style=self.style, emoji=self.emoji, disabled=True))
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
        super().__init__(timeout=None)
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
    from commands.Tickets.tickets import get_ticket_owner_id, CloseTicketButton
    owner_id = get_ticket_owner_id(channel)
    owner = interaction.guild.get_member(owner_id) if owner_id else interaction.user
    ping_role = interaction.guild.get_role(SUPPORT_ROLE_IDS[interaction.guild.id]) if ping_staff else None

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
    from commands.Tickets.tickets import get_ticket_owner_id
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
    from commands.Tickets.tickets import CloseTicketButton
    await post_support_outcome(
        interaction, title=title, description=description,
        color=color, view=CloseTicketButton(), unlock=False, ping_staff=False,
    )


async def _st_send_final(interaction, title: str, description: str, data: dict, *, view=None, color: int = 0x4F9EF5, ping_everyone: bool = False):
    from commands.Tickets.tickets import CloseTicketButton
    await post_support_outcome(
        interaction, title=title, description=description,
        color=color, view=view or CloseTicketButton(),
        fields=list(data.items()) if data is not None else None, unlock=True, ping_staff=not ping_everyone, ping_everyone=ping_everyone,
    )


async def _st_send_instructions(interaction, title: str, description: str, view: discord.ui.View):
    from commands.Tickets.tickets import CloseTicketButton
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
        from commands.Tickets.appeals import AppealCloseTicketButton
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
):
    # Wrap in a SimpleNamespace so helpers can use .channel / .guild / etc.
    ns = SimpleNamespace( channel=ticket_channel, guild=interaction.guild, client=interaction.client, user=interaction.user)
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

async def setup(bot):
    all_ids = list(SUPPORT_HANDLER_REGISTRY.keys())
    for i in range(0, len(all_ids), 25):
        chunk = all_ids[i:i + 25]
        persistent_view = SupportChoiceView() 
        for custom_id in chunk:
            persistent_view.add_item(SupportActionButton(label="Ghost", custom_id=custom_id))
        bot.add_view(persistent_view)