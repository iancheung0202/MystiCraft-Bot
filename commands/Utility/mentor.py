import discord

from discord import app_commands
from discord.ext import commands

handbook = """# MystiCraft Staff Handbook

> Any attempt to replicate or distribute this document to non-staff will result in demotion. Direct questions, comments, or concerns to **NinjaMC** on Discord.

You must read this handbook from start to end, and then complete a quiz without referencing the handbook. Passing the quiz is required to receive your in-game rank. The whole process will only take 10-20 minutes.

## 1. Core Values & General Conduct

Failure to abide by any of the staff guidelines and/or server rules may result in demotion, removal from the staff team, and/or removal from the server.

### 1.1 Be Friendly

Friendliness is one of the core values of MystiCraft. Even when players are disrespectful, you must remain polite and professional at all times.

- Follow the **"customer is always right"** principle by listening to their concerns and try to provide satisfactory resolutions.
- Do not start arguments or drama with server members. This damages our server image and leads to dissatisfaction towards the staff team.
- **Cherish every member of the community.** Do not take any action that directly or indirectly causes members to leave.
- Be calm, friendly, and professional. **Do not sink to a player's level.** Remain polite and resolve situations peacefully.
- If a player is being rude, calmly remind them of the rules. Do not match their energy; instead, you should de-escalate.
- Treat all players equally. Do not let personal feelings affect decisions. Base decisions on facts, not personal opinions.

### 1.2 Dealing with Tricky Situations

Staff are permitted to make **frontline judgment calls** to handle situations that may not be explicitly covered by the rules, as long as decisions stay in line with our core values: **friendliness, transparency, and professionalism**.

- **Rule enforcement is for the greater good of the community, and not for the sake of enforcement.** If enforcing a punishment will cause unnecessary backlash or serves no purpose, think carefully before acting.
- Do not interfere with situations unless it is absolutely necessary, especially if you do not have full context.
- When in doubt, **escalate to a higher staff member** immediately rather than risking a mistake.
- All actions must be logged in either <#1155910232204128256> or <#1457327745121128459>.

### 1.3 Be Official & Formal

When handling server matters (answering inquiries, managing tickets, etc.), you are **representing** MystiCraft.

- Use **"please," "sorry,"** and **"thank you"** where appropriate.
- Avoid slang, short forms, or improper punctuation in official settings (tickets, announcements, etc.).
- In casual chat channels, you may speak informally without degrading our server image.

### 1.4 Transparency

When you cannot fulfill a member's request, provide a clear reason why only when appropriate.

- Members feel more understood when given a reason, even if the reason is simple.
- Do not ignore member requests. Acknowledge them and let them know you are working on it.
- If a member needs thorough assistance (e.g., punishment appeal, role application), direct them to the **ticket system** so there is a log for future reference.
- **Transparency has limits:** Never leak information from private staff channels (including punishment reasons and evidence), including screenshots, quotes, summaries, or paraphrasing without explicit prior approval from everyone involved. This is strictly prohibited and results in harsh punishment.
- **Never tell players the exact reason or evidence of their punishment**, as this is also private unless it is explicitly stated publicly in the ban reason. 

### 1.5 Unanswerable Questions

- **Never** immediately redirect players to the owner by saying things like "wait for the owner." This makes members feel helpless.
- If you don't know the answer, say something like: *"This is a tricky question. I'll get back to you right away,"* then find the answer and follow up promptly using formal language.
- In tickets, if a question is outside your scope, **do not reply at all**. Flag it and a higher staff member will handle it when they are online. **Do not say "wait for owner to come" in tickets.**

### 1.6 Work as a Team

- **Teamwork** is essential at MystiCraft. When staff work together, reports are handled faster, players get help sooner, and problems are easier to fix.
- All staff are expected to collaborate. Every voice deserves to be heard if it is constructive.
- **Do not publicly disagree with or argue** against other staff in public chat channels.
- If a conflict cannot be resolved between staff, a final decision will be made by the owners and must not be challenged.
- Do not insist on or harass other staff members over their decisions. If you want to challenge a decision, **consult the owners**.
- All newly-accepted staff must follow the instructions of higher-ranking staff, who are more experienced. However, the hierarchy reflects duration of service, not worth or intelligence. Everyone must demonstrate mutual respect.
- If one staff member is busy or unresponsive, another can step in and help.

### 1.7 Professionalism & Conduct

- Anything a player should not be doing, you should not be doing either (even if you have the ability to). You are a **role model** for the server at all times.
- Do not go AFK in-game without being in vanish, as it appears as though you are ignoring players.
- Do not get roles you do not deserve or beg for promotions. Asking for promotion will delay it.
- You may not promote or demote any staff members, even if you have the role permissions to do so.
- You may not assign responsibilities to fellow staff unless explicitly asked by the owners.

## 2. Staff Hierarchy & Roles

### Rank Overview (Lowest to Highest)

- **Helper:** Entry-level staff. Answers questions, handles minor chat issues, issues warnings and temp mutes. Reports to Moderators.
- **Moderator:** Handles rule-breaking, in-game issues, cheating, and temp bans. Assists Helpers. Reports to Administrators.
- **Senior Moderator:** Handles complex issues, uses CoreProtect, and manages appeals. Reports to Administrators.
- **Administrator:** Takes on specialist roles (Player Disputes, Reports, etc.). Mentors staff. Reports to Managers.
- **Senior Administrator:** Oversees Admins, manages major projects, handles escalated issues. Reports to Managers.
- **Manager:** Engages and motivates the community through events, updates, and media. Oversees the entire staff team. Reports to Owners.

> **Note:** Executives and Developers are not included in this promotion/demotion structure.

### Role Responsibilities in Detail

**Helper**
- Provide a polite and welcoming approach to new players and assist them.
- Handle minor chat moderation (spamming, hate speech, racism, not listening to staff) and issue warnings or temp mutes.
- If a situation requires a ban or is outside your permissions, report it to a Moderator with valid evidence.

**Moderator**
- Actively look for cheaters (hacking, etc.) and issue temp bans when necessary.
- Handle chat offenses, cheating, inappropriate structures/skins.
- Support and guide Helpers.

**Senior Moderator**
- Handle more complex moderation issues like player appeals and conflicts in tickets.
- Use CoreProtect for investigation and rollbacks.

**Administrator**
- Take on a specialist role (e.g., Player Disputes, Reports).
- Answer questions from lower staff that they cannot resolve themselves.
- Cannot play on the server unless using a trusted or alt account.

**Senior Administrator**
- Oversee overall management and smooth coordination across all staff.
- Lead larger responsibilities: major projects, Admin coordination, complex issues.
- Cannot play on the server unless using a trusted or alt account.

### Mentor Role

- Mentors are typically Admin+ staff who have been on the server for a significant time. They help train new staff members.
- **Always contact your Mentor first** (through your journal or DMs) for questions and guidance.
- **Do not contact the Managers directly** for simple questions, as the Manager handles large-scale tasks and will refer you to your Mentor anyway.

## 3. Activity Requirements

### Recommended Weekly Hours (Discord)

- **Helper:** 6-8 hours/week
- **Moderator:** 10-12 hours/week
- **Senior Moderator:** 13-14 hours/week
- **Administrator:** 15-16 hours/week
- **Senior Administrator:** 17-19 hours/week
- **LOA:** 0 hours/week

Staff are expected to be active **in-game and on Discord daily** to stay up to date, handle tickets, and monitor the community.

### Minimum Logs & Tickets (Per Week)

- **Helper:** Warns 3, Mutes 5, Tickets 5
- **Moderator:** Mutes 5, Bans 2, Tickets 5
- **Senior Moderator:** Mutes 6, Bans 2, Tickets 10
- **Administrator:** Mutes 5, Bans 3, Tickets 15
- **Senior Administrator:** Mutes 10, Bans 3, Tickets 20

These are **bare minimums**. Meeting only the minimum may result in a longer promotion timeline. Exceeding these expectations improves your chances of a faster promotion.

### Minimum Punishment (Per 3 Days)

To prevent log farming, as a general guideline, you should have a certain number of logs/tickets helped every 3 days. These are not hard thresholds, but if it starts becoming a problem, you may be demoted.

- **Helper:** Logs 3, Tickets 2
- **Moderator:** Logs 3, Tickets 2
- **Senior Moderator:** Logs 4, Tickets 4
- **Administrator:** Logs 4, Tickets 6
- **Senior Administrator:** Logs 6, Tickets 8

### Leave of Absence (LOA)

- Always submit a LOA using the **absence template in your notebook** at least **2-3 days before** your expected leave.
- For emergencies or personal matters, DM **Ninja** directly, or ping him in your notebook.
- Staff may take up to **7 days off per month** for inactivity.
- If you require extra time, DM a Manager with the time and reason. Excessive absence month after month will result in a warning and potential demotion.

## 4. Player Moderation

Handling rule violations is one of the most common tasks for staff. Approach every situation calmly and fairly.

- **All punishments and durations are listed in this handbook.** Read and remember them thoroughly.
- Good judgment is essential. Some cases are nuanced; ensure punishments are correct and proportional.
- If a situation is confusing, too serious, or outside your permissions, ask for help in <#1090677449039302718> or contact your mentor.

### Before Any Punishment

Always run `/history (IGN)` before applying any command to check a player's punishment history.

The timeframe for all chat punishments has been changed to **5 minutes**. You also **cannot** punish using the history of Discord in-game chats.

### Receiving Reports

- Acknowledge reports as soon as possible and let the player know you have seen it.
- Be polite and professional. Ask for additional information (screenshots, video, details) if needed.

### Reviewing Evidence

- **Chat offenses (spamming, toxicity):** Check chat logs.
- **Cheating/hacking:** Valid **video evidence** (not screenshots) is required.

### Taking Action

- Use the guidelines to decide the correct punishment. Avoid personal bias in all decisions.
- Keep punishments fair, consistent, and proportional to the offense.
- If you do not have the correct permissions to punish a player, refer to an online staff member who does, or post in <#1090677449039302718>.

### Reporting a Player (as Staff)

Follow this format when posting in <#1090677449039302718>:
```
IGN:
Punishment:
Reason:
Duration:
Offense:
Evidence:
```

### Using Permissions Correctly

- Never kick or ban players without proper evidence.
- Always gather video or proof and submit it to higher staff before taking action when required.
- Misusing permissions harms the player experience and reflects poorly on the entire staff team.

### Raiding Player Bases
Staff members **cannot raid player bases** under any circumstances, as it gives an unfair advantage, destroys community trust, and damages the reputation of the entire staff team. Staff members who raid will be **removed from the team**.
- If you need to enter a base for legitimate moderation purposes, use **vanish mode**.
- **Do not teleport to players when not in vanish** as this risks interfering with gameplay.
- **Teleport trapping is strictly forbidden.** Never use TP traps to harm or trick players. This destroys community trust.

### Player Confidentiality

When you reach Moderator, you gain access to players' builds, homes, and farms. All information about a player's base or farms is **strictly private**. Violating this may result in instant demotion.

### In-Game Punishment Table

- **Word/Character Spam:** Warning → 30m Mute → 1h Mute → 1d Mute → 7d Mute → Perm Mute
- **Extreme Profanity:** Warning → 1h Mute → 6h Mute → 1d Mute → Perm Mute
- **Staff Disrespect:** Warning → 6h Mute → 3d Mute → 7d Ban → Perm Mute
- **Harassment:** Warning → 1h Mute → 1d Mute → 7d Mute → Perm Mute
- **Racism / Homophobia / Transphobia:** 1d Mute → 3d Mute → Perm Mute
- **Advertisements:** 1d Mute → 3d Mute → Perm Mute
- **Death Threats / Suicidal Encouragement:** Warning + 6h Mute → 7d Ban
- **Hacked Clients / Unapproved Mods:** 7d Ban → 14d Ban → 30d Ban → Perm Ban (Blacklist)
- **Xray Mod / Texture Pack:** 7d Ban → 14d Ban → 30d Ban → Perm Ban (Blacklist)
- **Autoclicker / Macro / F11 Glitch Abuse:** 7d Ban → 14d Ban → 30d Ban → Perm Ban (Blacklist)
- **Automated Work (Scripts):** 14d Ban → 30d Ban → Perm Ban
- **Ban Evasion:** Perm IP Ban
- **Mute Evasion (Alt Account):** Ban for duration of mute → Perm IP Ban
- **Leaking Personal Information:** Perm IP Ban
- **DDoS / Dox / SWAT Threats:** Perm IP Ban
- **Threats (Dox & DDoS):** Perm Mute
- **Light Bug Abuse:** 3d Ban → 7d Ban → 14d Ban → Perm
- **Medium Bug Abuse:** 7d Ban → 14d Ban → 30d Ban → Perm
- **Heavy Bug Abuse:** Perm IP Ban (Blacklist)
- **IRL Trading:** 1d Ban → 3d Ban → Perm Ban
- **Staff Impersonation:** 30d Ban → Perm Ban
- **Inappropriate Name:** Perm Ban
- **Harming the Server:** Perm IP Ban (Blacklist)

## 5. Discord Moderation

### Discord Punishments (Least to Most Severe)

1. Verbal Warning
2. Warn
3. Timeout / Temp Mute
4. Kick
5. Ban

As a general rule: always resolve issues using the **least severe action** that still prevents the behavior from recurring.

There is **no warning threshold required for a ban** at MystiCraft. If a ban is warranted, it can be enforced immediately.

### Support Tickets

- Keep a close eye on support ticket channels when online. Assist players efficiently.
- If another staff member is **already typing** in a ticket, stop and let them handle it. Do not double-post.
- If another staff member has already responded, **do not touch that ticket** without permission or unless it has been **inactive for 24+ hours**.

### Required In-Game Punishment Log

Every staff action in-game must be logged in <#1155910232204128256> using this exact format:

```
IGN:
Punishment:
Reason:
Duration:
Offense:
Evidence:
```

Keeping clear and accurate logs is critical for dealing with appeals later.

### Required Discord Punishment Log

Every staff action on Discord must be logged in <#1457327745121128459> using this exact format:

```
Discord ID: 
Punishment: 
Reason: 
Offense: 
Duration: 
Evidence:
```

## 6. Appeals

### Handling an Appeal (Senior Moderators+)

If a player appeals outside of Appeal tickets (which are only visible to Senior Moderators or above), please **redirect them** to create an Appeal ticket. Do not attempt to process appeals outside of Appeal tickets.

1. Check the player's punishment history and the staff server logs to understand why they were punished.
2. If the situation is unclear, ask the staff member who issued the punishment for more details.
3. Gather all necessary information **before** making a decision. Keep your response **formal**, whether you accept or deny. Provide **clear reasoning** for your decision without leaking private information so the player understands how they can improve.
4. Log the result using the buttons in the ticket (which will be posted in <#1286031597845614625>).

**Bias**

You **cannot** handle an appeal for someone you are personally involved with (friends or enemies). Violation results in a demotion or strike. This ensures fairness for everyone.

## 7. Staff Permissions & Commands

### Helper
- `/tempmute (IGN) (Template)` - e.g., `/tempmute Test Slurs`
- `/kick (IGN) (Template)`
- `/fly`
- `/lastuuid (IGN)`
- `/checkmute (IGN)`
- `/warnings (IGN)`
- `/warn (IGN) (Template)`
- `/history (IGN)` - checks full punishment history
- `/staffchat`

### Moderator *(all Helper commands, plus)*
- `/ipban (IGN) (Template)` - e.g., `/ipban Test Hacking`
- `/tempban (IGN) (Template)` - e.g., `/tempban Test Hacking`
- `/mute (IGN) (Template)` - e.g., `/mute Test Racism`
- `/kick (IGN) (Reason)`
- `/vulcan freeze (IGN)`
- `/unmute (IGN)`
- `/unban (IGN)`
- `/svcmute (IGN)`
- `/checkban (IGN)`
- `/tp (IGN)` - teleport yourself to a player
- `/vanish`
- `/realname (IGN)`
- `/dupeip` / `/alts`

### Senior Moderator *(all Moderator commands, plus)*
- `/ban (IGN) (Template)` - e.g., `/ban Test AutoWork`
- `/mute (IGN) (Template)` - e.g., `/mute Test NonEnglish`
- `/ipban (IGN) (Template)` - e.g., `/ipban Test BanEvading`
- `/dupeip (IGN)`
- `/co lookup` - Investigate what happened in an area or by a user
- `/co rollback` - Undo a player's actions or changes in an area.
- `/co inspect` - Toggle inspection mode to click blocks and see their history
- `/co restore` - Restore block data (rarely used in practice).
- `/socialspy`

As a Senior Moderator, you gain access to **CoreProtect**, a plugin that logs all player actions on the server. It allows staff to investigate incidents and roll back damage or unwanted changes.

**Modifiers (`#2`, `#3`, etc.) - Format: `modifier:value`**

- `u:(username)`: Specify the user to look up or undo
- `r:(number)`: Set the radius to search
- `t:(time)`: Set the time range (e.g., `t:1h`, `t:2d`)
- `a:(action)`: Filter by action type
- `i:(block)`: Include only specific blocks/entities
- `e:(block)`: Exclude specific blocks/entities

**Action Types (used with `a:`):**
- `+block` / `-block` - Block placed or broken
- `+inventory` / `-inventory`
- `+container` / `-container`
- `+item` / `-item`
- `+session` / `-session`
- `sign`
- `username`
- `kill`
- `death`
- `click`
- `command`
- `chat`

**CoreProtect Command Format:** `/co [action] [modifiers]`

> `/co lookup u:PlayerName r:10 t:1h a:+block` - This looks up all blocks placed by "PlayerName" within a 10-block radius in the last 1 hour.

### Administrator *(all Senior Moderator commands, plus)*
- All commands +
- `/pw admin`
- `/ipreport`
- `/adminchat`

### Senior Administrator *(all Administrator commands, plus)*
- `/staffhistory`
- `/lockdown`

### Manager *(all Senior Administrator commands, plus)*
- LuckPerms access

## 8. Promotions, Demotions & Resignations

### Demotions

Breaking any rules or guidelines puts you at risk for demotion. You will be notified by the Managers or the Owners, along with the reason for demotion.

**Strike Policy:**
- Missing a week → Verbal warning (noted in personal notebook)
- 1 verbal warning → 1 strike
- 2 strikes → Demotion or removal
- Strikes **expire after 1 month**

### Promotions

Promotions are based on overall performance. Things that improve your chances:
- Consistent activity (meeting or exceeding minimums)
- Proper communication with players and staff
- Teamwork, dedication, and flexibility

**Asking for a promotion will delay it.** Do not beg.

### Staff Milestones (Punishment Count Rewards)

- **Milestone 1:** 100 punishments
  - Reward: 300 Coins / 50 Relics & 2 Mythic Keys / 1x Sapphire Key
- **Milestone 2:** 200 punishments
  - Reward: 500 Coins / 75 Relics & 3 Mythic Keys / 1x Sapphire Key
- **Milestone 3:** 300 punishments
  - Reward: VIP+ / Elite / Survival Rank & 500 Coins / 75 Relics
- **Milestone 4:** 400 punishments
  - Reward: 1000 Coins / 150 Relics, 3 Mythic Keys / 1x Sapphire Key, 3 Ultimate Keys / 2x Sapphire Key
- **Milestone 5:** 500 punishments
  - Reward: MVP / Immortal / Survival+ Rank
- **Milestone 6:** 600 punishments
  - Reward: 1000 Coins / 150 Relics, 5 Mythic Keys / 2x Sapphire Keys, 5 Ultimate Keys / 3x Sapphire Keys, 1x Temporary Crate Key
- **Milestone 7:** 700 punishments
  - Reward: MVP+ / Supreme / Essence Rank

Contact the owner once you've reached a milestone to claim your reward.

## 9. Notebooks & Mentors

### What Are Notebooks?

Notebooks are a tool added to the staffing server to enhance team performance. Each staff member has a notebook used for:
- Mentor lessons
- Staff reporting
- Correcting mistakes
- Weekly performance and progress tracking

### Mentors

- Mentors are typically Admin+ staff with significant server experience.
- They explain every important detail of your position and guide you through training.
- Contact your Mentor first through your journal or DMs when you have questions.
"""

