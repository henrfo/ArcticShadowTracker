# Arctic Shadow Tracker - VPS Infrastructure Setup

## VPS Specifications (Hetzner Recommended)

### Minimum Requirements
- **Instance Type**: CPX21 (3 vCPU, 4GB RAM, 80GB SSD)
- **Monthly Cost**: ~$22/month
- **Location**: Europe (Germany) for compliance and latency
- **OS**: Ubuntu 22.04 LTS

### Storage Layout
```
/
├── /opt/arctic-shadow-tracker/     # Application code
├── /var/log/arctic/               # Application logs
├── /data/arctic/                  # Persistent data storage
│   ├── csv/                       # CSV output files
│   ├── dashboards/               # HTML dashboards
│   ├── intelligence/             # Intelligence reports
│   └── backups/                  # Daily backups
└── /etc/systemd/system/          # Service files
```

### Network Configuration
- **Firewall**: UFW with restrictive rules
- **SSH**: Key-based authentication only
- **HTTPS**: Let's Encrypt SSL certificate
- **Monitoring**: Port 9090 (Prometheus) - restricted to monitoring IPs

## Initial Server Setup

### 1. Basic Security Hardening
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y ufw fail2ban htop curl wget git python3 python3-pip python3-venv nginx

# Setup firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable

# Configure fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 2. User Management
```bash
# Create service user
sudo useradd -r -m -s /bin/bash arctic-user
sudo mkdir -p /home/arctic-user/.ssh
sudo chmod 700 /home/arctic-user/.ssh

# Add deployment key (GitHub Actions will provide this)
# sudo vi /home/arctic-user/.ssh/authorized_keys
# sudo chmod 600 /home/arctic-user/.ssh/authorized_keys
# sudo chown -R arctic-user:arctic-user /home/arctic-user/.ssh
```

### 3. Application Directory Structure
```bash
# Create application directories
sudo mkdir -p /opt/arctic-shadow-tracker
sudo mkdir -p /data/arctic/{csv,dashboards,intelligence,backups}
sudo mkdir -p /var/log/arctic

# Set ownership
sudo chown -R arctic-user:arctic-user /opt/arctic-shadow-tracker
sudo chown -R arctic-user:arctic-user /data/arctic
sudo chown -R arctic-user:arctic-user /var/log/arctic
```

### 4. Python Environment Setup
```bash
# Switch to service user
sudo su - arctic-user

# Create virtual environment
cd /opt/arctic-shadow-tracker
python3 -m venv venv
source venv/bin/activate

# Install dependencies (requirements.txt will be deployed via GitHub Actions)
# pip install -r requirements.txt
```

## Cost Breakdown & Optimization

### Monthly Costs
- **VPS (Hetzner CPX21)**: $22/month
- **Backup Storage**: $3/month (20GB backup storage)
- **Domain (optional)**: $12/year (~$1/month)
- **Total**: ~$26/month

### Cost Optimization Options
1. **Smaller Instance**: CPX11 (2 vCPU, 2GB RAM) for $11/month if resource usage is low
2. **Reserved Instance**: 12-month commitment can reduce costs by 15-20%
3. **Auto-shutdown**: During maintenance windows (saves ~5% monthly)

## Backup Strategy

### Automated Daily Backups
```bash
# Backup script (will be created in deployment)
/opt/arctic-shadow-tracker/scripts/backup.sh

# Retention policy
- Daily backups: 7 days
- Weekly backups: 4 weeks  
- Monthly backups: 3 months
```

### Disaster Recovery
- **RTO**: 15 minutes (time to restore service)
- **RPO**: 24 hours (maximum data loss)
- **Backup Storage**: Both local and remote (Hetzner backup service)

## Environment Variables

### System Environment File: `/etc/environment`
```bash
ARCTIC_ENV=production
ARCTIC_DATA_DIR=/data/arctic
ARCTIC_LOG_DIR=/var/log/arctic
ARCTIC_CONFIG_DIR=/opt/arctic-shadow-tracker/config
```

### Application Configuration
Configuration will be managed through GitHub Secrets and deployed via GitHub Actions.

## Monitoring Endpoints

### Health Check Endpoint
- **URL**: `http://localhost:8080/health`
- **Response**: JSON status of all components
- **Timeout**: 30 seconds

### Resource Monitoring
- **CPU Usage**: Target <70% average
- **Memory Usage**: Target <80% average  
- **Disk Usage**: Alert at >85%
- **Network**: Monitor API call rates and failures

## Security Considerations

### Access Control
- SSH access restricted to specific IP ranges
- Service account with minimal privileges
- Regular security updates via GitHub Actions

### API Security
- BarentsWatch credentials stored as GitHub Secrets
- API rate limiting and retry logic
- Secure credential rotation procedures

### Data Protection
- No sensitive vessel data persisted beyond operational needs
- GDPR compliance for any EU maritime data
- Encrypted backups with key rotation

## Scaling Considerations

### Vertical Scaling
- Monitor resource usage metrics
- Upgrade to CPX31 (4 vCPU, 8GB RAM) if needed
- Auto-scaling triggers based on CPU/memory thresholds

### Horizontal Scaling (Future)
- Load balancer for multiple instances
- Shared data storage (S3-compatible)
- Database for coordination between instances

This setup provides a robust, cost-effective foundation for the Arctic Shadow Tracker system while maintaining simplicity and operational efficiency.