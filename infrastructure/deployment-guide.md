# Arctic Shadow Tracker - Complete Deployment Guide

## Overview
This guide provides step-by-step instructions for deploying the Arctic Shadow Tracker system using the GitHub Actions + VPS hybrid approach.

## Prerequisites

### 1. VPS Requirements
- **Provider**: Hetzner (recommended) or any Ubuntu 22.04 VPS
- **Specifications**: 3 vCPU, 4GB RAM, 80GB SSD (CPX21)
- **Operating System**: Ubuntu 22.04 LTS
- **Network**: Public IP address, SSH access

### 2. API Credentials
- **BarentsWatch API**: Client ID and Secret from Norwegian Coastal Administration
- **Sentinel Hub**: Client ID and Secret (optional for satellite imagery)
- **Copernicus**: Username and Password (optional for satellite data)

### 3. GitHub Repository
- **Fork or clone**: Arctic Shadow Tracker repository
- **Permissions**: Repository admin access for GitHub Actions and Secrets

## Phase 1: VPS Initial Setup

### Step 1: Create VPS Instance
```bash
# On Hetzner Cloud Console:
1. Create new server
2. Select: Ubuntu 22.04
3. Choose: CPX21 (3 vCPU, 4GB RAM)
4. Add SSH key or create password
5. Create server and note public IP address
```

### Step 2: Initial Connection
```bash
# Connect to your VPS
ssh root@YOUR_VPS_IP

# Create non-root user for initial setup
adduser deploy
usermod -aG sudo deploy
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys

# Switch to deploy user
su - deploy
```

### Step 3: Run VPS Setup Script
```bash
# Download and run the setup script
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/ArcticShadowTracker/main/infrastructure/setup-vps.sh -o setup-vps.sh
chmod +x setup-vps.sh
./setup-vps.sh
```

### Step 4: Configure SSH Keys for GitHub Actions
```bash
# Generate SSH key pair for GitHub Actions
ssh-keygen -t ed25519 -f ~/.ssh/github_actions_key -N ""

# Copy public key to arctic-user
sudo mkdir -p /home/arctic-user/.ssh
sudo cp ~/.ssh/github_actions_key.pub /home/arctic-user/.ssh/authorized_keys
sudo chown -R arctic-user:arctic-user /home/arctic-user/.ssh
sudo chmod 700 /home/arctic-user/.ssh
sudo chmod 600 /home/arctic-user/.ssh/authorized_keys

# Display private key for GitHub Secrets (copy this)
cat ~/.ssh/github_actions_key
```

## Phase 2: GitHub Configuration

### Step 1: Configure Repository Secrets
Go to your GitHub repository → Settings → Secrets and Variables → Actions

Add these secrets:

#### VPS Connection Secrets
```
VPS_HOST=YOUR_VPS_IP_ADDRESS
VPS_USER=arctic-user
VPS_SSH_KEY=-----BEGIN OPENSSH PRIVATE KEY-----
(paste the entire private key from previous step)
-----END OPENSSH PRIVATE KEY-----
```

#### API Credentials (Base64 Encoded)
```bash
# Encode your credentials before adding to GitHub
echo -n "your-barentswatch-client-id" | base64
echo -n "your-barentswatch-secret" | base64
```

Add encoded values as secrets:
```
BARENTSWATCH_CLIENT_ID=<base64-encoded-client-id>
BARENTSWATCH_CLIENT_SECRET=<base64-encoded-secret>
SENTINEL_HUB_CLIENT_ID=<base64-encoded-client-id>
SENTINEL_HUB_CLIENT_SECRET=<base64-encoded-secret>
COPERNICUS_USERNAME=<base64-encoded-username>
COPERNICUS_PASSWORD=<base64-encoded-password>
```

#### Optional Alert Webhooks
```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

### Step 2: Verify GitHub Actions Workflows
Ensure these files exist in your repository:
- `.github/workflows/deploy.yml`
- `.github/workflows/monitor.yml`

## Phase 3: Initial Deployment

### Step 1: Test VPS Connectivity
```bash
# From your local machine, test SSH connection
ssh -i ~/.ssh/github_actions_key arctic-user@YOUR_VPS_IP "echo 'Connection successful'"
```

### Step 2: Trigger Initial Deployment
1. Go to GitHub → Actions → "Arctic Shadow Tracker - Deploy to VPS"
2. Click "Run workflow"
3. Select "full-deploy" option
4. Click "Run workflow"

### Step 3: Monitor Deployment
Watch the GitHub Actions logs for deployment progress. The deployment should:
1. ✅ Validate application syntax
2. ✅ Deploy application files to VPS
3. ✅ Install Python dependencies
4. ✅ Create configuration from secrets
5. ✅ Start systemd service
6. ✅ Run health checks

### Step 4: Verify Deployment
```bash
# SSH to VPS and check service status
ssh arctic-user@YOUR_VPS_IP

# Check service status
sudo systemctl status arctic-shadow-tracker

# Check logs
tail -f /data/arctic/streaming.log

# Run health check
cd /opt/arctic-shadow-tracker
python3 health_check.py

# Check dashboard
curl http://localhost/dashboard
```

## Phase 4: Monitoring Setup

### Step 1: Verify GitHub Actions Monitoring
The monitoring workflow should automatically:
- Run health checks every 30 minutes
- Create daily backups at 02:00 UTC
- Send alerts on failures
- Attempt service restart on critical issues

### Step 2: Set Up External Monitoring (Optional)
```bash
# Install additional monitoring tools on VPS
sudo apt install htop iotop nethogs

