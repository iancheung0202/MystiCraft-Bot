import discord, firebase_admin, datetime, asyncio, time, emoji, random, os, string, requests, re
from firebase_admin import db
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from PIL import Image, ImageDraw, ImageFont
from essential_generators import DocumentGenerator
import pandas as pd
import matplotlib.pyplot as plt
import importlib
import os

commands_module = importlib.import_module("commands")
from commands.Events.enabledChannels import enabledChannels

last_modified = os.path.getmtime("./commands/Events/enabledChannels.py")


def check_and_reload():
    global last_modified, enabledChannels
    new_modified = os.path.getmtime("./commands/Events/enabledChannels.py")
    if new_modified > last_modified:
        with open("./commands/Events/enabledChannels.py", "r") as f:
            lines = f.readlines()
        for line in lines:
            if line.startswith("enabledChannels ="):
                new_enabled_channels = eval(
                    line.split("=")[1].strip()
                )  # Extract the new list
        if new_enabled_channels != enabledChannels:  # Only update if there's a change
            enabledChannels = new_enabled_channels
            last_modified = new_modified
            print("Random Events ./commands/Events/enabledChannels.py reloaded!")


### --- ADD MORA TO USER --- ###
async def addMora(userID, addedMora, channelID, guildID):
    channelID = str(channelID)
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
    if ogData is None:  # Initialize structure if user is new
        ogData = {"guilds": {}}
    if guildID not in ogData["guilds"]:  # Ensure guild exists
        ogData["guilds"][guildID] = {"channels": {}}
    if (
        channelID not in ogData["guilds"][guildID]["channels"]
    ):  # Ensure channel exists, if not, create a new one
        ogData["guilds"][guildID]["channels"][channelID] = {}
    timestamp = str(int(time.time()))
    ogData["guilds"][guildID]["channels"][channelID][
        timestamp
    ] = addedMora  # Append the new mora entry under the same channel
    data = {"User": {"User ID": userID, "Data": ogData}}
    if found_key:  # If user already exists, delete old entry before updating
        db.reference("/User Events Mora").child(found_key).delete()
    for key, value in data.items():
        ref.push().set(value)


def userAndTitle(userID, guildID):
    ref = db.reference("/User Events Inventory")
    inventories = ref.get()
    if inventories:
        for key, val in inventories.items():
            if val["User ID"] == userID:
                inv = val["Items"].copy()
                for i, item in enumerate(inv):
                    if item[3] == guildID and len(item) > 5 and item[5] == "Pinned":
                        role_mention = (
                            f"<@&{item[0]}>"
                            if isinstance(item[0], int) or item[0].isdigit()
                            else item[0]
                        )
                        return f"<@{userID}> **({role_mention})**"
    return f"<@{userID}>"


### --- DEFEAT THE BOSS --- ###


async def defeatTheBoss(channel, client):
    bosses = [
        "Stormterror Dvalin",
        "Andrius",
        "Childe",
        "Azhdaha",
        "La Signora",
        "Magatsu Mitake Narukami no Mikoto",
        "Everlasting Lord of Arcane Wisdom",
        "Guardian of Apep's Oasis",
        "All-Devouring Narwhal",
        "The Knave",
        "Lord of Eroded Primal Fire",
        "Geo Hypostasis",
        "Cryo Hypostasis",
        "Pyro Hypostasis",
        "Electro Hypostasis",
        "Anemo Hypostasis",
        "Hydro Hypostasis",
        "Cryo Regisvine",
        "Pyro Regisvine",
        "Oceanid",
        "Primo Geovishap",
        "Perpetual Mechanical Array",
        "Maguu Kenki",
        "Ruin Serpent",
        "Thunder Manifestation",
        "Golden Wolflord",
        "Bathysmal Vishap Herd",
        "Algorithm of Semi-Intransient Matrix of Overseer Network",
        "Aeonblight Drake",
        "Jadeplume Terrorshroom",
        "Electro Regisvine",
        "Pyro Scorpion",
        "Iniquitous Baptist",
        "Emperor of Fire and Iron",
        "Emperor of Wind and Frost",
        "Emperor of Pure Water",
        "Emperor of Lightning and Thunder",
        "Emperor of Earth and Stone",
        "Emperor of Ice and Snow",
        "Emperor of Flames and Ashes",
        "Emperor of Storms and Tempests",
        "Emperor of Shadows and Darkness",
        "Emperor of Light and Radiance",
        "Doomsday Beast",
        "Cocolia, Mother of Deception",
        "Phantylia the Undying",
        "Starcrusher Swarm King - Skaracabaz (Synthetic)",
        "Harmonious Choir - The Great Septimus",
        "Shadow of Feixiao and Ecliptic Inner Beast",
        "Abundant Ebon Deer",
        "Annihilator of Desolation Mistral",
        "Argenti (Boss)",
        "Blaznana Monkey Trick",
        "Borisin Warhead: Hoolay",
        "Savage God, Mad King, Incarnation of Strife",
        "The Giver, Master of Legions, Lance of Fury",
        "The Past, Present, and Eternal Show",
    ]
    boss = random.choice(bosses)
    punches = random.randint(4, 6)
    reward = random.randint(1000, 3000)
    seconds = random.randint(15, 20)
    msg = await channel.send(
        embed=discord.Embed(
            title=f"Defeat The Boss - {boss}",
            description=f"`{punches}` people must react with `👊` to defeat **{boss}** within `{seconds} Seconds`.\nEach user will be rewarded <:MystiCoin:1141391721297616906> `{reward}` if successful!",
            color=discord.Color.purple(),
        )
    )
    await msg.add_reaction("👊")
    await asyncio.sleep(seconds)
    msg = await msg.channel.fetch_message(msg.id)
    if msg.reactions[0].count >= punches and str(msg.reactions[0].emoji) == "👊":
        async for user in msg.reactions[0].users():
            await addMora(user.id, reward, channel.id, channel.guild.id)
        await msg.reply(
            embed=discord.Embed(
                title=f"{boss} has died!",
                description=f"Congratulations, you all have defeated the boss! \nEach user who reacted with `👊` has been awarded <:MystiCoin:1141391721297616906> `{reward}`.",
                color=discord.Color.green(),
            )
        )
    elif msg.reactions[0].count < punches and str(msg.reactions[0].emoji) == "👊":
        await msg.reply(
            embed=discord.Embed(
                title=f"{boss} NOT defeated...",
                description=f"Uh oh, only **{msg.reactions[0].count}** users reacted with `👊`. \nGood effort and best of luck next time!",
                color=discord.Color.red(),
            )
        )


### --- PICK UP THE WATERMELON --- ###


class PickUpButton(discord.ui.Button):
    def __init__(self, disabled=False):
        super().__init__(emoji="🍉", style=discord.ButtonStyle.grey, disabled=disabled)

    async def callback(self, interaction: discord.Interaction):
        reward = int(interaction.message.embeds[0].description.split("`")[3])
        await interaction.response.edit_message(
            content="",
            embed=discord.Embed(
                title=f"Pick up the watermelon - :watermelon:",
                description=f"{userAndTitle(interaction.user.id, interaction.guild.id)} picked up the `🍉` watermelon and earned <:MystiCoin:1141391721297616906> `{reward}`.",
                color=discord.Color.gold(),
            ),
            view=PickUpView(disabled=True),
        )
        await addMora(
            interaction.user.id, reward, interaction.channel.id, interaction.guild.id
        )


