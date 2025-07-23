# Strands Agent Session Manager with Long Term Memory

AWS Strands Agent SDK 1.0.1을 사용한 프로덕션급 대화형 AI 세션 관리 시스템입니다. Redis 기반 세션 저장, DynamoDB 기반 대화 히스토리 저장, 그리고 **Long Term Memory (LTM)** 기능을 통한 사용자 개인화를 지원합니다.

## 🆕 주요 기능

### 핵심 기능
- **Multi-turn 대화**: 컨텍스트를 유지하는 연속 대화 지원
- **세션 관리**: Redis 기반 고성능 세션 저장
- **대화 히스토리**: LangChain + DynamoDB 기반 영구 대화 기록 저장
- **Long Term Memory**: 사용자 선호도 자동 분석 및 개인화 (🆕)
- **다중 에이전트**: 일반 어시스턴트, 고객 지원, 데이터 분석 전문가
- **웹 인터페이스**: 브라우저에서 바로 테스트 가능한 모던 채팅 UI
- **비동기 처리**: SQS 기반 백그라운드 LTM 처리

### 🧠 Long Term Memory (LTM) 기능
- **자동 선호도 추출**: 대화 종료 시 AI가 사용자 선호도를 자동 분석
- **개인화된 응답**: 사용자 히스토리 기반 맞춤형 AI 응답
- **지속적 학습**: 새로운 대화마다 기존 LTM과 병합하여 지속적 개선
- **비동기 처리**: 메인 애플리케이션 성능에 영향 없는 백그라운드 처리

### 🔚 스마트 세션 종료 기능 (🆕)
- **RESTful API 설계**: PATCH를 사용한 의미론적으로 올바른 세션 상태 업데이트
- **명시적 세션 종료**: 웹 UI의 "대화 종료" 버튼으로 수동 종료
- **자동 세션 정리**: 브라우저 종료 시 자동 세션 종료 및 LTM 처리
- **세션 복구**: 브라우저 재시작 시 1시간 이내 세션 자동 복구
- **다중 종료 감지**: 브라우저 종료, 탭 숨김, 포커스 잃음 등 다양한 상황 대응
- **안전한 요청 전송**: `navigator.sendBeacon()` 사용으로 브라우저 종료 시에도 안정적 요청 전송
- **사용자 경험 개선**: 확인 다이얼로그, 상태 메시지, 입력 필드 상태 관리
- **관리자 기능**: 실제 세션 삭제를 위한 별도 DELETE API 제공

## 🏗️ 시스템 아키텍처

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
                    │  Strands Agent 1.0.1    │
                    └─────────┬───────────────┘
                              │
                 ┌────────────┼────────────┐
                 │            │            │
        ┌────────▼──────┐    │    ┌───────▼────────┐
        │ Redis Cluster │    │    │   DynamoDB     │
        │  (Sessions)   │    │    │ (Chat History) │
        └───────────────┘    │    └────────────────┘
                             │
                    ┌────────▼────────┐
                    │   SQS Queue     │
                    │ (LTM Processing)│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   LTM Worker    │
                    │ (Background)    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   DynamoDB      │
                    │ (LTM Storage)   │
                    └─────────────────┘
```

## 🛠️ 기술 스택

### Backend
- **FastAPI 0.115+**: 고성능 비동기 웹 프레임워크
- **Python 3.10+**: 최신 Python 기능 활용
- **AWS Strands Agent SDK 1.0.1**: 최신 AI 에이전트 프레임워크

### Storage & Queue
- **Redis**: 고성능 세션 저장소 (primary)
- **DynamoDB**: 대화 히스토리 및 LTM 저장
- **SQS**: LTM 처리를 위한 메시지 큐
- **Memory**: 세션 저장소 fallback

### AI & Models
- **AWS Bedrock**: Claude 3.5 Sonnet (기본)
- **Anthropic API**: 직접 API 연결 (선택적)
- **OpenAI API**: GPT-4 연결 (선택적)

## 📦 설치 및 실행

### 1. 환경 준비

```bash
# Python 가상환경 생성
python3 -m venv venv
source venv/bin/activate  # Linux/Mac

