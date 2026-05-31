"""
超长任务Agent树形双生子模块化执行系统 - 执行上下文实现
Execution Context Implementation for Long-Task Agent Twin-Module Execution System

阶段14：执行上下文管理实现
遵循原则：图难于其易，为大于其细
核心约束：嵌套上下文，步骤追踪，父子引用，上下文栈管理
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import threading

from core_types.core_types import ModuleID, TaskID


# =============================================================================
# 1. 上下文状态枚举 (Context State Enumeration)
# =============================================================================

class ContextState(Enum):
    """上下文状态枚举"""
    CREATED = auto()       # 已创建
    ACTIVE = auto()        # 活跃（正在执行）
    PAUSED = auto()        # 暂停
    COMPLETED = auto()     # 已完成
    FAILED = auto()        # 失败
    CANCELLED = auto()     # 已取消


# =============================================================================
# 2. 上下文条目 (Context Entry)
# =============================================================================

@dataclass
class ContextEntry:
    """
    上下文条目
    记录上下文中的单个键值对
    """
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    source: str = ""  # 来源（模块ID或系统）

    def update(self, new_value: Any) -> None:
        """更新值"""
        self.value = new_value
        self.updated_at = datetime.now()


# =============================================================================
# 3. 步骤信息 (Step Info)
# =============================================================================

@dataclass
class StepInfo:
    """
    步骤信息
    记录单个执行步骤的详细信息
    """
    step_number: int = 0
    step_name: str = ""
    description: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending/running/completed/failed/skipped
    result: Any = None
    error: Optional[str] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        """步骤耗时（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "step_number": self.step_number,
            "step_name": self.step_name,
            "description": self.description,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "duration_seconds": self.duration_seconds,
        }


# =============================================================================
# 4. 执行上下文 (Execution Context)
# =============================================================================

