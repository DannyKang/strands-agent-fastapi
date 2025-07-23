@app.get("/health")
async def health_check():
    """간단한 헬스 체크 엔드포인트"""
    try:
        # 세션 관리자 연결 확인
        session_mgr = get_session_manager()
        if hasattr(session_mgr, "redis_client"):
            session_mgr.redis_client.ping()
            storage_type = "redis"
        else:
            storage_type = "memory"
        
        # 현재 시간을 문자열로 변환
        current_time = datetime.utcnow().isoformat()
        
        return {
            "status": "healthy",
            "storage": storage_type,
            "strands_agent": "available" if STRANDS_CLIENT_AVAILABLE else "mock_mode",
            "timestamp": current_time,
            "ltm_enabled": "ltm_manager" in globals() and ltm_manager is not None
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        error_time = datetime.utcnow().isoformat()
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": error_time
            }
        )
