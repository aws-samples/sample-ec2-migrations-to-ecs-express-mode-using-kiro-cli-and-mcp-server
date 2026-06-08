# Deploy Script - Region Configuration

## Usage

### Deploy to eu-north-1 (default)
```bash
cd scripts/deployment
./deploy.sh
```

### Deploy to specific region
```bash
./deploy.sh us-west-2
./deploy.sh eu-west-1
./deploy.sh ap-southeast-1
```

### Deploy with a new VPC (no default VPC)
```bash
./deploy.sh us-west-2 no_default_vpc
```

## What the Script Does

1. Accepts region parameter (defaults to `eu-north-1`)
2. Builds and deploys CDK infrastructure to the specified region
3. Creates: Cognito User Pool, DynamoDB table, S3 bucket, EC2 instance with ALB
4. Auto-detects region from CloudFormation stack outputs
5. Packages and deploys the sample application to EC2 via SSM
6. Validates health checks

## Verification

After deployment, verify the stack:
```bash
aws cloudformation describe-stacks \
  --stack-name BlogAppStack \
  --region <your-region> \
  --query 'Stacks[0].StackStatus'

aws cloudformation describe-stacks \
  --stack-name BlogAppStack \
  --region <your-region> \
  --query 'Stacks[0].Outputs'
```

## Notes

- Each region gets its own isolated resources (Cognito, S3, DynamoDB)
- The `sample-application/.env` file is auto-updated with correct resource IDs
- Stack outputs are saved to `stack-outputs.json` (gitignored)
