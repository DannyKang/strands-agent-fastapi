import asyncio
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from strands import Agent
    from strands.models import BedrockModelProvider
    from strands.tools import Tool
    from strands_agents_tools.web_search import WebSearchTool
    from strands_agents_tools.calculator import CalculatorTool
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False
    # Mock Tool class for when strands is not available
    class Tool:
        def __init__(self, name, description, function, parameters=None):
            self.name = name
            self.description = description
            self.function = function
            self.parameters = parameters or {}

logger = logging.getLogger(__name__)

class StrandsAgentClient:
    """AWS Strands Agent SDK를 사용하는 클라이언트"""
    
    def __init__(self, model_provider: str = "bedrock", model_id: str = None, region: str = "us-west-2"):
        """
        Strands Agent 클라이언트 초기화
        
        Args:
            model_provider: 모델 제공자 (bedrock, anthropic, openai 등)
            model_id: 모델 ID
            region: AWS 리전
        """
        self.model_provider = model_provider
        self.model_id = model_id or "anthropic.claude-3-7-sonnet-20241022-v1:0"
        self.region = region
        self.agents = {}  # 에이전트 인스턴스 캐시
        
        if not STRANDS_AVAILABLE:
            logger.warning("Strands Agent SDK not available, using mock client")
            return
            
        # 기본 도구들 설정
        self.default_tools = self._setup_default_tools()
        
    def _setup_default_tools(self) -> List[Tool]:
        """기본 도구들 설정"""
        tools = []
        
        try:
            # 웹 검색 도구
            tools.append(WebSearchTool())
            logger.info("Added WebSearchTool")
        except Exception as e:
            logger.warning(f"Failed to add WebSearchTool: {e}")
            
        try:
            # 계산기 도구
            tools.append(CalculatorTool())
            logger.info("Added CalculatorTool")
        except Exception as e:
            logger.warning(f"Failed to add CalculatorTool: {e}")
            
        # 커스텀 도구 추가
        tools.extend(self._create_custom_tools())
        
        return tools
    
    def _create_custom_tools(self) -> List[Tool]:
        """커스텀 도구들 생성"""
        tools = []
        
        # 시간 도구
        def get_current_time() -> str:
            """현재 시간을 반환합니다."""
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        time_tool = Tool(
            name="get_current_time",
            description="현재 시간을 조회합니다",
            function=get_current_time
        )
        tools.append(time_tool)
        
        # 세션 정보 도구
        def get_session_info(session_id: str) -> str:
            """세션 정보를 반환합니다."""
            return f"세션 ID: {session_id}, 상태: 활성"
        
        session_tool = Tool(
            name="get_session_info",
            description="세션 정보를 조회합니다",
            function=get_session_info,
            parameters={
                "session_id": {
                    "type": "string",
                    "description": "세션 ID"
                }
            }
        )
        tools.append(session_tool)
        
        return tools
    
    def _create_agent(self, agent_id: str, system_prompt: str = None) -> Agent:
        """에이전트 인스턴스 생성"""
        if not STRANDS_AVAILABLE:
            raise RuntimeError("Strands Agent SDK not available")
            
        # 시스템 프롬프트 설정
        if not system_prompt:
            system_prompt = self._get_default_system_prompt(agent_id)
        
        try:
            # Bedrock 모델 제공자 설정
            if self.model_provider == "bedrock":
                model_provider = BedrockModelProvider(
                    model_id=self.model_id,
                    region=self.region
                )
            else:
                # 다른 모델 제공자 지원 (추후 확장)
                raise ValueError(f"Unsupported model provider: {self.model_provider}")
            
            # 에이전트 생성
            agent = Agent(
                model_provider=model_provider,
                tools=self.default_tools,
                system_prompt=system_prompt,
                max_iterations=10,
                enable_tracing=True
            )
            
            logger.info(f"Created Strands agent {agent_id} with {len(self.default_tools)} tools")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create agent {agent_id}: {e}")
            raise
    
    def _get_default_system_prompt(self, agent_id: str) -> str:
        """에이전트별 기본 시스템 프롬프트"""
        prompts = {
            "assistant-001": """
당신은 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 정확하고 유용한 답변을 제공하세요.
사용 가능한 도구들을 적극적으로 활용하여 최신 정보를 제공하고 계산을 수행하세요.
한국어로 답변하며, 친근하고 전문적인 톤을 유지하세요.
            """.strip(),
            
            "support-001": """
당신은 고객 지원 전문 AI 어시스턴트입니다. 고객의 문제를 해결하고 도움을 제공하는 것이 주요 역할입니다.
문제 해결을 위해 단계별로 접근하고, 필요한 경우 도구를 사용하여 정보를 조회하세요.
정중하고 이해하기 쉬운 방식으로 답변하세요.
            """.strip(),
            
            "analyst-001": """
당신은 데이터 분석 전문 AI 어시스턴트입니다. 데이터를 분석하고 인사이트를 제공하는 것이 주요 역할입니다.
계산기 도구를 사용하여 수치 계산을 수행하고, 웹 검색을 통해 최신 데이터를 조회하세요.
분석 결과를 명확하고 구조적으로 제시하세요.
            """.strip()
        }
        
        return prompts.get(agent_id, prompts["assistant-001"])
    
    async def send_message(self, agent_id: str, message: str, session_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        에이전트에게 메시지 전송
        
        Args:
            agent_id: 에이전트 ID
            message: 사용자 메시지
            session_context: 세션 컨텍스트
            
        Returns:
            에이전트 응답
        """
        if not STRANDS_AVAILABLE:
            # Strands SDK가 없으면 직접 Bedrock 호출
            return await self._direct_bedrock_call(agent_id, message, session_context)
        
        try:
            # 에이전트 인스턴스 가져오기 또는 생성
            if agent_id not in self.agents:
                self.agents[agent_id] = self._create_agent(agent_id)
            
            agent = self.agents[agent_id]
            
            # 컨텍스트가 있으면 메시지에 포함
            if session_context:
                context_info = f"\n\n[세션 컨텍스트: {session_context.get('session_id', 'unknown')}]"
                message_with_context = message + context_info
            else:
                message_with_context = message
            
            # 에이전트 실행 (비동기)
            response = await asyncio.to_thread(agent, message_with_context)
            
            return {
                "success": True,
                "response": str(response),
                "agent_id": agent_id,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {
                    "model_provider": self.model_provider,
                    "model_id": self.model_id,
                    "tools_used": len(self.default_tools)
                }
            }
            
        except Exception as e:
            logger.error(f"Error sending message to agent {agent_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": f"죄송합니다. 에이전트 처리 중 오류가 발생했습니다: {str(e)}"
            }
    
    async def _direct_bedrock_call(self, agent_id: str, message: str, session_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """직접 Bedrock API 호출 (Strands SDK가 없을 때)"""
        try:
            import boto3
            import json
            
            # Bedrock Runtime 클라이언트 생성
            bedrock_runtime = boto3.client(
                'bedrock-runtime',
                region_name=self.region
            )
            
            # 에이전트별 시스템 프롬프트
            system_prompt = self._get_default_system_prompt(agent_id)
            
            # 대화 컨텍스트 추가
            context_message = ""
            if session_context and session_context.get('conversation_history'):
                context_message = "\n\n이전 대화:\n"
                for conv in session_context['conversation_history'][-3:]:  # 최근 3개만
                    context_message += f"사용자: {conv.get('message', '')}\n"
                    context_message += f"AI: {conv.get('response', '')}\n"
            
            # Claude 3.7 Sonnet 모델에 맞는 요청 바디 구성
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "temperature": 0.7,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": context_message + "\n\n" + message
                    }
                ]
            }
            
            # Bedrock API 호출
            response = bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            # 응답 파싱
            response_body = json.loads(response['body'].read())
            
            if 'content' in response_body and len(response_body['content']) > 0:
                ai_response = response_body['content'][0]['text']
            else:
                ai_response = "죄송합니다. 응답을 생성할 수 없습니다."
            
            return {
                "success": True,
                "response": ai_response,
                "agent_id": agent_id,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {
                    "mode": "bedrock_direct",
                    "model_provider": self.model_provider,
                    "model_id": self.model_id,
                    "strands_available": False
                }
            }
            
        except Exception as e:
            logger.error(f"Bedrock API 호출 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": f"죄송합니다. Bedrock API 호출 중 오류가 발생했습니다: {str(e)}"
            }
    
    async def _mock_send_message(self, agent_id: str, message: str, session_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Mock 메시지 전송 (Strands SDK가 없을 때)"""
        await asyncio.sleep(0.5)  # 실제 처리 시뮬레이션
        
        mock_responses = {
            "assistant-001": f"안녕하세요! 일반 어시스턴트입니다. '{message}'에 대한 답변을 드리겠습니다. 이것은 데모용 응답입니다.",
            "support-001": f"고객 지원팀입니다. '{message}' 문의사항을 확인했습니다. 도움을 드리겠습니다.",
            "analyst-001": f"데이터 분석가입니다. '{message}'에 대한 분석을 수행하겠습니다."
        }
        
        response_text = mock_responses.get(agent_id, f"에이전트 {agent_id}에서 '{message}'에 대한 응답입니다.")
        
        return {
            "success": True,
            "response": response_text,
            "agent_id": agent_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "mode": "mock",
                "strands_available": False
            }
        }
    
    async def get_agent_info(self, agent_id: str) -> Dict[str, Any]:
        """에이전트 정보 조회"""
        agent_info = {
            "assistant-001": {
                "id": "assistant-001",
                "name": "General Assistant",
                "description": "일반적인 질문에 답변하는 Strands 어시스턴트",
                "capabilities": ["general_qa", "web_search", "calculation", "conversation"],
                "model_provider": self.model_provider,
                "model_id": self.model_id
            },
            "support-001": {
                "id": "support-001",
                "name": "Customer Support Agent",
                "description": "고객 지원 전문 Strands 어시스턴트",
                "capabilities": ["customer_support", "troubleshooting", "web_search"],
                "model_provider": self.model_provider,
                "model_id": self.model_id
            },
            "analyst-001": {
                "id": "analyst-001",
                "name": "Data Analyst Agent",
                "description": "데이터 분석 전문 Strands 어시스턴트",
                "capabilities": ["data_analysis", "calculation", "web_search", "reporting"],
                "model_provider": self.model_provider,
                "model_id": self.model_id
            }
        }
        
        if agent_id in agent_info:
            return {
                "success": True,
                "agent_info": agent_info[agent_id]
            }
        else:
            return {
                "success": False,
                "error": "Agent not found"
            }
    
    async def list_agents(self) -> Dict[str, Any]:
        """사용 가능한 에이전트 목록 조회"""
        agents = []
        
        for agent_id in ["assistant-001", "support-001", "analyst-001"]:
            result = await self.get_agent_info(agent_id)
            if result.get("success"):
                agents.append(result["agent_info"])
        
        return {
            "success": True,
            "agents": agents,
            "total": len(agents),
            "strands_available": STRANDS_AVAILABLE
        }
    
    async def get_agent_capabilities(self) -> Dict[str, Any]:
        """에이전트 기능 정보 조회"""
        return {
            "success": True,
            "capabilities": {
                "model_providers": ["bedrock", "anthropic", "openai"],
                "default_model": self.model_id,
                "tools": [
                    {"name": "web_search", "description": "웹 검색 기능"},
                    {"name": "calculator", "description": "수학 계산 기능"},
                    {"name": "get_current_time", "description": "현재 시간 조회"},
                    {"name": "get_session_info", "description": "세션 정보 조회"}
                ],
                "features": [
                    "Multi-turn conversation",
                    "Tool usage",
                    "Context awareness",
                    "Streaming support"
                ]
            },
            "strands_sdk_version": "0.1.0" if STRANDS_AVAILABLE else "not_available"
        }
