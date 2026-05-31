"""
阶段71-75：任务执行引擎
Task Execution Engine

职责定义：
- 任务调度和执行
- 执行状态管理
- 执行结果收集
"""

from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from enum import Enum, auto

from core.base_module import BaseModule
from core_types.core_types import (
    ModuleID, TaskID, TaskParam, ModuleInput, ModuleOutput,
)
from interfaces.module_interface import (
    ExecutionRequest, ExecutionContext, InitRequest, InitContext,
)
from system.module_tree import ModuleTree
from utils.logger import Logger


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = auto()      # 待执行
    RUNNING = auto()      # 执行中
    COMPLETED = auto()    # 已完成
    FAILED = auto()       # 失败
    CANCELLED = auto()    # 已取消


class ExecutionRecord:
    """执行记录"""
    
    def __init__(self, task_id: TaskID, module_id: ModuleID):
        self.task_id = task_id
        self.module_id = module_id
        self.status = ExecutionStatus.PENDING
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.result: Optional[ModuleOutput] = None
        self.error: Optional[str] = None
    
    def start(self) -> None:
        """开始执行"""
        self.status = ExecutionStatus.RUNNING
        self.start_time = datetime.now()
    
    def complete(self, result: ModuleOutput) -> None:
        """完成执行"""
        self.status = ExecutionStatus.COMPLETED
        self.end_time = datetime.now()
        self.result = result
    
    def fail(self, error: str) -> None:
        """执行失败"""
        self.status = ExecutionStatus.FAILED
        self.end_time = datetime.now()
        self.error = error
    
    def cancel(self) -> None:
        """取消执行"""
        self.status = ExecutionStatus.CANCELLED
        self.end_time = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": str(self.task_id),
            "module_id": str(self.module_id),
            "status": self.status.name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "result": self.result.data if self.result else None,
            "error": self.error,
        }


