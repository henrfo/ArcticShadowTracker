# Arctic Shadow Tracker - Security Setup

## Security Architecture Overview

### Defense in Depth Strategy
1. **Network Security**: Firewall, SSH hardening, restricted access
2. **Application Security**: Secure credential management, input validation
3. **System Security**: User privileges, file permissions, service isolation
4. **Data Security**: Encryption at rest, secure backups, data retention policies
5. **Operational Security**: Audit logging, monitoring, incident response

## Network Security

### VPS Firewall Configuration (UFW)
```bash
# Reset firewall rules
sudo ufw --force reset

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Essential services
sudo ufw allow ssh
sudo ufw allow 80/tcp    # HTTP (for dashboard)
sudo ufw allow 443/tcp   # HTTPS (for dashboard)

# Optional: Restrict SSH to specific IPs
# sudo ufw allow from YOUR_IP_ADDRESS to any port ssh

# Enable firewall
sudo ufw enable

# Verify rules
sudo ufw status verbose
```

### SSH Hardening
```bash
# Edit SSH configuration
sudo tee -a /etc/ssh/sshd_config << 'EOF'

# Security hardening
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

# Restart SSH service
sudo systemctl restart sshd
```

### fail2ban Configuration
```bash
# Create custom jail for Arctic Shadow Tracker
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

# Create filter for application logs
sudo tee /etc/fail2ban/filter.d/arctic-app.conf << 'EOF'
[Definition]
failregex = ^.*ERROR.*Authentication failed.*<HOST>.*$
            ^.*ERROR.*API.*401.*<HOST>.*$
            ^.*ERROR.*Too many requests.*<HOST>.*$
EOF

# Restart fail2ban
sudo systemctl restart fail2ban
```

## Application Security

### GitHub Secrets Configuration
Configure these secrets in GitHub repository settings:

#### VPS Access Secrets
```
VPS_HOST=your-vps-ip-address
VPS_USER=arctic-user
VPS_SSH_KEY=-----BEGIN OPENSSH PRIVATE KEY-----
```

#### API Credentials (Base64 Encoded for Security)
```bash
# Encode credentials before storing in GitHub Secrets
echo -n "your-barentswatch-client-id" | base64
echo -n "your-barentswatch-secret" | base64
echo -n "your-sentinel-hub-client-id" | base64
echo -n "your-sentinel-hub-secret" | base64
```

#### GitHub Secrets Required
```
BARENTSWATCH_CLIENT_ID=<base64-encoded-client-id>
BARENTSWATCH_CLIENT_SECRET=<base64-encoded-secret>
SENTINEL_HUB_CLIENT_ID=<base64-encoded-client-id>
SENTINEL_HUB_CLIENT_SECRET=<base64-encoded-secret>
COPERNICUS_USERNAME=<base64-encoded-username>
COPERNICUS_PASSWORD=<base64-encoded-password>

# Optional: Alert webhooks
DISCORD_WEBHOOK_URL=<webhook-url>
SLACK_WEBHOOK_URL=<webhook-url>
```

### Credential Management on VPS
```bash
# Create secure config file (deployed via GitHub Actions)
sudo tee /opt/arctic-shadow-tracker/deploy-config.sh << 'EOF'
#!/bin/bash
# This script is called by GitHub Actions to deploy configuration

# Decode base64 credentials and create config.yaml
cat > /opt/arctic-shadow-tracker/config.yaml << CONFIGEOF
barentswatch:
  client_id: '$(echo $BARENTSWATCH_CLIENT_ID | base64 -d)'
  client_secret: '$(echo $BARENTSWATCH_CLIENT_SECRET | base64 -d)'
  scope: 'ais'

sentinel_hub:
  client_id: '$(echo $SENTINEL_HUB_CLIENT_ID | base64 -d)'
  client_secret: '$(echo $SENTINEL_HUB_CLIENT_SECRET | base64 -d)'

copernicus:
  username: '$(echo $COPERNICUS_USERNAME | base64 -d)'
  password: '$(echo $COPERNICUS_PASSWORD | base64 -d)'

image:
  resolution: 100
  max_size: 2000
  default_days: 30
CONFIGEOF

# Set restrictive permissions
chmod 600 /opt/arctic-shadow-tracker/config.yaml
chown arctic-user:arctic-user /opt/arctic-shadow-tracker/config.yaml

# Remove this script for security
rm -- "$0"
EOF

chmod +x /opt/arctic-shadow-tracker/deploy-config.sh
```

## System Security

