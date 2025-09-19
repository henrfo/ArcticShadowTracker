#!/bin/bash
# Arctic Shadow Tracker - VPS Initial Setup Script
# Run this script on a fresh Ubuntu 22.04 VPS

set -e  # Exit on any error

echo "🛰️ Arctic Shadow Tracker - VPS Setup Starting..."

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

# Update system
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install essential packages
print_status "Installing essential packages..."
sudo apt install -y \
    ufw fail2ban htop curl wget git \
    python3 python3-pip python3-venv \
    nginx software-properties-common \
    unattended-upgrades apt-listchanges \
    logrotate rsync gnupg

# Configure automatic security updates
print_status "Configuring automatic security updates..."
sudo dpkg-reconfigure -plow unattended-upgrades

# Setup firewall
print_status "Configuring firewall..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

print_status "Firewall configured:"
sudo ufw status verbose

# Create service user
print_status "Creating service user..."
if ! id "arctic-user" &>/dev/null; then
    sudo useradd -r -m -s /bin/bash -d /home/arctic-user arctic-user
    print_status "User 'arctic-user' created"
else
    print_warning "User 'arctic-user' already exists"
fi

# Create directory structure
print_status "Creating directory structure..."
sudo mkdir -p /opt/arctic-shadow-tracker/{scripts,config,logs}
sudo mkdir -p /data/arctic/{csv,dashboards,intelligence,backups}
sudo mkdir -p /var/log/arctic

# Set ownership and permissions
print_status "Setting directory permissions..."
sudo chown -R arctic-user:arctic-user /opt/arctic-shadow-tracker
sudo chown -R arctic-user:arctic-user /data/arctic
sudo chown -R arctic-user:arctic-user /var/log/arctic

sudo chmod 755 /opt/arctic-shadow-tracker
sudo chmod 755 /data/arctic
sudo chmod 755 /var/log/arctic

# Setup Python environment
print_status "Setting up Python environment..."
sudo -u arctic-user bash << 'EOF'
cd /opt/arctic-shadow-tracker
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
EOF

print_status "Python virtual environment created"

# Configure SSH hardening
print_status "Hardening SSH configuration..."
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

sudo tee -a /etc/ssh/sshd_config << 'EOF'

# Arctic Shadow Tracker SSH Security Settings
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
AllowUsers arctic-user

# Disable unused features
X11Forwarding no
PermitEmptyPasswords no
PermitUserEnvironment no
AllowAgentForwarding no
AllowTcpForwarding no
GatewayPorts no
EOF

# Test SSH configuration before restarting
if sudo sshd -t; then
    print_status "SSH configuration is valid"
    sudo systemctl restart sshd
else
    print_error "SSH configuration has errors. Reverting..."
    sudo cp /etc/ssh/sshd_config.backup /etc/ssh/sshd_config
    exit 1
fi

# Configure fail2ban
print_status "Configuring fail2ban..."
sudo tee /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 1800
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600

[arctic-app]
enabled = true
port = http,https
filter = arctic-app
logpath = /data/arctic/streaming.log
maxretry = 5
bantime = 1800
EOF

sudo tee /etc/fail2ban/filter.d/arctic-app.conf << 'EOF'
[Definition]
failregex = ^.*ERROR.*Authentication failed.*<HOST>.*$
            ^.*ERROR.*API.*401.*<HOST>.*$
            ^.*ERROR.*Too many requests.*<HOST>.*$
EOF

sudo systemctl enable fail2ban
sudo systemctl restart fail2ban

# Setup log rotation
print_status "Configuring log rotation..."
sudo tee /etc/logrotate.d/arctic-shadow-tracker << 'EOF'
/var/log/arctic/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 644 arctic-user arctic-user
    postrotate
        /bin/systemctl reload arctic-shadow-tracker > /dev/null 2>&1 || true
    endscript
}

/data/arctic/streaming.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 arctic-user arctic-user
    postrotate
        /bin/systemctl reload arctic-shadow-tracker > /dev/null 2>&1 || true
    endscript
}
EOF

# Create basic health check script
print_status "Creating health check script..."
sudo -u arctic-user tee /opt/arctic-shadow-tracker/health_check.py << 'EOF'
#!/usr/bin/env python3
"""
Arctic Shadow Tracker Health Check
"""
import json
import os
import subprocess
import time
import sys
from datetime import datetime
from pathlib import Path

