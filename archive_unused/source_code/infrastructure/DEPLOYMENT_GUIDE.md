# Arctic Shadow Tracker - Production Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Arctic Shadow Tracker maritime surveillance system in a production environment with high availability, security, and operational excellence.

## Prerequisites

### Infrastructure Requirements

#### Minimum Hardware Specifications
- **Kubernetes Cluster**: 3+ nodes with 16 vCPUs, 32GB RAM each
- **Storage**: 1TB+ fast SSD storage with backup capabilities
- **Network**: High-bandwidth internet for satellite data downloads
- **GPU (Optional)**: For accelerated ML inference (NVIDIA T4 or better)

#### Software Dependencies
- Kubernetes 1.25+
- Docker 20.10+
- Helm 3.8+
- kubectl 1.25+
- Redis 7.0+
- PostgreSQL 14+ with PostGIS extension

### Security Requirements
- Valid TLS certificates for all endpoints
- Network segmentation and firewall rules
- API keys for Copernicus and AIS data sources
- Encryption at rest for sensitive data
- Regular security updates and vulnerability scanning

## Deployment Steps

### 1. Cluster Preparation

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Apply RBAC and security policies
kubectl apply -f k8s/rbac.yaml

# Create secrets (update with real values)
kubectl apply -f k8s/secret.yaml

# Create configuration
kubectl apply -f k8s/configmap.yaml
```

### 2. Storage Setup

```bash
# Create persistent volumes
kubectl apply -f k8s/pvc.yaml

# Verify storage classes exist
kubectl get storageclass
```

### 3. Database Deployment

```bash
# Deploy PostgreSQL with PostGIS
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install postgres bitnami/postgresql \
  --namespace arctic-surveillance \
  --set auth.postgresPassword=<secure_password> \
  --set auth.database=arctic_surveillance \
  --set primary.persistence.size=200Gi \
  --set primary.resources.requests.memory=4Gi \
  --set primary.resources.requests.cpu=2 \
  --set metrics.enabled=true

# Deploy Redis
helm install redis bitnami/redis \
  --namespace arctic-surveillance \
  --set auth.enabled=false \
  --set replica.replicaCount=1 \
  --set master.persistence.size=50Gi \
  --set metrics.enabled=true
```

### 4. Application Deployment

```bash
# Build and push container image
docker build -t arctic-tracker:latest .
docker tag arctic-tracker:latest your-registry/arctic-tracker:v1.0.0
docker push your-registry/arctic-tracker:v1.0.0

# Update deployment image reference
sed -i 's|arctic-tracker:latest|your-registry/arctic-tracker:v1.0.0|g' k8s/deployment.yaml

# Deploy application
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Wait for deployment to be ready
kubectl rollout status deployment/arctic-tracker-deployment -n arctic-surveillance
```

### 5. Monitoring Setup

```bash
# Deploy Prometheus and Grafana
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts

# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace arctic-surveillance \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
  --set grafana.adminPassword=<secure_password>

# Apply custom alerting rules
kubectl apply -f deploy/alert_rules.yml
```

### 6. Backup Configuration

```bash
# Deploy backup jobs
kubectl apply -f deploy/backup-cronjob.yaml

