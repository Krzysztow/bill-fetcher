import { Duration, RemovalPolicy, Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { DockerImageAsset } from 'aws-cdk-lib/aws-ecr-assets';
import { Bucket, BucketEncryption } from 'aws-cdk-lib/aws-s3';
import { EcsRunTask, EcsFargateLaunchTarget } from 'aws-cdk-lib/aws-stepfunctions-tasks'
import * as sfn from 'aws-cdk-lib/aws-stepfunctions'
import { FargateTaskDefinition, ContainerImage, LogDriver, Cluster } from 'aws-cdk-lib/aws-ecs';
import * as path from 'path';
import { RetentionDays } from 'aws-cdk-lib/aws-logs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as py_lambda from '@aws-cdk/aws-lambda-python-alpha';


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

    const cluster = new Cluster(this, 'bill-fetcher-cluster', {
      clusterName: "bill-fetcher-cluster",
      enableFargateCapacityProviders: true,
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
 
    
    const runTask = new EcsRunTask(this, 'run-bill-fetcher', {
      integrationPattern: sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
      cluster,
      taskDefinition: fargateTaskDefinition,
      launchTarget: new EcsFargateLaunchTarget(),
      containerOverrides: [{
        containerDefinition: container,
        environment: [{ name: 'TASK_TOKEN', value: sfn.JsonPath.taskToken }],
      }],
    });

    const success = new sfn.Succeed(this, 'We did it!');
    const fail = new sfn.Fail(this, "Failed!");

    const definition = runTask.next(success);

    const billFetcherSm = new sfn.StateMachine(this, 'bill-fetcher-sm', {
      definition,
      timeout: Duration.minutes(1),
    });

    billFetcherSm.grantTaskResponse(fargateTaskDefinition.taskRole);


    const billSenderFunction = new py_lambda.PythonFunction(this, 'bill-sender', {
      entry: path.join(__dirname, '..', '..', 'bill-sender'),
      runtime: lambda.Runtime.PYTHON_3_9,
      index: 'aws_sender.py',
      handler: 'send_bill__'
    });
  }
}
