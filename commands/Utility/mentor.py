import discord
import os
import aiohttp

from discord import app_commands
from discord.ext import commands

STAFF_TRAINING_API_URL = "http://mysticraft.xyz/api/admin/staff-training"
STAFF_TRAINING_API_KEY = os.environ.get("BOT_ACCESS_API_KEY")
QUIZ_CHOICE_LABELS = ["A", "B", "C", "D"] 
QUIZ_LOCK_CHANNEL_ID = 1342522451229278320

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

        section_header_line = lines[i]
        i += 1

        section_intro_lines = [section_header_line]
        while i < len(lines) and not lines[i].startswith("## ") and not lines[i].startswith("### "):
            section_intro_lines.append(lines[i])
            i += 1

        section_intro_text = "\n".join(section_intro_lines).strip()
        if section_intro_text:
            pages.extend(split_long_text(section_intro_text, max_length))

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


async def fetch_staff_training_data() -> dict | None:
    if not STAFF_TRAINING_API_KEY:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                STAFF_TRAINING_API_URL,
                headers={"x-api-key": STAFF_TRAINING_API_KEY},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    return None
                return await response.json()
    except Exception:
        return None


def parse_quiz_questions(fetched_questions: list) -> list[dict]:
    if not isinstance(fetched_questions, list):
        return []
    valid_questions = []
    for entry in fetched_questions:
        if not isinstance(entry, dict):
            continue
        question_text = entry.get("question")
        options = entry.get("options")
        correct = entry.get("correct")
        if not isinstance(question_text, str) or not question_text.strip():
            continue
        if not isinstance(options, list) or len(options) != 4:
            continue
        if not all(isinstance(o, str) and o.strip() for o in options):
            continue
        if not isinstance(correct, int) or not (0 <= correct <= 3):
            continue
        valid_questions.append({"question": question_text, "options": options, "correct": correct})
    return valid_questions


