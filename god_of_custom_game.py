import discord
from discord.ext import commands

from help import CustomHelp

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix="%",
            intents=intents,
            help_command=CustomHelp(command_attrs={'name': '도움', 'help': '사용 가능한 명령어 목록을 보여줍니다.'})
        )

    async def setup_hook(self):
        # 봇이 시작될 때 실행될 초기 설정들
        await self.add_commands()
        
    async def add_commands(self):
        # 명령어들을 여기서 추가
        @self.command(name="설명", help="봇에 대한 설명을 보여줍니다.")
        async def 설명(ctx):
            await ctx.send(f"{ctx.author.mention} : 설명이다 이히히")

        @self.command(name="핑!", help="봇의 지연 시간을 측정합니다.")
        async def 핑(ctx):
            await ctx.send(f"퐁! {round(self.latency * 1000)}ms")

    async def on_ready(self):
        print(f"Login bot: {self.user}")