import boto3
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal
import json
import logging

logger = logging.getLogger(__name__)

class DynamoDBHistoryManager:
    """DynamoDB를 사용한 대화 히스토리 관리자"""
    
    def __init__(self, table_name: str = "conversation_history", region: str = "us-west-2"):
        """
        DynamoDB 히스토리 관리자 초기화
        
        Args:
            table_name: DynamoDB 테이블 이름
            region: AWS 리전
        """
        self.table_name = table_name
        self.region = region
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
        
    async def create_table_if_not_exists(self):
        """테이블이 존재하지 않으면 생성"""
        try:
            # 테이블 존재 확인
            self.table.load()
            logger.info(f"DynamoDB table {self.table_name} already exists")
        except Exception:
            # 테이블 생성
            logger.info(f"Creating DynamoDB table {self.table_name}")
            table = self.dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'session_id',
                        'KeyType': 'HASH'  # Partition key
                    },
                    {
                        'AttributeName': 'timestamp',
                        'KeyType': 'RANGE'  # Sort key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'session_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'timestamp',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'user_id',
                        'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'user_id-timestamp-index',
                        'KeySchema': [
                            {
                                'AttributeName': 'user_id',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'timestamp',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'BillingMode': 'PAY_PER_REQUEST'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # 테이블 생성 완료 대기
            table.wait_until_exists()
            logger.info(f"DynamoDB table {self.table_name} created successfully")
    
    def _convert_decimals(self, obj):
        """DynamoDB Decimal 타입을 Python 타입으로 변환"""
        if isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._convert_decimals(value) for key, value in obj.items()}
        elif isinstance(obj, Decimal):
            return float(obj) if obj % 1 else int(obj)
        return obj
    
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
        대화를 DynamoDB에 저장
        
        Args:
            session_id: 세션 ID
            user_id: 사용자 ID
            message: 사용자 메시지
            response: 에이전트 응답
            agent_id: 에이전트 ID
            message_type: 메시지 타입
            metadata: 추가 메타데이터
            
        Returns:
            대화 ID
        """
        conversation_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        item = {
            'conversation_id': conversation_id,
            'session_id': session_id,
            'user_id': user_id,
            'timestamp': timestamp,
            'message': message,
            'response': response,
            'agent_id': agent_id,
            'message_type': message_type,
            'metadata': metadata or {},
            'created_at': timestamp
        }
        
        try:
            self.table.put_item(Item=item)
            logger.info(f"Saved conversation {conversation_id} for session {session_id}")
            return conversation_id
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
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
            last_evaluated_key: 페이지네이션용 키
            
        Returns:
            대화 히스토리와 페이지네이션 정보
        """
        try:
            query_params = {
                'KeyConditionExpression': 'session_id = :session_id',
                'ExpressionAttributeValues': {':session_id': session_id},
                'ScanIndexForward': False,  # 최신순 정렬
                'Limit': limit
            }
            
            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key
            
            response = self.table.query(**query_params)
            
            conversations = [self._convert_decimals(item) for item in response['Items']]
            
            return {
                'conversations': conversations,
                'count': len(conversations),
                'last_evaluated_key': response.get('LastEvaluatedKey'),
                'has_more': 'LastEvaluatedKey' in response
            }
            
        except Exception as e:
            logger.error(f"Failed to get session history for {session_id}: {e}")
            return {'conversations': [], 'count': 0, 'has_more': False}
    
    async def get_user_history(
        self, 
        user_id: str, 
        limit: int = 100,
        last_evaluated_key: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        사용자의 전체 대화 히스토리 조회
        
        Args:
            user_id: 사용자 ID
            limit: 조회할 대화 수
            last_evaluated_key: 페이지네이션용 키
            
        Returns:
            대화 히스토리와 페이지네이션 정보
        """
        try:
            query_params = {
                'IndexName': 'user_id-timestamp-index',
                'KeyConditionExpression': 'user_id = :user_id',
                'ExpressionAttributeValues': {':user_id': user_id},
                'ScanIndexForward': False,  # 최신순 정렬
                'Limit': limit
            }
            
            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key
            
            response = self.table.query(**query_params)
            
            conversations = [self._convert_decimals(item) for item in response['Items']]
            
            return {
                'conversations': conversations,
                'count': len(conversations),
                'last_evaluated_key': response.get('LastEvaluatedKey'),
                'has_more': 'LastEvaluatedKey' in response
            }
            
        except Exception as e:
            logger.error(f"Failed to get user history for {user_id}: {e}")
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
        history = await self.get_session_history(session_id, limit)
        conversations = history['conversations']
        
        # 시간순으로 정렬 (오래된 것부터)
        conversations.reverse()
        
        # Agent 컨텍스트 형태로 변환
        context = []
        for conv in conversations:
            context.append({
                'timestamp': conv['timestamp'],
                'message': conv['message'],
                'response': conv['response'],
                'message_type': conv['message_type']
            })
        
        return context
    
    async def delete_session_history(self, session_id: str) -> int:
        """
        세션의 모든 대화 히스토리 삭제
        
        Args:
            session_id: 세션 ID
            
        Returns:
            삭제된 대화 수
        """
        try:
            # 세션의 모든 대화 조회
            response = self.table.query(
                KeyConditionExpression='session_id = :session_id',
                ExpressionAttributeValues={':session_id': session_id},
                ProjectionExpression='session_id, #ts',
                ExpressionAttributeNames={'#ts': 'timestamp'}
            )
            
            deleted_count = 0
            
            # 배치 삭제
            with self.table.batch_writer() as batch:
                for item in response['Items']:
                    batch.delete_item(
                        Key={
                            'session_id': item['session_id'],
                            'timestamp': item['timestamp']
                        }
                    )
                    deleted_count += 1
            
            logger.info(f"Deleted {deleted_count} conversations for session {session_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete session history for {session_id}: {e}")
            return 0
    
    async def get_conversation_stats(self) -> Dict[str, Any]:
        """
        대화 통계 조회
        
        Returns:
            대화 통계 정보
        """
        try:
            # 전체 대화 수 조회 (스캔 사용 - 실제 운영에서는 별도 카운터 테이블 권장)
            response = self.table.scan(
                Select='COUNT'
            )
            
            return {
                'total_conversations': response['Count'],
                'scanned_count': response['ScannedCount']
            }
            
        except Exception as e:
            logger.error(f"Failed to get conversation stats: {e}")
            return {'total_conversations': 0, 'scanned_count': 0}