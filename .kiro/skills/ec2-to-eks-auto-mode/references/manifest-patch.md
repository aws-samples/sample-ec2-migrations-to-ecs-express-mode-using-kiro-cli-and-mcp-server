# Kubernetes Manifest Patch Reference

After generating the base manifest with `generate_app_manifest`, apply these additions.

## Required Additions to Deployment spec.template.spec

```yaml
spec:
  template:
    spec:
      serviceAccountName: <APP_NAME>-sa
      containers:
      - name: <APP_NAME>
        env:
        - name: AWS_REGION
          value: "<REGION>"
        - name: DYNAMODB_TABLE
          value: "<TABLE_NAME>"
        - name: S3_BUCKET
          value: "<BUCKET_NAME>"
        - name: PORT
          value: "<PORT>"
        livenessProbe:
          httpGet:
            path: /health
            port: <PORT>
          initialDelaySeconds: 10
          periodSeconds: 30
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: <PORT>
          initialDelaySeconds: 5
          periodSeconds: 10
          failureThreshold: 3
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
```

## Why Each Field Matters

| Field | Purpose |
|-------|---------|
| serviceAccountName | Links pod to IAM role via Pod Identity |
| livenessProbe | Restarts container if app becomes unresponsive |
| readinessProbe | Removes pod from LB if not ready to serve |
| resources.requests | Tells Auto Mode how much capacity to provision |
| resources.limits | Prevents runaway resource consumption |

## Notes

- `initialDelaySeconds` on liveness must be > app startup time
- Resource requests drive Auto Mode node sizing — set realistically
- Without resource requests, Auto Mode cannot right-size nodes
