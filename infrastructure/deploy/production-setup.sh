#!/bin/bash
# Arctic Shadow Tracker - Production Deployment Setup Script
# Comprehensive setup for production environment

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
APP_DIR="/app"
USER="arctic"
GROUP="arctic"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."
    
    apt-get update
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        git \
        curl \
        wget \
        htop \
        nano \
        supervisor \
        cron \
        logrotate \
        gdal-bin \
        libgdal-dev \
        libproj-dev \
        libgeos-dev \
        libspatialindex-dev \
        gcc \
        g++ \
        postgresql-client \
        redis-tools \
        nginx \
        certbot \
        python3-certbot-nginx
    
    log_success "System dependencies installed"
}

# Create application user and directories
setup_user_and_directories() {
    log "Setting up user and directories..."
    
    # Create user if it doesn't exist
    if ! id "$USER" &>/dev/null; then
        useradd --system --home-dir "$APP_DIR" --shell /bin/bash --create-home "$USER"
        log_success "Created user: $USER"
    else
        log "User $USER already exists"
    fi
    
    # Create directory structure
    mkdir -p "$APP_DIR"/{data,outputs,logs,config,tmp}
    mkdir -p "$APP_DIR"/data/{ais,satellite,cables,operational/{daily,historical,cumulative,latest}}
    mkdir -p "$APP_DIR"/outputs/{daily_reports,operational_reports,visualizations}
    mkdir -p /var/log/arctic-tracker
    
    # Set permissions
    chown -R "$USER:$GROUP" "$APP_DIR"
    chmod -R 755 "$APP_DIR"
    chmod -R 775 "$APP_DIR"/{data,outputs,logs,tmp}
    
    log_success "User and directories configured"
}

# Install Python dependencies
install_python_dependencies() {
    log "Installing Python dependencies..."
    
    # Upgrade pip
    python3 -m pip install --upgrade pip
    
    # Install requirements
    if [[ -f "$PROJECT_ROOT/config/requirements.txt" ]]; then
        python3 -m pip install -r "$PROJECT_ROOT/config/requirements.txt"
    fi
    
    # Install additional production dependencies
    python3 -m pip install \
        prometheus-client \
        flask \
        requests-oauthlib \
        supervisor \
        psutil \
        gunicorn
    
    log_success "Python dependencies installed"
}

# Copy application files
deploy_application() {
    log "Deploying application files..."
    
    # Copy all files except .git, __pycache__, etc.
    rsync -av \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.pytest_cache' \
        --exclude='arcticshadowtracker_env' \
        --exclude='venv' \
        "$PROJECT_ROOT/" "$APP_DIR/"
    
    # Set ownership
    chown -R "$USER:$GROUP" "$APP_DIR"
    
    log_success "Application deployed"
}

# Setup environment configuration
setup_environment() {
    log "Setting up environment configuration..."
    
    # Create environment file if it doesn't exist
    ENV_FILE="$APP_DIR/config/.env"
    
    if [[ ! -f "$ENV_FILE" ]]; then
        cat > "$ENV_FILE" << EOF
# Arctic Shadow Tracker Production Environment Configuration

# Application Settings
PYTHONPATH=$APP_DIR
PYTHONUNBUFFERED=1
LOG_LEVEL=INFO
DATA_PERSISTENCE_ENABLED=1
VISUALIZATION_ENABLED=1

# Database Configuration (if using external database)
# DATABASE_URL=postgresql://arctic_user:password@localhost:5432/arctic_surveillance

# API Keys (configure as needed)
# COPERNICUS_USERNAME=your_username
# COPERNICUS_PASSWORD=your_password
# AIS_API_KEY=your_ais_api_key

# Alert Configuration
EMAIL_ALERTS_ENABLED=false
WEBHOOK_ALERTS_ENABLED=false
SLACK_ALERTS_ENABLED=false
DAILY_SUMMARY_ENABLED=true

# Email Settings (if enabled)
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USERNAME=your_email@gmail.com
# SMTP_PASSWORD=your_app_password
# EMAIL_FROM=arctic-tracker@your-domain.com
# EMAIL_TO=admin@your-domain.com,ops@your-domain.com

# Webhook Settings (if enabled)
# WEBHOOK_URL=https://your-webhook-endpoint.com/alerts
# WEBHOOK_TOKEN=your_webhook_token

# Slack Settings (if enabled)
# SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
# SLACK_CHANNEL=#arctic-surveillance

# Security Settings
# SECRET_KEY=your_secret_key_here
# JWT_SECRET=your_jwt_secret_here

# Monitoring
PROMETHEUS_PORT=9090
METRICS_ENABLED=true
HEALTH_CHECK_ENABLED=true
EOF
    
        chown "$USER:$GROUP" "$ENV_FILE"
        chmod 600 "$ENV_FILE"
        log_success "Environment configuration created: $ENV_FILE"
        log_warning "Please edit $ENV_FILE to configure your specific settings"
    else
        log "Environment file already exists: $ENV_FILE"
    fi
}