class PickUpView(discord.ui.View):
    def __init__(self, disabled=False):
        super().__init__(timeout=None)
        self.add_item(PickUpButton(disabled))


async def pickUpTheWatermelon(channel, client):
    reward = random.randint(3000, 6000)
    await channel.send(
        embed=discord.Embed(
            title=f"Pick up the watermelon - :watermelon:",
            description=f"First to react to the `🍉` emoji earns <:MystiCoin:1141391721297616906> `{reward}`.",
            color=discord.Color.fuchsia(),
        ),
        view=PickUpView(),
    )


### --- PICK UP THE ICECREAM --- ###


class PickUpIceCreamButton(discord.ui.Button):
    def __init__(self, disabled=False):
        super().__init__(emoji="🍦", style=discord.ButtonStyle.grey, disabled=disabled)

    async def callback(self, interaction: discord.Interaction):
        num = int(interaction.message.embeds[0].description.split("`")[1])

        reward = random.randint(1250, num)
        if random.choice(["pos", "neg"]) == "neg":
            reason = random.choice(
                [
                    "having tooth decay",
                    "having a brain freeze",
                    "catching a cold",
                    "melt",
                ]
            )
            if reason == "melt":
                await interaction.response.edit_message(
                    content="",
                    embed=discord.Embed(
                        title=f"A wild 🍦 has appeared.",
                        description=f"Unfortunately, {interaction.user.mention} did not ate the `🍦` in time. The ice cream melted and {userAndTitle(interaction.user.id, interaction.guild.id)} lost <:MystiCoin:1141391721297616906> `{reward}`.",
                        color=discord.Color.red(),
                    ),
                    view=PickUpIceCreamView(disabled=True),
                )
            else:
                await interaction.response.edit_message(
                    content="",
                    embed=discord.Embed(
                        title=f"A wild 🍦 has appeared.",
                        description=f"Unfortunately, {userAndTitle(interaction.user.id, interaction.guild.id)} ate the `🍦` and lost <:MystiCoin:1141391721297616906> `{reward}` for {reason}.",
                        color=discord.Color.red(),
                    ),
                    view=PickUpIceCreamView(disabled=True),
                )
            await addMora(
                interaction.user.id,
                -reward,
                interaction.channel.id,
                interaction.guild.id,
            )
        else:
            await interaction.response.edit_message(
                content="",
                embed=discord.Embed(
                    title=f"A wild 🍦 has appeared.",
                    description=f"{userAndTitle(interaction.user.id, interaction.guild.id)} enjoyed the `🍦` while earning <:MystiCoin:1141391721297616906> `{reward}`.",
                    color=discord.Color.green(),
                ),
                view=PickUpIceCreamView(disabled=True),
            )
            await addMora(
                interaction.user.id,
                reward,
                interaction.channel.id,
                interaction.guild.id,
            )


class PickUpIceCreamView(discord.ui.View):
    def __init__(self, disabled=False):
        super().__init__(timeout=None)
        self.add_item(PickUpIceCreamButton(disabled))


async def pickUpIceCream(channel, client):
    num = random.randint(2000, 4000)
    await channel.send(
        embed=discord.Embed(
            title=f"A wild 🍦 has appeared.",
            description=f"First to eat can earn **up to** <:MystiCoin:1141391721297616906> `{num}`, **BUT** you can also lose up to that amount. \nIt's simply a 50/50 chance.",
            color=discord.Color.fuchsia(),
        ),
        view=PickUpIceCreamView(),
    )


### --- TYPE RACER --- ###


async def createImage(
    text, bg="./assets/F7E8BE.png", filename="./assets/typeracer.png"
):
    im1 = Image.open(bg)
    color = (0, 0, 0)
    font = ImageFont.truetype("./assets/ja-jp.ttf", 55)
    d1 = ImageDraw.Draw(im1)
    d1.text((120, 60), text, font=font, fill=color)
    im1.save(filename)
    return filename


async def quicktype(channel, client):
    reward = random.randint(4000, 7000)

    gen = DocumentGenerator()
    words = str(gen.sentence())[:25]
    filename = await createImage(words)
    chn = client.get_channel(1026968305208131645)
    msg = await chn.send(file=discord.File(filename))
    url = msg.attachments[0].proxy_url
    embed = discord.Embed(
        title=f"Quicktype Racer",
        description=f"First to type the following phrase in chat wins <:MystiCoin:1141391721297616906> `{reward}`.",
        color=discord.Color.blurple(),
    )
    embed.set_image(url=url)
    msg = await channel.send(embed=embed)

    def check(message):
        return message.channel == channel

    while True:
        answer = await client.wait_for("message", check=check)
        if answer.content.strip() == words.strip():
            embed = discord.Embed(
                title=f"Quicktype Racer",
                description=f"{userAndTitle(answer.author.id, answer.guild.id)} won <:MystiCoin:1141391721297616906> `{reward}`.",
                color=discord.Color.brand_green(),
            )
            embed.set_image(url=url)
            await addMora(answer.author.id, reward, answer.channel.id, answer.guild.id)
            await msg.edit(embed=embed)
            await answer.add_reaction("✅")
            break


async def reverseQuicktype(channel, client):
    reward = random.randint(3000, 4000)

    words = "".join(str(random.randint(0, 9)) for _ in range(6))
    filename = await createImage(words, bg="./assets/94e3fe.png")
    chn = client.get_channel(1026968305208131645)
    msg = await chn.send(file=discord.File(filename))
    url = msg.attachments[0].proxy_url
    embed = discord.Embed(
        title=f"Reverse Number Quicktype",
        description=f"First to type the following numbers **IN REVERSE** in chat wins <:MystiCoin:1141391721297616906> `{reward}`.",
        color=discord.Color.blurple(),
    )
    embed.set_image(url=url)
    msg = await channel.send(embed=embed)

    def check(message):
        return message.channel == channel

    while True:
        answer = await client.wait_for("message", check=check)
        if answer.content.strip() == words.strip()[::-1]:
            embed = discord.Embed(
                title=f"Reverse Number Quicktype",
                description=f"{userAndTitle(answer.author.id, answer.guild.id)} won <:MystiCoin:1141391721297616906> `{reward}`.",
                color=discord.Color.brand_green(),
            )
            embed.set_image(url=url)
            await addMora(answer.author.id, reward, answer.channel.id, answer.guild.id)
            await msg.edit(embed=embed)
            await answer.add_reaction("✅")
            break


### --- UNSCRAMBLE THE SCRAMBLED --- ###


def scramble_string(input_string):
    char_list = list(input_string)
    random.shuffle(char_list)
    while True:
        if char_list == list(input_string):
            random.shuffle(char_list)
        else:
            break
    scrambled_string = "".join(char_list)

    return scrambled_string


async def unscrambleWords(channel, client):
    reward = random.randint(3000, 5000)
    from assets.words import words

    word = random.choice(words)
    print(word)
    scrambled = scramble_string(word)
    embed = discord.Embed(
        title=f"Unscramble the Scrambled",
        description=f"First to unscramble the following word that wins <:MystiCoin:1141391721297616906> `{reward}`.",
        color=discord.Color.blurple(),
    )
    embed.add_field(name=f"Word:", value=f"`{scrambled}`", inline=True)
    msg = await channel.send(embed=embed)

    def check(message):
        return message.channel == channel

    while True:
        answer = await client.wait_for("message", check=check)
        if answer.content.lower().strip() == word.strip():
            await answer.add_reaction("✅")
            embed = discord.Embed(
                title=f"Unscramble the Scrambled",
                description=f"{userAndTitle(answer.author.id, answer.guild.id)} won <:MystiCoin:1141391721297616906> `{reward}`.\n\n**Original:** `{scrambled}`\n**Correct:** `{word}`",
                color=discord.Color.brand_green(),
            )
            await addMora(answer.author.id, reward, answer.channel.id, answer.guild.id)
            await msg.edit(embed=embed)
            break


