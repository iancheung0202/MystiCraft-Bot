import discord
try:
    from utils.commands import SlashCommand
except ImportError:
    class SlashCommand:
        def __init__(self, name):
            self.name = name

        def __str__(self):
            return f"`/{self.name}`"

CURRENCY_NAME = "Shards"
MORA_EMOTE = "<:nether_star:1518033504120606771>"

SIGIL_CURRENCY_NAME = "MystiCoins"
SIGIL_EMOTE = "<:MystiCoin:1141391721297616906>"

YES_EMOTE = "<:emerald:1518031176730804244>"    
NO_EMOTE = "<:barrier:1518454369887195228>"
YES_EMOTE_2 = "<:greencheckmark:1141391421480390726>"
NO_EMOTE_2 = "<:redcrossmark:1141391465206001836>"
RESOLVED_EMOTE = "<:emoji_36:1330638100006965269>"
UNRESOLVED_EMOTE = "<:heart:1523013916433842412>"
HMM_EMOTE = "<:question:1523014598628737198>"
THINK_EMOTE = "<:emoji_36:1330638100006965269>"
NO_STOCK_EMOTE = "<a:out_of_stock:1384990609584033812>"
LOADING_EMOTE = "<a:loading:1026905298088243240>"
SHRUG_EMOTE = "<:emoji_36:1330638100006965269>"
HAPPY_EMOTE = "<:luffythumbs:1373446751406788728>"
MONEYDANCE_EMOTE = "<a:moneydance:1227425759077859359>"
DOT_EMOTE = "<:dot:1357188726047899760>"
CONFUSED_EMOTE = "<:question:1523014598628737198>"
REPLY_EMOTE = "<:reply:1036792837821435976>"
TRACK_EMOTE = "<:mysticraftlogo:1263829753366974535>"
PRESTIGE_EMOTE = "<:Trophy:1523013568067539044>"
SIGILS_MESSAGE_EMOTE = "<:steve:1154872824037650603>"

GUILD_MORA_EMOTE = MORA_EMOTE
GLOBAL_MORA_EMOTE = "<:nether_star_2:1525330563328638987>"
GUILD_SIGIL_EMOTE = SIGIL_EMOTE
GLOBAL_SIGIL_EMOTE = "<:MystiToken:1525308123219361792>"

MORA_TO_XP_RATIO = 0.01
SIGILS_TO_XP_RATIO = 1000

DEFAULT_CHAT_RANGE = (19, 25)
DEFAULT_CHAT_MAX_CAP = 60
DEFAULT_CHAT_MSG_RANGE = (15, 20)

BALANCE_COMMAND = "inventory"
PROFILE_LINK_BUTTON = discord.ui.Button(label="Visit our Store", style=discord.ButtonStyle.link, url=f"https://store.mysticraft.xyz", emoji="<:shop:1518114830501023935>", row=1, disabled=False)

FRAMES_DIRECTORY = "./assets/Profile Frame"
INVENTORY_BG_PATH = "./assets/Mora Inventory Background"
ANIMATED_INVENTORY_BG_PATH = "./assets/Animated Mora Inventory Background"
GRAPHS_DIRECTORY = "./assets/graph"
DEFAULT_BG_PATH = "./assets/mora_bg.png"
FONT_PATH = "./assets/MinecraftTen-VGORe.ttf"
TYPERACER_FONT_PATH = "./assets/Minecraft.otf"
FONT_PRESETS = {
    "Default": FONT_PATH,
    ### TO BE ADDED
}
PROFILE_CARD_PATH = "./assets/mora.png"
TYPERACER_BG_PATH = "./assets/F7E8BE.png"
TYPERACER_PATH = "./assets/typeracer.png"
CURRENCY_ICON_PATH = "./assets/mora_icon.png"

