from discord.ext import commands
import discord
from utils.constants import DISCORD_TOKEN, COMMAND_PREFIX, MESSAGES, COLORS
from utils.embed_builder import EmbedBuilder
import asyncio

class MyBot(commands.Bot):
    def __init__(self):
        # 인텐트 설정
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix=COMMAND_PREFIX,
            intents=intents,
            help_command=None  # 기본 도움말 명령어 비활성화
        )
        
    async def setup_hook(self):
        """봇 시작 시 실행되는 설정"""
        # 코그 로드
        await self.load_extension("bot.cogs.user_commands")
        await self.load_extension("bot.cogs.game_commands")
        await self.load_extension("bot.cogs.stats_updater")  # 추가된 부분
        await self.add_base_commands()
        
    async def add_base_commands(self):
        """기본 명령어 추가"""
        @self.command(
            name="도움",
            help="사용 가능한 명령어 목록을 보여줍니다.",
            usage=f"{COMMAND_PREFIX}도움 [명령어]"
        )
        async def help(ctx, command_name: str = None):
            if command_name:
                # 특정 명령어의 도움말
                command = self.get_command(command_name)
                if command is None:
                    embed = EmbedBuilder.error(
                        "명령어 not found",
                        f"'{command_name}' 명령어를 찾을 수 없습니다."
                    )
                else:
                    embed = EmbedBuilder.info(
                        f"'{command_name}' 명령어 도움말",
                        command.help if command.help else "도움말이 없습니다.",
                        fields=[
                            ("사용법", command.usage if command.usage else "사용법이 지정되지 않았습니다.", False),
                            ("별칭", ", ".join(command.aliases) if command.aliases else "없음", False)
                        ]
                    )
            else:
                # 전체 명령어 목록
                commands_info = []
                for command in self.commands:
                    if not command.hidden:
                        usage = f"`{command.usage}`" if command.usage else "사용법이 지정되지 않았습니다."
                        commands_info.append(f"**{command.name}**\n{command.help}\n{usage}\n")

                embed = EmbedBuilder.info(
                    "명령어 도움말",
                    "사용 가능한 명령어 목록입니다.",
                    fields=[("명령어 목록", "\n".join(commands_info), False)],
                    footer=f"특정 명령어의 상세 정보는 {COMMAND_PREFIX}도움 [명령어] 로 확인하세요."
                )
            
            await ctx.reply(embed=embed)

        @self.command(
            name="소개",
            help="봇에 대한 설명을 보여줍니다.",
            usage=f"{COMMAND_PREFIX}소개",
            aliases=['정보']
        )
        async def info(ctx):
            embed = EmbedBuilder.info(
                "롤 내전 봇 소개",
                "칼바람 나락 내전 밸런싱을 도와주는 봇입니다.",
                fields=[
                    ("주요 기능", "• 유저 등록/관리\n• 게임 생성\n• 팀 밸런싱", False),
                    ("명령어 확인", f"{COMMAND_PREFIX}도움 을 입력하여 사용 가능한 명령어를 확인하세요!", False)
                ],
                footer=f"Made with ❤️ | {ctx.guild.name}",
                timestamp=True
            )
            await ctx.reply(embed=embed)

        @self.event
        async def on_command_error(ctx, error):
            """기본 에러 핸들링"""
            if isinstance(error, commands.MissingRequiredArgument):
                command = ctx.command
                embed = EmbedBuilder.error(
                    "명령어 사용법 오류",
                    "필수 인자가 누락되었습니다.",
                    fields=[
                        ("명령어 사용법", f"`{command.usage}`" if command.usage else "사용법이 지정되지 않았습니다.", False),
                        ("도움말", command.help if command.help else "도움말이 없습니다.", False)
                    ]
                )
                await ctx.reply(embed=embed)
                
            elif isinstance(error, commands.MissingPermissions):
                embed = EmbedBuilder.error(
                    "권한 오류",
                    "이 명령어를 실행할 권한이 없습니다."
                )
                await ctx.reply(embed=embed)
                
            elif isinstance(error, commands.CommandNotFound):
                pass  # 존재하지 않는 명령어는 무시
                
            else:
                embed = EmbedBuilder.error(
                    "오류 발생",
                    f"예상치 못한 오류가 발생했습니다: {str(error)}"
                )
                await ctx.reply(embed=embed)

    async def on_ready(self):
        """봇이 준비되었을 때 실행"""
        print(f"Logged in as: {self.user}")
        print(f"Bot is ready to serve {len(self.guilds)} guilds!")
        
        # 상태 메시지 설정
        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name=f"{COMMAND_PREFIX}도움 | 칼바람 내전"
        )
        await self.change_presence(activity=activity)

def run_bot():
    """봇 실행 함수"""
    bot = MyBot()
    
    @bot.event
    async def on_connect():
        print(f"Connected to Discord!")
        
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        print(f"Error running bot: {e}")