### --- EGGWALK --- ###


async def eggWalk(channel, client):
    reward = random.randint(1500, 2500)
    embed = discord.Embed(
        title=f"Eggwalk",
        description=f"**Users must alternate!** Start at 1 and count to 10. \nEach number you type will earn you <:MystiCoin:1141391721297616906> `{reward}` if successful.",
        color=discord.Color.dark_purple(),
    )
    msg = await channel.send(embed=embed)

    def check(message):
        return message.channel == channel

    number = 1
    previousUserID = None
    userIDs = []
    while True:
        answer = await client.wait_for("message", check=check)
        if answer.content.isnumeric():
            if answer.content.strip() == str(number):
                if answer.author.id != previousUserID:
                    number += 1
                    previousUserID = answer.author.id
                    userIDs.append(answer.author.id)
                    await answer.add_reaction("✅")
                else:
                    await answer.add_reaction("❌")
                    await msg.reply(
                        embed=discord.Embed(
                            title=f"Eggwalk",
                            description=f"One user did not alternate! Good luck next time!",
                            color=discord.Color.red(),
                        )
                    )
                    break
            else:
                await answer.add_reaction("❌")
                await msg.reply(
                    embed=discord.Embed(
                        title=f"Eggwalk",
                        description=f"Wrong number. Next number should be `{number}`! Better luck next time!",
                        color=discord.Color.red(),
                    )
                )
                break
            if number > 10:
                for userID in userIDs:
                    await addMora(userID, reward, answer.channel.id, answer.guild.id)
                await msg.reply(
                    embed=discord.Embed(
                        title=f"Eggwalk",
                        description=f"Good job everyone! That's not an easy task!\nAll of you earned <:MystiCoin:1141391721297616906> `{reward}` for every number you counted.",
                        color=discord.Color.green(),
                    )
                )
                break


### --- GUESS THE NUMBER --- ###


async def guessTheNumber(channel, client):
    reward = random.randint(2000, 3000)
    embed = discord.Embed(
        title=f"Guess The Number",
        description=f"First to guess what number in **between 1 and 10 (inclusive)** I am thinking of. \nFirst one to guess correctly will earn <:MystiCoin:1141391721297616906> `{reward}`.\n\nReacted `⬆️` means the actual number is **higher**\nReacted `⬇️` means the actual number is **lower**\n\n_Do not spam numbers in chat as I might not be able to process them._",
        color=discord.Color.dark_purple(),
    )
    msg = await channel.send(embed=embed)

    def check(message):
        return message.channel == channel

    number = random.randint(1, 10)

    while True:
        answer = await client.wait_for("message", check=check)
        if answer.content.isnumeric():
            if int(answer.content.strip()) == number:
                await answer.add_reaction("✅")
                await answer.reply(
                    embed=discord.Embed(
                        title=f"Guess The Number",
                        description=f"{userAndTitle(answer.author.id, answer.guild.id)} got it and earned <:MystiCoin:1141391721297616906> `{reward}`.",
                        color=discord.Color.green(),
                    )
                )
                await addMora(
                    answer.author.id, reward, answer.channel.id, answer.guild.id
                )
                break
            elif int(answer.content.strip()) > number:
                await answer.add_reaction("⬇️")
            else:
                await answer.add_reaction("⬆️")


### --- COUNTING MORA --- ###


async def countingCurrency(channel, client):
    reward = random.randint(3000, 5500)
    A = "<:mysticraft_dev:1267019102200008704>"
    B = "<:mysticraft:1078363938623860827>"
    C = "<:mysticraft_helper:1267016346584223836>"

    grid = [[None for _ in range(15)] for _ in range(15)]
    fill_probability = 0.2  # Adjust this value to control sparsity

    for i in range(15):
        for j in range(15):
            if random.random() < fill_probability:
                choice = random.choice([A, B, C])
                grid[i][j] = choice

    gridString = ""
    for row in grid:
        for col in row:
            if col == None:
                gridString = f"{gridString}ㅤ"
            else:
                gridString = f"{gridString}{col}"
        gridString = f"{gridString}\n"

    itemToCount = random.choice([A, B, C])
    embed = discord.Embed(
        title=f"Counting Logos",
        description=f"{gridString}\nFirst to count how many {itemToCount} there are wins <:MystiCoin:1141391721297616906> `{reward}`",
        color=discord.Color.blue(),
    )
    msg = await channel.send(embed=embed)

    def check(message):
        return message.channel == channel

    number = sum(row.count(itemToCount) for row in grid)
    while True:
        answer = await client.wait_for("message", check=check)
        if answer.content.isnumeric():
            if int(answer.content.strip()) == number:
                await answer.add_reaction("✅")
                await answer.reply(
                    embed=discord.Embed(
                        title=f"Counting Logos",
                        description=f"{userAndTitle(answer.author.id, answer.guild.id)} got it and earned <:MystiCoin:1141391721297616906> `{reward}`.",
                        color=discord.Color.green(),
                    )
                )
                await addMora(
                    answer.author.id, reward, answer.channel.id, answer.guild.id
                )
                break
            else:
                await answer.add_reaction("❌")


### --- MATCH THE PROFILE PICTURE --- ###


class matchPFPBtn(discord.ui.Button):
    def __init__(self, name, disabled=False):
        super().__init__(
            label=name, emoji="👤", style=discord.ButtonStyle.grey, disabled=disabled
        )

    async def callback(self, interaction: discord.Interaction):
        reward = int(interaction.message.embeds[0].description.split("`")[1])
        url = interaction.message.embeds[0].image.url
        ref = db.reference("/Global Events")
        randomevents = ref.get()
        for key, val in randomevents.items():
            if val["User ID"] == "Match the Profile Picture":
                user = val["Mora"]
                break

        duplicate = []
        for key, val in randomevents.items():
            if val["User ID"] == "Those who answered":
                duplicate = val["Mora"]
                break

        if int(interaction.user.id) in duplicate:
            await interaction.response.send_message(
                ":x: You have guessed once already. No second try!", ephemeral=True
            )
        else:
            if str(self.label) == user:
                embed = discord.Embed(
                    title=f"Who's this?",
                    description=f"{userAndTitle(interaction.user.id, interaction.guild.id)} guessed **{str(self.label)}** correctly and earned <:MystiCoin:1141391721297616906> `{reward}`.",
                    color=discord.Color.green(),
                )
                embed.set_image(url=url)
                await interaction.response.edit_message(
                    content="", embed=embed, view=None
                )
                await addMora(
                    interaction.user.id,
                    reward,
                    interaction.channel.id,
                    interaction.guild.id,
                )

                for key, val in randomevents.items():
                    if val["User ID"] == "Those who answered":
                        db.reference("/Global Events").child(key).delete()
            else:
                await interaction.response.send_message("Wrong! :x:", ephemeral=True)
                duplicate.append(int(interaction.user.id))
                data = {
                    "Those who answered": {
                        "User ID": "Those who answered",
                        "Mora": duplicate,
                    }
                }

                for key, value in data.items():
                    ref.push().set(value)


