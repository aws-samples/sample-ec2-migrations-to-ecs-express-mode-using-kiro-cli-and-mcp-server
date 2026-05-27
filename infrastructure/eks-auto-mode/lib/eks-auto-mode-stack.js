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
const eks = __importStar(require("aws-cdk-lib/aws-eks-v2"));
const ec2 = __importStar(require("aws-cdk-lib/aws-ec2"));
class EksAutoModeStack extends cdk.Stack {
    constructor(scope, id, props) {
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
exports.EksAutoModeStack = EksAutoModeStack;
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiZWtzLWF1dG8tbW9kZS1zdGFjay5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbImVrcy1hdXRvLW1vZGUtc3RhY2sudHMiXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6Ijs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7QUFBQSxpREFBbUM7QUFDbkMsNERBQThDO0FBQzlDLHlEQUEyQztBQUkzQyxNQUFhLGdCQUFpQixTQUFRLEdBQUcsQ0FBQyxLQUFLO0lBQzdDLFlBQVksS0FBZ0IsRUFBRSxFQUFVLEVBQUUsS0FBc0I7UUFDOUQsS0FBSyxDQUFDLEtBQUssRUFBRSxFQUFFLEVBQUUsS0FBSyxDQUFDLENBQUM7UUFFeEIsTUFBTSxHQUFHLEdBQUcsR0FBRyxDQUFDLEdBQUcsQ0FBQyxVQUFVLENBQUMsSUFBSSxFQUFFLFlBQVksRUFBRSxFQUFFLFNBQVMsRUFBRSxJQUFJLEVBQUUsQ0FBQyxDQUFDO1FBRXhFLGtFQUFrRTtRQUNsRSxNQUFNLE9BQU8sR0FBRyxJQUFJLEdBQUcsQ0FBQyxPQUFPLENBQUMsSUFBSSxFQUFFLGdCQUFnQixFQUFFO1lBQ3RELFdBQVcsRUFBRSx1QkFBdUI7WUFDcEMsT0FBTyxFQUFFLEdBQUcsQ0FBQyxpQkFBaUIsQ0FBQyxLQUFLO1lBQ3BDLEdBQUc7WUFDSCxVQUFVLEVBQUUsQ0FBQyxFQUFFLFVBQVUsRUFBRSxHQUFHLENBQUMsVUFBVSxDQUFDLE1BQU0sRUFBRSxDQUFDO1lBQ25ELDZEQUE2RDtZQUM3RCxtQkFBbUIsRUFBRSxHQUFHLENBQUMsbUJBQW1CLENBQUMsUUFBUTtTQUN0RCxDQUFDLENBQUM7UUFFSCxJQUFJLEdBQUcsQ0FBQyxTQUFTLENBQUMsSUFBSSxFQUFFLGFBQWEsRUFBRSxFQUFFLEtBQUssRUFBRSxPQUFPLENBQUMsV0FBVyxFQUFFLENBQUMsQ0FBQztRQUN2RSxJQUFJLEdBQUcsQ0FBQyxTQUFTLENBQUMsSUFBSSxFQUFFLFlBQVksRUFBRSxFQUFFLEtBQUssRUFBRSxPQUFPLENBQUMsVUFBVSxFQUFFLENBQUMsQ0FBQztRQUNyRSxJQUFJLEdBQUcsQ0FBQyxTQUFTLENBQUMsSUFBSSxFQUFFLGVBQWUsRUFBRTtZQUN2QyxLQUFLLEVBQUUsb0NBQW9DLE9BQU8sQ0FBQyxXQUFXLGFBQWEsSUFBSSxDQUFDLE1BQU0sRUFBRTtTQUN6RixDQUFDLENBQUM7SUFDTCxDQUFDO0NBQ0Y7QUF0QkQsNENBc0JDIiwic291cmNlc0NvbnRlbnQiOlsiaW1wb3J0ICogYXMgY2RrIGZyb20gJ2F3cy1jZGstbGliJztcbmltcG9ydCAqIGFzIGVrcyBmcm9tICdhd3MtY2RrLWxpYi9hd3MtZWtzLXYyJztcbmltcG9ydCAqIGFzIGVjMiBmcm9tICdhd3MtY2RrLWxpYi9hd3MtZWMyJztcbmltcG9ydCAqIGFzIGlhbSBmcm9tICdhd3MtY2RrLWxpYi9hd3MtaWFtJztcbmltcG9ydCB7IENvbnN0cnVjdCB9IGZyb20gJ2NvbnN0cnVjdHMnO1xuXG5leHBvcnQgY2xhc3MgRWtzQXV0b01vZGVTdGFjayBleHRlbmRzIGNkay5TdGFjayB7XG4gIGNvbnN0cnVjdG9yKHNjb3BlOiBDb25zdHJ1Y3QsIGlkOiBzdHJpbmcsIHByb3BzPzogY2RrLlN0YWNrUHJvcHMpIHtcbiAgICBzdXBlcihzY29wZSwgaWQsIHByb3BzKTtcblxuICAgIGNvbnN0IHZwYyA9IGVjMi5WcGMuZnJvbUxvb2t1cCh0aGlzLCAnRGVmYXVsdFZwYycsIHsgaXNEZWZhdWx0OiB0cnVlIH0pO1xuXG4gICAgLy8gRUtTIEF1dG8gTW9kZSBjbHVzdGVyIC0gYXdzLWVrcy12MiBlbmFibGVzIEF1dG8gTW9kZSBieSBkZWZhdWx0XG4gICAgY29uc3QgY2x1c3RlciA9IG5ldyBla3MuQ2x1c3Rlcih0aGlzLCAnQmxvZ0Vrc0NsdXN0ZXInLCB7XG4gICAgICBjbHVzdGVyTmFtZTogJ2Jsb2ctZWtzLWF1dG8tY2x1c3RlcicsXG4gICAgICB2ZXJzaW9uOiBla3MuS3ViZXJuZXRlc1ZlcnNpb24uVjFfMzQsXG4gICAgICB2cGMsXG4gICAgICB2cGNTdWJuZXRzOiBbeyBzdWJuZXRUeXBlOiBlYzIuU3VibmV0VHlwZS5QVUJMSUMgfV0sXG4gICAgICAvLyBBdXRvIE1vZGUgaXMgdGhlIGRlZmF1bHQgLSBubyBDZm5DbHVzdGVyIHdvcmthcm91bmQgbmVlZGVkXG4gICAgICBkZWZhdWx0Q2FwYWNpdHlUeXBlOiBla3MuRGVmYXVsdENhcGFjaXR5VHlwZS5BVVRPTU9ERSxcbiAgICB9KTtcblxuICAgIG5ldyBjZGsuQ2ZuT3V0cHV0KHRoaXMsICdDbHVzdGVyTmFtZScsIHsgdmFsdWU6IGNsdXN0ZXIuY2x1c3Rlck5hbWUgfSk7XG4gICAgbmV3IGNkay5DZm5PdXRwdXQodGhpcywgJ0NsdXN0ZXJBcm4nLCB7IHZhbHVlOiBjbHVzdGVyLmNsdXN0ZXJBcm4gfSk7XG4gICAgbmV3IGNkay5DZm5PdXRwdXQodGhpcywgJ0NvbmZpZ0NvbW1hbmQnLCB7XG4gICAgICB2YWx1ZTogYGF3cyBla3MgdXBkYXRlLWt1YmVjb25maWcgLS1uYW1lICR7Y2x1c3Rlci5jbHVzdGVyTmFtZX0gLS1yZWdpb24gJHt0aGlzLnJlZ2lvbn1gLFxuICAgIH0pO1xuICB9XG59XG4iXX0=