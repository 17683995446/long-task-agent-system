"""
超长任务Agent树形双生子模块化执行系统 - 异常处理体系实现
Exceptions Implementation for Long-Task Agent Twin-Module Execution System

阶段9：异常处理体系实现
遵循原则：图难于其易，为大于其细
核心约束：分层异常体系，支持精确捕获
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from core_types.core_types import ModuleID, TaskID


# =============================================================================
# 1. 异常严重级别枚举 (Exception Severity Enumeration)
# =============================================================================

class ExceptionSeverity(Enum):
    """
    异常严重级别枚举
    """
    DEBUG = auto()      # 调试信息
    INFO = auto()       # 信息
    WARNING = auto()    # 警告
    ERROR = auto()      # 错误
    CRITICAL = auto()   # 严重错误
    FATAL = auto()      # 致命错误


# =============================================================================
# 2. 异常上下文 (Exception Context)
# =============================================================================

@dataclass
class ExceptionContext:
    """
    异常上下文
    存储异常发生时的上下文信息
    """
    module_id: Optional[ModuleID] = None
    module_name: str = ""
    task_id: Optional[TaskID] = None
    step_number: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "module_id": str(self.module_id) if self.module_id else None,
            "module_name": self.module_name,
            "task_id": str(self.task_id) if self.task_id else None,
            "step_number": self.step_number,
            "timestamp": self.timestamp.isoformat(),
            "extra": self.extra,
        }


# =============================================================================
# 3. 基础异常类 (Base Exception)
# =============================================================================

class ModuleException(Exception):
    """
    模块异常基类
    
    所有系统异常的基类，提供：
    1. 错误代码
    2. 错误详情
    3. 异常上下文
    4. 严重级别
    5. 可恢复标记
    
    使用方式：
        raise ModuleException(
            code="ERR_001",
            message="初始化失败",
            severity=ExceptionSeverity.ERROR,
        )
    """
    
    def __init__(
        self,
        code: str,
        message: str,
        severity: ExceptionSeverity = ExceptionSeverity.ERROR,
        context: Optional[ExceptionContext] = None,
        recoverable: bool = False,
        cause: Optional[Exception] = None,
    ):
        """
        初始化异常
        
        Args:
            code: 错误代码
            message: 错误消息
            severity: 严重级别
            context: 异常上下文
            recoverable: 是否可恢复
            cause: 原始异常
        """
        super().__init__(message)
        
        self._code = code
        self._message = message
        self._severity = severity
        self._context = context or ExceptionContext()
        self._recoverable = recoverable
        self._cause = cause
    
    @property
    def code(self) -> str:
        """错误代码"""
        return self._code
    
    @property
    def message(self) -> str:
        """错误消息"""
        return self._message
    
    @property
    def severity(self) -> ExceptionSeverity:
        """严重级别"""
        return self._severity
    
    @property
    def context(self) -> ExceptionContext:
        """异常上下文"""
        return self._context
    
    @property
    def recoverable(self) -> bool:
        """是否可恢复"""
        return self._recoverable
    
    @property
    def cause(self) -> Optional[Exception]:
        """原始异常"""
        return self._cause
    
    def with_module(self, module_id: ModuleID, module_name: str = "") -> "ModuleException":
        """
        设置模块信息（支持链式调用）
        
        Args:
            module_id: 模块ID
            module_name: 模块名称
            
        Returns:
            ModuleException: 自身
        """
        self._context.module_id = module_id
        self._context.module_name = module_name
        return self
    
    def with_task(self, task_id: TaskID) -> "ModuleException":
        """
        设置任务信息（支持链式调用）
        
        Args:
            task_id: 任务ID
            
        Returns:
            ModuleException: 自身
        """
        self._context.task_id = task_id
        return self
    
    def with_step(self, step_number: int) -> "ModuleException":
        """
        设置步骤信息（支持链式调用）
        
        Args:
            step_number: 步骤编号
            
        Returns:
            ModuleException: 自身
        """
        self._context.step_number = step_number
        return self
    
    def with_extra(self, key: str, value: Any) -> "ModuleException":
        """
        设置额外信息（支持链式调用）
        
        Args:
            key: 键
            value: 值
            
        Returns:
            ModuleException: 自身
        """
        self._context.extra[key] = value
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.__class__.__name__,
            "code": self._code,
            "message": self._message,
            "severity": self._severity.name,
            "recoverable": self._recoverable,
            "context": self._context.to_dict(),
            "cause": str(self._cause) if self._cause else None,
        }
    
    def __str__(self) -> str:
        return f"[{self._code}] {self._message}"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self._code}, severity={self._severity.name})"


# =============================================================================
# 4. 初始化异常 (Initialization Exception)
# =============================================================================

class InitException(ModuleException):
    """
    初始化异常
    
    模块初始化过程中发生的异常
    
    常见错误代码：
    - INIT_001: 参数验证失败
    - INIT_002: 资源初始化失败
    - INIT_003: 配置加载失败
    - INIT_004: 依赖初始化失败
    """
    
    def __init__(
        self,
        code: str = "INIT_000",
        message: str = "初始化异常",
        severity: ExceptionSeverity = ExceptionSeverity.ERROR,
        context: Optional[ExceptionContext] = None,
        recoverable: bool = False,
        cause: Optional[Exception] = None,
    ):
        super().__init__(code, message, severity, context, recoverable, cause)


class ParamValidationException(InitException):
    """参数验证异常"""
    
    def __init__(
        self,
        message: str = "参数验证失败",
        param_name: str = "",
        param_value: Any = None,
    ):
        super().__init__(
            code="INIT_001",
            message=message,
        )
        if param_name:
            self.with_extra("param_name", param_name)
        if param_value is not None:
            self.with_extra("param_value", str(param_value))


class ResourceInitException(InitException):
    """资源初始化异常"""
    
    def __init__(
        self,
        message: str = "资源初始化失败",
        resource_name: str = "",
    ):
        super().__init__(
            code="INIT_002",
            message=message,
        )
        if resource_name:
            self.with_extra("resource_name", resource_name)


# =============================================================================
# 5. 执行异常 (Execution Exception)
# =============================================================================

class RunException(ModuleException):
    """
    执行异常
    
    模块执行过程中发生的异常
    
    常见错误代码：
    - RUN_001: 执行前置条件不满足
    - RUN_002: 执行超时
    - RUN_003: 执行结果无效
    - RUN_004: 子模块执行失败
    """
    
    def __init__(
        self,
        code: str = "RUN_000",
        message: str = "执行异常",
        severity: ExceptionSeverity = ExceptionSeverity.ERROR,
        context: Optional[ExceptionContext] = None,
        recoverable: bool = True,  # 执行异常默认可恢复
        cause: Optional[Exception] = None,
    ):
        super().__init__(code, message, severity, context, recoverable, cause)


class PreconditionException(RunException):
    """前置条件异常"""
    
    def __init__(
        self,
        message: str = "前置条件不满足",
        precondition: str = "",
    ):
        super().__init__(
            code="RUN_001",
            message=message,
            recoverable=False,
        )
        if precondition:
            self.with_extra("precondition", precondition)


class TimeoutException(RunException):
    """超时异常"""
    
    def __init__(
        self,
        message: str = "执行超时",
        timeout_seconds: float = 0,
    ):
        super().__init__(
            code="RUN_002",
            message=message,
        )
        if timeout_seconds:
            self.with_extra("timeout_seconds", timeout_seconds)


class InvalidResultException(RunException):
    """无效结果异常"""
    
    def __init__(
        self,
        message: str = "执行结果无效",
        result: Any = None,
    ):
        super().__init__(
            code="RUN_003",
            message=message,
        )
        if result is not None:
            self.with_extra("result", str(result))


class SubmoduleException(RunException):
    """子模块执行异常"""
    
    def __init__(
        self,
        message: str = "子模块执行失败",
        submodule_id: Optional[ModuleID] = None,
    ):
        super().__init__(
            code="RUN_004",
            message=message,
        )
        if submodule_id:
            self.with_extra("submodule_id", str(submodule_id))


# =============================================================================
# 6. 校验异常 (Validation Exception)
# =============================================================================

class CheckException(ModuleException):
    """
    校验异常
    
    模块校验过程中发生的异常
    
    常见错误代码：
    - CHECK_001: 类型校验失败
    - CHECK_002: 范围校验失败
    - CHECK_003: 规则校验失败
    - CHECK_004: 一致性校验失败
    """
    
    def __init__(
        self,
        code: str = "CHECK_000",
        message: str = "校验异常",
        severity: ExceptionSeverity = ExceptionSeverity.WARNING,
        context: Optional[ExceptionContext] = None,
        recoverable: bool = True,
        cause: Optional[Exception] = None,
    ):
        super().__init__(code, message, severity, context, recoverable, cause)


class TypeCheckException(CheckException):
    """类型校验异常"""
    
    def __init__(
        self,
        message: str = "类型校验失败",
        expected_type: str = "",
        actual_type: str = "",
    ):
        super().__init__(
            code="CHECK_001",
            message=message,
        )
        if expected_type:
            self.with_extra("expected_type", expected_type)
        if actual_type:
            self.with_extra("actual_type", actual_type)


class RangeCheckException(CheckException):
    """范围校验异常"""
    
    def __init__(
        self,
        message: str = "范围校验失败",
        value: Any = None,
        min_value: Any = None,
        max_value: Any = None,
    ):
        super().__init__(
            code="CHECK_002",
            message=message,
        )
        if value is not None:
            self.with_extra("value", str(value))
        if min_value is not None:
            self.with_extra("min_value", str(min_value))
        if max_value is not None:
            self.with_extra("max_value", str(max_value))


class RuleCheckException(CheckException):
    """规则校验异常"""
    
    def __init__(
        self,
        message: str = "规则校验失败",
        rule_name: str = "",
    ):
        super().__init__(
            code="CHECK_003",
            message=message,
        )
        if rule_name:
            self.with_extra("rule_name", rule_name)


# =============================================================================
# 7. 验证异常 (Validation Exception - 用于输入验证)
# =============================================================================

class ValidationException(ModuleException):
    """
    验证异常
    
    输入验证过程中发生的异常
    
    常见错误代码：
    - VAL_001: 必填字段缺失
    - VAL_002: 格式错误
    - VAL_003: 值不允许
    """
    
    def __init__(
        self,
        code: str = "VAL_000",
        message: str = "验证异常",
        severity: ExceptionSeverity = ExceptionSeverity.WARNING,
        context: Optional[ExceptionContext] = None,
        recoverable: bool = True,
        cause: Optional[Exception] = None,
    ):
        super().__init__(code, message, severity, context, recoverable, cause)


class MissingFieldException(ValidationException):
    """必填字段缺失异常"""
    
    def __init__(
        self,
        message: str = "必填字段缺失",
        field_name: str = "",
    ):
        super().__init__(
            code="VAL_001",
            message=message,
        )
        if field_name:
            self.with_extra("field_name", field_name)


class FormatException(ValidationException):
    """格式错误异常"""
    
    def __init__(
        self,
        message: str = "格式错误",
        field_name: str = "",
        expected_format: str = "",
    ):
        super().__init__(
            code="VAL_002",
            message=message,
        )
        if field_name:
            self.with_extra("field_name", field_name)
        if expected_format:
            self.with_extra("expected_format", expected_format)


# =============================================================================
# 8. 恢复异常 (Recovery Exception)
# =============================================================================

class RecoveryException(ModuleException):
    """
    恢复异常
    
    异常恢复过程中发生的异常
    
    常见错误代码：
    - REC_001: 快照恢复失败
    - REC_002: 状态回滚失败
    - REC_003: 重试次数耗尽
    """
    
    def __init__(
        self,
        code: str = "REC_000",
        message: str = "恢复异常",
        severity: ExceptionSeverity = ExceptionSeverity.ERROR,
        context: Optional[ExceptionContext] = None,
        recoverable: bool = False,  # 恢复异常默认不可恢复
        cause: Optional[Exception] = None,
    ):
        super().__init__(code, message, severity, context, recoverable, cause)


class SnapshotRecoveryException(RecoveryException):
    """快照恢复异常"""
    
    def __init__(
        self,
        message: str = "快照恢复失败",
        snapshot_id: str = "",
    ):
        super().__init__(
            code="REC_001",
            message=message,
        )
        if snapshot_id:
            self.with_extra("snapshot_id", snapshot_id)


class RollbackException(RecoveryException):
    """回滚异常"""
    
    def __init__(
        self,
        message: str = "状态回滚失败",
    ):
        super().__init__(
            code="REC_002",
            message=message,
        )


class RetryExhaustedException(RecoveryException):
    """重试次数耗尽异常"""
    
    def __init__(
        self,
        message: str = "重试次数耗尽",
        max_retries: int = 0,
    ):
        super().__init__(
            code="REC_003",
            message=message,
        )
        if max_retries:
            self.with_extra("max_retries", max_retries)


# =============================================================================
# 9. 状态异常 (State Exception)
# =============================================================================

class StateException(ModuleException):
    """
    状态异常
    
    状态转换过程中发生的异常
    
    常见错误代码：
    - STATE_001: 非法状态转换
    - STATE_002: 状态不一致
    - STATE_003: 状态丢失
    """
    
    def __init__(
        self,
        code: str = "STATE_000",
        message: str = "状态异常",
        severity: ExceptionSeverity = ExceptionSeverity.ERROR,
        context: Optional[ExceptionContext] = None,
        recoverable: bool = True,
        cause: Optional[Exception] = None,
    ):
        super().__init__(code, message, severity, context, recoverable, cause)


class InvalidStateTransitionException(StateException):
    """非法状态转换异常"""
    
    def __init__(
        self,
        message: str = "非法状态转换",
        from_state: str = "",
        to_state: str = "",
    ):
        super().__init__(
            code="STATE_001",
            message=message,
        )
        if from_state:
            self.with_extra("from_state", from_state)
        if to_state:
            self.with_extra("to_state", to_state)


class StateInconsistencyException(StateException):
    """状态不一致异常"""
    
    def __init__(
        self,
        message: str = "状态不一致",
    ):
        super().__init__(
            code="STATE_002",
            message=message,
        )


# =============================================================================
# 10. 配置异常 (Configuration Exception)
# =============================================================================

class ConfigurationException(ModuleException):
    """
    配置异常
    
    配置相关异常
    
    常见错误代码：
    - CFG_001: 配置缺失
    - CFG_002: 配置格式错误
    - CFG_003: 配置值无效
    """
    
    def __init__(
        self,
        code: str = "CFG_000",
        message: str = "配置异常",
        severity: ExceptionSeverity = ExceptionSeverity.ERROR,
        context: Optional[ExceptionContext] = None,
        recoverable: bool = False,
        cause: Optional[Exception] = None,
    ):
        super().__init__(code, message, severity, context, recoverable, cause)


class ConfigMissingException(ConfigurationException):
    """配置缺失异常"""
    
    def __init__(
        self,
        message: str = "配置缺失",
        config_key: str = "",
    ):
        super().__init__(
            code="CFG_001",
            message=message,
        )
        if config_key:
            self.with_extra("config_key", config_key)


# =============================================================================
# 11. 双子结构异常 (Twin Structure Exception)
# =============================================================================

class TwinStructureException(ModuleException):
    """
    双子结构异常
    
    双子结构相关异常
    
    常见错误代码：
    - TWIN_001: 子模块数量不正确
    - TWIN_002: 子模块类型不匹配
    - TWIN_003: 双子结构不完整
    """
    
    def __init__(
        self,
        code: str = "TWIN_000",
        message: str = "双子结构异常",
        severity: ExceptionSeverity = ExceptionSeverity.CRITICAL,
        context: Optional[ExceptionContext] = None,
        recoverable: bool = False,
        cause: Optional[Exception] = None,
    ):
        super().__init__(code, message, severity, context, recoverable, cause)


class ChildCountException(TwinStructureException):
    """子模块数量异常"""
    
    def __init__(
        self,
        message: str = "子模块数量不正确",
        expected: int = 2,
        actual: int = 0,
    ):
        super().__init__(
            code="TWIN_001",
            message=message,
        )
        self.with_extra("expected", expected)
        self.with_extra("actual", actual)


class ChildTypeException(TwinStructureException):
    """子模块类型异常"""
    
    def __init__(
        self,
        message: str = "子模块类型不匹配",
        expected_type: str = "",
        actual_type: str = "",
    ):
        super().__init__(
            code="TWIN_002",
            message=message,
        )
        if expected_type:
            self.with_extra("expected_type", expected_type)
        if actual_type:
            self.with_extra("actual_type", actual_type)


# =============================================================================
# 12. 异常工具函数 (Exception Utilities)
# =============================================================================

def is_recoverable(exception: Exception) -> bool:
    """
    检查异常是否可恢复
    
    Args:
        exception: 异常实例
        
    Returns:
        bool: 是否可恢复
    """
    if isinstance(exception, ModuleException):
        return exception.recoverable
    return False


def get_exception_severity(exception: Exception) -> ExceptionSeverity:
    """
    获取异常严重级别
    
    Args:
        exception: 异常实例
        
    Returns:
        ExceptionSeverity: 严重级别
    """
    if isinstance(exception, ModuleException):
        return exception.severity
    return ExceptionSeverity.ERROR


def exception_to_dict(exception: Exception) -> Dict[str, Any]:
    """
    将异常转换为字典
    
    Args:
        exception: 异常实例
        
    Returns:
        Dict[str, Any]: 异常信息字典
    """
    if isinstance(exception, ModuleException):
        return exception.to_dict()
    return {
        "type": exception.__class__.__name__,
        "message": str(exception),
    }


def wrap_exception(
    exception: Exception,
    code: str = "WRAPPED",
    message: str = "",
) -> ModuleException:
    """
    将普通异常包装为ModuleException
    
    Args:
        exception: 原始异常
        code: 错误代码
        message: 错误消息
        
    Returns:
        ModuleException: 包装后的异常
    """
    if isinstance(exception, ModuleException):
        return exception
    
    return ModuleException(
        code=code,
        message=message or str(exception),
        cause=exception,
    )


# =============================================================================
# 模块导出列表
# =============================================================================

__all__ = [
    # 枚举
    "ExceptionSeverity",
    
    # 上下文
    "ExceptionContext",
    
    # 基础异常
    "ModuleException",
    
    # 初始化异常
    "InitException",
    "ParamValidationException",
    "ResourceInitException",
    
    # 执行异常
    "RunException",
    "PreconditionException",
    "TimeoutException",
    "InvalidResultException",
    "SubmoduleException",
    
    # 校验异常
    "CheckException",
    "TypeCheckException",
    "RangeCheckException",
    "RuleCheckException",
    
    # 验证异常
    "ValidationException",
    "MissingFieldException",
    "FormatException",
    
    # 恢复异常
    "RecoveryException",
    "SnapshotRecoveryException",
    "RollbackException",
    "RetryExhaustedException",
    
    # 状态异常
    "StateException",
    "InvalidStateTransitionException",
    "StateInconsistencyException",
    
    # 配置异常
    "ConfigurationException",
    "ConfigMissingException",
    
    # 双子结构异常
    "TwinStructureException",
    "ChildCountException",
    "ChildTypeException",
    
    # 工具函数
    "is_recoverable",
    "get_exception_severity",
    "exception_to_dict",
    "wrap_exception",
]