async def matchThePFP(channel, client):
    reward = random.randint(3500, 5500)
    messages = [message async for message in channel.history(limit=200)]
    selected_items = []
    unique_ids = set()
    for message in messages:
        if (
            message.author.id not in unique_ids
            and message.author.id != 732422232273584198
        ):
            selected_items.append(message)
            unique_ids.add(message.author.id)
        if len(selected_items) == 100:
            break
    random_numbers = random.sample(range(len(selected_items)), 3)
    random_items = [selected_items[i] for i in random_numbers]
    embed = discord.Embed(
        title=f"Who's this?",
        description=f"The first to guess wins <:MystiCoin:1141391721297616906> `{reward}`. **You can only guess once!**",
        color=discord.Color.light_grey(),
    )
    user = random.choice(random_items).author
    embed.set_image(url=user.avatar.url)
    view = View()
    for item in random_items:
        view.add_item(matchPFPBtn(str(item.author)))
    ref = db.reference("/Global Events")
    randomevents = ref.get()
    try:
        for key, val in randomevents.items():
            if val["User ID"] == "Match the Profile Picture":
                db.reference("/Global Events").child(key).delete()
    except Exception:
        pass
    data = {
        "Match the Profile Picture": {
            "User ID": "Match the Profile Picture",
            "Mora": str(user),
        }
    }
    for key, value in data.items():
        ref.push().set(value)
    await channel.send(embed=embed, view=view)


### --- WHO SAID IT --- ###


class whoSaidItBtn(discord.ui.Button):
    def __init__(self, name, disabled=False):
        super().__init__(
            label=name, emoji="👤", style=discord.ButtonStyle.grey, disabled=disabled
        )

    async def callback(self, interaction: discord.Interaction):
        reward = int(interaction.message.embeds[0].description.split("`")[1])
        ref = db.reference("/Global Events")
        randomevents = ref.get()
        duplicate = []
        for key, val in randomevents.items():
            if val["User ID"] == "Who said it":
                user = val["Mora"]
            if val["User ID"] == "Who said it Jump URL":
                jumpUrl = val["Mora"]
            if val["User ID"] == "Those who answered in who said it":
                duplicate = val["Mora"]

        if int(interaction.user.id) in duplicate:
            await interaction.response.send_message(
                ":x: You have guessed once already. No second try!", ephemeral=True
            )
        else:
            if str(self.label) == user:
                embed = discord.Embed(
                    title=f"Who said it?",
                    description=f"{userAndTitle(interaction.user.id, interaction.guild.id)} guessed **{str(self.label)}** correctly and earned <:MystiCoin:1141391721297616906> `{reward}`.\n\n[Message Jump URL]({jumpUrl})",
                    color=discord.Color.green(),
                )
                await interaction.response.edit_message(
                    content="", embed=embed, view=None
                )
                await addMora(
                    interaction.user.id,
                    reward,
                    interaction.channel.id,
                    interaction.guild.id,
                )

                for key, val in randomevents.items():
                    if val["User ID"] == "Those who answered in who said it":
                        db.reference("/Global Events").child(key).delete()
            else:
                await interaction.response.send_message("Wrong! :x:", ephemeral=True)
                duplicate.append(int(interaction.user.id))
                data = {
                    "Those who answered in who said it": {
                        "User ID": "Those who answered in who said it",
                        "Mora": duplicate,
                    }
                }

                for key, value in data.items():
                    ref.push().set(value)


async def whoSaidIt(channel, client):
    reward = random.randint(3500, 6000)
    messages = [
        message
        async for message in channel.history(limit=100)
        if message.author.id != client.user.id
        and (message.content != "" or message.content != None)
        and len(message.embeds) == 0
        and len(message.attachments) == 0
        and len(message.stickers) == 0
    ]
    random_messages = random.sample(messages, 3)
    message = random.choice(random_messages)
    embed = discord.Embed(
        title=f"Who said it?",
        description=f"The first to guess wins <:MystiCoin:1141391721297616906> `{reward}`. **You can only guess once!**",
        color=discord.Color.light_grey(),
    )
    embed.add_field(name=f"Message Content", value=message.content, inline=True)
    view = View()
    for item in random_messages:
        view.add_item(whoSaidItBtn(str(item.author)))
    ref = db.reference("/Global Events")
    randomevents = ref.get()
    try:
        for key, val in randomevents.items():
            if (
                val["User ID"] == "Who said it"
                or val["User ID"] == "Who said it Jump URL"
                or val["User ID"] == "Those who answered in who said it"
            ):
                db.reference("/Global Events").child(key).delete()
    except Exception:
        print(Exception)
    data = {"Who said it": {"User ID": "Who said it", "Mora": str(message.author)}}
    for key, value in data.items():
        ref.push().set(value)
    data = {
        "Who said it Jump URL": {
            "User ID": "Who said it Jump URL",
            "Mora": str(message.jump_url),
        }
    }
    for key, value in data.items():
        ref.push().set(value)
    await channel.send(embed=embed, view=view)


### --- MEMORY GAME --- ###


class memoryBtn(discord.ui.Button):
    def __init__(self, emote, disabled=False):
        super().__init__(emoji=emote, style=discord.ButtonStyle.grey, disabled=disabled)

    async def callback(self, interaction: discord.Interaction):
        reward = int(interaction.message.embeds[0].description.split("`")[1])

        ref = db.reference("/Global Events")
        randomevents = ref.get()
        for key, val in randomevents.items():
            if val["User ID"] == "Memory Game":
                emote = val["Mora"]
                break

        duplicate = []
        for key, val in randomevents.items():
            if val["User ID"] == "Those who answered in Memory Game":
                duplicate = val["Mora"]
                break

        if int(interaction.user.id) in duplicate:
            await interaction.response.send_message(
                ":x: You have guessed once already. No second try!", ephemeral=True
            )
        else:
            if str(self.emoji) == emote:
                embed = discord.Embed(
                    title=f"Memory Game",
                    description=f"{userAndTitle(interaction.user.id, interaction.guild.id)} guessed correctly and earned <:MystiCoin:1141391721297616906> `{reward}`.",
                    color=discord.Color.green(),
                )
                await interaction.response.edit_message(
                    content="", embed=embed, view=None
                )
                await addMora(
                    interaction.user.id,
                    reward,
                    interaction.channel.id,
                    interaction.guild.id,
                )

                for key, val in randomevents.items():
                    if val["User ID"] == "Those who answered in Memory Game":
                        db.reference("/Global Events").child(key).delete()
            else:
                await interaction.response.send_message("Wrong! :x:", ephemeral=True)
                duplicate.append(int(interaction.user.id))
                data = {
                    "Those who answered in Memory Game": {
                        "User ID": "Those who answered in Memory Game",
                        "Mora": duplicate,
                    }
                }

                for key, value in data.items():
                    ref.push().set(value)


