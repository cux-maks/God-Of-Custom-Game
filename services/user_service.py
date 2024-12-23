import json
from datetime import datetime
from typing import Dict, Optional, Tuple

class UserService:
    def __init__(self, file_path: str = 'user_list.json'):
        self.file_path = file_path

    async def load_user_data(self) -> Dict:
        """유저 데이터 파일 로드"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        except FileNotFoundError:
            return {}

    async def save_user_data(self, user_data: Dict) -> None:
        """유저 데이터 저장"""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)

    async def register_user(self, nickname_tag: str, discord_name: str) -> bool:
        """새로운 유저 등록"""
        user_data = await self.load_user_data()
        
        # 이미 등록된 닉네임 체크
        for user in user_data.values():
            if user['nickname'] == nickname_tag:
                return False
            
        # 새 유저 정보 생성
        user_data[nickname_tag] = {
            "nickname": nickname_tag,
            "discord_name": discord_name,
            "registered_at": datetime.now().isoformat(),
            "games_played": 0,
            "wins": 0,
            "losses": 0
        }
        
        await self.save_user_data(user_data)
        return True

    async def delete_user(self, nickname_tag: str) -> Optional[str]:
        """유저 삭제"""
        user_data = await self.load_user_data()
        
        if nickname_tag not in user_data:
            return None
            
        # 유저 삭제
        del user_data[nickname_tag]
        await self.save_user_data(user_data)
        
        return nickname_tag

    async def get_user(self, nickname_tag: str) -> Optional[Dict]:
        """유저 정보 조회"""
        user_data = await self.load_user_data()
        return user_data.get(nickname_tag)

    async def find_user_by_nickname(self, nickname_tag: str) -> Tuple[Optional[str], Optional[Dict]]:
        """닉네임으로 유저 찾기"""
        user_data = await self.load_user_data()
        data = user_data.get(nickname_tag)
        if data:
            return nickname_tag, data
        return None, None

    async def update_user_stats(self, nickname_tag: str, won: bool) -> bool:
        """유저 게임 통계 업데이트"""
        user_data = await self.load_user_data()
        
        if nickname_tag not in user_data:
            return False
            
        user_data[nickname_tag]['games_played'] += 1
        if won:
            user_data[nickname_tag]['wins'] += 1
        else:
            user_data[nickname_tag]['losses'] += 1
            
        await self.save_user_data(user_data)
        return True