# Setup logging
setup_logging() {
    log "Setting up logging configuration..."
    
    # Create log rotation configuration
    cat > /etc/logrotate.d/arctic-shadow-tracker << EOF
$APP_DIR/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    su $USER $GROUP
}

/var/log/arctic-tracker/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF
    
    # Create systemd journal configuration
    mkdir -p /etc/systemd/journald.conf.d
    cat > /etc/systemd/journald.conf.d/arctic-tracker.conf << EOF
[Journal]
SystemMaxUse=1G
SystemKeepFree=2G
SystemMaxFileSize=100M
MaxRetentionSec=2592000
EOF
    
    log_success "Logging configuration completed"
}

# Setup systemd services
setup_systemd() {
    log "Setting up systemd services..."
    
    # Copy service files
    cp "$APP_DIR/infrastructure/deploy/arctic-shadow-tracker.service" /etc/systemd/system/
    cp "$APP_DIR/infrastructure/deploy/arctic-data-collector.service" /etc/systemd/system/
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable services
    systemctl enable arctic-shadow-tracker.service
    systemctl enable arctic-data-collector.service
    
    log_success "SystemD services configured"
}

# Setup cron jobs
setup_cron() {
    log "Setting up cron jobs..."
    
    # Install crontab for arctic user
    sudo -u "$USER" crontab "$APP_DIR/infrastructure/deploy/crontab-production"
    
    log_success "Cron jobs installed"
}

# Setup supervisor (for Docker deployment)
setup_supervisor() {
    log "Setting up supervisor configuration..."
    
    # Copy supervisor configuration
    cp "$APP_DIR/infrastructure/deploy/supervisord.conf" /etc/supervisor/conf.d/arctic-tracker.conf
    
    # Update supervisor
    if systemctl is-active --quiet supervisor; then
        supervisorctl reread
        supervisorctl update
    fi
    
    log_success "Supervisor configuration completed"
}

