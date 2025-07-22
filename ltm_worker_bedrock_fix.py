# ltm_worker.py의 extract_user_preferences 메서드에서 Bedrock 모델 ID 부분 수정

    def extract_user_preferences(self, conversation_history: List[Dict], user_id: str, agent_id: str) -> Dict[str, Any]:
        """AI를 사용하여 사용자 선호도 추출"""
        
        # 대화 내용을 텍스트로 변환
        conversation_text = self.format_conversation_for_analysis(conversation_history)
        
        if not conversation_text.strip():
            logger.warning(f"Empty conversation text for user {user_id}")
            return {"error": "Empty conversation"}
        
        # Bedrock 모델 ID를 환경 변수에서 가져오기
        bedrock_model_id = os.getenv('LTM_BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')
        
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
            # Bedrock Claude 사용 - 환경 변수에서 모델 ID 가져오기
            logger.info(f"Using Bedrock model: {bedrock_model_id} for LTM analysis")
            
            response = self.bedrock.invoke_model(
                modelId=bedrock_model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "temperature": 0.3,
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
                logger.info(f"Successfully extracted preferences for user {user_id} using model {bedrock_model_id}")
                return preferences
            else:
                logger.error(f"Failed to extract JSON from AI response for user {user_id}")
                return {"error": "Failed to extract JSON from AI response", "raw_response": content}
                
        except Exception as e:
            logger.error(f"Error in AI analysis for user {user_id} with model {bedrock_model_id}: {e}")
            return {"error": str(e)}
