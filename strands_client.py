"""
AWS Strands Agent SDK 클라이언트 (Version 1.0.1)

이 모듈은 AWS Strands Agent SDK 1.0.1의 최신 기능을 활용하여
프로덕션급 AI 에이전트 시스템을 구현합니다.

주요 변경사항 (1.0.1):
- 새로운 Agent 초기화 방식
- 향상된 도구 통합 시스템
- 개선된 모델 제공자 지원
- 더 나은 에러 핸들링
- 스트리밍 응답 개선
- MCP (Model Context Protocol) 지원 강화

주요 기능:
- 최신 Strands Agent SDK 1.0.1 API 사용
- 다중 모델 제공자 지원 (Bedrock, Anthropic, OpenAI)
- 고급 도구 통합 (WebSearch, Calculator, Custom Tools)
- 컨텍스트 인식 및 메모리 관리
- 스트리밍 및 비동기 처리
- 에러 핸들링 및 복구
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Strands Agent SDK 1.0.1 임포트
try:
    from strands import Agent
    from strands.models import BedrockModel, AnthropicModel, OpenAIModel
    from strands.tools import FunctionTool
    STRANDS_AVAILABLE = True
    logger.info("✅ Strands Agent SDK 1.0.1 loaded successfully")
except ImportError as e:
    STRANDS_AVAILABLE = False
    logger.warning(f"❌ Strands import failed: {e}")
    
    # Mock classes for when strands is not available
    class Agent:
        def __init__(self, *args, **kwargs):
            pass
        def __call__(self, message):
            return f"Mock response to: {message}"
    
    class BedrockModel:
        def __init__(self, *args, **kwargs):
            pass
    
    class AnthropicModel:
        def __init__(self, *args, **kwargs):
            pass
    
    class OpenAIModel:
        def __init__(self, *args, **kwargs):
            pass
    
    class FunctionTool:
        def __init__(self, name, description, function, parameters=None):
            self.name = name
            self.description = description
            self.function = function
            self.parameters = parameters or {}

# Strands Tools 1.0.1 임포트
try:
    from strands_tools.calculator import calculator
    from strands_tools.web_search import web_search
    from strands_tools.time import current_time
    TOOLS_AVAILABLE = True
    logger.info("✅ Strands Tools 1.0.1 loaded successfully")
except ImportError as e:
    TOOLS_AVAILABLE = False
    logger.warning(f"⚠️ strands_tools not available: {e}")
    calculator = None
    web_search = None
    current_time = None


class StrandsAgentClient:
    """
    최신 AWS Strands Agent SDK 1.0.1을 사용하는 프로덕션급 클라이언트
    
    Features (1.0.1):
    - Enhanced model-driven approach with improved reasoning
    - Multi-provider support (Bedrock, Anthropic, OpenAI)
    - Advanced tool integration with MCP support
    - Context-aware conversations with better memory
    - Streaming and async processing improvements
    - Production-ready error handling and recovery
    - Better observability and tracing
    """
    
    def __init__(self, 
                 model_provider: str = "bedrock", 
                 model_id: str = None, 
                 region: str = "ap-northeast-2",
                 **model_kwargs):
        """
        Strands Agent 클라이언트 초기화 (1.0.1)
        
        Args:
            model_provider: 모델 제공자 (bedrock, anthropic, openai)
            model_id: 모델 ID
            region: AWS 리전
            **model_kwargs: 추가 모델 설정
        """
        self.model_provider = model_provider
        self.model_id = model_id or self._get_default_model_id(model_provider)
        self.region = region
        self.model_kwargs = model_kwargs
        
        # 에이전트 인스턴스 저장소
        self.agents = {}
        
        if not STRANDS_AVAILABLE:
            logger.warning("Strands SDK not available, using mock implementation")
            return
        
        # 모델 초기화
        self.model = self._initialize_model()
        logger.info(f"Initialized Strands Agent 1.0.1 with {model_provider} provider")
    
    def _get_default_model_id(self, provider: str) -> str:
        """기본 모델 ID 반환"""
        defaults = {
            "bedrock": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "anthropic": "claude-3-5-sonnet-20241022",
            "openai": "gpt-4o"
        }
        return defaults.get(provider, defaults["bedrock"])
    
    def _initialize_model(self):
        """모델 초기화 (1.0.1 방식)"""
        try:
            if self.model_provider == "bedrock":
                return BedrockModel(
                    model_id=self.model_id,
                    region=self.region,
                    **self.model_kwargs
                )
            elif self.model_provider == "anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY environment variable required")
                return AnthropicModel(
                    model_id=self.model_id,
                    api_key=api_key,
                    **self.model_kwargs
                )
            elif self.model_provider == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY environment variable required")
                return OpenAIModel(
                    model_id=self.model_id,
                    api_key=api_key,
                    **self.model_kwargs
                )
            else:
                raise ValueError(f"Unsupported model provider: {self.model_provider}")
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            raise
    
    def _get_system_prompt(self, agent_id: str) -> str:
        """에이전트별 시스템 프롬프트 반환"""
        prompts = {
            "assistant-001": """
            당신은 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 정확하고 유용한 답변을 제공하세요.
            
            능력:
            - 일반적인 질문 답변
            - 웹 검색을 통한 최신 정보 제공
            - 수학적 계산 수행
            - 현재 시간 정보 제공
            - 세션 정보 관리
            
            항상 친절하고 전문적인 톤으로 응답하세요.
            """,
            
            "support-001": """
            당신은 고객 지원 전문가입니다. 고객의 문제를 해결하고 최상의 서비스를 제공하세요.
            
            역할:
            - 고객 문의사항 해결
            - 단계별 문제 해결 가이드 제공
            - 제품/서비스 정보 안내
            - 기술적 문제 해결 지원
            
            항상 고객 중심적이고 해결 지향적으로 접근하세요.
            """,
            
            "analyst-001": """
            당신은 데이터 분석 전문가입니다. 데이터를 분석하고 인사이트를 제공하세요.
            
            전문 분야:
            - 데이터 분석 및 해석
            - 통계적 계산 및 분석
            - 트렌드 분석
            - 비즈니스 인텔리전스
            - 수치 데이터 처리
            
            분석적이고 논리적인 접근 방식을 사용하세요.
            """
        }
        
        return prompts.get(agent_id, prompts["assistant-001"])
    
    def _create_tools(self, agent_id: str) -> List[FunctionTool]:
        """에이전트별 도구 생성 (1.0.1 방식)"""
        tools = []
        
        # 기본 도구들
        if TOOLS_AVAILABLE:
            # 웹 검색 도구
            if web_search:
                tools.append(FunctionTool(
                    name="web_search",
                    description="Search the web for current information",
                    function=web_search
                ))
            
            # 계산기 도구
            if calculator:
                tools.append(FunctionTool(
                    name="calculator",
                    description="Perform mathematical calculations",
                    function=calculator
                ))
            
            # 시간 도구
            if current_time:
                tools.append(FunctionTool(
                    name="current_time",
                    description="Get current time and date",
                    function=current_time
                ))
        
        # 커스텀 도구들
        tools.extend([
            FunctionTool(
                name="get_session_info",
                description="Get information about the current session",
                function=self._get_session_info
            ),
            FunctionTool(
                name="format_response",
                description="Format response for better readability",
                function=self._format_response
            )
        ])
        
        # 에이전트별 특화 도구
        if agent_id == "analyst-001":
            tools.append(FunctionTool(
                name="analyze_data",
                description="Analyze numerical data and provide insights",
                function=self._analyze_data
            ))
        
        return tools
    
    def _get_session_info(self, session_id: str = None) -> str:
        """세션 정보 반환"""
        return f"Session info for {session_id or 'current session'}: Active session with Strands Agent 1.0.1"
    
    def _format_response(self, text: str, format_type: str = "markdown") -> str:
        """응답 포맷팅"""
        if format_type == "markdown":
            return f"**Formatted Response:**\n\n{text}"
        return text
    
    def _analyze_data(self, data: str) -> str:
        """데이터 분석 (간단한 예시)"""
        try:
            # 간단한 숫자 분석
            numbers = [float(x) for x in data.split() if x.replace('.', '').replace('-', '').isdigit()]
            if numbers:
                avg = sum(numbers) / len(numbers)
                return f"Data analysis: {len(numbers)} numbers found. Average: {avg:.2f}, Min: {min(numbers)}, Max: {max(numbers)}"
            return "No numerical data found for analysis"
        except Exception as e:
            return f"Analysis error: {str(e)}"
    
    def get_or_create_agent(self, agent_id: str) -> Agent:
        """에이전트 인스턴스 가져오기 또는 생성 (1.0.1 방식)"""
        if not STRANDS_AVAILABLE:
            return Agent()
        
        if agent_id not in self.agents:
            try:
                # Strands Agent 1.0.1 방식으로 에이전트 생성
                system_prompt = self._get_system_prompt(agent_id)
                tools = self._create_tools(agent_id)
                
                self.agents[agent_id] = Agent(
                    model=self.model,
                    system_prompt=system_prompt,
                    tools=tools,
                    # 1.0.1 새로운 설정들
                    max_iterations=int(os.getenv("STRANDS_MAX_ITERATIONS", "10")),
                    enable_tracing=os.getenv("STRANDS_ENABLE_TRACING", "true").lower() == "true",
                    memory_enabled=os.getenv("STRANDS_MEMORY_ENABLED", "true").lower() == "true"
                )
                
                logger.info(f"Created new agent instance: {agent_id} with Strands 1.0.1")
                
            except Exception as e:
                logger.error(f"Failed to create agent {agent_id}: {e}")
                raise
        
        return self.agents[agent_id]
    
    async def send_message(self, 
                          agent_id: str, 
                          message: str, 
                          session_id: str = None,
                          context: Optional[Dict[str, Any]] = None) -> str:
        """
        에이전트에게 메시지 전송 (1.0.1 방식)
        
        Args:
            agent_id: 에이전트 ID
            message: 사용자 메시지
            session_id: 세션 ID
            context: 추가 컨텍스트
            
        Returns:
            에이전트 응답
        """
        try:
            agent = self.get_or_create_agent(agent_id)
            
            # 컨텍스트가 있으면 메시지에 포함
            if context:
                context_str = f"\n\nContext: {json.dumps(context, ensure_ascii=False)}"
                message = message + context_str
            
            # 세션 정보 추가
            if session_id:
                message = f"[Session: {session_id}] {message}"
            
            # Strands Agent 1.0.1 방식으로 메시지 처리
            if STRANDS_AVAILABLE:
                response = agent(message)
                
                # 응답이 문자열이 아닌 경우 처리
                if hasattr(response, 'content'):
                    return response.content
                elif hasattr(response, 'text'):
                    return response.text
                else:
                    return str(response)
            else:
                return f"Mock response to: {message}"
                
        except Exception as e:
            logger.error(f"Error sending message to agent {agent_id}: {e}")
            return f"죄송합니다. 처리 중 오류가 발생했습니다: {str(e)}"
    
    async def stream_message(self, 
                           agent_id: str, 
                           message: str, 
                           session_id: str = None,
                           context: Optional[Dict[str, Any]] = None):
        """
        스트리밍 메시지 처리 (1.0.1 개선된 방식)
        
        Args:
            agent_id: 에이전트 ID
            message: 사용자 메시지
            session_id: 세션 ID
            context: 추가 컨텍스트
            
        Yields:
            스트리밍 응답 청크
        """
        try:
            agent = self.get_or_create_agent(agent_id)
            
            # 컨텍스트 처리
            if context:
                context_str = f"\n\nContext: {json.dumps(context, ensure_ascii=False)}"
                message = message + context_str
            
            if session_id:
                message = f"[Session: {session_id}] {message}"
            
            if STRANDS_AVAILABLE and hasattr(agent, 'stream'):
                # 1.0.1의 개선된 스트리밍 지원
                async for chunk in agent.stream(message):
                    yield chunk
            else:
                # Fallback: 일반 응답을 청크로 분할
                response = await self.send_message(agent_id, message, session_id, context)
                words = response.split()
                for i, word in enumerate(words):
                    yield word + (" " if i < len(words) - 1 else "")
                    await asyncio.sleep(0.05)  # 스트리밍 시뮬레이션
                    
        except Exception as e:
            logger.error(f"Error streaming message to agent {agent_id}: {e}")
            yield f"스트리밍 중 오류가 발생했습니다: {str(e)}"
    
    def get_agent_capabilities(self, agent_id: str) -> Dict[str, Any]:
        """에이전트 능력 정보 반환"""
        capabilities = {
            "assistant-001": {
                "name": "General Assistant",
                "description": "범용 AI 어시스턴트",
                "tools": ["web_search", "calculator", "current_time", "session_info"],
                "specialties": ["일반 질문 답변", "정보 검색", "계산"]
            },
            "support-001": {
                "name": "Customer Support",
                "description": "고객 지원 전문가",
                "tools": ["web_search", "current_time", "session_info"],
                "specialties": ["문제 해결", "고객 지원", "기술 지원"]
            },
            "analyst-001": {
                "name": "Data Analyst",
                "description": "데이터 분석 전문가",
                "tools": ["calculator", "analyze_data", "current_time", "session_info"],
                "specialties": ["데이터 분석", "통계 계산", "트렌드 분석"]
            }
        }
        
        return capabilities.get(agent_id, capabilities["assistant-001"])
    
    def health_check(self) -> Dict[str, Any]:
        """시스템 상태 확인"""
        status = {
            "strands_sdk_version": "1.0.1",
            "strands_available": STRANDS_AVAILABLE,
            "tools_available": TOOLS_AVAILABLE,
            "model_provider": self.model_provider,
            "model_id": self.model_id,
            "region": self.region,
            "active_agents": list(self.agents.keys()),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if STRANDS_AVAILABLE:
            try:
                # 간단한 테스트 에이전트로 상태 확인
                test_agent = self.get_or_create_agent("assistant-001")
                status["agent_test"] = "healthy"
            except Exception as e:
                status["agent_test"] = f"error: {str(e)}"
        
        return status
