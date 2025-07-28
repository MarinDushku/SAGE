#!/usr/bin/env python3
"""
SAGE - Smart Adaptive General Executive
Zero-cost AI desktop assistant main entry point
"""

import asyncio
import sys
import signal
import argparse
from pathlib import Path
from typing import Optional

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.event_bus import EventBus
from core.plugin_manager import PluginManager
from core.config_manager import ConfigManager
from core.resource_monitor import ResourceMonitor
from core.cache_manager import CacheManager
from core.logger import Logger


class SAGEApplication:
    """Main SAGE application manager"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.running = False
        
        # Core components
        self.logger = None
        self.config_manager = None
        self.event_bus = None
        self.plugin_manager = None
        self.resource_monitor = None
        self.cache_manager = None
        
        # Signal handling
        self.shutdown_event = asyncio.Event()
        
    async def initialize(self) -> bool:
        """Initialize all SAGE components"""
        try:
            print("🚀 Starting SAGE - Smart Adaptive General Executive")
            print("   Zero-Cost AI Desktop Assistant")
            print("=" * 50)
            
            # Initialize logger first
            self.logger = Logger("SAGE")
            main_log = self.logger.get_logger("main")
            main_log.info("Initializing SAGE application...")
            
            # Initialize configuration manager
            self.config_manager = ConfigManager(self.config_file)
            if not self.config_manager.load_config():
                main_log.error("Failed to load configuration")
                return False
                
            # Set log level from config
            log_level = self.config_manager.get("core.log_level", "INFO")
            self.logger.set_level(log_level)
            
            main_log.info(f"Configuration loaded from {self.config_file}")
            
            # Validate configuration
            issues = self.config_manager.validate_config()
            if issues["errors"]:
                main_log.error(f"Configuration errors: {issues['errors']}")
                return False
            if issues["warnings"]:
                main_log.warning(f"Configuration warnings: {issues['warnings']}")
                
            # Initialize cache manager
            cache_config = self.config_manager.get_performance_config()
            self.cache_manager = CacheManager(
                max_memory_mb=cache_config.get("cache_size_mb", 200),
                default_ttl=3600
            )
            main_log.info("Cache manager initialized")
            
            # Initialize event bus
            queue_size = self.config_manager.get("core.event_queue_size", 1000)
            self.event_bus = EventBus(max_queue_size=queue_size)
            await self.event_bus.start()
            main_log.info("Event bus started")
            
            # Initialize resource monitor
            monitor_interval = self.config_manager.get("core.resource_monitor_interval", 30)
            self.resource_monitor = ResourceMonitor(check_interval=monitor_interval)
            
            # Set resource thresholds
            perf_config = self.config_manager.get_performance_config()
            if "max_memory_mb" in perf_config:
                self.resource_monitor.set_threshold("sage_memory_mb", perf_config["max_memory_mb"])
            if "max_cpu_percent" in perf_config:
                self.resource_monitor.set_threshold("cpu_percent", perf_config["max_cpu_percent"])
                
            # Add resource monitoring callbacks
            self.resource_monitor.add_callback("sage_memory_limit", self._handle_memory_warning)
            self.resource_monitor.add_callback("high_cpu", self._handle_cpu_warning)
            
            await self.resource_monitor.start()
            main_log.info("Resource monitor started")
            
            # Initialize plugin manager
            self.plugin_manager = PluginManager()
            self.plugin_manager.set_dependencies(
                event_bus=self.event_bus,
                config_manager=self.config_manager,
                cache_manager=self.cache_manager,
                logger=self.logger
            )
            main_log.info("Plugin manager initialized")
            
            # Load auto-load modules
            auto_load_modules = self.config_manager.get_auto_load_modules()
            if auto_load_modules:
                main_log.info(f"Loading auto-load modules: {auto_load_modules}")
                load_results = await self.plugin_manager.load_all_modules(auto_load_modules)
                
                loaded_count = sum(1 for success in load_results.values() if success)
                main_log.info(f"Loaded {loaded_count}/{len(auto_load_modules)} modules successfully")
                
                # Log any failures
                for module_name, success in load_results.items():
                    if not success:
                        main_log.error(f"Failed to load module: {module_name}")
            else:
                main_log.info("No auto-load modules configured")
                
            self.running = True
            main_log.info("SAGE initialization completed successfully")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize SAGE: {e}", "main")
            else:
                print(f"❌ Failed to initialize SAGE: {e}")
            return False
            
    async def shutdown(self) -> None:
        """Shutdown SAGE gracefully"""
        try:
            if not self.running:
                return
                
            self.running = False
            main_log = self.logger.get_logger("main") if self.logger else None
            
            if main_log:
                main_log.info("Starting SAGE shutdown...")
            else:
                print("🔄 Shutting down SAGE...")
                
            # Shutdown modules first
            if self.plugin_manager:
                await self.plugin_manager.unload_all_modules()
                if main_log:
                    main_log.info("All modules unloaded")
                    
            # Shutdown core components
            if self.resource_monitor:
                await self.resource_monitor.stop()
                if main_log:
                    main_log.info("Resource monitor stopped")
                    
            if self.event_bus:
                await self.event_bus.stop()
                if main_log:
                    main_log.info("Event bus stopped")
                    
            # Clean up cache
            if self.cache_manager:
                self.cache_manager.cleanup()
                if main_log:
                    main_log.info("Cache cleaned up")
                    
            # Save configuration
            if self.config_manager:
                self.config_manager.save_config()
                if main_log:
                    main_log.info("Configuration saved")
                    
            # Final log and cleanup
            if self.logger:
                main_log.info("SAGE shutdown completed")
                self.logger.flush_logs()
            else:
                print("✅ SAGE shutdown completed")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error during shutdown: {e}", "main")
            else:
                print(f"❌ Error during shutdown: {e}")
                
    def _handle_memory_warning(self, snapshot) -> None:
        """Handle memory usage warnings"""
        if self.logger:
            self.logger.warning(
                f"High memory usage: {snapshot.sage_memory_mb:.1f}MB", 
                "resources"
            )
            
        # Trigger cache cleanup
        if self.cache_manager:
            self.cache_manager.cleanup()
            
        # Trigger resource optimization  
        if self.resource_monitor:
            asyncio.create_task(self.resource_monitor.optimize_performance())
            
    def _handle_cpu_warning(self, snapshot) -> None:
        """Handle CPU usage warnings"""
        if self.logger:
            self.logger.warning(
                f"High CPU usage: {snapshot.cpu_percent:.1f}%", 
                "resources"
            )
            
    async def run(self) -> None:
        """Main application run loop"""
        try:
            # Setup signal handlers
            def signal_handler(signum, frame):
                print(f"\n🛑 Received signal {signum}, shutting down...")
                self.shutdown_event.set()
                
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            main_log = self.logger.get_logger("main")
            main_log.info("SAGE is running. Press Ctrl+C to stop.")
            print("✅ SAGE is running. Press Ctrl+C to stop.")
            
            # Print status information
            self._print_status()
            
            # Main event loop
            while self.running and not self.shutdown_event.is_set():
                try:
                    # Wait for shutdown signal or timeout
                    await asyncio.wait_for(
                        self.shutdown_event.wait(), 
                        timeout=10.0
                    )
                    break
                except asyncio.TimeoutError:
                    # Timeout is normal - continue running
                    continue
                except Exception as e:
                    main_log.error(f"Error in main loop: {e}")
                    await asyncio.sleep(1)
                    
        except KeyboardInterrupt:
            print("\n🛑 Keyboard interrupt received")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in main run loop: {e}", "main")
            else:
                print(f"❌ Error in main run loop: {e}")
        finally:
            await self.shutdown()
            
    def _print_status(self) -> None:
        """Print current SAGE status"""
        try:
            print("\n📊 SAGE Status:")
            print("-" * 30)
            
            # Loaded modules
            if self.plugin_manager:
                loaded_modules = self.plugin_manager.get_loaded_modules()
                print(f"Loaded modules: {', '.join(loaded_modules) if loaded_modules else 'None'}")
                
            # Resource usage
            if self.resource_monitor:
                current = self.resource_monitor.get_current_snapshot()
                if current:
                    print(f"Memory usage: {current.sage_memory_mb:.1f}MB")
                    print(f"CPU usage: {current.sage_cpu_percent:.1f}%")
                    
            # Cache statistics
            if self.cache_manager:
                cache_stats = self.cache_manager.get_statistics()
                memory_cache = cache_stats.get("memory_cache", {})
                print(f"Cache usage: {memory_cache.get('size_mb', 0):.1f}MB ({memory_cache.get('entries', 0)} entries)")
                
            print("-" * 30)
            
        except Exception as e:
            print(f"⚠️  Error printing status: {e}")
            
    async def get_status(self) -> dict:
        """Get comprehensive system status"""
        try:
            status = {
                "running": self.running,
                "config_file": str(self.config_file),
                "modules": {},
                "resources": {},
                "cache": {},
                "events": {}
            }
            
            # Module status
            if self.plugin_manager:
                status["modules"] = await self.plugin_manager.get_module_status()
                
            # Resource status
            if self.resource_monitor:
                status["resources"] = self.resource_monitor.get_statistics()
                
            # Cache status
            if self.cache_manager:
                status["cache"] = self.cache_manager.get_statistics()
                
            # Event bus status
            if self.event_bus:
                status["events"] = self.event_bus.get_statistics()
                
            return status
            
        except Exception as e:
            return {"error": str(e)}


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="SAGE - Smart Adaptive General Executive")
    parser.add_argument(
        "--config", 
        default="config.yaml",
        help="Configuration file path (default: config.yaml)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--status",
        action="store_true", 
        help="Show status and exit"
    )
    
    args = parser.parse_args()
    
    # Create SAGE application
    app = SAGEApplication(config_file=args.config)
    
    try:
        # Initialize application
        if not await app.initialize():
            print("❌ Failed to initialize SAGE")
            return 1
            
        if args.status:
            # Show status and exit
            status = await app.get_status()
            print("\n📊 SAGE Status:")
            print("=" * 50)
            for key, value in status.items():
                print(f"{key.title()}: {value}")
            return 0
            
        # Run application
        await app.run()
        return 0
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    # Ensure proper asyncio event loop on Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    # Run the application
    exit_code = asyncio.run(main())
    sys.exit(exit_code)