PRICE_UP_EMOTE = "<:price_ascending:1346329079145562112>"
PRICE_DOWN_EMOTE = "<:price_descending:1346329080462577725>"
NAME_UP_EMOTE = "<:name_ascending:1346329053455585324>"
NAME_DOWN_EMOTE = "<:name_descending:1346329054634053703>"
SHOP_SORT_OPTIONS = [("sort by cost (low to high)", PRICE_UP_EMOTE), ("sort by cost (high to low)", PRICE_DOWN_EMOTE), ("sort by name (a-z)", NAME_UP_EMOTE), ("sort by name (z-a)", NAME_DOWN_EMOTE),]
SHOP_CURRENCY_FILTERS = [
    ("All currencies", "<:stats:1523014008490426468>"),
    (f"Guild {CURRENCY_NAME}", GUILD_MORA_EMOTE),
    (f"Global {CURRENCY_NAME}", GLOBAL_MORA_EMOTE),
    (f"Guild {SIGIL_CURRENCY_NAME}", GUILD_SIGIL_EMOTE),
    (f"Global {SIGIL_CURRENCY_NAME}", GLOBAL_SIGIL_EMOTE),
]
CURRENCY_INFO = {
    "guild_mora": {
        "emoji": GUILD_MORA_EMOTE, 
        "label": f"Guild {CURRENCY_NAME}", 
        "filter_label": f"Guild {CURRENCY_NAME}"
    },
    "global_mora": {
        "emoji": GLOBAL_MORA_EMOTE, 
        "label": f"Global {CURRENCY_NAME}", 
        "filter_label": f"Global {CURRENCY_NAME}"
    },
    "guild_sigils": {
        "emoji": GUILD_SIGIL_EMOTE, 
        "label": f"Guild {SIGIL_CURRENCY_NAME}", 
        "filter_label": f"Guild {SIGIL_CURRENCY_NAME}"
    },
    "global_sigils": {
        "emoji": GLOBAL_SIGIL_EMOTE, 
        "label": f"Global {SIGIL_CURRENCY_NAME}", 
        "filter_label": f"Global {SIGIL_CURRENCY_NAME}"
    },
}
MILESTONE_SORT_OPTIONS = [("sort by threshold (low to high)", PRICE_UP_EMOTE), ("sort by threshold (high to low)", PRICE_DOWN_EMOTE), ("sort by name (a-z)", NAME_UP_EMOTE), ("sort by name (z-a)", NAME_DOWN_EMOTE),]

DROP_TIERS = ["Coal", "Iron", "Gold", "Diamond", "Netherite", "Enchanted"]
DROP_WEIGHTS = [0.3, 0.25, 0.2, 0.15, 0.08, 0.02]
DROP_AMOUNTS = {
    "Tiny": (500, 999),
    "Small": (1500, 2000),
    "Medium": (3000, 3500),
    "Large": (6000, 6700),
    "Huge": (9800, 10200),
    "Mega": (13000, 15000),
}
XP_BONUS_CHANCE = 0.2
BONUS_XP = 1000

