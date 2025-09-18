# Arctic Shadow Tracker - Production Deployment Guide

This guide provides comprehensive instructions for deploying Arctic Shadow Tracker in a production environment with automated scheduling, monitoring, and alerting capabilities.

## Quick Start

For immediate deployment on Ubuntu/Debian systems:

```bash
# Clone the repository
git clone https://github.com/henrfo/ArcticShadowTracker.git
cd ArcticShadowTracker

# Run automated production setup (requires sudo)
sudo ./infrastructure/deploy/production-setup.sh
```

This will set up the complete production environment with systemd services, cron jobs, monitoring, and alerting.

## Deployment Options

### Option 1: Native Linux Deployment (Recommended)

**Requirements:**
- Ubuntu 20.04+ or Debian 11+
- 4GB+ RAM
- 20GB+ storage
- Root/sudo access

**Steps:**

1. **Automated Setup:**
   ```bash
   sudo ./infrastructure/deploy/production-setup.sh
   ```

2. **Configure Environment:**
   ```bash
   sudo nano /app/config/.env
   # Edit with your API keys and alert settings
   ```

3. **Start Services:**
   ```bash
   sudo systemctl start arctic-shadow-tracker
   sudo systemctl start arctic-data-collector
   ```

### Option 2: Docker Deployment

**Requirements:**
- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ RAM
- 20GB+ storage

**Steps:**

1. **Configure Environment:**
   ```bash
   cp infrastructure/deploy/.env.example .env
   # Edit .env with your settings
   ```

2. **Deploy with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

3. **Verify Deployment:**
   ```bash
   docker-compose ps
   docker-compose logs arctic-tracker
   ```

### Option 3: Kubernetes Deployment

**Requirements:**
- Kubernetes 1.20+
- kubectl configured
- 8GB+ RAM cluster
- Persistent storage

**Steps:**

1. **Apply Kubernetes Manifests:**
   ```bash
   kubectl apply -f infrastructure/k8s/
   ```

2. **Configure Secrets:**
   ```bash
   kubectl create secret generic arctic-secrets \
     --from-literal=copernicus-username="your_username" \
     --from-literal=copernicus-password="your_password"
   ```

## Configuration

### Essential Configuration

1. **API Credentials** (Required for live data):
   ```bash
   # Copernicus/Sentinel Hub (for satellite data)
   COPERNICUS_USERNAME=your_username
   COPERNICUS_PASSWORD=your_password
   
   # Optional: AIS API key for enhanced vessel data
   AIS_API_KEY=your_ais_key
   ```

2. **Alert Configuration** (Recommended):
   ```bash
   # Email alerts
   EMAIL_ALERTS_ENABLED=true
   SMTP_SERVER=smtp.gmail.com
   SMTP_USERNAME=your_email@gmail.com
   SMTP_PASSWORD=your_app_password
   EMAIL_TO=admin@your-domain.com
   
   # Slack alerts (optional)
   SLACK_ALERTS_ENABLED=true
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK
   ```

### Alert System Configuration

The system supports multiple alert channels:

#### Email Alerts
- **Critical threats:** Immediate email notification
- **System issues:** Health alerts for service failures
- **Daily summaries:** Automated surveillance reports

#### Webhook Alerts
- **Integration:** Works with most webhook-compatible systems
- **Format:** JSON payload with threat details
- **Security:** Token-based authentication

#### Slack Integration
- **Channels:** Configurable Slack channels
- **Formatting:** Rich message formatting with colors
- **Filtering:** Configurable alert levels

### Monitoring Configuration

#### Prometheus Metrics
Available at `http://localhost:9090/metrics`:

- `arctic_threats_total` - Total threats detected
- `arctic_threats_critical_total` - Current critical threats
- `arctic_ais_vessels_current` - Current AIS vessel count
- `arctic_system_health_score` - System health (0-100)

#### Grafana Dashboards
Access at `http://localhost:3000`:
- **Arctic Overview:** Real-time surveillance status
- **Threat Analysis:** Historical threat patterns
- **System Health:** Performance and availability metrics

## Operational Procedures

### Daily Operations

The system runs automatically with the following schedule:

```
06:00, 12:00, 18:00, 00:00 UTC - Full surveillance runs
Every 6 hours (offset +30min) - Satellite data download
Every 15 minutes - System health checks
Daily 02:00 - Log cleanup
Daily 04:00 - Data backup
Daily 07:30 - Alert system test
```

### Manual Operations

**Run immediate surveillance:**
```bash
sudo -u arctic python3 -m utils.daily_operations
```

**Check system health:**
```bash
sudo -u arctic python3 /app/infrastructure/deploy/health_monitor.py
```

**Test alert system:**
```bash
sudo -u arctic python3 /app/infrastructure/deploy/alert_system.py --test
```

**View real-time logs:**
```bash
journalctl -u arctic-shadow-tracker -f
```

### Backup and Recovery

**Automated Backups:**
- Daily backups at 04:00 UTC
- 7-day retention period
- Stored in `/app/backups/`

**Manual Backup:**
```bash
sudo -u arctic python3 /app/infrastructure/deploy/backup_manager.py
```

**Recovery:**
```bash
# Extract backup
tar -xzf /app/backups/arctic_backup_YYYYMMDD_HHMMSS.tar.gz

# Restore data
cp -r operational/ /app/data/
cp -r config/ /app/
```

## Security Considerations

### Network Security
- **Firewall:** UFW configured with minimal open ports
- **Access:** SSH access only, web interfaces on localhost
- **API Security:** Token-based authentication for webhooks

