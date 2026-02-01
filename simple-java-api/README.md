# Simple Java REST API

A minimal Spring Boot REST API application with health check endpoints for Amazon ECS/EKS deployments.

## Endpoints

### Root Endpoints (for health checks)
- `GET /` - Service status and version info
- `GET /health` - Health check endpoint (returns {"status": "UP"})

### API Endpoints
- `GET /api/hello` - Returns a hello message
- `GET /api/health` - API health check endpoint
- `POST /api/echo` - Echoes back the JSON payload

## Configuration

The application runs on port 8080 by default, but can be configured via the `PORT` environment variable:
- Default: 8080
- Environment variable: `PORT=8080`

## Run Locally

```bash
mvn spring-boot:run
```

## Build and Run with Docker

```bash
docker build -t simple-java-api .
docker run -p 8080:8080 simple-java-api
```

## Test

```bash
# Health checks
curl http://localhost:8080/
curl http://localhost:8080/health

# API endpoints
curl http://localhost:8080/api/hello
curl http://localhost:8080/api/health
curl -X POST http://localhost:8080/api/echo -H "Content-Type: application/json" -d '{"test": "data"}'
```

## Deployment Notes

- **Port**: Runs on port 8080 (configurable via PORT env var)
- **Health Check**: Use `/` or `/health` for load balancer health checks
- **Resources**: Recommended minimum 1 vCPU (1024) and 2GB RAM (2048) for Amazon ECS/EKS