### User Account Security
```bash
# Create service account with minimal privileges
sudo useradd -r -m -s /bin/bash -d /home/arctic-user arctic-user

# Add to necessary groups only
sudo usermod -a -G systemd-journal arctic-user  # For log access

# Disable password login for service account
sudo passwd -l arctic-user

# Set up sudo restrictions (if needed)
sudo tee /etc/sudoers.d/arctic-user << 'EOF'
arctic-user ALL=(root) NOPASSWD: /bin/systemctl restart arctic-shadow-tracker
arctic-user ALL=(root) NOPASSWD: /bin/systemctl stop arctic-shadow-tracker
arctic-user ALL=(root) NOPASSWD: /bin/systemctl start arctic-shadow-tracker
arctic-user ALL=(root) NOPASSWD: /bin/systemctl status arctic-shadow-tracker
EOF
```

### File System Security
```bash
# Set up directory permissions
sudo chmod 755 /opt/arctic-shadow-tracker
sudo chmod 755 /data/arctic
sudo chmod 755 /var/log/arctic

# Set ownership
sudo chown -R arctic-user:arctic-user /opt/arctic-shadow-tracker
sudo chown -R arctic-user:arctic-user /data/arctic
sudo chown -R arctic-user:arctic-user /var/log/arctic

# Secure configuration files
sudo chmod 600 /opt/arctic-shadow-tracker/config.yaml
sudo chown arctic-user:arctic-user /opt/arctic-shadow-tracker/config.yaml

# Create .htaccess for web directory (if serving files via nginx)
sudo tee /data/arctic/.htaccess << 'EOF'
# Deny access to sensitive files
<FilesMatch "\.(yaml|yml|json|log)$">
    Require all denied
</FilesMatch>
EOF
```

### Service Security (systemd)
```bash
# Security-hardened systemd service configuration
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
MemoryDenyWriteExecute=true
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

[Install]
WantedBy=multi-user.target
EOF
```

## Data Security

### Encryption at Rest
```bash
# Enable full disk encryption (during VPS setup)
# For existing systems, encrypt sensitive directories
sudo apt install ecryptfs-utils

# Encrypt backup directory
sudo ecryptfs-add-passphrase
sudo mount -t ecryptfs /data/arctic/backups /data/arctic/backups

# Make encryption persistent
echo "/data/arctic/backups /data/arctic/backups ecryptfs defaults 0 0" | sudo tee -a /etc/fstab
```

### Secure Backup Strategy
```bash
# Create encrypted backup script
sudo tee /opt/arctic-shadow-tracker/secure-backup.sh << 'EOF'
#!/bin/bash
# Secure backup with encryption

BACKUP_DIR="/data/arctic/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="arctic_backup_$DATE.tar.gz.gpg"

# Create encrypted backup
tar -czf - /data/arctic/*.csv /data/arctic/*.json 2>/dev/null | \
gpg --symmetric --cipher-algo AES256 --compress-algo 1 \
    --output "$BACKUP_DIR/$BACKUP_FILE"

# Clean old backups (keep 14 days)
find "$BACKUP_DIR" -name "*.gpg" -mtime +14 -delete

echo "Encrypted backup created: $BACKUP_FILE"
EOF

chmod +x /opt/arctic-shadow-tracker/secure-backup.sh
```

### Data Retention Policy
```bash
# Automated data cleanup script
sudo tee /opt/arctic-shadow-tracker/data-cleanup.sh << 'EOF'
#!/bin/bash
# Data retention and cleanup

DATA_DIR="/data/arctic"
LOG_DIR="/var/log/arctic"

# Keep CSV files for 30 days
find "$DATA_DIR" -name "*.csv" -mtime +30 -delete

# Keep dashboards for 7 days
find "$DATA_DIR" -name "*.html" -mtime +7 -delete

# Keep application logs for 14 days  
find "$LOG_DIR" -name "*.log" -mtime +14 -delete

# Keep vessel history for 90 days
find "$DATA_DIR" -name "*history.json" -mtime +90 -delete

echo "Data cleanup completed: $(date)"
EOF

chmod +x /opt/arctic-shadow-tracker/data-cleanup.sh

# Add to crontab for daily execution
echo "0 2 * * * /opt/arctic-shadow-tracker/data-cleanup.sh" | sudo crontab -u arctic-user -
```

## Audit Logging

### System Audit Configuration
```bash
# Install auditd
sudo apt install auditd audispd-plugins

# Configure audit rules
sudo tee -a /etc/audit/rules.d/arctic.rules << 'EOF'
# Monitor Arctic Shadow Tracker files
-w /opt/arctic-shadow-tracker/ -p wa -k arctic-app
-w /data/arctic/ -p wa -k arctic-data
-w /etc/systemd/system/arctic-shadow-tracker.service -p wa -k arctic-service

# Monitor configuration changes
-w /opt/arctic-shadow-tracker/config.yaml -p wa -k arctic-config

# Monitor service account activities
-w /home/arctic-user/ -p wa -k arctic-user
EOF

# Restart auditd
sudo systemctl restart auditd
```

