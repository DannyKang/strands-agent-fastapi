#!/bin/bash

# LTM Worker 백그라운드 실행 스크립트

cd /home/ec2-user/strands-agent-fastapi

# 기존 프로세스 종료
pkill -f ltm_worker.py

# 가상환경 활성화 및 백그라운드 실행
source venv/bin/activate
nohup python ltm_worker.py > ltm_worker.log 2>&1 &

echo "LTM Worker started in background"
echo "PID: $!"
echo "Log file: ltm_worker.log"
echo ""
echo "To stop: pkill -f ltm_worker.py"
echo "To check status: ps aux | grep ltm_worker"
echo "To view logs: tail -f ltm_worker.log"
