#!/bin/bash

# 서버 시작 및 테스트 실행 스크립트

echo "=== FastAPI 서버 시작 및 테스트 실행 ==="

# 가상환경 활성화
source venv/bin/activate

# 기존 서버 프로세스 종료
echo "기존 서버 프로세스를 종료합니다..."
pkill -f "uvicorn main:app" 2>/dev/null || true

# 서버를 백그라운드에서 시작
echo "FastAPI 서버를 백그라운드에서 시작합니다..."
nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload > server.log 2>&1 &
SERVER_PID=$!

# 서버가 시작될 때까지 대기
echo "서버 시작을 기다리는 중..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ 서버가 성공적으로 시작되었습니다!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ 서버 시작 시간 초과"
        kill $SERVER_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

echo ""
echo "=== 테스트 옵션 ==="
echo "1. 전체 데모 실행"
echo "2. 간단한 테스트 실행"
echo "3. 서버만 실행 (테스트 없음)"
echo ""

read -p "선택하세요 (1-3, 기본값: 1): " choice
choice=${choice:-1}

case $choice in
    1)
        echo "전체 데모를 실행합니다..."
        python test_client.py
        ;;
    2)
        echo "간단한 테스트를 실행합니다..."
        python test_client.py simple
        ;;
    3)
        echo "서버만 실행합니다. 종료하려면 Ctrl+C를 누르세요."
        echo "서버 주소: http://localhost:8000"
        echo "API 문서: http://localhost:8000/docs"
        wait $SERVER_PID
        ;;
    *)
        echo "잘못된 선택입니다. 전체 데모를 실행합니다..."
        python test_client.py
        ;;
esac

# 테스트 완료 후 서버 종료 여부 확인
if [ "$choice" != "3" ]; then
    echo ""
    read -p "테스트가 완료되었습니다. 서버를 종료하시겠습니까? (Y/n): " stop_server
    stop_server=${stop_server:-Y}
    
    if [[ "$stop_server" =~ ^[Yy]$ ]]; then
        echo "서버를 종료합니다..."
        kill $SERVER_PID 2>/dev/null || true
        echo "✅ 서버가 종료되었습니다."
    else
        echo "서버가 계속 실행됩니다."
        echo "서버 주소: http://localhost:8000"
        echo "수동으로 종료하려면: kill $SERVER_PID"
    fi
fi