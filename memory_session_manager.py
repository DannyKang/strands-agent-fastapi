import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from models import StrandsSession, SessionStatus
import logging

logger = logging.getLogger(__name__)

class MemorySessionManager:
    """메모리 기반 세션 관리자 (개발용)"""
    
    def __init__(self, session_ttl: int = 3600):
        """
        메모리 세션 관리자 초기화
        
        Args:
            session_ttl: 세션 TTL (초 단위)
        """
        self.sessions: Dict[str, StrandsSession] = {}
        self.user_sessions: Dict[str, set] = {}
        self.session_ttl = session_ttl
        
    def ping(self):
        """Redis ping 메서드 호환성을 위한 더미 메서드"""
        return True
        
    async def create_session(self, user_id: str, agent_id: str, metadata: Optional[Dict[str, Any]] = None) -> StrandsSession:
        """새로운 세션 생성"""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        session = StrandsSession(
            session_id=session_id,
            user_id=user_id,
            agent_id=agent_id,
            status=SessionStatus.ACTIVE,
            created_at=now,
            last_activity=now,
            metadata=metadata or {},
            conversation_history=[]
        )
        
        # 메모리에 세션 저장
        self.sessions[session_id] = session
        
        # 사용자별 세션 목록에 추가
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(session_id)
        
        logger.info(f"Created session {session_id} for user {user_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[StrandsSession]:
        """세션 조회"""
        session = self.sessions.get(session_id)
        if session:
            # TTL 체크
            if datetime.utcnow() - session.last_activity > timedelta(seconds=self.session_ttl):
                await self.delete_session(session_id)
                return None
        return session
    
    async def update_session(self, session: StrandsSession) -> bool:
        """세션 업데이트"""
        session.last_activity = datetime.utcnow()
        self.sessions[session.session_id] = session
        logger.info(f"Updated session {session.session_id}")
        return True
    
    async def delete_session(self, session_id: str) -> bool:
        """세션 삭제"""
        session = self.sessions.get(session_id)
        if not session:
            return False
            
        # 세션 삭제
        del self.sessions[session_id]
        
        # 사용자 세션 목록에서 제거
        if session.user_id in self.user_sessions:
            self.user_sessions[session.user_id].discard(session_id)
            if not self.user_sessions[session.user_id]:
                del self.user_sessions[session.user_id]
        
        logger.info(f"Deleted session {session_id}")
        return True
    
    async def get_user_sessions(self, user_id: str, active_only: bool = True) -> List[StrandsSession]:
        """사용자의 세션 목록 조회"""
        if user_id not in self.user_sessions:
            return []
            
        sessions = []
        for session_id in list(self.user_sessions[user_id]):
            session = await self.get_session(session_id)
            if session:
                if not active_only or session.status == SessionStatus.ACTIVE:
                    sessions.append(session)
        
        # 마지막 활동 시간 기준으로 정렬
        sessions.sort(key=lambda x: x.last_activity, reverse=True)
        return sessions
    
    async def add_message_to_session(self, session_id: str, message: str, response: str, message_type: str = "user") -> bool:
        """세션에 메시지 추가"""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        # 대화 기록에 메시지 추가
        conversation_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "response": response,
            "message_type": message_type
        }
        
        session.conversation_history.append(conversation_entry)
        
        # 대화 기록이 너무 길어지지 않도록 제한 (최근 100개만 유지)
        if len(session.conversation_history) > 100:
            session.conversation_history = session.conversation_history[-100:]
        
        return await self.update_session(session)
    
    async def expire_old_sessions(self, max_age_hours: int = 24) -> int:
        """오래된 세션 만료 처리"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        expired_count = 0
        
        # 만료된 세션 찾기
        expired_sessions = []
        for session_id, session in self.sessions.items():
            if session.last_activity < cutoff_time:
                expired_sessions.append(session_id)
        
        # 만료된 세션 삭제
        for session_id in expired_sessions:
            await self.delete_session(session_id)
            expired_count += 1
        
        logger.info(f"Expired {expired_count} old sessions")
        return expired_count