# Setup nginx (optional)
setup_nginx() {
    log "Setting up nginx configuration..."
    
    # Create nginx configuration
    cat > /etc/nginx/sites-available/arctic-tracker << EOF
server {
    listen 80;
    server_name arctic-tracker.local;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /metrics {
        proxy_pass http://localhost:9090;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    
    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
EOF
    
    # Enable site (optional - only if nginx is to be used)
    # ln -sf /etc/nginx/sites-available/arctic-tracker /etc/nginx/sites-enabled/
    
    log_success "Nginx configuration created (not enabled by default)"
}

# Create backup script
create_backup_script() {
    log "Creating backup script..."
    
    cat > "$APP_DIR/infrastructure/deploy/backup_manager.py" << 'EOF'
#!/usr/bin/env python3
"""Simple backup manager for Arctic Shadow Tracker data."""

import sys
import os
import shutil
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def perform_daily_backup():
    """Perform daily backup of critical data."""
    try:
        app_dir = Path('/app')
        backup_dir = app_dir / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        # Create backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f'arctic_backup_{timestamp}.tar.gz'
        
        # Create backup
        with tarfile.open(backup_file, 'w:gz') as tar:
            # Backup operational data (last 7 days)
            operational_dir = app_dir / 'data' / 'operational'
            if operational_dir.exists():
                tar.add(operational_dir, arcname='operational')
            
            # Backup configuration
            config_dir = app_dir / 'config'
            if config_dir.exists():
                tar.add(config_dir, arcname='config')
            
            # Backup recent logs (last 24 hours)
            logs_dir = app_dir / 'logs'
            if logs_dir.exists():
                for log_file in logs_dir.glob('*.log'):
                    if (datetime.now().timestamp() - log_file.stat().st_mtime) < 86400:
                        tar.add(log_file, arcname=f'logs/{log_file.name}')
        
        # Clean old backups (keep 7 days)
        cutoff_date = datetime.now() - timedelta(days=7)
        for old_backup in backup_dir.glob('arctic_backup_*.tar.gz'):
            if datetime.fromtimestamp(old_backup.stat().st_mtime) < cutoff_date:
                old_backup.unlink()
        
        print(f"Backup completed: {backup_file}")
        logger.info(f"Daily backup completed: {backup_file}")
        
    except Exception as e:
        print(f"Backup failed: {e}")
        logger.error(f"Daily backup failed: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    perform_daily_backup()
EOF
    
    chmod +x "$APP_DIR/infrastructure/deploy/backup_manager.py"
    chown "$USER:$GROUP" "$APP_DIR/infrastructure/deploy/backup_manager.py"
    
    log_success "Backup script created"
}

# Setup firewall (basic)
setup_firewall() {
    log "Setting up firewall rules..."
    
    # Enable UFW if available
    if command -v ufw &> /dev/null; then
        ufw --force enable
        ufw allow ssh
        ufw allow 80/tcp
        ufw allow 443/tcp
        # ufw allow 8000/tcp  # Uncomment if you want direct access to app
        # ufw allow 9090/tcp  # Uncomment if you want direct access to metrics
        log_success "Firewall configured"
    else
        log_warning "UFW not available, skipping firewall setup"
    fi
}

# Test deployment
test_deployment() {
    log "Testing deployment..."
    
    # Test Python imports
    if sudo -u "$USER" python3 -c "import sys; sys.path.append('$APP_DIR'); from utils.daily_operations import DailyOperations; print('Import test: OK')"; then
        log_success "Python imports test passed"
    else
        log_error "Python imports test failed"
        return 1
    fi
    
    # Test health monitor
    if sudo -u "$USER" python3 "$APP_DIR/infrastructure/deploy/health_monitor.py" --docker; then
        log_success "Health monitor test passed"
    else
        log_warning "Health monitor test had issues"
    fi
    
    # Test alert system
    if sudo -u "$USER" python3 "$APP_DIR/infrastructure/deploy/alert_system.py" --test; then
        log_success "Alert system test passed"
    else
        log_warning "Alert system test had issues (may be due to missing configuration)"
    fi
    
    log_success "Deployment testing completed"
}

# Start services
start_services() {
    log "Starting services..."
    
    # Start and enable cron
    systemctl enable cron
    systemctl start cron
    
    # Start systemd services
    systemctl start arctic-shadow-tracker.service
    systemctl start arctic-data-collector.service
    
    # Check service status
    if systemctl is-active --quiet arctic-shadow-tracker.service; then
        log_success "Arctic Shadow Tracker service started"
    else
        log_warning "Arctic Shadow Tracker service failed to start"
    fi
    
    if systemctl is-active --quiet arctic-data-collector.service; then
        log_success "Arctic Data Collector service started"
    else
        log_warning "Arctic Data Collector service failed to start"
    fi
}

# Print deployment summary
print_summary() {
    log "Deployment Summary"
    echo "=================="
    echo ""
    echo "Arctic Shadow Tracker has been deployed to: $APP_DIR"
    echo ""
    echo "Services:"
    echo "  - arctic-shadow-tracker.service (main surveillance)"
    echo "  - arctic-data-collector.service (data collection)"
    echo ""
    echo "Configuration:"
    echo "  - Environment: $APP_DIR/config/.env"
    echo "  - Logs: $APP_DIR/logs/"
    echo "  - Data: $APP_DIR/data/"
    echo ""
    echo "Useful commands:"
    echo "  - View logs: journalctl -u arctic-shadow-tracker -f"
    echo "  - Service status: systemctl status arctic-shadow-tracker"
    echo "  - Health check: sudo -u $USER python3 $APP_DIR/infrastructure/deploy/health_monitor.py"
    echo "  - Manual run: sudo -u $USER python3 -m utils.daily_operations"
    echo ""
    echo "Next steps:"
    echo "  1. Edit $APP_DIR/config/.env with your API keys and alert settings"
    echo "  2. Configure external data sources (Copernicus, AIS feeds)"
    echo "  3. Set up monitoring dashboards (Grafana)"
    echo "  4. Test alert notifications"
    echo ""
    log_success "Arctic Shadow Tracker production deployment complete!"
}

# Main execution
main() {
    log "Starting Arctic Shadow Tracker production deployment..."
    
    check_root
    install_dependencies
    setup_user_and_directories
    install_python_dependencies
    deploy_application
    setup_environment
    setup_logging
    setup_systemd
    setup_cron
    setup_supervisor
    setup_nginx
    create_backup_script
    setup_firewall
    test_deployment
    start_services
    print_summary
}

# Execute main function
main "$@"