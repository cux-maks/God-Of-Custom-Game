-- last_updates 테이블 생성
CREATE TABLE IF NOT EXISTS last_updates (
    user_id INT PRIMARY KEY,
    last_match_time BIGINT NOT NULL,            -- 마지막으로 분석한 게임의 시간
    last_match_id VARCHAR(20) NOT NULL,         -- 마지막으로 분석한 게임의 ID
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- game_records 테이블 존재 확인 및 생성
CREATE TABLE IF NOT EXISTS game_records (
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

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_match_id ON game_records(match_id);
CREATE INDEX IF NOT EXISTS idx_user_game_creation ON game_records(user_id, game_creation);