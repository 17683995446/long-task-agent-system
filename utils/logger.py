"""
超长任务Agent树形双生子模块化执行系统 - 日志系统实现
Logger Implementation for Long-Task Agent Twin-Module Execution System

阶段7：日志系统实现
遵循原则：图难于其易，为大于其细
核心约束：模块级日志隔离，分级输出
"""

from typing import Any, Dict, List, Optional, TextIO, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import threading
import sys
import os

from core_types.core_types import ModuleID, TaskID


# =============================================================================
# 1. 日志级别枚举 (Log Level Enumeration)
# =============================================================================

class LogLevel(Enum):
    """
    日志级别枚举
    从低到高：DEBUG < INFO < WARNING < ERROR < CRITICAL
    """
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    
    def __lt__(self, other):
        if isinstance(other, LogLevel):
            return self.value < other.value
        return NotImplemented
    
    def __le__(self, other):
        if isinstance(other, LogLevel):
            return self.value <= other.value
        return NotImplemented
    
    def __gt__(self, other):
        if isinstance(other, LogLevel):
            return self.value > other.value
        return NotImplemented
    
    def __ge__(self, other):
        if isinstance(other, LogLevel):
            return self.value >= other.value
        return NotImplemented


# =============================================================================
# 2. 日志记录 (Log Record)
# =============================================================================

@dataclass
class LogRecord:
    """
    日志记录
    存储单条日志的完整信息
    """
    timestamp: datetime
    level: LogLevel
    message: str
    module_id: Optional[ModuleID] = None
    module_name: str = ""
    task_id: Optional[TaskID] = None
    context: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[Exception] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "message": self.message,
            "module_id": str(self.module_id) if self.module_id else None,
            "module_name": self.module_name,
            "task_id": str(self.task_id) if self.task_id else None,
            "context": self.context,
            "exception": str(self.exception) if self.exception else None,
        }


# =============================================================================
# 3. 日志格式化器 (Log Formatter)
# =============================================================================

class LogFormatter:
    """
    日志格式化器
    将LogRecord格式化为字符串
    """
    
    # 日志级别颜色映射（用于终端输出）
    LEVEL_COLORS = {
        LogLevel.DEBUG: "\033[36m",      # 青色
        LogLevel.INFO: "\033[32m",       # 绿色
        LogLevel.WARNING: "\033[33m",    # 黄色
        LogLevel.ERROR: "\033[31m",      # 红色
        LogLevel.CRITICAL: "\033[35m",   # 紫色
    }
    RESET_COLOR = "\033[0m"
    
    def __init__(
        self,
        fmt: str = "[{timestamp}] [{level}] [{module}] {message}",
        datefmt: str = "%Y-%m-%d %H:%M:%S",
        use_colors: bool = False,
    ):
        """
        初始化格式化器
        
        Args:
            fmt: 格式字符串，可用字段：timestamp, level, module, message, task
            datefmt: 日期格式
            use_colors: 是否使用颜色
        """
        self._fmt = fmt
        self._datefmt = datefmt
        self._use_colors = use_colors
    
    def format(self, record: LogRecord) -> str:
        """
        格式化日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            str: 格式化后的字符串
        """
        timestamp = record.timestamp.strftime(self._datefmt)
        level = record.level.name
        module = record.module_name or "SYSTEM"
        message = record.message
        task = str(record.task_id) if record.task_id else "-"
        
        formatted = self._fmt.format(
            timestamp=timestamp,
            level=level,
            module=module,
            message=message,
            task=task,
        )
        
        # 添加颜色
        if self._use_colors and record.level in self.LEVEL_COLORS:
            color = self.LEVEL_COLORS[record.level]
            formatted = f"{color}{formatted}{self.RESET_COLOR}"
        
        # 添加异常信息
        if record.exception:
            formatted += f"\nException: {record.exception}"
        
        return formatted


# =============================================================================
# 4. 日志处理器 (Log Handler)
# =============================================================================