MORA_CHEST_NAME = "Daily Mystic Chest"
MORA_CHEST_TIERS = ["Cobblestone", "Mossy", "Obsidian", "Ancient"]
MORA_CHEST_REWARDS = [2500, 7500, 15000, 30000]
MORA_CHEST_UPGRADE_CHANCES = [0.3, 0.15, 0.2]
MORA_CHEST_UPGRADE_TIMES = 4
MORA_CHEST_STREAK_BONUS = 100
MORA_CHEST_MAX_STREAK_BONUS = 10000
MORA_CHEST_SPAWN_REQ = (4, 6)
MORA_CHEST_TIMEOUT = 300 
MORA_TIER_MAP = dict(zip(MORA_CHEST_TIERS, MORA_CHEST_REWARDS))
EMOTE_STREAK = "<a:streak:1371651844652273694>"
EMOTE_MAX_STREAK = "<a:max_streak:1371655286049214672>"
EMOTE_BLANK = "<:blank:1036792889121980426>"
def build_chest_description(gc: dict = None) -> str:
    if gc is None:
        gc = {}
    tier_names = gc.get("chests_tier_names", MORA_CHEST_TIERS)
    tier_rewards = gc.get("chests_tier_rewards", MORA_CHEST_REWARDS)
    upgrade_chances = gc.get("chests_upgrade_chances", MORA_CHEST_UPGRADE_CHANCES)
    spawn_req = gc.get("chests_spawn_req", list(MORA_CHEST_SPAWN_REQ))
    streak_bonus = gc.get("chests_streak_bonus", MORA_CHEST_STREAK_BONUS)
    max_streak = gc.get("chests_max_streak_bonus", MORA_CHEST_MAX_STREAK_BONUS)
    base_upgrades = gc.get("chests_base_upgrade_chances", MORA_CHEST_UPGRADE_TIMES)
    spawn_low = spawn_req[0] if len(spawn_req) > 0 else 4
    spawn_high = spawn_req[1] if len(spawn_req) > 1 else spawn_req[0]
    lines = [
        f"## How the {MORA_CHEST_NAME} Works 🎁",
        f"{DOT_EMOTE} Earn a chest per day after sending **{spawn_low} to {spawn_high} effortful messages** in minigame channels.",
        f"{DOT_EMOTE} Messages must be spaced out and not repetitive/spammy.",
        f"{DOT_EMOTE} A chest starts as **{tier_names[0] if tier_names else '?'}**, containing {MORA_EMOTE} `{tier_rewards[0]:,}`." if tier_rewards else "",
        f"{DOT_EMOTE} You get a minimum of **{base_upgrades} chances** to upgrade your chest.",
        f"{DOT_EMOTE} You must claim your chest within **{MORA_CHEST_TIMEOUT // 60} minutes** or it will be wasted.",
        f"{DOT_EMOTE} After claiming, wait until the next **UTC +0 midnight** to earn a new chest.",
        f"### Rewards (Base {CURRENCY_NAME}) 🏆",
    ]
    for i in range(len(tier_names)):
        r = tier_rewards[i] if i < len(tier_rewards) else 0
        lines.append(f"{DOT_EMOTE} **{tier_names[i]}**:   **`{r:,}`** {CURRENCY_NAME}")
    lines.append("### Upgrade Chances :arrow_up:")
    for i in range(len(tier_names) - 1):
        c = upgrade_chances[i] * 100 if i < len(upgrade_chances) else 0
        lines.append(f"{DOT_EMOTE} `{tier_names[i]} \u2192 {tier_names[i+1]}: {c:.0f}% chance`")
    lines.append(f"### Streak Bonus {EMOTE_STREAK}")
    lines.append(f"{DOT_EMOTE} You gain a **daily streak** if you claim a chest every day.")
    lines.append(f"{DOT_EMOTE} Each day in your streak adds `+{streak_bonus}` {MORA_EMOTE} (max {max_streak}) to the reward.")
    lines.append(f"{DOT_EMOTE} Miss a day? Your streak resets to 1.")
    return "\n".join(l for l in lines if l)

VIEW_FULL_TRACK = ""
TIPS = [
    "Send effortful messages to earn daily chests 📦",
    f"Reach {SlashCommand('milestones')} to earn titles/roles! Check it out! 💎",
    f"Use {SlashCommand('customize')} to add a custom inventory background image & pin titles 🌆",
    f"Hug your favorite person(s) using {SlashCommand('hug')} 🫂",
    f"Check your {SlashCommand('inventory')} with all your stats 🎉",
    f"Use {SlashCommand('gift')} to send Shards to your friends or even strangers! 🎁",
]

KINGDOM_NAME = "Structure"
DOMAIN_NAME = "Structures"
DOMAIN_DESCRIPTION = "Upgrade your structures to unlock powerful buffs"

BUILDINGS = {
    "schloss": {
        "name": "Stronghold", 
        "emoji": "👁️", 
        "desc": "The central fortress. (Max level for others)", 
        "color": discord.ButtonStyle.blurple
    },
    "theater": {
        "name": "Trial Chamber", 
        "emoji": "🗝️", 
        "desc": "Where challenges await. (Refund Summon minigame chance)", 
        "color": discord.ButtonStyle.grey
    },
    "bibliothek": {
        "name": "Enchanting Room", 
        "emoji": "🔮", 
        "desc": "Ancient wisdom. (Quest XP Boost)", 
        "color": discord.ButtonStyle.success
    },
    "garten": {
        "name": "Mob Farm", 
        "emoji": "⚔️", 
        "desc": "Automated riches. (Bonus Summon in Chest chance)", 
        "color": discord.ButtonStyle.danger
    }
}

def get_rank_title(level):
    rank = "Steve"
    if level >= 10: rank = "Miner"
    if level >= 25: rank = "Crafter"
    if level >= 50: rank = "Raider"
    if level >= 75: rank = "Speedrunner"
    if level >= 100: rank = "Gladiator"
    if level >= 150: rank = "Redstoner"
    if level >= 200: rank = "Survivor"
    if level >= 300: rank = "Operator"
    return rank

