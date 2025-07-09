import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain.memory import DynamoDBChatMessageHistory
from langchain.schema import HumanMessage, AIMessage, BaseMessage

logger = logging.getLogger(__name__)

class LangChainHistoryManager:
    """LangChain DynamoDBChatMessageHistory를 사용한 대화 히스토리 관리자"""
    
    def __init__(self, table_name: str = "langchain_chat_history", region: str = "ap-northeast-2"):
        """
        LangChain 히스토리 관리자 초기화
        
        Args:
            table_name: DynamoDB 테이블 이름
            region: AWS 리전
        """
        self.table_name = table_name
        self.region = region
        
    def get_chat_history(self, session_id: str) -> DynamoDBChatMessageHistory:
        """세션별 채팅 히스토리 객체 반환"""
        import os
        
        # 환경 변수로 AWS 리전 설정
        os.environ['AWS_DEFAULT_REGION'] = self.region
        
        return DynamoDBChatMessageHistory(
            table_name=self.table_name,
            session_id=session_id
        )
    
    async def save_conversation(
        self, 
        session_id: str, 
        user_id: str, 
        message: str, 
        response: str, 
        agent_id: str,
        message_type: str = "user",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        대화를 LangChain DynamoDB에 저장
        
        Args:
            session_id: 세션 ID
            user_id: 사용자 ID
            message: 사용자 메시지
            response: 에이전트 응답
            agent_id: 에이전트 ID
            message_type: 메시지 타입
            metadata: 추가 메타데이터
            
        Returns:
            대화 ID (session_id 반환)
        """
        try:
            chat_history = self.get_chat_history(session_id)
            
            # 사용자 메시지 추가
            human_msg = HumanMessage(content=message)
            if metadata:
                human_msg.additional_kwargs = {
                    "user_id": user_id,
                    "agent_id": agent_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    **metadata
                }
            chat_history.add_message(human_msg)
            
            # AI 응답 추가
            ai_msg = AIMessage(content=response)
            ai_msg.additional_kwargs = {
                "user_id": user_id,
                "agent_id": agent_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            chat_history.add_message(ai_msg)
            
            logger.info(f"Saved conversation to LangChain DynamoDB for session {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to save conversation to LangChain: {e}")
            raise
    
    async def get_session_history(
        self, 
        session_id: str, 
        limit: int = 50,
        last_evaluated_key: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        세션의 대화 히스토리 조회
        
        Args:
            session_id: 세션 ID
            limit: 조회할 대화 수
            last_evaluated_key: 페이지네이션용 키 (LangChain에서는 미지원)
            
        Returns:
            대화 히스토리와 페이지네이션 정보
        """
        try:
            chat_history = self.get_chat_history(session_id)
            messages = chat_history.messages
            
            # 최신 메시지부터 limit 개수만큼 가져오기
            if limit > 0:
                messages = messages[-limit:]
            
            # LangChain 메시지를 일반 형식으로 변환
            conversations = []
            for i in range(0, len(messages), 2):
                if i + 1 < len(messages):
                    human_msg = messages[i]
                    ai_msg = messages[i + 1]
                    
                    conversation = {
                        'session_id': session_id,
                        'timestamp': ai_msg.additional_kwargs.get('timestamp', datetime.utcnow().isoformat()),
                        'message': human_msg.content,
                        'response': ai_msg.content,
                        'user_id': ai_msg.additional_kwargs.get('user_id', ''),
                        'agent_id': ai_msg.additional_kwargs.get('agent_id', ''),
                        'message_type': 'user'
                    }
                    conversations.append(conversation)
            
            return {
                'conversations': conversations,
                'count': len(conversations),
                'last_evaluated_key': None,  # LangChain에서는 페이지네이션 미지원
                'has_more': False
            }
            
        except Exception as e:
            logger.error(f"Failed to get session history for {session_id}: {e}")
            return {'conversations': [], 'count': 0, 'has_more': False}
    
    async def get_recent_context(self, session_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        세션의 최근 대화 컨텍스트 조회 (Agent에게 전달용)
        
        Args:
            session_id: 세션 ID
            limit: 조회할 대화 수
            
        Returns:
            최근 대화 목록
        """
        try:
            chat_history = self.get_chat_history(session_id)
            messages = getattr(chat_history, 'messages', [])
            
            if not messages:
                return []
            
            # 최근 limit*2 개의 메시지 (사용자+AI 쌍)
            recent_messages = messages[-(limit*2):] if len(messages) > limit*2 else messages
            
            context = []
            for i in range(0, len(recent_messages), 2):
                if i + 1 < len(recent_messages):
                    human_msg = recent_messages[i]
                    ai_msg = recent_messages[i + 1]
                    
                    context.append({
                        'timestamp': ai_msg.additional_kwargs.get('timestamp', datetime.utcnow().isoformat()),
                        'message': human_msg.content,
                        'response': ai_msg.content,
                        'message_type': 'user'
                    })
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get recent context for {session_id}: {e}")
            # 에러 발생 시 빈 컨텍스트 반환
            return []
    
    async def delete_session_history(self, session_id: str) -> int:
        """
        세션의 모든 대화 히스토리 삭제
        
        Args:
            session_id: 세션 ID
            
        Returns:
            삭제된 대화 수
        """
        try:
            chat_history = self.get_chat_history(session_id)
            message_count = len(chat_history.messages)
            
            # LangChain의 clear() 메서드 사용
            chat_history.clear()
            
            logger.info(f"Deleted {message_count} messages for session {session_id}")
            return message_count
            
        except Exception as e:
            logger.error(f"Failed to delete session history for {session_id}: {e}")
            return 0
    
    async def get_user_history(
        self, 
        user_id: str, 
        limit: int = 100,
        last_evaluated_key: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        사용자의 전체 대화 히스토리 조회
        
        Note: LangChain DynamoDBChatMessageHistory는 사용자별 조회를 직접 지원하지 않음
        이 기능은 제한적으로 구현됨
        
        Args:
            user_id: 사용자 ID
            limit: 조회할 대화 수
            last_evaluated_key: 페이지네이션용 키
            
        Returns:
            대화 히스토리와 페이지네이션 정보
        """
        logger.warning("LangChain DynamoDBChatMessageHistory does not support user-based queries directly")
        return {
            'conversations': [],
            'count': 0,
            'last_evaluated_key': None,
            'has_more': False,
            'error': 'User-based history queries not supported by LangChain DynamoDBChatMessageHistory'
        }
    
    async def get_conversation_stats(self) -> Dict[str, Any]:
        """
        대화 통계 조회
        
        Note: LangChain에서는 전체 통계 조회가 제한적
        
        Returns:
            대화 통계 정보
        """
        return {
            'total_conversations': 0,
            'scanned_count': 0,
            'note': 'Statistics not available with LangChain DynamoDBChatMessageHistory'
        }