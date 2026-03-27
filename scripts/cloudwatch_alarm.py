import boto3

REGION = "us-east-1"
INSTANCE_ID = "i-0b40f96ac7bb883ce"
SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:716156542960:disaster-recovery-alerts"

cloudwatch = boto3.client("cloudwatch", region_name=REGION)

def create_ec2_health_alarm():
    """
    Creates a CloudWatch alarm that fires when EC2 status check fails.
    StatusCheckFailed = 1 means the instance is unhealthy/down.
    StatusCheckFailed = 0 means everything is fine.
    """
    cloudwatch.put_metric_alarm(
        AlarmName=f"EC2-Down-{INSTANCE_ID}",
        AlarmDescription=f"Fires when EC2 instance {INSTANCE_ID} fails status check",
        ActionsEnabled=True,

        # What to do when alarm fires — send SNS alert
        AlarmActions=[SNS_TOPIC_ARN],
        # What to do when alarm recovers — send SNS alert
        OKActions=[SNS_TOPIC_ARN],

        # The metric we're watching
        Namespace="AWS/EC2",
        MetricName="StatusCheckFailed",
        Dimensions=[
            {
                "Name": "InstanceId",
                "Value": INSTANCE_ID
            }
        ],

        # Trigger alarm if status check fails for 2 minutes straight
        Period=60,           # check every 60 seconds
        EvaluationPeriods=2, # must fail 2 times in a row to trigger
        Threshold=1,         # StatusCheckFailed >= 1 means instance is down
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        Statistic="Maximum",
        TreatMissingData="breaching"  # if no data = assume instance is down
    )
    print(f"Alarm created: EC2-Down-{INSTANCE_ID}")
    print("Monitoring: StatusCheckFailed metric every 60 seconds")
    print("Alert will fire if instance fails 2 checks in a row")

def create_cpu_alarm():
    """
    Bonus alarm — fires if CPU stays above 90% for 5 minutes.
    Useful to detect runaway processes before they crash the server.
    """
    cloudwatch.put_metric_alarm(
        AlarmName=f"EC2-HighCPU-{INSTANCE_ID}",
        AlarmDescription=f"CPU above 90% for 5 minutes on {INSTANCE_ID}",
        ActionsEnabled=True,
        AlarmActions=[SNS_TOPIC_ARN],
        OKActions=[SNS_TOPIC_ARN],
        Namespace="AWS/EC2",
        MetricName="CPUUtilization",
        Dimensions=[
            {
                "Name": "InstanceId",
                "Value": INSTANCE_ID
            }
        ],
        Period=300,          # check every 5 minutes
        EvaluationPeriods=1,
        Threshold=90,        # CPU > 90%
        ComparisonOperator="GreaterThanThreshold",
        Statistic="Average",
        TreatMissingData="notBreaching"
    )
    print(f"Alarm created: EC2-HighCPU-{INSTANCE_ID}")
    print("Monitoring: CPU utilization every 5 minutes")
    print("Alert will fire if CPU stays above 90% for 5 minutes")

def list_alarms():
    """Show all alarms and their current state"""
    response = cloudwatch.describe_alarms(
        AlarmNamePrefix=f"EC2-"
    )
    print("\nCurrent alarms:")
    print("-" * 50)
    for alarm in response["MetricAlarms"]:
        name = alarm["AlarmName"]
        state = alarm["StateValue"]  # OK, ALARM, or INSUFFICIENT_DATA
        reason = alarm["StateReason"]
        print(f"Name:   {name}")
        print(f"State:  {state}")
        print(f"Reason: {reason}")
        print("-" * 50)

def main():
    print("Setting up CloudWatch alarms...")
    print()

    create_ec2_health_alarm()
    print()

    create_cpu_alarm()
    print()

    list_alarms()
    print("\nDay 2 complete! Your EC2 is now being monitored.")

if __name__ == "__main__":
    main()
