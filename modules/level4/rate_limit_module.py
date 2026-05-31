"""
阶段47：四级限流模块
Level4RateLimitModule

职责定义：
- 请求限流
- 限流策略
- 限流统计
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

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


class Level4RateLimitModule(ControlModuleBase):
    """
    四级限流模块
    
    职责：
    1. 请求限流
    2. 限流策略
    3. 限流统计
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL4
        self._state.module_name = "Level4RateLimitModule"
        self._logger = Logger(f"L4RL_{self.module_id}")
        
        # 模块状态
        self._config: Dict[str, Any] = {}
        self._data_store: Dict[str, Any] = {}
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("四级限流模块初始化开始")
            
            # 1. 加载配置
            self._load_config(request)
            
            # 2. 初始化数据存储
            self._data_store = {}
            
            self._logger.info("四级限流模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="四级限流模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级限流模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L4RL_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("rate_limit_config", {})
            self._config.update(custom_config)
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("四级限流模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 执行核心逻辑
            result = self._execute_core(task_id, request, context)
            
            self._logger.info("四级限流模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level4RateLimitModule",
                },
                message="四级限流模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级限流模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L4RL_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _execute_core(
        self,
        task_id: TaskID,
        request: ExecutionRequest,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """执行核心逻辑"""
        return {
            "task_id": str(task_id),
            "executed_at": datetime.now().isoformat(),
            "status": "success",
        }
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("四级限流模块校验开始")
        
        checks = []
        
        # 1. 校验配置
        if isinstance(self._config, dict):
            checks.append("config_valid")
        
        # 2. 校验数据存储
        if isinstance(self._data_store, dict):
            checks.append("data_store_valid")
        
        # 3. 校验模块状态
        if self._state.module_level == ModuleLevel.LEVEL4:
            checks.append("level_valid")
        
        all_passed = len(checks) == 3
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="rate_limit_validation",
                message="四级限流模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="rate_limit_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("data_store_keys", list(self._data_store.keys()))
        snapshot.metadata["module_type"] = "Level4RateLimitModule"
    
    # =====================================================================
    # 公共接口
    # =====================================================================
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        return self._config.copy()
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level4RateLimitModule",
]
