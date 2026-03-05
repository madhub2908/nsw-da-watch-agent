import json
import os
from datetime import datetime, timezone
import boto3
s3 = boto3.client("s3")

def main(event, context):
   bucket = os.environ["RAW_BUCKET_NAME"]
   now = datetime.now(timezone.utc).isoformat()
   payload = {
       "status": "ok",
       "timestamp_utc": now,
       "event_summary": {
           "keys": list(event.keys()) if isinstance(event, dict) else str(type(event))
       },
   }
   s3.put_object(
       Bucket=bucket,
       Key="health/last_run.json",
       Body=json.dumps(payload).encode("utf-8"),
       ContentType="application/json",
   )
   print(f"Wrote health/last_run.json to s3://{bucket}/health/last_run.json at {now}")
   return payload
