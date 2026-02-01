#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { CdkInfrastructureStack } from '../lib/cdk-infrastructure-stack';

const app = new cdk.App();
new CdkInfrastructureStack(app, 'CdkInfrastructureStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});