# Create simple status page
curl http://YOUR_VPS_IP/dashboard
```

### Step 3: Configure Alert Notifications
If you set up Discord/Slack webhooks, test them:
```bash
# Test Discord webhook
curl -H "Content-Type: application/json" \
     -d '{"content": "🧪 Arctic Shadow Tracker test alert"}' \
     YOUR_DISCORD_WEBHOOK_URL

# Test Slack webhook  
curl -X POST -H 'Content-type: application/json' \
     --data '{"text":"🧪 Arctic Shadow Tracker test alert"}' \
     YOUR_SLACK_WEBHOOK_URL
```

## Phase 5: Operations & Maintenance

### Daily Operations

#### Check System Health
```bash
# SSH to VPS
ssh arctic-user@YOUR_VPS_IP

# Quick health check
/opt/arctic-shadow-tracker/health_check.py

# Service status
sudo systemctl status arctic-shadow-tracker

# Recent logs
tail -20 /data/arctic/streaming.log

# Resource usage
htop

# Disk space
df -h /data/arctic
```

#### View Current Data
```bash
# List recent data files
ls -la /data/arctic/

# View latest dashboard
curl http://YOUR_VPS_IP/dashboard/arctic_dashboard_latest.html

# Check CSV data
tail -5 /data/arctic/vessel_positions.csv
```

### Weekly Operations

#### Review Performance
```bash
# Check error logs
grep ERROR /data/arctic/streaming.log | tail -20

# Review system logs
sudo journalctl -u arctic-shadow-tracker --since "1 week ago" | grep ERROR

# Check backup status
ls -la /data/arctic/backups/

# Review security logs
sudo grep "Failed password" /var/log/auth.log | tail -10
```

#### Update Dependencies
```bash
# SSH to VPS
ssh arctic-user@YOUR_VPS_IP

# Update system
sudo apt update && sudo apt upgrade -y

# Update Python packages (if needed)
cd /opt/arctic-shadow-tracker
source venv/bin/activate
pip list --outdated
# pip install --upgrade package-name
```

### Monthly Operations

#### Security Maintenance
```bash
# Review and rotate SSH keys
# Review firewall rules
sudo ufw status verbose

# Check for security updates
sudo apt list --upgradable | grep -i security

# Review access logs
sudo grep "Accepted" /var/log/auth.log | tail -20
```

#### Performance Optimization
```bash
# Analyze resource usage trends
sar -u 1 3  # CPU usage
sar -r 1 3  # Memory usage

# Clean up old data (automated, but verify)
find /data/arctic -name "*.csv" -mtime +30 -ls

# Review log file sizes
du -sh /var/log/arctic/*
du -sh /data/arctic/*
```

## Troubleshooting Guide

### Service Won't Start
```bash
# Check service status
sudo systemctl status arctic-shadow-tracker

# Check service logs
sudo journalctl -u arctic-shadow-tracker -n 50

# Verify configuration
cd /opt/arctic-shadow-tracker
python3 -c "import yaml; print(yaml.safe_load(open('config.yaml')))"

# Test application manually
source venv/bin/activate
python3 arctic_shadow_streamer.py test
```

### No Data Being Collected
```bash
# Test API connectivity
cd /opt/arctic-shadow-tracker
source venv/bin/activate
python3 -c "
from arctic_shadow_streamer import get_barentswatch_token
token = get_barentswatch_token()
print('API OK' if token else 'API FAILED')
"

# Check network connectivity
curl -I https://id.barentswatch.no
curl -I https://live.ais.barentswatch.no

# Verify configuration
grep -v password config.yaml
```

### High Resource Usage
```bash
# Identify resource usage
top -p $(pgrep -f arctic_shadow_streamer)
ps aux | grep arctic

# Check for memory leaks
sudo systemctl restart arctic-shadow-tracker
sleep 60
ps aux | grep arctic_shadow_streamer
```

### GitHub Actions Failing
1. Check repository secrets are correctly set
2. Verify VPS SSH connectivity from GitHub
3. Review workflow logs in GitHub Actions tab
4. Test manual SSH connection with same credentials

## Scaling Considerations

### Vertical Scaling
If resource usage grows:
```bash
# Monitor current usage
htop
df -h
free -h

# Upgrade VPS instance type on Hetzner:
# CPX21 → CPX31 (4 vCPU, 8GB RAM)
# CPX31 → CPX41 (8 vCPU, 16GB RAM)
```

### Horizontal Scaling (Future)
For multi-instance deployment:
1. Set up load balancer
2. Use shared storage (S3-compatible)
3. Implement database for coordination
4. Configure distributed monitoring

## Security Checklist

### Initial Deployment
- [ ] SSH key authentication configured
- [ ] Password authentication disabled
- [ ] Firewall rules active and tested
- [ ] fail2ban configured and running
- [ ] Service account has minimal privileges
- [ ] Configuration files secured (600 permissions)
- [ ] GitHub Secrets properly configured
- [ ] SSL/TLS certificates installed (if using HTTPS)

### Ongoing Security
- [ ] Regular security updates applied
- [ ] SSH keys rotated quarterly
- [ ] API credentials rotated semi-annually
- [ ] Backup integrity verified monthly
- [ ] Security logs reviewed weekly
- [ ] Access logs monitored continuously

## Cost Monitoring

### Monthly Costs
- **Hetzner CPX21**: ~$22/month
- **Backup Storage**: ~$3/month
- **Domain (optional)**: ~$1/month
- **Total**: ~$26/month

### Cost Optimization
- Monitor resource usage to right-size instance
- Use reserved instances for 12+ month deployments
- Implement auto-shutdown during maintenance windows
- Optimize data retention policies

This deployment guide provides a complete, production-ready setup for the Arctic Shadow Tracker system with comprehensive monitoring, security, and operational procedures.