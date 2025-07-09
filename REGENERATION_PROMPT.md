# Strands Agent Session Manager 완전 재생성 프롬프트

다음 요구사항에 따라 AWS Strands Agent SDK를 사용한 프로덕션급 대화형 AI 세션 관리 시스템을 구축해주세요:

## 🎯 핵심 요구사항

### 1. 아키텍처 설계 (Production-Ready)
- **Stateless FastAPI 서버**: EKS Pod 스케일링 지원 (3-100 pods)
- **Redis 기반 세션 관리**: 고성능 세션 저장 및 조회
- **LangChain + DynamoDB**: 표준 ChatMessage 형식으로 대화 히스토리 저장
- **하이브리드 저장소**: Redis 장애 시 메모리 기반 fallback
- **사용자 중심 설계**: 개인화된 대화 경험 및 기록 유지

### 2. 기술 스택 (최신 버전)
- **Backend**: FastAPI 0.115+, Python 3.10+
- **세션 저장소**: Redis Cluster (primary), Memory (fallback)
- **히스토리 저장소**: LangChain + DynamoDB (ap-northeast-2)
- **AI 모델**: AWS Strands Agent SDK + Bedrock Claude 3.5 Sonnet
- **Frontend**: 모던 반응형 웹 채팅 인터페이스 (FontAwesome, CSS Grid)
- **도구 통합**: WebSearch, Calculator, Custom Tools (선택적)

### 3. Strands Agent SDK 통합 (핵심)
```python
# 순수 Strands Agent SDK 사용 (직접 Bedrock 호출 금지)
from strands import Agent
from strands.models import BedrockModel
from strands.tools import FunctionTool

# 에이전트 생성
model = BedrockModel(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    region="ap-northeast-2"
)

agent = Agent(
    model=model,
    tools=custom_tools,
    system_prompt=agent_specific_prompt,
    max_iterations=10,
    enable_tracing=True
)
```

### 4. 사용자 중심 UI/UX
- **로그인 시스템**: 사용자 ID 입력 필수
- **로컬 스토리지**: 사용자 정보 자동 저장/복원
- **대화 기록 유지**: 재접속 시 이전 대화 자동 로드
- **개인화**: 사용자별 아바타, 설정, 히스토리

### 5. 에이전트 타입 및 시스템 프롬프트
```python
AGENT_PROMPTS = {
    "assistant-001": """
당신은 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 정확하고 유용한 답변을 제공하세요.
사용 가능한 도구들을 적극적으로 활용하여 최신 정보를 제공하고 계산을 수행하세요.
한국어로 답변하며, 친근하고 전문적인 톤을 유지하세요.
    """,
    "support-001": """
당신은 고객 지원 전문 AI 어시스턴트입니다. 고객의 문제를 해결하고 도움을 제공하는 것이 주요 역할입니다.
문제 해결을 위해 단계별로 접근하고, 필요한 경우 도구를 사용하여 정보를 조회하세요.
정중하고 이해하기 쉬운 방식으로 답변하세요.
    """,
    "analyst-001": """
당신은 데이터 분석 전문 AI 어시스턴트입니다. 데이터를 분석하고 인사이트를 제공하는 것이 주요 역할입니다.
계산기 도구를 사용하여 수치 계산을 수행하고, 웹 검색을 통해 최신 데이터를 조회하세요.
분석 결과를 명확하고 구조적으로 제시하세요.
    """
}
```

### 6. LangChain 히스토리 관리
```python
# LangChain DynamoDBChatMessageHistory 사용
from langchain_community.chat_message_histories import DynamoDBChatMessageHistory
from langchain.schema import HumanMessage, AIMessage

class LangChainHistoryManager:
    def get_chat_history(self, session_id: str):
        return DynamoDBChatMessageHistory(
            table_name="langchain_chat_history",
            session_id=session_id
        )
    
    async def save_conversation(self, session_id, message, response):
        chat_history = self.get_chat_history(session_id)
        chat_history.add_user_message(message)
        chat_history.add_ai_message(response)
```

### 7. API 엔드포인트 구조 (완전)
```
# 세션 관리
POST /sessions - 세션 생성
GET /sessions/{session_id} - 세션 조회
DELETE /sessions/{session_id} - 세션 삭제
GET /users/{user_id}/sessions - 사용자 세션 목록

# 메시지 처리
POST /sessions/{session_id}/messages - 메시지 전송 (Strands Agent)
GET /sessions/{session_id}/history - 대화 히스토리 조회

# 사용자 관리
GET /users/{user_id}/history - 사용자 전체 히스토리 (모달 UI)
DELETE /sessions/{session_id}/history - 세션 히스토리 삭제

# 시스템 관리
GET /health - 시스템 상태 확인
GET /api - API 정보
GET /agents - 에이전트 목록 및 기능
GET /admin/stats - 시스템 통계

# 정적 파일
GET / - 메인 채팅 인터페이스 (리다이렉트)
GET /static/* - 정적 파일 서빙
```

