"""
Resource Monitor - System resource monitoring and management for SAGE
"""

import asyncio
import sys
import time
import tracemalloc
import gc
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from collections import deque, defaultdict
import threading
import logging
from pathlib import Path
import json
from datetime import datetime, timedelta

# Try to import psutil, provide fallback if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None


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
    module_resources: Dict[str, 'ModuleResourceUsage'] = field(default_factory=dict)


@dataclass
class ModuleResourceUsage:
    """Resource usage tracking for a specific module"""
    module_name: str
    timestamp: float
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    thread_count: int = 0
    file_handles: int = 0
    network_connections: int = 0
    cache_usage_mb: float = 0.0
    event_queue_size: int = 0
    error_count: int = 0
    last_activity: Optional[float] = None
    status: str = "unknown"  # running, idle, error, stopped
    
    
@dataclass
class ResourceQuota:
    """Resource quota for a module"""
    module_name: str
    max_memory_mb: float = 100.0
    max_cpu_percent: float = 50.0
    max_threads: int = 5
    max_file_handles: int = 20
    max_cache_mb: float = 50.0
    enabled: bool = True
    
    
@dataclass
class ResourceAlert:
    """Resource usage alert"""
    module_name: str
    alert_type: str  # quota_exceeded, high_usage, error_spike
    message: str
    severity: str  # low, medium, high, critical
    timestamp: float
    metrics: Dict[str, Any] = field(default_factory=dict)


