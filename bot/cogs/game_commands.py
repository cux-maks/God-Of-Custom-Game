import discord
from discord.ext import commands
from discord import ui
from typing import List, Dict
import random
from services.user_service import UserService

class PlayerSelect(ui.Select):
    def __init__(self, players: List[dict]):
        options = [
            discord.SelectOption(
                label=player['nickname'],
                value=str(player['discord_id']),
                description=f"승률: {(player['wins'] / player['games_played'] * 100 if player['games_played'] > 0 else 0):.1f}%"
            ) for player in players
        ]
        super().__init__(
            placeholder="참가할 플레이어를 선택하세요",
            min_values=1,
            max_values=len(players),
            options=options
        )

class TeamBalancer:
    @staticmethod
    def balance_teams(players: List[dict]) -> tuple[List[dict], List[dict]]:
        """
        승률을 기준으로 팀을 밸런싱합니다.
        """
        # 승률 계산 및 정렬
        for player in players:
            player['winrate'] = (player['wins'] / player['games_played'] * 100) if player['games_played'] > 0 else 50
        
        sorted_players = sorted(players, key=lambda x: x['winrate'], reverse=True)
        team1, team2 = [], []
        
        # 지그재그로 팀 분배 (상위 승률부터 번갈아가며 분배)
        for i, player in enumerate(sorted_players):
            if i % 2 == 0:
                team1.append(player)
            else:
                team2.append(player)
        
        return team1, team2

class GameCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_service = UserService()

    @commands.command(
        name="게임생성", 
        help="인원수를 입력하여, 게임의 팀을 생성합니다.",
        usage="%게임생성 [인원수]"
    )
    async def create_game(self, ctx, player_count: int):
        if not 2 <= player_count <= 10:
            embed = discord.Embed(
                title="인원 수 오류",
                description="참가 인원은 2명에서 10명 사이여야 합니다.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        # 등록된 모든 플레이어 데이터 가져오기
        user_data = await self.user_service.load_user_data()
        if not user_data:
            embed = discord.Embed(
                title="등록된 사용자 없음",
                description="게임 생성을 위해서는 먼저 사용자 등록이 필요합니다.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        # 플레이어 데이터 가공
        players = []
        for discord_id, data in user_data.items():
            players.append({
                'discord_id': discord_id,
                'nickname': data['nickname'],
                'games_played': data['games_played'],
                'wins': data['wins'],
                'losses': data['losses']
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

            # 팀 밸런싱
            team1, team2 = TeamBalancer.balance_teams(selected_players)
            
            # 결과 임베드 생성
            embed = discord.Embed(
                title="팀 구성 결과",
                color=discord.Color.blue()
            )
            
            team1_winrate = sum(p['winrate'] for p in team1) / len(team1)
            team2_winrate = sum(p['winrate'] for p in team2) / len(team2)
            
            embed.add_field(
                name="🔵 블루팀",
                value="\n".join([f"• {p['nickname']} (승률: {p['winrate']:.1f}%)" for p in team1]) +
                      f"\n팀 평균 승률: {team1_winrate:.1f}%",
                inline=False
            )
            
            embed.add_field(
                name="🔴 레드팀",
                value="\n".join([f"• {p['nickname']} (승률: {p['winrate']:.1f}%)" for p in team2]) +
                      f"\n팀 평균 승률: {team2_winrate:.1f}%",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
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