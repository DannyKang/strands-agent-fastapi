from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Optional, Any

from models import (
    StrandsSession, CreateSessionRequest, MessageRequest, MessageResponse,
    SessionListResponse, ErrorResponse, SessionStatus
)
from pydantic import BaseModel
from typing import Optional
from session_manager import SessionManager
from memory_session_manager import MemorySessionManager
from strands_client import StrandsAgentClient
from dynamodb_history_manager import DynamoDBHistoryManager
from langchain_history_manager import LangChainHistoryManager
from ltm_manager import LongTermMemoryManager

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JSON 직렬화 유틸리티
def json_serializer(obj: Any) -> Any:
    """JSON 직렬화를 위한 커스텀 시리얼라이저"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

# 요청 모델들
class SessionStatusUpdate(BaseModel):
    status: str
    reason: Optional[str] = "manual"
    metadata: Optional[dict] = None

def safe_json_response(data: dict, status_code: int = 200) -> JSONResponse:
    """안전한 JSON 응답 생성"""
    try:
        json_str = json.dumps(data, default=json_serializer, ensure_ascii=False)
        return JSONResponse(content=json.loads(json_str), status_code=status_code)
    except Exception as e:
        logger.error(f"JSON serialization error: {e}")
        # datetime 객체를 문자열로 변환하여 재시도
        safe_data = convert_datetime_to_str(data)
        return JSONResponse(content=safe_data, status_code=status_code)

def convert_datetime_to_str(obj: Any) -> Any:
    """datetime 객체를 문자열로 재귀적으로 변환"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: convert_datetime_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_str(item) for item in obj]
    else:
        return obj

