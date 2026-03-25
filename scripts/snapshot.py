import boto3
import datetime

REGION = "us-east-1"
SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:716156542960:disaster-recovery-alerts"
INSTANCE_ID = "i-0b40f96ac7bb883ce"

ec2 = boto3.client("ec2", region_name=REGION)
sns = boto3.client("sns", region_name=REGION)

def get_instance_volumes(instance_id):
    response = ec2.describe_instances(InstanceIds=[instance_id])
    volumes = []
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            for mapping in instance["BlockDeviceMappings"]:
                volumes.append(mapping["Ebs"]["VolumeId"])
    return volumes

def create_snapshot(volume_id, instance_id):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M")
    description = f"AutoBackup-{instance_id}-{timestamp}"
    response = ec2.create_snapshot(
        VolumeId=volume_id,
        Description=description,
        TagSpecifications=[{
            "ResourceType": "snapshot",
            "Tags": [
                {"Key": "Name", "Value": description},
                {"Key": "AutoBackup", "Value": "true"},
                {"Key": "InstanceId", "Value": instance_id}
            ]
        }]
    )
    snapshot_id = response["SnapshotId"]
    print(f"Snapshot created: {snapshot_id} for volume {volume_id}")
    return snapshot_id

def send_alert(message, subject):
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=message,
        Subject=subject
    )
    print(f"Alert sent: {subject}")

def main():
    print(f"Starting backup for instance: {INSTANCE_ID}")
    volumes = get_instance_volumes(INSTANCE_ID)
    print(f"Found {len(volumes)} volume(s): {volumes}")

    snapshot_ids = []
    for volume_id in volumes:
        snapshot_id = create_snapshot(volume_id, INSTANCE_ID)
        snapshot_ids.append(snapshot_id)

    message = f"""
Backup Successful!

Instance ID: {INSTANCE_ID}
Volumes backed up: {volumes}
Snapshots created: {snapshot_ids}
Time: {datetime.datetime.now()}
    """
    send_alert(message, "SUCCESS: Backup Completed")
    print("Backup completed successfully!")

if __name__ == "__main__":
    main()