class MentorNextView(discord.ui.View):
    def __init__(self, cog: "Mentor", user_id: int, page_index: int, total_pages: int):
        super().__init__(timeout=3600)
        self.cog = cog
        self.user_id = user_id
        self.page_index = page_index
        self.previous_page.disabled = page_index == 0
        if page_index >= total_pages - 1:
            self.next_page.label = "Start Quiz"

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "Only the person who started this mentor flow can continue it.",
                ephemeral=True,
            )

        await interaction.response.defer()
        
        # Fetch fresh data for previous page
        data = await fetch_staff_training_data()
        handbook_text = data.get("handbook", "") if data else ""
        pages = build_handbook_pages(handbook_text) if handbook_text.strip() else []

        previous_index = self.page_index - 1
        if previous_index < 0 or previous_index >= len(pages):
            return

        previous_embed = self.cog.build_page_embed(pages[previous_index], previous_index, len(pages))
        previous_view = MentorNextView(self.cog, self.user_id, previous_index, len(pages))
        await interaction.message.edit(embed=previous_embed, view=previous_view)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "Only the person who started this mentor flow can continue it.",
                ephemeral=True,
            )

        await interaction.response.defer()

        # Fetch fresh data for next page / quiz kickoff
        data = await fetch_staff_training_data()
        handbook_text = data.get("handbook", "") if data else ""
        pages = build_handbook_pages(handbook_text) if handbook_text.strip() else []

        next_index = self.page_index + 1
        if next_index < len(pages):
            next_embed = self.cog.build_page_embed(pages[next_index], next_index, len(pages))
            next_view = MentorNextView(self.cog, self.user_id, next_index, len(pages))
            await interaction.message.edit(embed=next_embed, view=next_view)
            return

        quiz_intro_embed = self.cog.build_quiz_intro_embed()
        await interaction.message.edit(embed=quiz_intro_embed, view=None)

        # Parse questions fresh from the same payload
        questions = parse_quiz_questions(data.get("questions")) if data else []
        if not questions:
            await interaction.followup.send("Failed to load quiz questions from API. Flow stopped.", ephemeral=True)
            return

        await self.cog.start_quiz(channel=interaction.channel, user=interaction.user, quiz_questions=questions)


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
        if self.message is None or self.completed or (len(self.message.embeds) > 0 and self.message.embeds[0].title == "Mentor Quiz Completed"):
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
        await interaction.response.defer()
        
        next_answers = self.answers + [selected_option]
        next_question_index = self.question_index + 1

        # Fetch fresh data to ensure we process answers against latest structure
        data = await fetch_staff_training_data()
        quiz_questions = parse_quiz_questions(data.get("questions")) if data else []
        
        if not quiz_questions:
            await interaction.followup.send("Failed to sync live quiz questions from API.", ephemeral=True)
            return

        if next_question_index < len(quiz_questions):
            next_embed = self.cog.build_quiz_question_embed(next_question_index, quiz_questions)
            next_view = MentorQuizView(self.cog, self.user_id, next_question_index, next_answers)
            await interaction.message.edit(embed=next_embed, view=next_view)
            return

        result_embed, wrong_embeds = self.cog.build_quiz_result_embeds(next_answers, quiz_questions)
        self.completed = True
        self.stop()
        await interaction.message.edit(embed=result_embed, view=None)
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

    def build_page_embed(self, content: str, page_index: int, total_pages: int) -> discord.Embed:
        embed = discord.Embed(description=content, color=discord.Color.blurple())
        embed.set_footer(text=f"Handbook Page {page_index + 1}/{total_pages}")
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

    def build_quiz_question_embed(self, question_index: int, quiz_questions: list[dict]) -> discord.Embed:
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

    def build_quiz_result_embeds(self, answers: list[int], quiz_questions: list[dict]) -> tuple[discord.Embed, list[discord.Embed]]:
        total_questions = len(quiz_questions)
        correct_count = 0
        wrong_entries = []
        
        for index, question_data in enumerate(quiz_questions):
            # Guard against answers index length anomalies if API question count shrinks mid-flight
            if index >= len(answers):
                continue
                
            selected = answers[index]
            correct = question_data["correct"]
            if selected == correct:
                correct_count += 1
                continue

            selected_text = question_data["options"][selected]
            correct_text = question_data["options"][correct]
            wrong_entries.append(
                f"**Q{index + 1}. {question_data['question']}**\n"
                f"**Your answer:** {selected_text}\n"
                f"**Correct answer:** {correct_text}"
            )

        result_embed = discord.Embed(
            title="Mentor Quiz Completed",
            description=f"You got **{correct_count}/{total_questions}** correct.",
            color=discord.Color.green() if correct_count == total_questions else discord.Color.gold(),
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
        quiz_questions: list[dict]
    ):
        await self.set_quiz_channel_readable(user.id, False)
        first_question_embed = self.build_quiz_question_embed(0, quiz_questions)
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

        await interaction.response.defer()
        
        data = await fetch_staff_training_data()
        handbook_text = data.get("handbook", "") if data else ""
        pages = build_handbook_pages(handbook_text) if handbook_text.strip() else []

        if not pages:
            return await interaction.followup.send(
                "Handbook content is unavailable right now. Please contact the developer.",
                ephemeral=True,
            )

        first_embed = self.build_page_embed(pages[0], 0, len(pages))
        view = MentorNextView(self, interaction.user.id, 0, len(pages))
        await interaction.followup.send(embed=first_embed, view=view)

    @app_commands.command(name="handbook", description="Send the MystiCraft staff handbook as sequential messages.")
    async def handbook(self, interaction: discord.Interaction) -> None:
        if interaction.guild.id != 1064570075304177734:
            await interaction.response.send_message(
                "This command can only be used in the MystiCraft staff server.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        data = await fetch_staff_training_data()
        handbook_text = data.get("handbook", "") if data else ""
        section_pages = build_handbook_section_pages(handbook_text) if handbook_text.strip() else []

        if not section_pages:
            await interaction.followup.send(
                "Handbook content is unavailable right now. Please contact the developer.",
                ephemeral=True,
            )
            return
            
        CHANNEL = interaction.guild.get_channel(QUIZ_LOCK_CHANNEL_ID)

        for index, page in enumerate(section_pages):
            embed = self.build_handbook_embed(page)
            await CHANNEL.send(embed=embed)

        await interaction.followup.send(f"Finished sending the handbook in {CHANNEL.mention}.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Mentor(bot))