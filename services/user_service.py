import json
from datetime import datetime
from typing import Dict, Optional, Tuple
import logging
from .riot_service import RiotService

class UserService:
    def __init__(self, file_path: str = 'user_list.json'):
        self.file_path = file_path
        self.riot_service = RiotService()
        
        # 로깅 설정
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        fh = logging.FileHandler('user_service.log', encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

    async def load_user_data(self) -> Dict:
        """유저 데이터 파일 로드"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON 파일 파싱 오류: {str(e)}")
                    return {}
        except FileNotFoundError:
            self.logger.info(f"유저 데이터 파일이 없어 새로 생성합니다: {self.file_path}")
            return {}
        except Exception as e:
            self.logger.error(f"파일 로드 중 오류 발생: {str(e)}")
            return {}

    async def save_user_data(self, user_data: Dict) -> bool:
        """유저 데이터 저장"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            self.logger.error(f"데이터 저장 중 오류 발생: {str(e)}")
            return False

    async def register_user(self, nickname_tag: str, discord_name: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """새로운 유저 등록"""
        try:
            user_data = await self.load_user_data()
            
            # 이미 등록된 닉네임 체크
            for user in user_data.values():
                if user['nickname'] == nickname_tag:
                    return False, "이미 등록된 닉네임입니다.", None
                
            # 닉네임과 태그 분리
            try:
                nickname, tag = nickname_tag.split('#')
            except ValueError:
                return False, "올바른 닉네임 형식이 아닙니다. (닉네임#태그)", None
            
            # Riot API로 유저 정보 및 전적 분석
            performance_data, error = await self.riot_service.analyze_aram_performance(nickname, tag)
            if error:
                return False, error, None
            if not performance_data:
                return False, "게임 데이터를 분석할 수 없습니다.", None
                
            # 새 유저 정보 생성 (필수 정보만 저장)
            user_info = {
                "nickname": nickname_tag,
                "registered_at": datetime.now().isoformat(),
                "summoner_id": performance_data['summoner_id'],
                "puuid": performance_data['puuid'],
                "account_id": performance_data['account_id'],
                "games_played": performance_data['games_played'],
                "wins": performance_data['wins'],
                "losses": performance_data['games_played'] - performance_data['wins'],
                "avg_kda": performance_data['avg_kda'],
                "avg_damage_dealt": performance_data['avg_damage_dealt'],
                "avg_damage_taken": performance_data['avg_damage_taken'],
                "avg_healing": performance_data['avg_healing'],
                "avg_cc_score": performance_data.get('avg_cc_score', 0),
                "performance_score": performance_data['performance_score'],
                "last_updated": datetime.now().isoformat()
            }
            
            user_data[nickname_tag] = user_info
            
            if not await self.save_user_data(user_data):
                return False, "데이터 저장 중 오류가 발생했습니다.", None
                
            return True, None, user_info
            
        except Exception as e:
            self.logger.error(f"유저 등록 중 오류 발생: {str(e)}")
            return False, f"유저 등록 중 오류가 발생했습니다: {str(e)}", None

    async def delete_user(self, nickname_tag: str) -> Tuple[bool, Optional[str]]:
        """유저 삭제"""
        try:
            user_data = await self.load_user_data()
            
            if nickname_tag not in user_data:
                return False, "등록되지 않은 유저입니다."
                
            # 유저 삭제
            del user_data[nickname_tag]
            
            if not await self.save_user_data(user_data):
                return False, "데이터 저장 중 오류가 발생했습니다."
            
            return True, None
            
        except Exception as e:
            self.logger.error(f"유저 삭제 중 오류 발생: {str(e)}")
            return False, f"유저 삭제 중 오류가 발생했습니다: {str(e)}"

    async def get_user(self, nickname_tag: str) -> Tuple[Optional[Dict], Optional[str]]:
        """유저 정보 조회"""
        try:
            user_data = await self.load_user_data()
            user = user_data.get(nickname_tag)
            
            if not user:
                return None, "등록되지 않은 유저입니다."
                
            return user, None
            
        except Exception as e:
            self.logger.error(f"유저 조회 중 오류 발생: {str(e)}")
            return None, f"유저 조회 중 오류가 발생했습니다: {str(e)}"

    async def find_user_by_nickname(self, nickname_tag: str) -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
        """닉네임으로 유저 찾기"""
        try:
            user_data = await self.load_user_data()
            user = user_data.get(nickname_tag)
            
            if not user:
                return None, None, "등록되지 않은 유저입니다."
                
            return nickname_tag, user, None
            
        except Exception as e:
            self.logger.error(f"유저 검색 중 오류 발생: {str(e)}")
            return None, None, f"유저 검색 중 오류가 발생했습니다: {str(e)}"

    async def update_user_stats(self, nickname_tag: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """유저 전적 정보 업데이트"""
        try:
            user_data = await self.load_user_data()
            
            if nickname_tag not in user_data:
                return False, "등록되지 않은 유저입니다.", None
                
            # 닉네임에서 태그 분리
            nickname = nickname_tag.split('#')[0]
            
            # Riot API로 최신 전적 정보 가져오기
            performance_data, error = await self.riot_service.analyze_aram_performance(nickname)
            if error:
                return False, error, None
            if not performance_data:
                return False, "게임 데이터를 분석할 수 없습니다.", None
                
            # 유저 정보 업데이트
            user_data[nickname_tag].update({
                "games_played": performance_data['games_played'],
                "wins": performance_data['wins'],
                "losses": performance_data['games_played'] - performance_data['wins'],
                "avg_kda": performance_data['avg_kda'],
                "avg_damage_dealt": performance_data['avg_damage_dealt'],
                "avg_damage_taken": performance_data['avg_damage_taken'],
                "avg_healing": performance_data['avg_healing'],
                "avg_cc_score": performance_data.get('avg_cc_score', 0),
                "performance_score": performance_data['performance_score'],
                "last_updated": datetime.now().isoformat()
            })
            
            if not await self.save_user_data(user_data):
                return False, "데이터 저장 중 오류가 발생했습니다.", None
                
            return True, None, user_data[nickname_tag]
            
        except Exception as e:
            self.logger.error(f"유저 정보 업데이트 중 오류 발생: {str(e)}")
            return False, f"유저 정보 업데이트 중 오류가 발생했습니다: {str(e)}", None