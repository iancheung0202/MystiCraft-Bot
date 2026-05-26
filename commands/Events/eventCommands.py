import discord, time, datetime, firebase_admin
from discord import app_commands
from discord.ext import commands
from firebase_admin import db
from PIL import Image, ImageDraw, ImageFont, ImageEnhance 
import os.path
import pandas as pd
from discord.ui import Button, View
from commands.Events.event import addMora, userAndTitle

letter_emojis = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷", "🇸"]
minigame_titles = [
    "Defeat The Boss",
    "Quicktype Racer",
    "Egg Walk",
    "Match The Profile Picture",
    "Split or Steal",
    "Reverse Number Quicktype",
    "Pick Up Ice Cream",
    "Pick Up The Watermelon",
    "Guess The Number",
    "Memory Game",
    "Who Said It",
    "Unscramble Words",
    "Two Truths and a Lie",
    "Counting Logos",
    "Rock Paper Scissors",
    "Teyvat Trivia",
    "Teyvat Voiceline Quiz",
    "Teyvat Emoji Riddles",
    "True or False :new:"
]


async def purchase_autocomplete(
    interaction: discord.Interaction,
    current: str,
):
    ref = db.reference("/Global Events Rewards")
    daily = ref.get()
    rewards = []
    choices = []
    for key, val in daily.items():
        if val["Server ID"] == interaction.guild.id:
            rewards = val["Rewards"]
            
    ref = db.reference("User Events Mora")
    randomevents = ref.get()
    total_mora = 0
    if randomevents:
        for key, val in randomevents.items():
            if val['User ID'] == interaction.user.id:
                total_mora = get_total_mora(val['Data'])

    for reward in rewards:
        reward_name = reward[0]
        reward_cost = reward[2] 

        if isinstance(reward_name, int) or reward_name.isdigit():
            role = interaction.guild.get_role(int(reward_name))
            display_name = f"Role: {role.name}" if role else "Unknown Role"
        else:
            display_name = reward_name
        
        choice_name = f"{display_name} (Cost: {reward_cost})"

        if current.lower() in reward_name.lower() or (
            isinstance(reward_name, int) or reward_name.isdigit()
            and role
            and current.lower() in role.name.lower()
        ):
            # if int(total_mora) > int(reward_cost):
            choices.append(app_commands.Choice(name=choice_name, value=reward_name))

    return choices[:25]

async def pin_title_autocomplete(
    interaction: discord.Interaction,
    current: str,
):
    ref = db.reference("/User Events Inventory")
    inventories = ref.get()
    items_set = set()  # Use a set to track unique item[0] values
    items_list = []
    
    if inventories:
        for key, val in inventories.items():
            if val["User ID"] == interaction.user.id:
                try:
                    for item in val["Items"]:
                        role = None
                        try:
                            role = interaction.guild.get_role(int(item[0]))
                        except Exception:
                            pass
                        if len(item) > 3 and item[3] == interaction.guild.id and (
                            current.lower() in str(item[0]).lower() or (
                            isinstance(item[0], int) or item[0].isdigit()
                            and role
                            and current.lower() in role.name.lower()
                        )):
                            if item[0] not in items_set:  # Check if item[0] is unique
                                items_set.add(item[0])
                                if isinstance(item[0], int) or str(item[0]).isdigit():
                                    items_list.append(app_commands.Choice(name=f"Role: {role.name}", value=item[0]))
                                else:
                                    items_list.append(app_commands.Choice(name=f"Title: {item[0]}", value=item[0]))
                except Exception as e:
                    print(e)
                    
    items_list.insert(0, app_commands.Choice(name=f"Unpin my current item only", value="unpin"))
    return items_list[:25]

### --- CONFIRM CUSTOMIZE BACKGROUND --- ###


class ConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Confirm", style=discord.ButtonStyle.green, custom_id="confirmbg"
    )
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if str(interaction.user.id) not in interaction.message.embeds[0].description:
            await interaction.response.send_message(
                "You can't perform this action!", ephemeral=True
            )
            raise Exception()

        embed = interaction.message.embeds[0]
        embed.title = "Confirmed"
        embed.description = f"The following will be how {interaction.user.mention}'s inventory would appear.\n\nYou can always use this command again to change your inventory background."
        embed.color = discord.Color.green()

        try:
            os.remove(f"./assets/Mora Inventory Background/{interaction.user.id}.png")
        except Exception:
            pass

        os.rename(
            f"./assets/Mora Inventory Background/{interaction.user.id}-temp.png",
            f"./assets/Mora Inventory Background/{interaction.user.id}.png",
        )

        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(
        label="Cancel", style=discord.ButtonStyle.grey, custom_id="cancelbg"
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) not in interaction.message.embeds[0].description:
            await interaction.response.send_message(
                "You can't perform this action!", ephemeral=True
            )
            raise Exception()

        os.remove(f"./assets/Mora Inventory Background/{interaction.user.id}-temp.png")
        embed = discord.Embed(
            title="Action Cancelled",
            description="You can always use this command again to change your inventory background.",
            color=discord.Color.red(),
        )
        await interaction.response.edit_message(embed=embed, view=None)


### --- CREATE PROFILE CARD --- ###


async def createProfileCard(
    user, num, rank, bg="./assets/mora_bg.png", filename="./assets/mora.png"
):
    await user.avatar.with_static_format("png").with_size(128).save(filename)
    im1 = Image.open(bg)  # background (720, 256)
    im2 = Image.open(filename)  # user logo
    im3 = Image.open("./assets/mora_icon.png")  # mora icon

    bigsize = (im2.size[0] * 1, im2.size[1] * 1)
    mask = Image.new("L", bigsize, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + bigsize, fill=255)
    mask = mask.resize(im2.size, Image.LANCZOS)
    im2.putalpha(mask)  # USER AVATAR
    im1.paste(im2, (20, 20), im2.convert("RGBA"))

    font = ImageFont.truetype("./assets/MinecraftTen-VGORe.ttf", 52)
    d1 = ImageDraw.Draw(im1)
    d1.text(
        (166, 35), user.display_name, font=font, fill=(255, 255, 255)
    )  # DISPLAY NAME
    im1.save(filename)

    font = ImageFont.truetype("./assets/MinecraftTen-VGORe.ttf", 28)
    d1 = ImageDraw.Draw(im1)
    d1.text((166, 97), user.name, font=font, fill=(225, 225, 225))  # USERNAME
    im1.save(filename)

    bigsize = (im3.size[0] * 1, im3.size[1] * 1)
    mask = Image.new("L", bigsize, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + bigsize, fill=255)
    mask = mask.resize(im3.size, Image.LANCZOS)
    im3.putalpha(mask)  # MORA ICON
    im1.paste(im3, (38, 185), im3.convert("RGBA"))

    font = ImageFont.truetype("./assets/MinecraftTen-VGORe.ttf", 50)
    d1 = ImageDraw.Draw(im1)
    d1.text((92, 185), num, font=font, fill=(233, 253, 255))  # MORA AMOUNT
    im1.save(filename)

    if rank != "N/A":
        font = ImageFont.truetype("./assets/MinecraftTen-VGORe.ttf", 40)
        d1 = ImageDraw.Draw(im1)
        d1.text(
            (420, 192), f"Guild Rank: {rank}", font=font, fill=(203, 254, 196)
        )  # RANK
        im1.save(filename)

    # font = ImageFont.truetype("./assets/MinecraftTen-VGORe.ttf", 35)
    # text = f"{user.name}"
    # textLen = len(text)
    # d2 = ImageDraw.Draw(im1)
    # d2.text((((1024/2)-(20*(textLen/2))),410), text, font=font, fill=(255, 255, 255))
    # im1.save(filename)

    return filename


