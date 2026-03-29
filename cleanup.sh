#!/bin/bash

# ============================================
# Automated Disaster Recovery - Cleanup Script
# ============================================

REGION="us-east-1"
INSTANCE_ID="i-0b40f96ac7bb883ce"
ACCOUNT_ID="716156542960"

echo "============================================"
echo " Disaster Recovery - Cleanup"
echo "============================================"
echo ""
echo "WARNING: This will delete all resources!"
read -p "Are you sure? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
  echo "Cancelled."
  exit 0
fi

# Delete CloudWatch alarms
echo "[1/5] Deleting CloudWatch alarms..."
aws cloudwatch delete-alarms \
  --alarm-names "EC2-Down-${INSTANCE_ID}" "EC2-HighCPU-${INSTANCE_ID}" \
  --region $REGION
echo "Alarms deleted!"

# Delete Lambda function
echo "[2/5] Deleting Lambda function..."
aws lambda delete-function \
  --function-name disaster-recovery \
  --region $REGION
echo "Lambda deleted!"

# Detach and delete IAM role
echo "[3/5] Cleaning up IAM role..."
aws iam detach-role-policy \
  --role-name disaster-recovery-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam detach-role-policy \
  --role-name disaster-recovery-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2FullAccess
aws iam detach-role-policy \
  --role-name disaster-recovery-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSNSFullAccess
aws iam delete-role \
  --role-name disaster-recovery-lambda-role
echo "IAM role deleted!"

# Delete SNS topic
echo "[4/5] Deleting SNS topic..."
aws sns delete-topic \
  --topic-arn "arn:aws:sns:${REGION}:${ACCOUNT_ID}:disaster-recovery-alerts" \
  --region $REGION
echo "SNS topic deleted!"

# Remove cron jobs
echo "[5/5] Removing cron jobs..."
crontab -l | grep -v snapshot.py | grep -v check_health.py | crontab -
echo "Cron jobs removed!"

echo ""
echo "============================================"
echo " Cleanup Complete! All resources deleted."
echo "============================================"
