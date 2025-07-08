# AWS Strands Agent Session Manager

AWS Strands Agent SDK와 FastAPI를 사용한 AI 에이전트 세션 관리 시스템입니다. 사용자와 Strands Agent 간의 대화 세션을 생성, 관리, 저장하는 기능을 제공합니다.

## 🧬 AWS Strands Agent란?

AWS Strands Agent는 모델 중심 접근 방식을 사용하는 오픈소스 AI 에이전트 SDK입니다:

- **간단함**: 몇 줄의 코드로 강력한 AI 에이전트 구축
- **모델 중립적**: Amazon Bedrock, Anthropic, OpenAI 등 다양한 모델 지원
- **도구 통합**: 웹 검색, 계산기, 커스텀 도구 등 강력한 기능
- **프로덕션 준비**: AWS 내부 팀들이 실제 프로덕션에서 사용 중

## 주요 기능

- **Strands Agent 통합**: AWS의 최신 AI 에이전트 SDK 사용
- **세션 관리**: 사용자별 대화 세션 생성, 조회, 삭제
- **실시간 대화**: Strands Agent와의 실시간 메시지 교환
- **도구 활용**: 웹 검색, 계산기, 시간 조회 등 다양한 도구 지원
- **대화 기록**: 세션별 대화 내용 저장 및 조회
- **Redis 캐싱**: 고성능 세션 데이터 저장
- **RESTful API**: 표준 REST API 인터페이스
- **자동 문서화**: FastAPI 자동 API 문서 생성

## 프로젝트 구조

```
agent-fastapi/
├── main.py              # FastAPI 메인 애플리케이션
├── models.py            # Pydantic 데이터 모델
├── session_manager.py   # 세션 관리 로직
├── strands_client.py    # Strands Agent SDK 클라이언트
├── strands_example.py   # 독립 실행 Strands Agent 예제
├── test_client.py       # API 테스트 클라이언트
├── requirements.txt     # Python 의존성
├── .env                 # 환경 변수 설정
├── docker-compose.yml   # Docker 구성
├── Dockerfile          # Docker 이미지 빌드
├── run.sh              # 실행 스크립트
└── README.md           # 프로젝트 문서
```

## 설치 및 실행

### 사전 요구사항

1. **Python 3.10+** 설치
2. **Redis** 설치 및 실행
3. **AWS 자격 증명** 설정 (Bedrock 사용 시)

### 방법 1: 빠른 시작 (권장)

```bash
# 프로젝트 디렉토리로 이동
cd /Users/inhokang/Dev/strands-agent/agent-fastapi

# 실행 스크립트 사용
./run.sh
```

### 방법 2: 수동 설치

```bash
# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# Redis 실행 (별도 터미널)
redis-server

# FastAPI 서버 실행
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 방법 3: Docker 실행

```bash
# Docker Compose로 전체 스택 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

## 환경 설정

`.env` 파일을 수정하여 환경을 설정하세요:

```env
# FastAPI 설정
SECRET_KEY=your-secret-key-here
REDIS_URL=redis://localhost:6379

# AWS 설정 (Strands Agent용)
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key

# Strands Agent 설정
STRANDS_MODEL_PROVIDER=bedrock
STRANDS_MODEL_ID=anthropic.claude-3-7-sonnet-20241022-v1:0
STRANDS_REGION=us-west-2

# 개발 모드 (실제 AWS 자격 증명이 없을 때 Mock 사용)
DEVELOPMENT_MODE=true
```

### AWS 자격 증명 설정

Strands Agent가 Amazon Bedrock을 사용하려면 AWS 자격 증명이 필요합니다:

1. **환경 변수 방식**:
   ```bash
   export AWS_ACCESS_KEY_ID=your-access-key
   export AWS_SECRET_ACCESS_KEY=your-secret-key
   export AWS_REGION=us-west-2
   ```

2. **AWS CLI 방식**:
   ```bash
   aws configure
   ```

3. **IAM 역할** (EC2, ECS, Lambda에서 실행 시)

4. **Bedrock 모델 액세스 활성화**:
   - AWS 콘솔에서 Amazon Bedrock 서비스로 이동
   - Model access 메뉴에서 Claude 3.7 Sonnet 모델 활성화

## API 사용법

### 1. 서버 상태 확인

```bash
curl http://localhost:8000/health
```

### 2. Strands Agent 기능 확인

```bash
curl http://localhost:8000/agents/capabilities
```

### 3. 세션 생성

```bash
curl -X POST "http://localhost:8000/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "agent_id": "assistant-001",
    "metadata": {"demo": true}
  }'
```

### 4. Strands Agent와 대화

```bash
curl -X POST "http://localhost:8000/sessions/{session_id}/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "{session_id}",
    "message": "AWS Strands Agent에 대해 설명해주세요",
    "message_type": "user"
  }'
```

### 5. 대화 기록 조회

```bash
curl "http://localhost:8000/sessions/{session_id}/history?limit=10"
```

## API 문서

