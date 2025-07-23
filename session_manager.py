import json
import uuid
from datetime import datetime, timedelta
import os
from typing import Optional, List, Dict, Any
import redis
from models import StrandsSession, SessionStatus
import logging
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self, redis_url: Optional[str] = None, session_ttl: int = 3600):
        """
        세션 관리자 초기화
        
        Args:
            redis_url: Redis 연결 URL (None인 경우 .env에서 REDIS_URL 읽음)
            session_ttl: 세션 TTL (초 단위)
        """
        # Redis URL 결정: 파라미터 -> 환경변수 -> 기본값 순서
        if redis_url is None:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.session_ttl = session_ttl
        self.session_prefix = "strands:session:"
        self.user_sessions_prefix = "strands:user_sessions:"
        
        logger.info(f"SessionManager initialized with Redis URL: {redis_url}")
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
    
    async def end_session_with_ltm(self, session_id: str, ltm_manager=None, reason: str = "manual") -> bool:
        """
        세션 종료 및 LTM 처리
        
        Args:
            session_id: 세션 ID
            ltm_manager: LTM 관리자 인스턴스
            reason: 종료 이유 (manual, expired, timeout, system_shutdown)
            
        Returns:
            성공 여부
        """
        try:
            # 세션 정보 조회
            session = await self.get_session(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found for termination")
                return False
            
            # 세션이 이미 종료된 경우 스킵
            if session.status == SessionStatus.EXPIRED:
                logger.info(f"Session {session_id} already expired")
                return True
            
            # 세션 상태를 EXPIRED로 변경
            session.status = SessionStatus.EXPIRED
            session.ended_at = datetime.utcnow()
            session.metadata = session.metadata or {}
            session.metadata['termination_reason'] = reason
            session.metadata['terminated_at'] = session.ended_at.isoformat()
            
            # 세션 업데이트
            await self.update_session(session)
            
            # LTM 처리 (메시지 수가 충분한 경우에만)
            min_messages_for_ltm = 3  # 최소 메시지 수
            message_count = len(session.conversation_history)
            
            if ltm_manager and message_count >= min_messages_for_ltm:
                try:
                    success = ltm_manager.queue_ltm_processing(
                        session_id=session_id,
                        user_id=session.user_id,
                        agent_id=session.agent_id,
                        message_count=message_count,
                        metadata={
                            **session.metadata,
                            'termination_reason': reason,
                            'session_duration': (session.ended_at - session.created_at).total_seconds()
                        }
                    )
                    
                    if success:
                        logger.info(f"LTM processing queued for session {session_id} (reason: {reason})")
                    else:
                        logger.warning(f"Failed to queue LTM processing for session {session_id}")
                        
                except Exception as e:
                    logger.error(f"Error queuing LTM processing for session {session_id}: {e}")
            else:
                if not ltm_manager:
                    logger.debug(f"LTM manager not available for session {session_id}")
                else:
                    logger.info(f"Session {session_id} has insufficient messages ({message_count}) for LTM processing")
            
            # Redis에서 세션 삭제
            session_key = self._get_session_key(session_id)
            self.redis_client.delete(session_key)
            
            # 사용자 세션 목록에서 제거
            user_sessions_key = self._get_user_sessions_key(session.user_id)
            self.redis_client.srem(user_sessions_key, session_id)
            
            logger.info(f"Session {session_id} terminated successfully (reason: {reason})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to end session {session_id}: {e}")
            return False
    
    async def get_user_sessions(self, user_id: str, limit: int = 20) -> List[StrandsSession]:
        """
        사용자의 모든 세션 조회
        
        Args:
            user_id: 사용자 ID
            limit: 조회할 세션 수 제한
            
        Returns:
            사용자의 세션 목록
        """
        try:
            # Redis에서 사용자의 모든 세션 키 조회
            pattern = f"{self.session_prefix}*"
            session_keys = self.redis_client.keys(pattern)
            
            user_sessions = []
            for key in session_keys:
                try:
                    session_data = self.redis_client.get(key)
                    if session_data:
                        session_dict = json.loads(session_data)
                        if session_dict.get('user_id') == user_id:
                            session = StrandsSession(**session_dict)
                            user_sessions.append(session)
                except Exception as e:
                    logger.warning(f"Failed to parse session {key}: {e}")
                    continue
            
            # 최근 활동 순으로 정렬
            user_sessions.sort(key=lambda x: x.last_activity, reverse=True)
            
            # 제한된 수만 반환
            return user_sessions[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get user sessions for {user_id}: {e}")
            return []
    
    async def expire_old_sessions_with_ltm(self, ltm_manager=None, max_age_hours: int = 24, 
                                         max_duration_hours: int = 168) -> Dict[str, int]:
        """
        개선된 세션 만료 처리 (LTM 포함)
        
        Args:
            ltm_manager: LTM 관리자 인스턴스
            max_age_hours: 최대 비활성 시간 (기본 24시간)
            max_duration_hours: 최대 세션 지속 시간 (기본 7일)
            
        Returns:
            만료 처리 결과 통계
        """
        now = datetime.utcnow()
        inactivity_cutoff = now - timedelta(hours=max_age_hours)
        duration_cutoff = now - timedelta(hours=max_duration_hours)
        
        stats = {
            'expired_by_inactivity': 0,
            'expired_by_duration': 0,
            'expired_by_corruption': 0,
            'total_expired': 0
        }
        
        # 모든 세션 키 조회
        session_keys = self.redis_client.keys(f"{self.session_prefix}*")
        
        for session_key in session_keys:
            session_data = self.redis_client.get(session_key)
            if not session_data:
                continue
                
            try:
                session_dict = json.loads(session_data)
                session_id = session_key.replace(self.session_prefix, '')
                
                # 세션 시간 정보 파싱
                last_activity = datetime.fromisoformat(session_dict.get('last_activity', ''))
                created_at = datetime.fromisoformat(session_dict.get('created_at', ''))
                
                # 만료 조건 확인
                reason = None
                if last_activity < inactivity_cutoff:
                    reason = 'expired'
                    stats['expired_by_inactivity'] += 1
                elif created_at < duration_cutoff:
                    reason = 'timeout'
                    stats['expired_by_duration'] += 1
                
                # 세션 종료 처리
                if reason:
                    success = await self.end_session_with_ltm(
                        session_id=session_id,
                        ltm_manager=ltm_manager,
                        reason=reason
                    )
                    if success:
                        stats['total_expired'] += 1
                        
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                # 손상된 데이터 처리
                logger.warning(f"Corrupted session data in {session_key}: {e}")
                self.redis_client.delete(session_key)
                stats['expired_by_corruption'] += 1
                stats['total_expired'] += 1
        
        logger.info(f"Session cleanup completed: {stats}")
        return stats
