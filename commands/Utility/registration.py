import discord
import datetime

from firebase_admin import db
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput

class RegistrationModal(Modal):
    def __init__(self, queue_id, questions):
        super().__init__(title=f"Registration: {queue_id}")
        self.queue_id = queue_id
        self.questions = questions.split(',')
        self.inputs = []
        
        for question in self.questions:
            input_field = TextInput(
                label=question.strip(),
                style=discord.TextStyle.short,
                required=True
            )
            self.add_item(input_field)
            self.inputs.append(input_field)

    async def on_submit(self, interaction: discord.Interaction):
        answers = {q: inp.value for q, inp in zip(self.questions, self.inputs)}
        
        ref = db.reference(f"/Registrations/{self.queue_id}/{interaction.user.id}")
        if ref.get():
            await interaction.response.send_message(
                f"❌ Registration failed! You were already registered for `{self.queue_id}`.",
                ephemeral=True
            )
            return
        
        ref = db.reference(f"/Registrations/{self.queue_id}")
        user_data = {
            "user_id": interaction.user.id,
            "username": str(interaction.user),
            "answers": answers
        }
        ref.child(str(interaction.user.id)).set(user_data)
        
        await interaction.response.send_message(
            f"✅ Registration submitted for `{self.queue_id}`!",
            ephemeral=True
        )

class RegistrationButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(
            label="Register",
            style=discord.ButtonStyle.primary,
            custom_id="registration_button"
        ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        message = interaction.message
        if not message.embeds:
            await interaction.response.send_message("❌ This message has no embed.", ephemeral=True)
            return False
            
        embed = message.embeds[0]
        footer = embed.footer.text if embed.footer else ""
        if not footer.startswith("Queue ID: "):
            await interaction.response.send_message("❌ Could not find queue ID in embed footer.", ephemeral=True)
            return False
            
        queue_id = footer[len("Queue ID: "):].strip()
        
        ref = db.reference(f"/Registration Queues/{queue_id}")
        queue = ref.get()
        if not queue:
            await interaction.response.send_message("❌ This registration queue no longer exists.", ephemeral=True)
            return False
        
        reg_ref = db.reference(f"/Registrations/{queue_id}/{interaction.user.id}")
        if reg_ref.get():
            view = CancelRegistrationView(queue_id, interaction.user.id)
            await interaction.response.send_message(
                f"❌ You're already registered for `{queue_id}`! Would you like to cancel your existing registration?",
                view=view,
                ephemeral=True
            )
            return False
            
        modal = RegistrationModal(queue_id, queue['questions'])
        await interaction.response.send_modal(modal)
        return True

class CancelRegistrationView(View):
    def __init__(self, queue_id, user_id):
        super().__init__(timeout=None) 
        self.queue_id = queue_id
        self.user_id = user_id

    @discord.ui.button(label="Cancel Registration", style=discord.ButtonStyle.danger, custom_id="cancelRegistration")
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the original registrant can cancel this registration.", ephemeral=True)
            return
            
        ref = db.reference(f"/Registrations/{self.queue_id}/{self.user_id}")
        if not ref.get():
            await interaction.response.send_message("❌ Registration not found. It may have already been cancelled.", ephemeral=True)
            return
            
        ref.delete()
        await interaction.response.send_message(
            f"✅ Your registration for `{self.queue_id}` has been cancelled.",
            ephemeral=True
        )
        button.disabled = True
        button.label = "Cancelled"
        button.style = discord.ButtonStyle.grey
        await interaction.message.edit(view=self)
        
class QueueListView(discord.ui.View):
    def __init__(self, queues, user_id):
        super().__init__(timeout=None)
        self.queues = queues
        self.user_id = user_id
        self.page = 0
        self.max_page = (len(queues) - 1) // 25
        self.update_buttons()

    def update_buttons(self):
        self.prev_button.disabled = (self.page == 0)
        self.next_button.disabled = (self.page == self.max_page)

    def create_embed(self):
        embed = discord.Embed(
            title="Registration Queues",
            color=discord.Color.green()
        )
        start = self.page * 25
        end = start + 25
        for qid, data in list(self.queues.items())[start:end]:
            embed.add_field(
                name=qid,
                value=f"Questions: {data['questions']}",
                inline=False
            )
        embed.set_footer(text=f"Page {self.page+1}/{self.max_page+1}")
        return embed

    @discord.ui.button(label="◀", style=discord.ButtonStyle.grey, custom_id="prev_queue")
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return
        self.page -= 1
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.create_embed(), 
            view=self
        )

    @discord.ui.button(label="▶", style=discord.ButtonStyle.grey, custom_id="next_queue")
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return
        self.page += 1
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.create_embed(), 
            view=self
        )