# Test backup manually
kubectl create job --from=cronjob/arctic-tracker-backup test-backup -n arctic-surveillance
```

## Configuration Management

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `COPERNICUS_USERNAME` | Copernicus Data Space username | Yes | - |
| `COPERNICUS_PASSWORD` | Copernicus Data Space password | Yes | - |
| `AIS_API_KEY` | AIS data provider API key | Yes | - |
| `POSTGRES_PASSWORD` | Database password | Yes | - |
| `REDIS_HOST` | Redis server hostname | No | `redis-service` |
| `LOG_LEVEL` | Logging level | No | `INFO` |
| `DATA_REFRESH_INTERVAL` | Data update interval (seconds) | No | `1800` |

### API Rate Limits

Configure rate limits based on your API subscription:

```yaml
# In configmap.yaml
COPERNICUS_RATE_LIMIT: "60"  # requests per minute
AIS_RATE_LIMIT: "100"        # requests per minute
WEATHER_RATE_LIMIT: "200"    # requests per minute
```

## Operational Procedures

### Daily Operations

1. **Health Check**
   ```bash
   kubectl get pods -n arctic-surveillance
   kubectl logs -f deployment/arctic-tracker-deployment -n arctic-surveillance
   ```

2. **Data Verification**
   ```bash
   # Check latest AIS data
   kubectl exec -it deployment/arctic-tracker-deployment -n arctic-surveillance -- \
     ls -la /app/data/ais/

   # Verify satellite data downloads
   kubectl exec -it deployment/arctic-tracker-deployment -n arctic-surveillance -- \
     ls -la /app/data/satellite/
   ```

3. **Alert Review**
   ```bash
   # Check for threat alerts
   kubectl exec -it deployment/arctic-tracker-deployment -n arctic-surveillance -- \
     find /app/outputs/alerts/ -name "*.json" -mtime -1
   ```

### Weekly Maintenance

1. **Update Container Images**
   ```bash
   # Pull latest security updates
   docker pull your-registry/arctic-tracker:latest
   kubectl set image deployment/arctic-tracker-deployment \
     arctic-tracker=your-registry/arctic-tracker:latest \
     -n arctic-surveillance
   ```

2. **Backup Verification**
   ```bash
   # Verify backups are running
   kubectl get jobs -n arctic-surveillance | grep backup
   
   # Check backup logs
   kubectl logs job/arctic-tracker-backup-<timestamp> -n arctic-surveillance
   ```

3. **Performance Review**
   - Review Grafana dashboards for performance metrics
   - Check Prometheus alerts for any issues
   - Analyze API rate limit usage

### Emergency Procedures

#### System Outage Recovery

1. **Check Pod Status**
   ```bash
   kubectl get pods -n arctic-surveillance
   kubectl describe pod <failing-pod> -n arctic-surveillance
   ```

2. **Restart Services**
   ```bash
   kubectl rollout restart deployment/arctic-tracker-deployment -n arctic-surveillance
   kubectl rollout restart deployment/sentinel-downloader-deployment -n arctic-surveillance
   ```

3. **Database Recovery**
   ```bash
   # If database is corrupted, restore from backup
   kubectl scale deployment postgres --replicas=0 -n arctic-surveillance
   # Restore data from S3 backup
   kubectl scale deployment postgres --replicas=1 -n arctic-surveillance
   ```

#### Data Loss Recovery

1. **Identify Missing Data**
   ```bash
   # Check data directories
   kubectl exec -it deployment/arctic-tracker-deployment -n arctic-surveillance -- \
     ls -la /app/data/
   ```

2. **Restore from Backup**
   ```bash
   # Download backup from S3
   aws s3 cp s3://arctic-surveillance-backups/data/latest.tar.gz /tmp/
   
   # Extract to pod
   kubectl cp /tmp/latest.tar.gz arctic-tracker-pod:/tmp/
   kubectl exec -it arctic-tracker-pod -- tar -xzf /tmp/latest.tar.gz -C /app/
   ```

## Security Hardening

### Network Security

1. **Configure Network Policies**
   ```bash
   kubectl apply -f k8s/network-policy.yaml
   ```

2. **Enable Pod Security Standards**
   ```bash
   kubectl label namespace arctic-surveillance \
     pod-security.kubernetes.io/enforce=restricted \
     pod-security.kubernetes.io/audit=restricted \
     pod-security.kubernetes.io/warn=restricted
   ```

### Access Control

1. **Implement RBAC**
   ```bash
   kubectl apply -f k8s/rbac.yaml
   ```

2. **Configure Service Accounts**
   ```bash
   # Ensure pods run with minimal privileges
   kubectl patch deployment arctic-tracker-deployment \
     -p '{"spec":{"template":{"spec":{"serviceAccount":"arctic-tracker-sa"}}}}' \
     -n arctic-surveillance
   ```

### Data Protection

1. **Enable Encryption at Rest**
   ```bash
   # Configure storage encryption
   kubectl patch storageclass fast-ssd \
     -p '{"parameters":{"encrypted":"true"}}'
   ```

2. **Secure Secret Management**
   ```bash
   # Use external secret management (e.g., AWS Secrets Manager)
   helm repo add external-secrets https://charts.external-secrets.io
   helm install external-secrets external-secrets/external-secrets \
     --namespace external-secrets-system \
     --create-namespace
   ```

## Scaling Strategies

### Horizontal Scaling

```bash
# Scale based on load
kubectl scale deployment arctic-tracker-deployment --replicas=3 -n arctic-surveillance