QUIZ_CHOICE_LABELS = ["A", "B", "C", "D"]
QUIZ_LOCK_CHANNEL_ID = 1342522451229278320

quiz_questions = [
	{
		"question": "According to the Core Values, how should you respond if a player is being disrespectful or rude to you?",
		"options": [
			"Immediately ban them for staff disrespect without a warning.",
			"Remain polite, stay professional, and attempt to de-escalate the situation.",
			"Match their energy so they know you aren't a pushover.",
			"Ignore them completely and do not acknowledge their presence.",
		],
		"correct": 1,
	},
	{
		"question": "What is the policy regarding sharing evidence or reasons for a punishment with players?",
		"options": [
			"You can share evidence only if the player asks nicely in public chat.",
			"You should show the player all screenshots and video evidence so they can learn.",
			"Never tell players the exact reason or evidence unless it is stated publicly in the ban reason.",
			"You must send the evidence to the player's friends if they ask.",
		],
		"correct": 2,
	},
	{
		"question": "If a player asks you a tricky question and you don't know the answer, what is the best response?",
		"options": [
			"Ignore the question until you happen to see the owner online.",
			"Acknowledge it is a tricky question, say you will find out, and follow up promptly.",
			"Make up a plausible answer so you look knowledgeable.",
			"Tell them to wait for the owner to get back to them.",
		],
		"correct": 1,
	},
	{
		"question": "Who is the first person a new staff member should contact for questions or guidance?",
		"options": [
			"The Owner (NinjaMC)",
			"Their assigned Mentor (Admin+)",
			"A Manager",
			"Any random player who has been on the server a long time.",
		],
		"correct": 1,
	},
	{
		"question": "What is the primary purpose of the Notebook tool on the staffing server?",
		"options": [
			"To store your passwords safely.",
			"To write daily summaries about the server.",
			"To keep a list of players you personally dislike.",
			"For mentor lessons, tracking performance, and correcting mistakes.",
		],
		"correct": 3,
	},
	{
		"question": "Which command should you ALWAYS run before applying any punishment to a player?",
		"options": ["/warnings (IGN)", "/co lookup", "/history (IGN)", "/dupeip (IGN)"],
		"correct": 2,
	},
	{
		"question": "What type of evidence is strictly required to punish a player for hacking or cheating?",
		"options": [
			"Screenshots of the player moving fast.",
			"A written statement from two other players.",
			"Valid video evidence.",
			"Evidence is only required for permanent bans, not temporary ones.",
		],
		"correct": 2,
	},
	{
		"question": "If you are a Moderator and see another staff member already typing in a Discord support ticket, what should you do?",
		"options": [
			"Type faster so you can get the ticket log credit.",
			"Stop and let the other staff member handle it; do not double-post.",
			"Wait 5 minutes and then give a different answer to be helpful.",
			"Close the ticket immediately to clear the queue.",
		],
		"correct": 1,
	},
	{
		"question": "What is the Strike Policy for staff members who miss a week of activity?",
		"options": [
			"A permanent strike that never disappears from your notebook.",
			"You are banned from the server for 7 days.",
			"Immediate demotion to Helper.",
			"A verbal warning for the first week, followed by strikes that expire after 1 month.",
		],
		"correct": 3,
	},
	{
		"question": "Can you handle an appeal for a player who is a personal friend or enemy?",
		"options": [
			"No, personal involvement results in a strike or demotion to ensure fairness.",
			"Yes, but only if an Admin watches you do it.",
			"Yes, because you know them best and can be fair.",
			"Only if they are a friend; you cannot handle appeals for enemies.",
		],
		"correct": 0,
	},
    {
		"question": "A player asks you why their friend was banned. You know the reason from internal staff logs. What do you do?",
		"options": [
			"Tell them the reason privately via DM to be transparent.",
			"Give them a vague summary so they feel informed.",
			"Decline to share. Private punishment details must never be disclosed unless stated publicly in the ban reason.",
			"Share it only if they promise not to tell anyone.",
		],
		"correct": 2,
	},
    {
		"question": "You are going on vacation for 10 days next month. What is the correct way to handle this?",
		"options": [
			"Just go. Staff will notice you're gone and cover for you.",
			"Submit a LOA using the absence template at least 2-3 days before, and DM a Manager since it exceeds the 7-day monthly limit.",
			"Post in staff chat that you'll be away.",
			"Set your Discord bio to 'Going on a Vacation'",
		],
		"correct": 1,
	},
    {
		"question": "You discover a player has ban evaded using an alt account. What is the correct punishment for the alt account?",
		"options": [
			"Ban for the same duration as the original ban.",
			"A verbal warning since it is a new account.",
			"Perm IP Ban",
			"7d Ban",
		],
		"correct": 2,
	},
	{
		"question": "Describe the best approach to communicating with players when handling issues.",
		"options": [
			"Be calm, friendly, and professional, using formal language and de-escalation techniques.",
			"Match the player's energy to show authority and use slang to seem relatable.",
			"Use short forms and skip punctuation to resolve tickets as quickly as possible.",
			"Redirect all rude players to the owner immediately to avoid personal stress.",
		],
		"correct": 0,
	},
	{
		"question": "If a player is spamming in chat, how should you handle the situation according to server rules?",
		"options": [
			"Warning -> 30m Mute -> 1h Mute -> 1d Mute -> 7d Mute -> Perm Mute",
			"Warning -> Kick -> 1h Mute -> 30d Ban",
			"1h Mute -> 1d Mute -> 7d Mute -> Perm Ban",
			"Warning -> Verbal Warning -> Kick",
		],
		"correct": 0,
	},
    {
		"question": "As a Moderator, you teleport to a player to check on a report without using vanish. Why is this a problem?",
		"options": [
			"It drains your in-game stamina.",
			"It is only allowed for Senior Moderators and above.",
			"Teleporting without vanish risks interfering with gameplay and is against staff conduct rules.",
			"There is no problem. Moderators are allowed to teleport freely.",
		],
		"correct": 2,
	},
    {
		"question": "A senior staff member you admire makes a decision in a ticket that you believe is wrong. What is the correct way to handle this?",
		"options": [
			"Publicly correct them in the ticket so the player sees the right answer.",
			"Say nothing. Seniors are always right.",
			"Challenge them directly in front of other staff members.",
			"Raise your concern privately, and if unresolved, consult the owners. Never challenge it publicly.",
		],
		"correct": 3,
	},
    {
        "question": "You are handling a ticket and a player reports an issue that is out of your scope of duties. What should you do?",
        "options": [
            "Answer with your best guess so the player doesn't have to wait.",
            "Tell them to wait for the owner to come online.",
            "Do not reply to the ticket at all. Flag it and let a higher staff member handle it when available.",
            "Close the ticket and ask them to reopen it later.",
        ],
        "correct": 2,
    },
    {
		"question": "You log a punishment but forget to include the evidence field in the required log format. Why does this matter?",
		"options": [
			"It doesn't matter as long as the IGN and punishment type are included.",
			"Incomplete logs make it impossible to fairly process appeals later, which is a core staff responsibility.",
			"It only matters for permanent bans, not temp bans.",
			"The system will automatically fill in missing fields.",
		],
		"correct": 1,
	},
	{
		"question": "If you receive a player report but don't have enough evidence to take action, what do you do next?",
		"options": [
			"Guess based on the player's reputation and punish them anyway.",
			"Ask the player for video evidence and escalate to a higher staff member or the reports channel if needed.",
			"Ask the player for screenshot evidence and escalate to a higher staff member or the reports channel if needed.",
			"Close the case immediately since you can't prove it right now.",
		],
		"correct": 1,
	},
	{
		"question": "How should you handle a frustrated or rude player while staying professional?",
		"options": [
			"Calmly remind them of the rules, stay polite, and de-escalate the situation.",
			"Tell them you are going to get the owner to ban them.",
			"Give them a taste of their own medicine so they respect you.",
			"Mute them immediately without speaking to them.",
		],
		"correct": 0,
	},
	{
		"question": "What steps would you take if a player challenges your authority as a staff member?",
		"options": [
			"Argue with them in public chat until they back down.",
			"Instantly permanent ban them for questioning you.",
			"Ignore all their future messages and reports.",
			"Remain professional, follow the punishment guidelines for staff disrespect if applicable, and avoid ego-based decisions.",
		],
		"correct": 3,
	},
	{
		"question": "What are the staff raiding rules at MystiCraft, and why are they important?",
		"options": [
			"Raiding is strictly forbidden; violators will be removed from the team because it destroys community trust.",
			"Staff can raid as long as they are not in vanish.",
			"Staff are allowed to raid if they give the items back later.",
			"Staff can only raid if the player has been offline for 30 days.",
		],
		"correct": 0,
	},
	{
		"question": "What is the recommended weekly Discord activity hour requirement for a Helper?",
		"options": ["6-8 hours", "10-12 hours", "15-16 hours", "20+ hours"],
		"correct": 0,
	},
	{
		"question": "What are the bare minimum weekly ticket requirements for a Helper?",
		"options": ["5 Tickets", "10 Tickets", "15 Tickets", "20 Tickets"],
		"correct": 0,
	},
	{
		"question": "What is log farming, and how does the Handbook suggest preventing it?",
		"options": [
			"It is when your account is stolen by other players; you enable 2FA on your account.",
			"It is padding numbers with unnecessary logs; it is monitored via a Minimum Punishment per 3 days guideline.",
			"It is a way to get rewards, and staff are encouraged to do it.",
			"It is when you help too many people, and it is prevented by limiting tickets to 1 per day.",
		],
		"correct": 1,
	},
	{
		"question": "How many days of Leave of Absence (LOA) is a staff member allowed per month for inactivity?",
		"options": ["Unlimited, as long as you write it in your notebook", "14 days", "3 days", "7 days"],
		"correct": 3,
	},
    {
		"question": "You are a Helper and witness a player clearly hacking in-game. You do not have ban permissions. What should you do?",
		"options": [
			"Record video evidence, then report it in the reports channel.",
			"Kick them repeatedly until a Moderator comes online.",
			"Warn them in chat and tell them you'll ban them next time.",
			"Do nothing since it's not your responsibility as a Helper.",
		],
		"correct": 0,
	},
    {
		"question": "A player opens a General Support ticket appealing for their punishment. You are a Helper. What should you do?",
		"options": [
			"Review their history, make a decision, and close the ticket.",
			"Tell them 'wait for the owner' to comet.",
			"Ping a higher staff member to handle, as appeals are outside Helper scope.",
			"Redirect them to creating an Appeal ticket.",
		],
		"correct": 3,
	},
	{
		"question": "Which of the following is a Perm IP Ban (Blacklist) offense?",
		"options": ["Inappropriate Name", "Word Spam", "Staff Disrespect", "Heavy Bug Abuse"],
		"correct": 3,
	},
	{
		"question": "What is the specific timeframe for chat punishments (checking back into history)?",
		"options": ["24 hours", "1 hour", "1 minute", "5 minutes"],
		"correct": 3,
	},
	{
		"question": "What happens to staff strikes after 1 month?",
		"options": ["They are sent to the player community to vote on.", "They become permanent marks.", "They double in severity.", "They expire."],
		"correct": 3,
	},
]