### --- LEADERBOARD PAGINATION VIEW --- ###


class LeaderboardPageView(discord.ui.View):
    def __init__(self, pages):
        super().__init__()
        self.page = 0
        self.pages = pages

    @discord.ui.button(
        style=discord.ButtonStyle.grey, custom_id="super_prev_lb", emoji = "<:fastbackward:1351972112696479824>"
    )  # , emoji="" if wanted
    async def super_prev_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.page = 0
        embed = self.pages[self.page]
        embed.set_footer(text=f"Page {self.page + 1} of {len(self.pages)}")
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(
        style=discord.ButtonStyle.grey, custom_id="prev_lb", emoji = "<:backarrow:1351972111010369618>"
    )  # , emoji="" if wanted
    async def prev_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.page > 0:
            self.page -= 1
        else:
            self.page = len(self.pages) - 1
        embed = self.pages[self.page]
        embed.set_footer(text=f"Page {self.page + 1} of {len(self.pages)}")
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(
        style=discord.ButtonStyle.grey, custom_id="next_lb", emoji = "<:rightarrow:1351972116819480616>"
    )  # , emoji="" if wanted
    async def next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.page < len(self.pages) - 1:
            self.page += 1
        else:
            self.page = 0
        embed = self.pages[self.page]
        embed.set_footer(text=f"Page {self.page + 1} of {len(self.pages)}")
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(
        style=discord.ButtonStyle.grey, custom_id="super_next_lb", emoji = "<:fastforward:1351972114433048719>"
    )  # , emoji="" if wanted
    async def super_next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.page = len(self.pages) - 1
        embed = self.pages[self.page]
        embed.set_footer(text=f"Page {self.page + 1} of {len(self.pages)}")
        await interaction.response.edit_message(embed=embed)


### --- REMOVE MORA FROM USER --- ###


async def subtractGuildMora(userID, subtractMora, guildID):
    guildID = str(guildID)
    ref = db.reference("/User Events Mora")
    randomevents = ref.get()
    ogData = None
    found_key = None
    if randomevents:
        for key, val in randomevents.items():
            if val["User ID"] == userID:
                ogData = val["Data"]
                found_key = key
                break
    if ogData is None:
        return False  # No user data exists
    guild_data = ogData["guilds"].get(guildID)
    if guild_data is None:
        return False  # No data for this guild
    channels = guild_data.get("channels", {})
    total_guild = 0
    for channel in channels.values():
        for amt in channel.values():
            total_guild += amt
    if subtractMora > total_guild:  # If not enough mora
        return False
    entries = []
    for channel_id, timestamps in channels.items():
        for timestamp, amount in timestamps.items():
            entries.append((channel_id, timestamp, amount))
    entries.sort(key=lambda x: int(x[1]))
    amount_left = subtractMora
    for channel_id, timestamp, amount in entries:
        if amount_left <= 0:
            break
        if amount >= amount_left:
            new_amount = amount - amount_left
            ogData["guilds"][guildID]["channels"][channel_id][timestamp] = new_amount
            amount_left = 0
        else:
            ogData["guilds"][guildID]["channels"][channel_id][timestamp] = 0
            amount_left -= amount
    data = {"User": {"User ID": userID, "Data": ogData}}
    if found_key:
        db.reference("/User Events Mora").child(found_key).delete()
    for key, value in data.items():
        ref.push().set(value)
    new_total_guild = 0
    for channel in ogData["guilds"][guildID]["channels"].values():
        for amt in channel.values():
            new_total_guild += amt
    return new_total_guild


### --- GET MORA FROM USER THROUGH DICT --- ###


def get_total_mora(data: dict) -> int:
    total = 0
    for guild in data.get("guilds", {}).values():
        for channel in guild.get("channels", {}).values():
            for amt in channel.values():
                total += amt
    return total


def get_guild_mora(data: dict, guild_id: str) -> int:
    total = 0
    guild_data = data.get("guilds", {}).get(guild_id, {})
    channels = guild_data.get("channels", {})
    for channel in channels.values():
        for amt in channel.values():
            total += amt
    return total


class EventCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="lb", description="Check the server leaderboard"
    )
    #@app_commands.describe(type="Specify which type of leaderboard you want to view")
    #@app_commands.choices(
        #type=[
            #app_commands.Choice(name="Global Leaderboard", value="global"),
            #app_commands.Choice(name="Server-specific Leaderboard", value="server"),
        #]
    #)
    async def lb(
        self, interaction: discord.Interaction, 
        #type: app_commands.Choice[str]
    ) -> None:
        ref = db.reference("/User Events Mora")
        summer = ref.get()
        dict_lb = []

        try:
            if summer:
                for key, val in summer.items():
                    user_id = val["User ID"]
                    if True:
                        member = interaction.guild.get_member(user_id)
                        if member is not None:
                            user_data = val["Data"]
                            guild_mora = 0
                            guild_key = str(interaction.guild.id)
                            if (
                                "guilds" in user_data
                                and guild_key in user_data["guilds"]
                            ):
                                for channel in (
                                    user_data["guilds"][guild_key]
                                    .get("channels", {})
                                    .values()
                                ):
                                    for mora_value in channel.values():
                                        guild_mora += mora_value
                            if guild_mora != 0:
                                dict_lb.append({"User ID": user_id, "Mora": guild_mora})
        except Exception as e:
            print(e)

        df = pd.DataFrame(dict_lb)
        if not df.empty:
            df = df.sort_values(by="Mora", ascending=False)
        else:
            df = pd.DataFrame(columns=["User ID", "Mora"])

        num = 1
        pages = []
        page_string = ""
        for idx in range(min(len(df), 50)):
            user_id = df.iloc[idx]["User ID"]
            mora = df.iloc[idx]["Mora"]
            if user_id == interaction.user.id:
                page_string += f"{num}. {userAndTitle(user_id, interaction.guild.id)} - <:MystiCoin:1141391721297616906> `{mora}` <:you:1339737311319162890>\n"
            else:
                page_string += (
                    f"{num}. <@{user_id}> - <:MystiCoin:1141391721297616906> `{mora}`\n"
                )
            if num % 10 == 0 or num == len(df):
                if True:
                    embed = discord.Embed(
                        title=f"{interaction.guild.name}'s Leaderboard",
                        description=f"A ranking of users within this server based on their current toral MystiCoins. Compete with fellow members and climb to the top!\n\n {page_string}",
                        color=0x2A7E19,
                    )
                    embed.set_thumbnail(url=interaction.guild.icon.url)
                
                pages.append(embed)
                page_string = ""
            num += 1

        if not pages:
            embed = discord.Embed(
                title="Leaderboard", description="No data available.", color=0xFFD700
            )
            pages.append(embed)

        # Set the footer on the first page and send the paginated leaderboard.
        pages[0].set_footer(text=f"Page 1 of {len(pages)}")
        await interaction.response.send_message(
            embed=pages[0], view=LeaderboardPageView(pages)
        )

    @app_commands.command(
        name="customize", description="Customize your MystiCoin inventory and profile"
    )
    @app_commands.describe(
        background="Your desired inventory background (auto cropped and scaled to 720x256px)",
        pin_item="Title/role name to pin (displayed next to your name in mini-games)"
    )
    @app_commands.autocomplete(pin_item=pin_title_autocomplete)
    async def customize(
        self, interaction: discord.Interaction, background: discord.Attachment = None, pin_item: str = None
    ) -> None:
        await interaction.response.defer(thinking=True)
        
        if pin_item is not None:
            ref = db.reference("/User Events Inventory")
            inventories = ref.get()

            if inventories:
                for key, val in inventories.items():
                    if val['User ID'] == interaction.user.id:
                        print("User trying to pin found in inventory")

                        inv = val["Items"].copy()

                        # Unpin the currently pinned item
                        unpinned = None
                        for i, item in enumerate(inv):
                            if item[3] == interaction.guild.id and len(item) > 5 and item[5] == "Pinned":
                                print("Unpinning previous item")
                                inv[i] = item[:-1]  # Remove the "Pinned" tag
                                unpinned = item[0]

                        # Pin the newly selected item
                        if str(pin_item) != "unpin":
                            for i, item in enumerate(inv):
                                if item[3] == interaction.guild.id and item[0] == str(pin_item):
                                    print("Pinning new item")
                                    inv[i] = item + ["Pinned"]  # Append "Pinned"

                        # Update the database in one step
                        ref.child(key).update({"Items": inv})
                        break  # Stop after updating the user's inventory

            if str(pin_item) == "unpin":
                if unpinned is None:
                    if str(pin_item) == "unpin":
                        await interaction.followup.send(embed=discord.Embed(title="Oops", description=f"{interaction.user.mention}. you currently have no items in your inventory pinned. ", color=discord.Color.red()))
                        return
                role_mention = (
                    f"<@&{unpinned}>"
                    if isinstance(unpinned, int) or unpinned.isdigit()
                    else unpinned
                )
                await interaction.followup.send(embed=discord.Embed(title="Item Unpinned", description=f"**{role_mention}** is now unpinned, {interaction.user.mention}. You can always pin another item later.", color=discord.Color.green()))
            else:
                role_mention = (
                    f"<@&{pin_item}>"
                    if isinstance(pin_item, int) or pin_item.isdigit()
                    else pin_item
                )
                await interaction.followup.send(embed=discord.Embed(title="Item Pinned", description=f"**{role_mention}** is now :pushpin: pinned. It will appear alongside your name every time you play or win a game.", color=discord.Color.green()))

        
        if background is None and pin_item is None:
            await interaction.followup.send(":x: Please either attach your desired inventory background **and/or** specify a title/role to pin.")
            return
        
        if background is None:
            return

        path = f"./assets/Mora Inventory Background/{interaction.user.id}-temp.png"
        await background.save(path)
        image = Image.open(path)
        width = image.size[0]
        height = image.size[1]
        aspect = width / float(height)
        ideal_width = 720
        ideal_height = 256
        ideal_aspect = ideal_width / float(ideal_height)
        if aspect > ideal_aspect:
            new_width = int(ideal_aspect * height)
            offset = (width - new_width) / 2
            resize = (offset, 0, width - offset, height)
        else:
            new_height = int(width / ideal_aspect)
            offset = (height - new_height) / 2
            resize = (0, offset, width, height - offset)
        thumb = image.crop(resize).resize((ideal_width, ideal_height), Image.LANCZOS)
        thumb.save(path)
        image = Image.open(path)
        enhancer = ImageEnhance.Brightness(image)
        im_output = enhancer.enhance(0.4)
        im_output.save(path)

        filename = await createProfileCard(interaction.user, f"69,420", "69", bg=path)

        chn = interaction.client.get_channel(1026968305208131645)
        msg = await chn.send(file=discord.File(filename))
        url = msg.attachments[0].proxy_url

        embed = discord.Embed(
            title="Preview",
            description=f"The following image showcases how {interaction.user.mention}'s inventory would appear.",
            color=discord.Color.gold(),
        )
        embed.set_image(url=url)
        await interaction.followup.send(embed=embed, view=ConfirmView())

    @app_commands.command(name="inventory", description="Check a user's inventory")
    @app_commands.describe(
        user="Specify any user other than yourself if needed",
    )
    async def mora(
        self, interaction: discord.Interaction, user: discord.Member = None
    ) -> None:
        await interaction.response.defer(thinking=True)
        if user is None:
            user = interaction.user

        ref = db.reference("/User Events Mora")
        randomevents = ref.get()

        global_ranking = []
        global_total = 0
        global_temp_total = 0
        if randomevents:
            for key, val in randomevents.items():
                uid = val["User ID"]
                data = val["Data"]
                global_temp_total = get_total_mora(data)
                global_ranking.append((uid, global_temp_total))
                if uid == user.id:
                    global_total = global_temp_total  # Set the total for the requested user
            global_ranking.sort(key=lambda x: x[1], reverse=True)
        global_rank = "N/A"
        for idx, (uid, total) in enumerate(global_ranking, start=1):
            if uid == user.id:
                global_rank = idx
                break
              
        print(f"User ID: {interaction.user.id} | User Name: {interaction.user.name}")
        print(f"Global Total: {global_total}")
        print(f"Global Rank: {global_rank}")

        guild_ranking = []
        guild_total = 0
        guild_temp_total = 0
        if randomevents:
            for val in randomevents.values():
                uid = val["User ID"]
                data = val["Data"]
                guild_temp_total = get_guild_mora(data, str(interaction.guild.id))
                if guild_temp_total > 0 and interaction.guild.get_member(uid):
                    guild_ranking.append((uid, guild_temp_total))
                if uid == user.id:
                    guild_total = guild_temp_total
            guild_ranking.sort(key=lambda x: x[1], reverse=True)
        guild_rank = "N/A"
        for idx, (uid, total) in enumerate(guild_ranking, start=1):
            if uid == user.id:
                guild_rank = idx
                break
                
        print(f"Guild Total: {guild_total}")
        print(f"Guild Rank: {guild_rank}")
        print("--------------------")

        def word(n):
            if n == "N/A":
                return "N/A"
            return str(n) + (
                "th"
                if 4 <= n % 100 <= 20
                else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
            )

        ref = db.reference("/User Events Inventory")
        inventories = ref.get()
        inv = "Empty"

        MAX_INV_LENGTH = 1024  # Discord's character limit
        EXTRA_LENGTH = 15  # Estimated length for "(X more)" message

        if inventories:
            for key, val in inventories.items():
                if val["User ID"] == user.id:
                    try:
                        item_dict = {}
                        pinned_items = {}  # Separate dict for pinned items

                        for item in val["Items"]:
                            print(f"Processing item: {item}")  # Debugging line
                            if len(item) > 3 and item[3] == interaction.guild.id:
                                role_id = item[0]
                                timestamp = item[4] if len(item) > 4 else 1741083000
                                is_pinned = len(item) > 5 and item[5] == "Pinned"

                                target_dict = pinned_items if is_pinned else item_dict

                                if role_id in target_dict:
                                    target_dict[role_id]["count"] += 1
                                    target_dict[role_id]["timestamp"] = min(target_dict[role_id]["timestamp"], timestamp)
                                else:
                                    target_dict[role_id] = {"count": 1, "timestamp": timestamp}

                        # Generate item lists with formatting
                        def format_item(role, data, pinned=False):
                            prefix = "📌 **Pinned:** " if pinned else "- "
                            if isinstance(role, int) or str(role).isdigit():  # Role ID format
                                return (
                                    f"{prefix}<@&{role}> **(x{data['count']})** - *First acquired <t:{data['timestamp']}:R>*"
                                    if data["count"] > 1
                                    else f"{prefix}<@&{role}> - *Acquired <t:{data['timestamp']}:R>*"
                                )
                            else:
                                return (
                                    f"{prefix}{role} **(x{data['count']})** - *First acquired <t:{data['timestamp']}:R>*"
                                    if data["count"] > 1
                                    else f"{prefix}{role} - *Acquired <t:{data['timestamp']}:R>*"
                                )

                        print(f"Final pinned_items before list creation: {pinned_items}")
                        pinned_list = [format_item(role, data, True) for role, data in pinned_items.items()]
                        print(f"Final item_dict before list creation: {item_dict}")
                        items_list = [format_item(role, data) for role, data in item_dict.items()]
                        combined_list = pinned_list + items_list  # Pinned items first

                        if combined_list:  # Ensure inventory is not considered empty if any items exist
                            inv = ""
                            remaining_count = 0

                            for item in combined_list:
                                if len(inv) + len(item) + EXTRA_LENGTH > MAX_INV_LENGTH:
                                    break
                                inv += item + "\n"

                            remaining_count = len(combined_list) - inv.count("\n")  # Count items left out
                            if remaining_count > 0:
                                inv += f"*({remaining_count} more...)*"

                            inv = inv.strip()  # Remove trailing newline if any

                        break
                    except Exception as e:
                        print(e)

        betaAmount = next(
            (
                val["Mora"]
                for val in db.reference("/Random Events").get().values()
                if val["User ID"] == user.id
            ),
            0,
        )
        legacy = None
        if betaAmount != 0:
            legacy = (
                f"\n-# <a:legacy:1345876714240213073> *Legacy Player: `{betaAmount}`*"
            )

        embed = discord.Embed(
            title=f"{user.display_name}'s Inventory",
            description=f"{legacy if legacy is not None else ''}",
            color=discord.Color.gold(),
        )

        if guild_rank != "N/A":
            embed.add_field(
                name=interaction.guild.name,
                value=f"<:MystiCoin:1141391721297616906> MystiCoins: `{guild_total}`\n:medal: Rank: **{word(guild_rank)}**",
                inline=True,
            )

        #if global_rank != "N/A":
            #embed.add_field(
                #name="Global",
                #value=f"MystiCoins: <:MystiCoin:1141391721297616906> `{global_total}`\n<:medal: Rank: **{word(global_rank)}**",
                #inline=True,
            #)

        embed.add_field(name="Guild Inventory", value=inv, inline=False)

        customized = os.path.isfile(f"./assets/Mora Inventory Background/{user.id}.png")
        if customized:
            filename = await createProfileCard(
                user,
                f"{guild_total:,}",
                guild_rank,
                bg=f"./assets/Mora Inventory Background/{user.id}.png",
            )
            embed.set_footer(
                text="Tip: Use /customize to PIN a role/title next to your name in mini-games!"
            )
        else:
            filename = await createProfileCard(user, f"{guild_total:,}", guild_rank)
            embed.set_footer(
                text="Tip: use /customize to customize your own inventory background for FREE!"
            )

        chn = interaction.client.get_channel(1026968305208131645)
        msg_obj = await chn.send(file=discord.File(filename))
        url = msg_obj.attachments[0].proxy_url
        embed.set_image(url=url)

        await interaction.followup.send(embed=embed)


