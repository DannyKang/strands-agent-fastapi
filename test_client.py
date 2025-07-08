import asyncio
import httpx
import json
from datetime import datetime

class StrandsSessionClient:
    """Strands Agent Session API 테스트 클라이언트"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient()
    
    async def close(self):
        """클라이언트 종료"""
        await self.client.aclose()
    
    async def health_check(self):
        """헬스 체크"""
        response = await self.client.get(f"{self.base_url}/health")
        return response.json() if response.status_code == 200 else None
    
    async def get_agent_capabilities(self):
        """에이전트 기능 조회"""
        response = await self.client.get(f"{self.base_url}/agents/capabilities")
        return response.json() if response.status_code == 200 else None
    
    async def create_session(self, user_id: str, agent_id: str, metadata: dict = None):
        """세션 생성"""
        payload = {
            "user_id": user_id,
            "agent_id": agent_id,
            "metadata": metadata or {}
        }
        
        response = await self.client.post(f"{self.base_url}/sessions", json=payload)
        return response.json() if response.status_code == 200 else None
    
    async def get_session(self, session_id: str):
        """세션 조회"""
        response = await self.client.get(f"{self.base_url}/sessions/{session_id}")
        return response.json() if response.status_code == 200 else None
    
    async def send_message(self, session_id: str, message: str):
        """메시지 전송"""
        payload = {
            "session_id": session_id,
            "message": message,
            "message_type": "user"
        }
        
        response = await self.client.post(
            f"{self.base_url}/sessions/{session_id}/messages", 
            json=payload
        )
        return response.json() if response.status_code == 200 else None
    
    async def get_conversation_history(self, session_id: str, limit: int = 10):
        """대화 기록 조회"""
        response = await self.client.get(
            f"{self.base_url}/sessions/{session_id}/history?limit={limit}"
        )
        return response.json() if response.status_code == 200 else None
    
    async def get_user_sessions(self, user_id: str, active_only: bool = True):
        """사용자 세션 목록 조회"""
        response = await self.client.get(
            f"{self.base_url}/users/{user_id}/sessions?active_only={active_only}"
        )
        return response.json() if response.status_code == 200 else None
    
    async def list_agents(self):
        """에이전트 목록 조회"""
        response = await self.client.get(f"{self.base_url}/agents")
        return response.json() if response.status_code == 200 else None
    
    async def get_agent_info(self, agent_id: str):
        """에이전트 정보 조회"""
        response = await self.client.get(f"{self.base_url}/agents/{agent_id}")
        return response.json() if response.status_code == 200 else None
    
    async def get_stats(self):
        """시스템 통계 조회"""
        response = await self.client.get(f"{self.base_url}/admin/stats")
        return response.json() if response.status_code == 200 else None
    
    async def delete_session(self, session_id: str):
        """세션 삭제"""
        response = await self.client.delete(f"{self.base_url}/sessions/{session_id}")
        return response.status_code == 200

async def demo_strands_conversation():
    """Strands Agent 데모 대화 시나리오"""
    client = StrandsSessionClient()
    
    try:
        print("=== AWS Strands Agent Session Manager 데모 ===\n")
        
        # 0. 헬스 체크
        print("0. 시스템 상태 확인")
        health = await client.health_check()
        if health:
            print(f"✅ 시스템 상태: {health.get('status')}")
            print(f"   Redis: {health.get('redis')}")
            print(f"   Strands Agent: {health.get('strands_agent')}")
            print(f"   구성 요소: {health.get('components', {})}")
        else:
            print("❌ 시스템 상태 확인 실패")
            return
        print()
        
        # 1. Strands Agent 기능 확인
        print("1. Strands Agent 기능 확인")
        capabilities = await client.get_agent_capabilities()
        if capabilities:
            print(f"모델 제공자: {capabilities.get('model_providers', [])}")
            print(f"기본 모델: {capabilities.get('default_model')}")
            print("사용 가능한 도구:")
            for tool in capabilities.get('tools', []):
                print(f"  - {tool['name']}: {tool['description']}")
            print("지원 기능:")
            for feature in capabilities.get('features', []):
                print(f"  - {feature}")
        print()
        
        # 2. 사용 가능한 에이전트 목록 조회
        print("2. 사용 가능한 Strands Agent 목록 조회")
        agents_result = await client.list_agents()
        if agents_result:
            agents = agents_result.get('agents', [])
            print(f"사용 가능한 에이전트: {len(agents)}개")
            for agent in agents:
                print(f"  - {agent['id']}: {agent['name']}")
                print(f"    설명: {agent['description']}")
                print(f"    기능: {', '.join(agent.get('capabilities', []))}")
        print()
        
        # 3. 새 세션 생성
        print("3. 새 세션 생성")
        user_id = "demo_user_123"
        agent_id = "assistant-001"  # 일반 어시스턴트
        
        session = await client.create_session(
            user_id=user_id,
            agent_id=agent_id,
            metadata={
                "demo": True, 
                "created_by": "strands_test_client",
                "agent_type": "general_assistant"
            }
        )
        
        if session:
            session_id = session['session_id']
            print(f"✅ 세션 생성 성공: {session_id}")
            print(f"   사용자: {session['user_id']}")
            print(f"   에이전트: {session['agent_id']}")
            print(f"   상태: {session['status']}")
        else:
            print("❌ 세션 생성 실패")
            return
        print()
        
        # 4. Strands Agent와 대화
        print("4. Strands Agent와 대화 시작")
        messages = [
            "안녕하세요! AWS Strands Agent에 대해 설명해주세요.",
            "현재 시간이 몇 시인가요?",
            "간단한 계산을 해주세요: 25 * 4 + 10",
            "FastAPI와 Strands Agent를 함께 사용하는 장점은 무엇인가요?",
            "감사합니다!"
        ]
        
        for i, message in enumerate(messages, 1):
            print(f"[{i}] 사용자: {message}")
            
            response = await client.send_message(session_id, message)
            if response:
                print(f"    Strands Agent: {response['response']}")
                print(f"    응답 시간: {response.get('timestamp', 'N/A')}")
                if 'metadata' in response:
                    metadata = response['metadata']
                    print(f"    모델: {metadata.get('model_id', 'N/A')}")
                    print(f"    도구 수: {metadata.get('tools_used', 'N/A')}")
            else:
                print("    ❌ 응답 받기 실패")
            print()
            
            # 잠시 대기
            await asyncio.sleep(1)
        
        # 5. 대화 기록 조회
        print("5. 대화 기록 조회")
        history = await client.get_conversation_history(session_id)
        if history:
            print(f"총 대화 수: {history['total_messages']}")
            print("최근 대화 (최대 3개):")
            for entry in history['conversation_history'][-3:]:
                print(f"  [{entry['timestamp']}]")
                print(f"  사용자: {entry['message']}")
                print(f"  에이전트: {entry['response'][:100]}...")
                print()
        
        # 6. 다른 에이전트로 세션 생성 및 테스트
        print("6. 고객 지원 에이전트 테스트")
        support_session = await client.create_session(
            user_id=user_id,
            agent_id="support-001",
            metadata={"demo": True, "agent_type": "customer_support"}
        )
        
        if support_session:
            support_session_id = support_session['session_id']
            print(f"✅ 고객 지원 세션 생성: {support_session_id}")
            
            # 고객 지원 메시지 테스트
            support_message = "제품 사용 중 문제가 발생했습니다. 도움을 받을 수 있나요?"
            print(f"사용자: {support_message}")
            
            support_response = await client.send_message(support_session_id, support_message)
            if support_response:
                print(f"고객지원 Agent: {support_response['response']}")
            print()
        
        # 7. 사용자의 모든 세션 조회
        print("7. 사용자 세션 목록 조회")
        user_sessions = await client.get_user_sessions(user_id)
        if user_sessions:
            print(f"사용자 {user_id}의 활성 세션: {len(user_sessions)}개")
            for session in user_sessions:
                print(f"  - {session['session_id']} ({session['agent_id']})")
                print(f"    생성: {session['created_at']}")
                print(f"    마지막 활동: {session['last_activity']}")
        print()
        
        # 8. 시스템 통계 조회
        print("8. 시스템 통계 조회")
        stats = await client.get_stats()
        if stats:
            print("세션 통계:")
            session_stats = stats.get('sessions', {})
            print(f"  총 세션 수: {session_stats.get('total_sessions', 0)}")
            print(f"  세션을 가진 사용자 수: {session_stats.get('total_users_with_sessions', 0)}")
            
            print("Strands Agent 정보:")
            strands_stats = stats.get('strands_agent', {})
            print(f"  사용 가능: {strands_stats.get('available', False)}")
            print(f"  SDK 버전: {strands_stats.get('sdk_version', 'N/A')}")
            print(f"  모델 제공자: {strands_stats.get('model_provider', 'N/A')}")
            print(f"  모델 ID: {strands_stats.get('model_id', 'N/A')}")
        print()
        
        # 9. 세션 삭제 (선택사항)
        print("9. 세션 정리")
        delete_confirm = input("테스트 세션들을 삭제하시겠습니까? (y/N): ").lower().strip()
        if delete_confirm == 'y':
            # 메인 세션 삭제
            success1 = await client.delete_session(session_id)
            print(f"메인 세션 삭제: {'성공' if success1 else '실패'}")
            
            # 지원 세션 삭제 (있는 경우)
            if 'support_session_id' in locals():
                success2 = await client.delete_session(support_session_id)
                print(f"지원 세션 삭제: {'성공' if success2 else '실패'}")
        else:
            print("세션을 유지합니다.")
        
        print("\n=== AWS Strands Agent 데모 완료 ===")
        
    except Exception as e:
        print(f"❌ 데모 실행 중 오류 발생: {e}")
    finally:
        await client.close()

async def simple_strands_test():
    """간단한 Strands Agent API 테스트"""
    client = StrandsSessionClient()
    
    try:
        print("=== 간단한 Strands Agent 테스트 ===\n")
        
        # 헬스 체크
        response = await client.health_check()
        if response and response.get('status') == 'healthy':
            print("✅ API 서버가 정상적으로 실행 중입니다.")
            print(f"   Strands Agent: {response.get('strands_agent')}")
        else:
            print("❌ API 서버에 연결할 수 없습니다.")
            return
        
        # 에이전트 목록 확인
        agents_result = await client.list_agents()
        if agents_result:
            print(f"✅ {len(agents_result.get('agents', []))}개의 에이전트 사용 가능")
        
        # 간단한 세션 생성 및 메시지 테스트
        print("\n간단한 세션 테스트...")
        session = await client.create_session("test_user", "assistant-001")
        if session:
            print(f"✅ 세션 생성 성공: {session['session_id']}")
            
            # 메시지 전송
            response = await client.send_message(session['session_id'], "Hello Strands Agent!")
            if response:
                print(f"✅ 메시지 전송 성공")
                print(f"   응답: {response['response'][:100]}...")
            else:
                print("❌ 메시지 전송 실패")
        else:
            print("❌ 세션 생성 실패")
            
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "simple":
        # 간단한 테스트 실행
        asyncio.run(simple_strands_test())
    else:
        # 전체 데모 실행
        asyncio.run(demo_strands_conversation())
