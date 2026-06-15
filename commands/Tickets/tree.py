import discord
import re

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
    def __init__(self, *, label: str, custom_id: str, style: discord.ButtonStyle = discord.ButtonStyle.grey, emoji=None, opens_modal: bool = False, channel: discord.TextChannel = None):
        super().__init__(label=label, style=style, emoji=emoji, custom_id=custom_id)
        self._opens_modal = opens_modal
        self._channel = channel

    async def callback(self, interaction: discord.Interaction):
        entry = SUPPORT_HANDLER_REGISTRY.get(self.custom_id)
        if not entry:
            return
        handler, opens_modal = entry

        current_channel = self._channel or interaction.channel

        if opens_modal:
            await handler(interaction, channel=current_channel)
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
            await handler(interaction, channel=current_channel)


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

async def owner_only(interaction: discord.Interaction) -> bool:
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

async def post_support_outcome(interaction, *, title: str, description: str, color=0x4F9EF5, view=None, fields=None, unlock: bool = False, ping_staff: bool = False, ping_everyone: bool = False, channel=None):
    if channel is None:
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


async def send_close_button(interaction, title: str, description: str, *, color: int = 0xFF0000, channel=None):
    from commands.Tickets.tickets import CloseTicketButton
    await post_support_outcome(interaction, title=title, description=description, color=color, view=CloseTicketButton(), unlock=False, ping_staff=False, channel=channel)


async def send_final(interaction, title: str, description: str, data: dict, *, view=None, color: int = 0x4F9EF5, ping_everyone: bool = False, channel=None):
    from commands.Tickets.tickets import CloseTicketButton
    await post_support_outcome(interaction, title=title, description=description, color=color, view=view or CloseTicketButton(), fields=list(data.items()) if data is not None else None, unlock=True, ping_staff=not ping_everyone, ping_everyone=ping_everyone, channel=channel)


async def send_instructions(interaction, title: str, description: str, view: discord.ui.View, channel=None):
    from commands.Tickets.tickets import CloseTicketButton
    close_view = CloseTicketButton()
    for item in close_view.children:
        view.add_item(item)
    embed = discord.Embed(title=title, description=description, color=0x4F9EF5)
    if LINK_INSTRUCTIONS in description:
        embed.set_image(url="https://media.discordapp.net/attachments/741540685852835871/1500668562178572428/Screenshot_20260503-182038.Discord.png?ex=69f94602&is=69f7f482&hm=6d563648ab50f0c3b00dcae99d02b55f6b5cbece7c2ef3131ef9b4ae2a38a136&=")
        embed.set_footer(text="DM the code to one of these bots depending on which gamemode you use /link in")
    await channel.send(embed=embed, view=view)

LINK_INSTRUCTIONS = (
    "1. Join the [main Discord server](https://discord.gg/mysticraft) if you haven't already\n"
    "2. Use `/link` in any gamemodes (Lifesteal/Practice/Survival/Vanilla) to get a code\n"
    "3. DM the **4-digit code** to the corresponding Discord bot.\n"
    "4. Once linked, staff will reset your password within 1-3 days."
)

BUG_FIELDS = [
    ("IGN", "What is your in-game name?", True),
    ("Bug Description", "Describe the bug and how to reproduce it", True),
    ("Link to Video Proof of Bug", "Paste the video link", True),
]

