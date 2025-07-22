# ltm_worker.py의 __init__ 메서드에 추가할 설정들

    def __init__(self):
        self.sqs = boto3.client('sqs', region_name=os.getenv('AWS_REGION', 'ap-northeast-2'))
        self.dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'ap-northeast-2'))
        self.bedrock = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION', 'ap-northeast-2'))
        
        # Bedrock 설정
        self.bedrock_model_id = os.getenv('LTM_BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')
        self.bedrock_max_tokens = int(os.getenv('LTM_BEDROCK_MAX_TOKENS', '2000'))
        self.bedrock_temperature = float(os.getenv('LTM_BEDROCK_TEMPERATURE', '0.3'))
        
        # 테이블 참조
        self.chat_history_table = self.dynamodb.Table(
            os.getenv('DYNAMODB_HISTORY_TABLE', 'langchain_chat_history')
        )
        self.ltm_table = self.dynamodb.Table(
            os.getenv('LTM_TABLE_NAME', 'user_long_term_memory')
        )
        
        self.queue_url = os.getenv('LTM_QUEUE_URL')
        if not self.queue_url:
            raise ValueError(LTM_QUEUE_URL environment variable is required)
        
        # 처리 설정
        self.processing_timeout = int(os.getenv('LTM_PROCESSING_TIMEOUT', '300'))
        self.max_retries = int(os.getenv('LTM_MAX_RETRIES', '3'))
        
        self.running = True
        self.processed_count = 0
        self.error_count = 0
        
        logger.info(fLTM Worker initialized with Bedrock model: {self.bedrock_model_id})
        logger.info(fMax tokens: {self.bedrock_max_tokens}, Temperature: {self.bedrock_temperature})
        
        # Graceful shutdown 설정
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

# extract_user_preferences 메서드에서 사용할 수정된 Bedrock 호출 부분
            response = self.bedrock.invoke_model(
                modelId=self.bedrock_model_id,
                body=json.dumps({
                    anthropic_version: bedrock-2023-05-31,
                    max_tokens: self.bedrock_max_tokens,
                    temperature: self.bedrock_temperature,
                    messages: [
                        {
                            role: user,
                            content: analysis_prompt
                        }
                    ]
                })
            )
