from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Optional

from models import (
    StrandsSession, CreateSessionRequest, MessageRequest, MessageResponse,
    SessionListResponse, ErrorResponse, SessionStatus
)
from session_manager import SessionManager
from memory_session_manager import MemorySessionManager
from strands_client import StrandsAgentClient
from dynamodb_history_manager import DynamoDBHistoryManager

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 전역 변수
session_manager: Optional[SessionManager] = None
strands_client: Optional[StrandsAgentClient] = None
history_manager: Optional[DynamoDBHistoryManager] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    global session_manager, strands_client, history_manager
    
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
    
    # Strands Agent 클라이언트 초기화
    model_provider = os.getenv("STRANDS_MODEL_PROVIDER", "bedrock")
    model_id = os.getenv("STRANDS_MODEL_ID", "anthropic.claude-3-7-sonnet-20250219-v1:0")
    region = os.getenv("STRANDS_REGION", "ap-northeast-2")
    development_mode = os.getenv("DEVELOPMENT_MODE", "true").lower() == "true"
    
    strands_client = StrandsAgentClient(
        model_provider=model_provider,
        model_id=model_id,
        region=region
    )
    
    if development_mode:
        logger.info("Running in development mode with Strands Agent SDK")
    else:
        logger.info("Running in production mode with AWS Bedrock")
    
    # DynamoDB 히스토리 관리자 초기화
    table_name = os.getenv("DYNAMODB_HISTORY_TABLE", "conversation_history")
    region = os.getenv("AWS_REGION", "ap-northeast-2")
    
    history_manager = DynamoDBHistoryManager(table_name=table_name, region=region)
    
    try:
        await history_manager.create_table_if_not_exists()
        logger.info("DynamoDB history manager initialized")
    except Exception as e:
        logger.warning(f"DynamoDB initialization failed: {e}. History will not be saved to DynamoDB")
        history_manager = None
    
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

def get_history_manager() -> Optional[DynamoDBHistoryManager]:
    """히스토리 관리자 의존성"""
    return history_manager

