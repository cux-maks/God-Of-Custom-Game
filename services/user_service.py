import logging
from typing import Dict, Optional, Tuple, List
from .riot_service import RiotService
from .database_service import DatabaseService
from utils.logging_config import setup_logger

class UserService:
    def __init__(self):
        self.riot_service = RiotService()
        self.db_service = DatabaseService()
        
        # 로깅 설정
        self.logger = setup_logger(__name__, 'commands.log')


    async def register_user(self, guild_id: int, guild_name: str, nickname_tag: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """새로운 유저 등록"""
        try:
            # 길드 등록
            success, error = await self.db_service.register_guild(guild_id, guild_name)
            if error:
                return False, f"길드 등록 실패: {error}", None

            # 닉네임과 태그 분리
            try:
                nickname, tag = nickname_tag.split('#')
            except ValueError:
                return False, "올바른 닉네임 형식이 아닙니다. (닉네임#태그)", None
            
            # 이미 등록된 유저인지 확인
            existing_user, _ = await self.db_service.get_user(guild_id, nickname, tag)
            if existing_user:
                return False, "이미 등록된 사용자입니다.", None
            
            # Riot API로 유저 정보 및 전적 분석 (last_match_time=None으로 전체 데이터 가져오기)
            basic_info, error, new_matches = await self.riot_service.analyze_aram_performance(nickname, tag)
            if error:
                return False, error, None
            if not basic_info:
                return False, "게임 데이터를 분석할 수 없습니다.", None

            # 기본 유저 정보로 새 유저 등록 (초기 통계는 0으로)
            success, error, user_id = await self.db_service.register_user(
                guild_id=guild_id,
                nickname=nickname,
                tag=tag,
                user_data={
                    **basic_info,
                    'games_played': 0,
                    'wins': 0,
                    'losses': 0,
                    'avg_kda': 0.0,
                    'avg_damage_dealt': 0,
                    'avg_damage_taken': 0,
                    'avg_healing': 0,
                    'performance_score': 0.0
                }
            )
            
            if not success:
                return False, f"사용자 등록 실패: {error}", None

            # 새로운 매치 데이터 저장
            for match_data in new_matches:
                success, error = await self.db_service.save_match_record(user_id, match_data)
                if not success:
                    self.logger.error(f"매치 저장 실패: {error}")

            # 전체 통계 계산
            success, error = await self.db_service.update_user_stats_from_db(user_id)
            if not success:
                return False, error, None

            # 등록된 유저 정보 조회
            user_info, error = await self.db_service.get_user(guild_id, nickname, tag)
            if error:
                return False, f"사용자 정보 조회 실패: {error}", None
                
            return True, None, user_info
                
        except Exception as e:
            self.logger.error(f"유저 등록 중 오류 발생: {str(e)}")
            return False, f"유저 등록 중 오류가 발생했습니다: {str(e)}", None

    async def delete_user(self, guild_id: int, nickname_tag: str) -> Tuple[bool, Optional[str]]:
        """유저 삭제"""
        try:
            nickname, tag = nickname_tag.split('#')
            return await self.db_service.delete_user(guild_id, nickname, tag)
            
        except ValueError:
            return False, "올바른 닉네임 형식이 아닙니다. (닉네임#태그)"
        except Exception as e:
            self.logger.error(f"유저 삭제 중 오류 발생: {str(e)}")
            return False, f"유저 삭제 중 오류가 발생했습니다: {str(e)}"

    async def get_user(self, guild_id: int, nickname_tag: str) -> Tuple[Optional[Dict], Optional[str]]:
        """유저 정보 조회"""
        try:
            nickname, tag = nickname_tag.split('#')
            return await self.db_service.get_user(guild_id, nickname, tag)
            
        except ValueError:
            return None, "올바른 닉네임 형식이 아닙니다. (닉네임#태그)"
        except Exception as e:
            self.logger.error(f"유저 조회 중 오류 발생: {str(e)}")
            return None, f"유저 조회 중 오류가 발생했습니다: {str(e)}"

    async def get_all_users(self, guild_id: int) -> Tuple[List[Dict], Optional[str]]:
        """길드의 모든 유저 목록 조회"""
        try:
            return await self.db_service.get_all_users(guild_id)
        except Exception as e:
            self.logger.error(f"유저 목록 조회 중 오류 발생: {str(e)}")
            return [], f"유저 목록 조회 중 오류가 발생했습니다: {str(e)}"

    async def update_user_match_history(self, guild_id: int, nickname: str, tag: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """유저의 매치 히스토리 업데이트"""
        try:
            # 먼저 user_id 조회
            user_info, error = await self.db_service.get_user(guild_id, nickname, tag)
            if error:
                return False, error, None

            # 마지막 매치 시간 조회
            last_match_time, error = await self.db_service.get_last_match_time(user_info['id'])
            if error:
                return False, error, None

            # Riot API로 새로운 매치 데이터 가져오기
            _, error, new_matches = await self.riot_service.analyze_aram_performance(
                nickname, tag, last_match_time
            )
            if error:
                return False, error, None

            # 새로운 매치 데이터 저장
            for match_data in new_matches:
                success, error = await self.db_service.save_match_record(user_info['id'], match_data)
                if not success:
                    self.logger.error(f"매치 저장 실패: {error}")

            # 전체 통계 재계산
            success, error = await self.db_service.update_user_stats_from_db(user_info['id'])
            if not success:
                return False, error, None

            # 업데이트된 유저 정보 반환
            updated_user, error = await self.db_service.get_user(guild_id, nickname, tag)
            if error:
                return False, error, None

            return True, None, updated_user

        except Exception as e:
            self.logger.error(f"매치 히스토리 업데이트 중 오류 발생: {str(e)}")
            return False, f"매치 히스토리 업데이트 중 오류가 발생했습니다: {str(e)}", None

    async def update_user_stats(self, guild_id: int, nickname_tag: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """유저 전적 정보 업데이트"""
        try:
            nickname, tag = nickname_tag.split('#')
            
            # 기존 유저 확인
            existing_user, error = await self.db_service.get_user(guild_id, nickname, tag)
            if error:
                return False, error, None

            # 매치 히스토리 업데이트
            success, error, updated_user = await self.update_user_match_history(
                guild_id=guild_id,
                nickname=nickname,
                tag=tag
            )
            
            if not success:
                return False, error, None

            return True, None, updated_user

        except ValueError:
            return False, "올바른 닉네임 형식이 아닙니다. (닉네임#태그)", None
        except Exception as e:
            self.logger.error(f"유저 정보 업데이트 중 오류 발생: {str(e)}")
            return False, f"유저 정보 업데이트 중 오류가 발생했습니다: {str(e)}", None
    
    async def get_user_with_updated_stats(self, guild_id: int, nickname_tag: str) -> Tuple[Optional[Dict], Optional[str]]:
        """유저 정보 조회 (필요한 경우 전적 업데이트)"""
        try:
            nickname, tag = nickname_tag.split('#')
            
            # 기존 유저 정보 조회
            user_info, error = await self.db_service.get_user(guild_id, nickname, tag)
            if error:
                return None, error

            # 마지막 업데이트 시간 확인
            last_match_time, error = await self.db_service.get_last_match_time(user_info['id'])
            if error:
                return None, error

            # 마지막 업데이트 후 새로운 매치가 있는지 확인
            _, error, new_matches = await self.riot_service.analyze_aram_performance(
                nickname, tag, last_match_time
            )
            
            if error:
                return None, error

            # 새로운 매치가 있으면 업데이트
            if new_matches:
                success, error, updated_user = await self.update_user_match_history(
                    guild_id=guild_id,
                    nickname=nickname,
                    tag=tag
                )
                if success:
                    return updated_user, None
                return None, error

            return user_info, None

        except ValueError:
            return None, "올바른 닉네임 형식이 아닙니다. (닉네임#태그)"
        except Exception as e:
            self.logger.error(f"유저 정보 조회 중 오류 발생: {str(e)}")
            return None, f"유저 정보 조회 중 오류가 발생했습니다: {str(e)}"