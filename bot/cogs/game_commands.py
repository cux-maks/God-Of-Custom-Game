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

        # 승률 (25%)
        winrate = (player['wins'] / player['games_played'] * 100)
        
        # KDA 점수 (20%)
        kda_score = player['avg_kda'] * 10
        
        # 딜량 점수 (20%)
        damage_score = player['avg_damage_dealt'] / 1000
        
        # 생존력 점수 (10%)
        tankiness_score = player['avg_damage_taken'] / 1000
        
        # 유틸리티 점수 (15%)
        utility_score = (
            (player['avg_healing'] / 1000) +  # 힐량
            (player.get('avg_cc_score', 0) * 2)  # CC점수
        )
        
        # 기존 performance_score 반영 (10%)
        performance_score = player['performance_score'] * 10
        
        # 종합 점수 계산
        total_score = (
            winrate * 0.25 +             # 승률 25%
            kda_score * 0.20 +           # KDA 20%
            damage_score * 0.20 +        # 딜량 20%
            tankiness_score * 0.10 +     # 생존력 10%
            utility_score * 0.15 +       # 유틸리티(힐, CC) 15%
            performance_score * 0.10     # 기존 성능점수 10%
        )
        
        return total_score

    @staticmethod
    def balance_teams(players: List[dict]) -> tuple[List[dict], List[dict]]:
        """
        종합 점수를 기준으로 최적의 팀 밸런스를 찾습니다.
        """
        import itertools

        # 각 플레이어의 종합 점수 계산
        for player in players:
            player['score'] = TeamBalancer.calculate_player_score(player)

        n = len(players)
        target_team_size = n // 2  # 목표 팀 크기
        
        min_diff = float('inf')
        best_team1 = []
        best_team2 = []

        # 가능한 모든 팀 조합을 검사
        for team1_players in itertools.combinations(players, target_team_size):
            team1_set = set(player['discord_id'] for player in team1_players)
            team2_players = [p for p in players if p['discord_id'] not in team1_set]

            team1_score = sum(p['score'] for p in team1_players)
            team2_score = sum(p['score'] for p in team2_players)
            
            # 점수 차이 계산
            score_diff = abs(team1_score - team2_score)
            
            # 더 좋은 밸런스를 찾은 경우 업데이트
            if score_diff < min_diff:
                min_diff = score_diff
                best_team1 = list(team1_players)
                best_team2 = team2_players

        # 두 팀의 점수가 비슷하도록 미세 조정
        total_adjustments = 0
        while total_adjustments < 10:  # 최대 10번까지만 시도
            improvements_made = False
            
            # 각 팀에서 한 명씩 선택해서 교체 시도
            for p1 in best_team1:
                for p2 in best_team2:
                    # 교체했을 때의 점수 차이 계산
                    curr_diff = abs(sum(p['score'] for p in best_team1) - sum(p['score'] for p in best_team2))
                    
                    # 임시로 선수 교체
                    best_team1.remove(p1)
                    best_team2.remove(p2)
                    best_team1.append(p2)
                    best_team2.append(p1)
                    
                    new_diff = abs(sum(p['score'] for p in best_team1) - sum(p['score'] for p in best_team2))
                    
                    # 교체가 도움이 되지 않으면 원상복구
                    if new_diff >= curr_diff:
                        best_team1.remove(p2)
                        best_team2.remove(p1)
                        best_team1.append(p1)
                        best_team2.append(p2)
                    else:
                        improvements_made = True
                        break
                
                if improvements_made:
                    break
            
            if not improvements_made:
                break
                
            total_adjustments += 1

        return best_team1, best_team2

class GameCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_service = UserService()

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
        user_data = await self.user_service.load_user_data()
        if not user_data:
            embed = EmbedBuilder.error(
                "등록된 사용자 없음",
                "게임 생성을 위해서는 먼저 사용자 등록이 필요합니다."
            )
            await ctx.send(embed=embed)
            return

        # 플레이어 데이터 가공
        players = []
        for nickname, data in user_data.items():
            players.append({
                'discord_id': nickname,
                'nickname': data['nickname'],
                'games_played': data['games_played'],
                'wins': data['wins'],
                'losses': data['losses'],
                'avg_kda': data['avg_kda'],
                'avg_damage_dealt': data['avg_damage_dealt'],
                'avg_damage_taken': data['avg_damage_taken'],
                'avg_healing': data['avg_healing'],
                'avg_cc_score': data.get('avg_cc_score', 0),
                'performance_score': data['performance_score']
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
                success, error_msg, updated_info = await self.user_service.update_user_stats(player['nickname'])
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
                        'avg_cc_score': updated_info.get('avg_cc_score', 0),
                        'performance_score': updated_info['performance_score']
                    })
                else:
                    # 갱신 실패 시 기존 데이터 사용
                    updated_players.append(player)

            # 팀 밸런싱
            team1, team2 = TeamBalancer.balance_teams(updated_players)
            
            # 결과 임베드 생성
            embed = discord.Embed(
                title="팀 구성 결과",
                color=discord.Color.blue()
            )
            
            team1_avg_score = sum(p['score'] for p in team1) / len(team1)
            team2_avg_score = sum(p['score'] for p in team2) / len(team2)
            
            embed.add_field(
                name="🔵 블루팀",
                value="\n".join([
                    f"• {p['nickname']} (승률: {(p['wins']/p['games_played']*100 if p['games_played'] > 0 else 0):.1f}%, "
                    f"KDA: {p['avg_kda']:.2f}, "
                    f"평균 딜량: {p['avg_damage_dealt']:,})"
                    for p in team1
                ]) + f"\n\n팀 평균 점수: {team1_avg_score:.1f}",
                inline=False
            )
            
            embed.add_field(
                name="🔴 레드팀",
                value="\n".join([
                    f"• {p['nickname']} (승률: {(p['wins']/p['games_played']*100 if p['games_played'] > 0 else 0):.1f}%, "
                    f"KDA: {p['avg_kda']:.2f}, "
                    f"평균 딜량: {p['avg_damage_dealt']:,})"
                    for p in team2
                ]) + f"\n\n팀 평균 점수: {team2_avg_score:.1f}",
                inline=False
            )
            
            score_diff = abs(team1_avg_score - team2_avg_score)
            embed.add_field(
                name="팀 밸런스",
                value=f"팀 점수 차이: {score_diff:.1f}점",
                inline=False
            )
            
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