### 8. 모던 웹 인터페이스 (완전 구현)
```html
<!-- 주요 기능 -->
- 로그인 화면: 사용자 ID 입력 + 에이전트 선택
- 채팅 화면: 실시간 대화 + 타이핑 인디케이터
- 히스토리 모달: 전체 대화 기록 보기
- 반응형 디자인: 모바일/데스크톱 완벽 지원
- 아이콘 통합: FontAwesome 6.0
- 애니메이션: CSS 전환 효과
- 상태 표시: 연결 상태 실시간 모니터링
```

### 9. 환경 설정 (프로덕션)
```env
# Redis 설정
REDIS_URL=redis://localhost:6379

# AWS 설정
AWS_REGION=ap-northeast-2
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Strands Agent 설정
STRANDS_MODEL_PROVIDER=bedrock
STRANDS_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
STRANDS_REGION=ap-northeast-2

# 히스토리 관리자 선택
USE_LANGCHAIN_HISTORY=true
DYNAMODB_HISTORY_TABLE=langchain_chat_history

# 프로덕션 모드
DEVELOPMENT_MODE=false
USE_STRANDS_SDK=true
```

### 10. 파일 구조 (완전)
```
agent-fastapi/
├── main.py                      # FastAPI 메인 (lifespan, 예외처리)
├── models.py                    # Pydantic 모델 정의
├── session_manager.py           # Redis 세션 관리자
├── memory_session_manager.py    # 메모리 기반 fallback
├── dynamodb_history_manager.py  # Custom DynamoDB 관리자
├── langchain_history_manager.py # LangChain 히스토리 관리자
├── strands_client.py           # Strands Agent 클라이언트 (순수 SDK)
├── static/
│   ├── index.html              # 모던 채팅 인터페이스
│   └── test.html               # 간단한 테스트 페이지
├── requirements.txt             # 모든 의존성 (LangChain 포함)
├── .env.example                # 환경 변수 예시
├── .env                        # 실제 환경 변수
├── run.sh                      # 실행 스크립트
├── start_and_test.sh           # 통합 테스트 스크립트
├── test_client.py              # API 테스트 클라이언트
├── README.md                   # 완전한 문서
└── REGENERATION_PROMPT.md      # 이 파일
```

### 11. 핵심 기능 구현 세부사항

#### A. 세션 관리 (고급)
- UUID4 기반 세션 ID 생성
- Redis 연결 실패 시 메모리 기반 자동 전환
- TTL 기반 자동 만료 (3600초)
- 사용자별 다중 세션 지원
- 세션 메타데이터 저장 (생성시간, 마지막 활동, 에이전트 타입)

#### B. Strands Agent 통합 (핵심)
- 순수 Strands Agent SDK 사용 (직접 Bedrock 호출 금지)
- BedrockModel을 통한 Claude 3.5 Sonnet 연결
- FunctionTool을 사용한 커스텀 도구 생성
- 에이전트별 시스템 프롬프트 차별화
- 컨텍스트 유지 (최근 5개 대화)
- 도구 사용 추적 및 로깅

#### C. LangChain 히스토리 (표준)
- DynamoDBChatMessageHistory 사용
- HumanMessage/AIMessage 표준 형식
- 자동 직렬화/역직렬화
- 메타데이터 포함 (user_id, agent_id, timestamp)

#### D. 모던 웹 인터페이스 (완전)
- 로그인 시스템: 사용자 ID + 에이전트 선택
- 로컬 스토리지: 사용자 정보 자동 저장
- 실시간 채팅: 타이핑 인디케이터, 메시지 애니메이션
- 히스토리 모달: 전체 대화 기록 팝업
- 반응형 디자인: CSS Grid, Flexbox
- 아이콘 통합: FontAwesome 6.0
- 상태 관리: 연결 상태, 로딩 상태

#### E. 오류 처리 및 안정성
- FastAPI jsonable_encoder 사용 (datetime 직렬화)
- 예외 처리기: HTTP/일반 예외 모두 처리
- 로깅: 구조화된 로그 (INFO 레벨)
- Graceful degradation: 서비스 장애 시 부분 기능 유지

