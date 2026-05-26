from discord.ext import commands

class OnMemberRemove(commands.Cog): 
    def __init__(self, bot):
        self.client = bot
  
    @commands.Cog.listener() 
    async def on_member_remove(self, user):
        if user.guild.id == 1136662635039952988:
            channel = self.client.get_channel(1136672658503774258)
            msg = f"**{user.name}** left our server! Only **{len(user.guild.members)} members** left!"
            await channel.send(msg)
            
async def setup(bot): 
    await bot.add_cog(OnMemberRemove(bot))