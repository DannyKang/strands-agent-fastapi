import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import redis
from models import StrandsSession, SessionStatus
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self, redis_url: str = "redis://localhost:6379", session_ttl: int = 3600):
        """
        세션 관리자 초기화
        
        Args:
            redis_url: Redis 연결 URL
            session_ttl: 세션 TTL (초 단위)
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.session_ttl = session_ttl
        self.session_prefix = "strands:session:"
        self.user_sessions_prefix = "strands:user_sessions:"
        
    def _get_session_key(self, session_id: str) -> str:
        """세션 키 생성"""
        return f"{self.session_prefix}{session_id}"
    
    def _get_user_sessions_key(self, user_id: str) -> str:
        """사용자 세션 목록 키 생성"""
        return f"{self.user_sessions_prefix}{user_id}"
    
    async def create_session(self, user_id: str, agent_id: str, metadata: Optional[Dict[str, Any]] = None) -> StrandsSession:
        """
        새로운 세션 생성
        
        Args:
            user_id: 사용자 ID
            agent_id: Strands Agent ID
            metadata: 추가 메타데이터
            
        Returns:
            생성된 세션 객체
        """
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
        
        # Redis에 세션 저장
        session_key = self._get_session_key(session_id)
        session_data = session.model_dump_json()
        
        # 세션 데이터 저장 (TTL 설정)
        self.redis_client.setex(session_key, self.session_ttl, session_data)
        
        # 사용자별 세션 목록에 추가
        user_sessions_key = self._get_user_sessions_key(user_id)
        self.redis_client.sadd(user_sessions_key, session_id)
        self.redis_client.expire(user_sessions_key, self.session_ttl)
        
        logger.info(f"Created session {session_id} for user {user_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[StrandsSession]:
        """
        세션 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            세션 객체 또는 None
        """
        session_key = self._get_session_key(session_id)
        session_data = self.redis_client.get(session_key)
        
        if not session_data:
            return None
            
        try:
            session_dict = json.loads(session_data)
            return StrandsSession(**session_dict)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse session data for {session_id}: {e}")
            return None
    
    async def update_session(self, session: StrandsSession) -> bool:
        """
        세션 업데이트
        
        Args:
            session: 업데이트할 세션 객체
            
        Returns:
            성공 여부
        """
        session_key = self._get_session_key(session.session_id)
        
        # 마지막 활동 시간 업데이트
        session.last_activity = datetime.utcnow()
        
        try:
            session_data = session.model_dump_json()
            self.redis_client.setex(session_key, self.session_ttl, session_data)
            logger.info(f"Updated session {session.session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update session {session.session_id}: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제
        
        Args:
            session_id: 세션 ID
            
        Returns:
            성공 여부
        """
        session = await self.get_session(session_id)
        if not session:
            return False
            
        session_key = self._get_session_key(session_id)
        user_sessions_key = self._get_user_sessions_key(session.user_id)
        
        # 세션 데이터 삭제
        self.redis_client.delete(session_key)
        
        # 사용자 세션 목록에서 제거
        self.redis_client.srem(user_sessions_key, session_id)
        
        logger.info(f"Deleted session {session_id}")
        return True
    
    async def get_user_sessions(self, user_id: str, active_only: bool = True) -> List[StrandsSession]:
        """
        사용자의 세션 목록 조회
        
        Args:
            user_id: 사용자 ID
            active_only: 활성 세션만 조회할지 여부
            
        Returns:
            세션 목록
        """
        user_sessions_key = self._get_user_sessions_key(user_id)
        session_ids = self.redis_client.smembers(user_sessions_key)
        
        sessions = []
        for session_id in session_ids:
            session = await self.get_session(session_id)
            if session:
                if not active_only or session.status == SessionStatus.ACTIVE:
                    sessions.append(session)
        
        # 마지막 활동 시간 기준으로 정렬
        sessions.sort(key=lambda x: x.last_activity, reverse=True)
        return sessions
    
    async def add_message_to_session(self, session_id: str, message: str, response: str, message_type: str = "user") -> bool:
        """
        세션에 메시지 추가
        
        Args:
            session_id: 세션 ID
            message: 사용자 메시지
            response: 에이전트 응답
            message_type: 메시지 타입
            
        Returns:
            성공 여부
        """
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
        """
        오래된 세션 만료 처리
        
        Args:
            max_age_hours: 최대 세션 유지 시간 (시간 단위)
            
        Returns:
            만료 처리된 세션 수
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        expired_count = 0
        
        # 모든 세션 키 조회
        session_keys = self.redis_client.keys(f"{self.session_prefix}*")
        
        for session_key in session_keys:
            session_data = self.redis_client.get(session_key)
            if session_data:
                try:
                    session_dict = json.loads(session_data)
                    last_activity = datetime.fromisoformat(session_dict.get('last_activity', ''))
                    
                    if last_activity < cutoff_time:
                        session_id = session_key.replace(self.session_prefix, '')
                        await self.delete_session(session_id)
                        expired_count += 1
                        
                except (json.JSONDecodeError, ValueError, TypeError):
                    # 잘못된 데이터는 삭제
                    self.redis_client.delete(session_key)
                    expired_count += 1
        
        logger.info(f"Expired {expired_count} old sessions")
        return expired_count
