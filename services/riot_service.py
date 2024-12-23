import aiohttp
from typing import Optional, Dict, List, Tuple
import asyncio
from datetime import datetime, timedelta
import logging
from urllib import parse
from utils.constants import RIOT_API_KEY, RIOT_API_BASE_URL, RIOT_API_ASIA_URL
from utils.rate_limiter import RateLimiter

class RiotService:
    def __init__(self):
        if not RIOT_API_KEY:
            raise ValueError("RIOT_API_KEY가 설정되지 않았습니다.")
            
        self.api_key = RIOT_API_KEY
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://developer.riotgames.com",
            "X-Riot-Token": self.api_key
        }
        
        # Rate Limiter 초기화
        self.rate_limiter = RateLimiter(
            requests_per_second=20,
            requests_per_two_minutes=100
        )
        
        # 로깅 설정
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        fh = logging.FileHandler('riot_api.log', encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

    async def _make_request(self, url: str) -> Tuple[Optional[Dict], Optional[str]]:
        """API 요청 실행"""
        try:
            # Rate limit 체크
            await self.rate_limiter.acquire()
            
            self.logger.debug(f"API 요청: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json(), None
                    
                    error_msg = None
                    try:
                        error_data = await response.json()
                        error_msg = error_data.get('status', {}).get('message', 'Unknown error')
                    except:
                        error_msg = await response.text()
                    
                    if response.status == 404:
                        return None, "소환사를 찾을 수 없습니다."
                    elif response.status == 403:
                        return None, "API 키가 만료되었거나 유효하지 않습니다."
                    elif response.status == 429:
                        retry_after = response.headers.get('Retry-After', '120')
                        return None, f"API 호출 한도를 초과했습니다. {retry_after}초 후에 다시 시도해주세요."
                    elif response.status >= 500:
                        return None, "라이엇 서버에 문제가 발생했습니다. 잠시 후 다시 시도해주세요."
                    else:
                        return None, f"API 오류 (상태 코드: {response.status}): {error_msg}"
                        
        except aiohttp.ClientError as e:
            self.logger.error(f"네트워크 오류: {str(e)}")
            return None, "네트워크 연결에 실패했습니다."
        except Exception as e:
            self.logger.error(f"예상치 못한 오류: {str(e)}")
            return None, f"예상치 못한 오류가 발생했습니다: {str(e)}"

    async def get_account_by_riot_id(self, game_name: str, tag_line: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Riot ID로 계정 정보 조회"""
        encoded_name = parse.quote(game_name)
        url = f"{RIOT_API_ASIA_URL}/riot/account/v1/accounts/by-riot-id/{encoded_name}/{tag_line}"
        return await self._make_request(url)

    async def get_summoner_by_puuid(self, puuid: str) -> Tuple[Optional[Dict], Optional[str]]:
        """PUUID로 소환사 정보 조회"""
        url = f"{RIOT_API_BASE_URL}/lol/summoner/v4/summoners/by-puuid/{puuid}"
        return await self._make_request(url)

    async def get_aram_matches(self, puuid: str, start_time: Optional[int] = None) -> Tuple[List[str], Optional[str]]:
        """ARAM 매치 목록 조회"""
        if not start_time:
            # 최근 30일의 데이터만 조회
            start_time = int((datetime.now() - timedelta(days=30)).timestamp())

        url = (
            f"{RIOT_API_ASIA_URL}/lol/match/v5/matches/by-puuid/{puuid}/ids"
            f"?queue=450&type=normal&start=0&count=50&startTime={start_time}"
        )
        result, error = await self._make_request(url)
        return (result if result else [], error)

    async def get_match_details(self, match_id: str) -> Tuple[Optional[Dict], Optional[str]]:
        """매치 상세 정보 조회"""
        url = f"{RIOT_API_ASIA_URL}/lol/match/v5/matches/{match_id}"
        return await self._make_request(url)

    async def analyze_aram_performance(self, game_name: str, tag_line: str) -> Tuple[Optional[Dict], Optional[str]]:
        """ARAM 게임 성능 분석"""
        try:
            # Riot ID로 계정 정보 조회
            account_info, error = await self.get_account_by_riot_id(game_name, tag_line)
            if error:
                return None, error
            if not account_info:
                return None, "계정 정보를 찾을 수 없습니다."

            # PUUID로 소환사 정보 조회
            summoner, error = await self.get_summoner_by_puuid(account_info['puuid'])
            if error:
                return None, error
            if not summoner:
                return None, "소환사 정보를 찾을 수 없습니다."

            # ARAM 매치 목록 조회
            matches, error = await self.get_aram_matches(account_info['puuid'])
            if error:
                return None, error

            if not matches:
                return {
                    'summoner_id': summoner['id'],
                    'puuid': summoner['puuid'],
                    'account_id': summoner['accountId'],
                    'summoner_level': summoner['summonerLevel'],
                    'games_played': 0,
                    'wins': 0,
                    'avg_kda': 0.0,
                    'avg_damage_dealt': 0,
                    'avg_damage_taken': 0,
                    'avg_healing': 0,
                    'performance_score': 0.0
                }, None

            total_stats = {
                'games': 0,
                'wins': 0,
                'kills': 0,
                'deaths': 0,
                'assists': 0,
                'damage_dealt': 0,
                'damage_taken': 0,
                'healing': 0,
                'cc_score': 0
            }

            # 최대 20게임까지만 분석
            processed_matches = 0
            for match_id in matches[:20]:
                match_detail, error = await self.get_match_details(match_id)
                if error:
                    self.logger.warning(f"매치 {match_id} 조회 실패: {error}")
                    continue
                if not match_detail or match_detail['info']['queueId'] != 450:  # ARAM 큐 ID 확인
                    continue

                # 참가자 정보 찾기
                participant = next(
                    (p for p in match_detail['info']['participants'] 
                     if p['puuid'] == account_info['puuid']),
                    None
                )
                if not participant:
                    continue

                processed_matches += 1
                total_stats['games'] += 1
                total_stats['wins'] += 1 if participant['win'] else 0
                total_stats['kills'] += participant['kills']
                total_stats['deaths'] += participant['deaths']
                total_stats['assists'] += participant['assists']
                total_stats['damage_dealt'] += participant['totalDamageDealtToChampions']
                total_stats['damage_taken'] += participant['totalDamageTaken']
                total_stats['healing'] += participant['totalHeal'] + participant.get('totalDamageSelfMitigated', 0)
                total_stats['cc_score'] += participant.get('timeCCingOthers', 0)

                # API 호출 제한을 위한 딜레이
                await asyncio.sleep(0.1)

            # 평균 계산
            games = total_stats['games']
            if games > 0:
                avg_kda = (total_stats['kills'] + total_stats['assists']) / max(1, total_stats['deaths'])
                performance_data = {
                    'summoner_id': summoner['id'],
                    'puuid': summoner['puuid'],
                    'account_id': summoner['accountId'],
                    'summoner_level': summoner['summonerLevel'],
                    'games_played': games,
                    'wins': total_stats['wins'],
                    'avg_kda': round(avg_kda, 2),
                    'avg_damage_dealt': round(total_stats['damage_dealt'] / games),
                    'avg_damage_taken': round(total_stats['damage_taken'] / games),
                    'avg_healing': round(total_stats['healing'] / games),
                    'avg_cc_score': round(total_stats['cc_score'] / games, 1),
                    'performance_score': round((
                        (avg_kda * 0.3) +
                        (total_stats['wins'] / games * 0.3) +
                        (total_stats['damage_dealt'] / games / 1000 * 0.2) +
                        (total_stats['healing'] / games / 1000 * 0.1) +
                        (total_stats['cc_score'] / games / 10 * 0.1)
                    ), 2)
                }
                return performance_data, None

            return None, "분석할 수 있는 ARAM 게임 데이터가 없습니다."

        except Exception as e:
            self.logger.error(f"성능 분석 중 오류 발생: {str(e)}")
            return None, f"성능 분석 중 오류가 발생했습니다: {str(e)}"