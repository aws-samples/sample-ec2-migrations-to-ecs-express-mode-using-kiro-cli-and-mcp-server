# IAM Policy Template for EKS Pod Identity

Replace placeholders with actual values. Only include statements for services your app uses.

## Pod Role Trust Policy (required for all apps)

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "pods.eks.amazonaws.com"},
    "Action": ["sts:AssumeRole", "sts:TagSession"]
  }]
}
```

## Common Service Policies (include only what's needed)

### DynamoDB
```json
{
  "Sid": "DynamoDB",
  "Effect": "Allow",
  "Action": ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:BatchWriteItem", "dynamodb:BatchGetItem"],
  "Resource": "arn:aws:dynamodb:<REGION>:<ACCOUNT>:table/<TABLE>"
}
```

### S3
```json
{
  "Sid": "S3",
  "Effect": "Allow",
  "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject", "s3:ListBucket"],
  "Resource": ["arn:aws:s3:::<BUCKET>", "arn:aws:s3:::<BUCKET>/*"]
}
```

### SQS
```json
{
  "Sid": "SQS",
  "Effect": "Allow",
  "Action": ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"],
  "Resource": "arn:aws:sqs:<REGION>:<ACCOUNT>:<QUEUE>"
}
```

### SNS
```json
{
  "Sid": "SNS",
  "Effect": "Allow",
  "Action": ["sns:Publish"],
  "Resource": "arn:aws:sns:<REGION>:<ACCOUNT>:<TOPIC>"
}
```

### Secrets Manager
```json
{
  "Sid": "Secrets",
  "Effect": "Allow",
  "Action": ["secretsmanager:GetSecretValue"],
  "Resource": "arn:aws:secretsmanager:<REGION>:<ACCOUNT>:secret:<SECRET_NAME>*"
}
```

### SSM Parameter Store
```json
{
  "Sid": "SSM",
  "Effect": "Allow",
  "Action": ["ssm:GetParameter", "ssm:GetParameters"],
  "Resource": "arn:aws:ssm:<REGION>:<ACCOUNT>:parameter/<PREFIX>/*"
}
```

## Notes

- Pod Identity is preferred over IRSA for EKS Auto Mode
- Trust policy uses `pods.eks.amazonaws.com` (not `eks.amazonaws.com`)
- `sts:TagSession` is required alongside `sts:AssumeRole`
- Always scope resources to specific ARNs — never use `*`
- Copy permissions from the existing EC2 instance profile as baseline
- **CRITICAL**: All `<REGION>` placeholders MUST be replaced with the actual `<TARGET_REGION>` from BlogAppStack. A region mismatch (e.g., `ap-southeast-1` vs `ap-southeast-2`) causes `AccessDeniedException` at runtime.
- Always derive resource values (table name, bucket name, user pool ID) from LIVE CloudFormation stack outputs, not from cached files
