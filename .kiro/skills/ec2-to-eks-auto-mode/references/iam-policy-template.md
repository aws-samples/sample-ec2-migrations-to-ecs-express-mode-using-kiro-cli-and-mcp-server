# IAM Policy Template for EKS Pod Identity

Use this template to create the pod IAM policy. Replace placeholders with actual values.

## DynamoDB + S3 Access (Common for Blog/CRUD Apps)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": "arn:aws:dynamodb:<REGION>:<ACCOUNT_ID>:table/<TABLE_NAME>"
    },
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::<BUCKET_NAME>",
        "arn:aws:s3:::<BUCKET_NAME>/*"
      ]
    }
  ]
}
```

## Pod Role Trust Policy (EKS Pod Identity)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "pods.eks.amazonaws.com"
      },
      "Action": [
        "sts:AssumeRole",
        "sts:TagSession"
      ]
    }
  ]
}
```

## Notes

- Pod Identity is preferred over IRSA for EKS Auto Mode clusters
- The trust policy uses `pods.eks.amazonaws.com` (not `eks.amazonaws.com`)
- `sts:TagSession` is required alongside `sts:AssumeRole`
- Scope resources to specific ARNs — never use `*`
