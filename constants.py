SERVER_IDS = {
    "staff": 1064570075304177734,
    "main": 1136662635039952988,
    "support": 1373869107484688436,
    "tierlist": 1304829305443844096,
    "interview": 1391091143059701810
}

ROLE_IDS = {
    SERVER_IDS["main"]: {
        "base": 1136672562307412079,
        "linked": 1275144456122929152,
        "roles": {
            "owner": 1136672543466598592,
            "manager": 1136672551729381418,
            "senior_admin": 1290543539368759429,
            "admin": 1136672556322128034,
            "developer": 1136672555214852106,
            "senior_mod": 1232589300428832820,
            "mod": 1136672558469615748,
            "helper": 1172845504414097439
        }
    },
    SERVER_IDS["staff"]: {
        "base": 1066298571000909975,
        "roles": {
            "owner": 1064570857537667193,
            "manager": 1064571207627853844,
            "senior_admin": 1290409277638311947,
            "admin": 1090330479179350037,
            "developer": 1064571463409082408,
            "senior_mod": 1232591866281852959,
            "mod": 1066298183879229490,
            "helper": 1172834016412569610
        },
        "tierlist_staff": 1516242972629532712
    },
    SERVER_IDS["support"]: {
        "base": 1373882802084511754,
        "roles": {
            "owner": 1373893342169137202,
            "manager": 1373892851745685524,
            "senior_admin": 1373891660471210024,
            "admin": 1373890838496673852,
            "developer": 1373890109216129155,
            "senior_mod": 1373889160833798274,
            "mod": 1373887662842183801,
            "helper": 1373883332492001341
        }
    },
    SERVER_IDS["tierlist"]: {
        "base": 1305573653332754533,
        "linked": 1459863162223595656,
        "roles": {
            "owner": 1304848576190484553,
            "manager": 1460312013535318077,
            "admin": 1304851740226748556,
            "regulator": 1339144441583370251,
            "staff": 1305573653332754533
        }
    }
}

EMOTES = {
    "owner": "<:mystcraft_owner:1267018399293243523>",
    "executive": "<:mysticraft_executive:1267015078675222548>",
    "manager": "<:mysticraft_manager:1267012427946393641>",
    "senior_admin": "<:mysticraft_sradmin:1294524850542739496>",
    "admin": "<:mysticraft_admin:1267020293134614620>",
    "developer": "<:mysticraft_dev:1267019102200008704>",
    "senior_mod": "<:mysticraft_srmod:1267014449844457564>",
    "mod": "<:mysticraft_mod:1267004112332001303>",
    "helper": "<:mysticraft_helper:1267016346584223836>"
}

CATEGORY_IDS = {
    SERVER_IDS["support"]: {
        "password reset": 1500604708987994342,
        "other questions": 1374959236420730890,
        "billing support": 1374959248806510662,
        "punishment appeals": 1374959224752312362,
        "player reports": 1374959260458287125,
        "bug/glitch reports": 1374959285716647947,
        "staff reports": 1374959273930391592
    },
    SERVER_IDS["tierlist"]: {
        "general support": 1462026697024213024,
        "high testing": 1462026779823833211,
        "tier migration": 1462026806335897725,
    },
    f'{SERVER_IDS["support"]} application': {
        "staff": 1374959644727840899,
        "media": 1374959657310748745,
    },
    f'{SERVER_IDS["tierlist"]} application': {
        "staff": 1462957616534655103,
        "tester": 1462026742486011934
    }
}

CATEGORY_EMOJIS_MAP = {
    "password reset": "🖥️",
    "other questions": "❓",
    "billing support": "💰",
    "punishment appeals": "✍️",
    "player reports": "⚠️",
    "bug/glitch reports": "🐛",
    "staff reports": "👤"
}

TICKET_COOLDOWNS = {
    "normal": 21600,  # 6 hours
    "password_reset": 86400 * 7,  # 7 days
    "appeal": 86400 * 14,  # 14 days
    "high_testing": 86400 * 30,  # 30 days
    "staff_app_tierlist": 86400 * 30,  # 30 days
}

FLAG_CHANNEL_IDS = {
    "owner": {
        SERVER_IDS["support"]: 1374962834210951259,
        SERVER_IDS["tierlist"]: 1452375067538362540,
        "emoji": "⚫️"
    },
    "manager": {
        SERVER_IDS["support"]: 1374962875998670860,
        SERVER_IDS["tierlist"]: 1452375111431753748,
        "emoji": "🟠"
    },
    "mod": {
        SERVER_IDS["support"]: 1374962893451165856,
        SERVER_IDS["tierlist"]: 1452375122823479336,
        "emoji": "🟣"
    }
}

SUPPORT_ROLE_IDS = {
    SERVER_IDS["support"]: 1375131045589946518,
    SERVER_IDS["tierlist"]: 1460537858388398121
}

LOG_CHANNEL_IDS = {
    SERVER_IDS["support"]: 1374962935360782347,
    SERVER_IDS["tierlist"]: 1338567613869199462,
    f'{SERVER_IDS["support"]} application': 1391586125839077447,
    f'{SERVER_IDS["tierlist"]} application': 1516295046259802142
}

COOLDOWN_BYPASS_USER_IDS = [692254240290242601, 840972960793100309, 740750243808673895]
APPEAL_LOG_CHANNEL_ID = 1286031597845614625