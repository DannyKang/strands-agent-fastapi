#!/usr/bin/env python3
"""
Long Term Memory Worker

사용자 대화 종료 시 SQS 큐에서 메시지를 수신하여
대화 히스토리를 분석하고 사용자 선호도를 추출하여
Long Term Memory로 저장하는 백그라운드 워커
"""

import boto3
import json
import time
import logging
import os
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import signal
import sys

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LongTermMemoryWorker:
    """Long Term Memory 처리 워커"""
    
    def __init__(self):
        self.sqs = boto3.client('sqs', region_name=os.getenv('AWS_REGION', 'ap-northeast-2'))
        self.dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'ap-northeast-2'))
        self.bedrock = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION', 'ap-northeast-2'))
        
        # Bedrock 설정
        self.bedrock_model_id = os.getenv("LTM_BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
        self.bedrock_max_tokens = int(os.getenv("LTM_BEDROCK_MAX_TOKENS", "2000"))
        self.bedrock_temperature = float(os.getenv("LTM_BEDROCK_TEMPERATURE", "0.3"))
        
        # 테이블 참조
        self.chat_history_table = self.dynamodb.Table(
            os.getenv('DYNAMODB_HISTORY_TABLE', 'langchain_chat_history')
        )
        self.ltm_table = self.dynamodb.Table(
            os.getenv('LTM_TABLE_NAME', 'user_long_term_memory')
        )
        
        self.queue_url = os.getenv('LTM_QUEUE_URL')
        if not self.queue_url:
            raise ValueError("LTM_QUEUE_URL environment variable is required")
        
        self.running = True
        self.processed_count = 0
        self.error_count = 0
        
        # Graceful shutdown 설정
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Graceful shutdown 핸들러"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        
    def start_processing(self):
        """메인 처리 루프"""
        logger.info("Starting Long Term Memory worker...")
        logger.info(f"Queue URL: {self.queue_url}")
        logger.info(f"Chat History Table: {self.chat_history_table.table_name}")
        logger.info(f"LTM Table: {self.ltm_table.table_name}")
        logger.info(f"Bedrock Model: {self.bedrock_model_id}")
        logger.info(f"Max Tokens: {self.bedrock_max_tokens}, Temperature: {self.bedrock_temperature}")
        
        while self.running:
            try:
                # SQS에서 메시지 수신 (Long polling)
                response = self.sqs.receive_message(
                    QueueUrl=self.queue_url,
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=20,
                    MessageAttributeNames=['All'],
                    AttributeNames=['All']
                )
                
                messages = response.get('Messages', [])
                
                if not messages:
                    logger.debug("No messages received, continuing...")
                    continue
                    
                logger.info(f"Received {len(messages)} messages")
                
                for message in messages:
                    if not self.running:
                        break
                        
                    try:
                        self.process_message(message)
                        
                        # 처리 완료 후 메시지 삭제
                        self.sqs.delete_message(
                            QueueUrl=self.queue_url,
                            ReceiptHandle=message['ReceiptHandle']
                        )
                        
                        self.processed_count += 1
                        logger.info(f"Message processed successfully. Total processed: {self.processed_count}")
                        
                    except Exception as e:
                        self.error_count += 1
                        logger.error(f"Error processing message: {e}")
                        logger.error(f"Message body: {message.get('Body', 'N/A')}")
                        # 메시지는 삭제하지 않음 (재시도 또는 DLQ로 이동)
                        
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received, shutting down...")
                self.running = False
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(5)  # 에러 시 잠시 대기
        
        logger.info(f"Worker stopped. Processed: {self.processed_count}, Errors: {self.error_count}")
    
    def process_message(self, message: Dict[str, Any]):
        """개별 메시지 처리"""
        try:
            # 메시지 파싱
            body = json.loads(message['Body'])
            session_id = body['session_id']
            user_id = body['user_id']
            agent_id = body.get('agent_id', 'unknown')
            ended_at = body.get('ended_at')
            
            logger.info(f"Processing LTM for session {session_id}, user {user_id}, agent {agent_id}")
            
            # 1. 대화 히스토리 조회
            conversation_history = self.get_conversation_history(session_id)
            
            if not conversation_history:
                logger.warning(f"No conversation history found for session {session_id}")
                return
            
            logger.info(f"Found {len(conversation_history)} conversation items")
            
            # 2. AI를 사용하여 사용자 선호도 추출
            preferences = self.extract_user_preferences(conversation_history, user_id, agent_id)
            
            if preferences.get('error'):
                logger.error(f"Failed to extract preferences: {preferences['error']}")
                return
            
            # 3. Long Term Memory 저장
            self.save_long_term_memory(user_id, session_id, preferences, ended_at)
            
            logger.info(f"LTM processing completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error in process_message: {e}")
            raise
    
    def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """DynamoDB에서 대화 히스토리 조회"""
        try:
            # LangChain DynamoDB 구조에 맞게 조회
            response = self.chat_history_table.get_item(
                Key={'SessionId': session_id}
            )
            
            if 'Item' not in response:
                logger.warning(f"No chat history found for session {session_id}")
                return []
            
            item = response['Item']
            if 'History' not in item:
                logger.warning(f"No History field found for session {session_id}")
                return []
            
            # History 필드는 JSON 문자열로 저장됨
            history_str = item['History']
            if isinstance(history_str, str):
                history = json.loads(history_str)
            else:
                history = history_str
            
            return history if isinstance(history, list) else []
            
        except Exception as e:
            logger.error(f"Error retrieving conversation history for {session_id}: {e}")
            return []
    
    def extract_user_preferences(self, conversation_history: List[Dict], user_id: str, agent_id: str) -> Dict[str, Any]:
        """AI를 사용하여 사용자 선호도 추출"""
        
        # 대화 내용을 텍스트로 변환
        conversation_text = self.format_conversation_for_analysis(conversation_history)
        
        if not conversation_text.strip():
            logger.warning(f"Empty conversation text for user {user_id}")
            return {"error": "Empty conversation"}
        
        # AI 프롬프트
        analysis_prompt = f"""다음은 사용자 {user_id}가 {agent_id} 에이전트와 나눈 대화 내용입니다. 
이 대화를 분석하여 사용자의 선호도, 관심사, 행동 패턴을 JSON 형태로 추출해주세요.

대화 내용:
{conversation_text}

다음 형태로 분석 결과를 제공해주세요 (반드시 유효한 JSON 형태로):
{{
    "interests": ["관심사1", "관심사2"],
    "preferences": {{
        "communication_style": "선호하는 대화 스타일",
        "topics_of_interest": ["주제1", "주제2"],
        "problem_solving_approach": "문제 해결 접근 방식"
    }},
    "behavioral_patterns": {{
        "question_types": ["자주 묻는 질문 유형"],
        "interaction_frequency": "상호작용 빈도",
        "session_duration_preference": "선호하는 세션 길이"
    }},
    "context_clues": {{
        "mentioned_tools": ["사용한 도구들"],
        "domain_expertise": "전문 분야",
        "language_preference": "언어 선호도"
    }},
    "agent_interaction": {{
        "preferred_agent_type": "{agent_id}",
        "satisfaction_indicators": ["만족도 지표들"],
        "improvement_suggestions": ["개선 제안사항들"]
    }}
}}

JSON만 반환하고 다른 텍스트는 포함하지 마세요."""
        
        try:

            # Bedrock Claude 사용
            response = self.bedrock.invoke_model(
                modelId=self.bedrock_model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": self.bedrock_max_tokens,
                    "temperature": self.bedrock_temperature,
                    "messages": [
                        {
                            "role": "user",
                            "content": analysis_prompt
                        }
                    ]
                })
            )
            
            result = json.loads(response['body'].read())
            content = result['content'][0]['text']
            
            # JSON 추출 및 파싱
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                preferences = json.loads(json_match.group())
                logger.info(f"Successfully extracted preferences for user {user_id}")
                return preferences
            else:
                logger.error(f"Failed to extract JSON from AI response for user {user_id}")
                return {"error": "Failed to extract JSON from AI response", "raw_response": content}
                
        except Exception as e:
            logger.error(f"Error in AI analysis for user {user_id}: {e}")
            return {"error": str(e)}
    
    def format_conversation_for_analysis(self, conversation_history: List[Dict]) -> str:
        """대화 히스토리를 분석용 텍스트로 포맷팅"""
        formatted_text = ""
        
        try:
            for msg in conversation_history:
                msg_type = msg.get('type', 'unknown')
                msg_data = msg.get('data', {})
                content = msg_data.get('content', '')
                
                if msg_type == 'human':
                    role = "사용자"
                elif msg_type == 'ai':
                    role = "AI"
                else:
                    role = "시스템"
                
                if content:
                    formatted_text += f"{role}: {content}\n\n"
            
            return formatted_text.strip()
            
        except Exception as e:
            logger.error(f"Error formatting conversation: {e}")
            return ""
    
    def save_long_term_memory(self, user_id: str, session_id: str, preferences: Dict[str, Any], ended_at: str):
        """Long Term Memory를 DynamoDB에 저장"""
        try:
            # 기존 LTM 조회
            existing_ltm = self.get_existing_ltm(user_id)
            
            # 새로운 정보와 기존 정보 병합
            updated_ltm = self.merge_preferences(existing_ltm, preferences)
            
            # 메타데이터 추가
            ltm_item = {
                'user_id': user_id,
                'updated_at': datetime.utcnow().isoformat(),
                'last_session_id': session_id,
                'last_session_ended_at': ended_at or datetime.utcnow().isoformat(),
                'preferences': updated_ltm,
                'version': int(time.time()),  # 버전 관리
                'session_count': existing_ltm.get('session_count', 0) + 1,
                'ttl': int((datetime.utcnow() + timedelta(days=365)).timestamp())  # 1년 TTL
            }
            
            # DynamoDB에 저장
            self.ltm_table.put_item(Item=ltm_item)
            
            logger.info(f"LTM saved for user {user_id}, session count: {ltm_item['session_count']}")
            
        except Exception as e:
            logger.error(f"Error saving LTM for user {user_id}: {e}")
            raise
    
    def get_existing_ltm(self, user_id: str) -> Dict[str, Any]:
        """기존 LTM 조회"""
        try:
            response = self.ltm_table.get_item(Key={'user_id': user_id})
            item = response.get('Item', {})
            
            # Decimal 타입 변환
            return self._convert_decimals(item)
            
        except Exception as e:
            logger.error(f"Error retrieving existing LTM for user {user_id}: {e}")
            return {}
    
    def _convert_decimals(self, obj):
        """DynamoDB Decimal 타입을 Python 타입으로 변환"""
        if isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._convert_decimals(value) for key, value in obj.items()}
        elif isinstance(obj, Decimal):
            return float(obj) if obj % 1 else int(obj)
        return obj
    
    def merge_preferences(self, existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """기존 선호도와 새로운 선호도 병합"""
        if not existing:
            return new
        
        # 기존 preferences 가져오기
        existing_prefs = existing.get('preferences', {})
        
        # 병합 로직
        merged = existing_prefs.copy()
        
        for key, value in new.items():
            if key in merged:
                if isinstance(value, list) and isinstance(merged[key], list):
                    # 리스트는 중복 제거하여 병합
                    merged[key] = list(set(merged[key] + value))
                elif isinstance(value, dict) and isinstance(merged[key], dict):
                    # 딕셔너리는 재귀적으로 병합
                    merged[key] = self.merge_preferences({"preferences": merged[key]}, value).get('preferences', {})
                else:
                    # 새로운 값으로 덮어쓰기 (최신 정보 우선)
                    merged[key] = value
            else:
                merged[key] = value
        
        return merged

def main():
    """메인 함수"""
    try:
        worker = LongTermMemoryWorker()
        worker.start_processing()
    except Exception as e:
        logger.error(f"Failed to start LTM worker: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
