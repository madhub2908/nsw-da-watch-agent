from aws_cdk import (
   Duration,
   RemovalPolicy,
   Stack,
   CfnOutput,
   aws_s3 as s3,
   aws_lambda as _lambda,
   aws_events as events,
   aws_events_targets as targets,
   aws_dynamodb as dynamodb,
)
from constructs import Construct

class InfraStack(Stack):
   def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
       super().__init__(scope, construct_id, **kwargs)
       # S3 bucket for raw ingestion outputs
       raw_bucket = s3.Bucket(
           self,
           "RawBucket",
           block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
           versioned=True,
           encryption=s3.BucketEncryption.S3_MANAGED,
           enforce_ssl=True,
           removal_policy=RemovalPolicy.RETAIN,  # safer for portfolio; change later if you want
           lifecycle_rules=[
               s3.LifecycleRule(expiration=Duration.days(30))
           ],
       )
       # DynamoDB tables
       da_applications = dynamodb.Table(
           self,
           "DaApplicationsTable",
           partition_key=dynamodb.Attribute(name="pk", type=dynamodb.AttributeType.STRING),
           sort_key=dynamodb.Attribute(name="sk", type=dynamodb.AttributeType.STRING),
           billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
           point_in_time_recovery=True,
           removal_policy=RemovalPolicy.RETAIN,
       )
       da_updates = dynamodb.Table(
           self,
           "DaUpdatesTable",
           partition_key=dynamodb.Attribute(name="pk", type=dynamodb.AttributeType.STRING),
           sort_key=dynamodb.Attribute(name="ts", type=dynamodb.AttributeType.STRING),
           billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
           point_in_time_recovery=True,
           removal_policy=RemovalPolicy.RETAIN,
       )
       watch_profiles = dynamodb.Table(
           self,
           "WatchProfilesTable",
           partition_key=dynamodb.Attribute(
               name="profile_id", type=dynamodb.AttributeType.STRING
           ),
           billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
           point_in_time_recovery=True,
           removal_policy=RemovalPolicy.RETAIN,
       )
       # Lambda function (writes a health check file to S3 + writes a health item to DynamoDB)
       ingest_hello_fn = _lambda.Function(
           self,
           "IngestHelloFn",
           runtime=_lambda.Runtime.PYTHON_3_11,
           handler="handler.main",
           code=_lambda.Code.from_asset("services/ingest_hello"),
           timeout=Duration.seconds(30),
           memory_size=256,
           environment={
               "RAW_BUCKET_NAME": raw_bucket.bucket_name,
               "DA_APPLICATIONS_TABLE": da_applications.table_name,
               "DA_UPDATES_TABLE": da_updates.table_name,
               "WATCH_PROFILES_TABLE": watch_profiles.table_name,
           },
       )
       # Permissions
       raw_bucket.grant_put(ingest_hello_fn)
       da_applications.grant_write_data(ingest_hello_fn)
       da_updates.grant_write_data(ingest_hello_fn)
       watch_profiles.grant_write_data(ingest_hello_fn)
       # EventBridge schedule:
       # NOTE: events.Rule cron is effectively UTC-based. We'll upgrade to EventBridge Scheduler
       # with explicit Australia/Sydney timezone later.
       daily_rule = events.Rule(
           self,
           "DailyIngestSchedule",
           schedule=events.Schedule.cron(minute="0", hour="19"),
       )
       daily_rule.add_target(targets.LambdaFunction(ingest_hello_fn))
       # Outputs
       CfnOutput(self, "RawBucketName", value=raw_bucket.bucket_name)
       CfnOutput(self, "IngestHelloFunctionName", value=ingest_hello_fn.function_name)
       CfnOutput(self, "DaApplicationsTableName", value=da_applications.table_name)
       CfnOutput(self, "DaUpdatesTableName", value=da_updates.table_name)
       CfnOutput(self, "WatchProfilesTableName", value=watch_profiles.table_name)