class RegistrationView(discord.ui.View):
    def __init__(self, queue_id, registrations, user_id, guild):
        super().__init__(timeout=None)
        self.queue_id = queue_id
        self.registrations = list(registrations.items())
        self.user_id = user_id
        self.guild = guild
        self.page = 0
        self.max_page = (len(self.registrations) - 1) // 25
        self.update_buttons()

    def update_buttons(self):
        self.prev_button.disabled = (self.page == 0)
        self.next_button.disabled = (self.page == self.max_page)

    def create_embed(self):
        embed = discord.Embed(
            title=f"Registrations: {self.queue_id}",
            color=discord.Color.blue()
        )
        start = self.page * 25
        end = start + 25
        for user_id, data in self.registrations[start:end]:
            user = self.guild.get_member(int(user_id))
            user_field = user.name if user else f"User ID: {user_id}"
            answers = "\n".join(
                f"**{k}:** {v}" for k, v in data['answers'].items()
            )
            embed.add_field(
                name=user_field,
                value=f"**User:** {user.mention if user else 'Unknown'}\n{answers}",
                inline=False
            )
        embed.set_footer(text=f"Page {self.page+1}/{self.max_page+1}")
        return embed

    @discord.ui.button(label="◀", style=discord.ButtonStyle.grey, custom_id="prev_registration")
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return
        self.page -= 1
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.create_embed(), 
            view=self
        )

    @discord.ui.button(label="▶", style=discord.ButtonStyle.grey, custom_id="next_registration")
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return
        self.page += 1
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.create_embed(), 
            view=self
        )
            
@app_commands.guild_only()
class Registration(commands.GroupCog, name="registration"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()
        
    @app_commands.command(name="create", description="Create a new registration queue")
    @app_commands.describe(
        queue_id="Unique ID for this registration",
        questions="Comma-separated question labels (e.g., Name,Age,Email)"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def registration_create(
        self,
        interaction: discord.Interaction,
        queue_id: str,
        questions: str
    ):
        ref = db.reference("/Registration Queues")
        if ref.child(queue_id).get():
            await interaction.response.send_message(
                "❌ A queue with this ID already exists",
                ephemeral=True
            )
            return
            
        data = {
            "server_id": interaction.guild.id,
            "questions": questions,
            "created_by": interaction.user.id,
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        ref.child(queue_id).set(data)
        
        await interaction.response.send_message(
            f"✅ Registration queue `{queue_id}` created with questions: {questions}",
            ephemeral=True
        )
    
    @app_commands.command(name="delete", description="Delete a registration queue")
    @app_commands.describe(queue_id="The ID of the queue to delete")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def registration_delete(
        self,
        interaction: discord.Interaction,
        queue_id: str
    ):
        queues_ref = db.reference("/Registration Queues")
        if not queues_ref.child(queue_id).get():
            await interaction.response.send_message(
                "❌ Queue not found",
                ephemeral=True
            )
            return
            
        queues_ref.child(queue_id).delete()
        
        reg_ref = db.reference(f"/Registrations/{queue_id}")
        reg_ref.delete()
        
        await interaction.response.send_message(
            f"✅ Queue `{queue_id}` and all registrations deleted",
            ephemeral=True
        )
    
    @app_commands.command(name="embed", description="Create registration embed")
    @app_commands.describe(
        queue_id="The queue ID to register for",
        title="Embed title",
        description="Embed description"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def registration_embed(
        self,
        interaction: discord.Interaction,
        queue_id: str,
        title: str = "Registration",
        description: str = "Click the button below to register"
    ):
        ref = db.reference(f"/Registration Queues/{queue_id}")
        if not ref.get():
            await interaction.response.send_message("❌ Queue not found", ephemeral=True)
            return
            
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Queue ID: {queue_id}")
        
        view = RegistrationButtonView()
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Registration embed created!", ephemeral=True)

    @app_commands.command(name="view", description="View registration data")
    @app_commands.describe(queue_id="The queue ID to view (leave blank to list queues)")
    async def registration_view(
        self,
        interaction: discord.Interaction,
        queue_id: str = None
    ):
        if queue_id:
            ref = db.reference(f"/Registrations/{queue_id}")
            registrations = ref.get()
            
            if not registrations:
                await interaction.response.send_message(
                    "❌ No registrations found for this queue",
                    ephemeral=True
                )
                return
                
            view = RegistrationView(
                queue_id,
                registrations,
                interaction.user.id,
                interaction.guild
            )
            await interaction.response.send_message(
                embed=view.create_embed(),
                view=view,
                ephemeral=True
            )
        else:
            ref = db.reference("/Registration Queues")
            queues = ref.get()
            
            if not queues:
                await interaction.response.send_message(
                    "❌ No registration queues found",
                    ephemeral=True
                )
                return
                
            guild_queues = {
                qid: data for qid, data in queues.items()
                if data['server_id'] == interaction.guild.id
            }
            
            if not guild_queues:
                await interaction.response.send_message(
                    "❌ No registration queues found for this server",
                    ephemeral=True
                )
                return
                
            view = QueueListView(guild_queues, interaction.user.id)
            await interaction.response.send_message(
                embed=view.create_embed(),
                view=view,
                ephemeral=True
            )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Registration(bot))