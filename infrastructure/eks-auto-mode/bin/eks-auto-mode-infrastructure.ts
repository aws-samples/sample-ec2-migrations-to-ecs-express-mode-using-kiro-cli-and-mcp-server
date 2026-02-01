#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { EksAutoModeStack } from '../lib/eks-auto-mode-stack';

const app = new cdk.App();
new EksAutoModeStack(app, 'EksAutoModeStack', {
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT, 
    region: process.env.CDK_DEFAULT_REGION || 'eu-north-1'
  },
});
