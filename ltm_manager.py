"""
Long Term Memory Manager

사용자의 Long Term Memory를 관리하는 클래스
- LTM 조회
- LTM 업데이트
- SQS 메시지 전송
"""

import boto3
import json
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)

class LongTermMemoryManager:
    """Long Term Memory 관리자"""
    
    def __init__(self, region: str = "ap-northeast-2"):
        self.region = region
        self.sqs = boto3.client('sqs', region_name=region)
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        
        # 테이블 참조
        self.ltm_table = self.dynamodb.Table(
            os.getenv('LTM_TABLE_NAME', 'user_long_term_memory')
        )
        
        self.queue_url = os.getenv('LTM_QUEUE_URL')
        
    def queue_ltm_processing(self, session_id: str, user_id: str, agent_id: str, 
                           message_count: int = 0, metadata: Optional[Dict] = None) -> bool:
        """LTM 처리를 위한 메시지를 SQS에 전송"""
        if not self.queue_url:
            logger.warning("LTM_QUEUE_URL not configured, skipping LTM processing")
            return False
        
        ltm_message = {
            "session_id": session_id,
            "user_id": user_id,
            "agent_id": agent_id,
            "ended_at": datetime.utcnow().isoformat(),
            "message_count": message_count,
            "metadata": metadata or {}
        }
        
        try:
            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(ltm_message),
                MessageAttributes={
                    'MessageType': {
                        'StringValue': 'session_ended',
                        'DataType': 'String'
                    },
                    'UserId': {
                        'StringValue': user_id,
                        'DataType': 'String'
                    },
                    'AgentId': {
                        'StringValue': agent_id,
                        'DataType': 'String'
                    }
                }
            )
            
            logger.info(f"LTM processing queued for session {session_id}, message ID: {response['MessageId']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue LTM processing for session {session_id}: {e}")
            return False
    
    def get_user_ltm(self, user_id: str) -> Optional[Dict[str, Any]]:
        """사용자 Long Term Memory 조회"""
        try:
            response = self.ltm_table.get_item(Key={'user_id': user_id})
            
            if 'Item' not in response:
                return None
            
            item = response['Item']
            
            # Decimal 타입 변환
            return self._convert_decimals(item)
            
        except Exception as e:
            logger.error(f"Error retrieving LTM for user {user_id}: {e}")
            return None
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """사용자 선호도만 조회"""
        ltm = self.get_user_ltm(user_id)
        if ltm:
            return ltm.get('preferences', {})
        return {}
    
    def get_user_interests(self, user_id: str) -> list:
        """사용자 관심사 조회"""
        preferences = self.get_user_preferences(user_id)
        return preferences.get('interests', [])
    
    def get_communication_style(self, user_id: str) -> str:
        """사용자 커뮤니케이션 스타일 조회"""
        preferences = self.get_user_preferences(user_id)
        return preferences.get('preferences', {}).get('communication_style', 'standard')
    
    def get_preferred_agent_type(self, user_id: str) -> str:
        """사용자가 선호하는 에이전트 타입 조회"""
        preferences = self.get_user_preferences(user_id)
        return preferences.get('agent_interaction', {}).get('preferred_agent_type', 'assistant-001')
    
    def update_user_ltm(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """사용자 LTM 직접 업데이트 (관리자용)"""
        try:
            # 기존 LTM 조회
            existing_ltm = self.get_user_ltm(user_id) or {}
            
            # 업데이트된 아이템 생성
            updated_item = {
                'user_id': user_id,
                'updated_at': datetime.utcnow().isoformat(),
                'preferences': preferences,
                'version': int(datetime.utcnow().timestamp()),
                'session_count': existing_ltm.get('session_count', 0),
                'manual_update': True  # 수동 업데이트 표시
            }
            
            # 기존 필드들 유지
            for key in ['last_session_id', 'last_session_ended_at', 'ttl']:
                if key in existing_ltm:
                    updated_item[key] = existing_ltm[key]
            
            self.ltm_table.put_item(Item=updated_item)
            
            logger.info(f"LTM manually updated for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating LTM for user {user_id}: {e}")
            return False
    
    def delete_user_ltm(self, user_id: str) -> bool:
        """사용자 LTM 삭제"""
        try:
            self.ltm_table.delete_item(Key={'user_id': user_id})
            logger.info(f"LTM deleted for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting LTM for user {user_id}: {e}")
            return False
    
    def get_ltm_stats(self) -> Dict[str, Any]:
        """LTM 통계 조회"""
        try:
            # 간단한 통계 (실제로는 더 정교한 쿼리 필요)
            response = self.ltm_table.scan(
                Select='COUNT'
            )
            
            total_users = response['Count']
            
            return {
                'total_users_with_ltm': total_users,
                'table_name': self.ltm_table.table_name,
                'queue_url': self.queue_url,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting LTM stats: {e}")
            return {'error': str(e)}
    
    def _convert_decimals(self, obj):
        """DynamoDB Decimal 타입을 Python 타입으로 변환"""
        if isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._convert_decimals(value) for key, value in obj.items()}
        elif isinstance(obj, Decimal):
            return float(obj) if obj % 1 else int(obj)
        return obj
    
    def create_ltm_table_if_not_exists(self):
        """LTM 테이블이 존재하지 않으면 생성"""
        try:
            # 테이블 존재 확인
            self.ltm_table.load()
            logger.info(f"LTM table {self.ltm_table.table_name} already exists")
        except Exception:
            # 테이블 생성
            logger.info(f"Creating LTM table {self.ltm_table.table_name}")
            table = self.dynamodb.create_table(
                TableName=self.ltm_table.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'user_id',
                        'KeyType': 'HASH'  # Partition key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'user_id',
                        'AttributeType': 'S'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # 테이블 생성 완료 대기
            table.wait_until_exists()
            logger.info(f"LTM table {self.ltm_table.table_name} created successfully")
