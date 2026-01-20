import logging
import logging.config
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import json
from src.configs.settings import db_settings


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset_color = self.COLORS['RESET']
        
        # Add color to level name
        record.levelname = f"{log_color}{record.levelname}{reset_color}"
        
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'process': record.process
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
            
        return json.dumps(log_entry, ensure_ascii=False)


class LoggingConfig:
    """Centralized logging configuration for the application"""
    
    def __init__(self):
        self.settings = db_settings
        self.log_level = self._get_log_level()
        self.log_dir = self._setup_log_directory()
        
    def _get_log_level(self) -> str:
        """Get log level from environment or settings"""
        env_level = os.getenv("LOG_LEVEL", "INFO").upper()
        if db_settings.DEBUG:
            return "DEBUG"
        return env_level
    
    def _setup_log_directory(self) -> Path:
        """Create and return log directory path"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        return log_dir
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Return complete logging configuration dictionary"""
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'detailed': {
                    'format': '%(asctime)s | %(levelname)-8s | %(name)s | %(module)s.%(funcName)s:%(lineno)d | %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                },
                'colored': {
                    '()': ColoredFormatter,
                    'format': '%(asctime)s | %(levelname)-8s | %(name)s | %(module)s.%(funcName)s:%(lineno)d | %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                },
                'json': {
                    '()': JSONFormatter
                },
                'simple': {
                    'format': '%(levelname)-8s | %(name)s | %(message)s'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': self.log_level,
                    'formatter': 'colored' if sys.stdout.isatty() else 'detailed',
                    'stream': 'ext://sys.stdout'
                },
                'file_info': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': 'INFO',
                    'formatter': 'detailed',
                    'filename': str(self.log_dir / 'app.log'),
                    'maxBytes': 10485760,  # 10MB
                    'backupCount': 5,
                    'encoding': 'utf8'
                },
                'file_error': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': 'ERROR',
                    'formatter': 'detailed',
                    'filename': str(self.log_dir / 'error.log'),
                    'maxBytes': 10485760,  # 10MB
                    'backupCount': 5,
                    'encoding': 'utf8'
                },
                'file_debug': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': 'DEBUG',
                    'formatter': 'json',
                    'filename': str(self.log_dir / 'debug.log'),
                    'maxBytes': 10485760,  # 10MB
                    'backupCount': 3,
                    'encoding': 'utf8'
                }
            },
            'loggers': {
                '': {  # Root logger
                    'level': self.log_level,
                    'handlers': ['console', 'file_info', 'file_error'],
                    'propagate': False
                },
                'app': {
                    'level': self.log_level,
                    'handlers': ['console', 'file_info', 'file_error', 'file_debug'],
                    'propagate': False
                },
                'uvicorn': {
                    'level': 'INFO',
                    'handlers': ['console', 'file_info'],
                    'propagate': False
                },
                'uvicorn.access': {
                    'level': 'INFO',
                    'handlers': ['console', 'file_info'],
                    'propagate': False
                },
                'fastapi': {
                    'level': 'INFO',
                    'handlers': ['console', 'file_info'],
                    'propagate': False
                },
                'sqlalchemy': {
                    'level': 'WARNING',
                    'handlers': ['console', 'file_info'],
                    'propagate': False
                },
                'psycopg2': {
                    'level': 'WARNING',
                    'handlers': ['console', 'file_info'],
                    'propagate': False
                }
            }
        }


def setup_logging() -> logging.Logger:
    """Initialize and configure logging for the application"""
    config = LoggingConfig()
    logging_config = config.get_logging_config()
    
    # Apply the configuration
    logging.config.dictConfig(logging_config)
    
    # Get the main application logger
    logger = logging.getLogger('app')
    
    # Log the configuration
    logger.info(f"Logging initialized with level: {config.log_level}")
    logger.info(f"Log directory: {config.log_dir}")
    logger.info(f"Environment: {config.settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {config.settings.DEBUG}")
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance for the given name"""
    if name is None:
        return logging.getLogger('app')
    return logging.getLogger(f'app.{name}')


class LoggerMixin:
    """Mixin class to add logging capabilities to any class"""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        return get_logger(self.__class__.__name__)


def log_function_call(func):
    """Decorator to log function calls with parameters and execution time"""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        
        # Log function entry
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        
        start_time = datetime.now()
        try:
            result = func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.debug(f"Function {func.__name__} completed successfully in {execution_time:.4f}s")
            return result
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Function {func.__name__} failed after {execution_time:.4f}s: {str(e)}", exc_info=True)
            raise
    
    return wrapper


def log_async_function_call(func):
    """Decorator to log async function calls with parameters and execution time"""
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        
        # Log function entry
        logger.debug(f"Calling async {func.__name__} with args={args}, kwargs={kwargs}")
        
        start_time = datetime.now()
        try:
            result = await func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.debug(f"Async function {func.__name__} completed successfully in {execution_time:.4f}s")
            return result
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Async function {func.__name__} failed after {execution_time:.4f}s: {str(e)}", exc_info=True)
            raise
    
    return wrapper


# Initialize logging when this module is imported
main_logger = setup_logging()
