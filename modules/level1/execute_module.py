"""
阶段18：一级执行模块框架实现
Level 1 Execute Module Framework

职责定义：
- 超长任务迭代执行
- 初始化二级双子子模块
- 总迭代调度入口
"""

from typing import Optional, Dict, Any, List, Callable
from datetime import datetime

from core.base_module import BaseModule, ExecuteModuleBase
from core.twin_container import TwinContainer, TwinSlot
from core_types.core_types import (
    ModuleID, TaskID, ModuleType, ModuleState,
    InitResult, ModuleOutput, CheckResult, SnapshotData,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)
from utils.logger import Logger


class Level1ExecuteModule(ExecuteModuleBase):
    """
    一级执行模块
    
    职责：
    1. 超长任务迭代执行
    2. 总迭代调度
    3. 执行状态管理
    4. 迭代结果汇总
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._logger = Logger(f"Level1Execute_{self.module_id}")
        self._iteration_count: int = 0
        self._max_iterations: int = 10000
        self._iteration_results: List[Dict[str, Any]] = []
        self._current_iteration: Optional[int] = None
        self._iteration_hooks: Dict[str, List[Callable]] = {
            "before_iteration": [],
            "after_iteration": [],
        }
        
    # =====================================================================
    # 初始化接口实现
    # =====================================================================
    
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """
        一级执行模块初始化
        
        1. 加载执行配置
        2. 初始化迭代状态
        3. 注册迭代钩子
        """
        try:
            self._logger.info("一级执行模块初始化开始")
            
            # 1. 加载执行配置
            self._load_execution_config(request)
            
            # 2. 初始化迭代状态
            self._iteration_count = 0
            self._iteration_results = []
            self._current_iteration = None
            
            # 3. 注册默认迭代钩子
            self._register_default_hooks()
            
            self._logger.info("一级执行模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="一级执行模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"一级执行模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L1E_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_execution_config(self, request: InitRequest) -> None:
        """加载执行配置"""
        if request.task_param:
            self._max_iterations = request.task_param.get_param("max_steps", 10000)
        else:
            self._max_iterations = 10000
        
        self._logger.info(f"执行配置加载完成: max_iterations={self._max_iterations}")
    
    def _register_default_hooks(self) -> None:
        """注册默认迭代钩子"""
        pass  # 默认不注册钩子
    
    # =====================================================================
    # 执行接口实现
    # =====================================================================
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """
        一级执行模块执行
        
        职责：
        1. 执行迭代调度
        2. 管理迭代状态
        3. 汇总迭代结果
        """
        self._logger.info("一级执行模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 执行迭代
            iteration_result = self._execute_iterations(task_id, request, context)
            
            self._logger.info("一级执行模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "iteration_result": iteration_result,
                    "total_iterations": self._iteration_count,
                    "task_id": str(task_id),
                },
                message="一级执行模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"一级执行模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L1E_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _execute_iterations(
        self,
        task_id: TaskID,
        request: ExecutionRequest,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """执行迭代"""
        self._current_iteration = 0
        
        # 执行单次迭代（简化版）
        self._run_single_iteration(task_id, self._current_iteration)
        
        self._current_iteration = None
        
        return {
            "task_id": str(task_id),
            "iterations_completed": self._iteration_count,
            "max_iterations": self._max_iterations,
        }
    
    def _run_single_iteration(self, task_id: TaskID, iteration: int) -> Dict[str, Any]:
        """执行单次迭代"""
        # 执行before钩子
        self._run_hooks("before_iteration", task_id, iteration)
        
        # 执行迭代逻辑
        result = {
            "iteration": iteration,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
        }
        
        self._iteration_results.append(result)
        self._iteration_count += 1
        
        # 执行after钩子
        self._run_hooks("after_iteration", task_id, iteration, result)
        
        return result
    
    def _run_hooks(self, hook_name: str, *args, **kwargs) -> None:
        """执行钩子"""
        for hook in self._iteration_hooks.get(hook_name, []):
            try:
                hook(*args, **kwargs)
            except Exception as e:
                self._logger.warning(f"钩子执行失败: {e}")
    
    # =====================================================================
    # 校验接口实现
    # =====================================================================
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """
        一级执行模块校验
        """
        self._logger.info("一级执行模块校验开始")
        
        checks = []
        
        # 1. 校验迭代配置
        if self._max_iterations > 0:
            checks.append("max_iterations_valid")
        
        # 2. 校验迭代状态
        if self._iteration_count >= 0:
            checks.append("iteration_count_valid")
        
        # 3. 校验子模块
        if self._validate_children():
            checks.append("children_valid")
        
        all_passed = len(checks) == 3
        
        self._logger.info(f"一级执行模块校验完成: {checks}")
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="level1_execute_validation",
                message="一级执行模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="level1_execute_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _validate_children(self) -> bool:
        """校验子模块"""
        children = self.get_all_children()
        return len(children) <= 2
    
    # =====================================================================
    # 快照接口实现
    # =====================================================================
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("iteration_count", self._iteration_count)
        snapshot.set_state("max_iterations", self._max_iterations)
        snapshot.set_state("current_iteration", self._current_iteration)
        snapshot.set_state("iteration_results_count", len(self._iteration_results))
        snapshot.metadata["module_type"] = "Level1ExecuteModule"
        snapshot.metadata["version"] = "1.0"
    
    # =====================================================================
    # 迭代管理接口
    # =====================================================================
    
    def get_iteration_count(self) -> int:
        """获取迭代次数"""
        return self._iteration_count
    
    def get_iteration_results(self) -> List[Dict[str, Any]]:
        """获取迭代结果"""
        return self._iteration_results.copy()
    
    def register_iteration_hook(self, hook_name: str, hook: Callable) -> None:
        """注册迭代钩子"""
        if hook_name in self._iteration_hooks:
            self._iteration_hooks[hook_name].append(hook)
