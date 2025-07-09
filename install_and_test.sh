#!/bin/bash

# Strands Agent Session Manager - Installation and Test Script
# 최신 AWS Strands Agent SDK를 사용한 설치 및 테스트

set -e

echo "🧬 AWS Strands Agent Session Manager - Installation & Test"
echo "=========================================================="

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

# Python 버전 확인
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_success "Python $PYTHON_VERSION found"
else
    log_error "Python 3 not found. Please install Python 3.10+"
    exit 1
fi

# pip 확인
if command -v pip &> /dev/null; then
    log_success "pip found"
else
    log_error "pip not found. Please install pip"
    exit 1
fi

# 2. 가상환경 설정
log_info "Setting up virtual environment..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    log_success "Virtual environment created"
else
    log_info "Virtual environment already exists"
fi

# 가상환경 활성화
source venv/bin/activate
log_success "Virtual environment activated"

# 3. 의존성 설치
log_info "Installing dependencies (including latest Strands Agent SDK)..."

# pip 업그레이드
pip install --upgrade pip

# requirements.txt 설치
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    log_success "Dependencies installed successfully"
else
    log_error "requirements.txt not found"
    exit 1
fi

# 4. Strands Agent SDK 설치 확인
log_info "Verifying Strands Agent SDK installation..."

python3 -c "
try:
    from strands import Agent
    from strands.models import BedrockModel
    from strands.tools import FunctionTool
    print('✅ Core Strands Agent SDK imported successfully')
except ImportError as e:
    print(f'❌ Core Strands Agent SDK import failed: {e}')
    exit(1)

try:
    from strands_agents_tools.web_search import WebSearchTool
    from strands_agents_tools.calculator import CalculatorTool
    print('✅ Strands Agent Tools imported successfully')
except ImportError as e:
    print(f'⚠️ Strands Agent Tools import failed: {e}')
    print('   This is optional but recommended for full functionality')
"

# 5. 환경 변수 확인
log_info "Checking environment variables..."

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        log_warning ".env file created from .env.example"
        log_warning "Please edit .env file with your AWS credentials"
    else
        log_error ".env.example file not found"
        exit 1
    fi
else
    log_success ".env file exists"
fi

# AWS 자격 증명 확인
source .env 2>/dev/null || true

if [ -z "$AWS_ACCESS_KEY_ID" ] || [ "$AWS_ACCESS_KEY_ID" = "your-aws-access-key-id" ]; then
    log_warning "AWS_ACCESS_KEY_ID not set in .env file"
    log_warning "Please set your AWS credentials in .env file"
fi

if [ -z "$AWS_SECRET_ACCESS_KEY" ] || [ "$AWS_SECRET_ACCESS_KEY" = "your-aws-secret-access-key" ]; then
    log_warning "AWS_SECRET_ACCESS_KEY not set in .env file"
    log_warning "Please set your AWS credentials in .env file"
fi

# 6. Redis 확인
log_info "Checking Redis availability..."

if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        log_success "Redis is running"
    else
        log_warning "Redis is not running"
        log_info "Starting Redis with Docker..."
        
        if command -v docker &> /dev/null; then
            # 기존 Redis 컨테이너 정리
            docker stop redis 2>/dev/null || true
            docker rm redis 2>/dev/null || true
            
            # 새 Redis 컨테이너 시작
            docker run -d -p 6379:6379 --name redis redis:alpine
            
            # Redis 시작 대기
            sleep 3
            
            if redis-cli ping &> /dev/null; then
                log_success "Redis started with Docker"
            else
                log_error "Failed to start Redis with Docker"
                exit 1
            fi
        else
            log_error "Docker not found. Please install Docker or Redis"
            exit 1
        fi
    fi
else
    log_warning "redis-cli not found"
    log_info "Installing Redis with Docker..."
    
    if command -v docker &> /dev/null; then
        docker run -d -p 6379:6379 --name redis redis:alpine
        sleep 3
        log_success "Redis started with Docker"
    else
        log_error "Docker not found. Please install Docker or Redis"
        exit 1
    fi
fi

# 7. 서버 시작
log_info "Starting Strands Agent Session Manager..."

