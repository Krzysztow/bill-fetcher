import { Construct } from 'constructs';
import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';

import * as fs from 'fs';
import * as path from 'path';

interface EmailSendingStepSubStackProps{
  fetcherBucket: s3.Bucket,
}


export class EmailSendingStepSubStack extends Construct {

  readonly billSenderFunction: lambda.Function;

  constructor(scope: Construct, id: string, directProps: EmailSendingStepSubStackProps) {
    super(scope, id);

    const lambdaRuntime = lambda.Runtime.PYTHON_3_9;
    const lambdaBundlingRootDir = [__dirname, '..', 'lambda-builder'];
    const bytes = fs.readFileSync(path.join(...lambdaBundlingRootDir, 'Dockerfile'));
    if (!bytes.indexOf(lambdaRuntime.bundlingImage.image)) {
      throw Error(`lambda-builder/Dockerfile needs to be based off of ${lambdaRuntime.bundlingImage.image}. Contents: ${bytes}`);
    }
    const lambdaBundlingImage = cdk.DockerImage.fromBuild(path.join(__dirname, '..', 'lambda-builder'));

    this.billSenderFunction = new lambda.Function(this, 'bill-sender', {
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
              `python3 -m pip install -t ${cdk.AssetStaging.BUNDLING_OUTPUT_DIR}/ -r /tmp/requirements.txt`,
              `cp -rp . ${cdk.AssetStaging.BUNDLING_OUTPUT_DIR}/`
            ].join('&&'),
          ],
        }
      }),
    });

    directProps.fetcherBucket.grantRead(this.billSenderFunction);
    this.billSenderFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['ses:SendEmail', 'ses:SendRawEmail'],
      //chriswielgo+ses.com needs to correspond to sending identity - maybe I should introduce env variable injected from here
      resources: [`arn:aws:ses:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:identity/chriswielgo+ses@gmail.com`],
      effect: iam.Effect.ALLOW,
    }));

  }
}
