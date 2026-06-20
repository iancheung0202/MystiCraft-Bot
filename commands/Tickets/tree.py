import discord
import re
import os
import asyncio
import aiohttp

from constants import SUPPORT_ROLE_IDS, SERVER_IDS, ROLE_IDS

SUPPORT_TREE: dict[str, dict] = {}  
SUPPORT_HANDLER_REGISTRY: dict[str, tuple] = {}

async def is_linked(user, client):
    """Return (linked, ign) for a member using the linking table or main-server nickname fallback."""
    try:
        async with client.tllink_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SHOW TABLES")
                result = await cursor.fetchone()
                link_table = result[0] if result else "mystilinking"
                await cursor.execute(
                    f"SELECT player_name FROM {link_table} WHERE discord_id = %s",
                    (str(user.id),),
                )
                row = await cursor.fetchone()
                return (True, row[0]) if row else (False, None)
    except Exception as e:
        print(f"Error fetching linked IGN for {user.id}: {e}")
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
    except Exception as e:
        print(e)
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
                custom_id=label
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

    if "link" in title.lower():
        embed.set_image(url="https://media.discordapp.net/attachments/741540685852835871/1500668562178572428/Screenshot_20260503-182038.Discord.png?ex=69f94602&is=69f7f482&hm=6d563648ab50f0c3b00dcae99d02b55f6b5cbece7c2ef3131ef9b4ae2a38a136&=")
        embed.set_footer(text="DM the code to one of these bots depending on which gamemode you use /link in")

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
    if "link" in title.lower():
        embed.set_image(url="https://media.discordapp.net/attachments/741540685852835871/1500668562178572428/Screenshot_20260503-182038.Discord.png?ex=69f94602&is=69f7f482&hm=6d563648ab50f0c3b00dcae99d02b55f6b5cbece7c2ef3131ef9b4ae2a38a136&=")
        embed.set_footer(text="DM the code to one of these bots depending on which gamemode you use /link in")
    await channel.send(embed=embed, view=view)

async def dispatch_node(interaction: discord.Interaction, node_id: str, channel: discord.TextChannel = None, context: dict = None):
    if channel is None:
        channel = interaction.channel

    node = SUPPORT_TREE.get(node_id)
    if node is None:
        print(f"Error: No node found for id {node_id}")
        return

    kind = node["type"]
    description = node.get("description", "")
    if context:
        try:
            description = description.format(**context)
        except (KeyError, ValueError):
            pass

    CONDITION_MAP = {
        "is_linked": lambda i: is_linked(i.user, i.client)
    }

    if kind == "condition":
        if node.get("require_owner") and not await owner_only(interaction):
            return

        cond_name = node.get("run_condition")
        result, context_value = False, None
        if cond_name in CONDITION_MAP:
            result, context_value = await CONDITION_MAP[cond_name](interaction)

        outcome = node.get("if_true") if result else node.get("if_false")
        if isinstance(outcome, str):
            await dispatch_node(interaction, outcome, channel=channel, context={"ign": context_value})
        return

    def parse_hex_color(raw_color, default_color):
        if isinstance(raw_color, str):
            try:
                return int(raw_color, 16)
            except ValueError:
                return default_color
        return raw_color if raw_color is not None else default_color

    if (kind == "prompt"):
        buttons = []
        for btn in node.get("buttons", []):
            json_style = btn.get("style", "").lower()
            if json_style == "green" or btn["label"].lower() == "yes":
                style = discord.ButtonStyle.green
            elif json_style == "red" or btn["label"].lower() == "no":
                style = discord.ButtonStyle.red
            else:
                style = discord.ButtonStyle.grey
            buttons.append(SupportActionButton(label=btn["label"], custom_id=btn["next"], style=style, opens_modal=btn.get("opens_modal", False), channel=channel))
        view = SupportChoiceView(buttons)
        await send_instructions(interaction, title=node["title"], description=description, view=view, channel=channel)
        
    elif (kind == "close"):
        # FIXED: Now parsing the string color before forwarding it
        color_int = parse_hex_color(node.get("color"), 0xFF0000)
        await send_close_button(interaction, node["title"], description, color=color_int, channel=channel)
        
    elif (kind == "final"):
        color_int = parse_hex_color(node.get("color"), 0x4F9EF5)
        await send_final(interaction, node["title"], description, data=node.get("data"), color=color_int, ping_everyone=node.get("ping_everyone", False), channel=channel)
        
    elif (kind == "modal"):
        cfg = node["modal"]
        async def submit(obj, data, _cfg=cfg, current_channel=channel):
            view = None
            if _cfg.get("use_appeal_close_button"):
                from commands.Tickets.appeals import AppealCloseTicketButton
                view = AppealCloseTicketButton()
            await send_final(obj, _cfg["result_title"], _cfg["result_description"], data, view=view, ping_everyone=_cfg.get("ping_everyone", False), channel=current_channel)
        await interaction.response.send_modal(SupportFormModal(title=cfg["title"], fields=cfg["fields"], submit_handler=submit, source_message=interaction.message))

