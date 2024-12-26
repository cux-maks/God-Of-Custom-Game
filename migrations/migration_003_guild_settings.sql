-- migration_003_guild_settings.sql

-- guilds 테이블이 존재하지 않으면 생성
CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT PRIMARY KEY,
    guild_name VARCHAR(100) NOT NULL,
    update_notifications BOOLEAN DEFAULT TRUE,
    notification_channel VARCHAR(100) DEFAULT '게임방',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 이미 guilds 테이블이 존재하는 경우 새 컬럼 추가
ALTER TABLE guilds
ADD COLUMN IF NOT EXISTS update_notifications BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS notification_channel VARCHAR(100) DEFAULT '게임방';

-- 기존 데이터 업데이트
UPDATE guilds
SET update_notifications = TRUE,
    notification_channel = '게임방'
WHERE update_notifications IS NULL;