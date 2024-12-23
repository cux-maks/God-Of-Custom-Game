@echo off
chcp 65001>nul

echo === Checking deployment requirements... ===

if not exist logs (
    echo Creating logs directory...
    mkdir logs
)

if not exist .env (
    echo Creating template .env file...
    echo DISCORD_TOKEN=your_discord_token_here>.env
    echo COMMAND_PREFIX=%%>>.env
    echo RIOT_API_KEY=your_riot_api_key_here>>.env
    echo Please update the .env file with your actual tokens and try again.
    pause
    exit /b 1
)

echo Checking Docker status...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Docker is not running. Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo Stopping previous containers...
docker-compose down

echo Building new Docker image...
docker-compose build --no-cache

echo Starting containers...
docker-compose up -d

if %errorlevel% neq 0 (
    echo Error: Deployment failed!
    pause
    exit /b 1
) else (
    echo Success: Deployment completed!
    echo Showing logs... Press Ctrl+C to exit
    timeout /t 3 >nul
    docker-compose logs -f
)