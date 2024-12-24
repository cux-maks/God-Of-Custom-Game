# 내전의 신: God Of Custom Game

디스코드 서버에서 리그 오브 레전드 내전 게임을 위한 팀 밸런싱을 도와주는 디스코드 봇입니다. 칼바람 나락(ARAM) 전적을 기반으로 최적의 팀 구성을 제안합니다.

## 주요 기능

- **유저 관리**
  - 닉네임#태그 형식으로 간편한 유저 등록
  - 등록된 유저의 전적 정보 조회 및 갱신
  - 서버별 독립적인 유저 DB 관리

- **전적 분석**
  - Riot API를 통한 실시간 전적 데이터 수집
  - KDA, 승률, 평균 딜량 등 다양한 지표 분석
  - 종합 성능 점수 산출

- **팀 밸런싱**
  - 전적 기반의 실력 지표 계산
  - 최소한의 점수 차이로 팀 자동 분배
  - 공정하고 재미있는 게임 환경 조성

## 시작하기

### 사전 요구사항

- Python 3.12 이상
- Docker & Docker Compose
- MySQL 8.0 이상
- Discord Bot Token
- Riot API Key

### 설치 방법

1. 저장소 클론
```bash
git clone https://github.com/cux-maks/god-of-custom-game.git
cd god-of-custom-game
```

2. 환경 변수 설정
```bash
# .env 파일 생성
DISCORD_TOKEN=your_discord_token_here
COMMAND_PREFIX=%
RIOT_API_KEY=your_riot_api_key_here
```

3. Docker Compose로 실행
```bash
docker-compose up -d
```

## 사용 방법

### 기본 명령어

- `%도움`: 사용 가능한 모든 명령어 목록 표시
- `%소개`: 봇 소개 및 기능 안내

### 유저 관리 명령어

- `%유저등록 [닉네임#태그]`: 새로운 유저 등록
- `%유저목록`: 서버에 등록된 모든 유저 목록 조회
- `%유저정보 [닉네임#태그]`: 특정 유저의 상세 정보 조회
- `%전적갱신 [닉네임#태그]`: 유저의 전적 정보 업데이트

### 게임 관리 명령어

- `%게임생성 [인원수]`: 새로운 게임 생성 및 팀 밸런싱

## 개발 환경 설정

1. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. 의존성 설치
```bash
pip install -r requirements.txt
```

3. 데이터베이스 초기화
```bash
docker-compose up -d mysql
```

## 기술 스택

- **Backend**: Python 3.12
- **Framework**: discord.py 2.4.0
- **Database**: MySQL 8.0
- **Infrastructure**: Docker & Docker Compose
- **API**: Riot Games API

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 감사의 말

이 프로젝트는 Riot Games의 API를 사용하며, Riot Games의 정책을 준수합니다.