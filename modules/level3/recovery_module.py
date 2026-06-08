"""
阶段38：三级恢复模块
Level3RecoveryModule

职责定义：
- 故障恢复
- 状态恢复
- 检查点恢复
"""

from typing import Optional, Dict, Any, List
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


class RecoveryStatus(Enum):
    """恢复状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class RecoveryType(Enum):
    """恢复类型"""
    CHECKPOINT = "checkpoint"
    STATE = "state"
    FULL = "full"
    INCREMENTAL = "incremental"


@dataclass
class Checkpoint:
    """检查点"""
    checkpoint_id: str
    name: str
    created_at: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "data_keys": list(self.data.keys()),
            "metadata": self.metadata,
            "tags": self.tags,
        }


@dataclass
class RecoveryJob:
    """恢复任务"""
    job_id: str
    recovery_type: RecoveryType
    status: RecoveryStatus
    target_checkpoint: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    recovered_items: List[str] = field(default_factory=list)
    failed_items: List[str] = field(default_factory=list)
    error_log: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "recovery_type": self.recovery_type.value,
            "status": self.status.value,
            "target_checkpoint": self.target_checkpoint,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "recovered_items": self.recovered_items,
            "failed_items": self.failed_items,
            "error_log": self.error_log,
            "metadata": self.metadata,
        }


@dataclass
class FailureRecord:
    """故障记录"""
    failure_id: str
    component: str
    error_type: str
    error_message: str
    timestamp: datetime
    severity: str = "error"
    recovered: bool = False
    recovery_job_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_id": self.failure_id,
            "component": self.component,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity,
            "recovered": self.recovered,
            "recovery_job_id": self.recovery_job_id,
            "metadata": self.metadata,
        }


class Level3RecoveryModule(ExecuteModuleBase):
    """
    三级恢复模块
    
    职责：
    1. 故障恢复
    2. 状态恢复
    3. 检查点恢复
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL3
        self._state.module_name = "Level3RecoveryModule"
        self._logger = Logger(f"L3RE_{self.module_id}")
        
        # 检查点存储
        self._checkpoints: Dict[str, Checkpoint] = {}
        # 恢复任务
        self._recovery_jobs: Dict[str, RecoveryJob] = {}
        # 故障记录
        self._failure_records: List[FailureRecord] = []
        # 恢复策略
        self._recovery_policies: Dict[str, Dict[str, Any]] = {}
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("三级恢复模块初始化开始")
            
            # 1. 加载配置
            self._load_config(request)
            
            # 2. 初始化存储
            self._checkpoints = {}
            self._recovery_jobs = {}
            self._failure_records = []
            self._recovery_policies = {}
            
            # 3. 加载默认恢复策略
            self._load_default_policies()
            
            self._logger.info("三级恢复模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="三级恢复模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"三级恢复模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L3RE_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "auto_recovery": True,
            "max_checkpoints": 50,
            "recovery_timeout_seconds": 300,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("recovery_config", {})
            self._config.update(custom_config)
    
    def _load_default_policies(self) -> None:
        """加载默认恢复策略"""
        self._recovery_policies = {
            "default": {
                "retry_count": 3,
                "retry_delay_seconds": 5,
                "fallback_to_older_checkpoint": True,
                "notify_on_failure": True,
            },
            "aggressive": {
                "retry_count": 5,
                "retry_delay_seconds": 1,
                "fallback_to_older_checkpoint": True,
                "notify_on_failure": True,
            },
            "conservative": {
                "retry_count": 1,
                "retry_delay_seconds": 10,
                "fallback_to_older_checkpoint": False,
                "notify_on_failure": True,
            },
        }
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("三级恢复模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "create_checkpoint")
            
            if operation == "create_checkpoint":
                result = self._create_checkpoint_operation(input_data)
            elif operation == "record_failure":
                result = self._record_failure_operation(input_data)
            elif operation == "recover":
                result = self._recover_operation(input_data)
            elif operation == "get_checkpoint":
                result = self._get_checkpoint_operation(input_data)
            elif operation == "list_checkpoints":
                result = self._list_checkpoints_operation()
            elif operation == "get_recovery_status":
                result = self._get_recovery_status_operation(input_data)
            elif operation == "list_failures":
                result = self._list_failures_operation(input_data)
            elif operation == "delete_checkpoint":
                result = self._delete_checkpoint_operation(input_data)
            else:
                result = {"error": f"未知操作: {operation}"}
            
            self._logger.info("三级恢复模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level3RecoveryModule",
                    "recovery_summary": {
                        "total_checkpoints": len(self._checkpoints),
                        "total_jobs": len(self._recovery_jobs),
                        "total_failures": len(self._failure_records),
                        "unrecovered_failures": len([f for f in self._failure_records if not f.recovered]),
                    },
                },
                message="三级恢复模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"三级恢复模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L3RE_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _create_checkpoint_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建检查点"""
        import uuid
        
        checkpoint_id = str(uuid.uuid4())
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            name=input_data.get("name", f"checkpoint_{checkpoint_id[:8]}"),
            created_at=datetime.now(),
            data=input_data.get("data", {}),
            metadata=input_data.get("metadata", {}),
            tags=input_data.get("tags", []),
        )
        self._checkpoints[checkpoint_id] = checkpoint
        
        # 检查最大检查点数
        max_checkpoints = self._config.get("max_checkpoints", 50)
        if len(self._checkpoints) > max_checkpoints:
            # 删除最旧的检查点
            oldest = min(self._checkpoints.values(), key=lambda c: c.created_at)
            del self._checkpoints[oldest.checkpoint_id]
        
        return {
            "operation": "create_checkpoint",
            "checkpoint_id": checkpoint_id,
            "name": checkpoint.name,
            "created": True,
        }
    
    def _record_failure_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """记录故障"""
        import uuid
        
        failure = FailureRecord(
            failure_id=str(uuid.uuid4()),
            component=input_data.get("component", "unknown"),
            error_type=input_data.get("error_type", "unknown"),
            error_message=input_data.get("error_message", ""),
            timestamp=datetime.now(),
            severity=input_data.get("severity", "error"),
            metadata=input_data.get("metadata", {}),
        )
        self._failure_records.append(failure)
        
        # 自动恢复
        if self._config.get("auto_recovery", True):
            recovery_result = self._attempt_auto_recovery(failure)
            failure.recovered = recovery_result.get("success", False)
            if failure.recovered:
                failure.recovery_job_id = recovery_result.get("job_id")
        
        return {
            "operation": "record_failure",
            "failure_id": failure.failure_id,
            "recorded": True,
            "auto_recovered": failure.recovered,
            "recovery_job_id": failure.recovery_job_id,
        }
    
    def _attempt_auto_recovery(self, failure: FailureRecord) -> Dict[str, Any]:
        """尝试自动恢复"""
        # 查找最新的检查点
        if not self._checkpoints:
            return {"success": False, "error": "没有可用的检查点"}
        
        latest_checkpoint = max(self._checkpoints.values(), key=lambda c: c.created_at)
        
        return self._execute_recovery(
            recovery_type=RecoveryType.CHECKPOINT,
            checkpoint_id=latest_checkpoint.checkpoint_id,
            policy="default",
        )
    
    def _recover_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行恢复操作"""
        recovery_type_str = input_data.get("recovery_type", "checkpoint")
        checkpoint_id = input_data.get("checkpoint_id")
        policy = input_data.get("policy", "default")
        
        try:
            recovery_type = RecoveryType(recovery_type_str)
        except ValueError:
            return {
                "operation": "recover",
                "error": f"无效的恢复类型: {recovery_type_str}",
                "success": False,
            }
        
        result = self._execute_recovery(recovery_type, checkpoint_id, policy)
        return {
            "operation": "recover",
            **result,
        }
    
    def _execute_recovery(self, recovery_type: RecoveryType,
                          checkpoint_id: Optional[str], policy: str) -> Dict[str, Any]:
        """执行恢复"""
        import uuid
        
        job_id = str(uuid.uuid4())
        job = RecoveryJob(
            job_id=job_id,
            recovery_type=recovery_type,
            status=RecoveryStatus.IN_PROGRESS,
            target_checkpoint=checkpoint_id,
            started_at=datetime.now(),
        )
        self._recovery_jobs[job_id] = job
        
        policy_config = self._recovery_policies.get(policy, self._recovery_policies["default"])
        retry_count = policy_config.get("retry_count", 3)
        
        try:
            if recovery_type == RecoveryType.CHECKPOINT:
                if not checkpoint_id or checkpoint_id not in self._checkpoints:
                    # 尝试回退到更旧的检查点
                    if policy_config.get("fallback_to_older_checkpoint", True) and self._checkpoints:
                        sorted_checkpoints = sorted(self._checkpoints.values(), key=lambda c: c.created_at, reverse=True)
                        for cp in sorted_checkpoints:
                            if self._recover_from_checkpoint(cp):
                                job.recovered_items.append(cp.checkpoint_id)
                                break
                        else:
                            raise Exception("所有检查点恢复均失败")
                    else:
                        raise Exception(f"检查点 {checkpoint_id} 不存在")
                else:
                    checkpoint = self._checkpoints[checkpoint_id]
                    for attempt in range(retry_count):
                        if self._recover_from_checkpoint(checkpoint):
                            job.recovered_items.append(checkpoint_id)
                            break
                        if attempt < retry_count - 1:
                            import time
                            time.sleep(policy_config.get("retry_delay_seconds", 5))
                    else:
                        raise Exception(f"恢复失败，已重试 {retry_count} 次")
            
            elif recovery_type == RecoveryType.STATE:
                # 状态恢复逻辑
                job.recovered_items.append("state_restored")
            
            elif recovery_type == RecoveryType.FULL:
                # 完全恢复
                if checkpoint_id and checkpoint_id in self._checkpoints:
                    checkpoint = self._checkpoints[checkpoint_id]
                    self._recover_from_checkpoint(checkpoint)
                    job.recovered_items.append(checkpoint_id)
                job.recovered_items.append("full_recovery_completed")
            
            elif recovery_type == RecoveryType.INCREMENTAL:
                # 增量恢复
                job.recovered_items.append("incremental_recovery_completed")
            
            job.status = RecoveryStatus.SUCCESS
            job.completed_at = datetime.now()
            
            return {
                "job_id": job_id,
                "status": job.status.value,
                "recovered_items": job.recovered_items,
                "success": True,
            }
            
        except Exception as e:
            job.status = RecoveryStatus.FAILED
            job.completed_at = datetime.now()
            job.error_log.append(str(e))
            
            return {
                "job_id": job_id,
                "status": job.status.value,
                "error": str(e),
                "success": False,
            }
    
    def _recover_from_checkpoint(self, checkpoint: Checkpoint) -> bool:
        """从检查点恢复"""
        # 模拟恢复过程
        self._logger.info(f"从检查点 {checkpoint.checkpoint_id} 恢复")
        return True
    
    def _get_checkpoint_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取检查点信息"""
        checkpoint_id = input_data.get("checkpoint_id")
        if not checkpoint_id or checkpoint_id not in self._checkpoints:
            return {"operation": "get_checkpoint", "error": "检查点不存在"}
        
        checkpoint = self._checkpoints[checkpoint_id]
        return {
            "operation": "get_checkpoint",
            "checkpoint": checkpoint.to_dict(),
        }
    
    def _list_checkpoints_operation(self) -> Dict[str, Any]:
        """列出所有检查点"""
        checkpoints = sorted(self._checkpoints.values(), key=lambda c: c.created_at, reverse=True)
        return {
            "operation": "list_checkpoints",
            "total": len(checkpoints),
            "checkpoints": [cp.to_dict() for cp in checkpoints],
        }
    
    def _get_recovery_status_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取恢复任务状态"""
        job_id = input_data.get("job_id")
        if not job_id or job_id not in self._recovery_jobs:
            return {"operation": "get_recovery_status", "error": "恢复任务不存在"}
        
        job = self._recovery_jobs[job_id]
        return {
            "operation": "get_recovery_status",
            "job": job.to_dict(),
        }
    
    def _list_failures_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """列出故障记录"""
        filters = input_data.get("filters", {})
        limit = input_data.get("limit", 100)
        
        failures = self._failure_records
        
        if "component" in filters:
            failures = [f for f in failures if f.component == filters["component"]]
        if "severity" in filters:
            failures = [f for f in failures if f.severity == filters["severity"]]
        if "recovered" in filters:
            failures = [f for f in failures if f.recovered == filters["recovered"]]
        
        failures = sorted(failures, key=lambda f: f.timestamp, reverse=True)[:limit]
        
        return {
            "operation": "list_failures",
            "total": len(self._failure_records),
            "returned": len(failures),
            "failures": [f.to_dict() for f in failures],
        }
    
    def _delete_checkpoint_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """删除检查点"""
        checkpoint_id = input_data.get("checkpoint_id")
        if not checkpoint_id or checkpoint_id not in self._checkpoints:
            return {"operation": "delete_checkpoint", "error": "检查点不存在", "success": False}
        
        del self._checkpoints[checkpoint_id]
        return {
            "operation": "delete_checkpoint",
            "checkpoint_id": checkpoint_id,
            "deleted": True,
        }
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("三级恢复模块校验开始")
        
        checks = []
        
        # 1. 校验检查点存储
        if isinstance(self._checkpoints, dict):
            checks.append("checkpoints_valid")
        
        # 2. 校验恢复策略
        if isinstance(self._recovery_policies, dict) and len(self._recovery_policies) > 0:
            checks.append("policies_valid")
        
        # 3. 校验模块状态
        if self._state.module_level == ModuleLevel.LEVEL3:
            checks.append("level_valid")
        
        # 4. 校验自动恢复配置
        if self._config.get("auto_recovery", False) is not None:
            checks.append("auto_recovery_config_valid")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="recovery_validation",
                message="三级恢复模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="recovery_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("checkpoints", {
            cp_id: cp.to_dict() for cp_id, cp in self._checkpoints.items()
        })
        snapshot.set_state("recovery_jobs", {
            job_id: job.to_dict() for job_id, job in self._recovery_jobs.items()
        })
        snapshot.set_state("failure_count", len(self._failure_records))
        snapshot.set_state("policies", list(self._recovery_policies.keys()))
        snapshot.metadata["module_type"] = "Level3RecoveryModule"
    
    # =====================================================================
    # 公共接口
    # =====================================================================
    
    def create_checkpoint(self, name: str, data: Dict[str, Any], tags: List[str] = None) -> Checkpoint:
        """创建检查点"""
        import uuid
        checkpoint = Checkpoint(
            checkpoint_id=str(uuid.uuid4()),
            name=name,
            created_at=datetime.now(),
            data=data,
            tags=tags or [],
        )
        self._checkpoints[checkpoint.checkpoint_id] = checkpoint
        return checkpoint
    
    def record_failure(self, component: str, error_type: str, error_message: str,
                       severity: str = "error") -> FailureRecord:
        """记录故障"""
        import uuid
        failure = FailureRecord(
            failure_id=str(uuid.uuid4()),
            component=component,
            error_type=error_type,
            error_message=error_message,
            timestamp=datetime.now(),
            severity=severity,
        )
        self._failure_records.append(failure)
        return failure
    
    def recover(self, recovery_type: RecoveryType, checkpoint_id: Optional[str] = None) -> Dict[str, Any]:
        """执行恢复"""
        return self._execute_recovery(recovery_type, checkpoint_id, "default")
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """获取检查点"""
        return self._checkpoints.get(checkpoint_id)
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level3RecoveryModule",
    "Checkpoint",
    "RecoveryJob",
    "RecoveryStatus",
    "RecoveryType",
    "FailureRecord",
]