def register_new_nodes(bot, new_tree: dict):
    newly_registered = []

    def register(node_id: str):
        if node_id in SUPPORT_HANDLER_REGISTRY:
            return
        node = new_tree.get(node_id)
        if not node:
            return
            
        opens_modal = node["type"] == "modal"
        
        async def handler(interaction: discord.Interaction, channel=None, node_id=node_id):
            if not await owner_only(interaction):
                return
            await dispatch_node(interaction, node_id, channel=channel)
            
        SUPPORT_HANDLER_REGISTRY[node_id] = (handler, opens_modal)
        newly_registered.append(node_id)
        
        # 1. Traverse standard button transitions
        for btn in node.get("buttons", []):
            register(btn["next"])
            
        # 2. Traverse conditional transitions (Fixes your issue!)
        if "if_true" in node:
            register(node["if_true"])
        if "if_false" in node:
            register(node["if_false"])
            
        # 3. Traverse transitions following modal structures if applicable
        if "modal" in node and "next" in node:
            register(node["next"])

    for root_id in new_tree.keys():
        register(root_id)

    if newly_registered and bot is not None:
        for i in range(0, len(newly_registered), 25):
            chunk = newly_registered[i:i + 25]
            persistent_view = SupportChoiceView()
            for custom_id in chunk:
                persistent_view.add_item(
                    SupportActionButton(label="Button", custom_id=custom_id)
                )
            bot.add_view(persistent_view)

    return newly_registered


async def fetch_tree_api() -> dict | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://mysticraft.xyz/api/admin/ticket-tree",
                headers={"x-api-key": os.environ.get("BOT_ACCESS_API_KEY")},
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status != 200:
                    print(f"[Ticket Tree] API returned HTTP {resp.status}, keeping existing tree.")
                    return None
                data = await resp.json()
                if not isinstance(data, dict):
                    print(f"[Ticket Tree] API returned non-object JSON, keeping existing tree.")
                    return None
                return data
    except asyncio.TimeoutError:
        print("[Ticket Tree] API fetch timed out, keeping existing tree.")
        return None
    except Exception as e:
        print(f"[Ticket Tree] API fetch error: {e}, keeping existing tree.")
        return None


async def tree_poll_loop(bot):
    await bot.wait_until_ready()
    print(f"[Ticket Tree] Starting poll loop (every 5s) from http://mysticraft.xyz/api/admin/ticket-tree")
    while not bot.is_closed():
        new_tree = await fetch_tree_api()
        if new_tree is not None and new_tree != SUPPORT_TREE:
            added = set(new_tree) - set(SUPPORT_TREE)
            removed = set(SUPPORT_TREE) - set(new_tree)
            SUPPORT_TREE.clear()
            SUPPORT_TREE.update(new_tree)
            newly = register_new_nodes(bot, new_tree)
            print(f"[Ticket Tree] Tree updated — +{len(added)} nodes, -{len(removed)} nodes"
                  + (f", {len(newly)} newly registered with bot" if newly else ""))
        await asyncio.sleep(5)

async def start_support_tree(interaction: discord.Interaction, ticket_channel: discord.TextChannel, selected_key: str):
    print(f"Starting support tree with key {selected_key} in channel {ticket_channel.id}")
    await dispatch_node(interaction, selected_key, channel=ticket_channel)


async def setup(bot):
    all_ids = list(SUPPORT_HANDLER_REGISTRY.keys())
    for i in range(0, len(all_ids), 25):
        chunk = all_ids[i:i + 25]
        persistent_view = SupportChoiceView()
        for custom_id in chunk:
            persistent_view.add_item(SupportActionButton(label="Button", custom_id=custom_id))
        bot.add_view(persistent_view)

    initial = await fetch_tree_api()
    if initial is not None and initial != SUPPORT_TREE:
        SUPPORT_TREE.clear()
        SUPPORT_TREE.update(initial)
        register_new_nodes(bot, initial)
        print("[Ticket Tree] Initial tree loaded from API.")

    bot.loop.create_task(tree_poll_loop(bot))