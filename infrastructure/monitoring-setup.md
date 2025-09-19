# Arctic Shadow Tracker - Monitoring & Alerting

## Overview
Simple but effective monitoring system using GitHub Actions + basic system monitoring tools.

## Monitoring Architecture

### 1. GitHub Actions Monitoring (Primary)
- **Health Checks**: Every 30 minutes via cron schedule
- **Backup Verification**: Daily at 02:00 UTC
- **Deployment Monitoring**: On every deployment
- **Log Analysis**: Automated parsing of application logs

### 2. System-Level Monitoring (On VPS)
- **Service Status**: systemctl monitoring
- **Resource Usage**: CPU, Memory, Disk
- **Log File Monitoring**: Application log growth and content
- **Data Output Verification**: CSV file generation checks

### 3. Application-Level Monitoring
- **API Connectivity**: BarentsWatch API response times
- **Data Collection Success**: Vessel count and quality metrics
- **Processing Performance**: Time per surveillance cycle
- **Error Rate Tracking**: Failed cycles vs successful cycles

## Monitoring Components

### Health Check Script (Deployed on VPS)
Location: `/opt/arctic-shadow-tracker/health_check.py`

Features:
- Service status verification
- Log activity monitoring (last 60 minutes)
- Data output verification
- Resource usage checks
- JSON status output for GitHub Actions consumption

### GitHub Actions Monitoring Workflows

#### 1. Continuous Health Monitoring (`monitor.yml`)
```yaml
# Runs every 30 minutes
- Health status check
- Service restart on failure
- Alert notifications (Discord/Slack)
- Log analysis and reporting
```

#### 2. Daily Backup Monitoring
```yaml
# Runs daily at 02:00 UTC  
- Automated backup creation
- Backup integrity verification
- Old backup cleanup
- Backup status reporting
```

### Alert Thresholds

#### Critical Alerts (Immediate Action Required)
- **Service Down**: Service not running for >5 minutes
- **API Failure**: BarentsWatch API unreachable for >15 minutes
- **Disk Full**: Available space <500MB
- **Memory Critical**: >95% memory usage for >10 minutes

#### Warning Alerts (Investigation Needed)
- **No Data Output**: No new data files for >2 hours
- **High Error Rate**: >10% failed API calls in last hour
- **Resource Usage**: CPU >80% or Memory >85% for >30 minutes
- **Log Growth**: Log file >100MB (indicates potential issues)

#### Info Alerts (Monitoring Only)
- **Daily Summary**: Successful backup completion
- **Performance Report**: Daily statistics summary
- **Deployment Success**: Successful code deployment

## Alert Channels

### 1. GitHub Actions (Primary)
- **Workflow Status**: Failed/successful in GitHub Actions UI
- **Artifact Storage**: Logs and reports stored as workflow artifacts
- **Issue Creation**: Auto-create GitHub issues for critical failures

### 2. External Notifications (Optional)
- **Discord**: Webhook for real-time alerts
- **Slack**: Webhook for team notifications  
- **Email**: GitHub notification emails

### 3. Dashboard Access
- **Real-time Dashboard**: Latest HTML dashboard accessible via simple web server
- **Log Access**: SSH access to VPS for detailed troubleshooting
- **Status Page**: Simple status page showing system health

## Performance Metrics

### System Metrics
```bash
# CPU Usage
top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1"%"}'

# Memory Usage  
free | grep Mem | awk '{printf("%.1f%%", $3/$2 * 100.0)}'

# Disk Usage
df -h /data/arctic | awk 'NR==2 {print $5}'

# Service Uptime
systemctl show arctic-shadow-tracker --property=ActiveEnterTimestamp
```

### Application Metrics
```python
# From application logs and health check
{
  "vessels_collected": 45,
  "cycle_duration_seconds": 12.3,
  "api_response_time_ms": 850,
  "dark_vessels_detected": 2,
  "cable_alerts": 0,
  "last_successful_cycle": "2025-01-15T10:30:00Z"
}
```

## Troubleshooting Runbook

### Service Not Running
```bash
# 1. Check service status
sudo systemctl status arctic-shadow-tracker

# 2. Check recent logs
journalctl -u arctic-shadow-tracker --since "1 hour ago"

# 3. Check application logs
tail -n 100 /data/arctic/streaming.log

# 4. Restart service
sudo systemctl restart arctic-shadow-tracker

# 5. Verify restart
sudo systemctl is-active arctic-shadow-tracker
```

### High CPU/Memory Usage
```bash
# 1. Check process details
ps aux | grep arctic_shadow_streamer

# 2. Check system resources
htop

# 3. Check for memory leaks
valgrind --tool=memcheck python3 arctic_shadow_streamer.py test

# 4. Restart if necessary
sudo systemctl restart arctic-shadow-tracker
```

### API Connection Issues
```bash
# 1. Test network connectivity
curl -I https://id.barentswatch.no

# 2. Check DNS resolution
nslookup id.barentswatch.no

# 3. Test API authentication
cd /opt/arctic-shadow-tracker
python3 -c "
import yaml
from arctic_shadow_streamer import get_barentswatch_token
token = get_barentswatch_token()
print('Token OK' if token else 'Token FAILED')
"

# 4. Check firewall rules
sudo ufw status
```

### No Data Output
```bash
# 1. Check data directory permissions
ls -la /data/arctic/

# 2. Check available disk space
df -h /data/arctic

# 3. Check application configuration
cat /opt/arctic-shadow-tracker/config.yaml

# 4. Run test cycle manually
cd /opt/arctic-shadow-tracker
source venv/bin/activate
python3 arctic_shadow_streamer.py test
```

## Dashboard Setup

### Simple Web Dashboard (Optional)
```bash
# Install nginx if not already installed
sudo apt install nginx

# Create simple status page
sudo tee /var/www/html/arctic-status.html > /dev/null << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Arctic Shadow Tracker Status</title>
    <meta http-equiv="refresh" content="300">
</head>
<body>
    <h1>Arctic Shadow Tracker Status</h1>
    <div id="status">Loading...</div>
    <script>
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                document.getElementById('status').innerHTML = 
                    '<p>Status: ' + data.overall_health + '</p>' +
                    '<p>Last Update: ' + data.timestamp + '</p>';
            });
    </script>
</body>
</html>
EOF

# Configure nginx to serve status
sudo tee /etc/nginx/sites-available/arctic-status > /dev/null << 'EOF'
server {
    listen 8080;
    root /var/www/html;
    index arctic-status.html;
    
    location /api/status {
        proxy_pass http://localhost:8081/health;
    }
    
    location /dashboard {
        alias /data/arctic;
        autoindex on;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/arctic-status /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## Security Monitoring

### Log Analysis for Security Events
```bash
# Check for failed login attempts
sudo grep "Failed password" /var/log/auth.log | tail -20

# Check for unusual API requests
grep "ERROR" /data/arctic/streaming.log | grep -E "(401|403|429)"

# Check system resource usage patterns
sar -u 1 3  # CPU usage
sar -r 1 3  # Memory usage
```

### Automated Security Checks
- **SSH Login Monitoring**: fail2ban logs
- **Service Account Activity**: sudo logs for arctic-user
- **API Credential Usage**: Monitor for credential-related errors
- **File System Changes**: Monitor config file modifications

This monitoring setup provides comprehensive coverage while maintaining simplicity and cost-effectiveness for the MVP deployment.