#!/bin/bash

# ============================================
# Automated Disaster Recovery - Setup Script
# ============================================

set -e  # exit immediately if any command fails

# ---------- CONFIGURATION ----------
REGION="us-east-1"
INSTANCE_ID="i-0b40f96ac7bb883ce"
ACCOUNT_ID="716156542960"
EMAIL="pratik1971sinha@gmail.com"
LAMBDA_ROLE_NAME="disaster-recovery-lambda-role"
LAMBDA_FUNCTION_NAME="disaster-recovery"
ALARM_NAME="EC2-Down-${INSTANCE_ID}"
SNS_TOPIC_NAME="disaster-recovery-alerts"
# -----------------------------------

echo "============================================"
echo " Automated Disaster Recovery - Setup"
echo "============================================"
echo ""

# Step 1 — Create SNS Topic
echo "[1/6] Creating SNS topic..."
SNS_ARN=$(aws sns create-topic \
  --name $SNS_TOPIC_NAME \
  --region $REGION \
  --query "TopicArn" \
  --output text)
echo "SNS Topic: $SNS_ARN"

# Step 2 — Subscribe email
echo ""
echo "[2/6] Subscribing email to SNS topic..."
aws sns subscribe \
  --topic-arn $SNS_ARN \
  --protocol email \
  --notification-endpoint $EMAIL \
  --region $REGION > /dev/null
echo "Subscription sent to $EMAIL — check inbox and confirm!"

# Step 3 — Create IAM Role
echo ""
echo "[3/6] Creating IAM role for Lambda..."
cat > /tmp/lambda-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name $LAMBDA_ROLE_NAME \
  --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
  --region $REGION > /dev/null 2>&1 || echo "Role already exists, skipping..."

aws iam attach-role-policy \
  --role-name $LAMBDA_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam attach-role-policy \
  --role-name $LAMBDA_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2FullAccess
aws iam attach-role-policy \
  --role-name $LAMBDA_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonSNSFullAccess

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${LAMBDA_ROLE_NAME}"
echo "IAM Role: $ROLE_ARN"

# Step 4 — Deploy Lambda
echo ""
echo "[4/6] Deploying Lambda function..."
cd ~/disaster-recovery/scripts
zip -q lambda_deployment.zip lambda_function.py

aws lambda create-function \
  --function-name $LAMBDA_FUNCTION_NAME \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda_deployment.zip \
  --timeout 300 \
  --region $REGION > /dev/null 2>&1 || echo "Lambda already exists, updating code..."

aws lambda update-function-code \
  --function-name $LAMBDA_FUNCTION_NAME \
  --zip-file fileb://lambda_deployment.zip \
  --region $REGION > /dev/null

LAMBDA_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${LAMBDA_FUNCTION_NAME}"
echo "Lambda: $LAMBDA_ARN"

# Step 5 — Create CloudWatch Alarms
echo ""
echo "[5/6] Creating CloudWatch alarms..."
aws cloudwatch put-metric-alarm \
  --alarm-name $ALARM_NAME \
  --alarm-actions $SNS_ARN $LAMBDA_ARN \
  --ok-actions $SNS_ARN \
  --metric-name StatusCheckFailed \
  --namespace AWS/EC2 \
  --dimensions Name=InstanceId,Value=$INSTANCE_ID \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --statistic Maximum \
  --treat-missing-data breaching \
  --region $REGION

aws cloudwatch put-metric-alarm \
  --alarm-name "EC2-HighCPU-${INSTANCE_ID}" \
  --alarm-actions $SNS_ARN \
  --ok-actions $SNS_ARN \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --dimensions Name=InstanceId,Value=$INSTANCE_ID \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 90 \
  --comparison-operator GreaterThanThreshold \
  --statistic Average \
  --treat-missing-data notBreaching \
  --region $REGION

echo "CloudWatch alarms created!"

# Step 6 — Set up cron jobs
echo ""
echo "[6/6] Setting up cron jobs..."
(crontab -l 2>/dev/null | grep -v snapshot.py | grep -v check_health.py; \
  echo "0 0 * * * python3 /home/ubuntu/disaster-recovery/scripts/snapshot.py >> /home/ubuntu/disaster-recovery/backup.log 2>&1"; \
  echo "*/5 * * * * python3 /home/ubuntu/disaster-recovery/scripts/check_health.py >> /home/ubuntu/disaster-recovery/backup.log 2>&1") | crontab -
echo "Cron jobs configured!"

# Summary
echo ""
echo "============================================"
echo " Setup Complete!"
echo "============================================"
echo ""
echo "Resources created:"
echo "  SNS Topic:        $SNS_ARN"
echo "  IAM Role:         $ROLE_ARN"
echo "  Lambda Function:  $LAMBDA_ARN"
echo "  CloudWatch Alarm: $ALARM_NAME"
echo ""
echo "Cron jobs:"
echo "  Backup:       daily at midnight"
echo "  Health check: every 5 minutes"
echo ""
echo "IMPORTANT: Check $EMAIL and confirm SNS subscription!"
echo "============================================"
