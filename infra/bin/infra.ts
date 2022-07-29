#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { Tags } from 'aws-cdk-lib';
import { BillFetcherStack } from '../lib/infra-stack';

const app = new cdk.App();
Tags.of(app).add("bill-fetcher", "true");
new BillFetcherStack(app, 'BillFetcherStack');
