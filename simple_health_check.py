@app.get("/health")
async def health_check():
    """간단한 헬스 체크 엔드포인트"""
    try:
        # 세션 관리자 연결 확인
        session_mgr = get_session_manager()
        if hasattr(session_mgr, 'redis_client'):
            session_mgr.redis_client.ping()
            storage_type = "redis"
        else:
            storage_type = "memory"
        
        return {
            "status": "healthy",
            "storage": storage_type,
            "strands_agent": "available" if STRANDS_CLIENT_AVAILABLE else "mock_mode",
            "timestamp": datetime.utcnow().isoformat(),
            "ltm_enabled": ltm_manager is not None
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
