import re

def validate_nickname_tag(nickname_tag: str) -> bool:
    """닉네임#태그 형식 검증"""
    pattern = r'^[\w\d\s가-힣]+#[\w\d]+$'
    return bool(re.match(pattern, nickname_tag))