SUPPORT_TREE: dict[str, dict] = {

    "password reset": {
        "type": "dynamic",
    },
    "password reset can login": {
        "type": "prompt",
        "title": "Password Reset (Linking Instructions)",
        "description": LINK_INSTRUCTIONS,
        "buttons": [
            {"label": "I've finished linking", "next": "password reset verify", "style": discord.ButtonStyle.green},
        ],
    },
    "password reset verify": {
        "type": "dynamic",
    },
    "password reset verify again": {
        "type": "dynamic",
    },
    "password reset cannot login": {
        "type": "close",
        "title": "Password Reset",
        "description": (
            "Unfortunately, verification is impossible without a prior link to your account. "
            "Please continue to play on MystiCraft with an alt account."
        ),
    },

    "other questions": {
        "type": "prompt",
        "title": "Server Questions",
        "description": "Choose a topic that you need help with. If you have a question not listed here, select **Other Questions**.",
        "buttons": [
            {"label": "How to Link Account",               "next": "how to link"},
            {"label": "Switching from Cracked to Premium", "next": "switch from cracked to premium"},
            {"label": "Other Questions",                   "next": "other issues"},
        ],
    },
    "how to link": {
        "type": "close",
        "title": "How to Link Your Account",
        "description": LINK_INSTRUCTIONS,
        "color": 0x4F9EF5,
    },
    "switch from cracked to premium": {
        "type": "close",
        "title": "Switching from Cracked to Premium",
        "description": (
            "Log in with your cracked account, run `/premium <yourpassword>`, log out, "
            "then log back in with your premium account.\n\n"
            "Your premium account must have the **exact same username** as your cracked "
            "account, and the cracked account will no longer be used after migration."
        ),
        "color": 0x4F9EF5,
    },
    "other issues": {
        "type": "prompt",
        "title": "Other Questions or Issues",
        "description": "Are you reporting a player/staff member, reporting a bug, or appealing for a punishment?",
        "buttons": [
            {"label": "Yes", "next": "other issues yes", "style": discord.ButtonStyle.green},
            {"label": "No",  "next": "other issues no",  "style": discord.ButtonStyle.red, "opens_modal": True},
        ],
    },
    "other issues yes": {
        "type": "close",
        "title": "Wrong Category",
        "description": (
            "You created the wrong type of ticket. Please close this ticket and create a new ticket "
            "with the correct category in <#1373881299651268710>."
        ),
    },
    "other issues no": {
        "type": "modal",
        "modal": {
            "title": "Server Question",
            "fields": [
                ("IGN",      "What is your in-game name?",  True),
                ("Question", "What would you like to ask?", True),
            ],
            "result_title":       "Server Questions",
            "result_description": "Thanks! Staff will review your question shortly.",
        },
    },

    "billing support": {
        "type": "prompt",
        "title": "Billing Support",
        "description": "Choose the billing issue that best matches your request.",
        "buttons": [
            {"label": "I haven't received my purchase", "next": "billing purchase",  "opens_modal": True},
            {"label": "I want to request a refund",     "next": "billing refund",    "opens_modal": True},
            {"label": "I want to transfer a rank",      "next": "billing transfer"},
        ],
    },
    "billing purchase": {
        "type": "modal",
        "modal": {
            "title": "Billing Support",
            "fields": [
                ("IGN",                   "What is your in-game name?",             True),
                ("Transaction ID/Email",  "Transaction ID or email used",           True),
                ("Description/Reason",    "Describe the issue", True),
            ],
            "result_title":       "Billing Support",
            "result_description": "Thanks! Staff will review your billing request shortly.",
        },
    },
    "billing refund": {
        "type": "modal",
        "modal": {
            "title": "Billing Support",
            "fields": [
                ("IGN",                   "What is your in-game name?",             True),
                ("Transaction ID/Email",  "Transaction ID or email used",           True),
                ("Description/Reason",    "Describe reason for refund", True),
            ],
            "result_title":       "Billing Support",
            "result_description": "Thanks! Staff will review your billing request shortly.",
        },
    },
    "billing transfer": {
        "type": "close",
        "title": "Rank Transfer",
        "description": "Purchases, ranks, and perks are **non-transferable**.",
    },

    "punishment appeals": {
        "type": "prompt",
        "title": "Punishment Appeal",
        "description": (
            "Choose the appeal type that matches your case. Be sincere and talk about how you were "
            "unfairly punished or deserve a second chance."
        ),
        "buttons": [
            {"label": "My in-game punishment",  "next": "punishment appeal mc",     "opens_modal": True},
            {"label": "My Discord punishment",  "next": "punishment appeal dc",     "opens_modal": True},
            {"label": "My friend's punishment", "next": "punishment appeal friend"},
        ],
    },
    "punishment appeal mc": {
        "type": "modal",
        "modal": {
            "title": "Minecraft Appeal",
            "fields": [
                ("IGN",                  "What is your in-game name?",            True),
                ("Punishment Reason/ID", "Reason or ID of the punishment",        True),
                ("Appeal Statement",     "Why should the punishment be removed?", True),
            ],
            "result_title":       "Minecraft Punishment Appeal",
            "result_description": (
                "Your appeal has been submitted. Staff will review it shortly. "
                "We do not guarantee that we will accept your appeal. Our decision is final "
                "(meaning you cannot appeal your appeal decision), and you can appeal again "
                "in 14 days if it is rejected."
            ),
            "use_appeal_close_button": True,
        },
    },
    "punishment appeal dc": {
        "type": "modal",
        "modal": {
            "title": "Discord Appeal",
            "fields": [
                ("Discord Username",  "Your Discord username",                    True),
                ("Reason",           "Reason for the punishment",                 True),
                ("Appeal Statement", "Why should the punishment be removed?",     True),
            ],
            "result_title":       "Discord Punishment Appeal",
            "result_description": (
                "Your appeal has been submitted. Staff will review it shortly. "
                "We do not guarantee that we will accept your appeal. Our decision is final "
                "(meaning you cannot appeal your appeal decision), and you can appeal again "
                "in 14 days if it is rejected."
            ),
        },
    },
    "punishment appeal friend": {
        "type": "close",
        "title": "Appeal Rejected",
        "description": "We do not process appeals initiated for other people.",
    },

    "player reports": {
        "type": "prompt",
        "title": "Player Report",
        "description": "Choose the type of behaviour you want to report.",
        "buttons": [
            {"label": "Cheating / Hacking", "next": "player report cheat"},
            {"label": "Chat Misbehavior",   "next": "player report chat"},
        ],
    },
    "player report cheat": {
        "type": "prompt",
        "title": "Player Report (Cheating)",
        "description": "Do you have clear video evidence?",
        "buttons": [
            {"label": "Yes", "next": "player report cheat video", "style": discord.ButtonStyle.green, "opens_modal": True},
            {"label": "No",  "next": "player report cheat no video",  "style": discord.ButtonStyle.red},
        ],
    },
    "player report cheat video": {
        "type": "modal",
        "modal": {
            "title": "Player Report",
            "fields": [
                ("Offender IGN",       "Offending player's in-game name", True),
                ("Description",        "Describe what happened",           True),
                ("Link to Video Proof", "Paste the video link",            True),
            ],
            "result_title":       "Player Report",
            "result_description": (
                "Thanks! Staff will review the report shortly. "
                "Whether or not we take action is up to the discretion of our staff."
            ),
        },
    },
    "player report cheat no video": {
        "type": "close",
        "title": "Player Report",
        "description": (
            "Unfortunately, without video proof we cannot take action against any players. "
            "Please try to screen record future encounters."
        ),
    },
    "player report chat": {
        "type": "close",
        "title": "Player Report (Chat Misbehavior)",
        "description": (
            "Unfortunately, our time window for chat punishments is 5 minutes, meaning "
            "moderators are only allowed to take action on chat misbehaviour that occurred "
            "in the last 5 minutes. By the time you created a ticket and a moderator comes "
            "online, that window has likely passed. Therefore, **we won't process chat reports "
            "in tickets.** Next time, you are encouraged to use the `/report` command "
            "in-game to send moderators a notification so we can take action immediately."
        ),
    },

    "bug/glitch reports": {
        "type": "prompt",
        "title": "Bug / Glitch Report",
        "description": "Do you have clear video evidence?",
        "buttons": [
            {"label": "Yes", "next": "bug video", "style": discord.ButtonStyle.green},
            {"label": "No",  "next": "bug no video",  "style": discord.ButtonStyle.red},
        ],
    },
    "bug video": {
        "type": "prompt",
        "title": "Bug / Glitch Report",
        "description": "Choose the kind of bug report you are submitting.",
        "buttons": [
            {"label": "Reporting a bug (no items lost)",    "next": "bug no items lost",   "opens_modal": True},
            {"label": "Lost items due to a bug",            "next": "bug lost items", "opens_modal": True},
            {"label": "Lost items due to lag / combat log", "next": "bug lag"},
        ],
    },
    "bug no video": {
        "type": "close",
        "title": "Bug / Glitch Report",
        "description": "Without video proof or reproduction steps, we cannot fix bugs or restore items.",
    },
    "bug no items lost": {
        "type": "modal",
        "modal": {
            "title": "Bug Report",
            "fields": BUG_FIELDS,
            "result_title":       "Bug / Glitch Report",
            "result_description": "Thanks! Our owner will review the bug report shortly.",
        },
    },
    "bug lost items": {
        "type": "modal",
        "modal": {
            "title": "Bug / Item Loss",
            "fields": BUG_FIELDS,
            "result_title":       "Bug / Glitch Report (Item Loss)",
            "result_description": "Thanks! Our owner will review the bug report shortly.",
        },
    },
    "bug lag": {
        "type": "close",
        "title": "Bug / Glitch Report",
        "description": "Sorry, we do not restore items lost to lag, despawns, or combat disconnects.",
    },

    "staff reports": {
        "type": "prompt",
        "title": "Staff Report",
        "description": "Did the staff member unfairly **punish** you?",
        "buttons": [
            {"label": "Yes", "next": "staff punish", "style": discord.ButtonStyle.green},
            {"label": "No",  "next": "staff punish no",  "style": discord.ButtonStyle.red},
        ],
    },
    "staff punish": {
        "type": "close",
        "title": "Staff Report",
        "description": (
            "Please create an **Appeal** ticket instead. "
            "Staff reports are for behaviour issues (e.g. racism, hacking), not punishment disputes."
        ),
    },
    "staff punish no": {
        "type": "prompt",
        "title": "Staff Report",
        "description": "Do you have proof of the staff member's behaviour (screenshots/videos)?",
        "buttons": [
            {"label": "Yes", "next": "staff proof yes", "style": discord.ButtonStyle.green, "opens_modal": True},
            {"label": "No",  "next": "staff proof no",  "style": discord.ButtonStyle.red},
        ],
    },
    "staff proof yes": {
        "type": "modal",
        "modal": {
            "title": "Staff Report",
            "fields": [
                ("Your IGN",             "What is your in-game name?",    True),
                ("Staff IGN",            "Who are you reporting?",         True),
                ("Incident Description", "Describe what happened",         True),
                ("Proof Link",           "Paste the proof link",           True),
            ],
            "result_title":       "Staff Report",
            "result_description": "Thanks! Our managers and owners will review the report shortly.",
            "ping_everyone":      True,
        },
    },
    "staff proof no": {
        "type": "close",
        "title": "Staff Report",
        "description": "Unfortunately, we cannot investigate any staff report without concrete evidence and proof.",
    },
}

