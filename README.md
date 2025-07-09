# Strands Agent Session Manager

AWS Strands Agent SDK를 사용한 프로덕션급 대화형 AI 세션 관리 시스템입니다. 최신 Strands Agent SDK의 모든 기능을 활용하여 Redis 기반 세션 저장과 DynamoDB 기반 대화 히스토리 저장을 지원하며, 확장 가능한 마이크로서비스 아키텍처로 설계되었습니다.

## 🧬 AWS Strands Agent SDK

이 프로젝트는 **AWS Strands Agent SDK**의 완전한 데모 애플리케이션입니다:

- **Model-driven approach**: 복잡한 워크플로우 대신 모델의 추론 능력 활용
- **Multi-provider support**: Bedrock, Anthropic, OpenAI 등 다양한 모델 제공자 지원
- **Built-in tools**: WebSearch, Calculator 등 강력한 도구 통합
- **Production-ready**: 실제 AWS 팀들이 프로덕션에서 사용하는 SDK

## 🚀 주요 기능

### 핵심 기능
- **Multi-turn 대화**: 컨텍스트를 유지하는 연속 대화 지원
- **세션 관리**: Redis 기반 고성능 세션 저장
- **대화 히스토리**: LangChain + DynamoDB 기반 영구 대화 기록 저장
- **다중 에이전트**: 일반 어시스턴트, 고객 지원, 데이터 분석 전문가
- **웹 인터페이스**: 브라우저에서 바로 테스트 가능한 모던 채팅 UI
- **도구 통합**: 웹 검색, 계산기, 시간 조회 등 실용적 도구들

### 기술적 특징
- **Stateless 설계**: EKS Pod 스케일링 지원 (3-100 pods)
- **고가용성**: Redis 장애 시 메모리 기반 fallback
- **확장성**: 수천 명의 동시 사용자 지원
- **RESTful API**: 표준 HTTP API 제공
- **최신 SDK**: Strands Agent SDK 최신 기능 완전 활용

## 🏗️ 아키텍처

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Browser   │    │   Mobile App     │    │   API Client    │
└─────────┬───────┘    └─────────┬────────┘    └─────────┬───────┘
          │                      │                       │
          └──────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Load Balancer        │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     EKS Pods            │
                    │  (FastAPI Servers)      │
                    └─────────┬───────────────┘
                              │
                 ┌────────────┼────────────┐
                 │            │            │
        ┌────────▼──────┐    │    ┌───────▼────────┐
        │ Redis Cluster │    │    │   DynamoDB     │
        │  (Sessions)   │    │    │ (LangChain)    │
        └───────────────┘    │    └────────────────┘
                             │
                    ┌────────▼────────┐
                    │ AWS Strands     │
                    │ Agent SDK       │
                    │ + Bedrock       │
                    └─────────────────┘
```

## 🛠️ 기술 스택

### Backend
- **FastAPI 0.115+**: 고성능 비동기 웹 프레임워크
- **Python 3.10+**: 최신 Python 기능 활용
- **AWS Strands Agent SDK**: 최신 AI 에이전트 프레임워크

### Storage
- **Redis**: 고성능 세션 저장소 (primary)
- **Memory**: 세션 저장소 fallback
- **DynamoDB**: LangChain 표준 대화 히스토리 저장

### AI & Models
- **AWS Bedrock**: Claude 3.5 Sonnet (기본)
- **Anthropic API**: 직접 API 연결 (선택적)
- **OpenAI API**: GPT-4 연결 (선택적)

### Tools & Integrations
- **WebSearchTool**: 실시간 웹 검색
- **CalculatorTool**: 수학적 계산
- **Custom Tools**: 시간 조회, 세션 정보 등

## 📦 설치 및 실행

### 1. 환경 준비

```bash
# Python 가상환경 생성
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 의존성 설치 (최신 Strands Agent SDK 포함)
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
nano .env
```

필수 환경 변수:
```env
# AWS 설정 (Bedrock 사용 시)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=ap-northeast-2

# Strands Agent 설정
STRANDS_MODEL_PROVIDER=bedrock
STRANDS_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
STRANDS_REGION=ap-northeast-2

# Redis 설정
REDIS_URL=redis://localhost:6379
```

### 3. Redis 실행

```bash
# Docker로 Redis 실행
docker run -d -p 6379:6379 --name redis redis:alpine

# 또는 로컬 Redis 설치
# Ubuntu: sudo apt install redis-server
# macOS: brew install redis
```

### 4. 서버 실행

```bash
# process kill
lsof -ti:8000 | xargs kill -9

# 개발 모드
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 또는 스크립트 사용
./run.sh
```

### 5. 접속 및 테스트

- **웹 인터페이스**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **헬스 체크**: http://localhost:8000/health

## 🎯 사용 방법

### 웹 인터페이스 사용

1. 브라우저에서 http://localhost:8000 접속
2. 사용자 ID 입력 (예: user123)
3. 에이전트 선택 (assistant-001, support-001, analyst-001)
4. 대화 시작!

### API 사용 예시

```bash
# 세션 생성
curl -X POST "http://localhost:8000/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "agent_id": "assistant-001"
  }'

# 메시지 전송
curl -X POST "http://localhost:8000/sessions/{session_id}/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "안녕하세요! 오늘 날씨는 어떤가요?"
  }'