# 백그라운드에서 서버 시작
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

# 서버 시작 대기
log_info "Waiting for server to start..."
sleep 5

# 8. 헬스 체크
log_info "Performing health check..."

HEALTH_RESPONSE=$(curl -s http://localhost:8000/health || echo "failed")

if [[ $HEALTH_RESPONSE == *"healthy"* ]]; then
    log_success "Server is healthy!"
    
    # 헬스 체크 결과 출력
    echo ""
    echo "Health Check Response:"
    echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
    
else
    log_error "Health check failed"
    log_error "Response: $HEALTH_RESPONSE"
    
    # 서버 로그 확인
    log_info "Checking server logs..."
    sleep 2
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

# 9. API 테스트
log_info "Testing API endpoints..."

# 에이전트 목록 조회
AGENTS_RESPONSE=$(curl -s http://localhost:8000/agents || echo "failed")
if [[ $AGENTS_RESPONSE == *"agents"* ]]; then
    log_success "Agents endpoint working"
else
    log_warning "Agents endpoint test failed"
fi

# 에이전트 기능 조회
CAPABILITIES_RESPONSE=$(curl -s http://localhost:8000/agents/capabilities || echo "failed")
if [[ $CAPABILITIES_RESPONSE == *"capabilities"* ]]; then
    log_success "Capabilities endpoint working"
else
    log_warning "Capabilities endpoint test failed"
fi

# 10. 테스트 세션 생성 및 메시지 전송
log_info "Testing session creation and messaging..."

# 세션 생성
SESSION_RESPONSE=$(curl -s -X POST "http://localhost:8000/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "agent_id": "assistant-001",
    "metadata": {"test": true}
  }' || echo "failed")

if [[ $SESSION_RESPONSE == *"session_id"* ]]; then
    SESSION_ID=$(echo "$SESSION_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])" 2>/dev/null || echo "")
    
    if [ ! -z "$SESSION_ID" ]; then
        log_success "Session created: $SESSION_ID"
        
        # 메시지 전송 테스트
        MESSAGE_RESPONSE=$(curl -s -X POST "http://localhost:8000/sessions/$SESSION_ID/messages" \
          -H "Content-Type: application/json" \
          -d '{
            "message": "안녕하세요! 테스트 메시지입니다."
          }' || echo "failed")
        
        if [[ $MESSAGE_RESPONSE == *"response"* ]]; then
            log_success "Message sent and response received"
            
            # 응답 내용 출력
            echo ""
            echo "Test Message Response:"
            echo "$MESSAGE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$MESSAGE_RESPONSE"
            
        else
            log_warning "Message test failed"
            log_warning "Response: $MESSAGE_RESPONSE"
        fi
    else
        log_warning "Could not extract session ID"
    fi
else
    log_warning "Session creation test failed"
    log_warning "Response: $SESSION_RESPONSE"
fi

# 11. 완료 메시지
echo ""
echo "=========================================================="
log_success "Installation and testing completed!"
echo ""
echo "🌐 Access the application:"
echo "   Web Interface: http://localhost:8000"
echo "   API Documentation: http://localhost:8000/docs"
echo "   Health Check: http://localhost:8000/health"
echo ""
echo "🤖 Available Agents:"
echo "   - assistant-001: General Assistant"
echo "   - support-001: Customer Support"
echo "   - analyst-001: Data Analyst"
echo ""
echo "🛠️ Next Steps:"
echo "   1. Edit .env file with your AWS credentials"
echo "   2. Open http://localhost:8000 in your browser"
echo "   3. Start chatting with Strands Agents!"
echo ""
echo "🔧 To stop the server:"
echo "   kill $SERVER_PID"
echo ""
echo "📚 Documentation:"
echo "   - README.md for detailed information"
echo "   - REGENERATION_PROMPT.md for development specs"
echo ""
log_success "Server is running in the background (PID: $SERVER_PID)"
echo "=========================================================="

# 서버를 포그라운드로 가져오기 (선택적)
read -p "Press Enter to bring server to foreground (Ctrl+C to stop), or Ctrl+C to keep it in background..."
fg 2>/dev/null || echo "Server continues running in background"