async def memoryGame(channel, client):
    reward = random.randint(4000, 5000)

    allEmojis = [
        "😄",
        "😊",
        "😃",
        "😉",
        "😍",
        "😘",
        "😚",
        "😗",
        "😙",
        "😜",
        "😝",
        "😛",
        "🤑",
        "🤓",
        "😎",
        "🤗",
        "🙂",
        "🤔",
        "😐",
        "😑",
        "😶",
        "🙄",
        "😏",
        "😒",
        "🤥",
        "😌",
        "😔",
        "😪",
        "🤤",
        "😴",
        "😷",
        "🤒",
        "🤕",
        "🤢",
        "🤧",
        "😢",
        "😭",
        "😰",
        "😥",
        "😓",
        "😈",
        "👿",
        "👹",
        "👺",
        "💩",
        "👻",
        "💀",
        "👽",
        "🤖",
        "🎃",
        "🎉",
        "🌟",
        "🔥",
        "❤️",
        "💙",
        "💜",
        "💛",
        "💚",
        "🖤",
        "💖",
        "💗",
        "💓",
        "💕",
        "💞",
        "💘",
        "💝",
        "💌",
        "💍",
        "💎",
        "🎀",
        "🌈",
        "👍",
        "👎",
        "👌",
        "✌",
        "🤞",
        "🤟",
        "🤘",
        "👏",
        "🙌",
        "🤲",
        "💪",
        "🙏",
        "👊",
        "🤛",
        "🤜",
        "💅",
        "👀",
        "👁",
        "👅",
        "🐶",
        "🐱",
        "🐭",
        "🐹",
        "🐰",
        "🦊",
        "🐻",
        "🐼",
        "🐨",
        "🐯",
        "🦁",
        "🐷",
        "🐸",
        "🐵",
        "🦄",
        "🐉",
        "🐲",
        "🐍",
        "🦎",
        "🐢",
        "🍕",
        "🌺",
        "📚",
        "⚽",
        "🎵",
        "🍔",
        "🍦",
        "🎂",
        "🎁",
        "🎈",
        "🎨",
        "🚀",
        "⌛",
        "💡",
        "🎮",
        "📷",
        "📱",
        "💻",
        "⭐",
        "🌙",
        "🍎",
        "🍉",
        "🍇",
        "🍓",
        "🥑",
        "🍩",
        "🥨",
        "🥗",
        "🍿",
        "🍰",
        "🚗",
        "🚕",
        "🚙",
        "🚌",
        "🚎",
        "🚜",
        "🚲",
        "✈",
        "🚁",
        "🛳",
    ]

    emojis = random.sample(allEmojis, 3)
    chosenCol = random.randint(0, 2)
    chosenEmote = emojis[chosenCol]
    chosenCol += 1

    embed = discord.Embed(
        title=f"Memory Game",
        description=f"Remember the following order of emotes. You will be asked to recall which column an emoji is from. **You can only guess once!**\n\nFirst to guess correctly wins <:MystiCoin:1141391721297616906> `{reward}`.",
        color=discord.Color.light_grey(),
    )

    for x in range(3):
        embed.add_field(name=f"Column {x+1}", value=f"`{emojis[x]}`", inline=True)

    msg = await channel.send(embed=embed)
    await asyncio.sleep(5)
    await msg.delete()

    view = View()
    random.shuffle(emojis)
    for emote in emojis:
        view.add_item(memoryBtn(str(emote)))

    ref = db.reference("/Global Events")
    randomevents = ref.get()
    try:
        for key, val in randomevents.items():
            if (
                val["User ID"] == "Memory Game"
                or val["User ID"] == "Those who answered in Memory Game"
            ):
                db.reference("/Global Events").child(key).delete()
    except Exception:
        pass
    data = {"Memory Game": {"User ID": "Memory Game", "Mora": str(chosenEmote)}}
    for key, value in data.items():
        ref.push().set(value)

    await channel.send(
        embed=discord.Embed(
            title=f"Memory Game",
            description=f"Now, which of the following emote was in **Column {chosenCol}**? **You can only guess once!**\n\nFirst to guess correctly wins <:MystiCoin:1141391721297616906> `{reward}`.",
            color=discord.Color.light_grey(),
        ),
        view=view,
    )


### --- TWO TRUTH AND A LIE --- ###


class answerLieBtn(discord.ui.Button):
    def __init__(self, emote, disabled=False):
        super().__init__(emoji=emote, style=discord.ButtonStyle.grey, disabled=disabled)

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) in interaction.message.embeds[0].description:
            await interaction.response.send_message(
                "You can't answer your own question smh", ephemeral=True
            )
            raise Exception()
        reward = int(interaction.message.embeds[0].description.split("`")[1])
        ref = db.reference("/Global Events")
        randomevents = ref.get()
        for key, val in randomevents.items():
            if val["User ID"] == "Two Truths And A Lie":
                emote = val["Mora"]
                break

        duplicate = []
        for key, val in randomevents.items():
            if val["User ID"] == "Those who answered in ttal":
                duplicate = val["Mora"]
                break

        if int(interaction.user.id) in duplicate:
            await interaction.response.send_message(
                ":x: You have guessed once already. No second try!", ephemeral=True
            )
        else:
            if str(self.emoji) == str(emote):
                embed = interaction.message.embeds[0]
                await interaction.message.edit(content="", embed=embed, view=None)

                await addMora(
                    interaction.user.id,
                    reward,
                    interaction.channel.id,
                    interaction.guild.id,
                )
                embed = discord.Embed(
                    title=f"Two Truths And A Lie",
                    description=f"{userAndTitle(interaction.user.id, interaction.guild.id)} chose {self.emoji} correctly and earned <:MystiCoin:1141391721297616906> `{reward}`!",
                    color=discord.Color.green(),
                )
                embed.set_footer(
                    text="Now you all know a little bit more about each other."
                )
                await interaction.response.send_message(embed=embed)
                for key, val in randomevents.items():
                    if val["User ID"] == "Those who answered in ttal":
                        db.reference("/Global Events").child(key).delete()
            else:
                for key, val in randomevents.items():
                    if val["User ID"] == "Those who answered in ttal":
                        db.reference("/Global Events").child(key).delete()
                await interaction.response.send_message("Wrong! :x:", ephemeral=True)
                duplicate.append(int(interaction.user.id))
                data = {
                    "Those who answered in ttal": {
                        "User ID": "Those who answered in ttal",
                        "Mora": duplicate,
                    }
                }

                for key, value in data.items():
                    ref.push().set(value)


