"""
Plugin Manager - Dynamic module loading and management for SAGE
"""

import asyncio
import importlib
import importlib.util
import sys
import os
import json
import hashlib
from typing import Dict, List, Type, Optional, Any, Set
from pathlib import Path
import logging
from dataclasses import dataclass, field
from datetime import datetime
import threading
import time

# Optional watchdog import for hot reload
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    Observer = None
    FileSystemEventHandler = None
    WATCHDOG_AVAILABLE = False

from modules import BaseModule, EventType


@dataclass
class PluginMetadata:
    """Plugin metadata and dependency information"""
    name: str
    version: str = "1.0.0"
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    requires_api_version: str = "1.0.0"
    sandboxed: bool = False
    reload_safe: bool = True
    priority: int = 5
    config_schema: Dict[str, Any] = field(default_factory=dict)
    

@dataclass
class ModuleState:
    """Track module state and lifecycle"""
    loaded_at: datetime
    last_reload: Optional[datetime] = None
    reload_count: int = 0
    health_check_passed: bool = True
    error_count: int = 0
    last_error: Optional[str] = None
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    

if WATCHDOG_AVAILABLE:
    class FileWatchHandler(FileSystemEventHandler):
        """Handle file system changes for hot reload"""
        
        def __init__(self, plugin_manager):
            self.plugin_manager = plugin_manager
            self.last_modified = {}
            
        def on_modified(self, event):
            if event.is_directory:
                return
                
            file_path = Path(event.src_path)
            if file_path.suffix == '.py':
                # Debounce rapid file changes
                now = time.time()
                if file_path in self.last_modified:
                    if now - self.last_modified[file_path] < 1.0:
                        return
                        
                self.last_modified[file_path] = now
                
                # Find module name from path
                try:
                    parts = file_path.parts
                    if 'modules' in parts:
                        module_idx = parts.index('modules')
                        if module_idx + 1 < len(parts):
                            module_name = parts[module_idx + 1]
                            asyncio.create_task(self.plugin_manager._handle_module_change(module_name))
                except Exception as e:
                    logging.getLogger(__name__).error(f"Error handling file change: {e}")
else:
    class FileWatchHandler:
        """Dummy handler when watchdog is not available"""
        def __init__(self, plugin_manager):
            pass


