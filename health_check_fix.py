@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트 (최신 Strands Agent SDK)"""
    try:
        # 세션 관리자 연결 확인
        session_mgr = get_session_manager()
        if hasattr(session_mgr, 'redis_client'):
            session_mgr.redis_client.ping()
            storage_type = "redis"
        else:
            storage_type = "memory"
        
        # Strands Agent 상태 확인 (최신 API)
        strands = get_strands_client()
        health_result = strands.health_check()
        
        response_data = {
            "status": "healthy",
            "storage": storage_type,
            "strands_agent": "healthy" if health_result.get("strands_available") else "unavailable",
            "strands_version": health_result.get("strands_sdk_version", "unknown"),
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "session_manager": "ok",
                "strands_client": "ok" if health_result.get("strands_available") else "error",
                "storage": "ok"
            },
            "strands_details": {
                "model_provider": health_result.get("model_provider"),
                "model_id": health_result.get("model_id"),
                "active_agents": health_result.get("active_agents", []),
                "tools_available": health_result.get("tools_available", False)
            }
        }
        
        return safe_json_response(response_data)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        error_response = {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
        return safe_json_response(error_response, 503)
