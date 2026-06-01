# Kubernetes Manifest Patch Reference

After generating the base manifest with `generate_app_manifest`, apply these additions.

## Required Additions

```yaml
spec:
  template:
    spec:
      serviceAccountName: <APP_NAME>-sa
      containers:
      - name: <APP_NAME>
        env:
        - name: <ENV_VAR_NAME>
          value: "<ENV_VAR_VALUE>"
        # Add all env vars the app needs
        livenessProbe:
          httpGet:
            path: /<HEALTH_PATH>
            port: <PORT>
          initialDelaySeconds: <SEE_TABLE_BELOW>
          periodSeconds: 30
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /<HEALTH_PATH>
            port: <PORT>
          initialDelaySeconds: 5
          periodSeconds: 10
          failureThreshold: 3
        resources:
          requests:
            cpu: "<CPU_REQUEST>"
            memory: "<MEM_REQUEST>"
          limits:
            cpu: "<CPU_LIMIT>"
            memory: "<MEM_LIMIT>"
```

## Recommended Resource Settings by Runtime

| Runtime | CPU Request | Memory Request | CPU Limit | Memory Limit | Liveness Delay |
|---------|-------------|----------------|-----------|--------------|----------------|
| Node.js | 100m | 128Mi | 500m | 512Mi | 10s |
| Python | 100m | 128Mi | 500m | 512Mi | 10s |
| Go | 50m | 64Mi | 250m | 256Mi | 5s |
| Java | 250m | 512Mi | 1000m | 1Gi | 30-60s |
| .NET | 200m | 256Mi | 500m | 512Mi | 20-30s |

## Why Each Field Matters

| Field | Purpose |
|-------|---------|
| serviceAccountName | Links pod to IAM role via Pod Identity |
| livenessProbe | Restarts container if app becomes unresponsive |
| readinessProbe | Removes pod from LB if not ready to serve |
| resources.requests | Tells Auto Mode how much capacity to provision |
| resources.limits | Prevents runaway resource consumption |

## Notes

- `initialDelaySeconds` on liveness MUST exceed app startup time or pods will restart in a loop
- Resource requests drive Auto Mode node sizing — set realistically based on runtime
- Without resource requests, Auto Mode cannot right-size nodes
- Java/Spring Boot apps need higher memory due to JVM overhead
- Go apps can use very low resources due to small binary + fast startup
