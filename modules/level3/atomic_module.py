"""
阶段36：三级原子操作模块
Level3AtomicModule

职责定义：
- 原子操作执行
- 操作回滚
- 操作日志
"""

from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from core.base_module import ExecuteModuleBase
from core_types.core_types import (
    ModuleID, TaskID, ModuleLevel,
    InitResult, ModuleOutput, CheckResult, SnapshotData,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)
from utils.logger import Logger


class AtomicOperationStatus(Enum):
    """原子操作状态"""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


class TransactionStatus(Enum):
    """事务状态"""
    ACTIVE = "active"
    COMMITTED = "committed"
    ABORTED = "aborted"
    PARTIAL = "partial"


@dataclass
class AtomicOperation:
    """原子操作"""
    operation_id: str
    name: str
    execute_func: Optional[Callable] = None
    rollback_func: Optional[Callable] = None
    status: AtomicOperationStatus = AtomicOperationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    rolled_back_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "operation_id": self.operation_id,
            "name": self.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "rolled_back_at": self.rolled_back_at.isoformat() if self.rolled_back_at else None,
            "result": str(self.result) if self.result is not None else None,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class Transaction:
    """事务"""
    transaction_id: str
    name: str
    operations: List[AtomicOperation] = field(default_factory=list)
    status: TransactionStatus = TransactionStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    committed_at: Optional[datetime] = None
    aborted_at: Optional[datetime] = None
    isolation_level: str = "read_committed"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "transaction_id": self.transaction_id,
            "name": self.name,
            "status": self.status.value,
            "operation_count": len(self.operations),
            "created_at": self.created_at.isoformat(),
            "committed_at": self.committed_at.isoformat() if self.committed_at else None,
            "aborted_at": self.aborted_at.isoformat() if self.aborted_at else None,
            "isolation_level": self.isolation_level,
            "operations": [op.to_dict() for op in self.operations],
        }


@dataclass
class OperationLog:
    """操作日志条目"""
    log_id: str
    transaction_id: str
    operation_id: str
    action: str
    timestamp: datetime
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "transaction_id": self.transaction_id,
            "operation_id": self.operation_id,
            "action": self.action,
            "timestamp": self.timestamp.isoformat(),
            "before_state": self.before_state,
            "after_state": self.after_state,
            "details": self.details,
        }