def split_long_text(text: str, max_length: int = 3900) -> list[str]:
	if len(text) <= max_length:
		return [text]

	chunks = []
	current = ""
	paragraphs = text.split("\n\n")

	for paragraph in paragraphs:
		candidate = paragraph if not current else f"{current}\n\n{paragraph}"
		if len(candidate) <= max_length:
			current = candidate
			continue

		if current:
			chunks.append(current)
			current = ""

		if len(paragraph) <= max_length:
			current = paragraph
			continue

		# Fallback split by lines for very large paragraphs.
		line_buffer = ""
		for line in paragraph.splitlines():
			line_candidate = line if not line_buffer else f"{line_buffer}\n{line}"
			if len(line_candidate) <= max_length:
				line_buffer = line_candidate
			else:
				if line_buffer:
					chunks.append(line_buffer)
				line_buffer = line
		if line_buffer:
			chunks.append(line_buffer)

	if current:
		chunks.append(current)

	return chunks


def split_with_section_header(section_header: str, body_lines: list[str], max_length: int = 3900) -> list[str]:
	body = "\n".join(body_lines).strip()
	if not body:
		return [section_header]

	prefix = f"{section_header}\n\n"
	allowed_body_len = max(500, max_length - len(prefix))
	body_chunks = split_long_text(body, allowed_body_len)
	return [f"{prefix}{chunk}" for chunk in body_chunks]