class TwoTruthAndALieModal(discord.ui.Modal, title="Enter your two truths and one lie"):

    truth1 = discord.ui.TextInput(
        label="Truth #1",
        style=discord.TextStyle.short,
        placeholder="Enter a TRUE statement about yourself.",
        max_length=256,
        required=True,
    )

    truth2 = discord.ui.TextInput(
        label="Truth #2",
        style=discord.TextStyle.short,
        placeholder="Enter another TRUE statement about yourself.",
        max_length=256,
        required=True,
    )

    lie = discord.ui.TextInput(
        label="Lie",
        style=discord.TextStyle.short,
        placeholder="Enter a FALSE statement about yourself.",
        max_length=256,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        truth1 = str(self.truth1)
        truth2 = str(self.truth2)
        lie = str(self.lie)
        reward = int(interaction.message.embeds[0].description.split("`")[1])
        statements = [truth1, truth2, lie]

        random.shuffle(statements)

        if statements[0] == lie:
            emote = "<:mystcraft_owner:1267018399293243523>"
        elif statements[1] == lie:
            emote = "<:mysticraft_admin:1267020293134614620>"
        elif statements[2] == lie:
            emote = "<:mysticraft_helper:1267016346584223836>"

        ref = db.reference("/Global Events")
        randomevents = ref.get()
        try:
            for key, val in randomevents.items():
                if (
                    val["User ID"] == "Two Truths And A Lie"
                    or val["User ID"] == "Those who answered in ttal"
                ):
                    db.reference("/Global Events").child(key).delete()
        except Exception:
            pass
        data = {
            "Two Truths And A Lie": {"User ID": "Two Truths And A Lie", "Mora": emote}
        }
        for key, value in data.items():
            ref.push().set(value)

        self.update = discord.Embed(
            title="Two Truths and A Lie",
            description=f'First to determine which of the following statement by {userAndTitle(interaction.user.id, interaction.guild.id)} is a lie wins <:MystiCoin:1141391721297616906> `{reward}`!\n\n <:mystcraft_owner:1267018399293243523> "{statements[0]}"\n <:mysticraft_admin:1267020293134614620> "{statements[1]}"\n <:mysticraft_helper:1267016346584223836> "{statements[2]}"',
        )

        self.on_submit_interaction = interaction
        self.stop()


class TwoTruthAndALieButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Enter your two truths and one lie",
            emoji="🤫",
            style=discord.ButtonStyle.grey,
        )

    async def callback(self, interaction: discord.Interaction):
        msg = interaction.message.embeds[0].description
        if str(interaction.user.id) not in msg:
            await interaction.response.send_message(
                "You can't click this button!", ephemeral=True
            )
            raise Exception()

        if (
            "entering their truths and lies..."
            not in interaction.message.embeds[0].description
        ):
            await interaction.message.edit(
                embed=discord.Embed(
                    title="Two Truths and A Lie",
                    description=f"{msg}\n\n> *{userAndTitle(interaction.user.id, interaction.guild.id)} is entering their truths and lies...*",
                )
            )

        modal = TwoTruthAndALieModal()
        await interaction.response.send_modal(modal)
        response = await modal.wait()

        await interaction.message.edit(
            embed=discord.Embed(title="Two Truths and A Lie", description=f"{msg}"),
            view=None,
        )

        view = View()
        view.add_item(answerLieBtn("<:mystcraft_owner:1267018399293243523>"))
        view.add_item(answerLieBtn("<:mysticraft_admin:1267020293134614620>"))
        view.add_item(answerLieBtn("<:mysticraft_helper:1267016346584223836>"))
        await modal.on_submit_interaction.response.send_message(
            embed=modal.update, view=view
        )


async def twoTruthsAndALie(channel, client):
    reward = random.randint(4000, 7000)
    messages = [message async for message in channel.history(limit=5)]
    for x in range(4):
        user = messages[x].author
        if user.bot:
            continue
        else:
            break
    view = View()
    view.add_item(TwoTruthAndALieButton())
    await channel.send(
        embed=discord.Embed(
            title="Two Truths and A Lie",
            description=f"{userAndTitle(user.id, channel.guild.id)} will be entering their **three statements**. First to determine which statement is a lie wins <:MystiCoin:1141391721297616906> `{reward}`!",
        ),
        view=view,
    )


### --- SPLIT or STEAL --- ###


class split(discord.ui.Button):
    def __init__(self, disabled=False):
        super().__init__(
            label="Split", emoji="🤝", style=discord.ButtonStyle.green, disabled=disabled
        )

    async def callback(self, interaction: discord.Interaction):
        reward = int(interaction.message.embeds[0].title.split("`")[1])
        a = interaction.message.mentions[0]
        b = interaction.message.mentions[1]

        ref = db.reference("/Global Events")
        randomevents = ref.get()

        if interaction.user == a:  # A chose "Split"
            aChoice = "Split"
            bChoice = None
            try:
                for key, val in randomevents.items():
                    if val["User ID"] == "Split Or Steal":
                        aChoice = val["Mora"][0]
                        bChoice = val["Mora"][1]
                        break
            except Exception:
                pass
            if aChoice != "Split" and aChoice != None:
                await interaction.response.send_message(
                    f"You can't change your selection!", ephemeral=True
                )
            elif bChoice == None:
                data = {
                    "Split Or Steal": {
                        "User ID": "Split Or Steal",
                        "Mora": ["Split", None],
                    }
                }
                for key, value in data.items():
                    ref.push().set(value)
                await interaction.response.send_message(
                    f"Still waiting for {userAndTitle(b.id, interaction.guild.id)} to make their choice...",
                    ephemeral=True,
                )
            elif bChoice == "Split":
                await interaction.response.edit_message(
                    content=interaction.message.content, view=None
                )
                await interaction.message.reply(
                    embed=discord.Embed(
                        title="Split Success! 🎉",
                        description=f"Congrats, both {userAndTitle(a.id, interaction.guild.id)} and {userAndTitle(b.id, interaction.guild.id)} chose Split. You each won <:MystiCoin:1141391721297616906> `{int(reward/2)}`!",
                        color=discord.Color.green(),
                    )
                )
                await addMora(
                    a.id, int(reward / 2), interaction.channel.id, interaction.guild.id
                )
                await addMora(
                    b.id, int(reward / 2), interaction.channel.id, interaction.guild.id
                )
            elif bChoice == "Steal":
                await interaction.response.edit_message(
                    content=interaction.message.content, view=None
                )
                await interaction.message.reply(
                    embed=discord.Embed(
                        title="It's a Steal! 💰",
                        description=f"{userAndTitle(b.id, interaction.guild.id)} stole all the money and won <:MystiCoin:1141391721297616906> `{reward}`!",
                        color=discord.Color.yellow(),
                    )
                )
                await interaction.channel.send(f"")
                await addMora(
                    b.id, reward, interaction.channel.id, interaction.guild.id
                )

        elif interaction.user == b:  # B chose "Split"
            bChoice = "Split"
            aChoice = None
            try:
                for key, val in randomevents.items():
                    if val["User ID"] == "Split Or Steal":
                        aChoice = val["Mora"][0]
                        bChoice = val["Mora"][1]
                        break
            except Exception:
                pass
            if bChoice != "Split" and bChoice != None:
                await interaction.response.send_message(
                    f"You can't change your selection!", ephemeral=True
                )
            elif aChoice == None:
                data = {
                    "Split Or Steal": {
                        "User ID": "Split Or Steal",
                        "Mora": [None, "Split"],
                    }
                }
                for key, value in data.items():
                    ref.push().set(value)
                await interaction.response.send_message(
                    f"Still waiting for {userAndTitle(a.id, interaction.guild.id)} to make their choice...",
                    ephemeral=True,
                )
            elif aChoice == "Split":
                await interaction.response.edit_message(
                    content=interaction.message.content, view=None
                )
                await interaction.message.reply(
                    embed=discord.Embed(
                        title="Split Success! 🎉",
                        description=f"Congrats, both {userAndTitle(a.id, interaction.guild.id)} and {userAndTitle(b.id, interaction.guild.id)} chose Split. You each won <:MystiCoin:1141391721297616906> `{int(reward/2)}`!",
                        color=discord.Color.green(),
                    )
                )
                await addMora(
                    a.id, int(reward / 2), interaction.channel.id, interaction.guild.id
                )
                await addMora(
                    b.id, int(reward / 2), interaction.channel.id, interaction.guild.id
                )
            elif aChoice == "Steal":
                await interaction.response.edit_message(
                    content=interaction.message.content, view=None
                )
                await interaction.message.reply(
                    embed=discord.Embed(
                        title="It's a Steal! 💰",
                        description=f"{userAndTitle(a.id, interaction.guild.id)} stole all the money and won <:MystiCoin:1141391721297616906> `{reward}`!",
                        color=discord.Color.yellow(),
                    )
                )
                await addMora(
                    a.id, reward, interaction.channel.id, interaction.guild.id
                )

        else:
            await interaction.response.send_message(
                "You are not part of this game!", ephemeral=True
            )


