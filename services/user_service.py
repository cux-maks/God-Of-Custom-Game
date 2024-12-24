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
            # 길드 등록 (없으면 생성)
            success, error = await self.db_service.register_guild(guild_id, guild_name)
            if not success:
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
            
            # Riot API로 유저 정보 및 전적 분석
            performance_data, error = await self.riot_service.analyze_aram_performance(nickname, tag)
            if error:
                return False, error, None
            if not performance_data:
                return False, "게임 데이터를 분석할 수 없습니다.", None
                
            # 새 유저 등록
            success, error, user_id = await self.db_service.register_user(
                guild_id=guild_id,
                nickname=nickname,
                tag=tag,
                user_data=performance_data
            )
            
            if not success:
                return False, f"사용자 등록 실패: {error}", None
                
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

    async def update_user_stats(self, guild_id: int, nickname_tag: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """유저 전적 정보 업데이트"""
        try:
            nickname, tag = nickname_tag.split('#')
            
            # 기존 유저 확인
            existing_user, error = await self.db_service.get_user(guild_id, nickname, tag)
            if error:
                return False, error, None
                
            # Riot API로 최신 전적 정보 가져오기
            performance_data, error = await self.riot_service.analyze_aram_performance(nickname, tag)
            if error:
                return False, error, None
            if not performance_data:
                return False, "게임 데이터를 분석할 수 없습니다.", None
                
            # 통계 정보 업데이트
            success, error = await self.db_service.update_user_stats(
                guild_id=guild_id,
                nickname=nickname,
                tag=tag,
                stats=performance_data
            )
            
            if not success:
                return False, error, None
                
            # 업데이트된 유저 정보 조회
            updated_user, error = await self.db_service.get_user(guild_id, nickname, tag)
            if error:
                return False, f"업데이트된 정보 조회 실패: {error}", None
                
            return True, None, updated_user
            
        except ValueError:
            return False, "올바른 닉네임 형식이 아닙니다. (닉네임#태그)", None
        except Exception as e:
            self.logger.error(f"유저 정보 업데이트 중 오류 발생: {str(e)}")
            return False, f"유저 정보 업데이트 중 오류가 발생했습니다: {str(e)}", None