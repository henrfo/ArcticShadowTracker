#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Live Dashboard Server

Simple web server that serves the live Arctic surveillance dashboard
with automatic refresh capabilities.
"""

import http.server
import socketserver
import os
import time
import threading
import webbrowser
from pathlib import Path
import subprocess
import sys

class LiveDashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler for serving the live dashboard"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/' or self.path == '/dashboard':
            # Serve the main dashboard
            self.serve_dashboard()
        elif self.path == '/api/status':
            # API endpoint for dashboard status
            self.serve_status()
        elif self.path == '/api/latest':
            # API endpoint for latest data
            self.serve_latest_data()
        else:
            # Serve static files normally
            super().do_GET()
    
    def serve_dashboard(self):
        """Serve the main live dashboard page"""
        dashboard_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Arctic Shadow Tracker - Live Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            background: #1a1a1a;
            color: white;
        }
        .header {
            background: #2c3e50;
            padding: 15px;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        }
        .header h1 {
            margin: 0;
            color: #3498db;
        }
        .status {
            background: #34495e;
            padding: 10px;
            text-align: center;
            font-size: 14px;
        }
        .status.online {
            background: #27ae60;
        }
        .status.offline {
            background: #e74c3c;
        }
        .dashboard-container {
            position: relative;
            height: calc(100vh - 120px);
            overflow: hidden;
        }
        .dashboard-frame {
            width: 100%;
            height: 100%;
            border: none;
            background: white;
        }
        .loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 18px;
            color: #3498db;
        }
        .controls {
            position: fixed;
            top: 80px;
            right: 20px;
            background: rgba(44, 62, 80, 0.9);
            padding: 15px;
            border-radius: 8px;
            z-index: 1000;
        }
        .control-button {
            background: #3498db;
            color: white;
            border: none;
            padding: 8px 16px;
            margin: 5px;
            border-radius: 4px;
            cursor: pointer;
        }
        .control-button:hover {
            background: #2980b9;
        }
        .stats {
            font-size: 12px;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🌊 Arctic Shadow Tracker - Live Surveillance</h1>
        <div id="lastUpdate">Loading...</div>
    </div>
    
    <div id="status" class="status">
        <span id="statusText">Connecting to surveillance system...</span>
    </div>
    
    <div class="controls">
        <button class="control-button" onclick="refreshDashboard()">🔄 Refresh Now</button>
        <button class="control-button" onclick="toggleAutoRefresh()" id="autoRefreshBtn">⏸️ Pause Auto-refresh</button>
        <div class="stats">
            <div>Auto-refresh: <span id="refreshInterval">30s</span></div>
            <div>Last refresh: <span id="lastRefresh">Never</span></div>
            <div>Status: <span id="systemStatus">Unknown</span></div>
        </div>
    </div>
    
    <div class="dashboard-container">
        <div id="loading" class="loading">Loading Arctic surveillance dashboard...</div>
        <iframe id="dashboardFrame" class="dashboard-frame" style="display: none;"></iframe>
    </div>

    <script>
        let autoRefreshEnabled = true;
        let refreshInterval = 30; // seconds
        let refreshTimer;
        
        function updateStatus(online, message, lastUpdate) {
            const statusDiv = document.getElementById('status');
            const statusText = document.getElementById('statusText');
            const lastUpdateDiv = document.getElementById('lastUpdate');
            
            statusDiv.className = 'status ' + (online ? 'online' : 'offline');
            statusText.textContent = message;
            lastUpdateDiv.textContent = 'Last Update: ' + lastUpdate;
            
            document.getElementById('systemStatus').textContent = online ? 'Online' : 'Offline';
        }
        
        function refreshDashboard() {
            console.log('Refreshing dashboard...');
            document.getElementById('loading').style.display = 'block';
            document.getElementById('dashboardFrame').style.display = 'none';
            
            // Find the latest dashboard file
            fetch('/api/latest')
                .then(response => response.json())
                .then(data => {
                    if (data.dashboard_path) {
                        const frame = document.getElementById('dashboardFrame');
                        frame.src = data.dashboard_dir + '/' + data.dashboard_path + '?t=' + new Date().getTime();
                        frame.onload = function() {
                            document.getElementById('loading').style.display = 'none';
                            frame.style.display = 'block';
                        };
                        
                        updateStatus(true, `🟢 Active surveillance - ${data.vessel_count} vessels tracked`, data.last_update);
                        document.getElementById('lastRefresh').textContent = new Date().toLocaleTimeString();
                    } else {
                        updateStatus(false, '🔴 No dashboard available', 'Never');
                    }
                })
                .catch(error => {
                    console.error('Error refreshing dashboard:', error);
                    updateStatus(false, '🔴 Connection error', 'Error');
                });
        }
        
        function toggleAutoRefresh() {
            autoRefreshEnabled = !autoRefreshEnabled;
            const btn = document.getElementById('autoRefreshBtn');
            
            if (autoRefreshEnabled) {
                btn.textContent = '⏸️ Pause Auto-refresh';
                startAutoRefresh();
            } else {
                btn.textContent = '▶️ Resume Auto-refresh';
                clearTimeout(refreshTimer);
            }
        }
        
        function startAutoRefresh() {
            if (autoRefreshEnabled) {
                refreshTimer = setTimeout(() => {
                    refreshDashboard();
                    startAutoRefresh();
                }, refreshInterval * 1000);
            }
        }
        
        // Initialize
        refreshDashboard();
        startAutoRefresh();
        
        // Update refresh interval display
        document.getElementById('refreshInterval').textContent = refreshInterval + 's';
    </script>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(dashboard_html.encode())
    
    def serve_status(self):
        """Serve system status"""
        try:
            # Check if surveillance system is running
            dashboard_dir = Path('arctic_intelligence')
            latest_dashboard = dashboard_dir / 'arctic_dashboard_latest.html'
            
            status = {
                'online': latest_dashboard.exists(),
                'last_update': 'Unknown',
                'vessel_count': 0
            }
            
            if latest_dashboard.exists():
                # Get file modification time
                mtime = latest_dashboard.stat().st_mtime
                status['last_update'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
                
                # Try to get vessel count from CSV
                csv_file = dashboard_dir / 'vessel_positions.csv'
                if csv_file.exists():
                    with open(csv_file, 'r') as f:
                        lines = f.readlines()
                        status['vessel_count'] = max(0, len(lines) - 1)  # Subtract header
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            import json
            self.wfile.write(json.dumps(status).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(f'{{"error": "{str(e)}"}}'.encode())
    
    def serve_latest_data(self):
        """Serve latest dashboard data"""
        try:
            dashboard_dir = Path('arctic_intelligence')
            
            # Find the latest dashboard file (prefer enhanced with tracks)
            enhanced_files = list(dashboard_dir.glob('arctic_dashboard_with_tracks_*.html'))
            basic_files = list(dashboard_dir.glob('arctic_dashboard_*.html'))
            
            # Prefer enhanced dashboard if available
            if enhanced_files:
                dashboard_files = enhanced_files
            else:
                dashboard_files = basic_files
            
            latest_dashboard = None
            if dashboard_files:
                # Get the most recent dashboard file
                latest_dashboard = max(dashboard_files, key=lambda x: x.stat().st_mtime)
            
            response = {
                'dashboard_path': None,
                'last_update': 'Never',
                'vessel_count': 0
            }
            
            if latest_dashboard and latest_dashboard.exists():
                response['dashboard_path'] = str(latest_dashboard.name)  # Just the filename
                response['dashboard_dir'] = 'arctic_intelligence'
                mtime = latest_dashboard.stat().st_mtime
                response['last_update'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
                
                # Get vessel count
                csv_file = dashboard_dir / 'vessel_positions.csv'
                if csv_file.exists():
                    with open(csv_file, 'r') as f:
                        lines = f.readlines()
                        response['vessel_count'] = max(0, len(lines) - 1)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            import json
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(f'{{"error": "{str(e)}"}}'.encode())

def run_surveillance_background():
    """Run surveillance system in background"""
    try:
        while True:
            print("🌊 Running surveillance cycle...")
            result = subprocess.run([sys.executable, 'arctic_shadow_streamer.py', 'test'], 
                                  capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                print("✅ Surveillance cycle completed successfully")
            else:
                print(f"❌ Surveillance cycle failed: {result.stderr}")
            
            # Wait 30 seconds before next cycle
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("🛑 Background surveillance stopped")
    except Exception as e:
        print(f"❌ Background surveillance error: {e}")

def main():
    """Start the live dashboard server"""
    PORT = 8081
    
    print("🌊 Arctic Shadow Tracker - Live Dashboard Server")
    print("=" * 50)
    
    # Start background surveillance
    surveillance_thread = threading.Thread(target=run_surveillance_background, daemon=True)
    surveillance_thread.start()
    print(f"🔄 Background surveillance started")
    
    # Start web server
    with socketserver.TCPServer(("", PORT), LiveDashboardHandler) as httpd:
        url = f"http://localhost:{PORT}/dashboard"
        print(f"🌐 Live dashboard server running at: {url}")
        print("💡 The dashboard will auto-refresh every 30 seconds")
        print("🔄 Background surveillance updates every 30 seconds")
        print("⚡ Press Ctrl+C to stop the server")
        print()
        
        # Open browser automatically
        try:
            webbrowser.open(url)
            print(f"🚀 Opened dashboard in your default browser")
        except Exception as e:
            print(f"💡 Please open {url} in your browser")
        
        print()
        print("Dashboard Features:")
        print("• 🗺️  Real-time Arctic vessel tracking")
        print("• 🚢 Foreign vessel monitoring") 
        print("• 🔍 Dark vessel detection")
        print("• ⚠️  Submarine cable proximity alerts")
        print("• 📊 Live statistics and updates")
        print()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down live dashboard server...")

if __name__ == "__main__":
    main()