# 대화 히스토리 조회
curl "http://localhost:8000/sessions/{session_id}/history"
```

## 🤖 에이전트 타입

### 1. General Assistant (assistant-001)
- **역할**: 범용 AI 어시스턴트
- **기능**: 일반적인 질문 답변, 웹 검색, 계산
- **도구**: WebSearch, Calculator, Time, Session Info

### 2. Customer Support (support-001)
- **역할**: 고객 지원 전문가
- **기능**: 문제 해결, 단계별 가이드
- **도구**: WebSearch, Time, Session Info

### 3. Data Analyst (analyst-001)
- **역할**: 데이터 분석 전문가
- **기능**: 데이터 분석, 수치 계산, 트렌드 분석
- **도구**: WebSearch, Calculator, Time, Session Info

## 🔧 API 엔드포인트

### 세션 관리
- `POST /sessions` - 세션 생성
- `GET /sessions/{session_id}` - 세션 조회
- `DELETE /sessions/{session_id}` - 세션 삭제
- `GET /users/{user_id}/sessions` - 사용자 세션 목록

### 메시지 처리
- `POST /sessions/{session_id}/messages` - 메시지 전송
- `GET /sessions/{session_id}/history` - 대화 히스토리 조회

### 에이전트 관리
- `GET /agents` - 에이전트 목록
- `GET /agents/{agent_id}` - 에이전트 정보
- `GET /agents/capabilities` - 에이전트 기능 정보

### 시스템 관리
- `GET /health` - 시스템 상태 확인
- `GET /admin/stats` - 시스템 통계
- `POST /admin/cleanup` - 만료된 세션 정리

## 🔍 모니터링 및 로깅

### 헬스 체크
```bash
curl http://localhost:8000/health
```

응답 예시:
```json
{
  "status": "healthy",
  "storage": "redis",
  "strands_agent": "healthy",
  "timestamp": "2025-07-09T07:00:00Z",
  "strands_details": {
    "overall_status": "healthy",
    "components": {
      "strands_sdk": {"status": "available"},
      "strands_tools": {"status": "available"},
      "model_providers": {
        "bedrock": {"status": "available"}
      }
    }
  }
}
```

### 시스템 통계
```bash
curl http://localhost:8000/admin/stats
```

## 🚀 배포

### Docker 배포

```bash
# Docker 이미지 빌드
docker build -t strands-agent-api .

# 컨테이너 실행
docker run -d -p 8000:8000 \
  -e AWS_ACCESS_KEY_ID=your-key \
  -e AWS_SECRET_ACCESS_KEY=your-secret \
  -e REDIS_URL=redis://redis:6379 \
  strands-agent-api
```

### Kubernetes 배포

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: strands-agent-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: strands-agent-api
  template:
    metadata:
      labels:
        app: strands-agent-api
    spec:
      containers:
      - name: api
        image: strands-agent-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        - name: AWS_REGION
          value: "ap-northeast-2"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

## 🔧 개발 가이드

### 새로운 에이전트 추가

1. `strands_client.py`에서 시스템 프롬프트 추가:
```python
def _get_system_prompt(self, agent_id: str) -> str:
    prompts = {
        "your-agent-001": """
        당신의 새로운 에이전트 프롬프트...
        """
    }
```

2. `main.py`에서 에이전트 정보 추가:
```python
async def get_agent_info(agent_id: str):
    agent_configs = {
        "your-agent-001": {
            "id": "your-agent-001",
            "name": "Your Agent",
            "description": "설명..."
        }
    }
```

### 새로운 도구 추가

```python
def your_custom_tool(param: str) -> str:
    """Your custom tool description"""
    # 도구 로직 구현
    return result

custom_tool = FunctionTool(
    name="your_custom_tool",
    description="도구 설명",
    function=your_custom_tool
)
```

## 🐛 문제 해결

### 일반적인 문제들

1. **Strands SDK 설치 오류**
```bash
pip install --upgrade strands-agents strands-agents-tools
```

2. **Redis 연결 실패**
```bash
# Redis 상태 확인
redis-cli ping

# Docker Redis 재시작
docker restart redis
```

3. **AWS 자격 증명 오류**
```bash
# AWS CLI 설정 확인
aws configure list

# 환경 변수 확인
echo $AWS_ACCESS_KEY_ID
```

4. **DynamoDB 테이블 생성 실패**
- IAM 권한 확인: `dynamodb:CreateTable`, `dynamodb:PutItem`, `dynamodb:GetItem`

### 로그 확인

```bash
# 애플리케이션 로그
tail -f server.log

# Docker 로그
docker logs strands-agent-api
```

## 📚 참고 자료

- [AWS Strands Agent SDK 공식 문서](https://github.com/strands-agents/sdk-python)
- [Strands Agent Tools](https://github.com/strands-agents/tools)
- [AWS Bedrock 문서](https://docs.aws.amazon.com/bedrock/)
- [LangChain 문서](https://python.langchain.com/)
- [FastAPI 문서](https://fastapi.tiangolo.com/)

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 🙏 감사의 말

- AWS Strands Agent 팀의 훌륭한 SDK
- FastAPI 커뮤니티
- LangChain 프로젝트
- 모든 오픈소스 기여자들

---

**Made with ❤️ using AWS Strands Agent SDK**
