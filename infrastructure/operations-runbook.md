# Arctic Shadow Tracker - Operations Runbook

## Quick Reference Commands

### Service Management
```bash
# SSH to VPS
ssh arctic-user@YOUR_VPS_IP

# Service status
sudo systemctl status arctic-shadow-tracker

# Start/stop/restart service
sudo systemctl start arctic-shadow-tracker
sudo systemctl stop arctic-shadow-tracker
sudo systemctl restart arctic-shadow-tracker

# View real-time logs
tail -f /data/arctic/streaming.log

# View service logs
sudo journalctl -u arctic-shadow-tracker -f
```

### Health Checks
```bash
# Quick health check
cd /opt/arctic-shadow-tracker && python3 health_check.py

# System resources
htop
df -h
free -h

# Network connectivity
curl -I https://id.barentswatch.no
```

### Data Management
```bash
# View recent data
ls -la /data/arctic/
tail -10 /data/arctic/vessel_positions.csv

# Manual backup
/opt/arctic-shadow-tracker/backup.sh

# Clean old data
/opt/arctic-shadow-tracker/cleanup.sh
```

## Emergency Procedures

### Service Down (Critical)
1. **Immediate Response** (within 5 minutes)
   ```bash
   ssh arctic-user@YOUR_VPS_IP
   sudo systemctl status arctic-shadow-tracker
   sudo systemctl restart arctic-shadow-tracker
   ```

2. **Verify Recovery**
   ```bash
   sleep 30
   sudo systemctl is-active arctic-shadow-tracker
   tail -20 /data/arctic/streaming.log
   ```

3. **If Still Down**
   ```bash
   # Check logs for errors
   sudo journalctl -u arctic-shadow-tracker -n 100
   
   # Check configuration
   python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"
   
   # Test manually
   cd /opt/arctic-shadow-tracker
   source venv/bin/activate
   python3 arctic_shadow_streamer.py test
   ```

### High CPU/Memory (Warning)
1. **Check Process Details**
   ```bash
   ps aux | grep arctic_shadow_streamer
   top -p $(pgrep -f arctic_shadow_streamer)
   ```

2. **Restart if Necessary**
   ```bash
   sudo systemctl restart arctic-shadow-tracker
   ```

3. **Monitor Recovery**
   ```bash
   watch 'ps aux | grep arctic_shadow_streamer'
   ```

### Disk Space Full (Critical)
1. **Immediate Cleanup**
   ```bash
   # Clean old data
   /opt/arctic-shadow-tracker/cleanup.sh
   
   # Remove old backups
   find /data/arctic/backups -name "*.tar.gz" -mtime +3 -delete
   
   # Clean system logs
   sudo journalctl --vacuum-time=3d
   ```

2. **Check Space**
   ```bash
   df -h /data/arctic
   ```

### API Connection Failure (Warning)
1. **Test Connectivity**
   ```bash
   curl -I https://id.barentswatch.no
   curl -I https://live.ais.barentswatch.no
   ```

2. **Test Authentication**
   ```bash
   cd /opt/arctic-shadow-tracker
   source venv/bin/activate
   python3 -c "
   from arctic_shadow_streamer import get_barentswatch_token
   print('OK' if get_barentswatch_token() else 'FAILED')
   "
   ```

3. **Check Configuration**
   ```bash
   # Verify config exists and is readable
   ls -la config.yaml
   grep -v secret config.yaml
   ```

## Deployment Procedures

### Code Update Deployment
1. **Trigger GitHub Actions**
   - Go to GitHub → Actions → "Deploy to VPS"
   - Click "Run workflow" → "update"

2. **Monitor Deployment**
   - Watch GitHub Actions logs
   - SSH to VPS and monitor: `sudo journalctl -u arctic-shadow-tracker -f`

3. **Verify Success**
   ```bash
   sudo systemctl status arctic-shadow-tracker
   tail -10 /data/arctic/streaming.log
   python3 health_check.py
   ```

### Emergency Rollback
1. **Stop Current Service**
   ```bash
   sudo systemctl stop arctic-shadow-tracker
   ```

2. **Restore Backup**
   ```bash
   cd /opt/arctic-shadow-tracker
   BACKUP=$(ls -t arctic_shadow_streamer.py.backup.* | head -1)
   cp "$BACKUP" arctic_shadow_streamer.py
   ```

3. **Restart Service**
   ```bash
   sudo systemctl start arctic-shadow-tracker
   sudo systemctl status arctic-shadow-tracker
   ```

### Configuration Update
1. **Update GitHub Secrets** (if needed)
   - Repository → Settings → Secrets and Variables → Actions

2. **Redeploy Configuration**
   - GitHub Actions → "Deploy to VPS" → "restart"

3. **Verify New Config**
   ```bash
   grep -v secret /opt/arctic-shadow-tracker/config.yaml
   ```

