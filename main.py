from bot.bot import run_bot
import logging
import os

def setup_logging():
    # logs 디렉토리가 없으면 생성
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # 기본 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/bot.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

if __name__ == "__main__":
    setup_logging()
    run_bot()