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

        # 진행 중 임베드 표시
        progress_embed = EmbedBuilder.info(
            "등록 진행 중",
            f"{nickname_tag} 님의 전적을 분석하고 있습니다...",
            fields=[("예상 소요 시간", "약 10-20초", False)],
            footer="Riot API에서 데이터를 가져오는 중..."
        )
        progress_msg = await ctx.reply(embed=progress_embed)

        # 유저 등록 시도
        success, error_msg, user_info = await self.user_service.register_user(
            nickname_tag=nickname_tag,
            discord_name=str(ctx.author)  # 필요 없지만 메서드 signature는 유지
        )

        if not success:
            embed = EmbedBuilder.error(
                "등록 실패",
                error_msg
            )
        else:
            # 성능 지표 문자열 생성
            win_rate = (user_info['wins'] / user_info['games_played'] * 100) if user_info['games_played'] > 0 else 0
            performance_str = (
                f"• 전체 게임: {user_info['games_played']}게임\n"
                f"• 승/패: {user_info['wins']}승 {user_info['losses']}패 ({win_rate:.1f}%)\n"
                f"• 평균 KDA: {user_info['avg_kda']:.2f}\n"
                f"• 평균 딜량: {user_info['avg_damage_dealt']:,}\n"
                f"• 평균 받은 피해: {user_info['avg_damage_taken']:,}\n"
                f"• 평균 힐량: {user_info['avg_healing']:,}\n"
                f"• CC 점수: {user_info.get('avg_cc_score', 0):.1f}\n"
                f"• 종합 점수: {user_info['performance_score']:.2f}"
            )

            embed = EmbedBuilder.success(
                "등록 성공",
                f"{nickname_tag} 님이 성공적으로 등록되었습니다!",
                fields=[
                    ("등록 시각", datetime.now().strftime("%Y-%m-%d %H:%M"), True),
                    ("실력 분석 결과", performance_str, False)
                ],
                footer="게임에 참여하실 준비가 완료되었습니다!"
            )

        await progress_msg.delete()
        await ctx.reply(embed=embed)

    @commands.command(
        name="유저삭제",
        help="등록된 게이머를 삭제합니다. (관리자 전용)",
        usage="%유저삭제 [닉네임#태그]"
    )
    @commands.has_permissions(administrator=True)
    async def delete_user(self, ctx, nickname_tag: str):
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
                success, error_msg = await self.user_service.delete_user(nickname_tag)
                if success:
                    embed = EmbedBuilder.success(
                        "삭제 완료",
                        f"'{nickname_tag}' 유저가 성공적으로 삭제되었습니다."
                    )
                else:
                    embed = EmbedBuilder.error(
                        "삭제 실패",
                        error_msg
                    )
            else:
                embed = EmbedBuilder.info(
                    "삭제 취소",
                    "유저 삭제가 취소되었습니다."
                )
            
            await confirm_msg.delete()
            await ctx.reply(embed=embed)
            
        except asyncio.TimeoutError:
            await confirm_msg.delete()
            embed = EmbedBuilder.error(
                "시간 초과",
                "30초가 지나 삭제가 자동으로 취소되었습니다."
            )
            await ctx.reply(embed=embed)

    @commands.command(
        name="유저목록",
        help="등록된 모든 유저의 목록을 보여줍니다.",
        usage="%유저목록"
    )
    async def list_users(self, ctx):
        user_data = await self.user_service.load_user_data()
        
        if not user_data:
            embed = EmbedBuilder.error(
                "등록된 유저 없음",
                "현재 등록된 유저가 없습니다."
            )
            await ctx.reply(embed=embed)
            return
            
        # 닉네임순으로 정렬
        sorted_users = sorted(user_data.items(), key=lambda x: x[0].lower())
        
        # 데이터를 두 개의 컬럼으로 나누어 표시 (3개에서 2개로 변경)
        column1, column2 = [], []
        columns = [column1, column2]
        
        for i, (nickname, data) in enumerate(sorted_users):
            # 승률 계산
            winrate = (data['wins'] / data['games_played'] * 100) if data['games_played'] > 0 else 0
            
            # 유저 정보 포맷팅
            user_info = (
                f"```\n"
                f"{nickname}\n"
                f"승률  : {winrate:.0f}%\n"
                f"KDA   : {data['avg_kda']:.1f}\n"
                f"평점  : {data['performance_score']:.1f}\n"
                f"```"
            )
            
            # 각 컬럼에 번갈아가며 추가
            columns[i % 2].append(user_info)

        # 임베드 필드 생성
        if column1:
            embed = discord.Embed(
                title="📊 등록된 유저 목록",
                description=f"총 {len(user_data)}명의 유저가 등록되어 있습니다.",
                color=discord.Color.blue()
            )
            
            # 필드 이름을 공백으로 설정하되, Zero-Width Space를 사용하여 구분
            if column1:
                embed.add_field(name="⠀", value="\n".join(column1), inline=True)
            if column2:
                embed.add_field(name="⠀", value="\n".join(column2), inline=True)
            
            embed.set_footer(text="자세한 정보는 %유저정보 [닉네임#태그]")
            
            await ctx.reply(embed=embed)

    @commands.command(
        name="유저정보",
        help="등록된 게이머의 정보를 조회합니다.",
        usage="%유저정보 [닉네임#태그]"
    )
    async def user_info(self, ctx, nickname_tag: str):
        user_info, error_msg = await self.user_service.get_user(nickname_tag)
        
        if error_msg:
            embed = EmbedBuilder.error(
                "조회 실패",
                error_msg
            )
        else:
            # 성능 지표 문자열 생성
            performance_str = (
                f"• 전체 게임: {user_info['games_played']}게임\n"
                f"• 승/패: {user_info['wins']}승 {user_info['losses']}패\n"
                f"• 승률: {(user_info['wins'] / user_info['games_played'] * 100):.1f}%\n"
                f"• 평균 KDA: {user_info['avg_kda']:.2f}\n"
                f"• 평균 딜량: {user_info['avg_damage_dealt']:,}\n"
                f"• 평균 받은 피해: {user_info['avg_damage_taken']:,}\n"
                f"• 평균 힐량: {user_info['avg_healing']:,}\n"
                f"• CC 점수: {user_info.get('avg_cc_score', 0):.1f}\n"
                f"• 종합 점수: {user_info['performance_score']:.2f}"
            )
            
            last_updated = datetime.fromisoformat(user_info['last_updated'])
            time_diff = datetime.now() - last_updated
            
            embed = EmbedBuilder.info(
                f"{nickname_tag}님의 정보",
                "ARAM 전적 분석 결과",
                fields=[
                    ("등록일", datetime.fromisoformat(user_info['registered_at']).strftime("%Y-%m-%d"), True),
                    ("실력 분석 결과", performance_str, False)
                ],
                footer=f"마지막 업데이트: {time_diff.days}일 전"
            )
        
        await ctx.reply(embed=embed)

    @commands.command(
        name="전적갱신",
        help="등록된 게이머의 전적 정보를 최신 데이터로 갱신합니다.",
        usage="%전적갱신 [닉네임#태그]"
    )
    async def update_stats(self, ctx, nickname_tag: str):
        # 진행 중 임베드 표시
        progress_embed = EmbedBuilder.info(
            "갱신 진행 중",
            f"{nickname_tag} 님의 최신 전적을 분석하고 있습니다...",
            fields=[("예상 소요 시간", "약 10-20초", False)],
            footer="Riot API에서 데이터를 가져오는 중..."
        )
        progress_msg = await ctx.reply(embed=progress_embed)

        # 전적 갱신 시도
        success, error_msg, user_info = await self.user_service.update_user_stats(nickname_tag)

        if not success:
            embed = EmbedBuilder.error(
                "갱신 실패",
                error_msg
            )
        else:
            # 성능 지표 문자열 생성
            performance_str = (
                f"• 전체 게임: {user_info['games_played']}게임\n"
                f"• 승/패: {user_info['wins']}승 {user_info['losses']}패\n"
                f"• 승률: {(user_info['wins'] / user_info['games_played'] * 100):.1f}%\n"
                f"• 평균 KDA: {user_info['avg_kda']:.2f}\n"
                f"• 평균 딜량: {user_info['avg_damage_dealt']:,}\n"
                f"• 평균 받은 피해: {user_info['avg_damage_taken']:,}\n"
                f"• 평균 힐량: {user_info['avg_healing']:,}\n"
                f"• CC 점수: {user_info.get('avg_cc_score', 0):.1f}\n"
                f"• 종합 점수: {user_info['performance_score']:.2f}"
            )

            embed = EmbedBuilder.success(
                "갱신 완료",
                f"{nickname_tag} 님의 전적이 성공적으로 갱신되었습니다!",
                fields=[
                    ("갱신 시각", datetime.now().strftime("%Y-%m-%d %H:%M"), True),
                    ("실력 분석 결과", performance_str, False)
                ]
            )

        await progress_msg.delete()
        await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))