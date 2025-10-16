#!/usr/bin/env python3
"""
Mind-Base Sync Daemon
Automated conversation collection and synchronization service
Runs continuously and syncs conversations from AI tools on schedule
"""

import os
import sys
import time
import signal
import logging
import schedule
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any
import subprocess
import json

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from collect_conversations import get_collector, MindBaseSyncer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/mind-base-daemon.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('mind-base-daemon')

class SyncDaemon:
    """Mind-Base synchronization daemon"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.running = False
        self.syncer = None
        self.last_sync_times = {}
        
        # Initialize syncer
        if self.config.get('supabase_url') and self.config.get('supabase_key'):
            self.syncer = MindBaseSyncer(
                self.config['supabase_url'],
                self.config['supabase_key']
            )
        else:
            logger.error("Supabase configuration missing - sync disabled")
    
    def _load_config(self, config_path: str = None) -> Dict[str, Any]:
        """Load configuration from file or environment"""
        config = {
            # Default configuration
            'sync_schedule': '0 */6 * * *',  # Every 6 hours
            'batch_size': 50,
            'sources': ['claude-desktop', 'chatgpt', 'cursor', 'windsurf', 'claude-code'],
            'enabled_sources': ['claude-desktop'],  # Start with Claude Desktop only
            'max_conversation_age_days': 30,
            'retry_attempts': 3,
            'retry_delay_seconds': 60,
            'health_check_interval': 300,  # 5 minutes
            'log_level': 'INFO',
            'dry_run': False,
        }
        
        # Load from config file if provided
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                config.update(file_config)
                logger.info(f"Loaded config from {config_path}")
            except Exception as e:
                logger.warning(f"Error loading config file: {e}")
        
        # Override with environment variables
        env_config = {
            'supabase_url': os.getenv('SUPABASE_URL', 'http://mind-base.localhost:8000'),
            'supabase_key': os.getenv('SUPABASE_SERVICE_ROLE_KEY'),
            'sync_schedule': os.getenv('MB_SYNC_SCHEDULE', config['sync_schedule']),
            'batch_size': int(os.getenv('MB_BATCH_SIZE', str(config['batch_size']))),
            'dry_run': os.getenv('MB_DRY_RUN', '').lower() in ('true', '1', 'yes'),
        }
        
        # Remove None values
        env_config = {k: v for k, v in env_config.items() if v is not None}
        config.update(env_config)
        
        return config
    
    def start(self):
        """Start the sync daemon"""
        logger.info("Starting Mind-Base sync daemon...")
        logger.info(f"Configuration: {self._sanitize_config_for_log()}")
        
        if not self.syncer:
            logger.error("Cannot start daemon without valid Supabase configuration")
            return False
        
        self.running = True
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Schedule sync jobs
        self._setup_sync_schedule()
        
        # Start health check thread
        health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        health_thread.start()
        
        # Run initial sync
        self._run_sync()
        
        # Main loop
        logger.info("Daemon started - waiting for scheduled syncs...")
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)
        
        self.stop()
        return True
    
    def stop(self):
        """Stop the sync daemon"""
        logger.info("Stopping Mind-Base sync daemon...")
        self.running = False
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}")
        self.stop()
    
    def _sanitize_config_for_log(self) -> Dict[str, Any]:
        """Remove sensitive information from config for logging"""
        safe_config = self.config.copy()
        if 'supabase_key' in safe_config:
            safe_config['supabase_key'] = '***masked***'
        return safe_config
    
    def _setup_sync_schedule(self):
        """Set up sync schedule"""
        # Parse cron-like schedule
        schedule_str = self.config['sync_schedule']
        
        # For simplicity, support common patterns
        if schedule_str == '0 */6 * * *':  # Every 6 hours
            schedule.every(6).hours.do(self._run_sync)
        elif schedule_str == '0 */4 * * *':  # Every 4 hours
            schedule.every(4).hours.do(self._run_sync)
        elif schedule_str == '0 */2 * * *':  # Every 2 hours
            schedule.every(2).hours.do(self._run_sync)
        elif schedule_str == '0 * * * *':   # Every hour
            schedule.every().hour.do(self._run_sync)
        elif schedule_str == '*/30 * * * *': # Every 30 minutes
            schedule.every(30).minutes.do(self._run_sync)
        else:
            # Default to every 6 hours
            logger.warning(f"Unsupported schedule format: {schedule_str}, using 6 hours")
            schedule.every(6).hours.do(self._run_sync)
        
        logger.info(f"Sync scheduled: {schedule_str}")
    
    def _run_sync(self):
        """Run synchronization for all enabled sources"""
        logger.info("Starting scheduled sync...")
        
        sync_start = datetime.now()
        total_conversations = 0
        sync_results = {}
        
        for source in self.config['enabled_sources']:
            try:
                # Get conversations since last sync or max age
                since_date = self._get_sync_since_date(source)
                
                # Collect conversations
                collector = get_collector(source)
                conversations = collector.collect(since_date)
                
                if conversations:
                    # Sync to Mind-Base
                    if self.config['dry_run']:
                        logger.info(f"DRY RUN: Would sync {len(conversations)} conversations from {source}")
                        sync_results[source] = {'success': True, 'count': len(conversations)}
                    else:
                        result = self._sync_with_retry(conversations)
                        sync_results[source] = result
                        
                        if result.get('success'):
                            total_conversations += len(conversations)
                            self.last_sync_times[source] = sync_start
                else:
                    sync_results[source] = {'success': True, 'count': 0, 'message': 'No new conversations'}
                
                logger.info(f"{source}: {len(conversations)} conversations")
                
            except Exception as e:
                logger.error(f"Error syncing {source}: {e}")
                sync_results[source] = {'success': False, 'error': str(e)}
        
        # Log summary
        sync_duration = (datetime.now() - sync_start).total_seconds()
        logger.info(f"Sync completed in {sync_duration:.1f}s - {total_conversations} conversations")
        
        # Save sync status
        self._save_sync_status(sync_start, sync_results, sync_duration)
    
    def _get_sync_since_date(self, source: str) -> datetime:
        """Get the date to sync from for a source"""
        # Use last sync time if available
        if source in self.last_sync_times:
            return self.last_sync_times[source]
        
        # Otherwise, use max age
        max_age_days = self.config['max_conversation_age_days']
        return datetime.now() - timedelta(days=max_age_days)
    
    def _sync_with_retry(self, conversations) -> Dict[str, Any]:
        """Sync conversations with retry logic"""
        for attempt in range(self.config['retry_attempts']):
            try:
                result = self.syncer.sync_conversations(conversations)
                if result.get('success'):
                    return result
                
                if attempt < self.config['retry_attempts'] - 1:
                    logger.warning(f"Sync failed (attempt {attempt + 1}), retrying in {self.config['retry_delay_seconds']}s...")
                    time.sleep(self.config['retry_delay_seconds'])
                else:
                    return result
                    
            except Exception as e:
                if attempt < self.config['retry_attempts'] - 1:
                    logger.warning(f"Sync error (attempt {attempt + 1}): {e}, retrying...")
                    time.sleep(self.config['retry_delay_seconds'])
                else:
                    return {'success': False, 'error': str(e)}
        
        return {'success': False, 'error': 'Max retries exceeded'}
    
    def _save_sync_status(self, sync_time: datetime, results: Dict[str, Any], duration: float):
        """Save sync status to file"""
        status = {
            'timestamp': sync_time.isoformat(),
            'duration_seconds': duration,
            'results': results,
            'total_conversations': sum(r.get('count', 0) for r in results.values() if r.get('success')),
            'success_count': sum(1 for r in results.values() if r.get('success')),
            'error_count': sum(1 for r in results.values() if not r.get('success')),
        }
        
        status_file = Path('/tmp/mind-base-sync-status.json')
        try:
            with open(status_file, 'w') as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save sync status: {e}")
    
    def _health_check_loop(self):
        """Periodic health check"""
        while self.running:
            try:
                self._health_check()
                time.sleep(self.config['health_check_interval'])
            except Exception as e:
                logger.error(f"Health check error: {e}")
                time.sleep(60)  # Wait a minute before retry
    
    def _health_check(self):
        """Perform health check"""
        # Check Supabase connectivity
        if self.syncer:
            try:
                # Simple health check - try to access the functions endpoint
                response = self.syncer.session.get(
                    f'{self.syncer.base_url}/functions/v1',
                    timeout=10
                )
                if response.status_code in [200, 404]:  # 404 is OK, means endpoint exists
                    logger.debug("Supabase health check: OK")
                else:
                    logger.warning(f"Supabase health check failed: {response.status_code}")
            except Exception as e:
                logger.warning(f"Supabase health check error: {e}")
        
        # Check disk space
        try:
            import shutil
            disk_usage = shutil.disk_usage('/')
            free_gb = disk_usage.free / (1024**3)
            if free_gb < 1:  # Less than 1GB free
                logger.warning(f"Low disk space: {free_gb:.1f}GB free")
        except Exception as e:
            logger.debug(f"Disk space check error: {e}")

def create_systemd_service():
    """Create systemd service file for the daemon"""
    service_content = f"""[Unit]