def calculate_cost(level):
    return int(5000 * (1.1 ** level))

def perk_info(key, lvl):
    if key == "schloss": 
        func_desc = "Command Center"
        perk_val = f"*(Max level for others)*"
    elif key == "theater": 
        func_desc = "Refund Summon"
        chance = min(50, lvl)
        perk_val = f"`{chance}%` chance"
    elif key == "bibliothek": 
        func_desc = "Quest XP Boost"
        boost = min(50, lvl)
        perk_val = f"`+{boost}%` XP"
    elif key == "garten": 
        func_desc = "Bonus Summon in Chest"
        chance = min(50, lvl)
        perk_val = f"`{chance}%` chance"
    return func_desc, perk_val

class ThanksEliteTrack(discord.ui.Button):
    def __init__(self, is_active=False):
        super().__init__(
            label="Elite Patron",
            style=discord.ButtonStyle.green,
            disabled=True,
            emoji="<:patronplusicon:1523992174767898755>", 
            row=1
        )
    async def callback(self, interaction: discord.Interaction):
        pass
    
class PurchaseEliteTrack(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Elite Track",
            style=discord.ButtonStyle.green,
            emoji="<:patronplusicon:1523992174767898755>",
            row=1
        )

    async def callback(self, interaction: discord.Interaction):
        elite_button = discord.ui.Button(
            label="Become a Patron",
            style=discord.ButtonStyle.link,
            url="https://store.mysticraft.xyz",
            emoji="<:shop:1518114830501023935>"
        )
        
        embed = discord.Embed(
            title=f"{TRACK_EMOTE} Elite Track for Patrons only <:patronplusicon:1523992174767898755>", 
            description=(
                f"If you are **one of our top-tier <@&1523960131174531152> ($500+) or <@&1523959442570477568> ($100+)** "
                f"who graciously supports MystiCraft, you are eligible to claim your lifetime **Elite Track** benefits "
                "by simply creating a ticket at <#1136672651209871541>!\n\n"
                f"-# {HAPPY_EMOTE} Thank you for your incredible contribution to being a vital part of our awesome community!"
            ), 
            color=0xf472b6
        )
        
        view = discord.ui.View()
        view.add_item(elite_button)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

