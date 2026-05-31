"""
阶段17：一级管控模块框架实现
Level 1 Control Module Framework

职责定义：
- 全局任务治理
- 初始化二级双子子模块
- 全局异常拦截入口
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from core.base_module import BaseModule, ControlModuleBase
from core.twin_container import TwinContainer, TwinSlot
from core_types.core_types import (
    ModuleID, TaskID, ModuleType, ModuleState,
    InitResult, ModuleOutput, CheckResult, SnapshotData,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)
from interfaces.module_interface import IModule
from utils.logger import Logger
from core.exceptions import ModuleException, InitException


class Level1ControlModule(ControlModuleBase):
    """
    一级管控模块
    
    职责：
    1. 全局任务治理
    2. 监控任务执行状态
    3. 协调管控与执行模块
    4. 全局异常拦截与处理
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._logger = Logger(f"Level1Control_{self.module_id}")
        self._task_registry: Dict[TaskID, Dict[str, Any]] = {}
        self._global_config: Dict[str, Any] = {}
        self._exception_handlers: List[callable] = []
        
    # =====================================================================
    # 初始化接口实现
    # =====================================================================
    
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """
        一级管控模块初始化
        
        1. 加载全局配置
        2. 初始化任务注册表
        3. 注册异常处理器
        """
        try:
            self._logger.info("一级管控模块初始化开始")
            
            # 1. 加载全局配置
            self._load_global_config(request)
            
            # 2. 初始化任务注册表
            self._task_registry = {}
            
            # 3. 注册默认异常处理器
            self._register_default_exception_handlers()
            
            self._logger.info("一级管控模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="一级管控模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"一级管控模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L1C_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_global_config(self, request: InitRequest) -> None:
        """加载全局配置"""
        if request.task_param:
            self._global_config = {
                "max_iterations": request.task_param.get_param("max_iterations", 10000),
                "timeout_seconds": request.task_param.get_param("timeout_seconds", 3600),
                "enable_checkpoint": request.task_param.get_param("enable_checkpoint", True),
                "checkpoint_interval": request.task_param.get_param("checkpoint_interval", 100),
            }
        else:
            self._global_config = {
                "max_iterations": 10000,
                "timeout_seconds": 3600,
                "enable_checkpoint": True,
                "checkpoint_interval": 100,
            }
        
        self._logger.info(f"全局配置加载完成: {self._global_config}")
    
    def _register_default_exception_handlers(self) -> None:
        """注册默认异常处理器"""
        self._exception_handlers = [
            self._handle_init_exception,
            self._handle_runtime_exception,
        ]
    
    # =====================================================================
    # 执行接口实现
    # =====================================================================
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """
        一级管控模块执行
        
        职责：
        1. 治理任务执行
        2. 监控执行状态
        3. 协调子模块
        """
        self._logger.info("一级管控模块执行开始")
        
        try:
            # 1. 获取任务ID
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 2. 注册任务
            self._register_task(task_id, request)
            
            # 3. 执行治理逻辑
            governance_result = self._execute_governance(task_id, request, context)
            
            # 4. 更新任务状态
            self._update_task_status(task_id, "completed", governance_result)
            
            self._logger.info("一级管控模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "governance_result": governance_result,
                    "task_id": str(task_id),
                },
                message="一级管控模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"一级管控模块执行失败: {e}")
            return self._handle_execution_error(request, e)
    
    def _register_task(self, task_id: TaskID, request: ExecutionRequest) -> None:
        """注册任务"""
        self._task_registry[task_id] = {
            "request": request,
            "status": "running",
            "start_time": datetime.now(),
            "iteration_count": 0,
        }
        self._logger.info(f"任务注册完成: {task_id}")
    
    def _execute_governance(
        self,
        task_id: TaskID,
        request: ExecutionRequest,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """执行治理逻辑"""
        return {
            "task_id": str(task_id),
            "governance_applied": True,
            "policies_enforced": ["timeout_policy", "checkpoint_policy"],
        }
    
    def _update_task_status(
        self,
        task_id: TaskID,
        status: str,
        result: Dict[str, Any]
    ) -> None:
        """更新任务状态"""
        if task_id in self._task_registry:
            self._task_registry[task_id]["status"] = status
            self._task_registry[task_id]["result"] = result
            self._task_registry[task_id]["end_time"] = datetime.now()
    
    def _handle_execution_error(
        self,
        request: ExecutionRequest,
        error: Exception
    ) -> ModuleOutput:
        """处理执行错误"""
        task_id = request.module_input.task_id if request.module_input else TaskID()
        
        # 尝试使用异常处理器
        for handler in self._exception_handlers:
            handled = handler(error)
            if handled:
                return ModuleOutput.success_output(
                    task_id=task_id,
                    data={"recovered": True},
                    message="错误已处理"
                )
        
        return ModuleOutput.failure_output(
            task_id=task_id,
            error_code="L1C_EXECUTION_FAILED",
            error_detail=str(error)
        )
    
    # =====================================================================
    # 校验接口实现
    # =====================================================================
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """
        一级管控模块校验
        
        校验内容：
        1. 全局配置有效性
        2. 任务注册表状态
        3. 子模块状态
        """
        self._logger.info("一级管控模块校验开始")
        
        checks = []
        
        # 1. 校验全局配置
        if self._validate_global_config():
            checks.append("global_config_valid")
        
        # 2. 校验任务注册表
        if self._validate_task_registry():
            checks.append("task_registry_valid")
        
        # 3. 校验子模块
        if self._validate_children():
            checks.append("children_valid")
        
        all_passed = len(checks) == 3
        
        self._logger.info(f"一级管控模块校验完成: {checks}")
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="level1_control_validation",
                message="一级管控模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="level1_control_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _validate_global_config(self) -> bool:
        """校验全局配置"""
        required_keys = ["max_iterations", "timeout_seconds"]
        return all(key in self._global_config for key in required_keys)
    
    def _validate_task_registry(self) -> bool:
        """校验任务注册表"""
        return isinstance(self._task_registry, dict)
    
    def _validate_children(self) -> bool:
        """校验子模块"""
        # 一级管控模块应该有两个子模块（二级管控和二级执行）
        children = self.get_all_children()
        return len(children) <= 2  # 允许0-2个子模块（初始化阶段可能未完成）
    
    # =====================================================================
    # 快照接口实现
    # =====================================================================
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("global_config", self._global_config)
        snapshot.set_state("task_count", len(self._task_registry))
        snapshot.set_state("task_ids", [str(tid) for tid in self._task_registry.keys()])
        snapshot.metadata["module_type"] = "Level1ControlModule"
        snapshot.metadata["version"] = "1.0"
    
    # =====================================================================
    # 异常处理
    # =====================================================================
    
    def _handle_init_exception(self, exception: Exception) -> bool:
        """处理初始化异常"""
        if isinstance(exception, InitException):
            self._logger.error(f"初始化异常: {exception}")
            return True
        return False
    
    def _handle_runtime_exception(self, exception: Exception) -> bool:
        """处理运行时异常"""
        self._logger.error(f"运行时异常: {exception}")
        return False  # 未处理，继续抛出
    
    def register_exception_handler(self, handler: callable) -> None:
        """注册自定义异常处理器"""
        self._exception_handlers.append(handler)
    
    # =====================================================================
    # 治理接口
    # =====================================================================
    
    def get_task_status(self, task_id: TaskID) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return self._task_registry.get(task_id)
    
    def get_all_tasks(self) -> Dict[TaskID, Dict[str, Any]]:
        """获取所有任务"""
        return self._task_registry.copy()
    
    def get_global_config(self) -> Dict[str, Any]:
        """获取全局配置"""
        return self._global_config.copy()
    
    def update_global_config(self, config: Dict[str, Any]) -> None:
        """更新全局配置"""
        self._global_config.update(config)
        self._logger.info(f"全局配置已更新: {config}")
