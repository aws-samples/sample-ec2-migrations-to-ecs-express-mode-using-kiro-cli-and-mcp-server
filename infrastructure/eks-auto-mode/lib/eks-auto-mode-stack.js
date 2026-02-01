"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.EksAutoModeStack = void 0;
const cdk = __importStar(require("aws-cdk-lib"));
const eks = __importStar(require("aws-cdk-lib/aws-eks"));
const ec2 = __importStar(require("aws-cdk-lib/aws-ec2"));
const iam = __importStar(require("aws-cdk-lib/aws-iam"));
class EksAutoModeStack extends cdk.Stack {
    constructor(scope, id, props) {
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
        const cfnCluster = cluster.node.defaultChild;
        cfnCluster.computeConfig = {
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
exports.EksAutoModeStack = EksAutoModeStack;
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiZWtzLWF1dG8tbW9kZS1zdGFjay5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbImVrcy1hdXRvLW1vZGUtc3RhY2sudHMiXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6Ijs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7QUFBQSxpREFBbUM7QUFDbkMseURBQTJDO0FBQzNDLHlEQUEyQztBQUMzQyx5REFBMkM7QUFHM0MsTUFBYSxnQkFBaUIsU0FBUSxHQUFHLENBQUMsS0FBSztJQUM3QyxZQUFZLEtBQWdCLEVBQUUsRUFBVSxFQUFFLEtBQXNCO1FBQzlELEtBQUssQ0FBQyxLQUFLLEVBQUUsRUFBRSxFQUFFLEtBQUssQ0FBQyxDQUFDO1FBRXhCLGtCQUFrQjtRQUNsQixNQUFNLEdBQUcsR0FBRyxHQUFHLENBQUMsR0FBRyxDQUFDLFVBQVUsQ0FBQyxJQUFJLEVBQUUsWUFBWSxFQUFFO1lBQ2pELFNBQVMsRUFBRSxJQUFJO1NBQ2hCLENBQUMsQ0FBQztRQUVILDJCQUEyQjtRQUMzQixNQUFNLFdBQVcsR0FBRyxJQUFJLEdBQUcsQ0FBQyxJQUFJLENBQUMsSUFBSSxFQUFFLGdCQUFnQixFQUFFO1lBQ3ZELFNBQVMsRUFBRSxJQUFJLEdBQUcsQ0FBQyxnQkFBZ0IsQ0FBQyxtQkFBbUIsQ0FBQztZQUN4RCxlQUFlLEVBQUU7Z0JBQ2YsR0FBRyxDQUFDLGFBQWEsQ0FBQyx3QkFBd0IsQ0FBQyx3QkFBd0IsQ0FBQzthQUNyRTtTQUNGLENBQUMsQ0FBQztRQUVILHFDQUFxQztRQUNyQyxNQUFNLFlBQVksR0FBRyxJQUFJLEdBQUcsQ0FBQyxJQUFJLENBQUMsSUFBSSxFQUFFLGlCQUFpQixFQUFFO1lBQ3pELFNBQVMsRUFBRSxJQUFJLEdBQUcsQ0FBQyxnQkFBZ0IsQ0FBQyxtQkFBbUIsQ0FBQztZQUN4RCxlQUFlLEVBQUU7Z0JBQ2YsR0FBRyxDQUFDLGFBQWEsQ0FBQyx3QkFBd0IsQ0FBQywyQkFBMkIsQ0FBQztnQkFDdkUsR0FBRyxDQUFDLGFBQWEsQ0FBQyx3QkFBd0IsQ0FBQyxzQkFBc0IsQ0FBQztnQkFDbEUsR0FBRyxDQUFDLGFBQWEsQ0FBQyx3QkFBd0IsQ0FBQyxvQ0FBb0MsQ0FBQztnQkFDaEYsR0FBRyxDQUFDLGFBQWEsQ0FBQyx3QkFBd0IsQ0FBQyw4QkFBOEIsQ0FBQzthQUMzRTtTQUNGLENBQUMsQ0FBQztRQUVILHFGQUFxRjtRQUNyRixNQUFNLE9BQU8sR0FBRyxJQUFJLEdBQUcsQ0FBQyxPQUFPLENBQUMsSUFBSSxFQUFFLGdCQUFnQixFQUFFO1lBQ3RELFdBQVcsRUFBRSx1QkFBdUI7WUFDcEMsT0FBTyxFQUFFLEdBQUcsQ0FBQyxpQkFBaUIsQ0FBQyxLQUFLO1lBQ3BDLEdBQUc7WUFDSCxVQUFVLEVBQUUsQ0FBQyxFQUFFLFVBQVUsRUFBRSxHQUFHLENBQUMsVUFBVSxDQUFDLE1BQU0sRUFBRSxDQUFDO1lBQ25ELElBQUksRUFBRSxXQUFXO1lBQ2pCLGVBQWUsRUFBRSxDQUFDO1NBQ25CLENBQUMsQ0FBQztRQUVILGtDQUFrQztRQUNsQyxNQUFNLFVBQVUsR0FBRyxPQUFPLENBQUMsSUFBSSxDQUFDLFlBQThCLENBQUM7UUFDOUQsVUFBa0IsQ0FBQyxhQUFhLEdBQUc7WUFDbEMsT0FBTyxFQUFFLElBQUk7WUFDYixXQUFXLEVBQUUsWUFBWSxDQUFDLE9BQU87U0FDbEMsQ0FBQztRQUVGLFVBQVU7UUFDVixJQUFJLEdBQUcsQ0FBQyxTQUFTLENBQUMsSUFBSSxFQUFFLGFBQWEsRUFBRTtZQUNyQyxLQUFLLEVBQUUsT0FBTyxDQUFDLFdBQVc7U0FDM0IsQ0FBQyxDQUFDO1FBRUgsSUFBSSxHQUFHLENBQUMsU0FBUyxDQUFDLElBQUksRUFBRSxZQUFZLEVBQUU7WUFDcEMsS0FBSyxFQUFFLE9BQU8sQ0FBQyxVQUFVO1NBQzFCLENBQUMsQ0FBQztRQUVILElBQUksR0FBRyxDQUFDLFNBQVMsQ0FBQyxJQUFJLEVBQUUsZUFBZSxFQUFFO1lBQ3ZDLEtBQUssRUFBRSxvQ0FBb0MsT0FBTyxDQUFDLFdBQVcsYUFBYSxJQUFJLENBQUMsTUFBTSxFQUFFO1NBQ3pGLENBQUMsQ0FBQztJQUNMLENBQUM7Q0FDRjtBQTFERCw0Q0EwREMiLCJzb3VyY2VzQ29udGVudCI6WyJpbXBvcnQgKiBhcyBjZGsgZnJvbSAnYXdzLWNkay1saWInO1xuaW1wb3J0ICogYXMgZWtzIGZyb20gJ2F3cy1jZGstbGliL2F3cy1la3MnO1xuaW1wb3J0ICogYXMgZWMyIGZyb20gJ2F3cy1jZGstbGliL2F3cy1lYzInO1xuaW1wb3J0ICogYXMgaWFtIGZyb20gJ2F3cy1jZGstbGliL2F3cy1pYW0nO1xuaW1wb3J0IHsgQ29uc3RydWN0IH0gZnJvbSAnY29uc3RydWN0cyc7XG5cbmV4cG9ydCBjbGFzcyBFa3NBdXRvTW9kZVN0YWNrIGV4dGVuZHMgY2RrLlN0YWNrIHtcbiAgY29uc3RydWN0b3Ioc2NvcGU6IENvbnN0cnVjdCwgaWQ6IHN0cmluZywgcHJvcHM/OiBjZGsuU3RhY2tQcm9wcykge1xuICAgIHN1cGVyKHNjb3BlLCBpZCwgcHJvcHMpO1xuXG4gICAgLy8gVXNlIGRlZmF1bHQgVlBDXG4gICAgY29uc3QgdnBjID0gZWMyLlZwYy5mcm9tTG9va3VwKHRoaXMsICdEZWZhdWx0VnBjJywge1xuICAgICAgaXNEZWZhdWx0OiB0cnVlLFxuICAgIH0pO1xuXG4gICAgLy8gSUFNIFJvbGUgZm9yIEVLUyBDbHVzdGVyXG4gICAgY29uc3QgY2x1c3RlclJvbGUgPSBuZXcgaWFtLlJvbGUodGhpcywgJ0Vrc0NsdXN0ZXJSb2xlJywge1xuICAgICAgYXNzdW1lZEJ5OiBuZXcgaWFtLlNlcnZpY2VQcmluY2lwYWwoJ2Vrcy5hbWF6b25hd3MuY29tJyksXG4gICAgICBtYW5hZ2VkUG9saWNpZXM6IFtcbiAgICAgICAgaWFtLk1hbmFnZWRQb2xpY3kuZnJvbUF3c01hbmFnZWRQb2xpY3lOYW1lKCdBbWF6b25FS1NDbHVzdGVyUG9saWN5JyksXG4gICAgICBdLFxuICAgIH0pO1xuXG4gICAgLy8gSUFNIFJvbGUgZm9yIEVLUyBBdXRvIE1vZGUgY29tcHV0ZVxuICAgIGNvbnN0IGF1dG9Nb2RlUm9sZSA9IG5ldyBpYW0uUm9sZSh0aGlzLCAnRWtzQXV0b01vZGVSb2xlJywge1xuICAgICAgYXNzdW1lZEJ5OiBuZXcgaWFtLlNlcnZpY2VQcmluY2lwYWwoJ2VjMi5hbWF6b25hd3MuY29tJyksXG4gICAgICBtYW5hZ2VkUG9saWNpZXM6IFtcbiAgICAgICAgaWFtLk1hbmFnZWRQb2xpY3kuZnJvbUF3c01hbmFnZWRQb2xpY3lOYW1lKCdBbWF6b25FS1NXb3JrZXJOb2RlUG9saWN5JyksXG4gICAgICAgIGlhbS5NYW5hZ2VkUG9saWN5LmZyb21Bd3NNYW5hZ2VkUG9saWN5TmFtZSgnQW1hem9uRUtTX0NOSV9Qb2xpY3knKSxcbiAgICAgICAgaWFtLk1hbmFnZWRQb2xpY3kuZnJvbUF3c01hbmFnZWRQb2xpY3lOYW1lKCdBbWF6b25FQzJDb250YWluZXJSZWdpc3RyeVJlYWRPbmx5JyksXG4gICAgICAgIGlhbS5NYW5hZ2VkUG9saWN5LmZyb21Bd3NNYW5hZ2VkUG9saWN5TmFtZSgnQW1hem9uU1NNTWFuYWdlZEluc3RhbmNlQ29yZScpLFxuICAgICAgXSxcbiAgICB9KTtcblxuICAgIC8vIEVLUyBDbHVzdGVyIHdpdGggQXV0byBNb2RlIC0gSzhzIDEuMzAgKGF1dGggbW9kZSBkZWZhdWx0cyB0byBBUEkgZm9yIG5ldyBjbHVzdGVycylcbiAgICBjb25zdCBjbHVzdGVyID0gbmV3IGVrcy5DbHVzdGVyKHRoaXMsICdCbG9nRWtzQ2x1c3RlcicsIHtcbiAgICAgIGNsdXN0ZXJOYW1lOiAnYmxvZy1la3MtYXV0by1jbHVzdGVyJyxcbiAgICAgIHZlcnNpb246IGVrcy5LdWJlcm5ldGVzVmVyc2lvbi5WMV8zMCxcbiAgICAgIHZwYyxcbiAgICAgIHZwY1N1Ym5ldHM6IFt7IHN1Ym5ldFR5cGU6IGVjMi5TdWJuZXRUeXBlLlBVQkxJQyB9XSxcbiAgICAgIHJvbGU6IGNsdXN0ZXJSb2xlLFxuICAgICAgZGVmYXVsdENhcGFjaXR5OiAwLFxuICAgIH0pO1xuXG4gICAgLy8gRW5hYmxlIEF1dG8gTW9kZSB2aWEgQ2ZuQ2x1c3RlclxuICAgIGNvbnN0IGNmbkNsdXN0ZXIgPSBjbHVzdGVyLm5vZGUuZGVmYXVsdENoaWxkIGFzIGVrcy5DZm5DbHVzdGVyO1xuICAgIChjZm5DbHVzdGVyIGFzIGFueSkuY29tcHV0ZUNvbmZpZyA9IHtcbiAgICAgIGVuYWJsZWQ6IHRydWUsXG4gICAgICBub2RlUm9sZUFybjogYXV0b01vZGVSb2xlLnJvbGVBcm4sXG4gICAgfTtcblxuICAgIC8vIE91dHB1dHNcbiAgICBuZXcgY2RrLkNmbk91dHB1dCh0aGlzLCAnQ2x1c3Rlck5hbWUnLCB7XG4gICAgICB2YWx1ZTogY2x1c3Rlci5jbHVzdGVyTmFtZSxcbiAgICB9KTtcblxuICAgIG5ldyBjZGsuQ2ZuT3V0cHV0KHRoaXMsICdDbHVzdGVyQXJuJywge1xuICAgICAgdmFsdWU6IGNsdXN0ZXIuY2x1c3RlckFybixcbiAgICB9KTtcblxuICAgIG5ldyBjZGsuQ2ZuT3V0cHV0KHRoaXMsICdDb25maWdDb21tYW5kJywge1xuICAgICAgdmFsdWU6IGBhd3MgZWtzIHVwZGF0ZS1rdWJlY29uZmlnIC0tbmFtZSAke2NsdXN0ZXIuY2x1c3Rlck5hbWV9IC0tcmVnaW9uICR7dGhpcy5yZWdpb259YCxcbiAgICB9KTtcbiAgfVxufVxuIl19