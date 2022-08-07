import { Duration, RemovalPolicy, Stack, StackProps, AssetStaging, DockerImage } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { DockerImageAsset } from 'aws-cdk-lib/aws-ecr-assets';
import { Bucket, BucketEncryption } from 'aws-cdk-lib/aws-s3';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { EcsRunTask, EcsFargateLaunchTarget, LambdaInvoke } from 'aws-cdk-lib/aws-stepfunctions-tasks'
import * as sfn from 'aws-cdk-lib/aws-stepfunctions'
import * as ecs from 'aws-cdk-lib/aws-ecs';
import { RetentionDays } from 'aws-cdk-lib/aws-logs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as fs from 'fs';
import * as path from 'path';


export class BillFetcherStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const fetcherBucket = new Bucket(this, 'bill-fetcher-bucket', {
      encryption: BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      versioned: true,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    // use parameter store, as it's cheaper than the secret manager
    // Note: secure parameter needs to be created manually
    const hoPassword = ssm.StringParameter.fromSecureStringParameterAttributes(this, 'bill-fetcher-ho-password', {
      parameterName: '/bill-fetcher/secrets/password',
    });
    const hoUsername = ssm.StringParameter.fromSecureStringParameterAttributes(this, 'bill-fetcher-ho-username', {
      parameterName: '/bill-fetcher/secrets/username',
    });

    const asset = new DockerImageAsset(this, 'bill-fetcher', {
      directory: path.join(__dirname, '..', '..', 'src'),
      file: path.join('fetch-bill', 'Dockerfile'),
    });

    const fargateTaskDefinition = new ecs.FargateTaskDefinition(this, 'bill-fetcher-task-def', {
      memoryLimitMiB: 2048,
      cpu: 1024,
    });

    const vpc = new ec2.Vpc(this, 'bill-fetcher-vpc', {
      cidr: "10.0.0.0/16",
      natGateways: 0, //we don't want NAT gateway as it generates cost -> run the fetcher ECS tasks in public subnet
      subnetConfiguration: [
        {
          name: "bill-fetcher-public-subnet",
          subnetType: ec2.SubnetType.PUBLIC,
        }
      ]
    });

    const cluster = new ecs.Cluster(this, 'bill-fetcher-cluster', {
      clusterName: "bill-fetcher-cluster",
      enableFargateCapacityProviders: true,
      vpc,
    });

    const container = fargateTaskDefinition.addContainer("bill-fetcher-container", {
      image: ecs.ContainerImage.fromDockerImageAsset(asset),
      //command: TODO: override this
      environment: {
        "RESULT_BUCKET_NAME": fetcherBucket.bucketName,
      },
      secrets: {
        "HO_USERNAME": ecs.Secret.fromSsmParameter(hoUsername),
        "HO_PASSWORD": ecs.Secret.fromSsmParameter(hoPassword),
      },
      memoryLimitMiB: 2048,
      cpu: 1024,
      entryPoint: ["python3", "./aws_fetcher.py"],
      logging: ecs.LogDriver.awsLogs({
        streamPrefix: 'bill-fetcher-container',
        logRetention: RetentionDays.ONE_DAY,
      }),
    });

    fetcherBucket.grantWrite(fargateTaskDefinition.taskRole);

    const lambdaRuntime = lambda.Runtime.PYTHON_3_9;
    const lambdaBundlingRootDir = [__dirname, '..', 'lambda-builder'];
    const bytes = fs.readFileSync(path.join(...lambdaBundlingRootDir, 'Dockerfile'));
    if (!bytes.indexOf(lambdaRuntime.bundlingImage.image)) {
      throw Error(`lambda-builder/Dockerfile needs to be based off of ${lambdaRuntime.bundlingImage.image}. Contents: ${bytes}`);
    }
    const lambdaBundlingImage = DockerImage.fromBuild(path.join(__dirname, '..', 'lambda-builder'));

    const billSenderFunction = new lambda.Function(this, 'bill-sender', {
      runtime: lambdaRuntime,
      handler: 'aws_sender.send_bill',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', '..', 'src'), {
        bundling: {
          image: lambdaBundlingImage,
          user: '0:0', //this image has problems with pipenv accessing it's system-wide paths (e.g. /.cache)
          command: [
            'bash',
            '-c',
            [
              'cd bill-sender',
              'python3 -m pipenv requirements > /tmp/requirements.txt',
              `python3 -m pip install -t ${AssetStaging.BUNDLING_OUTPUT_DIR}/ -r /tmp/requirements.txt`,
              `cp -rp . ${AssetStaging.BUNDLING_OUTPUT_DIR}/`
            ].join('&&'),
          ],
        }
      }),
    });


    const runTask = new EcsRunTask(this, 'run-bill-fetcher', {
      integrationPattern: sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
      cluster,
      taskDefinition: fargateTaskDefinition,
      launchTarget: new EcsFargateLaunchTarget(),
      containerOverrides: [{
        containerDefinition: container,
        environment: [{ name: 'TASK_TOKEN', value: sfn.JsonPath.taskToken }],
      }],
      assignPublicIp: true,
    });

    const lambdaTask = new LambdaInvoke(this, 'send-bill-lambda', {
      lambdaFunction: billSenderFunction,
      timeout: Duration.seconds(30),
    });

    fetcherBucket.grantRead(billSenderFunction);


    const success = new sfn.Succeed(this, 'We did it!');
    const fail = new sfn.Fail(this, "Failed!");

    const definition = runTask.
      next(lambdaTask).
      next(success);

    const billFetcherSm = new sfn.StateMachine(this, 'bill-fetcher-sm', {
      definition,
      timeout: Duration.minutes(1),
    });

    billFetcherSm.grantTaskResponse(fargateTaskDefinition.taskRole);
  }
}
