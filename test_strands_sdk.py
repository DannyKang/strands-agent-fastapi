#!/usr/bin/env python3
"""
Strands Agent SDK 테스트 스크립트

이 스크립트는 최신 AWS Strands Agent SDK의 기능을 테스트합니다.
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

def test_imports():
    """Strands Agent SDK 임포트 테스트"""
    print("🧬 Testing Strands Agent SDK imports...")
    
    try:
        from strands import Agent
        from strands.models import BedrockModel
        from strands.tools import FunctionTool
        print("✅ Core Strands Agent SDK imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Core Strands Agent SDK import failed: {e}")
        return False

def test_tools_import():
    """Strands Agent Tools 임포트 테스트"""
    print("\n🛠️ Testing Strands Agent Tools imports...")
    
    try:
        from strands_agents_tools.web_search import WebSearchTool
        from strands_agents_tools.calculator import CalculatorTool
        print("✅ Strands Agent Tools imported successfully")
        return True
    except ImportError as e:
        print(f"⚠️ Strands Agent Tools import failed: {e}")
        print("   This is optional but recommended for full functionality")
        return False

def test_model_creation():
    """모델 생성 테스트"""
    print("\n🤖 Testing model creation...")
    
    try:
        from strands.models import BedrockModel
        
        model = BedrockModel(
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            region=os.getenv("AWS_REGION", "ap-northeast-2")
        )
        print("✅ BedrockModel created successfully")
        return model
    except Exception as e:
        print(f"❌ Model creation failed: {e}")
        return None

def test_custom_tools():
    """커스텀 도구 생성 테스트"""
    print("\n🔧 Testing custom tools creation...")
    
    try:
        from strands.tools import FunctionTool
        
        def get_current_time() -> str:
            """현재 시간을 반환합니다."""
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        time_tool = FunctionTool(
            name="get_current_time",
            description="현재 시간을 조회합니다",
            function=get_current_time
        )
        
        print("✅ Custom tools created successfully")
        return [time_tool]
    except Exception as e:
        print(f"❌ Custom tools creation failed: {e}")
        return []

async def test_agent_creation():
    """에이전트 생성 테스트"""
    print("\n🤖 Testing agent creation...")
    
    try:
        from strands import Agent
        from strands.models import BedrockModel
        from strands.tools import FunctionTool
        
        # 모델 생성
        model = BedrockModel(
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            region=os.getenv("AWS_REGION", "ap-northeast-2")
        )
        
        # 커스텀 도구 생성
        def get_current_time() -> str:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        time_tool = FunctionTool(
            name="get_current_time",
            description="현재 시간을 조회합니다",
            function=get_current_time
        )
        
        # 에이전트 생성
        agent = Agent(
            model=model,
            tools=[time_tool],
            system_prompt="당신은 도움이 되는 AI 어시스턴트입니다. 한국어로 답변하세요.",
            max_iterations=5,
            enable_tracing=True
        )
        
        print("✅ Agent created successfully")
        return agent
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        return None

async def test_agent_execution(agent):
    """에이전트 실행 테스트"""
    print("\n💬 Testing agent execution...")
    
    if not agent:
        print("❌ No agent available for testing")
        return False
    
    try:
        # 간단한 메시지 테스트
        response = await asyncio.to_thread(agent, "안녕하세요! 현재 시간을 알려주세요.")
        
        print("✅ Agent execution successful")
        print(f"📝 Response: {response}")
        return True
    except Exception as e:
        print(f"❌ Agent execution failed: {e}")
        return False

def test_environment():
    """환경 설정 테스트"""
    print("\n🌍 Testing environment configuration...")
    
    # AWS 자격 증명 확인
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION")
    
    if aws_key and aws_key != "your-aws-access-key-id":
        print("✅ AWS_ACCESS_KEY_ID configured")
    else:
        print("⚠️ AWS_ACCESS_KEY_ID not configured")
    
    if aws_secret and aws_secret != "your-aws-secret-access-key":
        print("✅ AWS_SECRET_ACCESS_KEY configured")
    else:
        print("⚠️ AWS_SECRET_ACCESS_KEY not configured")
    
    if aws_region:
        print(f"✅ AWS_REGION configured: {aws_region}")
    else:
        print("⚠️ AWS_REGION not configured")
    
    # Strands 설정 확인
    model_provider = os.getenv("STRANDS_MODEL_PROVIDER", "bedrock")
    model_id = os.getenv("STRANDS_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    
    print(f"🧬 Strands Model Provider: {model_provider}")
    print(f"🧬 Strands Model ID: {model_id}")

async def main():
    """메인 테스트 함수"""
    print("🧬 AWS Strands Agent SDK Test Suite")
    print("=" * 50)
    
    # 1. 임포트 테스트
    core_available = test_imports()
    tools_available = test_tools_import()
    
    # 2. 환경 설정 테스트
    test_environment()
    
    if not core_available:
        print("\n❌ Core Strands Agent SDK not available. Please install:")
        print("   pip install strands-agents strands-agents-tools")
        sys.exit(1)
    
    # 3. 모델 생성 테스트
    model = test_model_creation()
    
    # 4. 커스텀 도구 테스트
    tools = test_custom_tools()
    
    # 5. 에이전트 생성 테스트
    agent = await test_agent_creation()
    
    # 6. 에이전트 실행 테스트 (AWS 자격 증명이 있는 경우에만)
    aws_configured = (
        os.getenv("AWS_ACCESS_KEY_ID") and 
        os.getenv("AWS_ACCESS_KEY_ID") != "your-aws-access-key-id" and
        os.getenv("AWS_SECRET_ACCESS_KEY") and 
        os.getenv("AWS_SECRET_ACCESS_KEY") != "your-aws-secret-access-key"
    )
    
    if aws_configured:
        await test_agent_execution(agent)
    else:
        print("\n⚠️ AWS credentials not configured. Skipping agent execution test.")
        print("   Configure AWS credentials in .env file to test agent execution.")
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("🎯 Test Summary:")
    print(f"   Core SDK: {'✅ Available' if core_available else '❌ Not Available'}")
    print(f"   Tools: {'✅ Available' if tools_available else '⚠️ Limited'}")
    print(f"   AWS Config: {'✅ Configured' if aws_configured else '⚠️ Not Configured'}")
    print(f"   Model: {'✅ Created' if model else '❌ Failed'}")
    print(f"   Agent: {'✅ Created' if agent else '❌ Failed'}")
    
    if core_available and model and agent:
        print("\n🎉 Strands Agent SDK is ready to use!")
        if not aws_configured:
            print("   Configure AWS credentials for full functionality.")
    else:
        print("\n⚠️ Some components need attention. Check the logs above.")

if __name__ == "__main__":
    asyncio.run(main())