QUEST_TYPES = ["participate_minigames", "win_minigames", "win_1v1_minigames", "earn_mora", "gift_mora", "collect_chests", "earn_big_mora", "gift_mora_unique", "summon_minigame", "customize_profile", "purchase_items", "unlock_drop_packs", "upgrade_buildings", "gift_mora_poorer", "hug_user", "win_minigames_under_5s"]
QUEST_GOAL_PRESETS = {
    "participate_minigames": {
        "daily": [4, 5],
        "weekly": [14, 16, 18],
        "monthly": [60, 70, 80]
    },
    "win_minigames": {
        "daily": [2, 3],
        "weekly": [8, 9, 10],
        "monthly": [25, 30, 35]
    },
    "win_1v1_minigames": {
        "daily": [1],
        "weekly": [4, 5, 6],
        "monthly": [10, 15, 20]
    },
    "earn_mora": {
        "daily": [15000, 17500, 20000],
        "weekly": [50000, 60000, 70000],
        "monthly": [250000, 275000, 300000]
    },
    "gift_mora": {
        "daily": [1000, 2000, 3000],
        "weekly": [10000, 15000, 20000],
        "monthly": [50000, 75000, 100000]
    },
    "collect_chests": {
        "daily": [1],
        "weekly": [5, 6, 7],
        "monthly": [20, 22, 24]
    },
    "earn_big_mora": {
        "daily": [1, 2],
        "weekly": [5, 7],
        "monthly": [20, 25]
    },
    "gift_mora_unique": {
        "daily": [2, 3],
        "weekly": [5, 7],
        "monthly": [15, 20]
    },
    "summon_minigame": {
        "daily": [1],
        "weekly": [3, 4, 5, 6],
        "monthly": [15, 20]
    },
    "customize_profile": {
        "daily": [1],
        "weekly": [2, 3],
        "monthly": [5, 6]
    },
    "purchase_items": {
        "monthly": [1, 2, 3]
    },
    "unlock_drop_packs": {
        "weekly": [1],
        "monthly": [2, 3]
    },
    "upgrade_buildings": {
        "daily": [1],
        "weekly": [3, 4],
        "monthly": [8, 10]
    },
    "gift_mora_poorer": {
        "daily": [1, 2],
        "weekly": [3, 5],
        "monthly": [10, 15]
    },
    "hug_user": {
        "daily": [2, 3],
        "weekly": [5, 7],
        "monthly": [15, 20]
    },
    "win_minigames_under_5s": {
        "daily": [1, 2],
        "weekly": [4, 5],
        "monthly": [12, 15]
    }
}
QUEST_DESCRIPTIONS = {
    "participate_minigames": "Participate in minigames",
    "win_minigames": "Win minigames",
    "win_1v1_minigames": "Win 1v1 minigames",
    "earn_mora": "Earn Shards",
    "gift_mora": "Gift Shards",
    "collect_chests": "Collect chests",
    "earn_big_mora": "Earn 10k+ Shards in one go",
    "gift_mora_unique": f"{SlashCommand('gift')} Shards to different users",
    "summon_minigame": f"{SlashCommand('summon')} a minigame",
    "customize_profile": f"{SlashCommand('customize')} your profile",
    "purchase_items": f"Purchase {SlashCommand('shop')} items with {SlashCommand('buy')}",
    "unlock_drop_packs": "Unlock Shards Drop packs",
    "upgrade_buildings": "Upgrade your Realm buildings 🏰",
    "gift_mora_poorer": f"{SlashCommand('gift')} Shards to users with less Shards",
    "hug_user": f"{SlashCommand('hug')} other users",
    "win_minigames_under_5s": "Win minigames in under 5 seconds"
}
QUEST_XP_REWARDS = {
    "daily": 250,
    "weekly": 500,
    "monthly": 1500
}
QUEST_BONUS_XP = {
    "daily": 500,
    "weekly": 1500,
    "monthly": 4500
}

class Season:
    def __init__(self, id, name, start_ts, end_ts, track_data):
        self.id = id
        self.name = name
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.track_data = track_data

