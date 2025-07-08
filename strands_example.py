#!/usr/bin/env python3
"""
AWS Strands Agent 독립 실행 예제

이 파일은 FastAPI 서버와 독립적으로 Strands Agent를 테스트할 수 있는 예제입니다.
"""

import asyncio
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

try:
    from strands import Agent
    from strands.models import BedrockModelProvider
    from strands.tools import Tool
    from strands_agents_tools.web_search import WebSearchTool
    from strands_agents_tools.calculator import CalculatorTool
    STRANDS_AVAILABLE = True
    print("✅ Strands Agent SDK가 사용 가능합니다.")
except ImportError as e:
    STRANDS_AVAILABLE = False
    print(f"❌ Strands Agent SDK를 가져올 수 없습니다: {e}")
    print("다음 명령어로 설치하세요:")
    print("pip install strands-agents strands-agents-tools")

def create_custom_tools():
    """커스텀 도구 생성"""
    tools = []
    
    # 현재 시간 도구
    def get_current_time() -> str:
        """현재 시간을 반환합니다."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    time_tool = Tool(
        name="get_current_time",
        description="현재 시간을 조회합니다",
        function=get_current_time
    )
    tools.append(time_tool)
    
    # 간단한 계산 도구
    def simple_calculator(expression: str) -> str:
        """간단한 수학 계산을 수행합니다."""
        try:
            # 안전한 계산을 위해 eval 대신 제한된 연산만 허용
            allowed_chars = set('0123456789+-*/.() ')
            if not all(c in allowed_chars for c in expression):
                return "오류: 허용되지 않는 문자가 포함되어 있습니다."
            
            result = eval(expression)
            return f"{expression} = {result}"
        except Exception as e:
            return f"계산 오류: {str(e)}"
    
    calc_tool = Tool(
        name="simple_calculator",
        description="간단한 수학 계산을 수행합니다 (예: 2+2, 10*5)",
        function=simple_calculator,
        parameters={
            "expression": {
                "type": "string",
                "description": "계산할 수학 표현식"
            }
        }
    )
    tools.append(calc_tool)
    
    return tools

async def test_basic_agent():
    """기본 에이전트 테스트"""
    if not STRANDS_AVAILABLE:
        print("Strands Agent SDK가 없어 기본 테스트를 건너뜁니다.")
        return
    
    print("\n=== 기본 Strands Agent 테스트 ===")
    
    try:
        # 기본 에이전트 생성 (도구 없음)
        agent = Agent()
        
        # 간단한 질문
        print("질문: AWS Strands Agent에 대해 간단히 설명해주세요.")
        response = await asyncio.to_thread(agent, "AWS Strands Agent에 대해 간단히 설명해주세요.")
        print(f"답변: {response}")
        
    except Exception as e:
        print(f"기본 에이전트 테스트 실패: {e}")

async def test_agent_with_tools():
    """도구를 사용하는 에이전트 테스트"""
    if not STRANDS_AVAILABLE:
        print("Strands Agent SDK가 없어 도구 테스트를 건너뜁니다.")
        return
    
    print("\n=== 도구를 사용하는 Strands Agent 테스트 ===")
    
    try:
        # 커스텀 도구 생성
        custom_tools = create_custom_tools()
        
        # 내장 도구 추가 시도
        tools = custom_tools.copy()
        
        try:
            tools.append(WebSearchTool())
            print("✅ 웹 검색 도구 추가됨")
        except Exception as e:
            print(f"⚠️ 웹 검색 도구 추가 실패: {e}")
        
        try:
            tools.append(CalculatorTool())
            print("✅ 계산기 도구 추가됨")
        except Exception as e:
            print(f"⚠️ 계산기 도구 추가 실패: {e}")
        
        # 시스템 프롬프트 설정
        system_prompt = """
