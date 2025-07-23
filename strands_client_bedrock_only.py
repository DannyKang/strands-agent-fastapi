    def _initialize_model(self):
        """모델 초기화 (1.0.1 방식 - BedrockModel만 지원)"""
        try:
            if self.model_provider == "bedrock":
                return BedrockModel(
                    model_id=self.model_id,
                    region=self.region,
                    **self.model_kwargs
                )
            else:
                logger.warning(f"Unsupported model provider: {self.model_provider}, falling back to bedrock")
                return BedrockModel(
                    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
                    region=self.region,
                    **self.model_kwargs
                )
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            raise
