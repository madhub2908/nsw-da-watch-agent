import json
import os
from datetime import datetime, timezone
import boto3
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")


def main(event, context):
   bucket = os.environ["RAW_BUCKET_NAME"]
   now = datetime.now(timezone.utc).isoformat()
    # 1) Write health file to S3
   payload = {
       "status": "ok",
       "timestamp_utc": now,
       "event_keys": list(event.keys()) if isinstance(event, dict) else [],
   }
   s3.put_object(
       Bucket=bucket,
       Key="health/last_run.json",
       Body=json.dumps(payload).encode("utf-8"),
       ContentType="application/json",
   )

   # 2) Write health item to DynamoDB (prove permissions + wiring)
   da_table_name = os.environ["DA_APPLICATIONS_TABLE"]
   table = dynamodb.Table(da_table_name)
   table.put_item(
       Item={
           "pk": "HEALTH",
           "sk": "LAST_RUN",
           "timestamp_utc": now,
           "status": "ok",
       }
   )
   print(f"Wrote S3 health file to s3://{bucket}/health/last_run.json")
   print(f"Wrote DynamoDB health item to table {da_table_name} at {now}")
   return {"status": "ok", "timestamp_utc": now}
