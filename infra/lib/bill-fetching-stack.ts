import { Construct } from 'constructs';
import * as cdk from 'aws-cdk-lib';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecr from 'aws-cdk-lib/aws-ecr-assets';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as ssm from 'aws-cdk-lib/aws-ssm';

import * as path from 'path';

interface FetchingStepSubStackProps {
  fetcherBucket: s3.Bucket,
}


export class FetchingStepSubStack extends Construct {

  readonly cluster: ecs.Cluster;
  readonly fargateTaskDefinition: ecs.FargateTaskDefinition;
  readonly container: ecs.ContainerDefinition;

  constructor(scope: Construct, id: string, directProps: FetchingStepSubStackProps) {
    super(scope, id);

    // use parameter store, as it's cheaper than the secret manager
    // Note: secure parameter needs to be created manually
    const hoPassword = ssm.StringParameter.fromSecureStringParameterAttributes(this, 'bill-fetcher-ho-password', {
      parameterName: '/bill-fetcher/secrets/password',
    });
    const hoUsername = ssm.StringParameter.fromSecureStringParameterAttributes(this, 'bill-fetcher-ho-username', {
      parameterName: '/bill-fetcher/secrets/username',
    });


    const asset = new ecr.DockerImageAsset(this, 'bill-fetcher', {
      directory: path.join(__dirname, '..', '..', 'src'),
      file: path.join('fetch-bill', 'Dockerfile'),
    });

    this.fargateTaskDefinition = new ecs.FargateTaskDefinition(this, 'bill-fetcher-task-def', {
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

    this.cluster = new ecs.Cluster(this, 'bill-fetcher-cluster', {
      clusterName: "bill-fetcher-cluster",
      enableFargateCapacityProviders: true,
      vpc,
    });

    this.container = this.fargateTaskDefinition.addContainer("bill-fetcher-container", {
      image: ecs.ContainerImage.fromDockerImageAsset(asset),
      //command: TODO: override this
      environment: {
        "RESULT_BUCKET_NAME": directProps.fetcherBucket.bucketName,
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
        logRetention: logs.RetentionDays.ONE_DAY,
      }),
    });

    directProps.fetcherBucket.grantWrite(this.fargateTaskDefinition.taskRole);
  }

}