# 전역 변수
session_manager: Optional[SessionManager] = None
strands_client: Optional[StrandsAgentClient] = None
history_manager: Optional[DynamoDBHistoryManager] = None
ltm_manager: Optional[LongTermMemoryManager] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    global session_manager, strands_client, history_manager, ltm_manager
    
    # 시작 시 초기화
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        session_manager = SessionManager(redis_url=redis_url)
        # Redis 연결 테스트
        session_manager.redis_client.ping()
        logger.info("Using Redis-based session manager")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Using memory-based session manager")
        session_manager = MemorySessionManager()
    
    # Strands Agent 클라이언트 초기화 (최신 SDK)
    model_provider = os.getenv("STRANDS_MODEL_PROVIDER", "bedrock")
    model_id = os.getenv("STRANDS_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    region = os.getenv("STRANDS_REGION", "ap-northeast-2")
    development_mode = os.getenv("DEVELOPMENT_MODE", "true").lower() == "true"
    
    # 추가 모델 설정
    model_kwargs = {}
    if model_provider == "bedrock":
        model_kwargs.update({
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 0.9
        })
    
    strands_client = StrandsAgentClient(
        model_provider=model_provider,
        model_id=model_id,
        region=region,
        **model_kwargs
    )
    
    if development_mode:
        logger.info("Running in development mode with Strands Agent SDK")
    else:
        logger.info("Running in production mode with AWS Bedrock")
    
    # 히스토리 관리자 초기화 (LangChain 또는 Custom DynamoDB)
    use_langchain = os.getenv("USE_LANGCHAIN_HISTORY", "true").lower() == "true"
    table_name = os.getenv("DYNAMODB_HISTORY_TABLE", "langchain_chat_history" if use_langchain else "conversation_history")
    region = os.getenv("AWS_REGION", "ap-northeast-2")
    
    if use_langchain:
        history_manager = LangChainHistoryManager(table_name=table_name, region=region)
        logger.info("Using LangChain DynamoDBChatMessageHistory")
    else:
        history_manager = DynamoDBHistoryManager(table_name=table_name, region=region)
        logger.info("Using Custom DynamoDB History Manager")
    
    try:
        if hasattr(history_manager, 'create_table_if_not_exists'):
            await history_manager.create_table_if_not_exists()
        logger.info("History manager initialized successfully")
    except Exception as e:
        logger.warning(f"History manager initialization failed: {e}. History will not be saved")
        history_manager = None
    
    # Long Term Memory 관리자 초기화
    try:
        ltm_manager = LongTermMemoryManager(region=region)
        ltm_manager.create_ltm_table_if_not_exists()
        logger.info("LTM manager initialized successfully")
    except Exception as e:
        logger.warning(f"LTM manager initialization failed: {e}. LTM features will be disabled")
        ltm_manager = None
    
    logger.info("Application started with Strands Agent integration")
    yield
    
    # 종료 시 정리
    logger.info("Application shutting down")

# FastAPI 앱 생성
app = FastAPI(
    title="Strands Agent Session Manager",
    description="AWS Strands Agent SDK를 사용한 세션 관리 API",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙
app.mount("/static", StaticFiles(directory="static"), name="static")

# 루트 경로 핸들러
@app.get("/")
async def root():
    """루트 경로 - 메인 페이지로 리다이렉트"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html", status_code=307)

@app.get("/favicon.ico")
async def favicon():
    """파비콘 요청 처리"""
    return JSONResponse({"message": "No favicon"}, status_code=404)

def get_session_manager() -> SessionManager:
    """세션 매니저 의존성"""
    if session_manager is None:
        raise HTTPException(status_code=500, detail="Session manager not initialized")
    return session_manager

def get_strands_client() -> StrandsAgentClient:
    """Strands 클라이언트 의존성"""
    if strands_client is None:
        raise HTTPException(status_code=500, detail="Strands client not initialized")
    return strands_client

def get_history_manager():
    """히스토리 관리자 의존성"""
    return history_manager

def get_ltm_manager():
    """LTM 관리자 의존성"""
    return ltm_manager

from fastapi.responses import RedirectResponse
import json
from datetime import datetime
from fastapi import Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.encoders import jsonable_encoder

@app.get("/")
async def root():
    """루트 엔드포인트 - 웹 인터페이스로 리다이렉트"""
    return RedirectResponse(url="/static/index.html")

@app.get("/api")
async def api_info():
    """에이피아이 정보"""
    return {
        "message": "Strands Agent Session Manager API",
        "version": "2.0.0",
        "status": "running",
        "framework": "AWS Strands Agent SDK",
        "documentation": "https://strandsagents.com/latest/"
    }

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트 (최신 Strands Agent SDK)"""
    try:
        # 세션 관리자 연결 확인
        session_mgr = get_session_manager()
        if hasattr(session_mgr, 'redis_client'):
            session_mgr.redis_client.ping()
            storage_type = "redis"
        else:
            session_mgr.ping()
            storage_type = "memory"
        
        # Strands Agent 상태 확인 (최신 API)
        strands = get_strands_client()
        health_result = await strands.health_check()
        
        return {
            "status": "healthy",
            "storage": storage_type,
            "strands_agent": health_result.get("health", {}).get("overall_status", "unknown"),
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "session_manager": "ok",
                "strands_client": "ok",
                "storage": "ok"
            },
            "strands_details": health_result.get("health", {})
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

# 인증 관련 엔드포인트

@app.post("/auth/login")
async def login(request: dict):
    """
    사용자 로그인 (간단한 사용자 ID 기반)
    """
    try:
        user_id = request.get("user_id", "").strip()
        
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
        
        # 간단한 사용자 ID 검증 (실제 환경에서는 더 복잡한 인증 로직 필요)
        if len(user_id) < 2:
            raise HTTPException(status_code=400, detail="User ID must be at least 2 characters")
        
        # 사용자 정보 반환 (실제 환경에서는 JWT 토큰 등 사용)
        return safe_json_response({
            "success": True,
            "user_id": user_id,
            "message": "Login successful",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        return safe_json_response({
            "success": False,
            "error": "Login failed",
            "detail": str(e)
        }, status_code=500)

@app.post("/auth/logout")
async def logout():
    """
    사용자 로그아웃
    """
    return safe_json_response({
        "success": True,
        "message": "Logout successful",
        "timestamp": datetime.utcnow().isoformat()
    })

# 세션 관리 엔드포인트

@app.post("/sessions", response_model=StrandsSession)
async def create_session(
    request: CreateSessionRequest,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """새로운 세션 생성"""
    try:
        session = await session_mgr.create_session(
            user_id=request.user_id,
            agent_id=request.agent_id,
            metadata=request.metadata
        )
        return session
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")

@app.get("/sessions/{session_id}", response_model=StrandsSession)
async def get_session(
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """세션 조회"""
    session = await session_mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@app.patch("/sessions/{session_id}")
async def update_session_status(
    session_id: str,
    update: SessionStatusUpdate,
    session_mgr: SessionManager = Depends(get_session_manager),
    ltm_mgr = Depends(get_ltm_manager)
):
    """세션 상태 업데이트 (종료 포함)"""
    
    # 세션 존재 확인
    session = await session_mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if update.status == "ended":
        # 이미 종료된 세션인지 확인
        if session.status == SessionStatus.EXPIRED:
            return {
                "message": "Session already ended",
                "session_id": session_id,
                "status": "ended",
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "ltm_processing": "already_processed"
            }
        
        # LTM 처리 (메시지가 3개 이상인 경우에만)
        message_count = len(session.conversation_history)
        ltm_queued = False
        
        if ltm_mgr and message_count >= 3:
            try:
                # 메타데이터 준비
                ltm_metadata = {
                    "termination_reason": update.reason,
                    "terminated_at": datetime.utcnow().isoformat(),
                    "ended_via": "patch_api"
                }
                if update.metadata:
                    ltm_metadata.update(update.metadata)
                
                ltm_queued = ltm_mgr.queue_ltm_processing(
                    session_id=session_id,
                    user_id=session.user_id,
                    agent_id=session.agent_id,
                    message_count=message_count,
                    metadata=ltm_metadata
                )
                logger.info(f"LTM processing queued for session {session_id} (reason: {update.reason})")
            except Exception as e:
                logger.error(f"Failed to queue LTM processing for session {session_id}: {e}")
        
        # 세션 삭제 (기존 방식)
        success = await session_mgr.delete_session(session_id)
        if not success:
            logger.warning(f"Failed to delete session {session_id}, but LTM processing was queued")
        
        return {
            "message": "Session ended successfully",
            "session_id": session_id,
            "status": "ended",
            "ended_at": datetime.utcnow().isoformat(),
            "reason": update.reason,
            "ltm_processing": "queued" if ltm_queued else "disabled",
            "message_count": message_count,
            "session_deleted": success
        }
    
    elif update.status == "active":
        # 세션 재활성화는 지원하지 않음 (이미 삭제된 세션은 복구 불가)
        raise HTTPException(
            status_code=400, 
            detail="Session reactivation is not supported. Please create a new session."
        )
    
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status '{update.status}'. Supported statuses: 'ended'"
        )

@app.delete("/sessions/{session_id}")
async def delete_session_permanently(
    session_id: str,
    force: bool = False,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """세션 영구 삭제 (관리자용)"""
    
    session = await session_mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 종료되지 않은 세션은 삭제 불가 (안전장치)
    if session.status != SessionStatus.EXPIRED and not force:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete active session. End the session first or use force=true"
        )
    
    success = await session_mgr.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete session")
    
    return {
        "message": "Session permanently deleted",
        "session_id": session_id,
        "deleted_at": datetime.utcnow().isoformat(),
        "was_forced": force
    }

# sendBeacon을 위한 POST 엔드포인트 (PATCH 시뮬레이션)
@app.post("/sessions/{session_id}")
async def handle_beacon_session_update(
    session_id: str,
    request: Request,
    method: Optional[str] = Form(None),
    data: Optional[str] = Form(None),
    session_mgr: SessionManager = Depends(get_session_manager),
    ltm_mgr = Depends(get_ltm_manager)
):
    """sendBeacon을 통한 세션 상태 업데이트 처리"""
    
    # method가 PATCH인 경우 PATCH 로직 실행
    if method == "PATCH" and data:
        try:
            update_data = json.loads(data)
            update = SessionStatusUpdate(**update_data)
            
            # 기존 PATCH 로직 재사용
            return await update_session_status(session_id, update, session_mgr, ltm_mgr)
            
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON data")
        except Exception as e:
            logger.error(f"Error processing beacon request: {e}")
            raise HTTPException(status_code=400, detail="Invalid request data")
    
    else:
        raise HTTPException(status_code=400, detail="Invalid beacon request")

# 메시지 처리 엔드포인트

@app.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    request: MessageRequest,
    session_mgr: SessionManager = Depends(get_session_manager),
    strands: StrandsAgentClient = Depends(get_strands_client),
    history_mgr = Depends(get_history_manager)
):
    """세션에 메시지 전송 (실제 Strands Agent 사용)"""
    try:
        # 세션 확인
        session = await session_mgr.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.status != SessionStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Session is not active")
        
        # 최근 대화 컨텍스트 가져오기 (에러 처리 개선)
        recent_context = []
        if history_mgr:
            try:
                recent_context = await history_mgr.get_recent_context(session_id, limit=5)
            except Exception as e:
                logger.warning(f"Failed to get recent context from DynamoDB: {e}")
                # Fallback to session conversation history
                recent_context = session.conversation_history[-5:] if session.conversation_history else []
        else:
            recent_context = session.conversation_history[-5:] if session.conversation_history else []
        
        # 실제 Strands Agent에게 메시지 전송
        try:
            agent_response = await strands.send_message(
                agent_id=session.agent_id,
                message=request.message,
                session_context={
                    "session_id": session_id,
                    "user_id": session.user_id,
                    "conversation_history": recent_context,
                    "metadata": session.metadata
                }
            )
            
            if not agent_response.get("success", False):
                error_msg = str(agent_response.get('error', 'Unknown error'))
                logger.error(f"Strands Agent failed: {error_msg}")
                # Fallback response
                response_text = f"죄송합니다. 현재 AI 에이전트에 일시적인 문제가 있습니다. 에러: {error_msg}"
            else:
                response_text = agent_response.get("response", "응답을 생성할 수 없습니다.")
                
        except Exception as e:
            logger.error(f"Strands Agent call failed: {e}")
            # Fallback response
            response_text = f"죄송합니다. AI 에이전트 호출 중 오류가 발생했습니다: {str(e)}"
        
        # DynamoDB에 대화 저장 (에러 처리 개선)
        if history_mgr:
            try:
                await history_mgr.save_conversation(
                    session_id=session_id,
                    user_id=session.user_id,
                    message=request.message,
                    response=response_text,
                    agent_id=session.agent_id,
                    message_type=request.message_type,
                    metadata={
                        "model_provider": "strands",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to save conversation to DynamoDB: {e}")
        
        # 세션에도 대화 기록 추가
        try:
            await session_mgr.add_message_to_session(
                session_id=session_id,
                message=request.message,
                response=response_text,
                message_type=request.message_type
            )
        except Exception as e:
            logger.warning(f"Failed to add message to session: {e}")
        
        # 응답 반환
        response_data = {
            "session_id": session_id,
            "message": request.message,
            "response": response_text,
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": session.agent_id
        }
        
        return safe_json_response(response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process message for session {session_id}: {e}")
        return safe_json_response({
            "error": "Failed to process message",
            "detail": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, status_code=500)

@app.get("/sessions/{session_id}/history")
async def get_conversation_history(
    session_id: str,
    limit: int = 50,
    last_key: Optional[str] = None,
    session_mgr: SessionManager = Depends(get_session_manager),
    history_mgr = Depends(get_history_manager)
):
    """세션의 대화 기록 조회 (DynamoDB 우선)"""
    # 세션 존재 확인
    session = await session_mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # DynamoDB에서 히스토리 조회 시도
    if history_mgr:
        try:
            last_evaluated_key = None
            if last_key:
                import json
                last_evaluated_key = json.loads(last_key)
            
            result = await history_mgr.get_session_history(
                session_id=session_id,
                limit=limit,
                last_evaluated_key=last_evaluated_key
            )
            
            return {
                "session_id": session_id,
                "conversation_history": result['conversations'],
                "total_messages": result['count'],
                "has_more": result['has_more'],
                "last_evaluated_key": json.dumps(result['last_evaluated_key']) if result.get('last_evaluated_key') else None,
                "source": "dynamodb"
            }
        except Exception as e:
            logger.error(f"Failed to get history from DynamoDB: {e}")
    
    # Fallback: 세션에서 히스토리 조회
    history = session.conversation_history[-limit:] if limit > 0 else session.conversation_history
    
    return {
        "session_id": session_id,
        "conversation_history": history,
        "total_messages": len(session.conversation_history),
        "has_more": False,
        "source": "session"
    }

# DynamoDB 히스토리 관리 엔드포인트

@app.get("/users/{user_id}/sessions")
async def get_user_sessions(
    user_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """사용자의 세션 목록 조회 (대화 히스토리 대안)"""
    try:
        # 사용자의 모든 세션 조회
        sessions = await session_mgr.get_user_sessions(user_id, limit=limit)
        
        # 각 세션의 기본 정보와 최근 대화 포함
        session_summaries = []
        for session in sessions:
            # 최근 대화 1개 가져오기
            last_conversation = None
            if session.conversation_history:
                last_conversation = session.conversation_history[-1]
            
            session_summaries.append({
                "session_id": session.session_id,
                "agent_id": session.agent_id,
                "status": session.status.value,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "total_messages": len(session.conversation_history),
                "last_conversation": last_conversation
            })
        
        return safe_json_response({
            "user_id": user_id,
            "sessions": session_summaries,
            "total_sessions": len(session_summaries),
            "note": "Use /sessions/{session_id}/history to get full conversation history for each session"
        })
        
    except Exception as e:
        logger.error(f"Failed to get user sessions for {user_id}: {e}")
        return safe_json_response({
            "error": "Failed to get user sessions",
            "detail": str(e)
        }, status_code=500)

@app.get("/users/{user_id}/history")
async def get_user_conversation_history(
    user_id: str,
    limit: int = 100,
    last_key: Optional[str] = None,
    history_mgr = Depends(get_history_manager)
):
    """사용자의 전체 대화 히스토리 조회"""
    if not history_mgr:
        raise HTTPException(status_code=503, detail="DynamoDB history manager not available")
    
    try:
        last_evaluated_key = None
        if last_key:
            import json
            last_evaluated_key = json.loads(last_key)
        
        result = await history_mgr.get_user_history(
            user_id=user_id,
            limit=limit,
            last_evaluated_key=last_evaluated_key
        )
        
        return {
            "user_id": user_id,
            "conversation_history": result['conversations'],
            "total_messages": result['count'],
            "has_more": result['has_more'],
            "last_evaluated_key": json.dumps(result['last_evaluated_key']) if result.get('last_evaluated_key') else None
        }
    except Exception as e:
        logger.error(f"Failed to get user history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user history")

@app.delete("/sessions/{session_id}/history")
async def delete_session_history(
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager),
    history_mgr = Depends(get_history_manager)
):
    """세션의 대화 히스토리 삭제"""
    # 세션 존재 확인
    session = await session_mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    deleted_count = 0
    
    # DynamoDB에서 히스토리 삭제
    if history_mgr:
        try:
            deleted_count = await history_mgr.delete_session_history(session_id)
        except Exception as e:
            logger.error(f"Failed to delete history from DynamoDB: {e}")
    
    # 세션에서도 히스토리 삭제
    session.conversation_history = []
    await session_mgr.update_session(session)
    
    return {
        "message": "Session history deleted successfully",
        "deleted_count": deleted_count
    }

@app.get("/admin/history/stats")
async def get_history_stats(
    history_mgr = Depends(get_history_manager)
):
    """대화 히스토리 통계 조회"""
    if not history_mgr:
        return {
            "dynamodb_available": False,
            "message": "DynamoDB history manager not available"
        }
    
    try:
        stats = await history_mgr.get_conversation_stats()
        return {
            "dynamodb_available": True,
            "total_conversations": stats['total_conversations'],
            "scanned_count": stats['scanned_count']
        }
    except Exception as e:
        logger.error(f"Failed to get history stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history statistics")

# 예외 처리기
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    content = {
        "error": str(exc.detail),
        "status_code": exc.status_code,
        "timestamp": datetime.utcnow().isoformat()
    }
    return safe_json_response(content, status_code=exc.status_code)

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    content = {
        "error": "Internal server error",
        "message": str(exc),
        "timestamp": datetime.utcnow().isoformat()
    }
    return safe_json_response(content, status_code=500)

# Strands Agent 관리 엔드포인트 (최신 SDK)

@app.get("/agents")
async def list_agents(strands: StrandsAgentClient = Depends(get_strands_client)):
    """사용 가능한 Strands Agent 목록 조회 (최신 API)"""
    result = await strands.list_agents()
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail="Failed to fetch agents")
    return {
        "agents": result.get("agents", []),
        "total": result.get("total", 0),
        "system_status": result.get("system_status", {}),
        "strands_available": result.get("system_status", {}).get("strands_available", False)
    }

@app.get("/agents/{agent_id}")
async def get_agent_info(
    agent_id: str,
    strands: StrandsAgentClient = Depends(get_strands_client)
):
    """Strands Agent 정보 조회 (최신 API)"""
    result = await strands.get_agent_info(agent_id)
    if not result.get("success", False):
        raise HTTPException(status_code=404, detail="Agent not found")
    return result.get("agent_info", {})

@app.get("/agents/capabilities")
async def get_agent_capabilities(strands: StrandsAgentClient = Depends(get_strands_client)):
    """Strands Agent 기능 정보 조회 (최신 API)"""
    result = await strands.get_capabilities()
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail="Failed to get capabilities")
    return result.get("capabilities", {})

@app.post("/debug/test-strands")
async def test_strands_directly(strands: StrandsAgentClient = Depends(get_strands_client)):
    """Debug endpoint to test Strands Agent directly"""
    try:
        result = await strands.send_message(
            agent_id="assistant-001",
            message="Hello, this is a test message",
            session_context={"session_id": "debug", "user_id": "debug_user"}
        )
        return safe_json_response(result)
    except Exception as e:
        return safe_json_response({
            "error": str(e),
            "type": type(e).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }, status_code=500)

# 스트리밍 메시지 엔드포인트 (향후 구현)
@app.post("/sessions/{session_id}/messages/stream")
async def send_message_stream(
    session_id: str,
    request: MessageRequest,
    session_mgr: SessionManager = Depends(get_session_manager),
    strands: StrandsAgentClient = Depends(get_strands_client)
):
    """스트리밍 메시지 전송 (향후 구현)"""
    # TODO: Strands Agent의 스트리밍 기능 구현
    raise HTTPException(status_code=501, detail="Streaming not yet implemented")

# 관리 엔드포인트

@app.post("/admin/cleanup")
async def cleanup_expired_sessions(
    max_age_hours: int = 24,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """만료된 세션 정리 (백그라운드 작업)"""
    background_tasks.add_task(session_mgr.expire_old_sessions, max_age_hours)
    return {"message": "Session cleanup started"}

@app.get("/admin/stats")
async def get_stats(
    session_mgr: SessionManager = Depends(get_session_manager),
    strands: StrandsAgentClient = Depends(get_strands_client)
):
    """시스템 통계 조회 (최신 Strands Agent SDK)"""
    try:
        # Redis에서 세션 관련 키 개수 조회
        session_keys = session_mgr.redis_client.keys(f"{session_mgr.session_prefix}*")
        user_session_keys = session_mgr.redis_client.keys(f"{session_mgr.user_sessions_prefix}*")
        
        # Strands Agent 정보 (최신 API)
        capabilities = await strands.get_capabilities()
        health_check = await strands.health_check()
        
        return {
            "sessions": {
                "total_sessions": len(session_keys),
                "total_users_with_sessions": len(user_session_keys)
            },
            "strands_agent": {
                "available": capabilities.get("success", False),
                "sdk_info": capabilities.get("capabilities", {}).get("sdk_info", {}),
                "model_provider": strands.model_provider,
                "model_id": strands.model_id,
                "health_status": health_check.get("health", {}).get("overall_status", "unknown")
            },
            "redis": {
                "connected": True,
                "url": session_mgr.redis_client.connection_pool.connection_kwargs.get("host", "localhost")
            },
            "system_health": health_check.get("health", {})
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")

# 에러 핸들러

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP 예외 핸들러"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=str(exc.detail) if hasattr(exc, 'detail') else None
        ).model_dump()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """일반 예외 핸들러"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail="An unexpected error occurred"
        ).model_dump()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