class ToggleEventModal(discord.ui.Modal, title="Toggling Event"):

    letter = discord.ui.TextInput(
        label="The corresponding letter(s)",
        style=discord.TextStyle.short,
        placeholder="Type letters consecutively to toggle multiple games (no spaces please)",
        max_length=26,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        # await interaction.response.defer()
        channelID = int(str(self.title).split(":")[1].replace(")", "").strip())
        ref = db.reference("/Global Events System")
        stickies = ref.get()
        originalList = None
        try:
            for key, val in stickies.items():
                if val["Channel ID"] == channelID:
                    originalList = val["Events"]
                    print(originalList)
                    frequency = val["Frequency"]
                    break
        except Exception as e:
            print(e)

        for letter in list(str(self.letter)):
            self.toggleLetter = str(letter).upper()

            if (
                self.toggleLetter
                in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S"]
                and originalList is not None
            ):
                if self.toggleLetter in originalList:
                    originalList.remove(self.toggleLetter)
                else:
                    originalList.append(self.toggleLetter)
                error = False
            else:
                error = True
                break

        if not (error):
            for key, val in stickies.items():
                if val["Channel ID"] == channelID:
                    db.reference("/Global Events System").child(key).delete()
                    break

            data = {
                channelID: {
                    "Channel ID": channelID,
                    "Frequency": frequency,
                    "Events": originalList,
                }
            }
            for key, value in data.items():
                ref.push().set(value)

            string = "\n> ".join(
                [
                    f"{emoji} - {title} ✅"
                    if self.toggleLetter in originalList
                    else f"{emoji} - {title} :x:"
                    for self.toggleLetter, emoji, title in zip(
                        "ABCDEFGHIJKLMNOPQRS", letter_emojis, minigame_titles
                    )
                ]
            )

            self.embed = discord.Embed(
                title="Customize which mini-games you'd like to enable",
                description=f"**Channel:** <#{channelID}>\n\n > {string}\n\nClick the button below and type in the **corresponding letter(s)** (i.e. `h` or `abdfm`) to **toggle** the mini-game(s). *To edit the frequency, use `/events enable` again.*",
                color=discord.Color.blurple(),
            )
            self.update = discord.Embed(
                description=f"Toggle successful :slight_smile:",
                color=discord.Color.green(),
            )
        else:
            self.embed = None
            self.update = discord.Embed(
                description=f"Invalid input. Please try again.",
                color=discord.Color.red(),
            )

        self.on_submit_interaction = interaction
        self.stop()


class ToggleEventButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Toggle Event", style=discord.ButtonStyle.blurple)

    async def callback(self, interaction: discord.Interaction):
        channelID = (
            interaction.message.embeds[0]
            .description.split("<#")[1]
            .split(">")[0]
            .strip()
        )

        toggleEventModal = ToggleEventModal(title=f"Toggle Event (ID: {channelID})")
        await interaction.response.send_modal(toggleEventModal)
        response = await toggleEventModal.wait()

        if toggleEventModal.embed is not None:
            await interaction.edit_original_response(embed=toggleEventModal.embed)
        await toggleEventModal.on_submit_interaction.response.send_message(
            embed=toggleEventModal.update, ephemeral=True
        )
        
class SortSelection(discord.ui.Select):
    def __init__(self, default="sort by cost (high to low)"):
        options = []
        sortOptions = ["sort by cost (low to high)", "sort by cost (high to low)", "sort by name (a-z)", "sort by name (z-a)"]
        sortOptionsEmoji = [
            "<:price_ascending:1346329079145562112>", "<:price_descending:1346329080462577725>", 
            "<:name_ascending:1346329053455585324>", "<:name_descending:1346329054634053703>"
        ]
        for i in sortOptions:
            if i == default:
                options.append(discord.SelectOption(label=i, emoji=sortOptionsEmoji[sortOptions.index(i)], default=True))
            else:
                options.append(discord.SelectOption(label=i, emoji=sortOptionsEmoji[sortOptions.index(i)]))
        super().__init__(
            placeholder="Choose the Sorting",
            max_values=1,
            min_values=1,
            options=options,
            custom_id="sortselection",
        )

    async def callback(self, interaction: discord.Interaction):
        ref = db.reference("/Global Events Rewards")
        rewards = ref.get()
        originalList = []
        try:
            for key, val in rewards.items():
                if val["Server ID"] == interaction.guild.id:
                    originalList = val["Rewards"]
                    print(originalList)
                    break
        except Exception:
            pass
            
        if interaction.data['values'][0] == "sort by cost (low to high)":
            pages = await get_shop_embeds(interaction, originalList, len(originalList) == 0, sort_by="cost", reverse=False)
        elif interaction.data['values'][0] == "sort by cost (high to low)":
            pages = await get_shop_embeds(interaction, originalList, len(originalList) == 0, sort_by="cost", reverse=True)
        elif interaction.data['values'][0] == "sort by name (a-z)":
            pages = await get_shop_embeds(interaction, originalList, len(originalList) == 0, sort_by="name", reverse=False)
        elif interaction.data['values'][0] == "sort by name (z-a)":
            pages = await get_shop_embeds(interaction, originalList, len(originalList) == 0, sort_by="name", reverse=True)
        else:
            pages = await get_shop_embeds(interaction, originalList, len(originalList) == 0)
            
        if interaction.user.guild_permissions.administrator:
            view = Panel(default=interaction.data['values'][0], pages=pages)
        else:
            view = SortSelectionView(default=interaction.data['values'][0], pages=pages)
        
        await interaction.response.edit_message(embed=pages[0], view=view)

class SortSelectionView(discord.ui.View):
    def __init__(self, default="sort by price (high to low)", pages=None, *, timeout=None):
        super().__init__(timeout=timeout)
        self.add_item(SortSelection(default))
        self.page = 0
        self.pages = pages
    
    @discord.ui.button(label="<<", style=discord.ButtonStyle.blurple, custom_id="super_prev_shop")
    async def super_prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 0
        embed = self.pages[self.page]
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="<", style=discord.ButtonStyle.blurple, custom_id="prev_shop")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        else:
            self.page = len(self.pages) - 1
        embed = self.pages[self.page]
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label=">", style=discord.ButtonStyle.blurple, custom_id="next_shop")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < len(self.pages) - 1:
            self.page += 1
        else:
            self.page = 0
        embed = self.pages[self.page]
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label=">>", style=discord.ButtonStyle.blurple, custom_id="super_next_shop")
    async def super_next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = len(self.pages) - 1
        embed = self.pages[self.page]
        await interaction.response.edit_message(embed=embed)

