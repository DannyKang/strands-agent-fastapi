#!/bin/bash

# Strands Agent Session Manager - Run Script
# 최신 AWS Strands Agent SDK를 사용한 실행 스크립트

set -e

echo "🧬 Starting Strands Agent Session Manager"
echo "========================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수 정의
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. 환경 확인
log_info "Checking environment..."

# 가상환경 확인 및 활성화
if [ -d "venv" ]; then
    source venv/bin/activate
    log_success "Virtual environment activated"
else
    log_warning "Virtual environment not found. Creating..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    log_success "Virtual environment created and dependencies installed"
fi

# 2. 환경 변수 로드
if [ -f ".env" ]; then
    source .env
    log_success "Environment variables loaded"
else
    log_warning ".env file not found. Using defaults"
fi

# 3. Redis 확인
log_info "Checking Redis..."

if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        log_success "Redis is running"
    else
        log_warning "Redis is not running. Attempting to start with Docker..."
        if command -v docker &> /dev/null; then
            docker run -d -p 6379:6379 --name redis redis:alpine 2>/dev/null || docker start redis 2>/dev/null || true
            sleep 2
            if redis-cli ping &> /dev/null; then
                log_success "Redis started"
            else
                log_warning "Redis start failed. Will use memory fallback"
            fi
        else
            log_warning "Docker not found. Will use memory fallback"
        fi
    fi
else
    log_warning "redis-cli not found. Will use memory fallback"
fi

# 4. Strands Agent SDK 확인
log_info "Verifying Strands Agent SDK..."

python3 -c "
try:
    from strands import Agent
    from strands.models import BedrockModel
    print('✅ Strands Agent SDK available')
except ImportError:
    print('⚠️ Strands Agent SDK not available - will run in mock mode')
"

# 5. AWS 자격 증명 확인
if [ ! -z "$AWS_ACCESS_KEY_ID" ] && [ "$AWS_ACCESS_KEY_ID" != "your-aws-access-key-id" ]; then
    log_success "AWS credentials configured"
else
    log_warning "AWS credentials not configured. Please set in .env file"
    log_warning "Strands Agent will run in mock mode"
fi

# 6. 실행 옵션 선택
echo ""
echo "🚀 Execution Options:"
echo "1. Start FastAPI Server (Web + API)"
echo "2. Run Strands Agent Test"
echo "3. Run API Test Client"
echo "4. Full Installation & Test"
echo ""

read -p "Choose option (1-4, default: 1): " choice
choice=${choice:-1}

case $choice in
    1)
        # 서버 시작
        log_info "Starting FastAPI server..."
        
        # 환경 변수 설정
        export PYTHONPATH="${PYTHONPATH}:$(pwd)"
        
        # 개발 모드 확인
        if [ "${DEVELOPMENT_MODE:-true}" = "true" ]; then
            log_info "Running in development mode with auto-reload"
            RELOAD_FLAG="--reload"
        else
            log_info "Running in production mode"
            RELOAD_FLAG=""
        fi
        
        # 포트 설정
        PORT=${PORT:-8000}
        HOST=${HOST:-0.0.0.0}
        
        echo ""
        echo "🌐 Server Information:"
        echo "   Web Interface: http://localhost:${PORT}"
        echo "   API Documentation: http://localhost:${PORT}/docs"
        echo "   Health Check: http://localhost:${PORT}/health"
        echo ""
        echo "🤖 Strands Agent Configuration:"
        echo "   Framework: AWS Strands Agent SDK"
        echo "   Model Provider: ${STRANDS_MODEL_PROVIDER:-bedrock}"
        echo "   Model ID: ${STRANDS_MODEL_ID:-anthropic.claude-3-5-sonnet-20241022-v2:0}"
        echo "   Region: ${STRANDS_REGION:-ap-northeast-2}"
        echo ""
        log_info "Starting server on http://${HOST}:${PORT}"
        
        # 서버 실행
        exec python3 -m uvicorn main:app \
            --host "$HOST" \
            --port "$PORT" \
            --log-level info \
            $RELOAD_FLAG
        ;;
        
    2)
        log_info "Running Strands Agent test..."
        if [ -f "strands_example.py" ]; then
            python3 strands_example.py
        else
            log_error "strands_example.py not found"
            exit 1
        fi
        ;;
        
    3)
        log_info "Running API test client..."
        if [ -f "test_client.py" ]; then
            echo ""
            echo "Test Options:"
            echo "1. Full demo"
            echo "2. Simple test"
            read -p "Choose test type (1-2, default: 1): " test_choice
            test_choice=${test_choice:-1}
            
            if [ "$test_choice" = "2" ]; then
                python3 test_client.py simple
            else
                python3 test_client.py
            fi
        else
            log_error "test_client.py not found"
            exit 1
        fi
        ;;
        
    4)
        log_info "Running full installation and test..."
        if [ -f "install_and_test.sh" ]; then
            ./install_and_test.sh
        else
            log_error "install_and_test.sh not found"
            exit 1
        fi
        ;;
        
    *)
        log_error "Invalid choice. Starting FastAPI server..."
        exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
        ;;
esac