당신은 도움이 되는 AI 어시스턴트입니다. 
사용자의 질문에 답변할 때 사용 가능한 도구들을 적극적으로 활용하세요.
특히 시간 관련 질문이나 계산이 필요한 경우 해당 도구를 사용하세요.
한국어로 답변하며, 친근하고 전문적인 톤을 유지하세요.
        """.strip()
        
        # 에이전트 생성
        agent = Agent(
            tools=tools,
            system_prompt=system_prompt,
            max_iterations=5
        )
        
        print(f"에이전트 생성 완료 (도구 {len(tools)}개)")
        
        # 테스트 질문들
        questions = [
            "현재 시간이 몇 시인가요?",
            "25 * 4 + 10을 계산해주세요.",
            "Strands Agent의 주요 특징을 설명해주세요."
        ]
        
        for i, question in enumerate(questions, 1):
            print(f"\n[질문 {i}] {question}")
            try:
                response = await asyncio.to_thread(agent, question)
                print(f"[답변 {i}] {response}")
            except Exception as e:
                print(f"[오류 {i}] {e}")
        
    except Exception as e:
        print(f"도구 에이전트 테스트 실패: {e}")

async def test_bedrock_agent():
    """Bedrock 모델을 사용하는 에이전트 테스트"""
    if not STRANDS_AVAILABLE:
        print("Strands Agent SDK가 없어 Bedrock 테스트를 건너뜁니다.")
        return
    
    print("\n=== Bedrock 모델 Strands Agent 테스트 ===")
    
    # AWS 자격 증명 확인
    aws_region = os.getenv("AWS_REGION", "us-west-2")
    model_id = os.getenv("STRANDS_MODEL_ID", "anthropic.claude-3-7-sonnet-20241022-v1:0")
    
    print(f"AWS 리전: {aws_region}")
    print(f"모델 ID: {model_id}")
    
    try:
        # Bedrock 모델 제공자 설정
        model_provider = BedrockModelProvider(
            model_id=model_id,
            region=aws_region
        )
        
        # 에이전트 생성
        agent = Agent(
            model_provider=model_provider,
            tools=create_custom_tools(),
            system_prompt="당신은 AWS Bedrock을 사용하는 Strands Agent입니다. 한국어로 답변하세요.",
            max_iterations=3
        )
        
        print("Bedrock 에이전트 생성 완료")
        
        # 테스트 질문
        question = "AWS Bedrock과 Strands Agent의 조합에 대해 설명해주세요."
        print(f"질문: {question}")
        
        response = await asyncio.to_thread(agent, question)
        print(f"답변: {response}")
        
    except Exception as e:
        print(f"Bedrock 에이전트 테스트 실패: {e}")
        print("AWS 자격 증명과 Bedrock 모델 액세스 권한을 확인하세요.")

def mock_agent_demo():
    """Mock 에이전트 데모 (Strands SDK가 없을 때)"""
    print("\n=== Mock Agent 데모 ===")
    print("Strands Agent SDK가 설치되지 않아 Mock 응답을 제공합니다.")
    
    questions = [
        "AWS Strands Agent에 대해 설명해주세요.",
        "현재 시간이 몇 시인가요?",
        "25 * 4 + 10을 계산해주세요."
    ]
    
    mock_responses = [
        "AWS Strands Agent는 모델 중심 접근 방식을 사용하는 AI 에이전트 SDK입니다. 간단한 코드로 강력한 에이전트를 구축할 수 있습니다.",
        "죄송하지만 실제 시간 도구가 없어 현재 시간을 알려드릴 수 없습니다. Strands Agent SDK를 설치하면 시간 도구를 사용할 수 있습니다.",
        "계산 도구가 없어 직접 계산할 수 없지만, 25 * 4 + 10 = 100 + 10 = 110입니다."
    ]
    
    for question, response in zip(questions, mock_responses):
        print(f"\n질문: {question}")
        print(f"Mock 답변: {response}")

async def main():
    """메인 함수"""
    print("AWS Strands Agent 독립 실행 예제")
    print("=" * 50)
    
    if STRANDS_AVAILABLE:
        await test_basic_agent()
        await test_agent_with_tools()
        
        # AWS 자격 증명이 있는 경우에만 Bedrock 테스트
        if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
            await test_bedrock_agent()
        else:
            print("\n⚠️ AWS 자격 증명이 설정되지 않아 Bedrock 테스트를 건너뜁니다.")
            print("AWS 자격 증명을 설정하려면:")
            print("1. .env 파일에 AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY 설정")
            print("2. 또는 'aws configure' 명령어 사용")
            print("3. 또는 IAM 역할 사용 (EC2, ECS, Lambda 등)")
    else:
        mock_agent_demo()
    
    print("\n" + "=" * 50)
    print("예제 실행 완료")

if __name__ == "__main__":
    asyncio.run(main())