### Application Audit Logging
```python
# Add to arctic_shadow_streamer.py (security logging)
import logging
import hashlib
import os

# Create security logger
security_logger = logging.getLogger('arctic.security')
security_handler = logging.FileHandler('/var/log/arctic/security.log')
security_formatter = logging.Formatter('%(asctime)s - SECURITY - %(levelname)s - %(message)s')
security_handler.setFormatter(security_formatter)
security_logger.addHandler(security_handler)
security_logger.setLevel(logging.INFO)

def log_security_event(event_type, details):
    """Log security-relevant events"""
    security_logger.info(f"{event_type}: {details}")

# Examples of security logging:
# log_security_event("CONFIG_ACCESS", f"Config file accessed by PID {os.getpid()}")
# log_security_event("API_AUTH", f"BarentsWatch authentication successful")
# log_security_event("DATA_EXPORT", f"CSV file created: {filename}")
```

## Incident Response

### Security Incident Response Plan
```bash
# Create incident response script
sudo tee /opt/arctic-shadow-tracker/incident-response.sh << 'EOF'
#!/bin/bash
# Security incident response script

echo "=== SECURITY INCIDENT RESPONSE ==="
echo "Timestamp: $(date)"

# 1. Stop service
sudo systemctl stop arctic-shadow-tracker
echo "Service stopped"

# 2. Preserve logs
cp /var/log/arctic/*.log /tmp/incident-logs-$(date +%Y%m%d_%H%M%S)/
cp /var/log/auth.log /tmp/incident-logs-$(date +%Y%m%d_%H%M%S)/
echo "Logs preserved"

# 3. Check for unauthorized changes
find /opt/arctic-shadow-tracker -type f -mtime -1 -ls
echo "Recent file changes listed"

# 4. Network analysis
ss -tulpn > /tmp/incident-logs-$(date +%Y%m%d_%H%M%S)/network-connections.txt
echo "Network connections logged"

# 5. Process analysis  
ps aux > /tmp/incident-logs-$(date +%Y%m%d_%H%M%S)/processes.txt
echo "Process list logged"

echo "=== INCIDENT RESPONSE COMPLETE ==="
echo "Review logs in /tmp/incident-logs-* before restarting service"
EOF

chmod +x /opt/arctic-shadow-tracker/incident-response.sh
```

## Security Monitoring

### Automated Security Checks
```bash
# Create security monitoring script
sudo tee /opt/arctic-shadow-tracker/security-check.sh << 'EOF'
#!/bin/bash
# Daily security checks

REPORT_FILE="/var/log/arctic/security-check-$(date +%Y%m%d).log"

echo "=== SECURITY CHECK REPORT $(date) ===" > $REPORT_FILE

# Check file permissions
echo "File permissions check:" >> $REPORT_FILE
ls -la /opt/arctic-shadow-tracker/config.yaml >> $REPORT_FILE
ls -la /data/arctic/ >> $REPORT_FILE

# Check service status
echo "Service status:" >> $REPORT_FILE
systemctl status arctic-shadow-tracker --no-pager >> $REPORT_FILE

# Check for failed login attempts
echo "Failed login attempts (last 24h):" >> $REPORT_FILE
grep "Failed password" /var/log/auth.log | grep "$(date +%b\ %d)" >> $REPORT_FILE

# Check running processes
echo "Running processes:" >> $REPORT_FILE
ps aux | grep arctic >> $REPORT_FILE

# Check network connections
echo "Network connections:" >> $REPORT_FILE
ss -tulpn | grep -E "(python|arctic)" >> $REPORT_FILE

echo "Security check completed: $REPORT_FILE"
EOF

chmod +x /opt/arctic-shadow-tracker/security-check.sh

# Add to daily cron
echo "0 1 * * * /opt/arctic-shadow-tracker/security-check.sh" | sudo crontab -u arctic-user -
```

## Compliance & Best Practices

### GDPR Compliance (for EU maritime data)
- **Data Minimization**: Only collect necessary vessel tracking data
- **Purpose Limitation**: Use data only for Arctic surveillance purposes
- **Storage Limitation**: Automatic data cleanup after retention periods
- **Transparency**: Log all data access and processing activities

### Security Checklist
- [ ] SSH key-based authentication configured
- [ ] Firewall rules implemented and tested
- [ ] Service account with minimal privileges
- [ ] Configuration files secured (600 permissions)
- [ ] Audit logging enabled and configured
- [ ] Backup encryption implemented
- [ ] Data retention policies automated
- [ ] Security monitoring scripts deployed
- [ ] Incident response procedures documented
- [ ] GitHub Secrets properly configured
- [ ] API credentials rotated regularly (quarterly)

This security setup provides comprehensive protection while maintaining operational simplicity for the MVP deployment.