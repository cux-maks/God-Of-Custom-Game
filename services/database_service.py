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

    async def save_match_record(self, user_id: int, match_data: dict) -> Tuple[bool, Optional[str]]:
        """게임 전적 데이터 저장"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 이미 저장된 매치인지 확인
            cursor.execute(
                "SELECT id FROM game_records WHERE match_id = %s AND user_id = %s",
                (match_data['match_id'], user_id)
            )
            if cursor.fetchone():
                return True, None  # 이미 저장된 매치는 성공으로 처리

            # 새로운 매치 기록 저장
            sql = """
            INSERT INTO game_records (
                match_id, user_id, game_creation, game_duration,
                champion_id, win, kills, deaths, assists,
                total_damage_dealt, total_damage_taken, total_heal,
                total_cc_score
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            cursor.execute(sql, (
                match_data['match_id'],
                user_id,
                match_data['game_creation'],
                match_data['game_duration'],
                match_data['champion_id'],
                match_data['win'],
                match_data['kills'],
                match_data['deaths'],
                match_data['assists'],
                match_data['total_damage_dealt'],
                match_data['total_damage_taken'],
                match_data['total_heal'],
                match_data['total_cc_score']
            ))

            # last_updates 테이블 업데이트
            sql = """
            INSERT INTO last_updates (user_id, last_match_time, last_match_id)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                last_match_time = GREATEST(last_match_time, VALUES(last_match_time)),
                last_match_id = CASE 
                    WHEN last_match_time < VALUES(last_match_time)
                    THEN VALUES(last_match_id)
                    ELSE last_match_id
                END
            """
            
            cursor.execute(sql, (
                user_id,
                match_data['game_creation'],
                match_data['match_id']
            ))

            conn.commit()
            return True, None

        except Exception as e:
            self.logger.error(f"매치 기록 저장 중 오류 발생: {str(e)}")
            return False, str(e)

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    async def get_last_match_time(self, user_id: int) -> Tuple[Optional[int], Optional[str]]:
        """유저의 마지막 매치 시간 조회"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT last_match_time FROM last_updates WHERE user_id = %s",
                (user_id,)
            )
            result = cursor.fetchone()
            
            return result[0] if result else None, None

        except Exception as e:
            self.logger.error(f"마지막 매치 시간 조회 중 오류 발생: {str(e)}")
            return None, str(e)

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    async def get_last_match_time(self, user_id: int) -> Tuple[Optional[int], Optional[str]]:
        """유저의 마지막 매치 시간 조회"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT last_match_time FROM last_updates WHERE user_id = %s",
                (user_id,)
            )
            result = cursor.fetchone()
            
            return result[0] if result else None, None

        except Exception as e:
            self.logger.error(f"마지막 매치 시간 조회 중 오류 발생: {str(e)}")
            return None, str(e)

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    async def update_user_stats_from_db(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """DB에 저장된 게임 기록을 기반으로 유저 통계 업데이트"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 모든 게임 데이터 집계
            sql = """
            SELECT 
                COUNT(*) as games_played,
                SUM(CASE WHEN win THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN NOT win THEN 1 ELSE 0 END) as losses,
                AVG((kills + assists) / GREATEST(deaths, 1)) as avg_kda,
                AVG(total_damage_dealt) as avg_damage_dealt,
                AVG(total_damage_taken) as avg_damage_taken,
                AVG(total_heal) as avg_healing,
                AVG(total_cc_score) as avg_cc_score
            FROM game_records
            WHERE user_id = %s
            """
            
            cursor.execute(sql, (user_id,))
            stats = cursor.fetchone()

            if not stats or not stats[0]:  # 게임 기록이 없는 경우
                return False, "게임 기록이 없습니다."

            # decimal을 float으로 변환하여 계산
            def to_float(val):
                return float(val) if val is not None else 0.0

            games_played = float(stats[0]) if stats[0] else 0
            wins = float(stats[1]) if stats[1] else 0
            avg_kda = to_float(stats[3])
            avg_damage = to_float(stats[4])
            avg_healing = to_float(stats[6])
            avg_cc_score = to_float(stats[7])

            # 성능 점수 계산
            performance_score = (
                (avg_kda * 0.3) +  # KDA
                ((wins / games_played if games_played > 0 else 0) * 0.3) +  # 승률
                ((avg_damage / 1000) * 0.2) +  # 평균 딜량
                ((avg_healing / 1000) * 0.1) +  # 평균 힐량
                ((avg_cc_score / 10) * 0.1)  # CC 점수
            )

            # user_stats 테이블 업데이트
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
                stats[0],  # games_played
                stats[1],  # wins
                stats[2],  # losses
                stats[3],  # avg_kda
                stats[4],  # avg_damage_dealt
                stats[5],  # avg_damage_taken
                stats[6],  # avg_healing
                stats[7],  # avg_cc_score
                performance_score,
                user_id
            ))

            conn.commit()
            return True, None

        except Exception as e:
            self.logger.error(f"유저 통계 업데이트 중 오류 발생: {str(e)}")
            return False, str(e)

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

