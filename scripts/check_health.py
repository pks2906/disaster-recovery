import boto3
import datetime

REGION = "us-east-1"
INSTANCE_ID = "i-0b40f96ac7bb883ce"
SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:716156542960:disaster-recovery-alerts"

ec2 = boto3.client("ec2", region_name=REGION)
sns = boto3.client("sns", region_name=REGION)
cloudwatch = boto3.client("cloudwatch", region_name=REGION)

def get_instance_state():
    """Check if EC2 instance is running or stopped"""
    response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
    state = response["Reservations"][0]["Instances"][0]["State"]["Name"]
    return state

def get_alarm_state():
    """Check CloudWatch alarm state"""
    response = cloudwatch.describe_alarms(
        AlarmNames=[f"EC2-Down-{INSTANCE_ID}"]
    )
    if response["MetricAlarms"]:
        return response["MetricAlarms"][0]["StateValue"]
    return "NO_ALARM_FOUND"

def send_alert(message, subject):
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=message,
        Subject=subject
    )

def main():
    print(f"Health check at {datetime.datetime.now()}")
    print("-" * 40)

    # Check instance state
    instance_state = get_instance_state()
    print(f"Instance state: {instance_state}")

    # Check alarm state
    alarm_state = get_alarm_state()
    print(f"Alarm state:    {alarm_state}")

    # Take action based on states
    if instance_state != "running":
        message = f"""
CRITICAL: Instance Down!

Instance ID: {INSTANCE_ID}
State: {instance_state}
Time: {datetime.datetime.now()}

Automatic recovery will begin shortly.
        """
        send_alert(message, "CRITICAL: EC2 Instance is Down!")
        print("ALERT SENT — instance is not running!")

    elif alarm_state == "ALARM":
        message = f"""
WARNING: CloudWatch Alarm Triggered!

Instance ID: {INSTANCE_ID}
Alarm State: {alarm_state}
Time: {datetime.datetime.now()}

Please investigate immediately.
        """
        send_alert(message, "WARNING: EC2 Health Check Failed!")
        print("ALERT SENT — alarm is triggered!")

    else:
        print("All systems healthy — no action needed")

if __name__ == "__main__":
    main()