서버 실행 후 다음 URL에서 자동 생성된 API 문서를 확인할 수 있습니다:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 테스트

### 1. 독립 실행 Strands Agent 테스트

```bash
# Strands Agent SDK 직접 테스트
python strands_example.py
```

### 2. API 테스트 클라이언트 실행

```bash
# 전체 데모 실행
python test_client.py

# 간단한 테스트만 실행
python test_client.py simple
```

### 3. 수동 테스트

```bash
# 헬스 체크
curl http://localhost:8000/health

# 에이전트 목록 조회
curl http://localhost:8000/agents

# 시스템 통계 조회
curl http://localhost:8000/admin/stats
```

## 사용 가능한 Strands Agent

| Agent ID | 이름 | 설명 | 기능 |
|----------|------|------|------|
| `assistant-001` | General Assistant | 일반적인 질문에 답변하는 어시스턴트 | 일반 대화, 웹 검색, 계산 |
| `support-001` | Customer Support | 고객 지원 전문 어시스턴트 | 고객 지원, 문제 해결 |
| `analyst-001` | Data Analyst | 데이터 분석 전문 어시스턴트 | 데이터 분석, 계산, 보고서 |

## 주요 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 루트 엔드포인트 |
| GET | `/health` | 헬스 체크 |
| GET | `/agents/capabilities` | Strands Agent 기능 조회 |
| POST | `/sessions` | 세션 생성 |
| GET | `/sessions/{session_id}` | 세션 조회 |
| DELETE | `/sessions/{session_id}` | 세션 삭제 |
| POST | `/sessions/{session_id}/messages` | 메시지 전송 |
| GET | `/sessions/{session_id}/history` | 대화 기록 조회 |
| GET | `/users/{user_id}/sessions` | 사용자 세션 목록 |
| GET | `/agents` | 에이전트 목록 |
| GET | `/agents/{agent_id}` | 에이전트 정보 |
| GET | `/admin/stats` | 시스템 통계 |

## Strands Agent 도구

이 시스템에서 사용하는 Strands Agent는 다음 도구들을 지원합니다:

- **웹 검색**: 실시간 웹 정보 검색
- **계산기**: 수학 계산 수행
- **시간 조회**: 현재 시간 확인
- **세션 정보**: 세션 상태 조회

## 개발 가이드

### 코드 구조

- **main.py**: FastAPI 애플리케이션 메인 파일
- **models.py**: Pydantic 데이터 모델 정의
- **session_manager.py**: Redis 기반 세션 관리 로직
- **strands_client.py**: Strands Agent SDK 통합 클라이언트
- **strands_example.py**: 독립 실행 Strands Agent 예제

### 새로운 에이전트 추가

1. `strands_client.py`에서 새 에이전트 ID와 시스템 프롬프트 추가
2. `get_agent_info()` 메서드에 에이전트 정보 추가
3. 필요한 경우 전용 도구 구현

### 커스텀 도구 추가

```python
from strands.tools import Tool

def my_custom_tool(param: str) -> str:
    """커스텀 도구 함수"""
    return f"처리 결과: {param}"

custom_tool = Tool(
    name="my_custom_tool",
    description="커스텀 도구 설명",
    function=my_custom_tool,
    parameters={
        "param": {
            "type": "string",
            "description": "입력 매개변수"
        }
    }
)
```

## 모니터링

- **헬스 체크**: `/health` 엔드포인트로 서비스 상태 확인
- **통계**: `/admin/stats`로 시스템 사용량 모니터링
- **로그**: 애플리케이션 로그로 오류 및 성능 추적

## 문제 해결

### Strands Agent SDK 설치 오류

```bash
# 최신 버전 설치
pip install --upgrade strands-agents strands-agents-tools

# 의존성 충돌 해결
pip install --force-reinstall strands-agents
```

### AWS Bedrock 연결 오류

1. **자격 증명 확인**:
   ```bash
   aws sts get-caller-identity
   ```

2. **Bedrock 모델 액세스 확인**:
   - AWS 콘솔 → Amazon Bedrock → Model access
   - Claude 3.7 Sonnet 모델 활성화

3. **리전 확인**:
   - Bedrock이 지원되는 리전 사용 (us-west-2 권장)

### Redis 연결 오류

```bash
# Redis 설치 및 실행
# macOS
brew install redis
brew services start redis

# Ubuntu
sudo apt install redis-server
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:alpine
```

### 포트 충돌

```bash
# 다른 포트로 실행
uvicorn main:app --host 0.0.0.0 --port 8001
```

## 참고 자료

- **Strands Agent 공식 문서**: https://strandsagents.com/latest/
- **GitHub 저장소**: https://github.com/strands-agents/sdk-python
- **AWS 블로그**: https://aws.amazon.com/blogs/opensource/introducing-strands-agents-an-open-source-ai-agents-sdk/
- **Amazon Bedrock 문서**: https://docs.aws.amazon.com/bedrock/

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 기여

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 지원

문제가 발생하거나 질문이 있으시면 이슈를 생성해 주세요.
