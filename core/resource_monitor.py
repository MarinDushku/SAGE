"""
Resource Monitor - System resource monitoring and management for SAGE
"""

import asyncio
import psutil
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from collections import deque
import threading
import logging


@dataclass
class ResourceSnapshot:
    """Snapshot of system resources at a point in time"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    sage_memory_mb: float
    sage_cpu_percent: float


class ResourceMonitor:
    """Monitors system resources and manages SAGE performance"""
    
    def __init__(self, check_interval: int = 30, history_size: int = 100):
        self.check_interval = check_interval
        self.history_size = history_size
        self.history: deque = deque(maxlen=history_size)
        self.thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_usage_percent": 90.0,
            "sage_memory_mb": 1000.0
        }
        self.callbacks: Dict[str, List[Callable[[ResourceSnapshot], None]]] = {
            "high_cpu": [],
            "high_memory": [],
            "high_disk": [],
            "sage_memory_limit": []
        }
        
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.logger = logging.getLogger(__name__)
        self.sage_process = psutil.Process()
        
        # Network baseline
        self.network_baseline = psutil.net_io_counters()
        
    async def start(self) -> None:
        """Start resource monitoring"""
        if self.running:
            return
            
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        self.logger.info("Resource monitor started")
        
    async def stop(self) -> None:
        """Stop resource monitoring"""
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Resource monitor stopped")
        
    def set_threshold(self, metric: str, value: float) -> None:
        """Set a threshold for resource alerts"""
        if metric in self.thresholds:
            self.thresholds[metric] = value
            self.logger.info(f"Set {metric} threshold to {value}")
        else:
            self.logger.warning(f"Unknown threshold metric: {metric}")
            
    def add_callback(self, event_type: str, callback: Callable[[ResourceSnapshot], None]) -> None:
        """Add callback for resource events"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
        else:
            self.logger.warning(f"Unknown callback event type: {event_type}")
            
    async def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self.running:
            try:
                snapshot = await self._take_snapshot()
                self.history.append(snapshot)
                
                # Check thresholds and trigger callbacks
                await self._check_thresholds(snapshot)
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in resource monitoring: {e}")
                await asyncio.sleep(self.check_interval)
                
    async def _take_snapshot(self) -> ResourceSnapshot:
        """Take a snapshot of current system resources"""
        try:
            # System resources
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            # SAGE process resources
            sage_memory = self.sage_process.memory_info()
            sage_cpu = self.sage_process.cpu_percent()
            
            return ResourceSnapshot(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_mb=memory.used / 1024 / 1024,
                disk_usage_percent=disk.percent,
                network_bytes_sent=network.bytes_sent - self.network_baseline.bytes_sent,
                network_bytes_recv=network.bytes_recv - self.network_baseline.bytes_recv,
                process_count=len(psutil.pids()),
                sage_memory_mb=sage_memory.rss / 1024 / 1024,
                sage_cpu_percent=sage_cpu
            )
            
        except Exception as e:
            self.logger.error(f"Failed to take resource snapshot: {e}")
            # Return a default snapshot
            return ResourceSnapshot(
                timestamp=time.time(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_mb=0.0,
                disk_usage_percent=0.0,
                network_bytes_sent=0,
                network_bytes_recv=0,
                process_count=0,
                sage_memory_mb=0.0,
                sage_cpu_percent=0.0
            )
            
    async def _check_thresholds(self, snapshot: ResourceSnapshot) -> None:
        """Check if any thresholds are exceeded and trigger callbacks"""
        try:
            # High CPU
            if snapshot.cpu_percent > self.thresholds["cpu_percent"]:
                for callback in self.callbacks["high_cpu"]:
                    try:
                        callback(snapshot)
                    except Exception as e:
                        self.logger.error(f"Error in high_cpu callback: {e}")
                        
            # High memory
            if snapshot.memory_percent > self.thresholds["memory_percent"]:
                for callback in self.callbacks["high_memory"]:
                    try:
                        callback(snapshot)
                    except Exception as e:
                        self.logger.error(f"Error in high_memory callback: {e}")
                        
            # High disk usage
            if snapshot.disk_usage_percent > self.thresholds["disk_usage_percent"]:
                for callback in self.callbacks["high_disk"]:
                    try:
                        callback(snapshot)
                    except Exception as e:
                        self.logger.error(f"Error in high_disk callback: {e}")
                        
            # SAGE memory limit
            if snapshot.sage_memory_mb > self.thresholds["sage_memory_mb"]:
                for callback in self.callbacks["sage_memory_limit"]:
                    try:
                        callback(snapshot)
                    except Exception as e:
                        self.logger.error(f"Error in sage_memory_limit callback: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error checking thresholds: {e}")
            
    def get_current_snapshot(self) -> Optional[ResourceSnapshot]:
        """Get the most recent resource snapshot"""
        return self.history[-1] if self.history else None
        
    def get_history(self, minutes: int = 30) -> List[ResourceSnapshot]:
        """Get resource history for the specified time period"""
        if not self.history:
            return []
            
        cutoff_time = time.time() - (minutes * 60)
        return [s for s in self.history if s.timestamp >= cutoff_time]
        
    def get_average_usage(self, minutes: int = 10) -> Dict[str, float]:
        """Get average resource usage over specified time period"""
        history = self.get_history(minutes)
        
        if not history:
            return {}
            
        return {
            "cpu_percent": sum(s.cpu_percent for s in history) / len(history),
            "memory_percent": sum(s.memory_percent for s in history) / len(history),
            "sage_memory_mb": sum(s.sage_memory_mb for s in history) / len(history),
            "sage_cpu_percent": sum(s.sage_cpu_percent for s in history) / len(history)
        }
        
    def get_peak_usage(self, minutes: int = 60) -> Dict[str, float]:
        """Get peak resource usage over specified time period"""
        history = self.get_history(minutes)
        
        if not history:
            return {}
            
        return {
            "cpu_percent": max(s.cpu_percent for s in history),
            "memory_percent": max(s.memory_percent for s in history),
            "sage_memory_mb": max(s.sage_memory_mb for s in history),
            "sage_cpu_percent": max(s.sage_cpu_percent for s in history)
        }
        
    def is_system_healthy(self) -> bool:
        """Check if system resources are within healthy limits"""
        current = self.get_current_snapshot()
        if not current:
            return True
            
        return (
            current.cpu_percent < self.thresholds["cpu_percent"] and
            current.memory_percent < self.thresholds["memory_percent"] and
            current.disk_usage_percent < self.thresholds["disk_usage_percent"] and
            current.sage_memory_mb < self.thresholds["sage_memory_mb"]
        )
        
    def get_system_info(self) -> Dict[str, Any]:
        """Get static system information"""
        try:
            return {
                "cpu_count": psutil.cpu_count(),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "memory_total_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024,
                "disk_total_gb": psutil.disk_usage('/').total / 1024 / 1024 / 1024,
                "platform": psutil.WINDOWS if hasattr(psutil, 'WINDOWS') else 'linux',
                "python_version": f"{psutil.version_info.major}.{psutil.version_info.minor}",
                "sage_pid": self.sage_process.pid
            }
        except Exception as e:
            self.logger.error(f"Failed to get system info: {e}")
            return {}
            
    async def optimize_performance(self) -> None:
        """Attempt to optimize SAGE performance"""
        try:
            current = self.get_current_snapshot()
            if not current:
                return
                
            self.logger.info("Running performance optimization...")
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Log current state
            self.logger.info(f"Before optimization - CPU: {current.sage_cpu_percent:.1f}%, Memory: {current.sage_memory_mb:.1f}MB")
            
            # Take new snapshot after optimization
            await asyncio.sleep(2)
            new_snapshot = await self._take_snapshot()
            self.logger.info(f"After optimization - CPU: {new_snapshot.sage_cpu_percent:.1f}%, Memory: {new_snapshot.sage_memory_mb:.1f}MB")
            
        except Exception as e:
            self.logger.error(f"Error during performance optimization: {e}")
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive resource statistics"""
        current = self.get_current_snapshot()
        avg_10min = self.get_average_usage(10)
        peak_1hour = self.get_peak_usage(60)
        
        return {
            "current": current.__dict__ if current else {},
            "average_10min": avg_10min,
            "peak_1hour": peak_1hour,
            "thresholds": self.thresholds,
            "system_healthy": self.is_system_healthy(),
            "history_size": len(self.history),
            "monitoring_active": self.running
        }