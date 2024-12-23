import discord
from discord.ext import commands
from services.user_service import UserService
from utils.validators import validate_nickname_tag
from utils.embed_builder import EmbedBuilder
from datetime import datetime
import asyncio

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_service = UserService()

    @commands.command(
        name="유저등록",
        help="새로운 게이머를 등록합니다.",
        usage="%유저등록 [닉네임#태그]"
    )
    async def register(self, ctx, nickname_tag: str):
        # 닉네임 형식 검증
        if not validate_nickname_tag(nickname_tag):
            embed = EmbedBuilder.error(
                "등록 실패",
                "올바른 형식이 아닙니다.",
                fields=[("올바른 형식", "'닉네임#태그' 형식으로 입력해주세요.\n예시: `%유저등록 플레이어#KR1`", False)]
            )
            await ctx.reply(embed=embed)
            return

        # 유저 등록 시도
        success = await self.user_service.register_user(
            nickname_tag,
            str(ctx.author)
        )

        if not success:
            # 이미 등록된 사용자인지 확인
            discord_id, user_data = await self.user_service.find_user_by_nickname(nickname_tag)
            if user_data:
                embed = EmbedBuilder.error(
                    "등록 실패",
                    f"이미 등록된 닉네임입니다.\n현재 등록: {user_data['nickname']}"
                )
            else:
                embed = EmbedBuilder.error(
                    "등록 실패",
                    "알 수 없는 오류가 발생했습니다."
                )
        else:
            embed = EmbedBuilder.success(
                "등록 성공",
                f"{nickname_tag} 님이 성공적으로 등록되었습니다!",
                fields=[
                    ("디스코드 닉네임", str(ctx.author), True),
                    ("등록 시각", datetime.now().strftime("%Y-%m-%d %H:%M"), True)
                ],
                footer="게임에 참여하실 준비가 완료되었습니다!"
            )
        await ctx.reply(embed=embed)

    @commands.command(
        name="유저삭제",
        help="등록된 게이머를 삭제합니다. (관리자 전용)",
        usage="%유저삭제 [닉네임#태그]"
    )
    @commands.has_permissions(administrator=True)
    async def delete_user(self, ctx, nickname_tag: str):
        try:
            # 삭제 확인 임베드
            confirm_embed = EmbedBuilder.warning(
                "삭제 확인",
                f"'{nickname_tag}' 유저를 정말 삭제하시겠습니까?",
                fields=[("확인 방법", "✅ - 삭제\n❌ - 취소", False)],
                footer="30초 내에 반응이 없으면 자동으로 취소됩니다."
            )
            
            confirm_msg = await ctx.reply(embed=confirm_embed)
            
            # 반응 추가
            await confirm_msg.add_reaction('✅')
            await confirm_msg.add_reaction('❌')
            
            def check(reaction, user):
                return (
                    user == ctx.author and 
                    str(reaction.emoji) in ['✅', '❌'] and 
                    reaction.message.id == confirm_msg.id
                )
            
            try:
                reaction, _ = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
                
                if str(reaction.emoji) == '✅':
                    deleted_id = await self.user_service.delete_user(nickname_tag)
                    if deleted_id:
                        embed = EmbedBuilder.success(
                            "삭제 완료",
                            f"'{nickname_tag}' 유저가 성공적으로 삭제되었습니다."
                        )
                    else:
                        embed = EmbedBuilder.error(
                            "유저 not found",
                            f"'{nickname_tag}' 유저를 찾을 수 없습니다."
                        )
                else:
                    embed = EmbedBuilder.error(
                        "삭제 취소",
                        "유저 삭제가 취소되었습니다."
                    )
                    
                await confirm_msg.delete()
                await ctx.reply(embed=embed)
                
            except asyncio.TimeoutError:
                await confirm_msg.delete()
                embed = EmbedBuilder.error(
                    "시간 초과",
                    "시간이 초과되어 삭제가 취소되었습니다."
                )
                await ctx.reply(embed=embed)
                
        except Exception as e:
            embed = EmbedBuilder.error(
                "오류 발생",
                f"오류가 발생했습니다: {str(e)}"
            )
            await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))