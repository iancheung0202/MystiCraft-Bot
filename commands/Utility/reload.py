import discord, os
from discord import app_commands
from discord.ext import commands

class Reload(commands.Cog):
  def __init__(self, bot: commands.Bot) -> None:
    self.bot = bot

  @app_commands.command(
    name = "reload",
    description = "Reload bot files (for bot developers only)"
  )
  async def reload(
    self,
    interaction: discord.Interaction
  ) -> None:
    await interaction.response.defer(ephemeral=True)
    ids = [647349358790180875, 692254240290242601, 740750243808673895]
    if interaction.user.id not in ids:
      await interaction.followup.send(content=f":x: You don't have permission to use this command.")
      return
    count = 0
    for path, subdirs, files in os.walk('commands'):
      for name in files:
        if name.endswith('.py'):
          extension = os.path.join(path, name).replace("/", ".")[:-3]
          await self.bot.reload_extension(extension)
          count += 1
    print(f"Reloaded {count} files.")
    await self.bot.tree.sync()
    await interaction.followup.send(content=f"Reloaded {count} files.")
    

async def setup(bot: commands.Bot) -> None:
  await bot.add_cog(Reload(bot))