class LogHandler:
    """
    日志处理器基类
    """
    
    def __init__(self, level: LogLevel = LogLevel.DEBUG, formatter: Optional[LogFormatter] = None):
        """
        初始化处理器
        
        Args:
            level: 最低处理级别
            formatter: 格式化器
        """
        self._level = level
        self._formatter = formatter or LogFormatter()
        self._lock = threading.Lock()
    
    def should_handle(self, record: LogRecord) -> bool:
        """检查是否应该处理该记录"""
        return record.level >= self._level
    
    def handle(self, record: LogRecord) -> None:
        """处理日志记录（子类实现）"""
        raise NotImplementedError
    
    def format(self, record: LogRecord) -> str:
        """格式化日志记录"""
        return self._formatter.format(record)


class ConsoleHandler(LogHandler):
    """
    控制台日志处理器
    输出到标准输出或标准错误
    """
    
    def __init__(
        self,
        level: LogLevel = LogLevel.DEBUG,
        formatter: Optional[LogFormatter] = None,
        use_stderr: bool = False,
        use_colors: bool = True,
    ):
        """
        初始化控制台处理器
        
        Args:
            level: 最低处理级别
            formatter: 格式化器
            use_stderr: 是否使用标准错误输出
            use_colors: 是否使用颜色
        """
        formatter = formatter or LogFormatter(use_colors=use_colors)
        super().__init__(level, formatter)
        self._use_stderr = use_stderr
        self._stream = sys.stderr if use_stderr else sys.stdout
    
    def handle(self, record: LogRecord) -> None:
        """处理日志记录"""
        if not self.should_handle(record):
            return
        
        with self._lock:
            formatted = self.format(record)
            self._stream.write(formatted + "\n")
            self._stream.flush()


class FileHandler(LogHandler):
    """
    文件日志处理器
    输出到文件
    """
    
    def __init__(
        self,
        filename: str,
        level: LogLevel = LogLevel.DEBUG,
        formatter: Optional[LogFormatter] = None,
        mode: str = "a",
        encoding: str = "utf-8",
    ):
        """
        初始化文件处理器
        
        Args:
            filename: 文件名
            level: 最低处理级别
            formatter: 格式化器
            mode: 文件打开模式
            encoding: 编码
        """
        super().__init__(level, formatter)
        self._filename = filename
        self._mode = mode
        self._encoding = encoding
        self._file: Optional[TextIO] = None
        self._open_file()
    
    def _open_file(self) -> None:
        """打开文件"""
        # 确保目录存在
        dir_path = os.path.dirname(self._filename)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        
        self._file = open(self._filename, self._mode, encoding=self._encoding)
    
    def handle(self, record: LogRecord) -> None:
        """处理日志记录"""
        if not self.should_handle(record):
            return
        
        with self._lock:
            if self._file is None:
                self._open_file()
            
            formatted = self.format(record)
            self._file.write(formatted + "\n")
            self._file.flush()
    
    def close(self) -> None:
        """关闭文件"""
        with self._lock:
            if self._file:
                self._file.close()
                self._file = None
    
    def __del__(self):
        """析构时关闭文件"""
        self.close()


class MemoryHandler(LogHandler):
    """
    内存日志处理器
    将日志存储在内存中，用于调试和测试
    """
    
    def __init__(
        self,
        level: LogLevel = LogLevel.DEBUG,
        formatter: Optional[LogFormatter] = None,
        max_records: int = 1000,
    ):
        """
        初始化内存处理器
        
        Args:
            level: 最低处理级别
            formatter: 格式化器
            max_records: 最大记录数
        """
        super().__init__(level, formatter)
        self._records: List[LogRecord] = []
        self._max_records = max_records
    
    def handle(self, record: LogRecord) -> None:
        """处理日志记录"""
        if not self.should_handle(record):
            return
        
        with self._lock:
            self._records.append(record)
            if len(self._records) > self._max_records:
                self._records.pop(0)
    
    def get_records(
        self,
        level: Optional[LogLevel] = None,
        limit: int = 100,
    ) -> List[LogRecord]:
        """
        获取日志记录
        
        Args:
            level: 级别过滤器
            limit: 最大数量
            
        Returns:
            List[LogRecord]: 日志记录列表
        """
        with self._lock:
            records = self._records.copy()
        
        if level:
            records = [r for r in records if r.level >= level]
        
        return records[-limit:]
    
    def clear(self) -> None:
        """清空记录"""
        with self._lock:
            self._records.clear()
    
    def get_formatted_logs(self, limit: int = 100) -> List[str]:
        """
        获取格式化的日志
        
        Args:
            limit: 最大数量
            
        Returns:
            List[str]: 格式化后的日志字符串列表
        """
        records = self.get_records(limit=limit)
        return [self.format(r) for r in records]


