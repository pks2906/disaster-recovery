import boto3
import json
import datetime

REGION = "us-east-1"
INSTANCE_ID = "i-0b40f96ac7bb883ce"
SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:716156542960:disaster-recovery-alerts"

ec2 = boto3.client("ec2", region_name=REGION)
sns = boto3.client("sns", region_name=REGION)

def send_alert(subject, message):
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=subject,
        Message=message
    )

def get_latest_snapshot():
    """Find the most recent snapshot taken by our backup script"""
    response = ec2.describe_snapshots(
        Filters=[
            {"Name": "tag:AutoBackup", "Values": ["true"]},
            {"Name": "tag:InstanceId", "Values": [INSTANCE_ID]},
            {"Name": "status", "Values": ["completed"]}
        ],
        OwnerIds=["self"]
    )

    snapshots = response["Snapshots"]

    if not snapshots:
        return None

    # Sort by date, get the latest one
    latest = sorted(snapshots, key=lambda x: x["StartTime"], reverse=True)[0]
    return latest

def get_instance_details():
    """Get original instance details to recreate it with same settings"""
    response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
    instance = response["Reservations"][0]["Instances"][0]
    return {
        "instance_type": instance["InstanceType"],
        "subnet_id": instance["SubnetId"],
        "security_groups": [sg["GroupId"] for sg in instance["SecurityGroups"]],
        "key_name": instance.get("KeyName", "")
    }

def restore_from_snapshot(snapshot_id, instance_details):
    """Create a new EC2 instance from the latest snapshot"""

    # Step 1 — create an AMI from the snapshot
    ami_response = ec2.register_image(
        Name=f"recovery-ami-{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M')}",
        Description="Auto-recovery AMI created by disaster recovery system",
        Architecture="x86_64",
        RootDeviceName="/dev/xvda",
        BlockDeviceMappings=[
            {
                "DeviceName": "/dev/xvda",
                "Ebs": {
                    "SnapshotId": snapshot_id,
                    "VolumeType": "gp2",
                    "DeleteOnTermination": True
                }
            }
        ],
        VirtualizationType="hvm"
    )
    ami_id = ami_response["ImageId"]
    print(f"AMI created: {ami_id}")

    # Step 2 — wait for AMI to be available
    print("Waiting for AMI to be ready...")
    waiter = ec2.get_waiter("image_available")
    waiter.wait(ImageIds=[ami_id])
    print("AMI is ready!")

    # Step 3 — launch new EC2 from that AMI
    new_instance = ec2.run_instances(
        ImageId=ami_id,
        InstanceType=instance_details["instance_type"],
        SubnetId=instance_details["subnet_id"],
        SecurityGroupIds=instance_details["security_groups"],
        KeyName=instance_details["key_name"],
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "Name", "Value": "disaster-recovery-restored"},
                    {"Key": "RestoredFrom", "Value": INSTANCE_ID},
                    {"Key": "RestoredAt", "Value": str(datetime.datetime.now())}
                ]
            }
        ]
    )

    new_instance_id = new_instance["Instances"][0]["InstanceId"]
    return new_instance_id, ami_id

def lambda_handler(event, context):
    """
    Main Lambda entry point.
    CloudWatch triggers this when EC2 status check fails.
    """
    print(f"Lambda triggered at {datetime.datetime.now()}")
    print(f"Event: {json.dumps(event)}")

    try:
        # Step 1 — check if instance is actually down
        response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
        state = response["Reservations"][0]["Instances"][0]["State"]["Name"]
        print(f"Instance state: {state}")

        if state == "running":
            print("Instance is running — false alarm, no action needed")
            return {"status": "ok", "message": "Instance is healthy"}

        # Step 2 — find latest snapshot
        print("Instance is down! Finding latest snapshot...")
        snapshot = get_latest_snapshot()

        if not snapshot:
            send_alert(
                "CRITICAL: Recovery Failed — No Snapshot Found",
                f"Instance {INSTANCE_ID} is down but no backup snapshot was found. Manual intervention required!"
            )
            return {"status": "error", "message": "No snapshot found"}

        snapshot_id = snapshot["SnapshotId"]
        snapshot_time = snapshot["StartTime"].strftime("%Y-%m-%d %H:%M")
        print(f"Latest snapshot: {snapshot_id} from {snapshot_time}")

        # Step 3 — get original instance settings
        instance_details = get_instance_details()
        print(f"Instance details: {instance_details}")

        # Step 4 — restore from snapshot
        print("Starting recovery...")
        send_alert(
            "WARNING: EC2 Down — Recovery Started",
            f"Instance {INSTANCE_ID} is down.\nLatest snapshot: {snapshot_id} from {snapshot_time}\nRecovery started automatically..."
        )

        new_instance_id, ami_id = restore_from_snapshot(snapshot_id, instance_details)

        # Step 5 — send success alert
        message = f"""
RECOVERY COMPLETE!

Original instance: {INSTANCE_ID} (down)
New instance: {new_instance_id} (restored)
Restored from snapshot: {snapshot_id}
Snapshot taken at: {snapshot_time}
Recovery completed at: {datetime.datetime.now()}

Your application should be back online shortly.
        """
        send_alert("SUCCESS: EC2 Recovery Complete", message)
        print(f"Recovery complete! New instance: {new_instance_id}")

        return {
            "status": "success",
            "original_instance": INSTANCE_ID,
            "new_instance": new_instance_id,
            "snapshot_used": snapshot_id,
            "ami_created": ami_id
        }

    except Exception as e:
        error_msg = f"Recovery failed with error: {str(e)}"
        print(error_msg)
        send_alert("CRITICAL: Recovery Failed", error_msg)
        return {"status": "error", "message": error_msg}