def build_handbook_pages(text: str) -> list[str]:
	lines = text.strip().splitlines()
	pages = []
	i = 0

	intro_lines = []
	while i < len(lines) and not lines[i].startswith("## "):
		intro_lines.append(lines[i])
		i += 1
	intro_text = "\n".join(intro_lines).strip()
	if intro_text:
		pages.extend(split_long_text(intro_text))

	while i < len(lines):
		if not lines[i].startswith("## "):
			i += 1
			continue

		section_header = lines[i]
		i += 1
		section_intro_lines = []
		subsections = []
		current_subsection = None

		while i < len(lines) and not lines[i].startswith("## "):
			line = lines[i]
			if line.startswith("### "):
				if current_subsection is not None:
					subsections.append(current_subsection)
				current_subsection = [line]
			else:
				if current_subsection is None:
					section_intro_lines.append(line)
				else:
					current_subsection.append(line)
			i += 1

		if current_subsection is not None:
			subsections.append(current_subsection)

		if any(line.strip() for line in section_intro_lines):
			pages.extend(split_with_section_header(section_header, section_intro_lines))

		for subsection_lines in subsections:
			pages.extend(split_with_section_header(section_header, subsection_lines))

	return pages


def build_handbook_section_pages(text: str, max_length: int = 3900) -> list[str]:
    lines = text.strip().splitlines()
    pages = []
    i = 0

    intro_lines = []
    while i < len(lines) and not lines[i].startswith("## "):
        intro_lines.append(lines[i])
        i += 1
    intro_text = "\n".join(intro_lines).strip()
    if intro_text:
        pages.extend(split_long_text(intro_text, max_length))

    while i < len(lines):
        if not lines[i].startswith("## "):
            i += 1
            continue

        # Split the ## section into chunks: one per ### subsection
        section_header_line = lines[i]
        i += 1

        # Collect section-level intro (before first ###)
        section_intro_lines = [section_header_line]
        while i < len(lines) and not lines[i].startswith("## ") and not lines[i].startswith("### "):
            section_intro_lines.append(lines[i])
            i += 1

        section_intro_text = "\n".join(section_intro_lines).strip()
        if section_intro_text:
            pages.extend(split_long_text(section_intro_text, max_length))

        # Each ### subsection becomes its own page (or pages if too long)
        while i < len(lines) and not lines[i].startswith("## "):
            if not lines[i].startswith("### "):
                i += 1
                continue

            subsection_lines = [lines[i]]
            i += 1
            while i < len(lines) and not lines[i].startswith("## ") and not lines[i].startswith("### "):
                subsection_lines.append(lines[i])
                i += 1

            subsection_text = "\n".join(subsection_lines).strip()
            if subsection_text:
                pages.extend(split_long_text(subsection_text, max_length))

    return pages