# =============================================================================
# 5. 日志器 (Logger)
# =============================================================================

class Logger:
    """
    日志器
    
    提供分级日志输出，支持：
    1. 模块级日志隔离
    2. 多个处理器
    3. 上下文信息
    
    使用方式：
        logger = Logger("ModuleName", module_id)
        logger.info("这是一条信息日志")
        logger.error("这是一条错误日志", exception=e)
    """
    
    _global_level: LogLevel = LogLevel.INFO
    _loggers: Dict[str, "Logger"] = {}
    _lock = threading.Lock()
    
    def __init__(
        self,
        name: str,
        module_id: Optional[ModuleID] = None,
        level: Optional[LogLevel] = None,
    ):
        """
        初始化日志器
        
        Args:
            name: 日志器名称（通常是模块名）
            module_id: 模块ID
            level: 日志级别，如果为None则使用全局级别
        """
        self._name = name
        self._module_id = module_id
        self._level = level
        self._handlers: List[LogHandler] = []
        self._context: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    # =====================================================================
    # 类方法：全局配置
    # =====================================================================
    
    @classmethod
    def set_global_level(cls, level: LogLevel) -> None:
        """设置全局日志级别"""
        cls._global_level = level
    
    @classmethod
    def get_global_level(cls) -> LogLevel:
        """获取全局日志级别"""
        return cls._global_level
    
    @classmethod
    def get_logger(cls, name: str, module_id: Optional[ModuleID] = None) -> "Logger":
        """
        获取或创建日志器
        
        Args:
            name: 日志器名称
            module_id: 模块ID
            
        Returns:
            Logger: 日志器实例
        """
        with cls._lock:
            if name not in cls._loggers:
                cls._loggers[name] = cls(name, module_id)
            return cls._loggers[name]
    
    @classmethod
    def remove_logger(cls, name: str) -> None:
        """移除日志器"""
        with cls._lock:
            cls._loggers.pop(name, None)
    
    @classmethod
    def clear_all_loggers(cls) -> None:
        """清除所有日志器"""
        with cls._lock:
            cls._loggers.clear()
    
    # =====================================================================
    # 属性
    # =====================================================================
    
    @property
    def name(self) -> str:
        """日志器名称"""
        return self._name
    
    @property
    def module_id(self) -> Optional[ModuleID]:
        """模块ID"""
        return self._module_id
    
    @property
    def level(self) -> LogLevel:
        """当前日志级别"""
        return self._level or self._global_level
    
    @level.setter
    def level(self, level: LogLevel) -> None:
        """设置日志级别"""
        self._level = level
    
    # =====================================================================
    # 处理器管理
    # =====================================================================
    
    def add_handler(self, handler: LogHandler) -> None:
        """添加处理器"""
        with self._lock:
            self._handlers.append(handler)
    
    def remove_handler(self, handler: LogHandler) -> None:
        """移除处理器"""
        with self._lock:
            if handler in self._handlers:
                self._handlers.remove(handler)
    
    def clear_handlers(self) -> None:
        """清除所有处理器"""
        with self._lock:
            self._handlers.clear()
    
    def has_handlers(self) -> bool:
        """是否有处理器"""
        return len(self._handlers) > 0
    
    # =====================================================================
    # 上下文管理
    # =====================================================================
    
    def set_context(self, key: str, value: Any) -> None:
        """设置上下文"""
        self._context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """获取上下文"""
        return self._context.get(key, default)
    
    def clear_context(self) -> None:
        """清除上下文"""
        self._context.clear()
    
    # =====================================================================
    # 日志记录方法
    # =====================================================================
    
    def _log(
        self,
        level: LogLevel,
        message: str,
        task_id: Optional[TaskID] = None,
        exception: Optional[Exception] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        内部日志记录方法
        
        Args:
            level: 日志级别
            message: 消息
            task_id: 任务ID
            exception: 异常
            extra_context: 额外上下文
        """
        # 检查级别
        if level < self.level:
            return
        
        # 合并上下文
        context = self._context.copy()
        if extra_context:
            context.update(extra_context)
        
        # 创建记录
        record = LogRecord(
            timestamp=datetime.now(),
            level=level,
            message=message,
            module_id=self._module_id,
            module_name=self._name,
            task_id=task_id,
            context=context,
            exception=exception,
        )
        
        # 分发到处理器
        with self._lock:
            handlers = self._handlers.copy()
        
        for handler in handlers:
            try:
                handler.handle(record)
            except Exception:
                # 处理器异常不应影响主流程
                pass
    
    def debug(self, message: str, **kwargs) -> None:
        """记录DEBUG级别日志"""
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """记录INFO级别日志"""
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """记录WARNING级别日志"""
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """记录ERROR级别日志"""
        self._log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """记录CRITICAL级别日志"""
        self._log(LogLevel.CRITICAL, message, **kwargs)
    
    # 别名
    warn = warning
    fatal = critical
    
    # =====================================================================
    # 便捷方法
    # =====================================================================
    
    def log(self, level: LogLevel, message: str, **kwargs) -> None:
        """指定级别记录日志"""
        self._log(level, message, **kwargs)
    
    def exception(self, message: str, exc: Exception, **kwargs) -> None:
        """记录异常日志"""
        self._log(LogLevel.ERROR, message, exception=exc, **kwargs)


# =============================================================================
# 6. 日志管理器 (Log Manager)
# =============================================================================

class LogManager:
    """
    日志管理器
    
    提供全局日志配置和管理
    """
    
    _instance: Optional["LogManager"] = None
    _lock = threading.Lock()
    
    def __init__(self):
        """私有初始化"""
        self._default_handlers: List[LogHandler] = []
        self._module_levels: Dict[str, LogLevel] = {}
    
    @classmethod
    def instance(cls) -> "LogManager":
        """获取单例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def setup_default_logging(
        self,
        level: LogLevel = LogLevel.INFO,
        log_file: Optional[str] = None,
        use_console: bool = True,
        use_colors: bool = True,
    ) -> None:
        """
        设置默认日志配置
        
        Args:
            level: 日志级别
            log_file: 日志文件路径
            use_console: 是否使用控制台输出
            use_colors: 是否使用颜色
        """
        Logger.set_global_level(level)
        
        # 为所有现有日志器添加处理器
        if use_console:
            console_handler = ConsoleHandler(level=level, use_colors=use_colors)
            self._default_handlers.append(console_handler)
        
        if log_file:
            file_handler = FileHandler(log_file, level=level)
            self._default_handlers.append(file_handler)
        
        # 应用到所有日志器
        for logger in Logger._loggers.values():
            for handler in self._default_handlers:
                logger.add_handler(handler)
    
    def set_module_level(self, module_name: str, level: LogLevel) -> None:
        """设置模块日志级别"""
        self._module_levels[module_name] = level
        logger = Logger._loggers.get(module_name)
        if logger:
            logger.level = level
    
    def get_module_level(self, module_name: str) -> Optional[LogLevel]:
        """获取模块日志级别"""
        return self._module_levels.get(module_name)


# =============================================================================
# 7. 便捷函数
# =============================================================================

def get_logger(name: str, module_id: Optional[ModuleID] = None) -> Logger:
    """
    获取日志器的便捷函数
    
    Args:
        name: 日志器名称
        module_id: 模块ID
        
    Returns:
        Logger: 日志器实例
    """
    return Logger.get_logger(name, module_id)


def setup_logging(
    level: LogLevel = LogLevel.INFO,
    log_file: Optional[str] = None,
    use_console: bool = True,
    use_colors: bool = True,
) -> None:
    """
    设置日志的便捷函数
    
    Args:
        level: 日志级别
        log_file: 日志文件路径
        use_console: 是否使用控制台输出
        use_colors: 是否使用颜色
    """
    LogManager.instance().setup_default_logging(
        level=level,
        log_file=log_file,
        use_console=use_console,
        use_colors=use_colors,
    )


# =============================================================================
# 模块导出列表
# =============================================================================

__all__ = [
    # 日志级别
    "LogLevel",
    
    # 日志记录
    "LogRecord",
    
    # 格式化器
    "LogFormatter",
    
    # 处理器
    "LogHandler",
    "ConsoleHandler",
    "FileHandler",
    "MemoryHandler",
    
    # 日志器
    "Logger",
    
    # 管理器
    "LogManager",
    
    # 便捷函数
    "get_logger",
    "setup_logging",
]
