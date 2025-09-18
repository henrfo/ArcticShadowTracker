#!/bin/bash
# Arctic Shadow Tracker - SystemD Service Setup Script

set -e

# Configuration
SERVICE_DIR="/etc/systemd/system"
APP_DIR="/app"
USER="arctic"
GROUP="arctic"

echo "Setting up Arctic Shadow Tracker systemd services..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)"
   exit 1
fi

# Create user if it doesn't exist
if ! id "$USER" &>/dev/null; then
    echo "Creating user: $USER"
    useradd --system --home-dir "$APP_DIR" --shell /bin/bash --create-home "$USER"
fi

# Ensure proper ownership
chown -R "$USER:$GROUP" "$APP_DIR"

# Copy service files
echo "Installing systemd service files..."
cp "$APP_DIR/infrastructure/deploy/arctic-shadow-tracker.service" "$SERVICE_DIR/"
cp "$APP_DIR/infrastructure/deploy/arctic-data-collector.service" "$SERVICE_DIR/"

# Set proper permissions
chmod 644 "$SERVICE_DIR/arctic-shadow-tracker.service"
chmod 644 "$SERVICE_DIR/arctic-data-collector.service"

# Reload systemd daemon
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable services
echo "Enabling Arctic Shadow Tracker services..."
systemctl enable arctic-shadow-tracker.service
systemctl enable arctic-data-collector.service

# Create log rotation configuration
echo "Setting up log rotation..."
cat > /etc/logrotate.d/arctic-shadow-tracker << EOF
/app/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    su arctic arctic
}
EOF

# Start services
echo "Starting Arctic Shadow Tracker services..."
systemctl start arctic-shadow-tracker.service
systemctl start arctic-data-collector.service

# Check service status
echo ""
echo "Service Status:"
echo "==============="
systemctl --no-pager status arctic-shadow-tracker.service --lines=5
echo ""
systemctl --no-pager status arctic-data-collector.service --lines=5

echo ""
echo "SystemD setup complete!"
echo ""
echo "Useful commands:"
echo "  View logs:        journalctl -u arctic-shadow-tracker -f"
echo "  Service status:   systemctl status arctic-shadow-tracker"
echo "  Restart service:  systemctl restart arctic-shadow-tracker"
echo "  Stop service:     systemctl stop arctic-shadow-tracker"
echo ""
echo "Data will be stored in: $APP_DIR/data"
echo "Logs will be written to: $APP_DIR/logs and journald"