HANDBOOK_PAGES = build_handbook_pages(handbook)
HANDBOOK_SECTION_PAGES = build_handbook_section_pages(handbook)


class MentorNextView(discord.ui.View):
	def __init__(self, cog: "Mentor", user_id: int, page_index: int):
		super().__init__(timeout=3600)
		self.cog = cog
		self.user_id = user_id
		self.page_index = page_index
		self.previous_page.disabled = page_index == 0
		if page_index >= len(HANDBOOK_PAGES) - 1:
			self.next_page.label = "Start Quiz"

	@discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
	async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.user_id:
			return await interaction.response.send_message(
				"Only the person who started this mentor flow can continue it.",
				ephemeral=True,
			)

		previous_index = self.page_index - 1
		if previous_index < 0:
			return await interaction.response.defer()

		previous_embed = self.cog.build_page_embed(HANDBOOK_PAGES[previous_index], previous_index)
		previous_view = MentorNextView(self.cog, self.user_id, previous_index)
		await interaction.response.edit_message(embed=previous_embed, view=previous_view)

	@discord.ui.button(label="Next", style=discord.ButtonStyle.blurple)
	async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.user_id:
			return await interaction.response.send_message(
				"Only the person who started this mentor flow can continue it.",
				ephemeral=True,
			)

		next_index = self.page_index + 1
		if next_index < len(HANDBOOK_PAGES):
			next_embed = self.cog.build_page_embed(HANDBOOK_PAGES[next_index], next_index)
			next_view = MentorNextView(self.cog, self.user_id, next_index)
			await interaction.response.edit_message(embed=next_embed, view=next_view)
			return

		quiz_intro_embed = self.cog.build_quiz_intro_embed()
		await interaction.response.edit_message(embed=quiz_intro_embed, view=None)

		await self.cog.start_quiz(channel=interaction.channel, user=interaction.user)