class steal(discord.ui.Button):
    def __init__(self, disabled=False):
        super().__init__(
            label="Steal", emoji="🤑", style=discord.ButtonStyle.red, disabled=disabled
        )

    async def callback(self, interaction: discord.Interaction):
        reward = int(interaction.message.embeds[0].title.split("`")[1])
        a = interaction.message.mentions[0]
        b = interaction.message.mentions[1]

        ref = db.reference("/Global Events")
        randomevents = ref.get()

        if interaction.user == a:  # A chose "Steal"
            aChoice = "Steal"
            bChoice = None
            try:
                for key, val in randomevents.items():
                    if val["User ID"] == "Split Or Steal":
                        aChoice = val["Mora"][0]
                        bChoice = val["Mora"][1]
                        break
            except Exception:
                pass
            if aChoice != "Steal" and aChoice != None:
                await interaction.response.send_message(
                    f"You can't change your selection!", ephemeral=True
                )
            elif bChoice == None:
                data = {
                    "Split Or Steal": {
                        "User ID": "Split Or Steal",
                        "Mora": ["Steal", None],
                    }
                }
                for key, value in data.items():
                    ref.push().set(value)
                await interaction.response.send_message(
                    f"Still waiting for {userAndTitle(b.id, interaction.guild.id)} to make their choice...",
                    ephemeral=True,
                )
            elif bChoice == "Split":
                await interaction.response.edit_message(
                    content=interaction.message.content, view=None
                )
                await interaction.message.reply(
                    embed=discord.Embed(
                        title="It's a Steal! 💰",
                        description=f"{userAndTitle(a.id, interaction.guild.id)} stole all the money and won <:MystiCoin:1141391721297616906> `{reward}`!",
                        color=discord.Color.yellow(),
                    )
                )
                await addMora(
                    a.id, reward, interaction.channel.id, interaction.guild.id
                )
            elif bChoice == "Steal":
                await interaction.response.edit_message(
                    content=interaction.message.content, view=None
                )
                await interaction.message.reply(
                    embed=discord.Embed(
                        title=random.choice(
                            [
                                "Both Got Nothing :person_shrugging:",
                                "Greed Leaves You With Nothing 💸",
                                "Greed Got the Best of You... :x:",
                                "No Winners This Time... :person_shrugging:",
                                "Mutual Betrayal ❌",
                            ]
                        ),
                        description=f"Both {userAndTitle(a.id, interaction.guild.id)} and {userAndTitle(b.id, interaction.guild.id)} chose Steal. No money for y'all.",
                        color=discord.Color.red(),
                    )
                )

        elif interaction.user == b:  # B chose "Steal"
            bChoice = "Steal"
            aChoice = None
            try:
                for key, val in randomevents.items():
                    if val["User ID"] == "Split Or Steal":
                        aChoice = val["Mora"][0]
                        bChoice = val["Mora"][1]
                        break
            except Exception:
                pass
            if bChoice != "Steal" and bChoice != None:
                await interaction.response.send_message(
                    f"You can't change your selection!", ephemeral=True
                )
            elif aChoice == None:
                data = {
                    "Split Or Steal": {
                        "User ID": "Split Or Steal",
                        "Mora": [None, "Steal"],
                    }
                }
                for key, value in data.items():
                    ref.push().set(value)
                await interaction.response.send_message(
                    f"Still waiting for {userAndTitle(a.id, interaction.guild.id)} to make their choice...",
                    ephemeral=True,
                )
            elif aChoice == "Split":
                await interaction.response.edit_message(
                    content=interaction.message.content, view=None
                )
                await interaction.message.reply(
                    embed=discord.Embed(
                        title="It's a Steal! 💰",
                        description=f"{userAndTitle(b.id, interaction.guild.id)} stole all the money and won <:MystiCoin:1141391721297616906> `{reward}`!",
                        color=discord.Color.yellow(),
                    )
                )
                await addMora(
                    b.id, reward, interaction.channel.id, interaction.guild.id
                )
            elif aChoice == "Steal":
                await interaction.response.edit_message(
                    content=interaction.message.content, view=None
                )
                await interaction.message.reply(
                    embed=discord.Embed(
                        title=random.choice(
                            [
                                "Both Got Nothing :person_shrugging:",
                                "Greed Leaves You With Nothing 💸",
                                "Greed Got the Best of You... :x:",
                                "No Winners This Time... :person_shrugging:",
                                "Mutual Betrayal ❌",
                            ]
                        ),
                        description=f"Both {userAndTitle(a.id, interaction.guild.id)} and {userAndTitle(b.id, interaction.guild.id)} chose Steal. No money for y'all.",
                        color=discord.Color.red(),
                    )
                )

        else:
            await interaction.response.send_message(
                "You are not part of this game!", ephemeral=True
            )


async def splitOrSteal(channel, client):
    reward = random.randint(5000, 9000)
    messages = [message async for message in channel.history(limit=20)]
    selected_items = []
    unique_ids = set()
    for message in messages:
        if (
            message.author.id not in unique_ids
            and message.author.id != 732422232273584198
            and message.author.bot == False
        ):
            selected_items.append(message)
            unique_ids.add(message.author.id)
        if len(selected_items) == 2:
            break
    a = selected_items[0].author
    b = selected_items[1].author
    view = View()
    view.add_item(split())
    view.add_item(steal())
    ref = db.reference("/Global Events")
    randomevents = ref.get()
    try:
        for key, val in randomevents.items():
            if val["User ID"] == "Split Or Steal":
                db.reference("/Global Events").child(key).delete()
    except Exception:
        pass
    await channel.send(
        f"{userAndTitle(a.id, channel.guild.id)} and {userAndTitle(b.id, channel.guild.id)}",
        embed=discord.Embed(
            title=f"Choose to **Split or Steal** <:MystiCoin:1141391721297616906> `{reward}`!",
            color=0x7F00FF,
        ),
        view=view,
    )


### --- ROCK PAPER SCISSORS --- ###


class Rock(discord.ui.Button):
    def __init__(self, disabled=False):
        super().__init__(
            label="Rock", emoji="🪨", style=discord.ButtonStyle.red, disabled=disabled
        )

    async def callback(self, interaction: discord.Interaction):
        await process_rps_choice(interaction, "Rock")


class Paper(discord.ui.Button):
    def __init__(self, disabled=False):
        super().__init__(
            label="Paper", emoji="📄", style=discord.ButtonStyle.green, disabled=disabled
        )

    async def callback(self, interaction: discord.Interaction):
        await process_rps_choice(interaction, "Paper")


class Scissors(discord.ui.Button):
    def __init__(self, disabled=False):
        super().__init__(
            label="Scissors",
            emoji="✂️",
            style=discord.ButtonStyle.grey,
            disabled=disabled,
        )

    async def callback(self, interaction: discord.Interaction):
        await process_rps_choice(interaction, "Scissors")