# 의존성 설치
pip install -r requirements.txt
```

### 2. AWS 인프라 배포

```bash
# LTM 인프라 배포 (SQS, DynamoDB, IAM)
./deploy-ltm-infrastructure.sh dev strands-agent ap-northeast-2
```

### 3. 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env
```

필수 환경 변수:
```env
# AWS 설정
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=ap-northeast-2

# Strands Agent 1.0.1 설정
STRANDS_MODEL_PROVIDER=bedrock
STRANDS_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
STRANDS_REGION=ap-northeast-2

# Redis 설정
REDIS_URL=redis://localhost:6379

# DynamoDB 설정
DYNAMODB_HISTORY_TABLE=langchain_chat_history
USE_LANGCHAIN_HISTORY=true

# Long Term Memory 설정
LTM_QUEUE_URL=https://sqs.ap-northeast-2.amazonaws.com/ACCOUNT_ID/strands-agent-ltm-processing-queue-dev
LTM_TABLE_NAME=strands-agent-user-long-term-memory-dev
LTM_BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
LTM_WORKER_ENABLED=true
```

### 4. Redis 실행

```bash
# Docker로 Redis 실행
docker run -d -p 6379:6379 --name redis redis:alpine
```

### 5. 서버 실행

```bash
# 메인 FastAPI 서버 실행
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 별도 터미널에서 LTM Worker 실행
python ltm_worker.py
```

### 6. 접속 및 테스트

- **웹 인터페이스**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **헬스 체크**: http://localhost:8000/health

## 🎯 사용 방법

### 웹 인터페이스 사용

1. 브라우저에서 http://localhost:8000 접속
2. 사용자 ID 입력 (예: user123)
3. 에이전트 선택 (assistant-001, support-001, analyst-001)
4. 대화 시작!
5. **대화 종료 방법**:
   - **수동 종료**: "대화 종료" 버튼 클릭
   - **자동 종료**: 브라우저 종료 시 자동 처리
   - **세션 복구**: 브라우저 재시작 시 1시간 이내 자동 복구

### 세션 종료 시나리오

#### 1. 명시적 종료 (권장)
```
사용자가 "대화 종료" 버튼 클릭
↓
확인 다이얼로그 표시
↓
세션 종료 API 호출 (PATCH /sessions/{session_id})
↓
LTM 처리 큐에 메시지 전송 (SQS)
↓
백그라운드에서 LTM Worker가 선호도 분석
```

#### 2. 브라우저 종료 시 자동 처리
```
브라우저 종료 감지 (beforeunload/visibilitychange)
↓
navigator.sendBeacon()으로 PATCH 요청 전송
↓
세션 정보 로컬 스토리지에서 제거
↓
LTM 처리 자동 시작
```

#### 3. 세션 복구
```
브라우저 재시작
↓
로컬 스토리지에서 세션 정보 확인
↓
세션 유효성 검증 (1시간 이내)
↓
유효한 경우 대화 복구, 무효한 경우 새 세션 생성
```

### API 사용 예시

#### 기본 세션 관리
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

# 세션 종료 (PATCH API 사용) - LTM 처리 자동 시작
curl -X PATCH "http://localhost:8000/sessions/{session_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "ended",
    "reason": "manual",
    "metadata": {
      "ended_via": "api",
      "user_feedback": "satisfied"
    }
  }'

# 세션 영구 삭제 (관리자용)
curl -X DELETE "http://localhost:8000/sessions/{session_id}?force=true"
```

#### Long Term Memory API
```bash
# 사용자 LTM 조회
curl "http://localhost:8000/users/user123/ltm"

# 사용자 선호도 조회
curl "http://localhost:8000/users/user123/preferences"