async def dispatch_node(interaction: discord.Interaction, node_id: str, channel: discord.TextChannel = None):
    if channel is None:
        channel = interaction.channel
        
    node = SUPPORT_TREE.get(node_id)
    if node is None:
        print(f"Error: No node found for id {node_id}")
        return

    kind = node["type"]

    if kind == "dynamic":
        handler = DYNAMIC_HANDLERS.get(node_id)
        if handler:
            await handler(interaction, channel)
        return

    if (kind == "prompt"):
        buttons = []
        for btn in node.get("buttons", []):
            buttons.append(SupportActionButton(label=btn["label"], custom_id=btn["next"], style=btn.get("style", discord.ButtonStyle.grey), opens_modal=btn.get("opens_modal", False), channel=channel))
        view = SupportChoiceView(buttons)
        await send_instructions(interaction, title=node["title"], description=node["description"], view=view, channel=channel)
    elif (kind == "close"):
        await send_close_button(interaction, node["title"], node["description"], color=node.get("color", 0xFF0000), channel=channel)
    elif (kind == "final"):
        await send_final(interaction, node["title"], node["description"], data=node.get("data"), color=node.get("color", 0x4F9EF5), ping_everyone=node.get("ping_everyone", False), channel=channel)
    elif (kind == "modal"):
        cfg = node["modal"]
        async def submit(obj, data, _cfg=cfg, current_channel=channel):
            view = None
            if _cfg.get("use_appeal_close_button"):
                from commands.Tickets.appeals import AppealCloseTicketButton
                view = AppealCloseTicketButton()
            await send_final(obj, _cfg["result_title"], _cfg["result_description"], data, view=view, ping_everyone=_cfg.get("ping_everyone", False), channel=current_channel)
        await interaction.response.send_modal(SupportFormModal(title=cfg["title"], fields=cfg["fields"], submit_handler=submit, source_message=interaction.message))

