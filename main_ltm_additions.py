
# LTM Manager 초기화 코드 (lifespan 함수에 추가할 내용)
    
    # Long Term Memory 관리자 초기화
    global ltm_manager
    ltm_manager = LongTermMemoryManager(region=region)
    
    try:
        # LTM 테이블 생성 (존재하지 않는 경우)
        ltm_manager.create_ltm_table_if_not_exists()
        logger.info("LTM manager initialized successfully")
    except Exception as e:
        logger.warning(f"LTM manager initialization failed: {e}. LTM features will be disabled")
        ltm_manager = None

# LTM 의존성 함수
def get_ltm_manager():
    """LTM 관리자 의존성"""
    return ltm_manager

# LTM API 엔드포인트들

@app.get("/users/{user_id}/ltm")
async def get_user_ltm(user_id: str):
    """사용자 Long Term Memory 조회"""
    if not ltm_manager:
        raise HTTPException(status_code=503, detail="LTM service not available")
    
    try:
        ltm_data = ltm_manager.get_user_ltm(user_id)
        
        if not ltm_data:
            return {
                "user_id": user_id, 
                "ltm": None,
                "message": "No Long Term Memory found for this user"
            }
        
        return {
            "user_id": user_id,
            "ltm": ltm_data.get('preferences', {}),
            "updated_at": ltm_data.get('updated_at'),
            "session_count": ltm_data.get('session_count', 0),
            "last_session_id": ltm_data.get('last_session_id'),
            "version": ltm_data.get('version')
        }
        
    except Exception as e:
        logger.error(f"Error retrieving LTM for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve LTM")

@app.get("/users/{user_id}/preferences")
async def get_user_preferences(user_id: str):
    """사용자 선호도만 조회"""
    if not ltm_manager:
        raise HTTPException(status_code=503, detail="LTM service not available")
    
    try:
        preferences = ltm_manager.get_user_preferences(user_id)
        return {
            "user_id": user_id,
            "preferences": preferences,
            "communication_style": ltm_manager.get_communication_style(user_id),
            "interests": ltm_manager.get_user_interests(user_id),
            "preferred_agent": ltm_manager.get_preferred_agent_type(user_id)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving preferences for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve preferences")

@app.put("/users/{user_id}/ltm")
async def update_user_ltm(user_id: str, preferences: dict):
    """사용자 LTM 수동 업데이트 (관리자용)"""
    if not ltm_manager:
        raise HTTPException(status_code=503, detail="LTM service not available")
    
    try:
        success = ltm_manager.update_user_ltm(user_id, preferences)
        
        if success:
            return {
                "message": "LTM updated successfully",
                "user_id": user_id,
                "updated_at": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update LTM")
            
    except Exception as e:
        logger.error(f"Error updating LTM for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update LTM")

@app.delete("/users/{user_id}/ltm")
async def delete_user_ltm(user_id: str):
    """사용자 LTM 삭제"""
    if not ltm_manager:
        raise HTTPException(status_code=503, detail="LTM service not available")
    
    try:
        success = ltm_manager.delete_user_ltm(user_id)
        
        if success:
            return {
                "message": "LTM deleted successfully",
                "user_id": user_id,
                "deleted_at": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete LTM")
            
    except Exception as e:
        logger.error(f"Error deleting LTM for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete LTM")

@app.get("/admin/ltm/stats")
async def get_ltm_stats():
    """LTM 통계 조회"""
    if not ltm_manager:
        raise HTTPException(status_code=503, detail="LTM service not available")
    
    try:
        stats = ltm_manager.get_ltm_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving LTM stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve LTM stats")

# 세션 종료 시 LTM 처리 큐에 추가하는 수정된 delete_session 엔드포인트
@app.delete("/sessions/{session_id}")
async def end_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """세션 종료 및 LTM 처리 큐에 추가"""
    
    # 세션 정보 조회
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 세션 종료 처리
    session.status = SessionStatus.EXPIRED
    await session_manager.update_session(session)
    
    # LTM 처리를 위한 메시지를 SQS에 전송 (LTM 매니저가 있는 경우)
    if ltm_manager:
        try:
            success = ltm_manager.queue_ltm_processing(
                session_id=session_id,
                user_id=session.user_id,
                agent_id=session.agent_id,
                message_count=len(session.conversation_history),
                metadata=session.metadata
            )
            
            if success:
                logger.info(f"LTM processing queued for session {session_id}")
            else:
                logger.warning(f"Failed to queue LTM processing for session {session_id}")
                
        except Exception as e:
            logger.error(f"Error queuing LTM processing for session {session_id}: {e}")
    
    return {
        "message": "Session ended", 
        "session_id": session_id,
        "ltm_queued": ltm_manager is not None
    }