## Monitoring Procedures

### Daily Health Check
```bash
# Connect to VPS
ssh arctic-user@YOUR_VPS_IP

# Run health check
cd /opt/arctic-shadow-tracker
python3 health_check.py

# Check recent activity
tail -20 /data/arctic/streaming.log
ls -la /data/arctic/*.csv | tail -5

# Check system resources
df -h /data/arctic
free -h | grep Mem
```

### Weekly Performance Review
```bash
# Error analysis
grep ERROR /data/arctic/streaming.log | tail -20

# Service restarts
sudo journalctl -u arctic-shadow-tracker --since "1 week ago" | grep -i restart

# Resource trends
sar -u 1 3  # CPU
sar -r 1 3  # Memory

# Data growth
du -sh /data/arctic/*
```

### Monthly Security Review
```bash
# Failed login attempts
sudo grep "Failed password" /var/log/auth.log | tail -20

# Service account activity
sudo grep "arctic-user" /var/log/auth.log | tail -10

# Firewall status
sudo ufw status verbose

# System updates
sudo apt list --upgradable
```

## Alert Response

### GitHub Actions Alert
1. **Check GitHub Actions Tab**
   - Review failed workflow details
   - Check error messages and logs

2. **SSH Investigation**
   ```bash
   ssh arctic-user@YOUR_VPS_IP
   sudo systemctl status arctic-shadow-tracker
   tail -50 /data/arctic/streaming.log
   ```

3. **Resolution Actions**
   - Restart service if needed
   - Fix configuration issues
   - Re-run GitHub Actions workflow

### Discord/Slack Alerts
1. **Immediate Assessment**
   - SSH to VPS
   - Run health check
   - Check service status

2. **Take Action Based on Alert Type**
   - Service down → restart service
   - High resources → investigate and restart
   - API failure → check network and credentials

## Backup & Recovery

### Manual Backup
```bash
# SSH to VPS
ssh arctic-user@YOUR_VPS_IP

# Run backup script
/opt/arctic-shadow-tracker/backup.sh

# Verify backup
ls -la /data/arctic/backups/
```

### Restore from Backup
```bash
# List available backups
ls -la /data/arctic/backups/

# Restore CSV data
tar -xzf /data/arctic/backups/csv_backup_YYYYMMDD.tar.gz -C /

# Restore configuration
cp /data/arctic/backups/config_YYYYMMDD.yaml /opt/arctic-shadow-tracker/config.yaml
chmod 600 /opt/arctic-shadow-tracker/config.yaml

# Restore application
cp /data/arctic/backups/app_YYYYMMDD.py /opt/arctic-shadow-tracker/arctic_shadow_streamer.py

# Restart service
sudo systemctl restart arctic-shadow-tracker
```

### Full System Recovery
```bash
# If VPS needs to be rebuilt:
1. Create new VPS with same IP (if possible)
2. Run setup-vps.sh script
3. Configure GitHub Secrets (if changed)
4. Trigger GitHub Actions deployment
5. Restore data from backups
6. Verify all functionality
```

## Performance Optimization

### Resource Monitoring
```bash
# Real-time monitoring
htop

# Disk I/O monitoring
iotop

# Network monitoring
nethogs

# Process-specific monitoring
ps aux | grep arctic_shadow_streamer
```

### Optimization Actions
```bash
# Clean temporary files
sudo apt autoclean
sudo apt autoremove

# Optimize log rotation
sudo logrotate -f /etc/logrotate.d/arctic-shadow-tracker

# Restart service to clear memory
sudo systemctl restart arctic-shadow-tracker
```

## Contact Information

### Emergency Contacts
- **Primary**: Your email/phone
- **Secondary**: Team lead contact
- **Escalation**: Management contact

### Service Providers
- **VPS Provider**: Hetzner Support
- **API Provider**: BarentsWatch Support
- **GitHub**: GitHub Support (if needed)

### Documentation Links
- **GitHub Repository**: Link to your repository
- **Monitoring Dashboard**: http://YOUR_VPS_IP/dashboard
- **GitHub Actions**: Link to Actions tab

## Quick Troubleshooting

| Issue | Quick Check | Quick Fix |
|-------|-------------|-----------|
| Service down | `systemctl status arctic-shadow-tracker` | `sudo systemctl restart arctic-shadow-tracker` |
| No data | `ls /data/arctic/*.csv` | Check API credentials and network |
| High CPU | `top -p $(pgrep arctic)` | Restart service |
| Disk full | `df -h /data/arctic` | Run cleanup script |
| API errors | `tail /data/arctic/streaming.log` | Check credentials and network |
| SSH issues | `ssh arctic-user@VPS_IP` | Check SSH keys and firewall |

Remember: When in doubt, restart the service and check the logs!