def check_service_status():
    """Check if systemd service is running"""
    try:
        result = subprocess.run(['systemctl', 'is-active', 'arctic-shadow-tracker'], 
                              capture_output=True, text=True)
        return result.stdout.strip() == 'active'
    except:
        return False

def check_log_activity():
    """Check if application log shows recent activity"""
    log_file = Path('/data/arctic/streaming.log')
    if not log_file.exists():
        return False
    
    try:
        # Check if log was modified in last 60 minutes
        mod_time = log_file.stat().st_mtime
        return (time.time() - mod_time) < 3600
    except:
        return False

def check_data_output():
    """Check if data files are being generated"""
    data_dir = Path('/data/arctic')
    if not data_dir.exists():
        return False
    
    try:
        csv_files = list(data_dir.glob('*.csv'))
        return len(csv_files) > 0
    except:
        return False

def check_disk_space():
    """Check available disk space"""
    try:
        result = subprocess.run(['df', '-h', '/data/arctic'], 
                              capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:
            usage = lines[1].split()[4].rstrip('%')
            return int(usage) < 90
    except:
        pass
    return True

def check_memory_usage():
    """Check memory usage"""
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
        
        total = None
        available = None
        for line in meminfo.split('\n'):
            if line.startswith('MemTotal:'):
                total = int(line.split()[1])
            elif line.startswith('MemAvailable:'):
                available = int(line.split()[1])
        
        if total and available:
            usage_percent = ((total - available) / total) * 100
            return usage_percent < 90
    except:
        pass
    return True

def main():
    """Run health checks and return status"""
    status = {
        'timestamp': datetime.now().isoformat(),
        'service_running': check_service_status(),
        'log_active': check_log_activity(),
        'data_output': check_data_output(),
        'disk_space_ok': check_disk_space(),
        'memory_ok': check_memory_usage(),
        'overall_health': 'healthy'
    }
    
    # Determine overall health
    critical_checks = ['service_running', 'disk_space_ok', 'memory_ok']
    warning_checks = ['log_active', 'data_output']
    
    critical_failed = any(not status[check] for check in critical_checks)
    warning_failed = any(not status[check] for check in warning_checks)
    
    if critical_failed:
        status['overall_health'] = 'unhealthy'
    elif warning_failed:
        status['overall_health'] = 'warning'
    
    # Output JSON for GitHub Actions
    print(json.dumps(status, indent=2))
    
    # Exit code for monitoring
    if status['overall_health'] == 'unhealthy':
        return 1
    elif status['overall_health'] == 'warning':
        return 2
    else:
        return 0

if __name__ == '__main__':
    exit(main())
EOF

chmod +x /opt/arctic-shadow-tracker/health_check.py

# Create backup script
print_status "Creating backup script..."
sudo -u arctic-user tee /opt/arctic-shadow-tracker/backup.sh << 'EOF'
#!/bin/bash
# Arctic Shadow Tracker Backup Script

BACKUP_DIR="/data/arctic/backups"
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/var/log/arctic/backup.log"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "$(date): Starting backup..." >> "$LOG_FILE"

# Backup CSV data
if ls /data/arctic/*.csv 1> /dev/null 2>&1; then
    tar -czf "$BACKUP_DIR/csv_backup_$DATE.tar.gz" /data/arctic/*.csv
    echo "$(date): CSV backup completed" >> "$LOG_FILE"
fi

# Backup configuration
if [ -f "/opt/arctic-shadow-tracker/config.yaml" ]; then
    cp "/opt/arctic-shadow-tracker/config.yaml" "$BACKUP_DIR/config_$DATE.yaml"
    echo "$(date): Config backup completed" >> "$LOG_FILE"
fi

# Backup application
cp "/opt/arctic-shadow-tracker/arctic_shadow_streamer.py" "$BACKUP_DIR/app_$DATE.py" 2>/dev/null || true

# Clean old backups (keep 7 days)
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete
find "$BACKUP_DIR" -name "*.yaml" -mtime +7 -delete  
find "$BACKUP_DIR" -name "*.py" -mtime +7 -delete

echo "$(date): Backup cleanup completed" >> "$LOG_FILE"
echo "$(date): Backup process finished" >> "$LOG_FILE"
EOF

chmod +x /opt/arctic-shadow-tracker/backup.sh

# Create data cleanup script
print_status "Creating data cleanup script..."
sudo -u arctic-user tee /opt/arctic-shadow-tracker/cleanup.sh << 'EOF'
#!/bin/bash
# Data retention and cleanup script

DATA_DIR="/data/arctic"
LOG_DIR="/var/log/arctic"

echo "$(date): Starting data cleanup..."

# Keep CSV files for 30 days
find "$DATA_DIR" -name "*.csv" -mtime +30 -delete 2>/dev/null

# Keep dashboards for 7 days
find "$DATA_DIR" -name "*.html" -mtime +7 -delete 2>/dev/null

# Keep application logs for 14 days
find "$LOG_DIR" -name "*.log" -mtime +14 -delete 2>/dev/null

# Keep vessel history for 90 days
find "$DATA_DIR" -name "*history.json" -mtime +90 -delete 2>/dev/null

echo "$(date): Data cleanup completed"
EOF

chmod +x /opt/arctic-shadow-tracker/cleanup.sh

# Set up cron jobs for arctic-user
print_status "Setting up cron jobs..."
sudo -u arctic-user bash << 'EOF'
# Create crontab
(crontab -l 2>/dev/null; echo "# Arctic Shadow Tracker Maintenance") | crontab -
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/arctic-shadow-tracker/backup.sh") | crontab -
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/arctic-shadow-tracker/cleanup.sh") | crontab -
EOF

print_status "Cron jobs configured"

# Create systemd service template
print_status "Creating systemd service template..."
sudo tee /etc/systemd/system/arctic-shadow-tracker.service << 'EOF'
[Unit]
Description=Arctic Shadow Tracker - Vessel Monitoring System
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=arctic-user
Group=arctic-user
WorkingDirectory=/opt/arctic-shadow-tracker
Environment=PATH=/opt/arctic-shadow-tracker/venv/bin
ExecStart=/opt/arctic-shadow-tracker/venv/bin/python arctic_shadow_streamer.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=arctic-shadow-tracker

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/data/arctic /var/log/arctic /tmp
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictRealtime=true
RestrictNamespaces=true
LockPersonality=true
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload

# Create environment file
print_status "Creating environment configuration..."
sudo tee /etc/environment << 'EOF'
ARCTIC_ENV=production
ARCTIC_DATA_DIR=/data/arctic
ARCTIC_LOG_DIR=/var/log/arctic
ARCTIC_CONFIG_DIR=/opt/arctic-shadow-tracker
PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EOF

# Setup nginx for dashboard serving (optional)
print_status "Configuring nginx for dashboard access..."
sudo tee /etc/nginx/sites-available/arctic-dashboard << 'EOF'
server {
    listen 80;
    server_name _;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Dashboard access
    location /dashboard {
        alias /data/arctic;
        autoindex on;
        autoindex_exact_size off;
        autoindex_localtime on;
        
        # Restrict access to HTML files only
        location ~* \.(html)$ {
            try_files $uri =404;
        }
        
        # Deny access to sensitive files
        location ~* \.(yaml|yml|json|log|csv)$ {
            deny all;
        }
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        return 200 '{"status":"nginx_ok"}';
        add_header Content-Type application/json;
    }
    
    # Block all other access
    location / {
        return 403;
    }
}
EOF

# Disable default nginx site and enable our dashboard
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/arctic-dashboard /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx

# Final system status
print_status "=== VPS Setup Complete ==="
print_status "Next steps:"
echo "1. Copy your SSH public key to /home/arctic-user/.ssh/authorized_keys"
echo "2. Configure GitHub Secrets with VPS details"
echo "3. Deploy application using GitHub Actions"
echo "4. Verify service status: sudo systemctl status arctic-shadow-tracker"
echo "5. Check dashboard: http://your-vps-ip/dashboard"

print_status "System Information:"
echo "- OS: $(lsb_release -d | cut -f2)"
echo "- Kernel: $(uname -r)"
echo "- Python: $(python3 --version)"
echo "- Disk Space: $(df -h / | awk 'NR==2 {print $4}') available"
echo "- Memory: $(free -h | awk 'NR==2 {print $7}') available"

print_status "Service Status:"
echo "- UFW Firewall: $(sudo ufw status | head -1)"
echo "- fail2ban: $(sudo systemctl is-active fail2ban)"
echo "- nginx: $(sudo systemctl is-active nginx)"

print_warning "Remember to:"
echo "- Set up SSH key authentication before disabling password auth"
echo "- Configure GitHub repository secrets"
echo "- Test deployment workflow"
echo "- Monitor logs after first deployment"

echo -e "\n${GREEN}🛰️ Arctic Shadow Tracker VPS setup completed successfully!${NC}"
EOF

chmod +x /opt/arctic-shadow-tracker/setup-vps.sh
EOF