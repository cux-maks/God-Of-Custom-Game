import discord
from discord.ext import commands
from discord import ui
from typing import List, Dict
import random
from services.user_service import UserService
from utils.embed_builder import EmbedBuilder

class PlayerSelect(ui.Select):
    def __init__(self, players: List[dict]):
        options = []
        for player in players:
            winrate = (player['wins'] / player['games_played'] * 100) if player['games_played'] > 0 else 0
            options.append(
                discord.SelectOption(
                    label=player['nickname'],
                    value=str(player['discord_id']),
                    description=f"승률: {winrate:.1f}% ({player['games_played']}게임)"
                )
            )
        super().__init__(
            placeholder="참가할 플레이어를 선택하세요",
            min_values=1,
            max_values=len(players),
            options=options
        )

class TeamBalancer:
    @staticmethod
    def calculate_player_score(player: dict) -> float:
        """플레이어의 종합 점수 계산"""
        if player['games_played'] == 0:
            return 50.0  # 기본 점수

        # 모든 값을 float로 변환
        winrate = float(player['wins']) / float(player['games_played']) * 100
        kda_score = float(player['avg_kda']) * 10
        damage_score = float(player['avg_damage_dealt']) / 1000
        tankiness_score = float(player['avg_damage_taken']) / 1000
        healing = float(player['avg_healing']) / 1000
        cc_score = float(player.get('avg_cc_score', 0)) * 2
        
        # 전투력 점수 (30%)
        combat_score = (kda_score + damage_score) / 2 * 0.3
        
        # 생존력 점수 (25%)
        survival_score = tankiness_score * 0.25
        
        # 유틸성 점수 (25%)
        utility_score = (healing + cc_score) / 2 * 0.25
        
        # 승률 점수 (20%)
        winrate_score = winrate * 0.2
        
        # 종합 점수 계산
        total_score = combat_score + survival_score + utility_score + winrate_score
        
        return float(total_score)

    @staticmethod
    def balance_teams(players: List[dict]) -> tuple[List[dict], List[dict]]:
        """종합 점수를 기준으로 최적의 팀 밸런스를 찾습니다."""
        import itertools

        # 각 플레이어의 종합 점수 계산
        for player in players:
            player['total_score'] = TeamBalancer.calculate_player_score(player)

        n = len(players)
        target_team_size = n // 2  # 목표 팀 크기
        
        min_diff = float('inf')
        best_team1 = []
        best_team2 = []

        # 가능한 모든 팀 조합을 검사
        for team1_players in itertools.combinations(players, target_team_size):
            team1_set = set(player['discord_id'] for player in team1_players)
            team2_players = [p for p in players if p['discord_id'] not in team1_set]

            team1_score = sum(float(p['total_score']) for p in team1_players)
            team2_score = sum(float(p['total_score']) for p in team2_players)
            
            # 점수 차이 계산
            score_diff = abs(team1_score - team2_score)
            
            # 더 좋은 밸런스를 찾은 경우 업데이트
            if score_diff < min_diff:
                min_diff = score_diff
                best_team1 = list(team1_players)
                best_team2 = team2_players

        return best_team1, best_team2

class GameCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_service = UserService()

    def create_team_embed(self, team1: List[dict], team2: List[dict]) -> discord.Embed:
        """팀 정보를 포함한 임베드 생성"""
        # 팀별 평균 점수 계산
        team1_avg = sum(p['total_score'] for p in team1) / len(team1)
        team2_avg = sum(p['total_score'] for p in team2) / len(team2)
        score_diff = abs(team1_avg - team2_avg)

        # 밸런스 상태 확인
        balance_state = "매우 균형" if score_diff < 5 else "균형" if score_diff < 10 else "적절" if score_diff < 15 else "불균형"
        balance_emoji = "🎯" if score_diff < 5 else "⭐" if score_diff < 10 else "⚖️" if score_diff < 15 else "⚠️"

        embed = discord.Embed(
            title="팀 구성 결과",
            description=f"{balance_emoji} 팀 밸런스: **{balance_state}** (점수차: {score_diff:.1f})",
            color=discord.Color.blue()
        )

        def create_team_text(players):
            # 플레이어 목록
            player_info = []
            team_kda = 0
            team_dmg = 0
            
            for player in players:
                winrate = (player['wins'] / player['games_played'] * 100) if player['games_played'] > 0 else 0
                player_info.append(f"{player['nickname']} ({winrate:.0f}%)")
                team_kda += float(player['avg_kda'])
                team_dmg += float(player['avg_damage_dealt'])
            
            avg_kda = team_kda / len(players)
            avg_dmg = team_dmg / len(players)
            
            return "\n".join([
                "\n".join([f"• {info}" for info in player_info]),
                "```",
                f"평균 KDA: {avg_kda:.2f}",
                f"평균 딜량: {avg_dmg:,.0f}",
                "```"
            ])

        # 팀 정보 추가 (inline으로 배치)
        embed.add_field(name="🔵 블루팀", value=create_team_text(team1), inline=True)
        embed.add_field(name="VS", value="⚔️", inline=True)
        embed.add_field(name="🔴 레드팀", value=create_team_text(team2), inline=True)

        return embed

    @commands.command(
        name="게임생성", 
        help="인원수를 입력하여 게임의 팀을 생성합니다.",
        usage="%게임생성 [인원수]"
    )
    async def create_game(self, ctx, player_count: int):
        if not 2 <= player_count <= 10:
            embed = EmbedBuilder.error(
                "인원 수 오류",
                "참가 인원은 2명에서 10명 사이여야 합니다."
            )
            await ctx.send(embed=embed)
            return

        # 등록된 모든 플레이어 데이터 가져오기
        user_data, error = await self.user_service.get_all_users(ctx.guild.id)
        if error:
            embed = EmbedBuilder.error(
                "등록된 사용자 없음",
                "게임 생성을 위해서는 먼저 사용자 등록이 필요합니다."
            )
            await ctx.send(embed=embed)
            return

        # 플레이어 데이터 가공
        players = []
        for data in user_data:
            players.append({
                'discord_id': f"{data['nickname']}#{data['tag']}",
                'nickname': data['nickname'],
                'games_played': data['games_played'],
                'wins': data['wins'],
                'losses': data['losses'],
                'avg_kda': data['avg_kda'],
                'avg_damage_dealt': data['avg_damage_dealt'],
                'avg_damage_taken': data['avg_damage_taken'],
                'avg_healing': data['avg_healing'],
                'avg_cc_score': data.get('avg_cc_score', 0)
            })

        view = discord.ui.View()
        select = PlayerSelect(players)
        
        async def select_callback(interaction: discord.Interaction):
            selected_players = [
                player for player in players
                if player['discord_id'] in select.values
            ]
            
            if len(selected_players) != player_count:
                await interaction.response.send_message(
                    f"정확히 {player_count}명의 플레이어를 선택해야 합니다.",
                    ephemeral=True
                )
                return

            # 전적 갱신 진행 메시지
            progress_embed = EmbedBuilder.info(
                "전적 갱신 중",
                "선택된 플레이어들의 전적을 갱신하고 있습니다...",
                footer="잠시만 기다려주세요..."
            )
            await interaction.response.send_message(embed=progress_embed)

            # 선택된 플레이어들의 전적 갱신
            updated_players = []
            for player in selected_players:
                success, error_msg, updated_info = await self.user_service.update_user_stats(
                    guild_id=ctx.guild.id,
                    nickname_tag=player['discord_id']
                )
                if success:
                    updated_players.append({
                        'discord_id': player['discord_id'],
                        'nickname': player['nickname'],
                        'games_played': updated_info['games_played'],
                        'wins': updated_info['wins'],
                        'losses': updated_info['losses'],
                        'avg_kda': updated_info['avg_kda'],
                        'avg_damage_dealt': updated_info['avg_damage_dealt'],
                        'avg_damage_taken': updated_info['avg_damage_taken'],
                        'avg_healing': updated_info['avg_healing'],
                        'avg_cc_score': updated_info.get('avg_cc_score', 0)
                    })
                else:
                    # 갱신 실패 시 기존 데이터 사용
                    updated_players.append(player)

            # 팀 밸런싱
            team1, team2 = TeamBalancer.balance_teams(updated_players)
            
            # 결과 임베드 생성 및 전송
            embed = self.create_team_embed(team1, team2)
            await interaction.followup.send(embed=embed)
            view.stop()

        select.callback = select_callback
        view.add_item(select)
        
        embed = discord.Embed(
            title="게임 생성",
            description=f"참가할 {player_count}명의 플레이어를 선택해주세요.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(GameCommands(bot))