### 12. 의존성 관리 (완전)
```txt
# Core FastAPI
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pydantic>=2.5.0

# Session & Storage
redis==5.0.1
boto3==1.35.0

# Strands Agent SDK (필수)
strands-agents==0.1.0
strands-agents-tools==0.1.0  # 선택적

# LangChain Integration
langchain>=0.2.0
langchain-community>=0.2.0

# Utilities
python-dotenv==1.0.0
python-multipart>=0.0.6
```

### 13. 배포 및 스케일링 (EKS)
```yaml
# Kubernetes 배포 예시
apiVersion: apps/v1
kind: Deployment
metadata:
  name: strands-agent-api
spec:
  replicas: 5
  template:
    spec:
      containers:
      - name: api
        image: strands-agent-api:latest
        env:
        - name: REDIS_URL
          value: "redis://elasticache-cluster:6379"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### 14. 로드 밸런서 구성 (ALB)
```yaml
# Session Affinity 설정
apiVersion: v1
kind: Service
metadata:
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
spec:
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 3600
```

### 15. 모니터링 및 관찰성
- **헬스 체크**: `/health` 엔드포인트
- **메트릭**: 세션 수, 대화 수, 응답 시간
- **로깅**: 구조화된 JSON 로그
- **추적**: Strands Agent 실행 추적
- **알림**: 오류율, 응답 시간 임계값

### 16. 보안 고려사항
- **CORS**: 프로덕션에서 특정 도메인으로 제한
- **Rate Limiting**: 사용자별 요청 제한 (준비)
- **JWT**: 인증 토큰 시스템 (준비)
- **환경 변수**: 민감한 정보 분리
- **AWS IAM**: 최소 권한 원칙

### 17. 테스트 전략
```python
# 자동 테스트 포함
- 헬스 체크 검증
- 세션 생성/조회/삭제 테스트
- Strands Agent 메시지 전송 테스트
- LangChain 히스토리 저장/조회 테스트
- UI 기능 테스트 (수동)
```

## 🚀 실행 방법 (완전)

### 1. 환경 준비
```bash
# Python 가상환경
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# Redis 실행 (Docker)
docker run -d -p 6379:6379 --name redis redis:alpine
```

### 2. AWS 설정
```bash
# AWS 자격 증명
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=ap-northeast-2

# DynamoDB 테이블 자동 생성됨
```

### 3. 서버 실행
```bash
# 개발 모드
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 또는 스크립트 사용
./run.sh
```

### 4. 접속 및 테스트
```bash
# 웹 인터페이스
http://localhost:8000

# API 문서
http://localhost:8000/docs

# 헬스 체크
curl http://localhost:8000/health
```

## 📋 구현 체크리스트

### ✅ 완료된 기능
- [x] Stateless FastAPI 서버
- [x] Redis 세션 관리 + 메모리 fallback
- [x] LangChain DynamoDBChatMessageHistory 통합
- [x] Strands Agent SDK 순수 사용
- [x] Claude 3.5 Sonnet 모델 연결
- [x] 사용자 중심 로그인 시스템
- [x] 모던 반응형 웹 인터페이스
- [x] 실시간 채팅 + 타이핑 인디케이터
- [x] 대화 기록 모달 UI
- [x] 로컬 스토리지 사용자 정보 유지
- [x] 완전한 API 엔드포인트
- [x] 오류 처리 및 JSON 직렬화
- [x] 구조화된 로깅
- [x] 환경 변수 관리

### 🔄 선택적 기능
- [ ] WebSearch, Calculator 도구 (strands_agents_tools 필요)
- [ ] JWT 인증 시스템
- [ ] Rate Limiting
- [ ] 고급 모니터링 (Prometheus/Grafana)

## 🎯 핵심 가치 제안

이 시스템은 **Strands Agent SDK의 완전한 데모**입니다:

1. **순수 SDK 사용**: 직접 Bedrock 호출 없이 Strands Agent만 사용
2. **프로덕션 준비**: EKS 배포, 스케일링, 모니터링 완비
3. **사용자 중심**: 개인화된 대화 경험 및 기록 유지
4. **표준 준수**: LangChain 표준 메시지 형식 사용
5. **모던 UI**: 최신 웹 기술을 활용한 사용자 경험

## 📝 추가 요청사항

- Git 브랜치 관리: `main`, `feature/dynamodb-history`, `feature/langchain-integration`
- 완전한 README.md 문서 작성
- 환경별 설정 파일 (.env.example, .env.prod)
- Docker 컨테이너화 (선택적)
- CI/CD 파이프라인 (선택적)

**이 프롬프트를 사용하여 완전한 Strands Agent Session Manager를 재생성해주세요.**