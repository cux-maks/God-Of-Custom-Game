import mysql.connector
from mysql.connector import pooling, Error as MySQLError
import os
from typing import Dict, Optional, Tuple, List
import logging
from datetime import datetime
import asyncio
from utils.logging_config import setup_logger

class DatabaseService:
    def __init__(self):
        # 데이터베이스 연결 설정
        self.db_config = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "bot_user"),
            "password": os.getenv("MYSQL_PASSWORD", "bot_password"),
            "database": os.getenv("MYSQL_DATABASE", "god_of_custom_game"),
            "pool_name": "mypool",
            "pool_size": 5,
            "pool_reset_session": True
        }
        

        # 로깅 설정
        self.logger = setup_logger('database_service', 'database.log')

        # 커넥션 풀 생성
        self._create_pool()

    def _create_pool(self):
        """커넥션 풀 생성"""
        try:
            self.connection_pool = mysql.connector.pooling.MySQLConnectionPool(**self.db_config)
        except MySQLError as e:
            self.logger.error(f"커넥션 풀 생성 실패: {str(e)}")
            raise

    def get_connection(self):
        """커넥션 풀에서 연결 가져오기"""
        try:
            return self.connection_pool.get_connection()
        except MySQLError as e:
            self.logger.error(f"데이터베이스 연결 실패: {str(e)}")
            # 풀 재생성 시도
            self._create_pool()
            return self.connection_pool.get_connection()

    async def check_database_connection(self) -> Tuple[bool, Optional[str]]:
        """데이터베이스 연결 상태 확인"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return True, None
        except Exception as e:
            return False, str(e)
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    async def register_guild(self, guild_id: int, guild_name: str) -> Tuple[bool, Optional[str]]:
        """새로운 길드(디스코드 서버) 등록"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            sql = """
            INSERT INTO guilds (guild_id, guild_name) 
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE 
                guild_name = VALUES(guild_name),
                updated_at = CURRENT_TIMESTAMP
            """
            
            cursor.execute(sql, (guild_id, guild_name))
            conn.commit()
            
            return True, None
            
        except Exception as e:
            self.logger.error(f"길드 등록 중 오류 발생: {str(e)}")
            return False, str(e)
            
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    async def register_user(
        self, 
        guild_id: int, 
        nickname: str, 
        tag: str,
        user_data: Dict
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """새로운 사용자 등록"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 트랜잭션 시작
            conn.start_transaction()

            try:
                # 사용자 기본 정보 등록
                sql = """
                INSERT INTO users (guild_id, nickname, tag, summoner_id, puuid, account_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(sql, (
                    guild_id,
                    nickname,
                    tag,
                    user_data['summoner_id'],
                    user_data['puuid'],
                    user_data['account_id']
                ))
                
                user_id = cursor.lastrowid

                # 사용자 통계 정보 등록
                sql = """
                INSERT INTO user_stats (
                    user_id, games_played, wins, losses, 
                    avg_kda, avg_damage_dealt, avg_damage_taken,
                    avg_healing, avg_cc_score, performance_score
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(sql, (
                    user_id,
                    user_data['games_played'],
                    user_data['wins'],
                    user_data['losses'],
                    user_data['avg_kda'],
                    user_data['avg_damage_dealt'],
                    user_data['avg_damage_taken'],
                    user_data['avg_healing'],
                    user_data.get('avg_cc_score', 0),
                    user_data['performance_score']
                ))

                # 트랜잭션 커밋
                conn.commit()
                return True, None, user_id

            except Exception as e:
                # 오류 발생 시 롤백
                conn.rollback()
                raise e

        except Exception as e:
            self.logger.error(f"사용자 등록 중 오류 발생: {str(e)}")
            return False, str(e), None

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    async def get_user(
        self, 
        guild_id: int, 
        nickname: str, 
        tag: str
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """사용자 정보 조회"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)

            sql = """
            SELECT 
                u.*,
                s.*
            FROM users u
            JOIN user_stats s ON u.id = s.user_id
            WHERE u.guild_id = %s AND u.nickname = %s AND u.tag = %s
            """
            
            cursor.execute(sql, (guild_id, nickname, tag))
            user = cursor.fetchone()
            
            if not user:
                return None, "등록되지 않은 사용자입니다."
                
            return user, None

        except Exception as e:
            self.logger.error(f"사용자 조회 중 오류 발생: {str(e)}")
            return None, str(e)

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    async def update_user_stats(
        self, 
        guild_id: int, 
        nickname: str, 
        tag: str, 
        stats: Dict
    ) -> Tuple[bool, Optional[str]]:
        """사용자 통계 정보 업데이트"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 먼저 user_id 조회
            sql = "SELECT id FROM users WHERE guild_id = %s AND nickname = %s AND tag = %s"
            cursor.execute(sql, (guild_id, nickname, tag))
            result = cursor.fetchone()
            
            if not result:
                return False, "등록되지 않은 사용자입니다."
                
            user_id = result[0]

            # 통계 정보 업데이트
            sql = """
            UPDATE user_stats 
            SET 
                games_played = %s,
                wins = %s,
                losses = %s,
                avg_kda = %s,
                avg_damage_dealt = %s,
                avg_damage_taken = %s,
                avg_healing = %s,
                avg_cc_score = %s,
                performance_score = %s
            WHERE user_id = %s
            """
            
            cursor.execute(sql, (
                stats['games_played'],
                stats['wins'],
                stats['losses'],
                stats['avg_kda'],
                stats['avg_damage_dealt'],
                stats['avg_damage_taken'],
                stats['avg_healing'],
                stats.get('avg_cc_score', 0),
                stats['performance_score'],
                user_id
            ))
            
            conn.commit()
            return True, None

        except Exception as e:
            self.logger.error(f"통계 업데이트 중 오류 발생: {str(e)}")
            return False, str(e)

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    async def get_all_users(self, guild_id: int) -> Tuple[List[Dict], Optional[str]]:
        """길드의 모든 사용자 목록 조회"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)

            sql = """
            SELECT 
                u.nickname,
                u.tag,
                u.registered_at,
                u.last_updated,
                s.*
            FROM users u
            JOIN user_stats s ON u.id = s.user_id
            WHERE u.guild_id = %s
            ORDER BY u.nickname
            """
            
            cursor.execute(sql, (guild_id,))
            users = cursor.fetchall()
            
            return users, None

        except Exception as e:
            self.logger.error(f"사용자 목록 조회 중 오류 발생: {str(e)}")
            return [], str(e)

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    async def delete_user(
        self, 
        guild_id: int, 
        nickname: str, 
        tag: str
    ) -> Tuple[bool, Optional[str]]:
        """사용자 삭제"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 트랜잭션 시작
            conn.start_transaction()

            try:
                # 먼저 user_id 조회
                sql = "SELECT id FROM users WHERE guild_id = %s AND nickname = %s AND tag = %s"
                cursor.execute(sql, (guild_id, nickname, tag))
                result = cursor.fetchone()
                
                if not result:
                    return False, "등록되지 않은 사용자입니다."
                    
                user_id = result[0]

                # 통계 정보 삭제
                sql = "DELETE FROM user_stats WHERE user_id = %s"
                cursor.execute(sql, (user_id,))

                # 사용자 정보 삭제
                sql = "DELETE FROM users WHERE id = %s"
                cursor.execute(sql, (user_id,))

                # 트랜잭션 커밋
                conn.commit()
                return True, None

            except Exception as e:
                # 오류 발생 시 롤백
                conn.rollback()
                raise e

        except Exception as e:
            self.logger.error(f"사용자 삭제 중 오류 발생: {str(e)}")
            return False, str(e)

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    async def check_tables_exist(self) -> Tuple[bool, Optional[str]]:
        """필요한 테이블들이 존재하는지 확인"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 테이블 존재 여부 확인
            sql = """
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_name IN ('guilds', 'users', 'user_stats')
            """
            
            cursor.execute(sql, (self.db_config['database'],))
            count = cursor.fetchone()[0]
            
            if count != 3:
                return False, "필요한 테이블이 모두 생성되지 않았습니다."
                
            return True, None

        except Exception as e:
            self.logger.error(f"테이블 확인 중 오류 발생: {str(e)}")
            return False, str(e)

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        # 여기서 필요한 정리 작업 수행
        pass