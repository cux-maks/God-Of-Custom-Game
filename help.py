import discord
from discord.ext import commands

class CustomHelp(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="명령어 목록", color=discord.Color.blue())
        
        for cog, commands in mapping.items():
            filtered = await self.filter_commands(commands)
            command_signatures = [f"%{c.name} - {c.help or '설명 없음'}" for c in filtered]
            if command_signatures:
                cog_name = getattr(cog, "qualified_name", "기타")
                embed.add_field(name=cog_name, value="\n".join(command_signatures), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)