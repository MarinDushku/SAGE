"""
Logger - Centralized logging system for SAGE
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any
import sys
from datetime import datetime


class Logger:
    """Centralized logging system for SAGE"""
    
    def __init__(self, name: str = "SAGE", log_dir: str = "data/logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.loggers: Dict[str, logging.Logger] = {}
        self.setup_logging()
        
    def setup_logging(self) -> None:
        """Setup the logging configuration"""
        # Create logs directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create main logger
        main_logger = logging.getLogger(self.name)
        main_logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        main_logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        main_logger.addHandler(console_handler)
        
        # File handler with rotation
        log_file = self.log_dir / f"{self.name.lower()}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        main_logger.addHandler(file_handler)
        
        # Error file handler
        error_file = self.log_dir / f"{self.name.lower()}_errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        main_logger.addHandler(error_handler)
        
        self.loggers[self.name] = main_logger
        
    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger for a specific component"""
        full_name = f"{self.name}.{name}" if name != self.name else name
        
        if full_name not in self.loggers:
            logger = logging.getLogger(full_name)
            logger.setLevel(logging.DEBUG)
            
            # Don't add handlers if parent logger handles it
            if not logger.handlers and name != self.name:
                # Module-specific file handler
                module_log_file = self.log_dir / f"{name.lower()}.log"
                module_handler = logging.handlers.RotatingFileHandler(
                    module_log_file,
                    maxBytes=5*1024*1024,  # 5MB
                    backupCount=2,
                    encoding='utf-8'
                )
                module_handler.setLevel(logging.DEBUG)
                module_formatter = logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
                )
                module_handler.setFormatter(module_formatter)
                logger.addHandler(module_handler)
                
            self.loggers[full_name] = logger
            
        return self.loggers[full_name]
        
    def set_level(self, level: str, logger_name: Optional[str] = None) -> None:
        """Set logging level for a specific logger or all loggers"""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        log_level = level_map.get(level.upper(), logging.INFO)
        
        if logger_name:
            if logger_name in self.loggers:
                self.loggers[logger_name].setLevel(log_level)
        else:
            # Set level for all loggers
            for logger in self.loggers.values():
                logger.setLevel(log_level)
                
    def debug(self, message: str, logger_name: Optional[str] = None) -> None:
        """Log debug message"""
        logger = self.get_logger(logger_name or self.name)
        logger.debug(message)
        
    def info(self, message: str, logger_name: Optional[str] = None) -> None:
        """Log info message"""
        logger = self.get_logger(logger_name or self.name)
        logger.info(message)
        
    def warning(self, message: str, logger_name: Optional[str] = None) -> None:
        """Log warning message"""
        logger = self.get_logger(logger_name or self.name)
        logger.warning(message)
        
    def error(self, message: str, logger_name: Optional[str] = None) -> None:
        """Log error message"""
        logger = self.get_logger(logger_name or self.name)
        logger.error(message)
        
    def critical(self, message: str, logger_name: Optional[str] = None) -> None:
        """Log critical message"""
        logger = self.get_logger(logger_name or self.name)
        logger.critical(message)
        
    def log_performance(self, operation: str, duration: float, module_name: str = "performance") -> None:
        """Log performance metrics"""
        logger = self.get_logger(module_name)
        logger.info(f"PERF: {operation} took {duration:.3f}s")
        
    def log_resource_usage(self, cpu_percent: float, memory_mb: float, module_name: str = "resources") -> None:
        """Log resource usage"""
        logger = self.get_logger(module_name)
        logger.info(f"RESOURCE: CPU={cpu_percent:.1f}% Memory={memory_mb:.1f}MB")
        
    def log_event(self, event_type: str, source: str, data: Dict[str, Any] = None) -> None:
        """Log event information"""
        logger = self.get_logger("events")
        data_str = f" Data: {data}" if data else ""
        logger.debug(f"EVENT: {event_type} from {source}{data_str}")
        
    def flush_logs(self) -> None:
        """Flush all log handlers"""
        for logger in self.loggers.values():
            for handler in logger.handlers:
                handler.flush()
                
    def get_recent_logs(self, lines: int = 50, level: str = "INFO") -> list:
        """Get recent log entries from the main log file"""
        log_file = self.log_dir / f"{self.name.lower()}.log"
        
        if not log_file.exists():
            return []
            
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                
            # Filter by level if specified
            if level != "ALL":
                filtered_lines = []
                for line in all_lines:
                    if f" - {level} - " in line or level == "DEBUG":
                        filtered_lines.append(line.strip())
                return filtered_lines[-lines:]
            else:
                return [line.strip() for line in all_lines[-lines:]]
                
        except Exception as e:
            self.error(f"Failed to read recent logs: {e}")
            return []
            
    def cleanup_old_logs(self, days: int = 30) -> None:
        """Clean up log files older than specified days"""
        try:
            cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
            
            for log_file in self.log_dir.glob("*.log*"):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    self.info(f"Cleaned up old log file: {log_file.name}")
                    
        except Exception as e:
            self.error(f"Failed to cleanup old logs: {e}")