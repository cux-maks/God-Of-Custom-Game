import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# Discord 관련 설정
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '%')  # 기본값 '%'

# Riot API 관련 설정
RIOT_API_KEY = os.getenv('RIOT_API_KEY')
RIOT_API_BASE_URL = "https://kr.api.riotgames.com"
RIOT_API_ASIA_URL = "https://asia.api.riotgames.com"

# 파일 경로 설정
USER_DATA_FILE = 'user_list.json'
GAME_DATA_FILE = 'game_list.json'

# 게임 관련 상수
MAX_TEAM_SIZE = 5
MIN_PLAYERS_FOR_GAME = 2
QUEUE_TIMEOUT = 300  # 5분

# 메시지 색상 (discord.Color 값)
COLORS = {
    'SUCCESS': 0x00FF00,  # 초록색
    'ERROR': 0xFF0000,    # 빨간색
    'WARNING': 0xFFFF00,  # 노란색
    'INFO': 0x0000FF     # 파란색
}

# 이모지
EMOJIS = {
    'SUCCESS': '✅',
    'ERROR': '❌',
    'WARNING': '⚠️',
    'LOADING': '🔄',
    'GAME': '🎮',
    'CROWN': '👑',
    'TEAM_A': '🔵',
    'TEAM_B': '🔴'
}

# 메시지 템플릿
MESSAGES = {
    'GAME_CREATED': '새로운 게임이 생성되었습니다!',
    'GAME_STARTED': '게임이 시작되었습니다!',
    'GAME_CANCELLED': '게임이 취소되었습니다.',
    'NOT_ENOUGH_PLAYERS': '플레이어가 부족합니다.',
    'ALREADY_REGISTERED': '이미 등록된 사용자입니다.',
    'USER_NOT_FOUND': '등록되지 않은 사용자입니다.',
    'REGISTRATION_SUCCESS': '{nickname} 님이 성공적으로 등록되었습니다!',
    'INVALID_FORMAT': '올바른 형식이 아닙니다.'
}

# 정규식 패턴
PATTERNS = {
    'NICKNAME_TAG': r'^[\w\d\s가-힣]+#[\w\d]+$'
}