# LTM 통계 조회
curl "http://localhost:8000/admin/ltm/stats"
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
- **도구**: Calculator, Analyze Data, Time, Session Info

## 🧠 Long Term Memory 상세

### 추출되는 정보
```json
{
  "interests": ["AI", "Technology", "Data Science"],
  "preferences": {
    "communication_style": "professional",
    "topics_of_interest": ["Machine Learning", "Cloud Computing"],
    "problem_solving_approach": "step-by-step"
  },
  "behavioral_patterns": {
    "question_types": ["technical", "how-to"],
    "interaction_frequency": "daily",
    "session_duration_preference": "medium"
  },
  "context_clues": {
    "mentioned_tools": ["calculator", "web_search"],
    "domain_expertise": "software_development",
    "language_preference": "korean"
  },
  "agent_interaction": {
    "preferred_agent_type": "assistant-001",
    "satisfaction_indicators": ["detailed_explanations"],
    "improvement_suggestions": ["more_examples"]
  }
}
```

### LTM 처리 플로우
1. **대화 종료**: 사용자가 세션 종료
2. **큐 전송**: SQS에 LTM 처리 메시지 전송
3. **백그라운드 처리**: LTM Worker가 메시지 수신
4. **히스토리 분석**: DynamoDB에서 대화 히스토리 조회
5. **AI 분석**: Bedrock Claude로 선호도 추출
6. **LTM 업데이트**: 기존 LTM과 병합하여 저장

## 🔧 API 엔드포인트

### 세션 관리
- `POST /sessions` - 세션 생성
- `GET /sessions/{session_id}` - 세션 조회
- `PATCH /sessions/{session_id}` - **세션 상태 업데이트 (종료 포함)** (🆕)
- `DELETE /sessions/{session_id}` - 세션 영구 삭제 (관리자용, force 옵션)
- `GET /users/{user_id}/sessions` - 사용자 세션 목록

### 메시지 처리
- `POST /sessions/{session_id}/messages` - 메시지 전송
- `GET /sessions/{session_id}/history` - 대화 히스토리 조회

### Long Term Memory
- `GET /users/{user_id}/ltm` - 사용자 LTM 조회
- `GET /users/{user_id}/preferences` - 사용자 선호도 조회
- `PUT /users/{user_id}/ltm` - LTM 수동 업데이트 (관리자용)
- `DELETE /users/{user_id}/ltm` - LTM 삭제

### 시스템 관리
- `GET /health` - 시스템 상태 확인
- `GET /admin/stats` - 시스템 통계
- `GET /admin/ltm/stats` - LTM 통계
- `POST /admin/cleanup` - 만료된 세션 정리

## 🚀 배포

### Docker 배포

#### 메인 애플리케이션
```bash
docker build -t strands-agent-api:latest .
docker run -d -p 8000:8000 \
  -e AWS_ACCESS_KEY_ID=your-key \
  -e AWS_SECRET_ACCESS_KEY=your-secret \
  -e REDIS_URL=redis://redis:6379 \
  -e LTM_QUEUE_URL=your-queue-url \
  strands-agent-api:latest
```

#### LTM Worker
```bash
docker build -f Dockerfile.ltm-worker -t ltm-worker:latest .
docker run -d \
  -e AWS_REGION=ap-northeast-2 \
  -e LTM_QUEUE_URL=your-queue-url \
  -e LTM_TABLE_NAME=your-table-name \
  -e LTM_BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0 \
  ltm-worker:latest
```

### Kubernetes 배포

```bash
# ConfigMap과 ServiceAccount 설정 후
kubectl apply -f k8s/ltm-worker-deployment.yaml
```

## 🔍 모니터링

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
  "strands_version": "1.0.1",
  "ltm_enabled": true,
  "timestamp": "2025-07-22T05:00:00Z"
}
```

### LTM 통계
```bash
curl http://localhost:8000/admin/ltm/stats
```

## 🐛 문제 해결

### 일반적인 문제들

1. **세션 종료가 제대로 작동하지 않음**
```bash
# 세션 상태 확인
curl http://localhost:8000/sessions/{session_id}

