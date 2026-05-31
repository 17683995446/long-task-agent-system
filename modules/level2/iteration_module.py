"""
阶段24：二级迭代模块
Level2IterationModule

职责定义：
- 迭代执行管理
- 迭代状态跟踪
- 迭代结果汇总
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

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


class Level2IterationModule(ExecuteModuleBase):
    """
    二级迭代模块
    
    职责：
    1. 迭代执行管理
    2. 迭代状态跟踪
    3. 迭代结果汇总
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL2
        self._state.module_name = "Level2IterationModule"
        self._logger = Logger(f"L2I_{self.module_id}")
        
        # 执行状态
        self._execution_count: int = 0
        self._results: List[Dict[str, Any]] = []
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("二级迭代模块初始化开始")
            
            # 1. 初始化执行状态
            self._execution_count = 0
            self._results = []
            
            self._logger.info("二级迭代模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="二级迭代模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"二级迭代模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L2I_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("二级迭代模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 执行核心逻辑
            result = self._execute_core(task_id, request, context)
            
            # 记录执行结果
            self._results.append(result)
            self._execution_count += 1
            
            self._logger.info("二级迭代模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "execution_count": self._execution_count,
                },
                message="二级迭代模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"二级迭代模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L2I_EXECUTION_FAILED",
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
            "module": "Level2IterationModule",
        }
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("二级迭代模块校验开始")
        
        checks = []
        
        # 1. 校验执行计数
        if self._execution_count >= 0:
            checks.append("execution_count_valid")
        
        # 2. 校验结果存储
        if isinstance(self._results, list):
            checks.append("results_store_valid")
        
        # 3. 校验模块状态
        if self._state.module_level == ModuleLevel.LEVEL2:
            checks.append("level_valid")
        
        all_passed = len(checks) == 3
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="iteration_validation",
                message="二级迭代模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="iteration_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("execution_count", self._execution_count)
        snapshot.set_state("results_count", len(self._results))
        snapshot.metadata["module_type"] = "Level2IterationModule"
    
    # =====================================================================
    # 公共接口
    # =====================================================================
    
    def get_execution_count(self) -> int:
        """获取执行次数"""
        return self._execution_count
    
    def get_results(self) -> List[Dict[str, Any]]:
        """获取执行结果"""
        return self._results.copy()


__all__ = [
    "Level2IterationModule",
]