class MentorQuizOptionButton(discord.ui.Button):
	def __init__(self, option_index: int):
		super().__init__(
			label=QUIZ_CHOICE_LABELS[option_index],
			style=discord.ButtonStyle.blurple,
			custom_id=f"mentor_quiz_option_{option_index}",
		)
		self.option_index = option_index

	async def callback(self, interaction: discord.Interaction):
		view = self.view
		if isinstance(view, MentorQuizView):
			await view.process_answer(interaction, self.option_index)


class MentorQuizView(discord.ui.View):
	def __init__(self, cog: "Mentor", user_id: int, question_index: int, answers: list[int]):
		super().__init__(timeout=1800)
		self.cog = cog
		self.user_id = user_id
		self.question_index = question_index
		self.answers = answers
		self.completed = False
		self.message: discord.Message | None = None

		for option_index in range(4):
			self.add_item(MentorQuizOptionButton(option_index))

	async def interaction_check(self, interaction: discord.Interaction) -> bool:
		if interaction.user.id != self.user_id:
			await interaction.response.send_message(
				"Only the person taking this quiz can answer these questions.",
				ephemeral=True,
			)
			return False
		return True

	async def on_timeout(self) -> None:
		if self.message is None or self.completed:
			return

		for child in self.children:
			if isinstance(child, discord.ui.Button):
				child.disabled = True

		timeout_embed = discord.Embed(
			title="Mentor Quiz Timed Out",
			description="No response was received for 30 minutes. Please run `/mentor` again when you are ready.",
			color=discord.Color.red(),
		)
		await self.message.edit(embed=timeout_embed, view=self)
		await self.cog.set_quiz_channel_readable(self.user_id, True)

	async def process_answer(self, interaction: discord.Interaction, selected_option: int):
		next_answers = self.answers + [selected_option]
		next_question_index = self.question_index + 1

		if next_question_index < len(quiz_questions):
			next_embed = self.cog.build_quiz_question_embed(next_question_index)
			next_view = MentorQuizView(self.cog, self.user_id, next_question_index, next_answers)
			await interaction.response.edit_message(embed=next_embed, view=next_view)
			return

		result_embed, wrong_embeds = self.cog.build_quiz_result_embeds(next_answers)
		self.completed = True
		self.stop()
		await interaction.response.edit_message(embed=result_embed, view=None)
		await self.cog.set_quiz_channel_readable(self.user_id, True)
		for wrong_embed in wrong_embeds:
			await interaction.followup.send(content=interaction.user.mention, embed=wrong_embed)


