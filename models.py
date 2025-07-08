from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class SessionStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"

class StrandsSession(BaseModel):
    session_id: str = Field(..., description="고유 세션 ID")
    user_id: str = Field(..., description="사용자 ID")
    agent_id: str = Field(..., description="Strands Agent ID")
    status: SessionStatus = Field(default=SessionStatus.ACTIVE, description="세션 상태")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="생성 시간")
    last_activity: datetime = Field(default_factory=datetime.utcnow, description="마지막 활동 시간")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="추가 메타데이터")
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list, description="대화 기록")

class CreateSessionRequest(BaseModel):
    user_id: str = Field(..., description="사용자 ID")
    agent_id: str = Field(..., description="Strands Agent ID")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="추가 메타데이터")

class MessageRequest(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    message: str = Field(..., description="사용자 메시지")
    message_type: str = Field(default="user", description="메시지 타입")

class MessageResponse(BaseModel):
    session_id: str
    message: str
    response: str
    timestamp: datetime
    agent_id: str

class SessionListResponse(BaseModel):
    sessions: List[StrandsSession]
    total: int
    page: int
    size: int

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