Description=Mind-Base Sync Daemon
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'ubuntu')}
WorkingDirectory={Path(__file__).parent}
ExecStart={sys.executable} {Path(__file__).absolute()}
Restart=always
RestartSec=10
Environment=PYTHONPATH={Path(__file__).parent}

[Install]
WantedBy=multi-user.target
"""
    
    service_file = Path('/tmp/mind-base-sync.service')
    with open(service_file, 'w') as f:
        f.write(service_content)
    
    print(f"Systemd service file created: {service_file}")
    print(f"To install: sudo cp {service_file} /etc/systemd/system/")
    print("To enable: sudo systemctl enable mind-base-sync")
    print("To start: sudo systemctl start mind-base-sync")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Mind-Base sync daemon')
    parser.add_argument('--config', type=str, help='Configuration file path')
    parser.add_argument('--create-service', action='store_true', help='Create systemd service file')
    parser.add_argument('--test-sync', action='store_true', help='Run one sync and exit')
    parser.add_argument('--status', action='store_true', help='Show sync status')
    
    args = parser.parse_args()
    
    if args.create_service:
        create_systemd_service()
        return 0
    
    if args.status:
        status_file = Path('/tmp/mind-base-sync-status.json')
        if status_file.exists():
            with open(status_file) as f:
                status = json.load(f)
            print(json.dumps(status, indent=2))
        else:
            print("No sync status available")
        return 0
    
    # Create and start daemon
    daemon = SyncDaemon(args.config)
    
    if args.test_sync:
        logger.info("Running test sync...")
        daemon._run_sync()
        return 0
    
    try:
        success = daemon.start()
        return 0 if success else 1
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Daemon error: {e}")
        return 1

if __name__ == '__main__':
    exit(main())