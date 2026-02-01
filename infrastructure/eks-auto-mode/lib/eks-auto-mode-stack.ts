import * as cdk from 'aws-cdk-lib';
import * as eks from 'aws-cdk-lib/aws-eks';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export class EksAutoModeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Use default VPC
    const vpc = ec2.Vpc.fromLookup(this, 'DefaultVpc', {
      isDefault: true,
    });

    // IAM Role for EKS Cluster
    const clusterRole = new iam.Role(this, 'EksClusterRole', {
      assumedBy: new iam.ServicePrincipal('eks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEKSClusterPolicy'),
      ],
    });

    // IAM Role for EKS Auto Mode compute
    const autoModeRole = new iam.Role(this, 'EksAutoModeRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEKSWorkerNodePolicy'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEKS_CNI_Policy'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEC2ContainerRegistryReadOnly'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
      ],
    });

    // EKS Cluster with Auto Mode - K8s 1.30 (auth mode defaults to API for new clusters)
    const cluster = new eks.Cluster(this, 'BlogEksCluster', {
      clusterName: 'blog-eks-auto-cluster',
      version: eks.KubernetesVersion.V1_30,
      vpc,
      vpcSubnets: [{ subnetType: ec2.SubnetType.PUBLIC }],
      role: clusterRole,
      defaultCapacity: 0,
    });

    // Enable Auto Mode via CfnCluster
    const cfnCluster = cluster.node.defaultChild as eks.CfnCluster;
    (cfnCluster as any).computeConfig = {
      enabled: true,
      nodeRoleArn: autoModeRole.roleArn,
    };

    // Outputs
    new cdk.CfnOutput(this, 'ClusterName', {
      value: cluster.clusterName,
    });

    new cdk.CfnOutput(this, 'ClusterArn', {
      value: cluster.clusterArn,
    });

    new cdk.CfnOutput(this, 'ConfigCommand', {
      value: `aws eks update-kubeconfig --name ${cluster.clusterName} --region ${this.region}`,
    });
  }
}