class Panel(discord.ui.View):
    def __init__(self, default="sort by price (high to low)", pages=None):
        super().__init__(timeout=None)
        self.add_item(SortSelection(default))
        self.page = 0
        self.pages = pages

    @discord.ui.button(
        label="Add Reward", style=discord.ButtonStyle.green, custom_id="addreward", row=0
    )
    async def add_reward(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        addRewardModel = AddRewardModel(title=f"Add a Custom Reward")
        if interaction.user.guild_permissions.administrator:
            await interaction.response.send_modal(addRewardModel)
            response = await addRewardModel.wait()
            pages = addRewardModel.pages
            if pages is not None:
                if interaction.user.guild_permissions.administrator:
                    view = Panel(pages=pages)
                else:
                    view = SortSelectionView(pages=pages)
                await interaction.edit_original_response(
                    embed=pages[0], view=view
                )
            await addRewardModel.on_submit_interaction.response.send_message(
                embed=addRewardModel.update, ephemeral=True
            )
        else:
            await interaction.response.send_message(
                ":x: You are missing `Administrator` permissions.", ephemeral=True
            )

    @discord.ui.button(
        label="Remove Reward", style=discord.ButtonStyle.red, custom_id="removereward", row=0
    )
    async def remove_reward(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        removeRewardModel = RemoveRewardModel(title=f"Remove a Custom Reward")
        if interaction.user.guild_permissions.administrator:
            await interaction.response.send_modal(removeRewardModel)
            response = await removeRewardModel.wait()
            pages = removeRewardModel.pages
            if pages is not None:
                if interaction.user.guild_permissions.administrator:
                    view = Panel(pages=pages)
                else:
                    view = SortSelectionView(pages=pages)
                await interaction.edit_original_response(
                    embed=pages[0], view=view
                )
            await removeRewardModel.on_submit_interaction.response.send_message(
                embed=removeRewardModel.update, ephemeral=True
            )
        else:
            await interaction.response.send_message(
                ":x: You are missing `Administrator` permissions.", ephemeral=True
            )

    @discord.ui.button(label="<<", style=discord.ButtonStyle.blurple, custom_id="super_prev_shop_admin", row=1)
    async def super_prev_button_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 0
        embed = self.pages[self.page]
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="<", style=discord.ButtonStyle.blurple, custom_id="prev_shop_admin", row=1)
    async def prev_button_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        else:
            self.page = len(self.pages) - 1
        embed = self.pages[self.page]
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label=">", style=discord.ButtonStyle.blurple, custom_id="next_shop_admin", row=1)
    async def next_button_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < len(self.pages) - 1:
            self.page += 1
        else:
            self.page = 0
        embed = self.pages[self.page]
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label=">>", style=discord.ButtonStyle.blurple, custom_id="super_next_shop_admin", row=1)
    async def super_next_button_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = len(self.pages) - 1
        embed = self.pages[self.page]
        await interaction.response.edit_message(embed=embed)
        
        
async def get_shop_embeds(interaction, item_list, empty_condition, sort_by="cost", reverse=True):
    if empty_condition:
        return [discord.Embed(title="This server has no purchasable items.")]

    sort_index = {"cost": 2, "name": 0}

    def key_func(x):
        if sort_by == "cost":
            return int(x[sort_index[sort_by]])
        else:
            if isinstance(x[0], int) or x[0].isdigit():  # Check if it's a role ID
                role = interaction.guild.get_role(int(x[0]))
                return role.name.lower() if role else ""  # Use role name for sorting
            return str(x[sort_index[sort_by]]).lower()

    order_text = "Descending" if reverse else "Ascending"
    sort_text = "Cost" if sort_by == "cost" else "Name"

    sorted_items = sorted(item_list, key=key_func, reverse=reverse)
    pages = []
    embed = discord.Embed(
        title=f"{interaction.guild.name}'s Server Shop",
        description=(
            f"You can use <:MystiCoin:1141391721297616906> earned in {interaction.guild.name} to purchase these items.\n"
            f"<:reply:1036792837821435976> *To check your MystiCoin balance and inventory, use </inventory:1257116518832144518>.*\n"
            f"<:reply:1036792837821435976> *To purchase an item, use </buy:1356831601174118422>.*\n"
            f"<:reply:1036792837821435976> *A 🔄 emoji indicates that the title can be purchased multiple times.*\n"
        ),
        color=discord.Color.gold()
    )

    for i, item in enumerate(sorted_items):
        count = i + 1
        if isinstance(item[0], int) or item[0].isdigit():
            role = interaction.guild.get_role(int(item[0]))
            embed.add_field(
                name=f"{count}ㅤ <:MystiCoin:1141391721297616906> {int(item[2]):,} • {role.name if role else 'Unknown Role'} {'🔄' if (len(item) > 3 and item[3]) else ''}",
                value=f"> **Role:** {role.mention if role else 'N/A'}\n> **Description:** {item[1]}",
                inline=False
            )
        else:
            embed.add_field(
                name=f"{count}ㅤ <:MystiCoin:1141391721297616906> {int(item[2]):,} • {item[0]} {'🔄' if (len(item) > 3 and item[3]) else ''}",
                value=f"> **Description:** {item[1]}",
                inline=False
            )

        # Every 5 items, start a new page
        if (i + 1) % 5 == 0 or (i + 1) == len(sorted_items):
            embed.set_footer(text=f"Sorted by {sort_text} in {order_text} order • Page {len(pages) + 1} of {len(sorted_items) // 5 + 1 if len(sorted_items) % 5 != 0 else len(sorted_items) // 5}")
            pages.append(embed)
            embed = discord.Embed(
                title=f"{interaction.guild.name}'s Server Shop",
                description=(
                    f"You can use <:MystiCoin:1141391721297616906> earned in {interaction.guild.name} to purchase these items.\n"
                    f"<:reply:1036792837821435976> *To check your mora balance and inventory, use </mora:1339721187953082543>.*\n"
                    f"<:reply:1036792837821435976> *To purchase an item, use </buy:1345883946105311382>.*\n"
                ),
                color=discord.Color.gold()
            )

    return pages