class ResourceMonitor:
    """Monitors system resources and manages SAGE performance"""
    
    def __init__(self, check_interval: int = 30, history_size: int = 100, data_dir: str = "data/monitoring"):
        self.check_interval = check_interval
        self.history_size = history_size
        self.history: deque = deque(maxlen=history_size)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Module tracking
        self.module_resources: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.module_quotas: Dict[str, ResourceQuota] = {}
        self.registered_modules: Dict[str, Any] = {}  # module_name -> module_instance
        self.module_baselines: Dict[str, ModuleResourceUsage] = {}
        
        # Alerts and notifications
        self.alerts: deque = deque(maxlen=500)
        self.alert_callbacks: Dict[str, List[Callable[[ResourceAlert], None]]] = defaultdict(list)
        
        # Profiling
        self.profiling_enabled = False
        self.memory_profiling = False
        
        # Enhanced thresholds
        self.thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_usage_percent": 90.0,
            "sage_memory_mb": 1000.0,
            "module_memory_mb": 100.0,
            "module_cpu_percent": 30.0,
            "error_rate_per_minute": 10
        }
        
        # Legacy callbacks (maintained for compatibility)
        self.callbacks: Dict[str, List[Callable[[ResourceSnapshot], None]]] = {
            "high_cpu": [],
            "high_memory": [],
            "high_disk": [],
            "sage_memory_limit": []
        }
        
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.logger = logging.getLogger(__name__)
        
        if PSUTIL_AVAILABLE:
            self.sage_process = psutil.Process()
            self.network_baseline = psutil.net_io_counters()
        else:
            self.sage_process = None
            self.network_baseline = None
        
        # Statistics tracking
        self.stats = {
            'total_alerts': 0,
            'quota_violations': 0,
            'modules_monitored': 0,
            'snapshots_taken': 0,
            'profiling_sessions': 0
        }
        
    def register_module(self, module_name: str, module_instance: Any, quota: Optional[ResourceQuota] = None):
        """Register a module for resource tracking"""
        self.registered_modules[module_name] = module_instance
        
        if quota:
            self.module_quotas[module_name] = quota
        else:
            # Create default quota
            self.module_quotas[module_name] = ResourceQuota(module_name=module_name)
            
        # Take baseline measurement
        baseline = self._measure_module_resources(module_name, module_instance)
        self.module_baselines[module_name] = baseline
        
        self.stats['modules_monitored'] = len(self.registered_modules)
        self.logger.info(f"Registered module {module_name} for resource monitoring")
        
    def unregister_module(self, module_name: str):
        """Unregister a module from resource tracking"""
        if module_name in self.registered_modules:
            del self.registered_modules[module_name]
            
        if module_name in self.module_quotas:
            del self.module_quotas[module_name]
            
        if module_name in self.module_baselines:
            del self.module_baselines[module_name]
            
        if module_name in self.module_resources:
            del self.module_resources[module_name]
            
        self.stats['modules_monitored'] = len(self.registered_modules)
        self.logger.info(f"Unregistered module {module_name} from resource monitoring")
        
    def set_module_quota(self, module_name: str, quota: ResourceQuota):
        """Set or update resource quota for a module"""
        self.module_quotas[module_name] = quota
        self.logger.info(f"Updated quota for module {module_name}")
        
    def enable_profiling(self, memory_profiling: bool = True):
        """Enable detailed profiling"""
        self.profiling_enabled = True
        self.memory_profiling = memory_profiling
        
        if memory_profiling:
            tracemalloc.start()
            
        self.stats['profiling_sessions'] += 1
        self.logger.info(f"Profiling enabled (memory={memory_profiling})")
        
    def disable_profiling(self):
        """Disable profiling"""
        self.profiling_enabled = False
        
        if self.memory_profiling:
            tracemalloc.stop()
            self.memory_profiling = False
            
        self.logger.info("Profiling disabled")
        
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
            
    def add_alert_callback(self, alert_type: str, callback: Callable[[ResourceAlert], None]):
        """Add callback for resource alerts"""
        self.alert_callbacks[alert_type].append(callback)
        self.logger.info(f"Added alert callback for {alert_type}")
        
    def _measure_module_resources(self, module_name: str, module_instance: Any) -> ModuleResourceUsage:
        """Measure current resource usage for a module"""
        try:
            timestamp = time.time()
            
            # Initialize with default values
            usage = ModuleResourceUsage(
                module_name=module_name,
                timestamp=timestamp
            )
            
            # Try to get module-specific metrics
            if hasattr(module_instance, 'get_resource_usage'):
                try:
                    module_metrics = module_instance.get_resource_usage()
                    if isinstance(module_metrics, dict):
                        usage.memory_mb = module_metrics.get('memory_mb', 0.0)
                        usage.cpu_percent = module_metrics.get('cpu_percent', 0.0)
                        usage.thread_count = module_metrics.get('thread_count', 0)
                        usage.file_handles = module_metrics.get('file_handles', 0)
                        usage.cache_usage_mb = module_metrics.get('cache_usage_mb', 0.0)
                        usage.error_count = module_metrics.get('error_count', 0)
                        usage.status = module_metrics.get('status', 'running')
                except Exception as e:
                    self.logger.warning(f"Failed to get resource usage from {module_name}: {e}")
                    
            # Get system-level metrics if possible
            if hasattr(module_instance, 'is_loaded'):
                usage.status = 'running' if module_instance.is_loaded else 'stopped'
                
            # Memory profiling if enabled
            if self.memory_profiling and tracemalloc.is_tracing():
                try:
                    current, peak = tracemalloc.get_traced_memory()
                    usage.memory_mb = current / 1024 / 1024
                except Exception:
                    pass
                    
            # Get event queue size if module has event bus connection
            if hasattr(module_instance, 'event_bus') and module_instance.event_bus:
                try:
                    bus_stats = module_instance.event_bus.get_statistics()
                    usage.event_queue_size = bus_stats.get('queue_size', 0)
                except Exception:
                    pass
                    
            usage.last_activity = timestamp
            return usage
            
        except Exception as e:
            self.logger.error(f"Error measuring resources for {module_name}: {e}")
            return ModuleResourceUsage(
                module_name=module_name,
                timestamp=time.time(),
                status='error'
            )
            
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
            if not PSUTIL_AVAILABLE:
                # Return minimal snapshot when psutil is not available
                snapshot = ResourceSnapshot(
                    timestamp=time.time(),
                    cpu_percent=0.0,
                    memory_percent=0.0,
                    memory_mb=0.0,
                    disk_usage_percent=0.0,
                    network_bytes_sent=0,
                    network_bytes_recv=0,
                    process_count=0,
                    sage_memory_mb=0.0,
                    sage_cpu_percent=0.0,
                    module_resources={}
                )
                self.stats['snapshots_taken'] += 1
                return snapshot
            
            # System resources
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            # SAGE process resources
            sage_memory = self.sage_process.memory_info() if self.sage_process else None
            sage_cpu = self.sage_process.cpu_percent() if self.sage_process else 0.0
            
            # Module resources
            module_resources = {}
            for module_name, module_instance in self.registered_modules.items():
                try:
                    module_usage = self._measure_module_resources(module_name, module_instance)
                    module_resources[module_name] = module_usage
                    
                    # Store in module history
                    self.module_resources[module_name].append(module_usage)
                    
                    # Check quotas and generate alerts
                    await self._check_module_quota(module_name, module_usage)
                    
                except Exception as e:
                    self.logger.error(f"Error measuring {module_name} resources: {e}")
            
            snapshot = ResourceSnapshot(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_mb=memory.used / 1024 / 1024,
                disk_usage_percent=disk.percent,
                network_bytes_sent=network.bytes_sent - (self.network_baseline.bytes_sent if self.network_baseline else 0),
                network_bytes_recv=network.bytes_recv - (self.network_baseline.bytes_recv if self.network_baseline else 0),
                process_count=len(psutil.pids()),
                sage_memory_mb=sage_memory.rss / 1024 / 1024 if sage_memory else 0.0,
                sage_cpu_percent=sage_cpu,
                module_resources=module_resources
            )
            
            self.stats['snapshots_taken'] += 1
            return snapshot
            
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
                sage_cpu_percent=0.0,
                module_resources={}
            )
            
    async def _check_module_quota(self, module_name: str, usage: ModuleResourceUsage):
        """Check if module exceeds its resource quota"""
        if module_name not in self.module_quotas:
            return
            
        quota = self.module_quotas[module_name]
        if not quota.enabled:
            return
            
        alerts = []
        
        # Check memory quota
        if usage.memory_mb > quota.max_memory_mb:
            alert = ResourceAlert(
                module_name=module_name,
                alert_type="quota_exceeded",
                message=f"Memory usage {usage.memory_mb:.1f}MB exceeds quota {quota.max_memory_mb:.1f}MB",
                severity="high",
                timestamp=time.time(),
                metrics={"memory_mb": usage.memory_mb, "quota_mb": quota.max_memory_mb}
            )
            alerts.append(alert)
            
        # Check CPU quota
        if usage.cpu_percent > quota.max_cpu_percent:
            alert = ResourceAlert(
                module_name=module_name,
                alert_type="quota_exceeded",
                message=f"CPU usage {usage.cpu_percent:.1f}% exceeds quota {quota.max_cpu_percent:.1f}%",
                severity="medium",
                timestamp=time.time(),
                metrics={"cpu_percent": usage.cpu_percent, "quota_percent": quota.max_cpu_percent}
            )
            alerts.append(alert)
            
        # Check thread quota
        if usage.thread_count > quota.max_threads:
            alert = ResourceAlert(
                module_name=module_name,
                alert_type="quota_exceeded",
                message=f"Thread count {usage.thread_count} exceeds quota {quota.max_threads}",
                severity="medium",
                timestamp=time.time(),
                metrics={"thread_count": usage.thread_count, "quota_threads": quota.max_threads}
            )
            alerts.append(alert)
            
        # Process alerts
        for alert in alerts:
            self.alerts.append(alert)
            self.stats['total_alerts'] += 1
            self.stats['quota_violations'] += 1
            
            # Trigger callbacks
            for callback in self.alert_callbacks[alert.alert_type]:
                try:
                    await callback(alert) if asyncio.iscoroutinefunction(callback) else callback(alert)
                except Exception as e:
                    self.logger.error(f"Error in alert callback: {e}")
                    
            self.logger.warning(f"[{module_name}] {alert.message}")
            
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
            if not PSUTIL_AVAILABLE:
                return {
                    "cpu_count": 0,
                    "cpu_count_logical": 0,
                    "memory_total_gb": 0.0,
                    "disk_total_gb": 0.0,
                    "platform": 'unknown',
                    "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
                    "sage_pid": 0,
                    "psutil_available": False
                }
            
            return {
                "cpu_count": psutil.cpu_count(),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "memory_total_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024,
                "disk_total_gb": psutil.disk_usage('/').total / 1024 / 1024 / 1024,
                "platform": psutil.WINDOWS if hasattr(psutil, 'WINDOWS') else 'linux',
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
                "sage_pid": self.sage_process.pid if self.sage_process else 0,
                "psutil_available": True
            }
        except Exception as e:
            self.logger.error(f"Failed to get system info: {e}")
            return {"error": str(e), "psutil_available": PSUTIL_AVAILABLE}
            
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
        
    def get_module_resource_usage(self, module_name: str) -> Dict[str, Any]:
        """Get detailed resource usage for a specific module"""
        if module_name not in self.module_resources:
            return {"error": f"Module {module_name} not registered"}
            
        history = list(self.module_resources[module_name])
        if not history:
            return {"error": f"No resource data for module {module_name}"}
            
        current = history[-1]
        
        # Calculate averages over different time periods
        now = time.time()
        recent_5min = [usage for usage in history if now - usage.timestamp <= 300]
        recent_1hour = [usage for usage in history if now - usage.timestamp <= 3600]
        
        def avg_usage(usages, attr):
            if not usages:
                return 0.0
            return sum(getattr(u, attr) for u in usages) / len(usages)
            
        return {
            "module_name": module_name,
            "current": {
                "memory_mb": current.memory_mb,
                "cpu_percent": current.cpu_percent,
                "thread_count": current.thread_count,
                "file_handles": current.file_handles,
                "cache_usage_mb": current.cache_usage_mb,
                "event_queue_size": current.event_queue_size,
                "error_count": current.error_count,
                "status": current.status,
                "last_activity": current.last_activity
            },
            "averages": {
                "memory_mb_5min": avg_usage(recent_5min, "memory_mb"),
                "cpu_percent_5min": avg_usage(recent_5min, "cpu_percent"),
                "memory_mb_1hour": avg_usage(recent_1hour, "memory_mb"),
                "cpu_percent_1hour": avg_usage(recent_1hour, "cpu_percent")
            },
            "quota": self.module_quotas.get(module_name, ResourceQuota(module_name)).__dict__,
            "baseline": self.module_baselines.get(module_name, {}).__dict__ if module_name in self.module_baselines else {},
            "history_points": len(history)
        }
        
    def get_all_module_usage(self) -> Dict[str, Dict[str, Any]]:
        """Get resource usage for all registered modules"""
        return {
            module_name: self.get_module_resource_usage(module_name)
            for module_name in self.registered_modules.keys()
        }
        
    def get_resource_alerts(self, module_name: Optional[str] = None, 
                           limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent resource alerts"""
        alerts = list(self.alerts)
        
        if module_name:
            alerts = [alert for alert in alerts if alert.module_name == module_name]
            
        # Sort by timestamp (newest first) and limit
        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        alerts = alerts[:limit]
        
        return [alert.__dict__ for alert in alerts]
        
    def get_resource_summary(self) -> Dict[str, Any]:
        """Get a comprehensive resource summary"""
        return {
            "system": self.get_statistics(),
            "modules": {
                "registered_count": len(self.registered_modules),
                "active_modules": list(self.registered_modules.keys()),
                "usage_summary": self.get_all_module_usage()
            },
            "quotas": {
                module_name: quota.__dict__ 
                for module_name, quota in self.module_quotas.items()
            },
            "alerts": {
                "total_count": len(self.alerts),
                "recent_10": self.get_resource_alerts(limit=10)
            },
            "statistics": self.stats,
            "profiling": {
                "enabled": self.profiling_enabled,
                "memory_profiling": self.memory_profiling
            }
        }
