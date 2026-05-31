"""
阶段22：二级异常处理模块
Level 2 Exception Module

职责定义：
- 异常捕获与分类
- 异常恢复策略
- 错误日志记录
"""

from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from enum import Enum, auto

from core.base_module import ControlModuleBase
from core_types.core_types import (
    ModuleID, TaskID, ModuleLevel,
    InitResult, ModuleOutput, CheckResult, SnapshotData,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)
from utils.logger import Logger


class ExceptionSeverity(Enum):
    """异常严重级别"""
    LOW = auto()       # 低级别，可忽略
    MEDIUM = auto()    # 中级别，需要记录
    HIGH = auto()      # 高级别，需要处理
    CRITICAL = auto()  # 严重级别，需要终止


class ExceptionRecord:
    """异常记录"""
    
    def __init__(
        self,
        exception_id: str,
        exception_type: str,
        message: str,
        severity: ExceptionSeverity,
        task_id: Optional[TaskID] = None
    ):
        self.exception_id = exception_id
        self.exception_type = exception_type
        self.message = message
        self.severity = severity
        self.task_id = task_id
        self.timestamp = datetime.now()
        self.resolved = False
        self.resolution = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "exception_id": self.exception_id,
            "exception_type": self.exception_type,
            "message": self.message,
            "severity": self.severity.name,
            "task_id": str(self.task_id) if self.task_id else None,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
            "resolution": self.resolution,
        }


class RecoveryStrategy:
    """恢复策略"""
    
    def __init__(
        self,
        strategy_id: str,
        name: str,
        applicable_types: List[str],
        handler: Callable[[ExceptionRecord], bool]
    ):
        self.strategy_id = strategy_id
        self.name = name
        self.applicable_types = applicable_types
        self.handler = handler
        self.enabled = True
    
    def can_handle(self, exception_type: str) -> bool:
        """是否能处理该类型异常"""
        return exception_type in self.applicable_types
    
    def execute(self, record: ExceptionRecord) -> bool:
        """执行恢复策略"""
        if not self.enabled:
            return False
        try:
            return self.handler(record)
        except Exception:
            return False