# Configure Horizontal Pod Autoscaler
kubectl autoscale deployment arctic-tracker-deployment \
  --cpu-percent=70 \
  --min=2 \
  --max=5 \
  -n arctic-surveillance
```

### Vertical Scaling

```yaml
# Update resource requests/limits
resources:
  requests:
    memory: "4Gi"
    cpu: "1000m"
  limits:
    memory: "8Gi"
    cpu: "4000m"
```

### Geographic Distribution

For expanded coverage areas:

1. **Multi-Region Deployment**
   - Deploy separate clusters in different regions
   - Configure data replication between regions
   - Implement region-specific monitoring

2. **Edge Computing**
   - Deploy lightweight processing nodes near data sources
   - Use edge-to-cloud data synchronization
   - Implement local alerting for critical threats

## Troubleshooting Guide

### Common Issues

1. **High Memory Usage**
   ```bash
   # Check memory usage
   kubectl top pods -n arctic-surveillance
   
   # Scale up resources
   kubectl patch deployment arctic-tracker-deployment \
     -p '{"spec":{"template":{"spec":{"containers":[{"name":"arctic-tracker","resources":{"limits":{"memory":"8Gi"}}}]}}}}' \
     -n arctic-surveillance
   ```

2. **API Rate Limit Exceeded**
   ```bash
   # Check rate limit status
   kubectl logs deployment/arctic-tracker-deployment -n arctic-surveillance | grep "rate limit"
   
   # Adjust rate limits in configuration
   kubectl patch configmap arctic-tracker-config \
     -p '{"data":{"AIS_RATE_LIMIT":"50"}}' \
     -n arctic-surveillance
   ```

3. **Satellite Data Download Failures**
   ```bash
   # Check Copernicus credentials
   kubectl get secret arctic-tracker-secrets -o yaml -n arctic-surveillance
   
   # Test connectivity
   kubectl exec -it deployment/arctic-tracker-deployment -n arctic-surveillance -- \
     curl -v https://catalogue.dataspace.copernicus.eu
   ```

### Log Analysis

```bash
# Application logs
kubectl logs -f deployment/arctic-tracker-deployment -n arctic-surveillance

# System logs
kubectl logs -f deployment/arctic-tracker-deployment -n arctic-surveillance --previous

# Aggregated logs with labels
kubectl logs -l app=arctic-tracker -n arctic-surveillance --tail=100
```

## Performance Optimization

### Database Optimization

```sql
-- Create indexes for frequent queries
CREATE INDEX idx_vessel_timestamp ON vessel_positions(timestamp);
CREATE INDEX idx_vessel_location ON vessel_positions USING GIST(location);
CREATE INDEX idx_threat_level ON threat_alerts(threat_level, created_at);
```

### Storage Optimization

```bash
# Configure storage classes for different workloads
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: kubernetes.io/gce-pd
parameters:
  type: pd-ssd
  replication-type: regional-pd
allowVolumeExpansion: true
EOF
```

### Network Optimization

```yaml
# Configure resource limits for optimal performance
resources:
  requests:
    memory: "2Gi"
    cpu: "500m"
    ephemeral-storage: "10Gi"
  limits:
    memory: "4Gi"
    cpu: "2000m"
    ephemeral-storage: "20Gi"
```

## Contact Information

**Operations Team**: arctic-ops@organization.mil
**Security Team**: arctic-security@organization.mil
**Emergency Hotline**: +1-XXX-XXX-XXXX

**Documentation**: https://docs.arctic-tracker.internal
**Monitoring**: https://grafana.arctic-tracker.internal
**Alerts**: https://alertmanager.arctic-tracker.internal