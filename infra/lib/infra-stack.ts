import { Duration, Stack, StackProps } from 'aws-cdk-lib';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subs from 'aws-cdk-lib/aws-sns-subscriptions';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { Construct } from 'constructs';
import { DockerImageAsset } from 'aws-cdk-lib/aws-ecr-assets';
import { Bucket, BucketEncryption } from 'aws-cdk-lib/aws-s3';
import { RemovalPolicy } from 'aws-cdk-lib';
import { FargateTaskDefinition, ContainerImage, LogDriver } from 'aws-cdk-lib/aws-ecs';
import * as path from 'path';
import { EcsApplication } from 'aws-cdk-lib/aws-codedeploy';
import { RetentionDays } from 'aws-cdk-lib/aws-logs';

export class BillFetcherStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const fetcher_bucket = new Bucket(this, 'bill-fetcher-bucket', {
      encryption: BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      versioned: true,
      removalPolicy: RemovalPolicy.DESTROY,
    });


    const asset = new DockerImageAsset(this, 'bill-fetcher', {
      directory: path.join(__dirname, '..', '..', 'fetch-bill'),
    });

    const fargateTaskDefinition = new FargateTaskDefinition(this, 'bill-fetcher-task-def', {
      memoryLimitMiB: 2048,
      cpu: 1024,
    });

    const container = fargateTaskDefinition.addContainer("bill-fetcher-container", {
      image: ContainerImage.fromDockerImageAsset(asset),
      //command: TODO: override this
      environment: {
        "HO_USERNAME": "chris.wielgo@gmail.com",
        "HO_PASSWORD": "",
        "RESULT_BUCKET_NAME": fetcher_bucket.bucketName,
      },
      memoryLimitMiB: 2048,
      cpu: 1024,
      entryPoint: ["python3", "./aws_fetcher.py"],
      logging: LogDriver.awsLogs({
        streamPrefix: 'bill-fetcher-container',
        logRetention: RetentionDays.ONE_DAY,
      })
    });

    fetcher_bucket.grantWrite(fargateTaskDefinition.taskRole);
    
  }
}