from fastapi.responses import RedirectResponse
import json

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
    """헬스 체크 엔드포인트"""
    try:
        # 세션 관리자 연결 확인
        session_mgr = get_session_manager()
        if hasattr(session_mgr, 'redis_client'):
            session_mgr.redis_client.ping()
            storage_type = "redis"
        else:
            session_mgr.ping()
            storage_type = "memory"
        
        # Strands Agent 상태 확인
        strands = get_strands_client()
        capabilities = await strands.get_agent_capabilities()
        
        return {
            "status": "healthy",
            "storage": storage_type,
            "strands_agent": "available" if capabilities.get("success") else "limited",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "session_manager": "ok",
                "strands_client": "ok",
                "storage": "ok"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

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

@app.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """세션 삭제"""
    success = await session_mgr.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted successfully"}

@app.get("/users/{user_id}/sessions", response_model=List[StrandsSession])
async def get_user_sessions(
    user_id: str,
    active_only: bool = True,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """사용자의 세션 목록 조회"""
    sessions = await session_mgr.get_user_sessions(user_id, active_only)
    return sessions

# 메시지 처리 엔드포인트

@app.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def send_message(
    session_id: str,
    request: MessageRequest,
    session_mgr: SessionManager = Depends(get_session_manager),
    strands: StrandsAgentClient = Depends(get_strands_client),
    history_mgr: Optional[DynamoDBHistoryManager] = Depends(get_history_manager)
):
    """세션에 메시지 전송 (Strands Agent 사용)"""
    # 세션 확인
    session = await session_mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")
    
    try:
        # DynamoDB에서 최근 대화 컨텍스트 가져오기
        recent_context = []
        if history_mgr:
            try:
                recent_context = await history_mgr.get_recent_context(session_id, limit=5)
            except Exception as e:
                logger.warning(f"Failed to get recent context from DynamoDB: {e}")
                # Fallback to session conversation history
                recent_context = session.conversation_history[-5:]
        else:
            recent_context = session.conversation_history[-5:]
        
        # Strands Agent에게 메시지 전송
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
            raise HTTPException(
                status_code=500, 
                detail=f"Strands Agent communication failed: {agent_response.get('error', 'Unknown error')}"
            )
        
        response_text = agent_response.get("response", "")
        
        # DynamoDB에 대화 저장
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
                        "model_provider": agent_response.get("metadata", {}).get("model_provider"),
                        "model_id": agent_response.get("metadata", {}).get("model_id"),
                        "timestamp": agent_response.get("timestamp")
                    }
                )
            except Exception as e:
                logger.error(f"Failed to save conversation to DynamoDB: {e}")
        
        # 세션에도 대화 기록 추가 (fallback 및 빠른 접근용)
        await session_mgr.add_message_to_session(
            session_id=session_id,
            message=request.message,
            response=response_text,
            message_type=request.message_type
        )
        
        return MessageResponse(
            session_id=session_id,
            message=request.message,
            response=response_text,
            timestamp=session.last_activity,
            agent_id=session.agent_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process message for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message")

@app.get("/sessions/{session_id}/history")
async def get_conversation_history(
    session_id: str,
    limit: int = 50,
    last_key: Optional[str] = None,
    session_mgr: SessionManager = Depends(get_session_manager),
    history_mgr: Optional[DynamoDBHistoryManager] = Depends(get_history_manager)
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

@app.get("/users/{user_id}/history")
async def get_user_conversation_history(
    user_id: str,
    limit: int = 100,
    last_key: Optional[str] = None,
    history_mgr: Optional[DynamoDBHistoryManager] = Depends(get_history_manager)
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
    history_mgr: Optional[DynamoDBHistoryManager] = Depends(get_history_manager)
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
    history_mgr: Optional[DynamoDBHistoryManager] = Depends(get_history_manager)
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

# Strands Agent 관리 엔드포인트

@app.get("/agents")
async def list_agents(strands: StrandsAgentClient = Depends(get_strands_client)):
    """사용 가능한 Strands Agent 목록 조회"""
    result = await strands.list_agents()
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail="Failed to fetch agents")
    return {
        "agents": result.get("agents", []),
        "total": result.get("total", 0),
        "strands_available": result.get("strands_available", False)
    }

@app.get("/agents/{agent_id}")
async def get_agent_info(
    agent_id: str,
    strands: StrandsAgentClient = Depends(get_strands_client)
):
    """Strands Agent 정보 조회"""
    result = await strands.get_agent_info(agent_id)
    if not result.get("success", False):
        raise HTTPException(status_code=404, detail="Agent not found")
    return result.get("agent_info", {})

@app.get("/agents/capabilities")
async def get_agent_capabilities(strands: StrandsAgentClient = Depends(get_strands_client)):
    """Strands Agent 기능 정보 조회"""
    result = await strands.get_agent_capabilities()
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail="Failed to get capabilities")
    return result.get("capabilities", {})

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
    """시스템 통계 조회"""
    try:
        # Redis에서 세션 관련 키 개수 조회
        session_keys = session_mgr.redis_client.keys(f"{session_mgr.session_prefix}*")
        user_session_keys = session_mgr.redis_client.keys(f"{session_mgr.user_sessions_prefix}*")
        
        # Strands Agent 정보
        capabilities = await strands.get_agent_capabilities()
        
        return {
            "sessions": {
                "total_sessions": len(session_keys),
                "total_users_with_sessions": len(user_session_keys)
            },
            "strands_agent": {
                "available": capabilities.get("success", False),
                "sdk_version": capabilities.get("strands_sdk_version", "unknown"),
                "model_provider": strands.model_provider,
                "model_id": strands.model_id
            },
            "redis": {
                "connected": True,
                "url": session_mgr.redis_client.connection_pool.connection_kwargs.get("host", "localhost")
            }
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
