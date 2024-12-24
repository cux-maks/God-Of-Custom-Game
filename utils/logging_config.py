import logging
import os

def setup_logger(name: str, log_file: str) -> logging.Logger:
    """
    개별 모듈을 위한 로거를 설정하는 유틸리티 함수
    
    Args:
        name: 로거 이름 (__name__ 사용)
        log_file: 로그 파일 경로
    """
    # logs 디렉토리가 없으면 생성
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 설정되어 있다면 추가 설정하지 않음
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.DEBUG)
    
    # 파일 핸들러 추가
    file_handler = logging.FileHandler(f'logs/{log_file}', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # 포맷터 설정
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(file_handler)
    
    return logger