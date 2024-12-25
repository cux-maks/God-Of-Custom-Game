-- 서버 정보 테이블
CREATE TABLE guilds (
    guild_id BIGINT PRIMARY KEY,
    guild_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 사용자 정보 테이블 
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    nickname VARCHAR(50) NOT NULL,
    tag VARCHAR(10) NOT NULL,
    summoner_id VARCHAR(100) NOT NULL,
    puuid VARCHAR(100) NOT NULL,
    account_id VARCHAR(100) NOT NULL,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id),
    UNIQUE KEY guild_nickname_tag (guild_id, nickname, tag)
);

-- 사용자 통계 테이블
CREATE TABLE user_stats (
    user_id INT NOT NULL,
    games_played INT DEFAULT 0,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    avg_kda DECIMAL(10,2) DEFAULT 0.00,
    avg_damage_dealt INT DEFAULT 0,
    avg_damage_taken INT DEFAULT 0,  
    avg_healing INT DEFAULT 0,
    avg_cc_score DECIMAL(10,2) DEFAULT 0.00,
    performance_score DECIMAL(10,2) DEFAULT 0.00,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 인덱스 추가
CREATE INDEX idx_guild_id ON users(guild_id);
CREATE INDEX idx_user_stats ON user_stats(user_id);

-- 게임 기록 테이블
CREATE TABLE game_records (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    match_id VARCHAR(20) NOT NULL,              -- Riot match ID
    user_id INT NOT NULL,                       -- users 테이블의 FK
    game_creation BIGINT NOT NULL,              -- 게임 생성 시간 (Unix timestamp)
    game_duration INT NOT NULL,                 -- 게임 진행 시간 (초)
    champion_id INT NOT NULL,                   -- 사용한 챔피언 ID
    win BOOLEAN NOT NULL,                       -- 승리 여부
    kills INT NOT NULL,
    deaths INT NOT NULL,
    assists INT NOT NULL,
    total_damage_dealt INT NOT NULL,            -- 챔피언에게 가한 피해량
    total_damage_taken INT NOT NULL,            -- 받은 피해량
    total_heal INT NOT NULL,                    -- 힐량
    total_cc_score FLOAT NOT NULL,              -- CC 점수
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE KEY unique_match_user (match_id, user_id)
);

-- 마지막 전적 갱신 시점 테이블 (API 호출 최적화용)
CREATE TABLE last_updates (
    user_id INT PRIMARY KEY,
    last_match_time BIGINT NOT NULL,            -- 마지막으로 분석한 게임의 시간
    last_match_id VARCHAR(20) NOT NULL,         -- 마지막으로 분석한 게임의 ID
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 인덱스 추가
CREATE INDEX idx_match_id ON game_records(match_id);
CREATE INDEX idx_user_game_creation ON game_records(user_id, game_creation);