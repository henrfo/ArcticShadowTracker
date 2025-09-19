#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Alert and Notification System
Handles critical threat alerts, system notifications, and daily summaries.
"""

import sys
import os
import json
import time
import smtplib
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

class AlertSystem:
    """Comprehensive alert and notification system for Arctic Shadow Tracker."""
    
    def __init__(self):
        """Initialize alert system with configuration."""
        self.config = self._load_configuration()
        self.data_dir = project_root / 'data'
        self.logs_dir = project_root / 'logs'
        
        # Alert thresholds
        self.thresholds = {
            'critical_threat_distance_km': 1.0,
            'high_threat_distance_km': 2.0,
            'dark_vessel_near_cable': True,
            'system_down_minutes': 5,
            'data_stale_hours': 6
        }
        
        # Track sent alerts to prevent spam
        self.sent_alerts = {}
        self.alert_cooldown_minutes = 30
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load alert configuration from environment and config files."""
        config = {
            # Email configuration
            'email_enabled': os.getenv('EMAIL_ALERTS_ENABLED', 'false').lower() == 'true',
            'smtp_server': os.getenv('SMTP_SERVER', 'localhost'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'smtp_username': os.getenv('SMTP_USERNAME', ''),
            'smtp_password': os.getenv('SMTP_PASSWORD', ''),
            'email_from': os.getenv('EMAIL_FROM', 'arctic-tracker@localhost'),
            'email_to': os.getenv('EMAIL_TO', 'admin@localhost').split(','),
            'email_use_tls': os.getenv('SMTP_USE_TLS', 'true').lower() == 'true',
            
            # Webhook configuration
            'webhook_enabled': os.getenv('WEBHOOK_ALERTS_ENABLED', 'false').lower() == 'true',
            'webhook_url': os.getenv('WEBHOOK_URL', ''),
            'webhook_token': os.getenv('WEBHOOK_TOKEN', ''),
            
            # Slack configuration
            'slack_enabled': os.getenv('SLACK_ALERTS_ENABLED', 'false').lower() == 'true',
            'slack_webhook_url': os.getenv('SLACK_WEBHOOK_URL', ''),
            'slack_channel': os.getenv('SLACK_CHANNEL', '#arctic-surveillance'),
            
            # Alert levels
            'alert_critical_enabled': True,
            'alert_warning_enabled': True,
            'alert_info_enabled': False,
            'daily_summary_enabled': True
        }
        
        return config
    
    def send_critical_threat_alert(self, threat_data: Dict[str, Any]) -> bool:
        """
        Send immediate alert for critical maritime threats.
        
        Args:
            threat_data: Dictionary containing threat information
            
        Returns:
            True if alert was sent successfully
        """
        alert_key = f"critical_threat_{threat_data.get('vessel_id', 'unknown')}"
        
        # Check cooldown to prevent spam
        if self._is_alert_on_cooldown(alert_key):
            logger.info(f"Alert {alert_key} on cooldown, skipping")
            return False
        
        # Prepare alert message
        subject = f"🚨 CRITICAL MARITIME THREAT - Arctic Waters"
        
        message_body = self._format_critical_threat_message(threat_data)
        
        # Send via all configured channels
        success = True
        
        if self.config['email_enabled']:
            success &= self._send_email_alert(subject, message_body, priority='high')
        
        if self.config['webhook_enabled']:
            success &= self._send_webhook_alert(subject, message_body, 'critical')
        
        if self.config['slack_enabled']:
            success &= self._send_slack_alert(subject, message_body, 'critical')
        
        if success:
            self._mark_alert_sent(alert_key)
            logger.info(f"Critical threat alert sent: {threat_data.get('vessel_id')}")
        
        return success
    
    def send_system_health_alert(self, health_status: Dict[str, Any]) -> bool:
        """
        Send alert for system health issues.
        
        Args:
            health_status: System health status from health monitor
            
        Returns:
            True if alert was sent successfully
        """
        if health_status.get('overall') not in ['WARNING', 'CRITICAL']:
            return True
        
        alert_key = f"system_health_{health_status.get('overall', 'unknown')}"
        
        # Check cooldown
        if self._is_alert_on_cooldown(alert_key):
            return False
        
        # Prepare alert message
        severity = health_status.get('overall', 'UNKNOWN')
        emoji = '⚠️' if severity == 'WARNING' else '🔴'
        subject = f"{emoji} Arctic Tracker System {severity}"
        
        message_body = self._format_system_health_message(health_status)
        
        # Send alerts (only for critical issues via all channels)
        success = True
        
        if severity == 'CRITICAL':
            if self.config['email_enabled']:
                success &= self._send_email_alert(subject, message_body, priority='high')
            
            if self.config['webhook_enabled']:
                success &= self._send_webhook_alert(subject, message_body, 'critical')
            
            if self.config['slack_enabled']:
                success &= self._send_slack_alert(subject, message_body, 'warning')
        
        elif severity == 'WARNING' and self.config['alert_warning_enabled']:
            # Only send warnings via webhook/Slack (less intrusive)
            if self.config['webhook_enabled']:
                success &= self._send_webhook_alert(subject, message_body, 'warning')
            
            if self.config['slack_enabled']:
                success &= self._send_slack_alert(subject, message_body, 'warning')
        
        if success:
            self._mark_alert_sent(alert_key)
            logger.info(f"System health alert sent: {severity}")
        
        return success
    
    def send_daily_summary(self, summary_data: Dict[str, Any]) -> bool:
        """
        Send daily surveillance summary.
        
        Args:
            summary_data: Daily summary from operations
            
        Returns:
            True if summary was sent successfully
        """
        if not self.config['daily_summary_enabled']:
            return True
        
        date_str = summary_data.get('date', datetime.now().strftime('%Y-%m-%d'))
        subject = f"📊 Arctic Surveillance Daily Summary - {date_str}"
        
        message_body = self._format_daily_summary_message(summary_data)
        
        # Send via email and webhook (not Slack to avoid spam)
        success = True
        
        if self.config['email_enabled']:
            success &= self._send_email_alert(subject, message_body, priority='normal')
        
        if self.config['webhook_enabled']:
            success &= self._send_webhook_alert(subject, message_body, 'info')
        
        if success:
            logger.info(f"Daily summary sent for {date_str}")
        
        return success
    
    def _format_critical_threat_message(self, threat_data: Dict[str, Any]) -> str:
        """Format critical threat alert message."""
        vessel_id = threat_data.get('vessel_id', 'Unknown')
        vessel_name = threat_data.get('vessel_name', 'Unknown')
        threat_level = threat_data.get('threat_level', 'UNKNOWN')
        distance = threat_data.get('distance_to_cable_km', 0)
        cable_name = threat_data.get('closest_cable', 'Unknown')
        has_ais = threat_data.get('has_ais', False)
        lat = threat_data.get('latitude', 0)
        lon = threat_data.get('longitude', 0)
        timestamp = threat_data.get('timestamp', datetime.now().isoformat())
        
        ais_status = "✅ AIS Active" if has_ais else "❌ DARK VESSEL (No AIS)"
        
        message = f"""
CRITICAL MARITIME THREAT DETECTED

🚢 Vessel Information:
   • ID: {vessel_id}
   • Name: {vessel_name}
   • AIS Status: {ais_status}
   • Threat Level: {threat_level}

📍 Location:
   • Coordinates: {lat:.4f}, {lon:.4f}
   • Nearest Cable: {cable_name}
   • Distance to Cable: {distance:.2f} km

⏰ Detection Time: {timestamp}

🔍 Assessment:
   This vessel is operating {"without AIS transponder " if not has_ais else ""}near critical submarine cable infrastructure in Arctic waters. Immediate investigation recommended.

📋 Recommended Actions:
   1. Verify vessel identity and intentions
   2. Monitor vessel movement patterns
   3. Contact vessel if possible
   4. Alert relevant maritime authorities
   5. Increase surveillance coverage in area

This is an automated alert from Arctic Shadow Tracker surveillance system.
        """.strip()
        
        return message
    
    def _format_system_health_message(self, health_status: Dict[str, Any]) -> str:
        """Format system health alert message."""
        overall = health_status.get('overall', 'UNKNOWN')
        alerts = health_status.get('alerts', [])
        last_check = health_status.get('last_check', 'Unknown')
        metrics = health_status.get('metrics', {})
        
        message = f"""
ARCTIC TRACKER SYSTEM HEALTH ALERT

🔍 Overall Status: {overall}
⏰ Last Check: {last_check}

"""
        
        if alerts:
            message += "⚠️ Active Alerts:\n"
            for alert in alerts[:10]:  # Limit to first 10 alerts
                message += f"   • {alert}\n"
            
            if len(alerts) > 10:
                message += f"   ... and {len(alerts) - 10} more alerts\n"
            message += "\n"
        
        if metrics:
            message += "📊 System Metrics:\n"
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    if 'percent' in key.lower():
                        message += f"   • {key.replace('_', ' ').title()}: {value:.1f}%\n"
                    else:
                        message += f"   • {key.replace('_', ' ').title()}: {value}\n"
            message += "\n"
        
        message += """
🔧 Recommended Actions:
   1. Check system logs for detailed error information
   2. Verify data pipeline status
   3. Monitor resource usage
   4. Restart services if necessary

This is an automated alert from Arctic Shadow Tracker health monitor.
        """.strip()
        
        return message
    
    def _format_daily_summary_message(self, summary_data: Dict[str, Any]) -> str:
        """Format daily summary message."""
        date_str = summary_data.get('date', 'Unknown')
        status = summary_data.get('status', 'Unknown')
        data_collected = summary_data.get('data_collected', {})
        summary = summary_data.get('summary', {})
        performance = summary_data.get('performance', {})
        
        message = f"""
ARCTIC SURVEILLANCE DAILY SUMMARY

📅 Date: {date_str}
✅ Mission Status: {status}

📊 Data Collection:
   • AIS Vessels Tracked: {data_collected.get('ais_vessels', 0)}
   • SAR Detections: {data_collected.get('sar_detections', 0)}
   • Threats Identified: {data_collected.get('threats', 0)}

🔍 Threat Assessment:
   • Total Threats: {summary.get('total_threats', 0)}
   • Critical Threats: {summary.get('critical_threats', 0)}
   • High Priority: {summary.get('high_threats', 0)}
   • Dark Vessels: {summary.get('dark_vessels', 0)}

⚡ Performance:
   • AIS Collection: {performance.get('ais_collection_seconds', 0):.1f}s
   • SAR Processing: {performance.get('sar_processing_seconds', 0):.1f}s
   • Threat Detection: {performance.get('threat_detection_seconds', 0):.1f}s

🌊 Arctic Waters Status: {"⚠️ THREATS DETECTED" if summary.get('total_threats', 0) > 0 else "✅ ALL CLEAR"}

This automated report covers 24-hour surveillance operations in Arctic maritime zones.
        """.strip()
        
        return message
    
    def _send_email_alert(self, subject: str, body: str, priority: str = 'normal') -> bool:
        """Send email alert."""
        try:
            if not self.config['email_enabled']:
                return True
            
            msg = MIMEMultipart()
            msg['From'] = self.config['email_from']
            msg['To'] = ', '.join(self.config['email_to'])
            msg['Subject'] = subject
            
            if priority == 'high':
                msg['X-Priority'] = '1'
                msg['Importance'] = 'high'
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port']) as server:
                if self.config['email_use_tls']:
                    server.starttls()
                
                if self.config['smtp_username'] and self.config['smtp_password']:
                    server.login(self.config['smtp_username'], self.config['smtp_password'])
                
                server.send_message(msg)
            
            logger.info(f"Email alert sent: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    def _send_webhook_alert(self, subject: str, body: str, level: str) -> bool:
        """Send webhook alert."""
        try:
            if not self.config['webhook_enabled'] or not self.config['webhook_url']:
                return True
            
            payload = {
                'subject': subject,
                'message': body,
                'level': level,
                'timestamp': datetime.now().isoformat(),
                'source': 'arctic-shadow-tracker'
            }
            
            headers = {'Content-Type': 'application/json'}
            
            if self.config['webhook_token']:
                headers['Authorization'] = f"Bearer {self.config['webhook_token']}"
            
            response = requests.post(
                self.config['webhook_url'],
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Webhook alert sent: {subject}")
                return True
            else:
                logger.error(f"Webhook alert failed: {response.status_code}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False
    
    def _send_slack_alert(self, subject: str, body: str, level: str) -> bool:
        """Send Slack alert."""
        try:
            if not self.config['slack_enabled'] or not self.config['slack_webhook_url']:
                return True
            
            # Format message for Slack
            color = {
                'critical': '#ff0000',
                'warning': '#ffaa00',
                'info': '#0066cc'
            }.get(level, '#cccccc')
            
            slack_payload = {
                'channel': self.config['slack_channel'],
                'username': 'Arctic Shadow Tracker',
                'icon_emoji': ':satellite:',
                'attachments': [{
                    'color': color,
                    'title': subject,
                    'text': body[:2000],  # Slack message limit
                    'ts': int(datetime.now().timestamp())
                }]
            }
            
            response = requests.post(
                self.config['slack_webhook_url'],
                json=slack_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Slack alert sent: {subject}")
                return True
            else:
                logger.error(f"Slack alert failed: {response.status_code}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
    
    def _is_alert_on_cooldown(self, alert_key: str) -> bool:
        """Check if alert is on cooldown to prevent spam."""
        now = datetime.now()
        last_sent = self.sent_alerts.get(alert_key)
        
        if last_sent is None:
            return False
        
        time_diff = (now - last_sent).total_seconds() / 60
        return time_diff < self.alert_cooldown_minutes
    
    def _mark_alert_sent(self, alert_key: str):
        """Mark alert as sent with timestamp."""
        self.sent_alerts[alert_key] = datetime.now()
        
        # Clean up old entries (keep last 24 hours)
        cutoff = datetime.now() - timedelta(hours=24)
        self.sent_alerts = {
            k: v for k, v in self.sent_alerts.items() 
            if v > cutoff
        }
    
    def test_alert_system(self) -> Dict[str, bool]:
        """Test all alert channels."""
        test_results = {}
        
        test_subject = "🧪 Arctic Tracker Alert System Test"
        test_message = f"""
This is a test message from Arctic Shadow Tracker alert system.

Time: {datetime.now().isoformat()}
System: Operational
Status: Testing alert delivery

If you receive this message, the alert system is working correctly.
        """.strip()
        
        if self.config['email_enabled']:
            test_results['email'] = self._send_email_alert(test_subject, test_message)
        
        if self.config['webhook_enabled']:
            test_results['webhook'] = self._send_webhook_alert(test_subject, test_message, 'info')
        
        if self.config['slack_enabled']:
            test_results['slack'] = self._send_slack_alert(test_subject, test_message, 'info')
        
        logger.info(f"Alert system test results: {test_results}")
        return test_results
    
    def run_daemon(self, check_interval: int = 60):
        """Run alert system as daemon to monitor for threats."""
        logger.info(f"Starting alert system daemon (check interval: {check_interval}s)")
        
        while True:
            try:
                # Check for new threats
                self._check_for_new_threats()
                
                # Check system health
                self._check_system_health_alerts()
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("Alert system daemon stopped")
                break
            except Exception as e:
                logger.error(f"Alert system daemon error: {e}")
                time.sleep(60)
    
    def _check_for_new_threats(self):
        """Check for new threats in latest data."""
        try:
            threats_file = self.data_dir / 'operational' / 'latest' / 'threats_latest.json'
            
            if not threats_file.exists():
                return
            
            with open(threats_file, 'r') as f:
                threats = json.load(f)
            
            for threat in threats:
                if threat.get('threat_level') == 'CRITICAL':
                    self.send_critical_threat_alert(threat)
                    
        except Exception as e:
            logger.error(f"Failed to check for new threats: {e}")
    
    def _check_system_health_alerts(self):
        """Check system health and send alerts if needed."""
        try:
            from infrastructure.deploy.health_monitor import HealthMonitor
            
            monitor = HealthMonitor()
            health_status = monitor.check_system_health()
            
            if health_status.get('overall') in ['WARNING', 'CRITICAL']:
                self.send_system_health_alert(health_status)
                
        except Exception as e:
            logger.error(f"Failed to check system health for alerts: {e}")


def test_alert_system():
    """Test alert system function for cron."""
    try:
        alert_system = AlertSystem()
        results = alert_system.test_alert_system()
        
        print("Alert System Test Results:")
        for channel, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {channel}: {status}")
        
        return all(results.values())
        
    except Exception as e:
        logger.error(f"Alert system test failed: {e}")
        print(f"Alert system test failed: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Arctic Shadow Tracker Alert System")
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--interval', type=int, default=60, help='Check interval in seconds (daemon mode)')
    parser.add_argument('--test', action='store_true', help='Test all alert channels')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.test:
        success = test_alert_system()
        sys.exit(0 if success else 1)
    elif args.daemon:
        alert_system = AlertSystem()
        alert_system.run_daemon(args.interval)
    else:
        print("Use --test to test alerts or --daemon to run as daemon")