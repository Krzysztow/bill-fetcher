#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { BillFetcherStack } from '../lib/infra-stack';

const app = new cdk.App();
new BillFetcherStack(app, 'BillFetcherStack');
