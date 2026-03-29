

A fully automated disaster recovery system built on AWS that monitors EC2 instances, takes daily backups, and automatically recovers from failures with zero manual intervention.

## Live Demo Result

```json
{
  "status": "success",
  "original_instance": "i-0b40f96ac7bb883ce",
  "new_instance": "i-0c624c2b13d64f5d6",
  "snapshot_used": "snap-09af1209b7dd1a503",
  "ami_created": "ami-09ef00992c6cf64a7"
}
```
New EC2 instance recovered automatically from snapshot in under 3 seconds.

## Architecture

```
EC2 Instance goes down
    -> CloudWatch detects failure within 2 minutes
        -> Triggers Lambda function + SNS email alert
            -> Lambda finds latest EBS snapshot
                -> Creates AMI from snapshot
                    -> Launches new EC2 with same settings
                        -> Sends Recovery Complete email
```

## Features

- Automated Backups — EBS snapshots taken daily at midnight via cron
- Real-time Monitoring — CloudWatch alarms check EC2 health every 60 seconds
- Auto Recovery — Lambda automatically restores EC2 from latest snapshot
- Instant Alerts — SNS email notifications for every event
- Health Checks — second layer of monitoring every 5 minutes via cron
- One Command Setup — entire infrastructure deployed with single bash script
- Clean Teardown — cleanup script removes all AWS resources to avoid billing

## Tech Stack

| Service | Purpose |
|---------|---------|
| AWS EC2 | Application server being monitored and recovered |
| AWS EBS | Persistent storage with automated snapshot backups |
| AWS Lambda | Serverless auto-recovery function |
| AWS CloudWatch | Metrics monitoring and alarm triggers |
| AWS SNS | Email alert notifications |
| AWS IAM | Roles and permissions for Lambda |
| Python + boto3 | All automation scripts |
| Bash + Cron | Scheduling and one-command deployment |

## Project Structure

```
disaster-recovery/
├── scripts/
│   ├── snapshot.py          # Takes EBS backup daily at midnight
│   ├── cloudwatch_alarm.py  # Creates CloudWatch alarms
│   ├── check_health.py      # Health check every 5 minutes
│   ├── lambda_function.py   # Auto-recovery Lambda function
│   └── notify.py            # SNS notification helper
├── setup.sh                 # One-command full deployment
├── cleanup.sh               # Removes all AWS resources cleanly
└── README.md
```

## How It Works

### 1. Daily Automated Backups
A cron job runs snapshot.py every night at midnight. It finds all EBS volumes attached to the monitored EC2 instance, creates a tagged snapshot, and sends a confirmation email via SNS.

### 2. Real-time Health Monitoring
Two CloudWatch alarms run continuously:
- StatusCheckFailed — detects instance crash within 2 minutes
- CPUUtilization — alerts if CPU stays above 90% for 5 minutes

A cron job also runs check_health.py every 5 minutes as a second monitoring layer.

### 3. Automatic Recovery Flow
When StatusCheckFailed triggers the alarm:
1. CloudWatch invokes Lambda function automatically
2. Lambda checks actual instance state
3. Lambda finds the most recent completed EBS snapshot
4. Lambda registers a new AMI from that snapshot
5. Lambda launches new EC2 with identical settings
6. SNS sends Recovery Complete email with new instance details

### 4. One Command Deployment
setup.sh deploys the entire system from scratch:
- Creates SNS topic and subscribes email
- Creates IAM role with required permissions
- Packages and deploys Lambda function
- Creates both CloudWatch alarms
- Configures all cron jobs
- Prints summary of all created resources

## Quick Start

### Prerequisites
- AWS account with IAM user (never use root access keys)
- AWS CLI installed and configured
- Python 3.x with boto3

```bash
pip3 install boto3
aws configure
```

### Deploy entire system in one command

```bash
# Clone the repo
git clone https://github.com/pks2906/disaster-recovery.git
cd disaster-recovery

# Update configuration in setup.sh
# Change REGION, INSTANCE_ID, ACCOUNT_ID, EMAIL to your values

# Deploy everything
bash setup.sh
```

### Teardown to avoid AWS billing

```bash
bash cleanup.sh
```

## Cron Schedule

| Script | Schedule | Purpose |
|--------|----------|---------|
| snapshot.py | Every day at midnight | Take EBS backup |
| check_health.py | Every 5 minutes | Verify EC2 health |

## Key Concepts Learned

RTO (Recovery Time Objective) — time to recover after failure. This system achieves 5-10 minute RTO fully automated.

RPO (Recovery Point Objective) — maximum acceptable data loss. With daily snapshots, RPO is 24 hours.

Event-driven architecture — Lambda only runs when triggered by CloudWatch, zero idle cost.

Idempotent scripts — setup.sh can be run multiple times safely, existing resources are skipped.

IAM least privilege — dedicated IAM role for Lambda with only required permissions, never using root access keys.

## Cost Estimate

| Service | Free Tier | Estimated Cost |
|---------|-----------|----------------|
| EC2 t2.micro | 750 hrs/month free | $0 free tier |
| EBS Snapshots | 1GB free | ~$0.05/GB/month |
| Lambda | 1M requests free | $0 free tier |
| CloudWatch | 10 alarms free | $0 free tier |
| SNS | 1000 emails free | $0 free tier |

Total cost for this project: $0 on AWS free tier

## What I Learned

- Designing event-driven architecture on AWS
- Writing serverless functions with AWS Lambda
- Automating infrastructure with Python boto3
- CloudWatch metrics, alarms and triggers
- EBS snapshot lifecycle management
- IAM roles and least privilege security
- RTO and RPO concepts in disaster recovery
- Writing idempotent infrastructure automation scripts

## Author

Pratik Kumar Sinha
- GitHub: https://github.com/pks2906
- Project built as part of DevOps portfolio

## Related Projects

- poker-devops: https://github.com/pks2906/poker-devops — Full-stack CI/CD pipeline with Docker, Kubernetes and Jenkins
ENDOFFILE
```