class Mentor(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	async def set_quiz_channel_readable(self, user_id: int, readable: bool) -> None:
		channel = self.bot.get_channel(QUIZ_LOCK_CHANNEL_ID)
		if not isinstance(channel, discord.abc.GuildChannel):
			return

		member = channel.guild.get_member(user_id)
		if member is None:
			return

		if readable:
			await channel.set_permissions(
				member,
				overwrite=None,
				reason="Mentor quiz completed or timed out - restore channel visibility",
			)
			return

		await channel.set_permissions(
			member,
			read_messages=False,
			reason="Mentor quiz started - temporarily hide quiz channel",
		)

	def build_page_embed(self, content: str, page_index: int) -> discord.Embed:
		embed = discord.Embed(description=content, color=discord.Color.blurple())
		embed.set_footer(text=f"Handbook Page {page_index + 1}/{len(HANDBOOK_PAGES)}")
		return embed

	def build_quiz_intro_embed(self) -> discord.Embed:
		return discord.Embed(
			title="Mentor Quiz Started",
			description=(
				"You have reached the end of the handbook. The quiz starts now. "
				"Please answer each question by clicking one of the buttons on the quiz messages. \n\n"
				"We have assumed you have thoroughly read through the handbook, which means you cannot go back and re-read. "
				"If you don't know the answer to a question, give your best educated guess. \n\n"
				"After completing the quiz, a higher staff member will review your answers and determine if you have passed or if you need to retake it. Good luck!"
			),
			color=discord.Color.green(),
		)

	def build_quiz_question_embed(self, question_index: int) -> discord.Embed:
		question_data = quiz_questions[question_index]
		option_lines = [
			f"**{QUIZ_CHOICE_LABELS[index]}.** {option}"
			for index, option in enumerate(question_data["options"])
		]
		embed = discord.Embed(
			title=f"Mentor Quiz Question {question_index + 1}/{len(quiz_questions)}",
			description=f"{question_data['question']}\n\n" + "\n".join(option_lines),
			color=discord.Color.orange(),
		)
		embed.set_footer(text="Select one option below.")
		return embed

	def build_quiz_result_embeds(self, answers: list[int]) -> tuple[discord.Embed, list[discord.Embed]]:
		total_questions = len(quiz_questions)
		correct_count = sum(
			1
			for index, question_data in enumerate(quiz_questions)
			if answers[index] == question_data["correct"]
		)

		result_embed = discord.Embed(
			title="Mentor Quiz Completed",
			description=f"You got **{correct_count}/{total_questions}** correct.",
			color=discord.Color.green() if correct_count == total_questions else discord.Color.gold(),
		)

		wrong_entries = []
		for index, question_data in enumerate(quiz_questions):
			selected = answers[index]
			correct = question_data["correct"]
			if selected == correct:
				continue

			selected_text = question_data["options"][selected]
			correct_text = question_data["options"][correct]
			wrong_entries.append(
				f"**Q{index + 1}. {question_data['question']}**\n"
				f"**Your answer:** {selected_text}\n"
				f"**Correct answer:** {correct_text}"
			)

		if not wrong_entries:
			result_embed.add_field(
				name="Review",
				value="Perfect score. You answered every question correctly.",
				inline=False,
			)
			return result_embed, []

		result_embed.add_field(
			name="Review",
			value="See the following message(s) for questions you got wrong.",
			inline=False,
		)

		details_text = "\n\n".join(wrong_entries)
		wrong_chunks = split_long_text(details_text, 3600)
		wrong_embeds = []
		for chunk_index, chunk in enumerate(wrong_chunks, start=1):
			wrong_embed = discord.Embed(
				title=f"Questions Missed (Page {chunk_index} of {len(wrong_chunks)})",
				description=chunk,
				color=discord.Color.red(),
			)
			wrong_embeds.append(wrong_embed)

		return result_embed, wrong_embeds

	def build_handbook_embed(self, content: str) -> discord.Embed:
		return discord.Embed(description=content, color=discord.Color.blurple())

	async def start_quiz(
		self,
		channel: discord.abc.Messageable,
		user: discord.Member | discord.User,
	):
		await self.set_quiz_channel_readable(user.id, False)
		first_question_embed = self.build_quiz_question_embed(0)
		view = MentorQuizView(self, user.id, 0, [])
		message = await channel.send(content=user.mention, embed=first_question_embed, view=view)
		view.message = message

	@app_commands.command(name="mentor", description="Start the MystiCraft mentor handbook and quiz for new staff members.")
	async def mentor(self, interaction: discord.Interaction) -> None:
		if interaction.guild.id != 1064570075304177734:
			await interaction.response.send_message(
				"This command can only be used in the MystiCraft staff server.",
				ephemeral=True,
			)
			return
		if not HANDBOOK_PAGES:
			return await interaction.response.send_message(
				"Handbook content is unavailable right now. Please contact the developer.",
				ephemeral=True,
			)

		first_embed = self.build_page_embed(HANDBOOK_PAGES[0], 0)
		view = MentorNextView(self, interaction.user.id, 0)
		await interaction.response.send_message(embed=first_embed, view=view)

	@app_commands.command(name="handbook", description="Send the MystiCraft staff handbook as sequential messages.")
	async def handbook(self, interaction: discord.Interaction) -> None:
		if interaction.guild.id != 1064570075304177734:
			await interaction.response.send_message(
				"This command can only be used in the MystiCraft staff server.",
				ephemeral=True,
			)
			return

		if not HANDBOOK_SECTION_PAGES:
			await interaction.response.send_message(
				"Handbook content is unavailable right now. Please contact the developer.",
				ephemeral=True,
			)
			return

		await interaction.response.defer()

		for index, page in enumerate(HANDBOOK_SECTION_PAGES):
			embed = self.build_handbook_embed(page)
			await interaction.channel.send(embed=embed)

		await interaction.followup.send("Finished sending the handbook.")
			

async def setup(bot: commands.Bot) -> None:
	await bot.add_cog(Mentor(bot))