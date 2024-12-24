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