SEASONS = [
    Season(
        id=1,
        name="Summer Chapters",
        start_ts=1782864001,   # July 1, 2026
        end_ts=1790812800,     # October 1, 2026
        track_data = [
            {'tier': 1,  'xp_req': 1000, 'cumulative_xp': 1000,    'free': 'Drop Pack',                                                      'elite': 'Custom Accent Color'},
            {'tier': 2,  'xp_req': 1000, 'cumulative_xp': 2000,    'free': 'Coin Gain Boost +5%',                                            'elite': 'Express Daily Chests'},
            {'tier': 3,  'xp_req': 1000, 'cumulative_xp': 3000,    'free': '+3 Minigames Summon',                                            'elite': 'Custom Title'},
            {'tier': 4,  'xp_req': 1000, 'cumulative_xp': 4000,    'free': 'Drop Pack',                                                      'elite': 'Coin Gain Boost +10%'},
            {'tier': 5,  'xp_req': 1000, 'cumulative_xp': 5000,    'free': 'Unlocks Gifting',                                           'elite': 'Coin Gift Tax -10%'},
            {'tier': 6,  'xp_req': 1000, 'cumulative_xp': 6000,    'free': 'Server Title | The Golden Apple Vacation Returns!',              'elite': 'Shop Discount +10%'},
            {'tier': 7,  'xp_req': 1000, 'cumulative_xp': 7000,   'free': 'Drop Pack',                                                       'elite': '+1 Chest Upgrade Limit'},
            {'tier': 8,  'xp_req': 1000, 'cumulative_xp': 8000,   'free': '+1 Chest Upgrade Limit',                                          'elite': 'Structure Discount +10%'},
            {'tier': 9,  'xp_req': 1000, 'cumulative_xp': 9000,   'free': 'Coin Gain Boost +5%',                                             'elite': 'Custom Card Font'},
            {'tier': 10, 'xp_req': 1000, 'cumulative_xp': 10000,   'free': 'Drop Pack',                                                      'elite': 'Custom GIF Background'},
            {'tier': 11, 'xp_req': 1000, 'cumulative_xp': 11000,   'free': 'Coin Gift Tax -5%',                                              'elite': 'Animated Frame | ' + FRAMES_DIRECTORY + '/Jade Stone.gif'},
            {'tier': 12, 'xp_req': 1000, 'cumulative_xp': 12000,   'free': '+1 Chest Upgrade Limit',                                         'elite': 'Coin Gain Boost +10%'},
            {'tier': 13, 'xp_req': 1000, 'cumulative_xp': 13000,   'free': 'Coin Gain Boost +5%',                                            'elite': 'Coin Gift Tax -10%'},
            {'tier': 14, 'xp_req': 1000, 'cumulative_xp': 14000,   'free': 'Static Frame | ' + FRAMES_DIRECTORY + '/Snowglobe.png',          'elite': 'Shop Discount +10%'},
            {'tier': 15, 'xp_req': 1000, 'cumulative_xp': 15000,   'free': 'Drop Pack',                                                      'elite': '+30 Minigames Summon'},
            {'tier': 16, 'xp_req': 2500, 'cumulative_xp': 17500,   'free': 'Coin Gift Tax -5%',                                              'elite': '+1 Chest Upgrade Limit'},
            {'tier': 17, 'xp_req': 2500, 'cumulative_xp': 20000,   'free': 'Drop Pack',                                                      'elite': 'Structure Discount +10%'},
            {'tier': 18, 'xp_req': 2500, 'cumulative_xp': 22500,   'free': 'Coin Gain Boost +5%',                                            'elite': 'Coin Gain Boost +10%'},
            {'tier': 19, 'xp_req': 2500, 'cumulative_xp': 25000,   'free': '+1 Chest Upgrade Limit',                                         'elite': 'Shop Discount +10%'},
            {'tier': 20, 'xp_req': 2500, 'cumulative_xp': 27500,   'free': 'Server Title | Immernachtreich Apokalypse',                      'elite': 'Structure Discount +10%'},
            {'tier': 21, 'xp_req': 2500, 'cumulative_xp': 30000,   'free': 'Coin Gain Boost +5%',                                            'elite': 'Animated Frame | ' + FRAMES_DIRECTORY + '/Dragon Mouth.gif'},
            {'tier': 22, 'xp_req': 2500, 'cumulative_xp': 32500,   'free': '+3 Minigames Summon',                                            'elite': 'Coin Gain Boost +10%'},
            {'tier': 23, 'xp_req': 2500, 'cumulative_xp': 35000,   'free': 'Coin Gain Boost +5%',                                            'elite': '+1 Chest Upgrade Limit'},
            {'tier': 24, 'xp_req': 2500, 'cumulative_xp': 37500,   'free': 'Coin Gift Tax -5%',                                              'elite': 'Shop Discount +10%'},
            {'tier': 25, 'xp_req': 2500, 'cumulative_xp': 40000,   'free': 'Drop Pack',                                                      'elite': 'Structure Discount +10%'},
            {'tier': 26, 'xp_req': 5000, 'cumulative_xp': 45000,   'free': 'Static Frame | ' + FRAMES_DIRECTORY + '/Mountains.png',          'elite': 'Animated Frame | ' + FRAMES_DIRECTORY + '/Holodragon.gif'},
            {'tier': 27, 'xp_req': 5000, 'cumulative_xp': 50000,   'free': 'Coin Gain Boost +5%',                                            'elite': 'Coin Gain Boost +10%'},
            {'tier': 28, 'xp_req': 5000, 'cumulative_xp': 55000,   'free': '+3 Minigames Summon',                                            'elite': 'Coin Gift Tax -10%'},
            {'tier': 29, 'xp_req': 5000, 'cumulative_xp': 60000,   'free': 'Drop Pack',                                                      'elite': 'Shop Discount +10%'},
            {'tier': 30, 'xp_req': 5000, 'cumulative_xp': 65000,   'free': 'Server Title | What a beautiful day!',                           'elite': 'Structure Discount +10%'},
            {'tier': 31, 'xp_req': 5000, 'cumulative_xp': 70000,  'free': 'Prestige +1',                                                     'elite': 'Prestige +1'},
        ]
    ),
]

