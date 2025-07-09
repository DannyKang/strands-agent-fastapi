# Strands Agent Session Manager 재생성 프롬프트

다음 요구사항에 따라 AWS Strands Agent SDK를 사용한 대화형 AI 세션 관리 시스템을 구축해주세요:

## 🎯 핵심 요구사항

### 1. 아키텍처 설계
- **Stateless FastAPI 서버**: EKS Pod 스케일링 지원
- **Redis 기반 세션 관리**: 고성능 세션 저장 및 조회
- **DynamoDB 대화 히스토리**: 영구 대화 기록 저장
- **하이브리드 저장소**: Redis 장애 시 메모리 기반 fallback

### 2. 기술 스택
- **Backend**: FastAPI, Python 3.10+
- **세션 저장소**: Redis (primary), Memory (fallback)
- **히스토리 저장소**: DynamoDB (us-west-2 또는 ap-northeast-2)
- **AI 모델**: AWS Strands Agent SDK + Bedrock Claude 3.7 Sonnet
- **Frontend**: 반응형 웹 채팅 인터페이스

### 3. 세션 관리 기능
```python
# 세션 생성: UUID4 기반 고유 ID
# 필수 파라미터: user_id, agent_id, metadata(선택)
# TTL: 3600초 (1시간)
# 저장 위치: Redis (primary) + Memory (fallback)
```

### 4. 에이전트 타입
- `assistant-001`: 일반 어시스턴트
- `support-001`: 고객 지원 전문가  
- `analyst-001`: 데이터 분석 전문가

### 5. API 엔드포인트 구조
```
POST /sessions - 세션 생성
GET /sessions/{session_id} - 세션 조회
DELETE /sessions/{session_id} - 세션 삭제
POST /sessions/{session_id}/messages - 메시지 전송
GET /sessions/{session_id}/history - 대화 히스토리 조회
GET /users/{user_id}/sessions - 사용자 세션 목록
GET /users/{user_id}/history - 사용자 전체 히스토리
GET /health - 시스템 상태 확인
GET /agents - 에이전트 목록
GET /admin/stats - 시스템 통계
```

### 6. 대화 히스토리 관리
- **실시간 저장**: 매 대화마다 DynamoDB에 즉시 저장
- **컨텍스트 제공**: 최근 5개 대화를 Agent에게 전달
- **페이지네이션**: 대용량 히스토리 조회 지원
- **사용자별 조회**: GSI를 통한 사용자별 전체 히스토리

### 7. DynamoDB 테이블 설계
```
테이블명: conversation_history
Partition Key: session_id (String)
Sort Key: timestamp (String)
GSI: user_id-timestamp-index
Billing: PAY_PER_REQUEST
```

### 8. 웹 인터페이스 요구사항
- **반응형 디자인**: 모바일/데스크톱 지원
- **실시간 채팅**: 메시지 전송/수신 UI
- **에이전트 선택**: 드롭다운으로 에이전트 변경
- **시스템 상태**: 연결 상태 실시간 표시
- **로딩 상태**: 응답 대기 중 스피너 표시

### 9. 환경 설정
```env
# Redis 설정
REDIS_URL=redis://localhost:6379

# DynamoDB 설정  
DYNAMODB_HISTORY_TABLE=conversation_history
AWS_REGION=ap-northeast-2

# Strands Agent 설정
STRANDS_MODEL_PROVIDER=bedrock
STRANDS_MODEL_ID=anthropic.claude-3-7-sonnet-20250219-v1:0
STRANDS_REGION=ap-northeast-2

# 개발 모드
DEVELOPMENT_MODE=true
```

### 10. 파일 구조
```
agent-fastapi/
├── main.py                    # FastAPI 메인 애플리케이션
├── models.py                  # Pydantic 모델 정의
├── session_manager.py         # Redis 세션 관리자
├── memory_session_manager.py  # 메모리 기반 fallback
├── dynamodb_history_manager.py # DynamoDB 히스토리 관리
├── strands_client.py          # Strands Agent 클라이언트
├── static/
│   ├── index.html            # 메인 채팅 인터페이스
│   └── test.html             # 테스트 페이지
├── requirements.txt           # Python 의존성
├── .env.example              # 환경 변수 예시
├── run.sh                    # 실행 스크립트
├── start_and_test.sh         # 통합 테스트 스크립트
├── test_client.py            # API 테스트 클라이언트
└── README.md                 # 완전한 문서
```

### 11. 핵심 기능 구현 요구사항

#### A. 세션 관리
- UUID4 기반 세션 ID 생성
- Redis 연결 실패 시 메모리 기반 자동 전환
- TTL 기반 자동 만료 (3600초)
- 사용자별 다중 세션 지원

#### B. 대화 처리
- Strands Agent SDK 통합
- 컨텍스트 유지 (최근 5개 대화)
- 실시간 DynamoDB 저장
- 오류 처리 및 fallback

#### C. 웹 인터페이스
- 실시간 채팅 UI
- 에이전트 선택 기능
- 시스템 상태 모니터링
- 반응형 디자인

#### D. 모니터링 및 로깅
- 헬스 체크 엔드포인트
- 상세한 로깅 (INFO 레벨)
- 시스템 통계 제공
- 오류 추적

### 12. 개발 환경 설정
- Python 가상환경 사용
- Docker Redis 컨테이너
- AWS 자격 증명 설정
- VS Code Remote SSH 지원

### 13. 배포 고려사항
- EKS 배포 준비
- 환경별 설정 분리
- CORS 설정 (개발: *, 프로덕션: 제한)
- 보안 설정 (JWT, Rate Limiting 준비)

### 14. 테스트 요구사항
- 자동 테스트 클라이언트 제공
- 헬스 체크 검증
- 세션 생성/조회/삭제 테스트
- 대화 전송 및 히스토리 조회 테스트

## 🚀 실행 방법
1. Redis Docker 컨테이너 실행
2. AWS 자격 증명 설정
3. `./run.sh` 실행
4. `http://localhost:8000` 접속

## 📝 추가 요청사항
- 완전한 README.md 문서 작성
- Git 브랜치 관리 (main, feature/dynamodb-history)
- 환경 변수 예시 파일 제공
- 문제 해결 가이드 포함

이 프롬프트를 사용하여 동일한 기능과 구조를 가진 Strands Agent Session Manager를 재생성해주세요.