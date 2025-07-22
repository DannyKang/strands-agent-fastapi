#!/bin/bash

# Long Term Memory 인프라 배포 스크립트

set -e

# 변수 설정
ENVIRONMENT=dev
PROJECT_NAME=strands-agent
AWS_REGION=ap-northeast-2

echo "Deploying LTM infrastructure for environment: "

# 1. DynamoDB 테이블 배포
echo "Deploying DynamoDB table..."
aws cloudformation deploy \
    --template-file cloudformation/ltm-dynamodb-table.yaml \
    --stack-name "-ltm-dynamodb-" \
    --parameter-overrides \
        Environment= \
        ProjectName= \
    --region  \
    --tags \
        Environment= \
        Project= \
        Component=LTM-Infrastructure

# 2. SQS 큐 배포
echo "Deploying SQS queues..."
aws cloudformation deploy \
    --template-file cloudformation/ltm-sqs-queue.yaml \
    --stack-name "-ltm-sqs-" \
    --parameter-overrides \
        Environment= \
        ProjectName= \
    --capabilities CAPABILITY_NAMED_IAM \
    --region  \
    --tags \
        Environment= \
        Project= \
        Component=LTM-Infrastructure

# 3. 출력값 가져오기
echo "Getting stack outputs..."
QUEUE_URL=

LTM_TABLE_NAME=

WORKER_ROLE_ARN=

echo ""
echo "=== Deployment Complete ==="
echo "Queue URL: "
echo "LTM Table Name: "
echo "Worker Role ARN: "
echo ""
echo "Update your .env file with:"
echo "LTM_QUEUE_URL="
echo "LTM_TABLE_NAME="
echo ""
echo "For Kubernetes deployment, update k8s/ltm-worker-deployment.yaml with:"
echo "- Queue URL: "
echo "- LTM Table Name: "
echo "- Worker Role ARN: "
