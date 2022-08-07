import { Construct } from 'constructs';
import * as cdk from 'aws-cdk-lib';
import * as s3 from "aws-cdk-lib/aws-s3";
import * as sfn from 'aws-cdk-lib/aws-stepfunctions'
import * as sfn_tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import { FetchingStepSubStack } from './bill-fetching-stack';
import { EmailSendingStepSubStack } from './email-sending-stack';

export class BillFetcherStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const fetcherBucket = new s3.Bucket(this, 'bill-fetcher-bucket', {
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      versioned: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const fetchingStep = new FetchingStepSubStack(this, "fetching-stack", {fetcherBucket});
    const emailSendingStep = new EmailSendingStepSubStack(this, "email-stack", {fetcherBucket});

    const runTask = new sfn_tasks.EcsRunTask(this, 'run-bill-fetcher', {
      integrationPattern: sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
      cluster: fetchingStep.cluster,
      taskDefinition: fetchingStep.fargateTaskDefinition,
      launchTarget: new sfn_tasks.EcsFargateLaunchTarget(),
      containerOverrides: [{
        containerDefinition: fetchingStep.container,
        environment: [{ name: 'TASK_TOKEN', value: sfn.JsonPath.taskToken }],
      }],
      assignPublicIp: true,
    });

    const lambdaTask = new sfn_tasks.LambdaInvoke(this, 'send-bill-lambda', {
      lambdaFunction: emailSendingStep.billSenderFunction,
      timeout: cdk.Duration.seconds(30),
    });

    const success = new sfn.Succeed(this, 'We did it!');
    const fail = new sfn.Fail(this, "Failed!");

    const definition = runTask.
      next(lambdaTask).
      next(success);

    const billFetcherSm = new sfn.StateMachine(this, 'bill-fetcher-sm', {
      definition,
      timeout: cdk.Duration.minutes(1),
    });

    // we need to allow fetcher to send Task Response to the Step Function execution engine
    billFetcherSm.grantTaskResponse(fetchingStep.fargateTaskDefinition.taskRole);
  }
}
