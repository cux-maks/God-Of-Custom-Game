import asyncio
from collections import deque
from datetime import datetime, timedelta
import logging

class RateLimiter:
    def __init__(self, requests_per_second: int, requests_per_two_minutes: int):
        self.requests_per_second = requests_per_second
        self.requests_per_two_minutes = requests_per_two_minutes
        
        # 초당 요청 추적
        self.second_requests = deque()
        
        # 2분당 요청 추적
        self.two_minute_requests = deque()
        
        self.logger = logging.getLogger(__name__)

    async def acquire(self) -> None:
        """Rate limit 체크 및 대기"""
        await self._clean_old_requests()
        
        while True:
            current_time = datetime.now()
            
            # 초당 제한 체크
            while (len(self.second_requests) >= self.requests_per_second and 
                   (current_time - self.second_requests[0]).total_seconds() <= 1):
                await asyncio.sleep(0.1)
                current_time = datetime.now()
                await self._clean_old_requests()
            
            # 2분 제한 체크
            while (len(self.two_minute_requests) >= self.requests_per_two_minutes and 
                   (current_time - self.two_minute_requests[0]).total_seconds() <= 120):
                wait_time = 120 - (current_time - self.two_minute_requests[0]).total_seconds()
                self.logger.warning(f"2분 제한에 도달. {wait_time:.1f}초 대기 중...")
                await asyncio.sleep(1)  # 1초마다 체크
                current_time = datetime.now()
                await self._clean_old_requests()
            
            # 모든 제한을 통과하면 요청 기록 추가
            self.second_requests.append(current_time)
            self.two_minute_requests.append(current_time)
            break

    async def _clean_old_requests(self) -> None:
        """만료된 요청 기록 제거"""
        current_time = datetime.now()
        
        # 1초 이상 지난 요청 제거
        while (self.second_requests and 
               (current_time - self.second_requests[0]).total_seconds() > 1):
            self.second_requests.popleft()
        
        # 2분 이상 지난 요청 제거
        while (self.two_minute_requests and 
               (current_time - self.two_minute_requests[0]).total_seconds() > 120):
            self.two_minute_requests.popleft()