# PATCH API로 세션 종료 테스트
curl -X PATCH "http://localhost:8000/sessions/{session_id}" \
  -H "Content-Type: application/json" \
  -d '{"status": "ended", "reason": "test"}'

# 브라우저 개발자 도구에서 콘솔 로그 확인
# "Session ended successfully" 메시지 확인
```

2. **LTM Worker가 메시지를 처리하지 않음**
```bash
# 큐 상태 확인
aws sqs get-queue-attributes --queue-url $LTM_QUEUE_URL --attribute-names All

# Worker 로그 확인
docker logs ltm-worker
```

3. **브라우저 종료 시 세션이 정리되지 않음**
```javascript
// 브라우저 개발자 도구에서 확인
localStorage.getItem('strandsSession')

// beforeunload 이벤트가 제대로 등록되었는지 확인
// 콘솔에서 "Browser close handlers setup completed" 메시지 확인
```

4. **sendBeacon PATCH 요청이 작동하지 않음**
```bash
# 서버 로그에서 POST 요청 확인 (sendBeacon은 POST로 전송됨)
tail -f app.log | grep "POST /sessions"

# FormData 처리 확인
curl -X POST "http://localhost:8000/sessions/{session_id}" \
  -F "method=PATCH" \
  -F 'data={"status":"ended","reason":"test"}'
```

5. **Bedrock 접근 오류**
```bash
# Bedrock 모델 접근 권한 확인
aws bedrock list-foundation-models --region ap-northeast-2

# 환경 변수 확인
echo $LTM_BEDROCK_MODEL_ID
```

6. **DynamoDB 접근 오류**
```bash
# 테이블 상태 확인
aws dynamodb describe-table --table-name $LTM_TABLE_NAME
```

## 🔧 개발 가이드

### 새로운 에이전트 추가

1. `strands_client.py`에서 시스템 프롬프트 추가
2. `main.py`에서 에이전트 정보 추가
3. LTM 분석 로직에 새 에이전트 타입 추가

### LTM 분석 로직 커스터마이징

`ltm_worker.py`의 `extract_user_preferences` 메서드를 수정하여 새로운 분석 요소를 추가할 수 있습니다.

### 세션 종료 기능 커스터마이징

#### RESTful API 설계 원칙
현재 구현은 REST API 설계 원칙을 따릅니다:
- **PATCH**: 세션 상태 업데이트 (종료 포함)
- **DELETE**: 실제 세션 데이터 삭제 (관리자용)

#### 세션 종료 조건 수정
`static/index.html`의 `setupBrowserCloseHandlers()` 메서드에서 세션 종료 조건을 수정할 수 있습니다:

```javascript
// 세션 복구 시간 변경 (기본: 1시간)
const sessionAge = Date.now() - new Date(parsed.timestamp).getTime();
if (sessionAge < 2 * 60 * 60 * 1000) { // 2시간으로 변경
    // 세션 복구 로직
}
```

#### PATCH API 요청 커스터마이징
```javascript
// 추가 메타데이터와 함께 세션 종료
const response = await fetch(`/sessions/${sessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        status: 'ended',
        reason: 'custom_reason',
        metadata: {
            ended_via: 'custom_ui',
            user_satisfaction: 'high',
            session_quality: 'excellent'
        }
    })
});
```

#### 추가 종료 이벤트 감지
```javascript
// 네트워크 연결 끊김 감지
window.addEventListener('offline', () => {
    if (this.sessionId) {
        this.endSession();
    }
});
```

## 📚 참고 자료

- [AWS Strands Agent SDK 1.0.1 문서](https://strandsagents.com/latest/)
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

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

---

**Made with ❤️ using AWS Strands Agent SDK 1.0.1 + Long Term Memory**