class ExecutionContext:
    """
    执行上下文

    管理模块执行过程中的上下文信息，支持：
    1. 步骤追踪（current_step / total_steps）
    2. 父子上下文引用（嵌套执行）
    3. 上下文栈管理（全局追踪）
    4. 键值数据存储
    5. 执行状态管理
    6. 线程安全

    使用方式：
        # 创建根上下文
        root_ctx = ExecutionContext(
            context_id="root",
            task_id=TaskID("task_001"),
            total_steps=10,
        )

        # 创建子上下文
        child_ctx = root_ctx.create_child(
            context_id="child_001",
            module_id=ModuleID("module_001"),
        )

        # 推进步骤
        root_ctx.advance_step("初始化模块")
        root_ctx.complete_current_step(result="ok")
    """

    # 类级别的上下文栈（线程局部存储）
    _context_stack: List["ExecutionContext"] = []
    _stack_lock = threading.RLock()

    def __init__(
        self,
        context_id: str = "",
        task_id: Optional[TaskID] = None,
        module_id: Optional[ModuleID] = None,
        total_steps: int = 0,
        parent: Optional["ExecutionContext"] = None,
    ):
        """
        初始化执行上下文

        Args:
            context_id: 上下文唯一标识
            task_id: 关联的任务ID
            module_id: 关联的模块ID
            total_steps: 总步骤数
            parent: 父上下文引用
        """
        self._context_id = context_id
        self._task_id = task_id
        self._module_id = module_id
        self._parent = parent

        # 步骤追踪
        self._current_step = 0
        self._total_steps = total_steps
        self._steps: List[StepInfo] = []

        # 状态
        self._state = ContextState.CREATED
        self._created_at = datetime.now()
        self._completed_at: Optional[datetime] = None

        # 数据存储
        self._data: Dict[str, ContextEntry] = {}

        # 子上下文
        self._children: List["ExecutionContext"] = []

        # 线程锁
        self._lock = threading.RLock()

        # 错误信息
        self._error: Optional[str] = None

    # =====================================================================
    # 属性
    # =====================================================================

    @property
    def context_id(self) -> str:
        """上下文ID"""
        return self._context_id

    @property
    def task_id(self) -> Optional[TaskID]:
        """任务ID"""
        return self._task_id

    @property
    def module_id(self) -> Optional[ModuleID]:
        """模块ID"""
        return self._module_id

    @property
    def current_step(self) -> int:
        """当前步骤"""
        return self._current_step

    @property
    def total_steps(self) -> int:
        """总步骤数"""
        return self._total_steps

    @property
    def state(self) -> ContextState:
        """上下文状态"""
        return self._state

    @property
    def parent(self) -> Optional["ExecutionContext"]:
        """父上下文"""
        return self._parent

    @property
    def children(self) -> List["ExecutionContext"]:
        """子上下文列表"""
        return list(self._children)

    @property
    def depth(self) -> int:
        """上下文深度（根为0）"""
        d = 0
        p = self._parent
        while p is not None:
            d += 1
            p = p._parent
        return d

    @property
    def progress(self) -> float:
        """执行进度（0.0 ~ 1.0）"""
        if self._total_steps <= 0:
            return 0.0
        return min(1.0, self._current_step / self._total_steps)

    @property
    def is_root(self) -> bool:
        """是否为根上下文"""
        return self._parent is None

    @property
    def is_active(self) -> bool:
        """是否活跃"""
        return self._state == ContextState.ACTIVE

    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self._state in (ContextState.COMPLETED, ContextState.FAILED, ContextState.CANCELLED)

    @property
    def error(self) -> Optional[str]:
        """错误信息"""
        return self._error

    @property
    def root(self) -> "ExecutionContext":
        """获取根上下文"""
        ctx = self
        while ctx._parent is not None:
            ctx = ctx._parent
        return ctx

    # =====================================================================
    # 状态管理
    # =====================================================================

    def activate(self) -> None:
        """激活上下文"""
        with self._lock:
            self._state = ContextState.ACTIVE

    def pause(self) -> None:
        """暂停上下文"""
        with self._lock:
            self._state = ContextState.PAUSED

    def resume(self) -> None:
        """恢复上下文"""
        with self._lock:
            if self._state == ContextState.PAUSED:
                self._state = ContextState.ACTIVE

    def complete(self) -> None:
        """完成上下文"""
        with self._lock:
            self._state = ContextState.COMPLETED
            self._completed_at = datetime.now()

    def fail(self, error: str) -> None:
        """标记失败"""
        with self._lock:
            self._state = ContextState.FAILED
            self._error = error
            self._completed_at = datetime.now()

    def cancel(self) -> None:
        """取消上下文"""
        with self._lock:
            self._state = ContextState.CANCELLED
            self._completed_at = datetime.now()

    # =====================================================================
    # 步骤管理
    # =====================================================================

    def set_total_steps(self, total: int) -> None:
        """设置总步骤数"""
        with self._lock:
            self._total_steps = total

    def advance_step(self, step_name: str = "", description: str = "") -> StepInfo:
        """
        推进到下一步

        Args:
            step_name: 步骤名称
            description: 步骤描述

        Returns:
            StepInfo: 当前步骤信息
        """
        with self._lock:
            # 完成上一步（如果有的话）
            if self._steps and self._steps[-1].status == "running":
                self._steps[-1].status = "completed"
                self._steps[-1].completed_at = datetime.now()

            # 推进步骤
            self._current_step += 1
            step = StepInfo(
                step_number=self._current_step,
                step_name=step_name or f"step_{self._current_step}",
                description=description,
                started_at=datetime.now(),
                status="running",
            )
            self._steps.append(step)
            return step

    def complete_current_step(self, result: Any = None, error: Optional[str] = None) -> StepInfo:
        """
        完成当前步骤

        Args:
            result: 步骤结果
            error: 错误信息

        Returns:
            StepInfo: 完成的步骤信息
        """
        with self._lock:
            if not self._steps:
                raise RuntimeError("没有活跃的步骤")

            step = self._steps[-1]
            step.completed_at = datetime.now()
            step.result = result
            step.error = error
            step.status = "failed" if error else "completed"
            return step

    def skip_step(self, reason: str = "") -> StepInfo:
        """
        跳过当前步骤

        Args:
            reason: 跳过原因

        Returns:
            StepInfo: 跳过的步骤信息
        """
        with self._lock:
            self._current_step += 1
            step = StepInfo(
                step_number=self._current_step,
                status="skipped",
                result=reason,
            )
            self._steps.append(step)
            return step

    def get_step(self, step_number: int) -> Optional[StepInfo]:
        """获取指定步骤信息"""
        with self._lock:
            if 1 <= step_number <= len(self._steps):
                return self._steps[step_number - 1]
            return None

    def get_all_steps(self) -> List[StepInfo]:
        """获取所有步骤信息"""
        with self._lock:
            return list(self._steps)

    def get_completed_steps(self) -> List[StepInfo]:
        """获取已完成的步骤"""
        with self._lock:
            return [s for s in self._steps if s.status == "completed"]

    def get_failed_steps(self) -> List[StepInfo]:
        """获取失败的步骤"""
        with self._lock:
            return [s for s in self._steps if s.status == "failed"]

    # =====================================================================
    # 数据管理
    # =====================================================================

    def set(self, key: str, value: Any, source: str = "") -> None:
        """
        设置上下文数据

        Args:
            key: 键
            value: 值
            source: 来源
        """
        with self._lock:
            if key in self._data:
                self._data[key].update(value)
            else:
                self._data[key] = ContextEntry(
                    key=key,
                    value=value,
                    source=source,
                )

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取上下文数据

        Args:
            key: 键
            default: 默认值

        Returns:
            Any: 值或默认值
        """
        with self._lock:
            entry = self._data.get(key)
            if entry is not None:
                return entry.value
            return default

    def get_with_source(self, key: str, default: Any = None) -> Tuple[Any, str]:
        """
        获取上下文数据及其来源

        Args:
            key: 键
            default: 默认值

        Returns:
            Tuple[Any, str]: (值, 来源)
        """
        with self._lock:
            entry = self._data.get(key)
            if entry is not None:
                return entry.value, entry.source
            return default, ""

    def has(self, key: str) -> bool:
        """检查键是否存在"""
        with self._lock:
            return key in self._data

    def delete(self, key: str) -> bool:
        """删除键"""
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def keys(self) -> List[str]:
        """获取所有键"""
        with self._lock:
            return list(self._data.keys())

    def items(self) -> Dict[str, Any]:
        """获取所有键值对"""
        with self._lock:
            return {k: v.value for k, v in self._data.items()}

    # =====================================================================
    # 上下文查找（向上冒泡）
    # =====================================================================

    def get_from_hierarchy(self, key: str, default: Any = None) -> Any:
        """
        从上下文层级中查找数据（先查当前，再查父级，逐级向上）

        Args:
            key: 键
            default: 默认值

        Returns:
            Any: 找到的值或默认值
        """
        with self._lock:
            ctx = self
            while ctx is not None:
                if ctx.has(key):
                    return ctx.get(key)
                ctx = ctx._parent
            return default

    # =====================================================================
    # 子上下文管理
    # =====================================================================

    def create_child(
        self,
        context_id: str = "",
        module_id: Optional[ModuleID] = None,
        total_steps: int = 0,
    ) -> "ExecutionContext":
        """
        创建子上下文

        Args:
            context_id: 子上下文ID
            module_id: 关联模块ID
            total_steps: 子上下文总步骤数

        Returns:
            ExecutionContext: 子上下文
        """
        with self._lock:
            child = ExecutionContext(
                context_id=context_id,
                task_id=self._task_id,
                module_id=module_id,
                total_steps=total_steps,
                parent=self,
            )
            self._children.append(child)
            return child

    def remove_child(self, context_id: str) -> bool:
        """移除子上下文"""
        with self._lock:
            for i, child in enumerate(self._children):
                if child.context_id == context_id:
                    self._children.pop(i)
                    return True
            return False

    def get_child(self, context_id: str) -> Optional["ExecutionContext"]:
        """获取子上下文"""
        with self._lock:
            for child in self._children:
                if child.context_id == context_id:
                    return child
            return None

    def get_all_descendants(self) -> List["ExecutionContext"]:
        """获取所有后代上下文（递归）"""
        with self._lock:
            result = []
            for child in self._children:
                result.append(child)
                result.extend(child.get_all_descendants())
            return result

    # =====================================================================
    # 上下文栈管理（类方法）
    # =====================================================================

    @classmethod
    def push(cls, context: "ExecutionContext") -> None:
        """将上下文推入全局栈"""
        with cls._stack_lock:
            cls._context_stack.append(context)

    @classmethod
    def pop(cls) -> Optional["ExecutionContext"]:
        """从全局栈弹出上下文"""
        with cls._stack_lock:
            if cls._context_stack:
                return cls._context_stack.pop()
            return None

    @classmethod
    def current(cls) -> Optional["ExecutionContext"]:
        """获取当前（栈顶）上下文"""
        with cls._stack_lock:
            if cls._context_stack:
                return cls._context_stack[-1]
            return None

    @classmethod
    def stack_depth(cls) -> int:
        """获取栈深度"""
        with cls._stack_lock:
            return len(cls._context_stack)

    @classmethod
    def clear_stack(cls) -> None:
        """清空全局栈"""
        with cls._stack_lock:
            cls._context_stack.clear()

    # =====================================================================
    # 上下文管理器支持
    # =====================================================================

    def __enter__(self) -> "ExecutionContext":
        """进入上下文"""
        self.activate()
        ExecutionContext.push(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """退出上下文"""
        ExecutionContext.pop()
        if exc_type is not None:
            self.fail(str(exc_val))
        elif self._state == ContextState.ACTIVE:
            self.complete()

    # =====================================================================
    # 魔术方法
    # =====================================================================

    def __repr__(self) -> str:
        return (
            f"ExecutionContext(id={self._context_id}, "
            f"step={self._current_step}/{self._total_steps}, "
            f"state={self._state.name}, "
            f"depth={self.depth})"
        )

    def __str__(self) -> str:
        return self._context_id


# =============================================================================
# 模块导出列表
# =============================================================================

__all__ = [
    # 枚举
    "ContextState",
    # 数据类
    "ContextEntry",
    "StepInfo",
    # 核心
    "ExecutionContext",
]