class ExecutionEngine:
    """
    任务执行引擎
    
    负责：
    1. 任务调度和执行
    2. 执行状态管理
    3. 执行结果收集
    4. 执行历史记录
    """
    
    def __init__(self, module_tree: ModuleTree):
        self._module_tree = module_tree
        self._logger = Logger("ExecutionEngine")
        self._execution_history: Dict[TaskID, ExecutionRecord] = {}
        self._active_executions: Dict[TaskID, ExecutionRecord] = {}
        self._execution_hooks: Dict[str, List[Callable]] = {
            "before": [],
            "after": [],
            "on_error": [],
        }
    
    def execute_task(
        self,
        task_id: TaskID,
        module_input: ModuleInput,
        target_module_id: Optional[ModuleID] = None,
        context: Optional[ExecutionContext] = None
    ) -> ExecutionRecord:
        """
        执行任务
        
        Args:
            task_id: 任务ID
            module_input: 模块输入
            target_module_id: 目标模块ID，如果为None则从根模块开始
            context: 执行上下文
            
        Returns:
            ExecutionRecord: 执行记录
        """
        if context is None:
            context = ExecutionContext()
        
        # 获取目标模块
        if target_module_id:
            module = self._module_tree.get_module(target_module_id)
            if not module:
                raise ValueError(f"模块未找到: {target_module_id}")
        else:
            module = self._module_tree.get_root().module
        
        # 创建执行记录
        record = ExecutionRecord(task_id, module.module_id)
        self._active_executions[task_id] = record
        self._execution_history[task_id] = record
        
        try:
            self._logger.info(f"开始执行任务: {task_id}")
            record.start()
            
            # 执行前钩子
            self._run_hooks("before", task_id, module_input)
            
            # 创建执行请求
            request = ExecutionRequest(
                module_input=module_input,
                priority=5,
            )
            
            # 执行模块
            result = module.module_run(request, context)
            
            if result.success:
                record.complete(result)
                self._logger.info(f"任务执行成功: {task_id}")
                # 执行后钩子
                self._run_hooks("after", task_id, result)
            else:
                record.fail(result.error_detail or "未知错误")
                self._logger.error(f"任务执行失败: {task_id} - {result.error_detail}")
                # 错误钩子
                self._run_hooks("on_error", task_id, result.error_detail)
            
        except Exception as e:
            record.fail(str(e))
            self._logger.error(f"任务执行异常: {task_id} - {e}")
            self._run_hooks("on_error", task_id, str(e))
        finally:
            if task_id in self._active_executions:
                del self._active_executions[task_id]
        
        return record
    
    def execute_pipeline(
        self,
        task_id: TaskID,
        pipeline: List[ModuleID],
        initial_input: ModuleInput
    ) -> List[ExecutionRecord]:
        """
        执行管道
        
        按顺序执行多个模块，前一个模块的输出作为后一个模块的输入
        
        Args:
            task_id: 任务ID
            pipeline: 模块ID列表
            initial_input: 初始输入
            
        Returns:
            List[ExecutionRecord]: 执行记录列表
        """
        self._logger.info(f"开始执行管道: {task_id}")
        
        records = []
        current_input = initial_input
        
        for i, module_id in enumerate(pipeline):
            sub_task_id = TaskID(f"{task_id}_step_{i}")
            record = self.execute_task(sub_task_id, current_input, module_id)
            records.append(record)
            
            if record.status == ExecutionStatus.FAILED:
                self._logger.error(f"管道执行失败于步骤 {i}: {module_id}")
                break
            
            # 使用当前结果作为下一步的输入
            if record.result:
                current_input = ModuleInput(
                    task_id=sub_task_id,
                    data=record.result.data
                )
        
        self._logger.info(f"管道执行完成: {task_id}")
        return records
    
    def cancel_task(self, task_id: TaskID) -> bool:
        """取消任务"""
        record = self._active_executions.get(task_id)
        if record:
            record.cancel()
            self._logger.info(f"任务已取消: {task_id}")
            return True
        return False
    
    def get_execution_status(self, task_id: TaskID) -> Optional[ExecutionStatus]:
        """获取执行状态"""
        record = self._execution_history.get(task_id)
        return record.status if record else None
    
    def get_execution_record(self, task_id: TaskID) -> Optional[ExecutionRecord]:
        """获取执行记录"""
        return self._execution_history.get(task_id)
    
    def get_execution_history(
        self,
        module_id: Optional[ModuleID] = None,
        status: Optional[ExecutionStatus] = None
    ) -> List[ExecutionRecord]:
        """
        获取执行历史
        
        Args:
            module_id: 按模块ID过滤
            status: 按状态过滤
            
        Returns:
            List[ExecutionRecord]: 执行记录列表
        """
        records = list(self._execution_history.values())
        
        if module_id:
            records = [r for r in records if r.module_id == module_id]
        
        if status:
            records = [r for r in records if r.status == status]
        
        return records
    
    def register_hook(self, hook_type: str, hook: Callable) -> None:
        """注册执行钩子"""
        if hook_type in self._execution_hooks:
            self._execution_hooks[hook_type].append(hook)
    
    def _run_hooks(self, hook_type: str, task_id: TaskID, data: Any) -> None:
        """运行钩子"""
        for hook in self._execution_hooks.get(hook_type, []):
            try:
                hook(task_id, data)
            except Exception as e:
                self._logger.error(f"钩子执行失败: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取执行统计"""
        total = len(self._execution_history)
        completed = sum(1 for r in self._execution_history.values() if r.status == ExecutionStatus.COMPLETED)
        failed = sum(1 for r in self._execution_history.values() if r.status == ExecutionStatus.FAILED)
        active = len(self._active_executions)
        
        return {
            "total_executions": total,
            "completed": completed,
            "failed": failed,
            "active": active,
            "success_rate": completed / total if total > 0 else 0,
        }


__all__ = [
    "ExecutionEngine",
    "ExecutionRecord",
    "ExecutionStatus",
]
