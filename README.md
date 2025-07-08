# Strands Agent Session Manager

AWS Strands Agent SDK를 사용한 대화형 AI 세션 관리 시스템입니다. Redis 기반 세션 저장과 DynamoDB 기반 대화 히스토리 저장을 지원하며, 확장 가능한 마이크로서비스 아키텍처로 설계되었습니다.

## 🚀 주요 기능

### 핵심 기능
- **Multi-turn 대화**: 컨텍스트를 유지하는 연속 대화 지원
- **세션 관리**: Redis 기반 고성능 세션 저장
- **대화 히스토리**: DynamoDB 기반 영구 대화 기록 저장
- **다중 에이전트**: 일반 어시스턴트, 고객 지원, 데이터 분석 전문가
- **웹 인터페이스**: 브라우저에서 바로 테스트 가능한 채팅 UI

### 기술적 특징
- **Stateless 설계**: EKS Pod 스케일링 지원
- **고가용성**: Redis 장애 시 메모리 기반 fallback
- **확장성**: 수천 명의 동시 사용자 지원
- **RESTful API**: 표준 HTTP API 제공

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
        │  (Sessions)   │    │    │  (History)     │
        └───────────────┘    │    └────────────────┘
                             │
                    ┌────────▼────────┐
                    │ AWS Bedrock     │
                    │ (Strands Agent) │
                    └─────────────────┘
```

## 📋 요구사항

### 시스템 요구사항
- Python 3.10+
- Docker (Redis 실행용)
- AWS 계정 및 자격 증명

### AWS 서비스
- **Amazon Bedrock**: Claude 3.7 Sonnet 모델 액세스 필요
- **DynamoDB**: 대화 히스토리 저장 (자동 생성)
- **IAM**: Bedrock 및 DynamoDB 액세스 권한

## 🛠️ 설치 및 실행

### 1. 저장소 클론 및 환경 설정

```bash
git clone <repository-url>
cd agent-fastapi

# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. Redis 실행 (Docker)

```bash
# Redis 컨테이너 실행
docker run -d -p 6379:6379 --name redis redis:alpine
```

### 3. 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
vim .env
```

**.env 파일 예시:**
```env
# Redis 설정
REDIS_URL=redis://localhost:6379

# DynamoDB 설정
DYNAMODB_HISTORY_TABLE=conversation_history
AWS_REGION=us-west-2

# Strands Agent 설정
STRANDS_MODEL_PROVIDER=bedrock
STRANDS_MODEL_ID=anthropic.claude-3-7-sonnet-20241022-v1:0
STRANDS_REGION=us-west-2

# 개발 모드
DEVELOPMENT_MODE=true
```

### 4. AWS 자격 증명 설정

```bash
# AWS CLI 설정
aws configure

# 또는 환경 변수로 설정
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
```

### 5. 서버 실행

```bash
# 간편 실행 스크립트 사용
./run.sh

# 또는 직접 실행
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 🌐 사용 방법

### 웹 인터페이스
브라우저에서 `http://localhost:8000`에 접속하면 채팅 인터페이스를 사용할 수 있습니다.

### API 문서
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### 주요 API 엔드포인트

#### 세션 관리
```bash
# 새 세션 생성
POST /sessions
{
  "user_id": "user123",
  "agent_id": "assistant-001",
  "metadata": {}
}

# 세션 조회
GET /sessions/{session_id}

# 사용자 세션 목록
GET /users/{user_id}/sessions
```

#### 메시지 전송
```bash
# 메시지 전송
POST /sessions/{session_id}/messages
{
  "session_id": "session_id",
  "message": "안녕하세요!",
  "message_type": "user"
}

# 대화 히스토리 조회
GET /sessions/{session_id}/history?limit=50
```

#### 시스템 관리
```bash
# 헬스 체크
GET /health

# 에이전트 목록
GET /agents

# 시스템 통계
GET /admin/stats
```

## 🧪 테스트

### 자동 테스트 클라이언트
```bash
# 전체 데모 실행
./run.sh
# 옵션 3 선택 → 옵션 1 선택

# 간단한 테스트
python test_client.py simple
```

### 수동 테스트
```bash
# 헬스 체크
curl http://localhost:8000/health

# 세션 생성
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "agent_id": "assistant-001"}'
```

## 🔧 개발 및 배포

### Git 브랜치 구조
- `main`: 안정 버전 (Redis 세션 관리)
- `feature/dynamodb-history`: DynamoDB 히스토리 기능

### Docker 배포
```bash
# Dockerfile 빌드
docker build -t strands-agent-api .

# 컨테이너 실행
docker run -p 8000:8000 strands-agent-api
```

### EKS 배포
```yaml
# deployment.yaml 예시
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
```

## 📊 모니터링

### 로그 확인
```bash
# 서버 로그
tail -f server.log

# 애플리케이션 로그
docker logs -f <container_id>
```

### 메트릭
- 세션 수: `/admin/stats`
- 시스템 상태: `/health`
- 대화 통계: `/admin/history/stats`

## 🔒 보안 고려사항

### 프로덕션 배포 시
1. **CORS 설정**: 특정 도메인으로 제한
2. **API 키 인증**: JWT 토큰 또는 API 키 구현
3. **Rate Limiting**: 요청 제한 설정
4. **HTTPS**: SSL/TLS 인증서 적용
5. **환경 변수**: 민감한 정보는 AWS Secrets Manager 사용

## 🐛 문제 해결

### 일반적인 문제

**Redis 연결 실패**
```bash
# Redis 상태 확인
docker ps | grep redis

# Redis 재시작
docker restart redis
```

**DynamoDB 권한 오류**
```bash
# IAM 정책 확인
aws iam list-attached-user-policies --user-name your-user

# 필요한 권한: DynamoDBFullAccess, BedrockFullAccess
```

**Strands Agent 오류**
- AWS 자격 증명 확인
- Bedrock 모델 액세스 권한 확인
- 리전 설정 확인

## 📈 성능 최적화

### 권장 설정
- **Redis**: 3-5개 노드 클러스터
- **DynamoDB**: On-Demand 빌링 모드
- **EKS**: HPA로 자동 스케일링 (3-100 pods)

### 확장성
- **동시 사용자**: 수만 명 지원
- **세션 처리량**: 초당 수천 건
- **대화 히스토리**: 무제한 저장

## 🤝 기여

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 지원

- **이슈 리포트**: GitHub Issues
- **문서**: `/docs` 엔드포인트
- **API 문서**: `/docs` (Swagger UI)

---

**Made with ❤️ using AWS Strands Agent SDK**