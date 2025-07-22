#!/bin/bash

# Long Term Memory 인프라 배포 스크립트

set -e

# 변수 설정
ENVIRONMENT=${1:-dev}
PROJECT_NAME=${2:-strands-agent}
AWS_REGION=${3:-ap-northeast-2}

echo "Deploying LTM infrastructure for environment: $ENVIRONMENT"
echo "Project: $PROJECT_NAME"
echo "Region: $AWS_REGION"

# 1. DynamoDB 테이블 배포
echo "Deploying DynamoDB table..."
aws cloudformation deploy     --template-file cloudformation/ltm-dynamodb-table.yaml     --stack-name "$PROJECT_NAME-ltm-dynamodb-$ENVIRONMENT"     --parameter-overrides         Environment=$ENVIRONMENT         ProjectName=$PROJECT_NAME     --region $AWS_REGION     --tags         Environment=$ENVIRONMENT         Project=$PROJECT_NAME         Component=LTM-Infrastructure

# 2. SQS 큐 배포
echo "Deploying SQS queues..."
aws cloudformation deploy     --template-file cloudformation/ltm-sqs-queue.yaml     --stack-name "$PROJECT_NAME-ltm-sqs-$ENVIRONMENT"     --parameter-overrides         Environment=$ENVIRONMENT         ProjectName=$PROJECT_NAME     --capabilities CAPABILITY_NAMED_IAM     --region $AWS_REGION     --tags         Environment=$ENVIRONMENT         Project=$PROJECT_NAME         Component=LTM-Infrastructure

# 3. 출력값 가져오기
echo "Getting stack outputs..."
QUEUE_URL=$(aws cloudformation describe-stacks     --stack-name "$PROJECT_NAME-ltm-sqs-$ENVIRONMENT"     --region $AWS_REGION     --query 'Stacks[0].Outputs[?OutputKey==`LTMQueueUrl`].OutputValue'     --output text)

LTM_TABLE_NAME=$(aws cloudformation describe-stacks     --stack-name "$PROJECT_NAME-ltm-dynamodb-$ENVIRONMENT"     --region $AWS_REGION     --query 'Stacks[0].Outputs[?OutputKey==`LTMTableName`].OutputValue'     --output text)

WORKER_ROLE_ARN=$(aws cloudformation describe-stacks     --stack-name "$PROJECT_NAME-ltm-sqs-$ENVIRONMENT"     --region $AWS_REGION     --query 'Stacks[0].Outputs[?OutputKey==`LTMWorkerRoleArn`].OutputValue'     --output text)

echo ""
echo "=== Deployment Complete ==="
echo "Queue URL: $QUEUE_URL"
echo "LTM Table Name: $LTM_TABLE_NAME"
echo "Worker Role ARN: $WORKER_ROLE_ARN"
echo ""
echo "Update your .env file with:"
echo "LTM_QUEUE_URL=$QUEUE_URL"
echo "LTM_TABLE_NAME=$LTM_TABLE_NAME"
echo ""
echo "For Kubernetes deployment, update k8s/ltm-worker-deployment.yaml with:"
echo "- Queue URL: $QUEUE_URL"
echo "- LTM Table Name: $LTM_TABLE_NAME"
echo "- Worker Role ARN: $WORKER_ROLE_ARN"