REWARD_TYPES = {
    "Drop Pack": "drop_pack",
    "Animated Background": "animated_background",
    "Custom GIF Background": "custom_gif_background",
    "Static Frame": "static_frame",
    "Animated Frame": "animated_frame",
    "Prestige +1": "prestige",
    "Coin Gain Boost +5%": "mora_boost",
    "Coin Gain Boost +67%": "mora_boost_67",
    "+1 Chest Upgrade Limit": "chest_upgrade",
    "+69 Chest Upgrade Limit": "chest_upgrade_69",
    "Unlocks Gifting": "unlock_gifting",
    "Coin Gift Tax -5%": "gift_tax",
    "+3 Minigames Summon": "minigame_summon",
    "Custom Embed Color": "accent_color",
    "Custom Accent Color": "accent_color",
    "Server Title": "title",
    "Custom Title": "custom_title",
    "Animated Title": "title",
    "Custom Card Font": "font_unlock",
    "Shop Discount +10%": "shop_discount",
    "Structure Discount +10%": "domain_discount",
    "Express Daily Chests": "express_daily_chests",
    "+30 Minigames Summon": "minigame_summon_30",
}

XP_QUEST_EMBED = discord.Embed(
    title="What Are XP & Quests <:question:1523014598628737198>",
    color=discord.Color.random()
).add_field(
    name="<:map:1518038367521210499> Quests ➜ XP",
    value="-# Complete daily, weekly, and monthly quests to **earn XP** just by playing, winning, or gifting!",
    inline=True
).add_field(
    name="<:gold_ingot:1518031441248653433> XP ➜ Rewards",
    value="-# Earning XP moves you up the Progression Track to **unlock boosts, chest upgrades, titles**, and more!",
    inline=True
).add_field(
    name="<:feather:1518454349053952150> Track in One Place",
    value=f"-# Use {SlashCommand('inventory')} to view **quests, XP, and rewards**. Each season's track lasts **3 months**!",
    inline=True
)

MINIGAME_TITLES = [
    "Boss Battle Blitz",
    "Quicktype Racer",
    "Egg Walk",
    "Match The Profile Picture",
    "Split or Steal",
    "Reverse Number Quicktype",
    "Pick Up Ice Cream",
    "Snatch The Watermelon",
    "Guess The Mystery Number",
    "Memory Game",
    "Who Said That",
    "Unscramble Words",
    "Two Truths, One Lie",
    "Currency Counting",
    "Rock Paper Scissors Duel",
    "Roll A Dice",
    "Group Blackjack",
    "Teyvat Emoji Riddles",
    "Galaxy Emoji Riddles",
    "Double or Keep",
    "Know Your Members",
    "Hangman",
    "Grand Auction House",
    "Bank Heist",
    "Simple Math Game",
    "Tik Tac Tok"
] # also present in event.py 
# 1 --> self.minigame_mapping 
# 2 --> letter_to_event = dict(zip(LETTER_LIST, events))

LETTER_LIST = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
LETTER_EMOTES = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷", "🇸", "🇹", "🇺", "🇻", "🇼", "🇽", "🇾", "🇿"]