class AddRewardModel(discord.ui.Modal, title="Add a Custom Reward"):
    name = discord.ui.TextInput(
        label="Role ID / Reward Title",
        style=discord.TextStyle.short,
        placeholder="Pick one or the other to add",
        required=True,
        max_length=50,
    )
    desc = discord.ui.TextInput(
        label="Description / Perk",
        style=discord.TextStyle.short,
        placeholder="Enter a short description of the reward",
        required=True,
        max_length=150,
    )
    cost = discord.ui.TextInput(
        label="Cost of Reward",
        style=discord.TextStyle.short,
        placeholder="Must be a reasonable integer",
        required=True,
        max_length=10,
    )
    multiple = discord.ui.TextInput(
        label="Enable multiple purchases? (Titles only)",
        style=discord.TextStyle.short,
        placeholder="Enter 'yes' or 'no'",
        required=False,
        max_length=3,
    )

    # emote = discord.ui.TextInput(label="Emoji", style=discord.TextStyle.short, placeholder="(Optional) Pick an emoji", required=False, max_length=50)

    async def on_submit(self, interaction: discord.Interaction):
        ref = db.reference("/Global Events Rewards")
        rewards = ref.get()
        originalList = []
        try:
            for key, val in rewards.items():
                if val["Server ID"] == interaction.guild.id:
                    originalList = val["Rewards"]
                    print(originalList)
                    break
        except Exception:
            pass

        duplicate = False
        for item in originalList:
            if item[0] == str(self.name):
                duplicate = True
                
        multiplier_map = {'k': 10**3, 'm': 10**6, 'b': 10**9, 't': 10**12}
        cost_lower = str(self.cost).lower()
        self.cost = int(float(str(self.cost)[:-1]) * multiplier_map.get(cost_lower[-1], 1) if cost_lower[-1] in multiplier_map else float(str(self.cost)))
        
        print(str(self.cost))

        costNotInteger = False
        if not (str(self.cost).isdigit()):
            duplicate = True
            costNotInteger = True
            
        if str(self.multiple).lower() == 'yes':
            multiple = True
        else:
            multiple = False

        if duplicate is not True:
            originalList.append([str(self.name), str(self.desc), str(self.cost), multiple])

            try:
                for key, val in rewards.items():
                    if val["Server ID"] == interaction.guild.id:
                        db.reference("/Global Events Rewards").child(key).delete()
                        break
            except Exception:
                pass

            data = {
                interaction.guild.id: {
                    "Server ID": interaction.guild.id,
                    "Rewards": originalList,
                }
            }
            for key, value in data.items():
                ref.push().set(value)
            self.update = discord.Embed(
                description=f"Added reward :slight_smile:", color=discord.Color.green()
            )
        else:
            if costNotInteger:
                self.update = discord.Embed(
                    description=f"Cost must be a reasonable integer :x:",
                    color=discord.Color.red(),
                )
            else:
                self.update = discord.Embed(
                    description=f"Found duplicate entry :x:", color=discord.Color.red()
                )

        self.pages = await get_shop_embeds(
            interaction, originalList, originalList == 0
        )

        self.on_submit_interaction = interaction
        self.stop()


class RemoveRewardModel(discord.ui.Modal, title="Remove a Custom Reward"):
    name = discord.ui.TextInput(
        label="Role ID / Reward Title",
        style=discord.TextStyle.short,
        placeholder="Pick one or the other to remove",
        required=True,
        max_length=50,
    )
    
    remove = discord.ui.TextInput(
        label="Remove this item from all and compensate?",
        style=discord.TextStyle.short,
        placeholder="Type 'yes' or 'no'",
        required=True,
        max_length=3,
    )

    async def on_submit(self, interaction: discord.Interaction):
        ref = db.reference("/Global Events Rewards")
        rewards = ref.get()
        originalList = []
        try:
            for key, val in rewards.items():
                if val["Server ID"] == interaction.guild.id:
                    originalList = val["Rewards"]
                    print(originalList)
                    break
        except Exception:
            pass

        if len(originalList) == 0:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"Are you crazy? You haven't added any rewards yet... :x:",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            raise Exception()

        itemToDelete = None
        for item in originalList:
            if item[0] == str(self.name):
                itemToDelete = item

        if itemToDelete is not None:
            originalList.remove(itemToDelete)
            self.update = discord.Embed(
                description=f"Removed reward :slight_smile:",
                color=discord.Color.green(),
            )
        else:
            self.update = discord.Embed(
                description=f"Reward not found :x:", color=discord.Color.red()
            )

        try:
            for key, val in rewards.items():
                if val["Server ID"] == interaction.guild.id:
                    db.reference("/Global Events Rewards").child(key).delete()
                    break
        except Exception:
            pass

        data = {
            interaction.guild.id: {
                "Server ID": interaction.guild.id,
                "Rewards": originalList,
            }
        }
        for key, value in data.items():
            ref.push().set(value)
            
        if str(self.remove).lower() == "yes":
            ref = db.reference("/User Events Inventory")
            inventories = ref.get()

            if inventories:
                for key, val in inventories.items():
                    try:
                        # Filter out all occurrences of the matching item
                        inv = [item for item in val["Items"] if not (item[3] == interaction.guild.id and item[0] == str(self.name))]

                        if len(inv) < len(val["Items"]):  # Ensure at least one item was removed
                            db.reference("/User Events Inventory").child(key).delete()
                            data = {
                                interaction.user.id: {
                                    "User ID": interaction.user.id,
                                    "Items": inv,
                                }
                            }
                            for key, value in data.items():
                                ref.push().set(value)

                            try:
                                member = interaction.guild.get_member(int(val["User ID"]))
                                await member.send(
                                    f"**Notice:** One or more items from your guild inventory in **{interaction.guild.name}** have been deleted from the shop. The total original cost of <:MystiCoin:1141391721297616906> `{sum(int(i[2]) for i in val['Items'] if i not in inv)}` has been refunded to your inventory."
                                )

                                # Refund the total cost of all removed items
                                total_refund = sum(int(i[2]) for i in val["Items"] if i not in inv)
                                await addMora(val["User ID"], total_refund, 1, interaction.guild.id)

                                try:
                                    gangRole = interaction.guild.get_role(int(item[0]))  # Keep same logic
                                except Exception:
                                    gangRole = None

                                if gangRole is not None and gangRole in interaction.user.roles:
                                    await member.remove_roles(gangRole)
                            except Exception:
                                pass
                    except Exception:
                        pass


        self.pages = await get_shop_embeds(
            interaction, originalList, originalList == 0
        )

        self.on_submit_interaction = interaction
        self.stop()


