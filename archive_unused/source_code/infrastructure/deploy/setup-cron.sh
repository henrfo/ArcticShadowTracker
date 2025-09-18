#!/bin/bash
# Arctic Shadow Tracker - Production Cron Setup Script

set -e

# Configuration
APP_DIR="/app"
CRON_FILE="$APP_DIR/infrastructure/deploy/crontab-production"
USER="arctic"
LOG_DIR="$APP_DIR/logs"

echo "Setting up Arctic Shadow Tracker production cron jobs..."

# Ensure log directory exists
mkdir -p "$LOG_DIR"
chown "$USER:$USER" "$LOG_DIR"

# Backup existing crontab if it exists
if crontab -u "$USER" -l >/dev/null 2>&1; then
    echo "Backing up existing crontab..."
    crontab -u "$USER" -l > "$LOG_DIR/crontab_backup_$(date +%Y%m%d_%H%M%S).bak"
fi

# Install new crontab
echo "Installing Arctic Shadow Tracker crontab..."
crontab -u "$USER" "$CRON_FILE"

# Verify installation
echo "Verifying cron installation..."
if crontab -u "$USER" -l | grep -q "Arctic Shadow Tracker"; then
    echo "✓ Cron jobs installed successfully"
    echo ""
    echo "Installed cron jobs:"
    crontab -u "$USER" -l | grep -v "^#" | grep -v "^$" | while read line; do
        echo "  - $line"
    done
else
    echo "✗ Cron installation failed"
    exit 1
fi

# Ensure cron service is running
if systemctl is-active --quiet cron; then
    echo "✓ Cron service is running"
elif systemctl is-active --quiet crond; then
    echo "✓ Crond service is running"
else
    echo "⚠ Warning: Cron service may not be running"
    echo "Please ensure cron is started: systemctl start cron"
fi

echo ""
echo "Production cron setup complete!"
echo "Logs will be written to: $LOG_DIR"
echo "Monitor with: tail -f $LOG_DIR/cron_daily_*.log"