async def process_rps_choice(interaction, choice):
    if interaction.user not in interaction.message.mentions:
        await interaction.response.send_message(
            "You are not part of the game!", ephemeral=True
        )
        return

    reward = int(interaction.message.embeds[0].description.split("`")[1])
    a = interaction.message.mentions[0]
    b = interaction.message.mentions[1]

    ref = db.reference("/Global Events")
    randomevents = ref.get()

    event_key = None
    existing_choice = None
    existing_player = None

    # Check if there is an existing choice stored
    try:
        for key, val in randomevents.items():
            if val["User ID"] == "Rock Paper Scissors":
                existing_choice = val["Choice"]
                existing_player = val["Player"]
                break
    except Exception as e:
        print(e)

    if existing_choice:  # Second player chooses → Compare immediately
        if interaction.user.id == existing_player:
            await interaction.response.send_message(
                "You have already chosen!", ephemeral=True
            )
            return

        await determine_rps_winner(
            interaction,
            await interaction.client.fetch_user(existing_player),
            interaction.user,
            existing_choice,
            choice,
            reward,
        )

        # Remove event from database after determining the winner
        for key, val in randomevents.items():
            if val["User ID"] == "Rock Paper Scissors":
                db.reference("/Global Events").child(key).delete()
    else:  # First player chooses → Store choice and start a timeout task
        entry_ref = ref.push()
        entry_ref.set(
            {
                "User ID": "Rock Paper Scissors",
                "Choice": choice,
                "Player": interaction.user.id,
            }
        )
        await interaction.response.send_message(
            f"Still waiting for {userAndTitle(b.id, interaction.guild.id) if interaction.user == a else userAndTitle(a.id, interaction.guild.id)} to choose...",
            ephemeral=True,
        )

        # Start a cleanup task to remove the entry if the second player never responds
        async def cleanup_later(randomevents):
            await asyncio.sleep(120)  # Wait 2 minutes
            for key, val in randomevents.items():
                if val["User ID"] == "Rock Paper Scissors":
                    db.reference("/Global Events").child(key).delete()

        asyncio.create_task(cleanup_later(randomevents))


async def determine_rps_winner(interaction, a, b, aChoice, bChoice, reward):
    results = {
        ("Rock", "Scissors"): a,
        ("Scissors", "Paper"): a,
        ("Paper", "Rock"): a,
        ("Scissors", "Rock"): b,
        ("Paper", "Scissors"): b,
        ("Rock", "Paper"): b,
    }

    rps_dict = {"Rock": "🪨", "Paper": "📄", "Scissors": "✂️"}

    aEmoji = rps_dict.get(aChoice, aChoice)
    bEmoji = rps_dict.get(bChoice, bChoice)

    if aChoice == bChoice:
        a = interaction.guild.get_member(a.id)
        b = interaction.guild.get_member(b.id)
        result_embed = discord.Embed(
            title=f"Both {a.nick if a.nick is not None else a.name} and {b.nick if b.nick is not None else b.name} chose **{aEmoji}**.",
            description=f"It's a tie! You each earn <:MystiCoin:1141391721297616906> `{int(reward/7)}` for participating!",
            color=discord.Color.yellow(),
        )
        await addMora(
            a.id, int(reward / 7), interaction.channel.id, interaction.guild.id
        )
        await addMora(
            b.id, int(reward / 7), interaction.channel.id, interaction.guild.id
        )
    else:
        winner = interaction.guild.get_member(results.get((aChoice, bChoice)).id)
        await addMora(winner.id, reward, interaction.channel.id, interaction.guild.id)
        result_embed = discord.Embed(
            title=f"{winner.nick if winner.nick is not None else winner.name} won <:MystiCoin:1141391721297616906> `{reward}`!",
            description=f"{userAndTitle(a.id, interaction.guild.id)} chose **{aEmoji}**, {userAndTitle(b.id, interaction.guild.id)} chose **{bEmoji}**",
            color=discord.Color.green(),
        )

    await interaction.response.edit_message(
        content=interaction.message.content, view=None
    )
    await interaction.message.reply(embed=result_embed)


async def rockPaperScissors(channel, client):
    messages = [message async for message in channel.history(limit=50)]
    selected_items = []
    unique_ids = set()

    for message in messages:
        if message.author.id not in unique_ids and not message.author.bot:
            selected_items.append(message)
            unique_ids.add(message.author.id)
        if len(selected_items) == 2:
            break

    if len(selected_items) < 2:
        await channel.send("Not enough players for Rock Paper Scissors!")
        return

    a, b = selected_items[0].author, selected_items[1].author
    view = View()
    view.add_item(Rock())
    view.add_item(Paper())
    view.add_item(Scissors())

    # Clear previous event
    ref = db.reference("/Global Events")
    randomevents = ref.get()
    try:
        for key, val in randomevents.items():
            if val["User ID"] == "Rock Paper Scissors":
                db.reference("/Global Events").child(key).delete()
    except Exception:
        pass

    await channel.send(
        content=f"{userAndTitle(a.id, channel.guild.id)} vs {userAndTitle(b.id, channel.guild.id)}",
        embed=discord.Embed(
            title=f"Choose **Rock, Paper, or Scissors!**",
            description=f"Winner gets <:MystiCoin:1141391721297616906> `{random.randint(4000, 5000)}`.",
            color=0xFF5349,
        ),
        view=view,
    )


class TheEventItself(commands.Cog):
    def __init__(self, bot):
        self.client = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.client.user or message.author.bot == True:
            return

        check_and_reload()
        if message.channel.id in enabledChannels:
            ref = db.reference("/Global Events System")
            events = ref.get()
            frequency = None
            try:
                for key, val in events.items():
                    if val["Channel ID"] == message.channel.id:
                        frequency = val["Frequency"]
                        originalList = val["Events"]
                        break
            except Exception:
                pass
            if frequency is not None and message.id % frequency == 0:
                okForEvent = True
                messages = [
                    message
                    async for message in message.channel.history(limit=frequency)
                ]
                for msg in messages:
                    try:
                        if len(msg.embeds) > 0 and msg.author.id == self.client.user.id:
                            okForEvent = False
                    except Exception:
                        pass
                if okForEvent:
                    embed = discord.Embed(
                        description="Since chat is relatively active, I'm dropping a random event in `3 seconds`.",
                        color=discord.Color.orange(),
                    )
                    embed.set_footer(
                        text=random.choice(
                            [
                                "Legacy players are those who started playing before April 2025.",
                                "Use /inventory to check your MystiCoin profile!",
                                "Use /shop to check out purchasable rewards!",
                                "Have questions? Create a ticket!",
                            ]
                        )
                    )
                    await message.channel.send(embed=embed)

                    letters = list("ABCDEFGHIJKLMNOPQR")
                    events = [
                        defeatTheBoss,
                        quicktype,
                        eggWalk,
                        matchThePFP,
                        splitOrSteal,
                        reverseQuicktype,
                        pickUpIceCream,
                        pickUpTheWatermelon,
                        guessTheNumber,
                        memoryGame,
                        whoSaidIt,
                        unscrambleWords,
                        twoTruthsAndALie,
                        countingCurrency,
                        rockPaperScissors,
                        unscrambleWords,
                        twoTruthsAndALie,
                        countingCurrency,
                        rockPaperScissors,
                        
                        #guessTheCharacter,
                        #guessTheVoiceline,
                        #emojiRiddle,
                        #trueOrFalse
                    ]
                    letter_to_event = dict(zip(letters, events))
                    eligible_events = [
                        letter_to_event[letter]
                        for letter in originalList
                        if letter in letter_to_event
                    ]
                    event = random.choice(eligible_events)
                    await asyncio.sleep(2.4)
                    await event(message.channel, self.client)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TheEventItself(bot))