### Data Security
- **Encryption:** Environment variables for sensitive data
- **Permissions:** Restricted file permissions (arctic user)
- **Logs:** Sensitive data excluded from logs

### Maritime Security Compliance
- **Data Handling:** Complies with international maritime law
- **Privacy:** No personal data collection
- **Transparency:** Open-source methodology

## Performance Optimization

### System Requirements

**Minimum:**
- 2 CPU cores
- 4GB RAM
- 20GB storage

**Recommended:**
- 4 CPU cores
- 8GB RAM
- 50GB SSD storage

### Performance Tuning

**Memory Optimization:**
```bash
# Adjust in .env
WORKER_MEMORY_LIMIT=2G
PROCESSING_BATCH_SIZE=100
```

**Processing Optimization:**
```bash
# Parallel processing
MAX_WORKER_PROCESSES=4
DATA_REFRESH_INTERVAL=1800
```

### Scaling Considerations

**Horizontal Scaling:**
- Multiple Arctic regions: Deploy separate instances
- Load balancing: Use nginx for API load balancing
- Data distribution: Shared storage for multi-instance deployment

**Vertical Scaling:**
- CPU: Increase for faster SAR processing
- Memory: Increase for larger datasets
- Storage: SSD recommended for optimal I/O

## Troubleshooting

### Common Issues

**Service Won't Start:**
```bash
# Check service status
systemctl status arctic-shadow-tracker

# Check logs
journalctl -u arctic-shadow-tracker --since "1 hour ago"

# Check dependencies
python3 -c "import sys; sys.path.append('/app'); from utils.daily_operations import DailyOperations"
```

**No Data Collection:**
```bash
# Check API credentials
sudo -u arctic python3 -c "import os; print('Copernicus user:', os.getenv('COPERNICUS_USERNAME'))"

# Test AIS connection
curl "http://data.aishub.net/ws.php?username=DH_DEMO&format=1&output=json&compress=0&latmin=69&latmax=82&lonmin=5&lonmax=35"

# Check file permissions
ls -la /app/data/
```

**Alerts Not Sending:**
```bash
# Test email configuration
sudo -u arctic python3 /app/infrastructure/deploy/alert_system.py --test

# Check SMTP settings
telnet smtp.gmail.com 587

# Verify webhook endpoint
curl -X POST your-webhook-url -H "Content-Type: application/json" -d '{"test": "message"}'
```

### Log Analysis

**Important Log Files:**
- `/app/logs/daily_surveillance_*.log` - Main operations
- `/var/log/arctic-tracker/` - System logs
- `journalctl -u arctic-shadow-tracker` - Service logs

**Common Log Patterns:**
```bash
# Search for errors
grep -r "ERROR" /app/logs/

# Search for critical threats
grep -r "CRITICAL" /app/logs/

# Check performance metrics
grep -r "duration" /app/logs/
```

## Monitoring and Alerting

### Health Monitoring

**System Health Checks:**
- Memory usage < 80%
- CPU usage < 85%
- Disk usage < 85%
- Data freshness < 6 hours
- Service availability

**Alert Thresholds:**
- **CRITICAL:** System failure, dark vessel near cable
- **WARNING:** High resource usage, stale data
- **INFO:** Daily summaries, routine operations

### Metrics Collection

**Prometheus Integration:**
```bash
# View metrics
curl http://localhost:9090/metrics | grep arctic

# Custom queries
curl 'http://localhost:9090/api/v1/query?query=arctic_threats_total'
```

**Grafana Dashboards:**
- Import dashboard configurations from `/infrastructure/deploy/`
- Configure data sources for Prometheus
- Set up alert rules for automated notifications

## Updates and Maintenance

### Software Updates

**System Updates:**
```bash
# Update system packages
sudo apt update && sudo apt upgrade

# Restart services
sudo systemctl restart arctic-shadow-tracker
```

**Application Updates:**
```bash
# Pull latest code
git pull origin main

# Update dependencies
pip install -r config/requirements.txt

# Restart services
sudo systemctl restart arctic-shadow-tracker
```

### Maintenance Tasks

**Weekly:**
- Review system logs
- Check backup integrity
- Verify alert system functionality
- Monitor resource usage trends

**Monthly:**
- Update system packages
- Review and update API credentials
- Analyze surveillance coverage and effectiveness
- Update threat detection parameters

### Capacity Planning

**Data Growth:**
- Daily operational data: ~10-50MB/day
- Logs: ~5-20MB/day
- Backups: ~100-500MB/week

**Storage Management:**
```bash
# Check disk usage
df -h /app/

# Clean old logs
find /app/logs/ -name "*.log" -mtime +30 -delete

# Archive old operational data
tar -czf archive_$(date +%Y%m).tar.gz /app/data/operational/daily/$(date -d "last month" +%Y-%m)-*
```

## Support and Documentation

### Additional Resources
- **GitHub Repository:** https://github.com/henrfo/ArcticShadowTracker
- **Architecture Documentation:** `/docs/architecture/`
- **API Reference:** `/docs/architecture/API_REFERENCE.md`

### Support Channels
- **Issues:** GitHub Issues for bug reports
- **Documentation:** Comprehensive guides in `/docs/`
- **Code Examples:** Jupyter notebooks in `/notebooks/`

### Contributing
- **Development Guide:** `/docs/architecture/DEVELOPMENT_GUIDE.md`
- **Testing Guide:** `/docs/architecture/TESTING_GUIDE.md`
- **Code Quality:** Automated testing and quality checks

---

**Arctic Shadow Tracker Production Deployment Guide**  
*Version 1.0 - Production Ready*  
*Comprehensive Maritime Surveillance System for Arctic Waters*