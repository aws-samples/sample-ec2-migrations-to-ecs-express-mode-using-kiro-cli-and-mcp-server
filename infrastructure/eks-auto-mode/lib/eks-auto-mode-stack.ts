import * as cdk from 'aws-cdk-lib';
import * as eks from 'aws-cdk-lib/aws-eks-v2';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';

export class EksAutoModeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const vpc = ec2.Vpc.fromLookup(this, 'DefaultVpc', { isDefault: true });

    // EKS Auto Mode cluster - aws-eks-v2 enables Auto Mode by default
    const cluster = new eks.Cluster(this, 'BlogEksCluster', {
      clusterName: 'blog-eks-auto-cluster',
      version: eks.KubernetesVersion.V1_34,
      vpc,
      vpcSubnets: [{ subnetType: ec2.SubnetType.PUBLIC }],
      // Auto Mode is the default - no CfnCluster workaround needed
      defaultCapacityType: eks.DefaultCapacityType.AUTOMODE,
    });

    new cdk.CfnOutput(this, 'ClusterName', { value: cluster.clusterName });
    new cdk.CfnOutput(this, 'ClusterArn', { value: cluster.clusterArn });
    new cdk.CfnOutput(this, 'ConfigCommand', {
      value: `aws eks update-kubeconfig --name ${cluster.clusterName} --region ${this.region}`,
    });
  }
}
