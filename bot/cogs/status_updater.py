import asyncio
import logging
from discord.ext import commands, tasks
from datetime import datetime, time
from typing import Optional, List, Dict, Tuple
from services.user_service import UserService
from utils.embed_builder import EmbedBuilder
from utils.logging_config import setup_logger

class AutomaticStatsUpdater(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_service = UserService()
        self.logger = setup_logger('stats_updater', 'stats_updater.log')
        
        # 자동 갱신 작업 시작
        self.stats_update_task.start()

    def cog_unload(self):
        """코그가 언로드될 때 작업 중지"""
        self.stats_update_task.cancel()

    @tasks.loop(time=time(hour=6))  # 매일 오전 6시
    async def stats_update_task(self):
        """전체 유저 전적 자동 갱신 작업"""
        self.logger.info("일일 전적 갱신 작업 시작")
        start_time = datetime.now()
        
        # 모든 길드에 대해 처리
        for guild in self.bot.guilds:
            try:
                await self.update_guild_users(guild)
            except Exception as e:
                self.logger.error(f"길드 {guild.name} ({guild.id}) 처리 중 오류: {str(e)}")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        self.logger.info(f"일일 전적 갱신 작업 완료 (소요 시간: {duration:.1f}초)")

    async def update_guild_users(self, guild) -> None:
        """길드 내 모든 유저의 전적 갱신"""
        self.logger.info(f"길드 {guild.name} ({guild.id}) 전적 갱신 시작")
        
        # 시스템 메시지 채널 찾기
        notify_channel = None
        for channel in guild.text_channels:
            # 'bot', 'system', 'notification' 등의 키워드가 포함된 채널 우선
            if any(keyword in channel.name.lower() for keyword in ['bot', 'system', 'notification']):
                notify_channel = channel
                break
        
        if not notify_channel:
            # 쓰기 권한이 있는 첫 번째 채널 사용
            for channel in guild.text_channels:
                permissions = channel.permissions_for(guild.me)
                if permissions.send_messages:
                    notify_channel = channel
                    break

        if not notify_channel:
            self.logger.warning(f"길드 {guild.name}에서 알림을 보낼 채널을 찾을 수 없습니다.")
            return

        try:
            # 진행 상황 알림 전송
            progress_embed = EmbedBuilder.info(
                "전적 갱신 시작",
                "서버 내 모든 유저의 전적을 갱신하고 있습니다...",
                footer="매일 오전 6시에 자동으로 갱신됩니다."
            )
            progress_msg = await notify_channel.send(embed=progress_embed)

            # 길드의 모든 유저 조회
            users, error = await self.user_service.get_all_users(guild.id)
            if error:
                self.logger.error(f"길드 {guild.name} 유저 목록 조회 실패: {error}")
                return

            if not users:
                await progress_msg.edit(embed=EmbedBuilder.info(
                    "전적 갱신 완료",
                    "현재 등록된 유저가 없습니다.",
                    footer="유저를 등록하려면 %유저등록 명령어를 사용하세요."
                ))
                return

            # 갱신 결과 추적
            success_count = 0
            fail_count = 0
            updated_users = []

            # 각 유저 전적 갱신
            for user in users:
                nickname_tag = f"{user['nickname']}#{user['tag']}"
                try:
                    success, error, updated_info = await self.user_service.update_user_stats(
                        guild_id=guild.id,
                        nickname_tag=nickname_tag
                    )
                    
                    if success and updated_info:
                        success_count += 1
                        # 변경된 전적이 있는 경우만 기록
                        if self._has_stats_changed(user, updated_info):
                            updated_users.append({
                                'nickname_tag': nickname_tag,
                                'old_stats': user,
                                'new_stats': updated_info
                            })
                    else:
                        fail_count += 1
                        self.logger.warning(f"유저 {nickname_tag} 갱신 실패: {error}")
                        
                except Exception as e:
                    fail_count += 1
                    self.logger.error(f"유저 {nickname_tag} 처리 중 오류: {str(e)}")

            # 결과 임베드 생성 및 전송
            result_embed = self._create_update_result_embed(
                total=len(users),
                success=success_count,
                failed=fail_count,
                updated_users=updated_users
            )
            
            await progress_msg.edit(embed=result_embed)

        except Exception as e:
            self.logger.error(f"길드 {guild.name} 전적 갱신 중 오류: {str(e)}")
            if notify_channel:
                error_embed = EmbedBuilder.error(
                    "전적 갱신 실패",
                    "전적 갱신 중 오류가 발생했습니다."
                )
                await notify_channel.send(embed=error_embed)

    def _has_stats_changed(self, old_stats: Dict, new_stats: Dict) -> bool:
        """전적 변경 여부 확인"""
        relevant_keys = ['games_played', 'wins', 'losses', 'avg_kda', 'performance_score']
        return any(
            old_stats.get(key) != new_stats.get(key)
            for key in relevant_keys
        )

    def _create_update_result_embed(
        self,
        total: int,
        success: int,
        failed: int,
        updated_users: List[Dict]
    ) -> discord.Embed:
        """갱신 결과 임베드 생성"""
        # 변경된 전적이 있는 유저들의 정보 포맷팅
        changes_text = ""
        for user in updated_users[:5]:  # 상위 5명만 표시
            old = user['old_stats']
            new = user['new_stats']
            
            # 승률 변화 계산
            old_winrate = (old['wins'] / old['games_played'] * 100) if old['games_played'] > 0 else 0
            new_winrate = (new['wins'] / new['games_played'] * 100) if new['games_played'] > 0 else 0
            
            changes_text += (
                f"**{user['nickname_tag']}**\n"
                f"• 게임: {old['games_played']} → {new['games_played']} "
                f"({new['games_played'] - old['games_played']:+d})\n"
                f"• 승률: {old_winrate:.1f}% → {new_winrate:.1f}% "
                f"({new_winrate - old_winrate:+.1f}%)\n"
                f"• 평점: {old['performance_score']:.1f} → {new['performance_score']:.1f} "
                f"({new['performance_score'] - old['performance_score']:+.1f})\n"
            )

        # 결과 임베드 생성
        if success == total:
            title = "✅ 전적 갱신 완료"
            description = "모든 유저의 전적이 성공적으로 갱신되었습니다."
            color = discord.Color.green()
        elif success == 0:
            title = "❌ 전적 갱신 실패"
            description = "전적 갱신에 실패했습니다."
            color = discord.Color.red()
        else:
            title = "⚠️ 전적 갱신 부분 완료"
            description = "일부 유저의 전적만 갱신되었습니다."
            color = discord.Color.yellow()

        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )

        # 통계 필드 추가
        embed.add_field(
            name="📊 갱신 통계",
            value=(
                f"• 전체: {total}명\n"
                f"• 성공: {success}명\n"
                f"• 실패: {failed}명"
            ),
            inline=False
        )

        # 변경사항 필드 추가 (변경된 유저가 있는 경우만)
        if changes_text:
            embed.add_field(
                name="📈 주요 변경사항",
                value=changes_text,
                inline=False
            )
            if len(updated_users) > 5:
                embed.add_field(
                    name="ℹ️ 참고",
                    value=f"그 외 {len(updated_users) - 5}명의 유저도 전적이 변경되었습니다.",
                    inline=False
                )

        # 타임스탬프 추가
        embed.timestamp = datetime.now()
        embed.set_footer(text="다음 갱신: 내일 오전 6시")

        return embed

    @stats_update_task.before_loop
    async def before_update_task(self):
        """봇이 준비될 때까지 대기"""
        await self.bot.wait_until_ready()
        self.logger.info("자동 전적 갱신 작업 준비 완료")

async def setup(bot):
    """코그 설정"""
    await bot.add_cog(AutomaticStatsUpdater(bot))