@app_commands.guild_only()
class EventSystem(commands.GroupCog, name="events"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(
        name="enable", description="Enable random events in a channel"
    )
    @app_commands.describe(
        frequency="How often you'd like the random events to appear",
        channel="The channel to enable random events in (Current channel if not provided)",
    )
    @app_commands.choices(
        frequency=[
            app_commands.Choice(name="Very Frequent (~10%)", value="10"),
            app_commands.Choice(name="Frequent (~5%)", value="20"),
            app_commands.Choice(name="Occasional (~3%)", value="30"),
            app_commands.Choice(name="Uncommon (~2%)", value="50"),
            app_commands.Choice(name="Rare (~1%)", value="100"),
            app_commands.Choice(name="Very Rare (~0.5%)", value="200"),
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def events_enable(
        self,
        interaction: discord.Interaction,
        frequency: app_commands.Choice[str],
        channel: discord.TextChannel = None,
    ) -> None:
        if channel is None:
            channel = interaction.channel

        ref = db.reference("/Global Events System")
        stickies = ref.get()

        originalList = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S"]
        try:
            for key, val in stickies.items():
                if val["Channel ID"] == channel.id:
                    originalList = val["Events"]
                    db.reference("/Global Events System").child(key).delete()
                    break
        except Exception:
            pass

        data = {
            channel.id: {
                "Channel ID": channel.id,
                "Frequency": int(frequency.value),
                "Events": originalList,
            }
        }

        for key, value in data.items():
            ref.push().set(value)

        embed = discord.Embed(
            title="All random events enabled!",
            description=f"Now, there will be a **{100//(int(frequency.value))}%** chance for every message sent in {channel.mention} to trigger a random event! \n\n***Tip:** You can use `/events settings` to blacklist/whitelist the events you want to appear!*",
            colour=0x00FF00,
        )
        embed.timestamp = datetime.datetime.now(datetime.UTC)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        with open("./commands/Events/enabledChannels.py", "r") as file:
            lines = file.readlines()
        for i, line in enumerate(lines):
            if line.startswith("enabledChannels ="):
                existing_ids = eval(line.split("=")[1].strip())
                if channel.id not in existing_ids:
                    existing_ids.append(channel.id)
                lines[i] = f"enabledChannels = {existing_ids}\n"
                break
        with open("./commands/Events/enabledChannels.py", "w") as file:
            file.writelines(lines)

    @app_commands.command(
        name="settings",
        description="Customize the selection of random events in your server",
    )
    @app_commands.describe(
        channel="The channel that already has random events enabled (Current channel if not provided)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def events_settings(
        self, interaction: discord.Interaction, channel: discord.TextChannel = None
    ) -> None:
        if channel == None:
            channel = interaction.channel
        ref = db.reference("/Global Events System")
        stickies = ref.get()
        found = None
        for key, val in stickies.items():
            if val["Channel ID"] == channel.id:
                found = val["Events"]
                break

        if found is not None:
            string = "\n> ".join(
                [
                    f"{emoji} - {title} ✅"
                    if letter in found
                    else f"{emoji} - {title} :x:"
                    for letter, emoji, title in zip(
                        "ABCDEFGHIJKLMNOPQRS", letter_emojis, minigame_titles
                    )
                ]
            )

            embed = discord.Embed(
                title="Customize which mini-games you'd like to enable",
                description=f"**Channel:** {channel.mention}\n\n > {string}\n\nClick the button below and type in the **corresponding letter(s)** (i.e. `h` or `abdfm`) to **toggle** the mini-game(s). *To edit the frequency, use `/events enable` again.*",
                color=discord.Color.blurple(),
            )
            view = View()
            view.add_item(ToggleEventButton())
            await interaction.response.send_message(
                embed=embed, view=view, ephemeral=True
            )
        else:
            embed = discord.Embed(
                title="Random events are not enabled!",
                description=f"What are you thinking? Random event is currently not even enabled in {channel.mention}. To enable the function, use `/events enable`.",
                colour=0xFFFF00,
            )
            embed.timestamp = datetime.datetime.now(datetime.UTC)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="disable", description="Disable random events in a channel"
    )
    @app_commands.describe(
        channel="The channel to disable random events in (Current channel if not provided)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def events_disable(
        self, interaction: discord.Interaction, channel: discord.TextChannel = None
    ) -> None:
        if channel is None:
            channel = interaction.channel

        ref = db.reference("/Global Events System")
        stickies = ref.get()

        found = False
        for key, val in stickies.items():
            if val["Channel ID"] == channel.id:
                db.reference("/Global Events System").child(key).delete()
                found = True
                break

        if found:
            embed = discord.Embed(
                title="Random events disabled!",
                description=f"Sad to see you go. If you change your mind at anytime, you could use `/events enable` to enable random events again.",
                colour=0xFF0000,
            )
            embed.timestamp = datetime.datetime.now(datetime.UTC)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            with open("./commands/Events/enabledChannels.py", "r") as file:
                lines = file.readlines()
            for i, line in enumerate(lines):
                if line.startswith("enabledChannels ="):
                    existing_ids = eval(line.split("=")[1].strip())
                    existing_ids.remove(channel.id)
                    lines[i] = f"enabledChannels = {existing_ids}\n"
                    break
            with open("./commands/Events/enabledChannels.py", "w") as file:
                file.writelines(lines)
        else:
            embed = discord.Embed(
                title="Random events are not enabled!",
                description=f"What are you thinking? Random event is currently not even enabled in {channel.mention}. To start having fun, use `/events enable` to enable random games in this channel!",
                colour=0xFFFF00,
            )
            embed.timestamp = datetime.datetime.now(datetime.UTC)
            await interaction.response.send_message(embed=embed, ephemeral=True)


class ConfirmPurchaseView(discord.ui.View):
    def __init__(self, itemName=""):
        self.itemName = itemName
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Purchase Item", style=discord.ButtonStyle.green, custom_id="buy"
    )
    async def purchaseItem(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if str(interaction.user.id) not in interaction.message.embeds[0].description:
            await interaction.response.send_message(
                "You can't perform this action.", ephemeral=True
            )
            raise Exception

        roleName = self.itemName
        try:
            gangRole = interaction.guild.get_role(int(roleName))
        except Exception:
            gangRole = None
        if gangRole is not None and gangRole in interaction.user.roles:
            embed = discord.Embed(
                title="Oops!",
                description=f"You already have the {gangRole.mention} role. Unlike titles, you can only purchase roles **once**.",
                color=discord.Color.red(),
            )
            await interaction.response.edit_message(embed=embed, view=None)
            raise Exception()

        ref = db.reference("/Global Events Rewards")
        daily = ref.get()
        rewards = []
        for key, val in daily.items():
            if val["Server ID"] == interaction.guild.id:
                rewards = val["Rewards"]

        x = 0
        for i in rewards:
            if i[0] == roleName:
                break
            x += 1
        itemCost = int(rewards[x][2])
        
        cannotBuyAgain = False
        if not(len(rewards[x]) > 3 and rewards[x][3]):
            cannotBuyAgain = True

        remove = await subtractGuildMora(
            interaction.user.id, itemCost, interaction.guild.id
        )
        role_mention = (
            f"<@&{roleName}>"
            if isinstance(roleName, int) or roleName.isdigit()
            else roleName
        )
        if remove == False:
            embed = discord.Embed(
                title="Insufficient MystiCoins",
                description=f"We couldn't assign you **{role_mention}**. Please check your MystiCoin balance using </inventory:1257116518832144518> to confirm if you have enough guild-specific mora for this purchase.",
                color=discord.Color.red(),
            )
            await interaction.response.edit_message(embed=embed, view=None)
        else: # Okay to buy
            if gangRole is not None:
                await interaction.user.add_roles(gangRole)

            ref = db.reference("/User Events Inventory")
            inventories = ref.get()
            inv = []
            found = False
            foundKey = None
            if inventories:
                for key, val in inventories.items():
                    if val["User ID"] == interaction.user.id:
                        try:
                            inv = val["Items"]
                            for item in inv:
                                if item[0] == roleName:
                                    found = True
                            foundKey = key
                        except Exception as e:
                            print(e)
                        
                    if found and cannotBuyAgain:
                        role_mention = (
                            f"<@&{roleName}>"
                            if isinstance(roleName, int) or roleName.isdigit()
                            else roleName
                        )
                        embed = discord.Embed(
                            title="Oops",
                            description=f"You already own **{role_mention}**! This title does not allow multiple purchases. If you believe this is a mistake, contact a server admin.",
                            color=discord.Color.red(),
                        )
                        await addMora(interaction.user.id, itemCost, 2, interaction.guild.id)
                        await interaction.response.edit_message(embed=embed, view=None)
                        raise Exception("Already own title, cannot buy again")
                        
                    #if val["User ID"] == interaction.user.id:
                        break
                        
            if foundKey is not None:
                db.reference("/User Events Inventory").child(foundKey).delete()
                print("Updating user inventory:", interaction.user.id)

            if isinstance(rewards[x][-1], bool):
                rewards[x].pop()
            rewards[x].append(interaction.guild.id)  # Add the guild ID to the list
            rewards[x].append(int(time.mktime(datetime.datetime.now().timetuple())))  # Add timestamp 
            print("Appending", rewards[x])
            inv.append(rewards[x])  # Append the entire list to inv
            print("New user inventory:", inv)
            
            data = {
                interaction.user.id: {
                    "User ID": interaction.user.id,
                    "Items": inv,
                }
            }

            for key, value in data.items():
                ref.push().set(value)

            embed = discord.Embed(
                title="Successful Purchase",
                description=f"Congratulations! You have paid <:MystiCoin:1141391721297616906> **{itemCost:,}**. You now own **{role_mention}**.",
                color=discord.Color.green(),
            )
            await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(
        label="Cancel", style=discord.ButtonStyle.grey, custom_id="cancelbuy"
    )
    async def cancelItem(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if str(interaction.user.id) not in interaction.message.embeds[0].description:
            await interaction.response.send_message(
                "You can't perform this action.", ephemeral=True
            )
            raise Exception
        await interaction.message.delete()


class BuyInventory(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="buy", description="Purchase an item from the guild shop"
    )
    @app_commands.describe(item="The item you wish to purchase")
    @app_commands.autocomplete(item=purchase_autocomplete)
    async def buy(self, interaction: discord.Interaction, item: str) -> None:
        ref = db.reference("/Global Events Rewards")
        daily = ref.get()
        rewards = []
        for key, val in daily.items():
            if val["Server ID"] == interaction.guild.id:
                rewards = val["Rewards"]

        x = 0
        for i in rewards:
            if i[0] == item:
                break
            x += 1

        itemCost = int(rewards[x][2])

        gangRole = discord.utils.get(interaction.guild.roles, name=item)
        role_mention = (
            f"<@&{item}>" if isinstance(item, int) or item.isdigit() else item
        )
        embed = discord.Embed(
            title="Confirm Purchase",
            description=f"{interaction.user.mention}, are you sure you want to purchase **{role_mention}**?\n\n_You will pay <:MystiCoin:1141391721297616906> **{itemCost:,}** (no refund available)._",
            color=discord.Color.gold(),
        )
        await interaction.response.send_message(
            embed=embed, view=ConfirmPurchaseView(item)
        )

    @app_commands.command(
        name="shop", description="View the guild shop (Admins can edit here too)"
    )
    async def shop(
        self,
        interaction: discord.Interaction,
    ) -> None:
        ref = db.reference("/Global Events System")
        stickies = ref.get()
        found = None
        try:
            for channel in interaction.guild.channels:
                for key, val in stickies.items():
                    if val["Channel ID"] == channel.id:
                        found = val["Events"]
                        break
        except Exception:
            pass

        if found is not None:
            ref = db.reference("/Global Events Rewards")
            rewards = ref.get()
            foundGuild = "Empty"
            try:
                for key, val in rewards.items():
                    if val["Server ID"] == interaction.guild.id:
                        foundGuild = val["Rewards"]
                        break
            except Exception:
                pass
                
            pages = await get_shop_embeds(
                interaction, foundGuild, foundGuild == "Empty"
            )

            if interaction.user.guild_permissions.administrator:
                view = Panel(pages=pages)
            else:
                view = SortSelectionView(pages=pages)
                
            await interaction.response.send_message(
                embed=pages[0],
                view=view,
            )
        else:
            embed = discord.Embed(
                title="Random events are not enabled within this server!",
                description=f"What are you thinking? Random event is currently not even enabled in **{interaction.guild.name}**. To enable the function in a channel, use `/events enable`.",
                colour=0xFFFF00,
            )
            embed.timestamp = datetime.datetime.now(datetime.UTC)
            await interaction.response.send_message(embed=embed, ephemeral=True)


class NewGameUpdate(commands.Cog): 
  def __init__(self, bot):
    self.client = bot

  @commands.Cog.listener() 
  async def on_message(self, message):
        
    if message.author == self.client.user or message.author.bot == True: 
        return
    
    if message.content.startswith("-addinv"):

        roleName = "Team Mizi"
        userID = 818165830301777925
        timestamp = 1742192340

        ref = db.reference("/Global Events Rewards")
        daily = ref.get()
        rewards = []
        for key, val in daily.items():
            if val["Server ID"] == message.guild.id:
                rewards = val["Rewards"]

        x = 0
        for i in rewards:
            if i[0] == roleName:
                break
            x += 1
        itemCost = int(rewards[x][2])
        
        cannotBuyAgain = False
        if not(len(rewards[x]) > 3 and rewards[x][3]):
            cannotBuyAgain = True

        role_mention = (
            f"<@&{roleName}>"
            if isinstance(roleName, int) or roleName.isdigit()
            else roleName
        )
        if True:

            ref = db.reference("/User Events Inventory")
            inventories = ref.get()
            inv = []
            found = False
            foundKey = None
            if inventories:
                for key, val in inventories.items():
                    if val["User ID"] == userID:
                        try:
                            inv = val["Items"]
                            foundKey = key
                        except Exception as e:
                            print(e)
                        
                    #if val["User ID"] == interaction.user.id:
                        break
                        
            if foundKey is not None:
                db.reference("/User Events Inventory").child(foundKey).delete()
                print("Updating user inventory:", userID)

            if isinstance(rewards[x][-1], bool):
                rewards[x].pop()
            rewards[x].append(message.guild.id)  # Add the guild ID to the list
            rewards[x].append(int(timestamp))  # Add timestamp
            print("Appending", rewards[x])
            inv.append(rewards[x])  # Append the entire list to inv
            print("New user inventory:", inv)
            
            data = {
                userID: {
                    "User ID": userID,
                    "Items": inv,
                }
            }

            for key, value in data.items():
                ref.push().set(value)

            embed = discord.Embed(
                title="Successful Purchase",
                description=f"Congratulations! <@{userID}> now own **{role_mention}**.",
                color=discord.Color.green(),
            )
            await message.channel.send(embed=embed, view=None)
            
    if message.content == "-hi":
        await addMora(818165830301777925, 1, 2, message.guild.id)
    
    if message.content.startswith("mc!newgameupdate") and message.author.id == 692254240290242601:
        LETTER = message.content.split(" ")[1].strip().upper()  # NEW GAME LETTER
        
        ref = db.reference("/Global Events System")
        stickies = ref.get()
        originalList = None
        count = 0
        for key, val in stickies.items():
            if "beta" in message.content and 1303235296254759008 != val["Channel ID"]:
                continue
            elif "beta" not in message.content and 1303235296254759008 == val["Channel ID"]:
                continue
            originalList = val["Events"]
            frequency = val["Frequency"]
            channelID = val["Channel ID"]
            print(originalList)
            originalList.append(LETTER)
            db.reference("/Global Events System").child(key).delete()
            data = {
                channelID: {
                    "Channel ID": channelID,
                    "Frequency": frequency,
                    "Events": originalList,
                }
            }
            for key, value in data.items():
                ref.push().set(value)
            count += 1
            if "beta" in message.content and 1303235296254759008 == val["Channel ID"]:
                await message.channel.send(f"<#{channelID}> updated with `{LETTER}` enabled by default.")
                break
        await message.channel.send(f"`{count}` channels updated with `{LETTER}` enabled by default.")
                
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EventCommands(bot))
    await bot.add_cog(EventSystem(bot))
    await bot.add_cog(BuyInventory(bot))
    await bot.add_cog(NewGameUpdate(bot))