async def password_reset_start(interaction, channel):
    linked, ign = await is_linked(interaction.user, interaction.client)
    if linked:
        await send_final(
            interaction, "Password Reset",
            f"Wow! Your account is already linked (`{ign}`). Staff will reset your password within 1–3 days.",
            data=None, color=0x00FF00, channel=channel
        )
    else:
        await dispatch_node(interaction, "password reset can login", channel=channel)

async def password_reset_verify(interaction, channel):
    if not await owner_only(interaction):
        return
    linked, ign = await is_linked(interaction.user, interaction.client)
    if linked:
        await send_final(
            interaction, "Password Reset",
            f"Great! Your account is now linked (`{ign}`). Staff will reset your password within 1–3 days.",
            data=None, color=0x00FF00, channel=channel
        )
    else:
        await send_instructions(
            interaction, "Still Not Linked",
            "We couldn't detect a link yet. Please try these steps again:\n\n" + LINK_INSTRUCTIONS,
            SupportChoiceView([
                SupportActionButton(label="Verify Again", custom_id="password reset verify again", style=discord.ButtonStyle.green),
            ]), channel=channel
        )

DYNAMIC_HANDLERS = {
    "password reset": password_reset_start,
    "password reset verify": password_reset_verify,
    "password reset verify again": password_reset_verify,
}

def build_registry() -> dict[str, tuple]:
    registry: dict[str, tuple] = {}

    def register(node_id: str):
        node = SUPPORT_TREE[node_id]
        opens_modal = node["type"] == "modal"
        
        async def handler(interaction: discord.Interaction, channel=None, node_id=node_id):
            if not await owner_only(interaction):
                return
            await dispatch_node(interaction, node_id, channel=channel)
            
        registry[node_id] = (handler, opens_modal)
        for btn in node.get("buttons", []):
            child_id = btn["next"]
            if child_id not in registry and child_id in SUPPORT_TREE:
                register(child_id)

    for root_id in ("password reset", "other questions", "billing support", "punishment appeals", "player reports", "bug/glitch reports", "staff reports"):
        register(root_id)

    return registry

SUPPORT_HANDLER_REGISTRY: dict[str, tuple] = build_registry()

async def start_support_tree(interaction: discord.Interaction, ticket_channel: discord.TextChannel, selected_key: str):
    print(f"Starting support tree with key {selected_key} in channel {ticket_channel.id}")
    await dispatch_node(interaction, selected_key, channel=ticket_channel)

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
            self.add_item(discord.ui.TextInput(label=field[1],placeholder=field[0],required=field[2],custom_id=field[0]))

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