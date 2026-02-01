import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as targets from 'aws-cdk-lib/aws-elasticloadbalancingv2-targets';
import { Construct } from 'constructs';

export class CdkInfrastructureStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Cognito User Pool
    const userPool = new cognito.UserPool(this, 'BlogUserPool', {
      userPoolName: 'blog-user-pool',
      selfSignUpEnabled: true,
      signInAliases: {
        email: true,
      },
      autoVerify: {
        email: true,
      },
      userVerification: {
        emailSubject: 'Verify your email for the blog app',
        emailBody: 'Your verification code is {####}',
        emailStyle: cognito.VerificationEmailStyle.CODE,
      },
      standardAttributes: {
        email: {
          required: true,
          mutable: true,
        },
      },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: false,
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Cognito User Pool Client
    const userPoolClient = new cognito.UserPoolClient(this, 'BlogUserPoolClient', {
      userPool,
      userPoolClientName: 'blog-web-client',
      generateSecret: false,
      authFlows: {
        userPassword: true,
        userSrp: true,
      },
      oAuth: {
        flows: {
          authorizationCodeGrant: true,
        },
        scopes: [cognito.OAuthScope.EMAIL, cognito.OAuthScope.OPENID, cognito.OAuthScope.PROFILE],
        callbackUrls: ['http://localhost:3000/callback'],
        logoutUrls: ['http://localhost:3000/'],
      },
    });

    // S3 Bucket for images (PRIVATE)
    const imagesBucket = new s3.Bucket(this, 'BlogImagesBucket', {
      bucketName: `blog-images-private-${this.account}-${this.region}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      cors: [{
        allowedHeaders: ['*'],
        allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST, s3.HttpMethods.DELETE, s3.HttpMethods.HEAD],
        allowedOrigins: ['*'],
        exposedHeaders: ['ETag'],
        maxAge: 3000,
      }],
    });

    // DynamoDB Table for blog posts
    const postsTable = new dynamodb.Table(this, 'BlogPostsTable', {
      tableName: 'blog-posts',
      partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Use default VPC
    const vpc = ec2.Vpc.fromLookup(this, 'DefaultVpc', {
      isDefault: true,
    });

    // Security Group for EC2
    const webServerSG = new ec2.SecurityGroup(this, 'WebServerSecurityGroup', {
      vpc,
      description: 'Security group for blog web server',
      allowAllOutbound: true,
    });

    webServerSG.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(3000),
      'Allow HTTP traffic from ALB'
    );

    webServerSG.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(22),
      'Allow SSH access'
    );

    // IAM Role for EC2
    const ec2Role = new iam.Role(this, 'BlogAppEC2Role', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
      ],
    });

    // Grant permissions to DynamoDB, S3, and Cognito
    postsTable.grantReadWriteData(ec2Role);
    imagesBucket.grantReadWrite(ec2Role);
    
    // Add Cognito permissions
    ec2Role.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'cognito-idp:AdminInitiateAuth',
        'cognito-idp:AdminCreateUser',
        'cognito-idp:AdminSetUserPassword',
        'cognito-idp:AdminConfirmSignUp',
        'cognito-idp:ListUsers',
        'cognito-idp:AdminGetUser',
        'cognito-idp:AdminUpdateUserAttributes',
        'cognito-idp:AdminDeleteUser',
      ],
      resources: [userPool.userPoolArn],
    }));

    // User Data Script - Minimal setup, app will be deployed from sample-app folder
    const userData = ec2.UserData.forLinux();
    userData.addCommands(
      'dnf update -y',
      'dnf install -y nodejs npm git',
      
      // Create application directory
      'mkdir -p /home/ec2-user/blog-app/src /home/ec2-user/blog-app/public',
      'cd /home/ec2-user/blog-app',
      
      // Create package.json with all dependencies
      `cat > package.json << 'EOF'
{
  "name": "sample-blog-app",
  "version": "1.0.0",
  "description": "Sample blog application with Cognito auth and S3 image support",
  "main": "src/server.js",
  "scripts": {
    "start": "node src/server.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "aws-sdk": "^2.1490.0",
    "multer": "^1.4.5-lts.1",
    "uuid": "^9.0.1",
    "cors": "^2.8.5",
    "dotenv": "^16.3.1",
    "jsonwebtoken": "^9.0.2",
    "jwk-to-pem": "^2.0.5",
    "axios": "^1.6.0"
  }
}
EOF`,
      
      // Install dependencies
      'npm install',
      
      // Create environment file
      `cat > .env << 'EOF'
AWS_REGION=${this.region}
DYNAMODB_TABLE=${postsTable.tableName}
S3_BUCKET=${imagesBucket.bucketName}
COGNITO_USER_POOL_ID=${userPool.userPoolId}
COGNITO_CLIENT_ID=${userPoolClient.userPoolClientId}
PORT=3000
EOF`,
      
      // Note: Application files will be deployed via deployment script
      
      // Create systemd service
      `cat > /etc/systemd/system/blog-app.service << 'EOF'
[Unit]
Description=Blog Application
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/blog-app
ExecStart=/usr/bin/node src/server.js
Restart=always

[Install]
WantedBy=multi-user.target
EOF`,
      
      'systemctl daemon-reload',
      'systemctl enable blog-app',
      
      'chown -R ec2-user:ec2-user /home/ec2-user/blog-app'
    );

    // EC2 Instance
    const instance = new ec2.Instance(this, 'BlogAppInstance', {
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
      machineImage: ec2.MachineImage.latestAmazonLinux2023(),
      vpc,
      securityGroup: webServerSG,
      role: ec2Role,
      userData,
      keyName: undefined, // No SSH key needed, use SSM
    });

    // Application Load Balancer
    const alb = new elbv2.ApplicationLoadBalancer(this, 'BlogAppALB', {
      vpc,
      internetFacing: true,
    });

    // Target Group
    const targetGroup = new elbv2.ApplicationTargetGroup(this, 'BlogAppTargetGroup', {
      vpc,
      port: 3000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targets: [new targets.InstanceTarget(instance)],
      healthCheck: {
        path: '/health',
        healthyHttpCodes: '200',
      },
    });

    // Listener
    alb.addListener('BlogAppListener', {
      port: 80,
      defaultTargetGroups: [targetGroup],
    });

    // Outputs
    new cdk.CfnOutput(this, 'LoadBalancerDNS', {
      value: alb.loadBalancerDnsName,
    });

    new cdk.CfnOutput(this, 'ApplicationURL', {
      value: `http://${alb.loadBalancerDnsName}`,
    });

    new cdk.CfnOutput(this, 'SSMCommand', {
      value: `aws ssm start-session --target ${instance.instanceId}`,
    });

    new cdk.CfnOutput(this, 'S3BucketName', {
      value: imagesBucket.bucketName,
    });

    new cdk.CfnOutput(this, 'DynamoDBTableName', {
      value: postsTable.tableName,
    });

    new cdk.CfnOutput(this, 'UserPoolId', {
      value: userPool.userPoolId,
    });

    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: userPoolClient.userPoolClientId,
    });
  }
}
