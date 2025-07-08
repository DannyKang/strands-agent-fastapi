#!/bin/bash

# AWS Strands Agent Session Manager 실행 스크립트

echo "=== AWS Strands Agent Session Manager ==="

# 가상환경 확인
if [ ! -d "venv" ]; then
    echo "가상환경을 생성합니다..."
    python3 -m venv venv
fi

# 가상환경 활성화
echo "가상환경을 활성화합니다..."
source venv/bin/activate

# 의존성 설치
echo "의존성을 설치합니다..."
pip install -r requirements.txt

# Strands Agent SDK 설치 확인
echo "Strands Agent SDK 설치를 확인합니다..."
if ! python -c "import strands" 2>/dev/null; then
    echo "⚠️  Strands Agent SDK가 설치되지 않았습니다."
    echo "다음 명령어로 설치를 시도합니다:"
    echo "pip install strands-agents strands-agents-tools"
    
    # 최신 버전 설치 시도
    pip install strands-agents strands-agents-tools
    
    if ! python -c "import strands" 2>/dev/null; then
        echo "⚠️  Strands Agent SDK 설치에 실패했습니다."
        echo "Mock 모드로 실행됩니다."
    else
        echo "✅ Strands Agent SDK가 성공적으로 설치되었습니다."
    fi
else
    echo "✅ Strands Agent SDK가 이미 설치되어 있습니다."
fi

# Redis 실행 확인
echo "Redis 연결을 확인합니다..."
# Docker Redis 컨테이너 확인
if docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -q "6379"; then
    echo "✅ Docker Redis가 정상적으로 실행 중입니다."
elif redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis가 정상적으로 실행 중입니다."
else
    echo "⚠️  Redis가 실행되지 않았습니다."
    echo "Redis를 설치하고 실행하세요:"
    echo "  macOS: brew install redis && brew services start redis"
    echo "  Ubuntu: sudo apt install redis-server && sudo systemctl start redis"
    echo "  또는 Docker로 실행: docker run -d -p 6379:6379 redis:alpine"
    echo ""
    echo "Redis 없이도 실행할 수 있지만 세션 저장 기능이 제한됩니다."
fi

# 환경변수 파일 확인
if [ ! -f ".env" ]; then
    echo "⚠️  .env 파일이 없습니다. 기본 설정으로 실행합니다."
else
    echo "✅ 환경 설정 파일을 찾았습니다."
fi

# AWS 자격 증명 확인
echo "AWS 자격 증명을 확인합니다..."
if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "✅ AWS 환경 변수가 설정되어 있습니다."
elif aws sts get-caller-identity > /dev/null 2>&1; then
    echo "✅ AWS CLI 자격 증명이 설정되어 있습니다."
else
    echo "⚠️  AWS 자격 증명이 설정되지 않았습니다."
    echo "Bedrock 모델을 사용하려면 AWS 자격 증명이 필요합니다:"
    echo "  1. .env 파일에 AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY 설정"
    echo "  2. 또는 'aws configure' 명령어 사용"
    echo "  3. Amazon Bedrock에서 Claude 3.7 Sonnet 모델 액세스 활성화"
    echo ""
    echo "자격 증명 없이도 Mock 모드로 실행됩니다."
fi

echo ""
echo "=== 시작 옵션 ==="
echo "1. FastAPI 서버 시작"
echo "2. Strands Agent 독립 테스트"
echo "3. API 테스트 클라이언트 실행"
echo ""

read -p "선택하세요 (1-3, 기본값: 1): " choice
choice=${choice:-1}

case $choice in
    1)
        echo "FastAPI 서버를 시작합니다..."
        echo "서버 주소: http://localhost:8000"
        echo "API 문서: http://localhost:8000/docs"
        echo "종료하려면 Ctrl+C를 누르세요."
        echo ""
        uvicorn main:app --host 0.0.0.0 --port 8000 --reload
        ;;
    2)
        echo "Strands Agent 독립 테스트를 실행합니다..."
        python strands_example.py
        ;;
    3)
        echo "API 테스트 클라이언트를 실행합니다..."
        echo "1. 전체 데모"
        echo "2. 간단한 테스트"
        read -p "선택하세요 (1-2, 기본값: 1): " test_choice
        test_choice=${test_choice:-1}
        
        if [ "$test_choice" = "2" ]; then
            python test_client.py simple
        else
            python test_client.py
        fi
        ;;
    *)
        echo "잘못된 선택입니다. FastAPI 서버를 시작합니다..."
        uvicorn main:app --host 0.0.0.0 --port 8000 --reload
        ;;
esac