class PluginManager:
    """Manages dynamic loading and lifecycle of SAGE modules"""
    
    def __init__(self, modules_path: str = "modules"):
        self.modules_path = Path(modules_path)
        self.loaded_modules: Dict[str, BaseModule] = {}
        self.module_classes: Dict[str, Type[BaseModule]] = {}
        self.module_metadata: Dict[str, PluginMetadata] = {}
        self.module_states: Dict[str, ModuleState] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}
        self.reverse_dependencies: Dict[str, Set[str]] = {}
        self.loading_order: List[str] = []
        self.logger = logging.getLogger(__name__)
        self.event_bus = None
        self.config_manager = None
        self.cache_manager = None
        self.module_logger = None
        
        # Hot reload support
        self.hot_reload_enabled = False
        self.file_observer = None
        self.reload_lock = threading.Lock()
        
        # Sandboxing support
        self.sandbox_enabled = False
        self.allowed_imports: Set[str] = set()
        self.restricted_modules: Set[str] = set()
        
    def set_dependencies(self, event_bus, config_manager, cache_manager=None, logger=None):
        """Set core dependencies for modules"""
        self.event_bus = event_bus
        self.config_manager = config_manager
        self.cache_manager = cache_manager
        self.module_logger = logger
        
    def enable_hot_reload(self, enabled: bool = True):
        """Enable or disable hot reload functionality"""
        if not WATCHDOG_AVAILABLE and enabled:
            self.logger.warning("Watchdog not available, hot reload disabled")
            return
            
        self.hot_reload_enabled = enabled
        
        if enabled and not self.file_observer and WATCHDOG_AVAILABLE:
            self.file_observer = Observer()
            handler = FileWatchHandler(self)
            self.file_observer.schedule(handler, str(self.modules_path), recursive=True)
            self.file_observer.start()
            self.logger.info("Hot reload enabled")
        elif not enabled and self.file_observer:
            self.file_observer.stop()
            self.file_observer.join()
            self.file_observer = None
            self.logger.info("Hot reload disabled")
            
    def enable_sandboxing(self, enabled: bool = True, allowed_imports: List[str] = None):
        """Enable or disable module sandboxing"""
        self.sandbox_enabled = enabled
        if allowed_imports:
            self.allowed_imports.update(allowed_imports)
        self.logger.info(f"Sandboxing {'enabled' if enabled else 'disabled'}")
        
    def discover_modules(self) -> List[str]:
        """Discover available modules and load their metadata"""
        modules = []
        
        if not self.modules_path.exists():
            self.logger.warning(f"Modules path {self.modules_path} does not exist")
            return modules
            
        for module_dir in self.modules_path.iterdir():
            if (module_dir.is_dir() and 
                not module_dir.name.startswith('_') and
                (module_dir / '__init__.py').exists()):
                
                module_name = module_dir.name
                modules.append(module_name)
                
                # Load module metadata if available
                self._load_module_metadata(module_name, module_dir)
                
        self.logger.info(f"Discovered modules: {modules}")
        return modules
        
    def _load_module_metadata(self, module_name: str, module_dir: Path):
        """Load metadata for a module"""
        metadata_file = module_dir / "metadata.json"
        
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    metadata_dict = json.load(f)
                    
                metadata = PluginMetadata(
                    name=module_name,
                    **metadata_dict
                )
                self.module_metadata[module_name] = metadata
                
                # Build dependency graph
                if metadata.dependencies:
                    self.dependency_graph[module_name] = set(metadata.dependencies)
                    for dep in metadata.dependencies:
                        if dep not in self.reverse_dependencies:
                            self.reverse_dependencies[dep] = set()
                        self.reverse_dependencies[dep].add(module_name)
                        
            except Exception as e:
                self.logger.warning(f"Failed to load metadata for {module_name}: {e}")
                # Create default metadata
                self.module_metadata[module_name] = PluginMetadata(name=module_name)
        else:
            # Create default metadata
            self.module_metadata[module_name] = PluginMetadata(name=module_name)
        
    def load_module_class(self, module_name: str) -> Optional[Type[BaseModule]]:
        """Load a module class dynamically with sandboxing support"""
        try:
            # Check sandboxing restrictions
            if self.sandbox_enabled:
                metadata = self.module_metadata.get(module_name)
                if metadata and metadata.sandboxed:
                    if not self._validate_sandbox_compliance(module_name):
                        self.logger.error(f"Module {module_name} failed sandbox validation")
                        return None
            
            # Import the module package
            module_path = f"modules.{module_name}"
            
            # Force reload if module exists in sys.modules (for hot reload)
            if module_path in sys.modules:
                importlib.reload(sys.modules[module_path])
            else:
                module = importlib.import_module(module_path)
            
            module = sys.modules[module_path]
            
            # Look for a class that inherits from BaseModule
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BaseModule) and 
                    attr != BaseModule):
                    self.module_classes[module_name] = attr
                    self.logger.info(f"Loaded module class {attr.__name__} for {module_name}")
                    return attr
                    
            self.logger.warning(f"No BaseModule subclass found in {module_name}")
            return None
            
        except ImportError as e:
            self.logger.error(f"Failed to import module {module_name}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error loading module class {module_name}: {e}")
            return None
            
    def _validate_sandbox_compliance(self, module_name: str) -> bool:
        """Validate that a module complies with sandboxing rules"""
        try:
            module_dir = self.modules_path / module_name
            
            # Check all Python files in the module
            for py_file in module_dir.rglob("*.py"):
                with open(py_file, 'r') as f:
                    content = f.read()
                    
                # Basic checks for dangerous imports/operations
                dangerous_patterns = [
                    'import os', 'import sys', 'import subprocess',
                    'import shutil', 'from os', 'from sys', 'from subprocess',
                    '__import__', 'eval(', 'exec('
                ]
                
                for pattern in dangerous_patterns:
                    if pattern in content:
                        # Allow if explicitly in allowed imports
                        if pattern.replace('import ', '').replace('from ', '') not in self.allowed_imports:
                            self.logger.warning(f"Potentially unsafe operation in {py_file}: {pattern}")
                            return False
                            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating sandbox compliance for {module_name}: {e}")
            return False
            
    async def load_module(self, module_name: str, config: Optional[Dict[str, Any]] = None, force_reload: bool = False) -> bool:
        """Load and initialize a specific module with dependency resolution"""
        if module_name in self.loaded_modules and not force_reload:
            self.logger.info(f"Module {module_name} already loaded")
            return True
            
        # Check and load dependencies first
        if not await self._load_dependencies(module_name):
            self.logger.error(f"Failed to load dependencies for {module_name}")
            return False
            
        # Load the module class if not already loaded
        if module_name not in self.module_classes or force_reload:
            module_class = self.load_module_class(module_name)
            if not module_class:
                return False
        else:
            module_class = self.module_classes[module_name]
            
        try:
            # Unload existing instance if force reload
            if force_reload and module_name in self.loaded_modules:
                await self.unload_module(module_name)
                
            # Create module instance
            module_instance = module_class(module_name)
            
            # Set dependencies
            module_instance.event_bus = self.event_bus
            module_instance.config = config or (self.config_manager.get_module_config(module_name) if self.config_manager else {})
            module_instance.cache = self.cache_manager
            module_instance.logger = self.module_logger
            
            # Add lifecycle hooks
            await self._execute_lifecycle_hook(module_name, 'before_initialize', module_instance)
            
            # Initialize the module
            success = await module_instance.initialize()
            if not success:
                self.logger.error(f"Module {module_name} initialization failed")
                await self._execute_lifecycle_hook(module_name, 'initialize_failed', module_instance)
                return False
                
            # Register with event bus
            if self.event_bus and hasattr(module_instance, 'subscribed_events') and module_instance.subscribed_events:
                for event_type in module_instance.subscribed_events:
                    self.event_bus.subscribe(event_type, module_instance)
                    
            self.loaded_modules[module_name] = module_instance
            
            # Track module state
            self.module_states[module_name] = ModuleState(
                loaded_at=datetime.now(),
                last_reload=datetime.now() if force_reload else None,
                reload_count=self.module_states.get(module_name, ModuleState(loaded_at=datetime.now())).reload_count + (1 if force_reload else 0)
            )
            
            # Execute post-load hooks
            await self._execute_lifecycle_hook(module_name, 'after_initialize', module_instance)
            
            # Emit module loaded event
            if self.event_bus:
                from modules import Event, EventType
                event = Event(
                    type=EventType.MODULE_LOADED,
                    data={"module_name": module_name, "force_reload": force_reload},
                    source_module="plugin_manager"
                )
                self.event_bus.emit(event)
                
            self.logger.info(f"Successfully loaded module: {module_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load module {module_name}: {e}")
            # Update error tracking
            if module_name in self.module_states:
                state = self.module_states[module_name]
                state.error_count += 1
                state.last_error = str(e)
                state.health_check_passed = False
            return False
            
    async def _load_dependencies(self, module_name: str) -> bool:
        """Load all dependencies for a module"""
        metadata = self.module_metadata.get(module_name)
        if not metadata or not metadata.dependencies:
            return True
            
        for dep_name in metadata.dependencies:
            if dep_name not in self.loaded_modules:
                self.logger.info(f"Loading dependency {dep_name} for {module_name}")
                if not await self.load_module(dep_name):
                    self.logger.error(f"Failed to load dependency {dep_name} for {module_name}")
                    return False
                    
        return True
        
    async def _execute_lifecycle_hook(self, module_name: str, hook_name: str, module_instance: BaseModule):
        """Execute lifecycle hooks if they exist"""
        try:
            hook_method = getattr(module_instance, f"_hook_{hook_name}", None)
            if hook_method and callable(hook_method):
                if asyncio.iscoroutinefunction(hook_method):
                    await hook_method()
                else:
                    hook_method()
        except Exception as e:
            self.logger.warning(f"Error executing {hook_name} hook for {module_name}: {e}")
            
    async def unload_module(self, module_name: str) -> bool:
        """Unload a specific module"""
        if module_name not in self.loaded_modules:
            self.logger.warning(f"Module {module_name} not loaded")
            return False
            
        try:
            module_instance = self.loaded_modules[module_name]
            
            # Unsubscribe from events
            if self.event_bus:
                for event_type in module_instance.subscribed_events:
                    self.event_bus.unsubscribe(event_type, module_instance)
                    
            # Shutdown the module
            await module_instance.shutdown()
            
            # Remove from loaded modules
            del self.loaded_modules[module_name]
            
            # Emit module unloaded event
            if self.event_bus:
                from modules import Event, EventType
                event = Event(
                    type=EventType.MODULE_UNLOADED,
                    data={"module_name": module_name},
                    source_module="plugin_manager"
                )
                self.event_bus.emit(event)
                
            self.logger.info(f"Successfully unloaded module: {module_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unload module {module_name}: {e}")
            return False
            
    async def load_all_modules(self, module_list: Optional[List[str]] = None) -> Dict[str, bool]:
        """Load all discovered modules or a specific list"""
        if module_list is None:
            module_list = self.discover_modules()
            
        results = {}
        
        # Sort by dependencies using topological sort
        module_list = self._resolve_load_order(module_list)
        
        for module_name in module_list:
            result = await self.load_module(module_name)
            results[module_name] = result
            
            if not result:
                self.logger.warning(f"Failed to load module {module_name}")
                
        return results
        
    async def unload_all_modules(self) -> None:
        """Unload all loaded modules"""
        module_names = list(self.loaded_modules.keys())
        
        for module_name in module_names:
            await self.unload_module(module_name)
            
    async def reload_module(self, module_name: str) -> bool:
        """Reload a specific module with hot reload support"""
        with self.reload_lock:
            try:
                self.logger.info(f"Reloading module: {module_name}")
                
                # Check if module is reload-safe
                metadata = self.module_metadata.get(module_name)
                if metadata and not metadata.reload_safe:
                    self.logger.warning(f"Module {module_name} is not marked as reload-safe")
                    return False
                
                # Store dependents to reload them too
                dependents = self.reverse_dependencies.get(module_name, set())
                
                # Unload dependents first
                for dependent in dependents:
                    if dependent in self.loaded_modules:
                        await self.unload_module(dependent)
                
                # Unload the module itself
                if module_name in self.loaded_modules:
                    await self.unload_module(module_name)
                    
                # Clear caches
                if module_name in self.module_classes:
                    del self.module_classes[module_name]
                    
                # Clear from sys.modules to force reimport
                modules_to_clear = []
                for mod_name in sys.modules:
                    if mod_name.startswith(f"modules.{module_name}"):
                        modules_to_clear.append(mod_name)
                        
                for mod_name in modules_to_clear:
                    del sys.modules[mod_name]
                    
                # Reload the module
                success = await self.load_module(module_name, force_reload=True)
                
                # Reload dependents
                for dependent in dependents:
                    await self.load_module(dependent, force_reload=True)
                    
                return success
                
            except Exception as e:
                self.logger.error(f"Error reloading module {module_name}: {e}")
                return False
                
    async def _handle_module_change(self, module_name: str):
        """Handle file system changes in module directory"""
        if not self.hot_reload_enabled:
            return
            
        if module_name in self.loaded_modules:
            self.logger.info(f"File change detected in {module_name}, triggering reload")
            await self.reload_module(module_name)
            
    def _resolve_load_order(self, modules: List[str]) -> List[str]:
        """Resolve module loading order using topological sort"""
        # Build in-degree count (how many dependencies each module has)
        in_degree = {module: 0 for module in modules}
        
        # Count dependencies for each module
        for module in modules:
            deps = self.dependency_graph.get(module, set())
            # Only count dependencies that are also in our modules list
            deps_in_list = [dep for dep in deps if dep in modules]
            in_degree[module] = len(deps_in_list)
                    
        # Topological sort using Kahn's algorithm
        queue = [module for module in modules if in_degree[module] == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            # For each module that depends on current, reduce its in-degree
            for module in modules:
                if module != current:
                    deps = self.dependency_graph.get(module, set())
                    if current in deps:
                        in_degree[module] -= 1
                        if in_degree[module] == 0:
                            queue.append(module)
                        
        # Check for circular dependencies
        if len(result) != len(modules):
            self.logger.warning("Circular dependencies detected, using fallback order")
            return sorted(modules)  # Fallback to alphabetical
            
        return result
        
    def get_module(self, module_name: str) -> Optional[BaseModule]:
        """Get a loaded module instance"""
        return self.loaded_modules.get(module_name)
        
    def is_module_loaded(self, module_name: str) -> bool:
        """Check if a module is loaded"""
        return module_name in self.loaded_modules
        
    def get_loaded_modules(self) -> List[str]:
        """Get list of loaded module names"""
        return list(self.loaded_modules.keys())
        
    async def get_module_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all modules"""
        status = {}
        
        for name, module in self.loaded_modules.items():
            try:
                resource_usage = await module.get_resource_usage()
                status[name] = {
                    "loaded": module.is_loaded,
                    "subscribed_events": [e.value for e in module.subscribed_events],
                    **resource_usage
                }
            except Exception as e:
                status[name] = {
                    "loaded": False,
                    "error": str(e)
                }
                
        return status
    
    async def health_check(self, module_name: Optional[str] = None) -> Dict[str, bool]:
        """Perform health checks on modules"""
        results = {}
        
        modules_to_check = [module_name] if module_name else self.loaded_modules.keys()
        
        for name in modules_to_check:
            if name not in self.loaded_modules:
                results[name] = False
                continue
                
            try:
                module = self.loaded_modules[name]
                
                # Basic health check
                is_healthy = module.is_loaded
                
                # Custom health check if available
                if hasattr(module, 'health_check'):
                    custom_result = await module.health_check()
                    is_healthy = is_healthy and custom_result
                    
                results[name] = is_healthy
                
                # Update state
                if name in self.module_states:
                    self.module_states[name].health_check_passed = is_healthy
                    
            except Exception as e:
                self.logger.error(f"Health check failed for {name}: {e}")
                results[name] = False
                if name in self.module_states:
                    self.module_states[name].health_check_passed = False
                    self.module_states[name].last_error = str(e)
                    
        return results
        
    def get_dependency_graph(self) -> Dict[str, Any]:
        """Get the complete dependency graph"""
        return {
            "dependencies": {k: list(v) for k, v in self.dependency_graph.items()},
            "reverse_dependencies": {k: list(v) for k, v in self.reverse_dependencies.items()},
            "loading_order": self.loading_order
        }
        
    def validate_dependencies(self) -> Dict[str, List[str]]:
        """Validate all module dependencies"""
        issues = {}
        
        for module_name, deps in self.dependency_graph.items():
            module_issues = []
            
            for dep in deps:
                # Check if dependency exists
                if dep not in self.module_metadata:
                    module_issues.append(f"Missing dependency: {dep}")
                    continue
                    
            if module_issues:
                issues[module_name] = module_issues
                
        return issues
        
    def create_plugin_template(self, plugin_name: str) -> bool:
        """Create a new plugin template"""
        try:
            plugin_dir = self.modules_path / plugin_name
            plugin_dir.mkdir(exist_ok=True)
            
            # Create __init__.py
            init_content = f'''"""
{plugin_name.title()} Module - Generated template
"""

import asyncio
from typing import Dict, Any, Optional

from modules import BaseModule, EventType, Event


class {plugin_name.title()}Module(BaseModule):
    """Main {plugin_name} module"""
    
    def __init__(self, name: str = "{plugin_name}"):
        super().__init__(name)
        
        # Subscribe to relevant events
        self.subscribed_events = [
            # Add your event subscriptions here
        ]
        
    async def initialize(self) -> bool:
        """Initialize the {plugin_name} module"""
        try:
            self.log(f"Initializing {plugin_name} module...")
            
            # Add your initialization code here
            
            self.is_loaded = True
            self.log(f"{plugin_name.title()} module initialized successfully")
            return True
            
        except Exception as e:
            self.log(f"Failed to initialize {plugin_name} module: {{e}}", "error")
            return False
            
    async def shutdown(self) -> None:
        """Shutdown the {plugin_name} module"""
        try:
            self.log(f"Shutting down {plugin_name} module...")
            
            # Add your cleanup code here
            
            self.is_loaded = False
            self.log(f"{plugin_name.title()} module shutdown completed")
            
        except Exception as e:
            self.log(f"Error during {plugin_name} module shutdown: {{e}}", "error")
            
    async def handle_event(self, event: Event) -> Optional[Any]:
        """Handle events from other modules"""
        try:
            # Add your event handling logic here
            self.log(f"Received event: {{event.type}}")
            return None
            
        except Exception as e:
            self.log(f"Error handling event {{event.type}}: {{e}}", "error")
            return None

__all__ = ['{plugin_name.title()}Module']
'''
            
            with open(plugin_dir / "__init__.py", 'w') as f:
                f.write(init_content)
                
            # Create metadata.json
            metadata_content = {
                "version": "1.0.0",
                "dependencies": [],
                "optional_dependencies": [],
                "provides": [plugin_name],
                "requires_api_version": "1.0.0",
                "sandboxed": False,
                "reload_safe": True,
                "priority": 5,
                "config_schema": {
                    "enabled": {"type": "boolean", "default": True}
                }
            }
            
            with open(plugin_dir / "metadata.json", 'w') as f:
                json.dump(metadata_content, f, indent=2)
                
            self.logger.info(f"Created plugin template: {plugin_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create plugin template {plugin_name}: {e}")
            return False
            
    def get_plugin_manager_stats(self) -> Dict[str, Any]:
        """Get plugin manager statistics"""
        return {
            "total_discovered": len(self.module_metadata),
            "total_loaded": len(self.loaded_modules),
            "hot_reload_enabled": self.hot_reload_enabled,
            "sandbox_enabled": self.sandbox_enabled,
            "dependency_graph_size": len(self.dependency_graph),
            "modules_with_errors": len([s for s in self.module_states.values() if not s.health_check_passed]),
            "total_reloads": sum(s.reload_count for s in self.module_states.values()),
            "average_error_count": sum(s.error_count for s in self.module_states.values()) / max(len(self.module_states), 1)
        }
        
    def __del__(self):
        """Cleanup on destruction"""
        if hasattr(self, 'file_observer') and self.file_observer:
            try:
                self.file_observer.stop()
                self.file_observer.join()
            except:
                pass