class Level3AtomicModule(ExecuteModuleBase):
    """
    三级原子操作模块
    
    职责：
    1. 原子事务管理
    2. 回滚机制
    3. 操作日志
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL3
        self._state.module_name = "Level3AtomicModule"
        self._logger = Logger(f"L3AT_{self.module_id}")
        
        # 事务存储
        self._transactions: Dict[str, Transaction] = {}
        # 当前活跃事务
        self._active_transaction: Optional[Transaction] = None
        # 操作日志
        self._operation_logs: List[OperationLog] = []
        # 已注册的操作模板
        self._operation_templates: Dict[str, Dict[str, Any]] = {}
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("三级原子操作模块初始化开始")
            
            # 1. 加载配置
            self._load_config(request)
            
            # 2. 初始化存储
            self._transactions = {}
            self._active_transaction = None
            self._operation_logs = []
            self._operation_templates = {}
            
            self._logger.info("三级原子操作模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="三级原子操作模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"三级原子操作模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L3AT_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "auto_rollback": True,
            "max_operations_per_transaction": 100,
            "log_all_operations": True,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("atomic_config", {})
            self._config.update(custom_config)
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("三级原子操作模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "create_transaction")
            
            if operation == "create_transaction":
                result = self._create_transaction_operation(input_data)
            elif operation == "add_operation":
                result = self._add_operation_to_transaction(input_data)
            elif operation == "execute_transaction":
                result = self._execute_transaction_operation(input_data)
            elif operation == "commit_transaction":
                result = self._commit_transaction_operation(input_data)
            elif operation == "rollback_transaction":
                result = self._rollback_transaction_operation(input_data)
            elif operation == "get_transaction":
                result = self._get_transaction_operation(input_data)
            elif operation == "get_logs":
                result = self._get_logs_operation(input_data)
            elif operation == "register_template":
                result = self._register_template_operation(input_data)
            else:
                result = {"error": f"未知操作: {operation}"}
            
            self._logger.info("三级原子操作模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level3AtomicModule",
                    "transaction_summary": {
                        "total_transactions": len(self._transactions),
                        "active_transaction": self._active_transaction.transaction_id if self._active_transaction else None,
                        "total_logs": len(self._operation_logs),
                    },
                },
                message="三级原子操作模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"三级原子操作模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L3AT_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _create_transaction_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建事务"""
        import uuid
        
        tx_id = str(uuid.uuid4())
        tx = Transaction(
            transaction_id=tx_id,
            name=input_data.get("name", f"transaction_{tx_id[:8]}"),
            isolation_level=input_data.get("isolation_level", "read_committed"),
        )
        self._transactions[tx_id] = tx
        self._active_transaction = tx
        
        self._log_operation(tx_id, "", "CREATE_TRANSACTION", {}, {"transaction_id": tx_id})
        
        return {
            "operation": "create_transaction",
            "transaction_id": tx_id,
            "status": tx.status.value,
            "created": True,
        }
    
    def _add_operation_to_transaction(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """向事务添加操作"""
        tx_id = input_data.get("transaction_id")
        if not tx_id or tx_id not in self._transactions:
            return {
                "operation": "add_operation",
                "error": "事务不存在",
                "success": False,
            }
        
        tx = self._transactions[tx_id]
        max_ops = self._config.get("max_operations_per_transaction", 100)
        if len(tx.operations) >= max_ops:
            return {
                "operation": "add_operation",
                "error": f"事务操作数超过最大值 {max_ops}",
                "success": False,
            }
        
        import uuid
        op_id = str(uuid.uuid4())
        op = AtomicOperation(
            operation_id=op_id,
            name=input_data.get("name", f"op_{op_id[:8]}"),
            metadata=input_data.get("metadata", {}),
        )
        tx.operations.append(op)
        
        self._log_operation(tx_id, op_id, "ADD_OPERATION", {}, {"operation_name": op.name})
        
        return {
            "operation": "add_operation",
            "transaction_id": tx_id,
            "operation_id": op_id,
            "operation_count": len(tx.operations),
            "success": True,
        }
    
    def _execute_transaction_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行事务"""
        tx_id = input_data.get("transaction_id")
        if not tx_id or tx_id not in self._transactions:
            return {
                "operation": "execute_transaction",
                "error": "事务不存在",
                "success": False,
            }
        
        tx = self._transactions[tx_id]
        completed_ops = []
        failed_op = None
        
        try:
            for op in tx.operations:
                op.status = AtomicOperationStatus.EXECUTING
                op.executed_at = datetime.now()
                
                # 模拟执行
                op.result = {"executed": True, "timestamp": datetime.now().isoformat()}
                op.status = AtomicOperationStatus.COMPLETED
                completed_ops.append(op.operation_id)
                
                self._log_operation(
                    tx_id, op.operation_id, "EXECUTE",
                    {"status": "executing"},
                    {"status": "completed", "result": op.result}
                )
            
            tx.status = TransactionStatus.COMMITTED
            tx.committed_at = datetime.now()
            
            self._log_operation(tx_id, "", "COMMIT", {}, {"committed_at": tx.committed_at.isoformat()})
            
            return {
                "operation": "execute_transaction",
                "transaction_id": tx_id,
                "status": tx.status.value,
                "completed_operations": len(completed_ops),
                "success": True,
            }
            
        except Exception as e:
            failed_op = op.operation_id if 'op' in locals() else None
            tx.status = TransactionStatus.ABORTED
            tx.aborted_at = datetime.now()
            
            # 自动回滚
            if self._config.get("auto_rollback", True):
                self._rollback_transaction(tx_id)
            
            self._log_operation(tx_id, failed_op or "", "ABORT", {}, {"error": str(e)})
            
            return {
                "operation": "execute_transaction",
                "transaction_id": tx_id,
                "status": tx.status.value,
                "failed_at_operation": failed_op,
                "error": str(e),
                "rolled_back": self._config.get("auto_rollback", True),
                "success": False,
            }
    
    def _commit_transaction_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """提交事务"""
        tx_id = input_data.get("transaction_id")
        if not tx_id or tx_id not in self._transactions:
            return {
                "operation": "commit_transaction",
                "error": "事务不存在",
                "success": False,
            }
        
        tx = self._transactions[tx_id]
        
        # 检查所有操作是否已完成
        all_completed = all(op.status == AtomicOperationStatus.COMPLETED for op in tx.operations)
        if not all_completed:
            return {
                "operation": "commit_transaction",
                "error": "不是所有操作都已完成",
                "success": False,
            }
        
        tx.status = TransactionStatus.COMMITTED
        tx.committed_at = datetime.now()
        
        self._log_operation(tx_id, "", "COMMIT", {}, {"committed_at": tx.committed_at.isoformat()})
        
        return {
            "operation": "commit_transaction",
            "transaction_id": tx_id,
            "status": tx.status.value,
            "success": True,
        }
    
    def _rollback_transaction_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """回滚事务"""
        tx_id = input_data.get("transaction_id")
        if not tx_id or tx_id not in self._transactions:
            return {
                "operation": "rollback_transaction",
                "error": "事务不存在",
                "success": False,
            }
        
        result = self._rollback_transaction(tx_id)
        return {
            "operation": "rollback_transaction",
            "transaction_id": tx_id,
            **result,
        }
    
    def _rollback_transaction(self, tx_id: str) -> Dict[str, Any]:
        """执行回滚"""
        tx = self._transactions[tx_id]
        rolled_back_ops = []
        
        # 逆序回滚已完成的操作
        for op in reversed(tx.operations):
            if op.status in [AtomicOperationStatus.COMPLETED, AtomicOperationStatus.FAILED]:
                op.status = AtomicOperationStatus.ROLLING_BACK
                op.rolled_back_at = datetime.now()
                
                # 模拟回滚
                op.status = AtomicOperationStatus.ROLLED_BACK
                rolled_back_ops.append(op.operation_id)
                
                self._log_operation(
                    tx_id, op.operation_id, "ROLLBACK",
                    {"status": "rolling_back"},
                    {"status": "rolled_back"}
                )
        
        tx.status = TransactionStatus.ABORTED
        tx.aborted_at = datetime.now()
        
        self._log_operation(tx_id, "", "ABORT", {}, {"aborted_at": tx.aborted_at.isoformat()})
        
        return {
            "rolled_back_operations": len(rolled_back_ops),
            "status": tx.status.value,
            "success": True,
        }
    
    def _get_transaction_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取事务信息"""
        tx_id = input_data.get("transaction_id")
        if not tx_id or tx_id not in self._transactions:
            return {
                "operation": "get_transaction",
                "error": "事务不存在",
            }
        
        tx = self._transactions[tx_id]
        return {
            "operation": "get_transaction",
            "transaction": tx.to_dict(),
        }
    
    def _get_logs_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取操作日志"""
        tx_id = input_data.get("transaction_id")
        limit = input_data.get("limit", 100)
        
        logs = self._operation_logs
        if tx_id:
            logs = [log for log in logs if log.transaction_id == tx_id]
        
        logs = sorted(logs, key=lambda l: l.timestamp, reverse=True)[:limit]
        
        return {
            "operation": "get_logs",
            "total_logs": len(self._operation_logs),
            "returned": len(logs),
            "logs": [log.to_dict() for log in logs],
        }
    
    def _register_template_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """注册操作模板"""
        template_name = input_data.get("template_name")
        template = input_data.get("template", {})
        self._operation_templates[template_name] = template
        
        return {
            "operation": "register_template",
            "template_name": template_name,
            "registered": True,
        }
    
    def _log_operation(self, tx_id: str, op_id: str, action: str,
                       before_state: Dict[str, Any], after_state: Dict[str, Any]) -> None:
        """记录操作日志"""
        import uuid
        
        if not self._config.get("log_all_operations", True):
            return
        
        log = OperationLog(
            log_id=str(uuid.uuid4()),
            transaction_id=tx_id,
            operation_id=op_id,
            action=action,
            timestamp=datetime.now(),
            before_state=before_state,
            after_state=after_state,
        )
        self._operation_logs.append(log)
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("三级原子操作模块校验开始")
        
        checks = []
        
        # 1. 校验事务存储
        if isinstance(self._transactions, dict):
            checks.append("transactions_valid")
        
        # 2. 校验操作日志
        if isinstance(self._operation_logs, list):
            checks.append("logs_valid")
        
        # 3. 校验模块状态
        if self._state.module_level == ModuleLevel.LEVEL3:
            checks.append("level_valid")
        
        # 4. 校验配置
        if self._config.get("auto_rollback", False) is not None:
            checks.append("rollback_config_valid")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="atomic_validation",
                message="三级原子操作模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="atomic_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("transactions", {
            tx_id: tx.to_dict() for tx_id, tx in self._transactions.items()
        })
        snapshot.set_state("active_transaction", self._active_transaction.transaction_id if self._active_transaction else None)
        snapshot.set_state("log_count", len(self._operation_logs))
        snapshot.set_state("templates", list(self._operation_templates.keys()))
        snapshot.metadata["module_type"] = "Level3AtomicModule"
    
    # =====================================================================
    # 公共接口
    # =====================================================================
    
    def create_transaction(self, name: str, isolation_level: str = "read_committed") -> Transaction:
        """创建事务"""
        import uuid
        tx = Transaction(
            transaction_id=str(uuid.uuid4()),
            name=name,
            isolation_level=isolation_level,
        )
        self._transactions[tx.transaction_id] = tx
        self._active_transaction = tx
        return tx
    
    def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        """获取事务"""
        return self._transactions.get(tx_id)
    
    def rollback_transaction(self, tx_id: str) -> Dict[str, Any]:
        """回滚事务"""
        return self._rollback_transaction(tx_id)
    
    def get_operation_logs(self, tx_id: Optional[str] = None) -> List[OperationLog]:
        """获取操作日志"""
        if tx_id:
            return [log for log in self._operation_logs if log.transaction_id == tx_id]
        return self._operation_logs
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level3AtomicModule",
    "AtomicOperation",
    "AtomicOperationStatus",
    "Transaction",
    "TransactionStatus",
    "OperationLog",
]
