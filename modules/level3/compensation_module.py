"""
阶段39：三级补偿模块
Level3CompensationModule

职责定义：
- 补偿事务
- 反向操作
- 补偿日志
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


class CompensationStatus(Enum):
    """补偿状态"""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class CompensationDirection(Enum):
    """补偿方向"""
    FORWARD = "forward"
    BACKWARD = "backward"


@dataclass
class CompensationAction:
    """补偿动作"""
    action_id: str
    name: str
    original_operation: str
    compensation_logic: Optional[str] = None
    status: CompensationStatus = CompensationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "original_operation": self.original_operation,
            "compensation_logic": self.compensation_logic,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "result": str(self.result) if self.result is not None else None,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class CompensationTransaction:
    """补偿事务"""
    transaction_id: str
    name: str
    actions: List[CompensationAction] = field(default_factory=list)
    status: CompensationStatus = CompensationStatus.PENDING
    direction: CompensationDirection = CompensationDirection.BACKWARD
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    original_transaction_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "name": self.name,
            "status": self.status.value,
            "direction": self.direction.value,
            "action_count": len(self.actions),
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "original_transaction_id": self.original_transaction_id,
            "metadata": self.metadata,
            "actions": [a.to_dict() for a in self.actions],
        }


@dataclass
class CompensationLog:
    """补偿日志"""
    log_id: str
    transaction_id: str
    action_id: str
    operation: str
    timestamp: datetime
    before_state: Dict[str, Any] = field(default_factory=dict)
    after_state: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "transaction_id": self.transaction_id,
            "action_id": self.action_id,
            "operation": self.operation,
            "timestamp": self.timestamp.isoformat(),
            "before_state": self.before_state,
            "after_state": self.after_state,
            "details": self.details,
        }


class Level3CompensationModule(ExecuteModuleBase):
    """
    三级补偿模块
    
    职责：
    1. 补偿事务
    2. 反向操作
    3. 补偿日志
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL3
        self._state.module_name = "Level3CompensationModule"
        self._logger = Logger(f"L3C_{self.module_id}")
        
        # 补偿事务存储
        self._compensation_transactions: Dict[str, CompensationTransaction] = {}
        # 补偿日志
        self._compensation_logs: List[CompensationLog] = []
        # 操作模板
        self._compensation_templates: Dict[str, Dict[str, Any]] = {}
        # 已注册的反操作
        self._reverse_operations: Dict[str, str] = {}
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("三级补偿模块初始化开始")
            
            # 1. 加载配置
            self._load_config(request)
            
            # 2. 初始化存储
            self._compensation_transactions = {}
            self._compensation_logs = []
            self._compensation_templates = {}
            self._reverse_operations = {}
            
            # 3. 加载默认模板
            self._load_default_templates()
            
            self._logger.info("三级补偿模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="三级补偿模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"三级补偿模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L3C_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "auto_compensate": True,
            "max_compensation_attempts": 3,
            "compensation_timeout_seconds": 60,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("compensation_config", {})
            self._config.update(custom_config)
    
    def _load_default_templates(self) -> None:
        """加载默认补偿模板"""
        self._compensation_templates = {
            "create": {
                "reverse": "delete",
                "description": "创建操作的补偿是删除",
            },
            "update": {
                "reverse": "restore",
                "description": "更新操作的补偿是恢复原始值",
            },
            "delete": {
                "reverse": "recreate",
                "description": "删除操作的补偿是重新创建",
            },
            "transfer": {
                "reverse": "reverse_transfer",
                "description": "转账操作的补偿是反向转账",
            },
        }
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("三级补偿模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "create_compensation_tx")
            
            if operation == "create_compensation_tx":
                result = self._create_compensation_tx_operation(input_data)
            elif operation == "add_action":
                result = self._add_action_operation(input_data)
            elif operation == "execute_compensation":
                result = self._execute_compensation_operation(input_data)
            elif operation == "register_reverse_op":
                result = self._register_reverse_op_operation(input_data)
            elif operation == "get_compensation_tx":
                result = self._get_compensation_tx_operation(input_data)
            elif operation == "get_logs":
                result = self._get_logs_operation(input_data)
            elif operation == "get_templates":
                result = self._get_templates_operation()
            elif operation == "validate_compensation":
                result = self._validate_compensation_operation(input_data)
            else:
                result = {"error": f"未知操作: {operation}"}
            
            self._logger.info("三级补偿模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level3CompensationModule",
                    "compensation_summary": {
                        "total_transactions": len(self._compensation_transactions),
                        "total_logs": len(self._compensation_logs),
                        "total_templates": len(self._compensation_templates),
                    },
                },
                message="三级补偿模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"三级补偿模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L3C_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _create_compensation_tx_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建补偿事务"""
        import uuid
        
        tx_id = str(uuid.uuid4())
        tx = CompensationTransaction(
            transaction_id=tx_id,
            name=input_data.get("name", f"compensation_{tx_id[:8]}"),
            original_transaction_id=input_data.get("original_transaction_id"),
            direction=CompensationDirection(input_data.get("direction", "backward")),
            metadata=input_data.get("metadata", {}),
        )
        self._compensation_transactions[tx_id] = tx
        
        self._log_compensation(tx_id, "", "CREATE_TX", {}, {"transaction_id": tx_id})
        
        return {
            "operation": "create_compensation_tx",
            "transaction_id": tx_id,
            "status": tx.status.value,
            "created": True,
        }
    
    def _add_action_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加补偿动作"""
        tx_id = input_data.get("transaction_id")
        if not tx_id or tx_id not in self._compensation_transactions:
            return {"operation": "add_action", "error": "补偿事务不存在", "success": False}
        
        tx = self._compensation_transactions[tx_id]
        
        import uuid
        action_id = str(uuid.uuid4())
        original_op = input_data.get("original_operation", "")
        
        # 自动查找反向操作
        reverse_op = input_data.get("compensation_logic")
        if not reverse_op and original_op in self._reverse_operations:
            reverse_op = self._reverse_operations[original_op]
        elif not reverse_op and original_op in self._compensation_templates:
            reverse_op = self._compensation_templates[original_op]["reverse"]
        
        action = CompensationAction(
            action_id=action_id,
            name=input_data.get("name", f"action_{action_id[:8]}"),
            original_operation=original_op,
            compensation_logic=reverse_op,
            metadata=input_data.get("metadata", {}),
        )
        tx.actions.append(action)
        
        self._log_compensation(tx_id, action_id, "ADD_ACTION", {}, {"action_name": action.name})
        
        return {
            "operation": "add_action",
            "transaction_id": tx_id,
            "action_id": action_id,
            "compensation_logic": reverse_op,
            "action_count": len(tx.actions),
            "success": True,
        }
    
    def _execute_compensation_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行补偿"""
        tx_id = input_data.get("transaction_id")
        if not tx_id or tx_id not in self._compensation_transactions:
            return {"operation": "execute_compensation", "error": "补偿事务不存在", "success": False}
        
        tx = self._compensation_transactions[tx_id]
        tx.status = CompensationStatus.EXECUTING
        tx.started_at = datetime.now()
        
        max_attempts = self._config.get("max_compensation_attempts", 3)
        completed_actions = []
        failed_actions = []
        
        try:
            # 根据方向决定执行顺序
            actions = tx.actions
            if tx.direction == CompensationDirection.BACKWARD:
                actions = list(reversed(actions))
            
            for action in actions:
                action.status = CompensationStatus.EXECUTING
                action.executed_at = datetime.now()
                
                # 模拟执行补偿
                for attempt in range(max_attempts):
                    try:
                        # 执行补偿逻辑
                        compensation_result = self._execute_compensation_action(action)
                        action.result = compensation_result
                        action.status = CompensationStatus.COMPLETED
                        completed_actions.append(action.action_id)
                        
                        self._log_compensation(
                            tx_id, action.action_id, "EXECUTE_COMPENSATION",
                            {"status": "executing"},
                            {"status": "completed", "result": compensation_result}
                        )
                        break
                    except Exception as e:
                        if attempt == max_attempts - 1:
                            action.error = str(e)
                            action.status = CompensationStatus.FAILED
                            failed_actions.append(action.action_id)
                            self._log_compensation(
                                tx_id, action.action_id, "EXECUTE_COMPENSATION",
                                {"status": "executing"},
                                {"status": "failed", "error": str(e)}
                            )
            
            # 确定事务状态
            if not failed_actions:
                tx.status = CompensationStatus.COMPLETED
            elif completed_actions and failed_actions:
                tx.status = CompensationStatus.PARTIAL
            else:
                tx.status = CompensationStatus.FAILED
            
            tx.completed_at = datetime.now()
            
            return {
                "operation": "execute_compensation",
                "transaction_id": tx_id,
                "status": tx.status.value,
                "completed_actions": len(completed_actions),
                "failed_actions": len(failed_actions),
                "success": tx.status in [CompensationStatus.COMPLETED, CompensationStatus.PARTIAL],
            }
            
        except Exception as e:
            tx.status = CompensationStatus.FAILED
            tx.completed_at = datetime.now()
            
            return {
                "operation": "execute_compensation",
                "transaction_id": tx_id,
                "status": tx.status.value,
                "error": str(e),
                "success": False,
            }
    
    def _execute_compensation_action(self, action: CompensationAction) -> Dict[str, Any]:
        """执行单个补偿动作"""
        # 模拟补偿执行
        self._logger.info(f"执行补偿动作: {action.name} (原操作: {action.original_operation})")
        
        return {
            "action_id": action.action_id,
            "original_operation": action.original_operation,
            "compensation_logic": action.compensation_logic,
            "executed": True,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _register_reverse_op_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """注册反向操作"""
        original_op = input_data.get("original_operation")
        reverse_op = input_data.get("reverse_operation")
        
        self._reverse_operations[original_op] = reverse_op
        
        return {
            "operation": "register_reverse_op",
            "original_operation": original_op,
            "reverse_operation": reverse_op,
            "registered": True,
        }
    
    def _get_compensation_tx_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取补偿事务"""
        tx_id = input_data.get("transaction_id")
        if not tx_id or tx_id not in self._compensation_transactions:
            return {"operation": "get_compensation_tx", "error": "补偿事务不存在"}
        
        tx = self._compensation_transactions[tx_id]
        return {
            "operation": "get_compensation_tx",
            "transaction": tx.to_dict(),
        }
    
    def _get_logs_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取补偿日志"""
        tx_id = input_data.get("transaction_id")
        limit = input_data.get("limit", 100)
        
        logs = self._compensation_logs
        if tx_id:
            logs = [log for log in logs if log.transaction_id == tx_id]
        
        logs = sorted(logs, key=lambda l: l.timestamp, reverse=True)[:limit]
        
        return {
            "operation": "get_logs",
            "total_logs": len(self._compensation_logs),
            "returned": len(logs),
            "logs": [log.to_dict() for log in logs],
        }
    
    def _get_templates_operation(self) -> Dict[str, Any]:
        """获取补偿模板"""
        return {
            "operation": "get_templates",
            "templates": self._compensation_templates,
        }
    
    def _validate_compensation_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证补偿事务"""
        tx_id = input_data.get("transaction_id")
        if not tx_id or tx_id not in self._compensation_transactions:
            return {"operation": "validate_compensation", "error": "补偿事务不存在", "valid": False}
        
        tx = self._compensation_transactions[tx_id]
        
        issues = []
        
        # 检查每个动作是否有补偿逻辑
        for action in tx.actions:
            if not action.compensation_logic:
                issues.append(f"动作 {action.action_id} 没有补偿逻辑")
        
        # 检查是否有重复的动作
        action_names = [a.name for a in tx.actions]
        if len(action_names) != len(set(action_names)):
            issues.append("存在重复的动作名称")
        
        valid = len(issues) == 0
        
        return {
            "operation": "validate_compensation",
            "transaction_id": tx_id,
            "valid": valid,
            "issues": issues,
        }
    
    def _log_compensation(self, tx_id: str, action_id: str, operation: str,
                          before_state: Dict[str, Any], after_state: Dict[str, Any]) -> None:
        """记录补偿日志"""
        import uuid
        
        log = CompensationLog(
            log_id=str(uuid.uuid4()),
            transaction_id=tx_id,
            action_id=action_id,
            operation=operation,
            timestamp=datetime.now(),
            before_state=before_state,
            after_state=after_state,
        )
        self._compensation_logs.append(log)
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("三级补偿模块校验开始")
        
        checks = []
        
        # 1. 校验补偿事务存储
        if isinstance(self._compensation_transactions, dict):
            checks.append("transactions_valid")
        
        # 2. 校验补偿日志
        if isinstance(self._compensation_logs, list):
            checks.append("logs_valid")
        
        # 3. 校验模块状态
        if self._state.module_level == ModuleLevel.LEVEL3:
            checks.append("level_valid")
        
        # 4. 校验模板
        if isinstance(self._compensation_templates, dict) and len(self._compensation_templates) > 0:
            checks.append("templates_valid")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="compensation_validation",
                message="三级补偿模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="compensation_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("transactions", {
            tx_id: tx.to_dict() for tx_id, tx in self._compensation_transactions.items()
        })
        snapshot.set_state("log_count", len(self._compensation_logs))
        snapshot.set_state("templates", list(self._compensation_templates.keys()))
        snapshot.set_state("reverse_operations", self._reverse_operations)
        snapshot.metadata["module_type"] = "Level3CompensationModule"
    
    # =====================================================================
    # 公共接口
    # =====================================================================
    
    def create_compensation_transaction(self, name: str,
                                         original_transaction_id: Optional[str] = None) -> CompensationTransaction:
        """创建补偿事务"""
        import uuid
        tx = CompensationTransaction(
            transaction_id=str(uuid.uuid4()),
            name=name,
            original_transaction_id=original_transaction_id,
        )
        self._compensation_transactions[tx.transaction_id] = tx
        return tx
    
    def add_compensation_action(self, tx_id: str, name: str, original_operation: str,
                                 compensation_logic: Optional[str] = None) -> CompensationAction:
        """添加补偿动作"""
        tx = self._compensation_transactions[tx_id]
        import uuid
        
        if not compensation_logic:
            compensation_logic = self._reverse_operations.get(original_operation)
        
        action = CompensationAction(
            action_id=str(uuid.uuid4()),
            name=name,
            original_operation=original_operation,
            compensation_logic=compensation_logic,
        )
        tx.actions.append(action)
        return action
    
    def execute_compensation(self, tx_id: str) -> Dict[str, Any]:
        """执行补偿"""
        return self._execute_compensation_operation({"transaction_id": tx_id})
    
    def register_reverse_operation(self, original_operation: str, reverse_operation: str) -> None:
        """注册反向操作"""
        self._reverse_operations[original_operation] = reverse_operation
    
    def get_compensation_logs(self, tx_id: Optional[str] = None) -> List[CompensationLog]:
        """获取补偿日志"""
        if tx_id:
            return [log for log in self._compensation_logs if log.transaction_id == tx_id]
        return self._compensation_logs
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level3CompensationModule",
    "CompensationAction",
    "CompensationTransaction",
    "CompensationLog",
    "CompensationStatus",
    "CompensationDirection",
]