class Level2ExceptionModule(ControlModuleBase):
    """
    二级异常处理模块
    
    职责：
    1. 异常捕获与分类
    2. 异常恢复策略管理
    3. 错误日志记录
    4. 异常统计分析
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL2
        self._state.module_name = "Level2ExceptionModule"
        self._logger = Logger(f"L2Exception_{self.module_id}")
        
        # 异常记录
        self._exceptions: Dict[str, ExceptionRecord] = {}
        self._exception_history: List[ExceptionRecord] = []
        
        # 恢复策略
        self._recovery_strategies: Dict[str, RecoveryStrategy] = {}
        
        # 异常处理器
        self._exception_handlers: Dict[str, Callable] = {}
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化异常处理模块"""
        try:
            self._logger.info("二级异常处理模块初始化开始")
            
            # 1. 初始化异常存储
            self._exceptions = {}
            self._exception_history = []
            
            # 2. 注册默认恢复策略
            self._register_default_strategies()
            
            # 3. 注册默认异常处理器
            self._register_default_handlers()
            
            self._logger.info("二级异常处理模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="二级异常处理模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"二级异常处理模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L2E_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _register_default_strategies(self) -> None:
        """注册默认恢复策略"""
        self._recovery_strategies = {
            "retry": RecoveryStrategy(
                strategy_id="retry",
                name="重试策略",
                applicable_types=["RuntimeError", "TimeoutError"],
                handler=self._retry_handler
            ),
            "fallback": RecoveryStrategy(
                strategy_id="fallback",
                name="降级策略",
                applicable_types=["ResourceError", "ServiceUnavailable"],
                handler=self._fallback_handler
            ),
            "ignore": RecoveryStrategy(
                strategy_id="ignore",
                name="忽略策略",
                applicable_types=["Warning", "Info"],
                handler=self._ignore_handler
            ),
        }
    
    def _register_default_handlers(self) -> None:
        """注册默认异常处理器"""
        self._exception_handlers = {
            "RuntimeError": self._handle_runtime_error,
            "ValueError": self._handle_value_error,
        }
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行异常处理逻辑"""
        self._logger.info("二级异常处理模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 1. 获取待处理异常（从输入数据）
            pending_exceptions = request.module_input.data.get("pending_exceptions", []) if request.module_input else []
            
            # 2. 处理每个异常
            processed = []
            for exc_data in pending_exceptions:
                record = self._process_exception(exc_data, task_id)
                processed.append(record.to_dict())
            
            # 3. 生成异常报告
            report = self._generate_exception_report()
            
            self._logger.info("二级异常处理模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "processed_exceptions": processed,
                    "exception_report": report,
                },
                message="异常处理完成"
            )
            
        except Exception as e:
            self._logger.error(f"二级异常处理模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L2E_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _process_exception(
        self,
        exc_data: Dict[str, Any],
        task_id: TaskID
    ) -> ExceptionRecord:
        """处理单个异常"""
        # 1. 创建异常记录
        record = ExceptionRecord(
            exception_id=f"exc_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self._exceptions)}",
            exception_type=exc_data.get("type", "Unknown"),
            message=exc_data.get("message", ""),
            severity=ExceptionSeverity[exc_data.get("severity", "MEDIUM")],
            task_id=task_id
        )
        
        # 2. 存储异常
        self._exceptions[record.exception_id] = record
        self._exception_history.append(record)
        
        # 3. 尝试恢复
        recovered = self._attempt_recovery(record)
        if recovered:
            record.resolved = True
            record.resolution = "自动恢复成功"
        
        return record
    
    def _attempt_recovery(self, record: ExceptionRecord) -> bool:
        """尝试恢复"""
        for strategy in self._recovery_strategies.values():
            if strategy.can_handle(record.exception_type):
                if strategy.execute(record):
                    return True
        return False
    
    def _retry_handler(self, record: ExceptionRecord) -> bool:
        """重试处理器"""
        self._logger.info(f"尝试重试恢复: {record.exception_id}")
        return True  # 模拟成功
    
    def _fallback_handler(self, record: ExceptionRecord) -> bool:
        """降级处理器"""
        self._logger.info(f"尝试降级恢复: {record.exception_id}")
        return True
    
    def _ignore_handler(self, record: ExceptionRecord) -> bool:
        """忽略处理器"""
        self._logger.info(f"忽略异常: {record.exception_id}")
        return True
    
    def _handle_runtime_error(self, error: Exception) -> bool:
        """处理运行时错误"""
        self._logger.warning(f"运行时错误: {error}")
        return True
    
    def _handle_value_error(self, error: Exception) -> bool:
        """处理值错误"""
        self._logger.warning(f"值错误: {error}")
        return True
    
    def _generate_exception_report(self) -> Dict[str, Any]:
        """生成异常报告"""
        severity_counts = {s.name: 0 for s in ExceptionSeverity}
        for record in self._exceptions.values():
            severity_counts[record.severity.name] += 1
        
        return {
            "total_exceptions": len(self._exceptions),
            "resolved_count": sum(1 for r in self._exceptions.values() if r.resolved),
            "severity_distribution": severity_counts,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验异常处理模块"""
        self._logger.info("二级异常处理模块校验开始")
        
        checks = []
        
        # 1. 校验异常存储
        if isinstance(self._exceptions, dict):
            checks.append("exception_storage_valid")
        
        # 2. 校验恢复策略
        if len(self._recovery_strategies) > 0:
            checks.append("recovery_strategies_valid")
        
        # 3. 校验异常处理器
        if len(self._exception_handlers) > 0:
            checks.append("exception_handlers_valid")
        
        all_passed = len(checks) == 3
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="level2_exception_validation",
                message="二级异常处理模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="level2_exception_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("exceptions_count", len(self._exceptions))
        snapshot.set_state("resolved_count", sum(1 for r in self._exceptions.values() if r.resolved))
        snapshot.set_state("strategies_count", len(self._recovery_strategies))
        snapshot.metadata["module_type"] = "Level2ExceptionModule"
    
    # =====================================================================
    # 公共接口
    # =====================================================================
    
    def register_exception(
        self,
        exception_type: str,
        message: str,
        severity: ExceptionSeverity = ExceptionSeverity.MEDIUM,
        task_id: Optional[TaskID] = None
    ) -> str:
        """注册异常"""
        record = ExceptionRecord(
            exception_id=f"exc_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self._exceptions)}",
            exception_type=exception_type,
            message=message,
            severity=severity,
            task_id=task_id
        )
        self._exceptions[record.exception_id] = record
        self._exception_history.append(record)
        self._logger.warning(f"异常已注册: {record.exception_id} - {message}")
        return record.exception_id
    
    def get_exception(self, exception_id: str) -> Optional[ExceptionRecord]:
        """获取异常记录"""
        return self._exceptions.get(exception_id)
    
    def get_all_exceptions(self) -> Dict[str, ExceptionRecord]:
        """获取所有异常"""
        return self._exceptions.copy()
    
    def resolve_exception(self, exception_id: str, resolution: str) -> bool:
        """解决异常"""
        record = self._exceptions.get(exception_id)
        if record:
            record.resolved = True
            record.resolution = resolution
            self._logger.info(f"异常已解决: {exception_id}")
            return True
        return False
    
    def add_recovery_strategy(self, strategy: RecoveryStrategy) -> None:
        """添加恢复策略"""
        self._recovery_strategies[strategy.strategy_id] = strategy
    
    def get_exception_statistics(self) -> Dict[str, Any]:
        """获取异常统计"""
        return self._generate_exception_report()


__all__ = [
    "Level2ExceptionModule",
    "ExceptionRecord",
    "ExceptionSeverity",
    "RecoveryStrategy",
]