BOSSES = [
    # --- Official Vanilla Bosses ---
    "The Ender Dragon",
    "The Wither",
    
    # --- Vanilla Mini-Bosses / Raid Bosses ---
    "The Warden",
    "Elder Guardian",
    "Evoker",
    "The Breeze",
    "Piglin Brute",
    "Ravager",
    
    # --- Minecraft Dungeons Bosses ---
    "The Arch-Illager",
    "The Heart of Ender",
    "The Nameless One",
    "Redstone Monstrosity",
    "Redstone Golem",
    "The Jungle Abomination",
    "The Corrupted Cauldron",
    "The Vengeful Heart of Ender",
    
    # --- Minecraft Story Mode & Legends Bosses ---
    "The Wither Storm",
    "The Great Hog",
    "The Devourer",
    "The Beast",
    
    # --- Legendary Modded Bosses (Universally Recognized) ---
    "The Twilight Lich",
    "The Hydra",
    "Ur-Ghast",
    "Naga",
    "The Snow Queen",
    "The Chaos Guardian",
    "Mutant Zombie",
    "Mutant Skeleton",
    "Herobrine"
]
HSR_EMOJI_RIDDLE_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR0pPz9A-wegeqpyIxYSjR-trCnP5ffIkOE-ThkVXhCC46pjgL9h5eEwOp42-oDce340eHYhO6TSbLl/pub?output=csv"
GENSHIN_EMOJI_RIDDLE_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTVeIY2FLhHODz6nyJ5D8IWBtDRRttfIZNkUKnRmqoTksaHXxZnckUD7ou4s5DKT_CDRZbMBs9tlnd8/pub?output=csv"
CURRENCY_EMOTES = [
    f"<:mysticraft_dev:1267019102200008704>",
    "<:mysticraft:1078363938623860827>",
    "<:mysticraft_helper:1267016346584223836>"
]
WORDS = [
    "creeper", "zombie", "skeleton", "enderman", "spider",
    "diamond", "gold", "iron", "emerald", "coal",
    "netherite", "obsidian", "bedrock", "cobblestone", "dirt",
    "crafting", "mining", "furnace", "anvil", "enchant",
    "potion", "elytra", "shulker", "wither", "dragon",
    "nether", "end", "overworld", "biome", "village",
    "pickaxe", "sword", "axe", "shovel",
    "armor", "helmet", "chestplate", "leggings", "boots",
    "redstone", "piston", "lever", "button", "plate",
    "torch", "lantern", "glowstone", "beacon", "compass",
    "zombified_piglin", "ghast", "blaze", "slime", "magma_cube",
    "trident", "bow", "arrow", "crossbow", "shield",
    "steve", "alex", "herobrine", "warden", "breeze", 
    "phantom", "axolotl", "drowned", "husk", "stray",
    "ravager", "evoker", "pillager", "allay", "sniffer",
    "armadillo", "camel", "piglin", "hoglin", "strider",
    "copper", "lapis", "amethyst", "quartz", "flint",
    "granite", "diorite", "andesite", "sandstone", "terracotta",
    "calcite", "tuff", "mud", "clay", "gravel",
    "barrel", "hopper", "dropper", "dispenser", "scaffolding",
    "campfire", "smoker", "composter", "cauldron", "lectern",
    "spyglass", "brush", "shears", "clock", "saddle",
    "totem", "sponge", "honeycomb", "sculk", "mushrooms",
    "mansion", "monument", "stronghold", "fortress", "dungeon", "mysticraft", "minecraft"
]
MEMORY_GAME_EMOJIS = [ "😄", "😊", "😃", "😉", "😍", "😘", "😚", "😗", "😙", "😜", "😝", "😛", "🤑", "🤓", "😎", "🤗", "🙂", "🤔", "😐", "😑", "😶", "🙄", "😏", "😒", "🤥", "😌", "😔", "😪", "🤤", "😴", "😷", "🤒", "🤕", "🤢", "🤧", "😢", "😭", "😰", "😥", "😓", "😈", "👿", "👹", "👺", "💩", "👻", "💀", "👽", "🤖", "🎃", "🎉", "🌟", "🔥", "❤️", "💙", "💜", "💛", "💚", "🖤", "💖", "💗", "💓", "💕", "💞", "💘", "💝", "💌", "💍", "💎", "🎀", "🌈", "👍", "👎", "👌", "✌", "🤞", "🤟", "🤘", "👏", "🙌", "🤲", "💪", "🙏", "👊", "🤛", "🤜", "💅", "👀", "👁", "👅", "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯", "🦁", "🐷", "🐸", "🐵", "🦄", "🐉", "🐲", "🐍", "🦎", "🐢", "🍕", "🌺", "📚", "⚽", "🎵", "🍔", "🍦", "🎂", "🎁", "🎈", "🎨", "🚀", "⌛", "💡", "🎮", "📷", "📱", "💻", "⭐", "🌙", "🍎", "🍉", "🍇", "🍓", "🥑", "🍩", "🥨", "🥗", "🍿", "🍰", "🚗", "🚕", "🚙", "🚌", "🚎", "🚜", "🚲", "✈", "🚁", "🛳", ]
TTOL_EMOJIS = ["<:mystcraft_owner:1267018399293243523>", "<:mysticraft_admin:1267020293134614620>", "<:mysticraft_helper:1267016346584223836>"]
CROSS_EMOJI = "<:cross:1458355882940170280>"
CIRCLE_EMOJI = "<:circle:1458355853731168307>"

async def setup(bot):
    pass