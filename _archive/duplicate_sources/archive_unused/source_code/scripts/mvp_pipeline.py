#!/usr/bin/env python3
"""
MVP Arctic Data Collection Pipeline
Coordinates all three data collection agents to prove we can collect real Arctic maritime data.

This is the deliverable: proof the pipeline works - real ships on a real map with real satellite imagery.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MVPPipelineCoordinator:
    """Coordinates all data collection agents for the MVP pipeline."""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = Path('data/mvp_pipeline')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Pipeline status tracking
        self.pipeline_status = {
            'timestamp': datetime.now().isoformat(),
            'pipeline_id': f"mvp_run_{self.timestamp}",
            'status': 'starting',
            'agents': {
                'barentswatch': {'status': 'pending', 'vessels': 0, 'errors': []},
                'aisstream': {'status': 'pending', 'vessels': 0, 'errors': []},
                'satellite': {'status': 'pending', 'products': 0, 'errors': []}
            },
            'summary': {
                'total_vessels': 0,
                'unique_mmsi': 0,
                'satellite_images': 0,
                'success': False
            },
            'next_steps': []
        }
    
    def run_pipeline(self):
        """Run the complete MVP pipeline."""
        print("🚀 MVP Arctic Data Collection Pipeline")
        print("=" * 60)
        print("Goal: Prove we can collect real Arctic maritime data")
        print("- Real ships from BarentsWatch (Norwegian official)")
        print("- Real ships from aisstream.io (free real-time)")
        print("- Real satellite images from Copernicus")
        print("=" * 60)
        
        try:
            # Stage 1: Collect AIS data from BarentsWatch
            print("\n📡 STAGE 1: BarentsWatch Official AIS Data")
            print("-" * 40)
            self._run_barentswatch_agent()
            
            # Stage 2: Collect AIS data from aisstream.io
            print("\n🌊 STAGE 2: aisstream.io Real-time AIS Data")
            print("-" * 40)
            self._run_aisstream_agent()
            
            # Stage 3: Collect satellite imagery
            print("\n🛰️ STAGE 3: Copernicus Satellite Imagery")
            print("-" * 40)
            self._run_satellite_agent()
            
            # Stage 4: Analyze results
            print("\n📊 STAGE 4: Pipeline Results Analysis")
            print("-" * 40)
            self._analyze_pipeline_results()
            
            # Stage 5: Generate final report
            print("\n📋 STAGE 5: Final MVP Report")
            print("-" * 40)
            self._generate_mvp_report()
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            self.pipeline_status['status'] = 'failed'
            self.pipeline_status['summary']['success'] = False
            print(f"❌ Pipeline failed: {e}")
        
        finally:
            self._save_pipeline_status()
    
    def _run_barentswatch_agent(self):
        """Run the BarentsWatch data collection agent."""
        agent_status = self.pipeline_status['agents']['barentswatch']
        
        try:
            script_path = Path(__file__).parent / "mvp_barentswatch_collector.py"
            
            print(f"🔄 Running BarentsWatch collector...")
            result = subprocess.run([
                sys.executable, str(script_path)
            ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
            
            if result.returncode == 0:
                agent_status['status'] = 'success'
                print("✅ BarentsWatch agent completed successfully")
                
                # Check for data files
                data_files = list(Path('data/mvp_pipeline/barentswatch').glob('barentswatch_vessels_*.json'))
                if data_files:
                    latest_file = max(data_files, key=lambda p: p.stat().st_mtime)
                    with open(latest_file, 'r') as f:
                        data = json.load(f)
                        agent_status['vessels'] = data.get('metadata', {}).get('total_vessels', 0)
                
            else:
                agent_status['status'] = 'failed'
                agent_status['errors'].append(f"Exit code: {result.returncode}")
                if result.stderr:
                    agent_status['errors'].append(result.stderr.strip())
                print(f"❌ BarentsWatch agent failed")
            
            # Show output
            if result.stdout:
                print(result.stdout)
                
        except subprocess.TimeoutExpired:
            agent_status['status'] = 'timeout'
            agent_status['errors'].append("Agent timed out after 5 minutes")
            print("⏰ BarentsWatch agent timed out")
        except Exception as e:
            agent_status['status'] = 'error'
            agent_status['errors'].append(str(e))
            print(f"❌ BarentsWatch agent error: {e}")
    
    def _run_aisstream_agent(self):
        """Run the aisstream.io data collection agent."""
        agent_status = self.pipeline_status['agents']['aisstream']
        
        try:
            script_path = Path(__file__).parent / "mvp_aisstream_collector.py"
            
            print(f"🔄 Running aisstream.io collector...")
            result = subprocess.run([
                sys.executable, str(script_path)
            ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
            
            if result.returncode == 0:
                agent_status['status'] = 'success'
                print("✅ aisstream.io agent completed successfully")
                
                # Check for data files
                data_files = list(Path('data/mvp_pipeline/aisstream').glob('aisstream_vessels_*.json'))
                if data_files:
                    latest_file = max(data_files, key=lambda p: p.stat().st_mtime)
                    with open(latest_file, 'r') as f:
                        data = json.load(f)
                        agent_status['vessels'] = data.get('metadata', {}).get('total_vessels', 0)
                
            else:
                agent_status['status'] = 'failed'
                agent_status['errors'].append(f"Exit code: {result.returncode}")
                if result.stderr:
                    agent_status['errors'].append(result.stderr.strip())
                print(f"❌ aisstream.io agent failed")
            
            # Show output
            if result.stdout:
                print(result.stdout)
                
        except subprocess.TimeoutExpired:
            agent_status['status'] = 'timeout'
            agent_status['errors'].append("Agent timed out after 5 minutes")
            print("⏰ aisstream.io agent timed out")
        except Exception as e:
            agent_status['status'] = 'error'
            agent_status['errors'].append(str(e))
            print(f"❌ aisstream.io agent error: {e}")
    
    def _run_satellite_agent(self):
        """Run the satellite imagery collection agent."""
        agent_status = self.pipeline_status['agents']['satellite']
        
        try:
            script_path = Path(__file__).parent / "mvp_satellite_collector.py"
            
            print(f"🔄 Running satellite collector...")
            result = subprocess.run([
                sys.executable, str(script_path)
            ], capture_output=True, text=True, timeout=600)  # 10 minute timeout for downloads
            
            if result.returncode == 0:
                agent_status['status'] = 'success'
                print("✅ Satellite agent completed successfully")
                
                # Check for data files
                metadata_files = list(Path('data/mvp_pipeline/satellite').glob('satellite_metadata_*.json'))
                if metadata_files:
                    agent_status['products'] = len(metadata_files)
                
            else:
                agent_status['status'] = 'failed'
                agent_status['errors'].append(f"Exit code: {result.returncode}")
                if result.stderr:
                    agent_status['errors'].append(result.stderr.strip())
                print(f"❌ Satellite agent failed")
            
            # Show output
            if result.stdout:
                print(result.stdout)
                
        except subprocess.TimeoutExpired:
            agent_status['status'] = 'timeout'
            agent_status['errors'].append("Agent timed out after 10 minutes")
            print("⏰ Satellite agent timed out")
        except Exception as e:
            agent_status['status'] = 'error'
            agent_status['errors'].append(str(e))
            print(f"❌ Satellite agent error: {e}")
    
    def _analyze_pipeline_results(self):
        """Analyze the results from all agents."""
        print("🔍 Analyzing pipeline results...")
        
        # Collect all vessel data
        all_vessels = []
        unique_mmsi = set()
        
        # BarentsWatch vessels
        barentswatch_dir = Path('data/mvp_pipeline/barentswatch')
        if barentswatch_dir.exists():
            for vessel_file in barentswatch_dir.glob('barentswatch_vessels_*.json'):
                try:
                    with open(vessel_file, 'r') as f:
                        data = json.load(f)
                        vessels = data.get('vessels', [])
                        all_vessels.extend(vessels)
                        for vessel in vessels:
                            if vessel.get('mmsi'):
                                unique_mmsi.add(vessel['mmsi'])
                except Exception as e:
                    logger.warning(f"Failed to read {vessel_file}: {e}")
        
        # aisstream.io vessels
        aisstream_dir = Path('data/mvp_pipeline/aisstream')
        if aisstream_dir.exists():
            for vessel_file in aisstream_dir.glob('aisstream_vessels_*.json'):
                try:
                    with open(vessel_file, 'r') as f:
                        data = json.load(f)
                        vessels = data.get('vessels', [])
                        all_vessels.extend(vessels)
                        for vessel in vessels:
                            if vessel.get('mmsi'):
                                unique_mmsi.add(vessel['mmsi'])
                except Exception as e:
                    logger.warning(f"Failed to read {vessel_file}: {e}")
        
        # Count satellite images
        satellite_dir = Path('data/mvp_pipeline/satellite')
        satellite_count = 0
        if satellite_dir.exists():
            satellite_count = len(list(satellite_dir.glob('*.zip'))) + len(list(satellite_dir.glob('*.SAFE')))
        
        # Update summary
        self.pipeline_status['summary'].update({
            'total_vessels': len(all_vessels),
            'unique_mmsi': len(unique_mmsi),
            'satellite_images': satellite_count,
            'success': len(all_vessels) > 0 or satellite_count > 0
        })
        
        print(f"📊 Pipeline Results:")
        print(f"   Total vessels collected: {len(all_vessels)}")
        print(f"   Unique vessels (MMSI): {len(unique_mmsi)}")
        print(f"   Satellite images: {satellite_count}")
        
        # Determine success criteria
        if len(all_vessels) > 0 and satellite_count > 0:
            self.pipeline_status['status'] = 'complete_success'
            print("🎉 COMPLETE SUCCESS: Both AIS data and satellite imagery collected!")
        elif len(all_vessels) > 0:
            self.pipeline_status['status'] = 'partial_success'
            print("✅ PARTIAL SUCCESS: AIS data collected (satellite data pending)")
        elif satellite_count > 0:
            self.pipeline_status['status'] = 'partial_success'
            print("✅ PARTIAL SUCCESS: Satellite data collected (AIS data pending)")
        else:
            self.pipeline_status['status'] = 'no_data'
            print("⚠️ No data collected from any source")
    
    def _generate_mvp_report(self):
        """Generate the final MVP report."""
        
        # Determine next steps
        next_steps = []
        
        agents = self.pipeline_status['agents']
        
        if agents['barentswatch']['status'] == 'success':
            next_steps.append("✅ BarentsWatch integration working - official Norwegian AIS data confirmed")
        else:
            next_steps.append("❌ BarentsWatch setup needed - get official Norwegian API access")
        
        if agents['aisstream']['status'] == 'success':
            next_steps.append("✅ aisstream.io integration working - real-time AIS data confirmed")
        else:
            next_steps.append("❌ aisstream.io setup needed - get free API key")
        
        if agents['satellite']['status'] == 'success':
            next_steps.append("✅ Copernicus integration working - satellite imagery confirmed")
        else:
            next_steps.append("❌ Copernicus setup needed - get free Data Space account")
        
        if self.pipeline_status['summary']['success']:
            next_steps.append("🎯 Ready for visualization: Create map showing vessels with satellite overlay")
            next_steps.append("📈 Ready for scaling: Implement automated daily collection")
        else:
            next_steps.append("🔧 Focus on data collection setup before proceeding to visualization")
        
        self.pipeline_status['next_steps'] = next_steps
        
        # Generate report
        print("\n" + "=" * 60)
        print("📋 MVP PIPELINE FINAL REPORT")
        print("=" * 60)
        
        print(f"\n🎯 MISSION: Prove Arctic maritime data collection works")
        print(f"📅 Pipeline run: {self.pipeline_status['pipeline_id']}")
        print(f"⏰ Timestamp: {self.pipeline_status['timestamp']}")
        print(f"🏆 Overall status: {self.pipeline_status['status'].upper()}")
        
        print(f"\n📊 DATA COLLECTION RESULTS:")
        for agent_name, agent_data in agents.items():
            status_icon = "✅" if agent_data['status'] == 'success' else "❌"
            print(f"   {status_icon} {agent_name.capitalize()}: {agent_data['status']}")
            if agent_name in ['barentswatch', 'aisstream'] and agent_data['vessels'] > 0:
                print(f"      └─ Vessels collected: {agent_data['vessels']}")
            elif agent_name == 'satellite' and agent_data['products'] > 0:
                print(f"      └─ Products collected: {agent_data['products']}")
            if agent_data['errors']:
                print(f"      └─ Errors: {'; '.join(agent_data['errors'][:2])}")
        
        summary = self.pipeline_status['summary']
        print(f"\n📈 SUMMARY METRICS:")
        print(f"   Total vessels: {summary['total_vessels']}")
        print(f"   Unique vessels: {summary['unique_mmsi']}")
        print(f"   Satellite images: {summary['satellite_images']}")
        print(f"   Pipeline success: {summary['success']}")
        
        print(f"\n🔄 NEXT STEPS:")
        for step in next_steps:
            print(f"   {step}")
        
        if summary['success']:
            print(f"\n🎉 DELIVERABLE STATUS: ACHIEVED")
            print(f"   ✅ Proof of concept complete: Real Arctic maritime data collected")
            print(f"   🚢 Real ships detected and tracked")
            if summary['satellite_images'] > 0:
                print(f"   🛰️ Real satellite imagery acquired")
            print(f"   📍 Ready for map visualization")
        else:
            print(f"\n⚠️ DELIVERABLE STATUS: PENDING")
            print(f"   Focus on resolving data collection setup issues first")
        
        print("\n" + "=" * 60)
    
    def _save_pipeline_status(self):
        """Save the complete pipeline status."""
        status_file = self.output_dir / f"pipeline_status_{self.timestamp}.json"
        
        with open(status_file, 'w') as f:
            json.dump(self.pipeline_status, f, indent=2)
        
        # Also save as latest
        latest_file = self.output_dir / "latest_pipeline_status.json"
        with open(latest_file, 'w') as f:
            json.dump(self.pipeline_status, f, indent=2)
        
        print(f"\n📋 Pipeline status saved: {status_file}")
        print(f"📋 Latest status: {latest_file}")

def main():
    """Run the MVP pipeline."""
    coordinator = MVPPipelineCoordinator()
    coordinator.run_pipeline()

if __name__ == "__main__":
    main()