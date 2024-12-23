import discord
from typing import List, Tuple, Optional, Union
from datetime import datetime
from .constants import COLORS, EMOJIS

class EmbedBuilder:
    @staticmethod
    def build(
        title: str,
        description: str,
        color: Union[int, discord.Color],
        emoji: str = None,
        fields: Optional[List[Tuple[str, str, bool]]] = None,
        footer: Optional[str] = None,
        footer_icon: Optional[str] = None,
        thumbnail: Optional[str] = None,
        timestamp: bool = False
    ) -> discord.Embed:
        """
        범용 임베드 생성기

        Parameters:
            title (str): 임베드 제목
            description (str): 임베드 설명
            color (Union[int, discord.Color]): 임베드 색상
            emoji (str, optional): 제목 앞에 붙일 이모지
            fields (List[Tuple[str, str, bool]], optional): (이름, 값, 인라인 여부) 형태의 필드 목록
            footer (str, optional): 푸터 텍스트
            footer_icon (str, optional): 푸터 아이콘 URL
            thumbnail (str, optional): 썸네일 이미지 URL
            timestamp (bool): 현재 시간 표시 여부
        """
        embed = discord.Embed(
            title=f"{emoji + ' ' if emoji else ''}{title}",
            description=description,
            color=color
        )
        
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
                
        if footer:
            embed.set_footer(text=footer, icon_url=footer_icon)
            
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
            
        if timestamp:
            embed.timestamp = datetime.now()
            
        return embed

    @classmethod
    def success(
        cls,
        title: str,
        description: str,
        **kwargs
    ) -> discord.Embed:
        """성공 메시지용 임베드"""
        return cls.build(
            title=title,
            description=description,
            color=COLORS['SUCCESS'],
            emoji=EMOJIS['SUCCESS'],
            **kwargs
        )
        
    @classmethod
    def error(
        cls,
        title: str,
        description: str,
        **kwargs
    ) -> discord.Embed:
        """에러 메시지용 임베드"""
        return cls.build(
            title=title,
            description=description,
            color=COLORS['ERROR'],
            emoji=EMOJIS['ERROR'],
            **kwargs
        )
        
    @classmethod
    def warning(
        cls,
        title: str,
        description: str,
        **kwargs
    ) -> discord.Embed:
        """경고 메시지용 임베드"""
        return cls.build(
            title=title,
            description=description,
            color=COLORS['WARNING'],
            emoji=EMOJIS['WARNING'],
            **kwargs
        )
        
    @classmethod
    def info(
        cls,
        title: str,
        description: str,
        **kwargs
    ) -> discord.Embed:
        """정보 메시지용 임베드"""
        return cls.build(
            title=title,
            description=description,
            color=COLORS['INFO'],
            emoji=None,
            **kwargs
        )
        
    @classmethod
    def game(
        cls,
        title: str,
        description: str,
        teams: Optional[dict] = None,
        **kwargs
    ) -> discord.Embed:
        """게임 정보용 임베드"""
        fields = kwargs.get('fields', [])
        
        if teams:
            # A팀 정보
            team_a = teams.get('team_a', [])
            team_a_text = "\n".join([f"• {player}" for player in team_a]) or "플레이어 없음"
            fields.append((
                f"{EMOJIS['TEAM_A']} A팀",
                team_a_text,
                True
            ))
            
            # B팀 정보
            team_b = teams.get('team_b', [])
            team_b_text = "\n".join([f"• {player}" for player in team_b]) or "플레이어 없음"
            fields.append((
                f"{EMOJIS['TEAM_B']} B팀",
                team_b_text,
                True
            ))
            
        kwargs['fields'] = fields
        
        return cls.build(
            title=title,
            description=description,
            color=COLORS['INFO'],
            emoji=EMOJIS['GAME'],
            **kwargs
        )

# 사용 예시:
"""
# 성공 메시지
embed = EmbedBuilder.success(
    "등록 완료",
    "성공적으로 등록되었습니다!",
    fields=[
        ("닉네임", "플레이어#KR1", True),
        ("등록일", "2024-03-23", True)
    ],
    footer="게임에 참여할 준비가 완료되었습니다!",
    timestamp=True
)

# 게임 정보
embed = EmbedBuilder.game(
    "내전 매칭",
    "팀이 구성되었습니다!",
    teams={
        'team_a': ['플레이어1', '플레이어2'],
        'team_b': ['플레이어3', '플레이어4']
    },
    footer="게임 시작까지 30초",
    timestamp=True
)
"""