"""
超长任务Agent树形双生子模块化执行系统 - 核心类型定义
Core Types Definition for Long-Task Agent Twin-Module Execution System

阶段1：核心类型定义
遵循原则：图难于其易，为大于其细
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import uuid


# =============================================================================
# 1. 基础标识类型 (Basic Identifier Types)
# =============================================================================

class ModuleID:
    """
    模块唯一标识符
    采用UUID确保全局唯一性
    """
    def __init__(self, prefix: str = ""):
        self._id = f"{prefix}_{uuid.uuid4().hex[:12]}" if prefix else uuid.uuid4().hex[:16]
    
    def __str__(self) -> str:
        return self._id
    
    def __repr__(self) -> str:
        return f"ModuleID({self._id})"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, ModuleID):
            return self._id == other._id
        return False
    
    def __hash__(self) -> int:
        return hash(self._id)


class TaskID:
    """
    任务唯一标识符
    """
    def __init__(self, prefix: str = "task"):
        self._id = f"{prefix}_{uuid.uuid4().hex[:12]}"
    
    def __str__(self) -> str:
        return self._id
    
    def __repr__(self) -> str:
        return f"TaskID({self._id})"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, TaskID):
            return self._id == other._id
        return False
    
    def __hash__(self) -> int:
        return hash(self._id)


class StepID:
    """
    步骤唯一标识符
    """
    def __init__(self, task_id: str, step_number: int):
        self._id = f"{task_id}_step_{step_number:06d}"
        self._step_number = step_number
    
    def __str__(self) -> str:
        return self._id
    
    def __repr__(self) -> str:
        return f"StepID({self._id})"
    
    @property
    def step_number(self) -> int:
        return self._step_number


# =============================================================================
# 2. 模块类型枚举 (Module Type Enumeration)
# =============================================================================

class ModuleType(Enum):
    """
    模块类型枚举
    严格区分管控类模块和执行类模块
    """
    CONTROL = auto()   # 管控类模块：规划、校验、监控、记忆、安全
    EXECUTE = auto()   # 执行类模块：拆解、调用、落地、迭代、输出


class ModuleLevel(Enum):
    """
    模块层级枚举
    """
    ROOT = 0      # 根模块
    LEVEL1 = 1    # 一级模块
    LEVEL2 = 2    # 二级模块
    LEVEL3 = 3    # 三级模块
    LEVEL4 = 4    # 四级模块


# =============================================================================
# 3. 模块状态枚举 (Module State Enumeration)
# =============================================================================

class ModuleState(Enum):
    """
    模块状态枚举
    描述模块的生命周期状态
    """
    UNINITIALIZED = auto()   # 未初始化
    INITIALIZING = auto()    # 初始化中
    READY = auto()           # 就绪
    RUNNING = auto()         # 运行中
    PAUSED = auto()          # 暂停
    COMPLETED = auto()       # 已完成
    ERROR = auto()           # 错误
    RECOVERING = auto()      # 恢复中


class TaskState(Enum):
    """
    任务状态枚举
    """
    PENDING = auto()         # 待处理
    PLANNING = auto()        # 规划中
    EXECUTING = auto()       # 执行中
    VALIDATING = auto()      # 校验中
    PAUSED = auto()          # 暂停
    COMPLETED = auto()       # 已完成
    FAILED = auto()          # 失败
    RECOVERING = auto()      # 恢复中


class StepState(Enum):
    """
    单步执行状态枚举
    """
    PENDING = auto()         # 待执行
    EXECUTING = auto()       # 执行中
    VALIDATING = auto()      # 校验中
    COMPLETED = auto()       # 已完成
    FAILED = auto()          # 失败
    RETRYING = auto()        # 重试中


# =============================================================================
# 4. 任务参数类型 (Task Parameter Types)
# =============================================================================

@dataclass
class TaskParam:
    """
    任务参数基类
    所有任务参数的基类，支持扩展
    """
    task_id: TaskID = field(default_factory=lambda: TaskID())
    task_name: str = ""
    task_description: str = ""
    max_steps: int = 10000           # 最大执行步数
    timeout_seconds: int = 3600      # 超时时间（秒）
    enable_checkpoint: bool = True   # 是否启用断点
    checkpoint_interval: int = 100   # 断点保存间隔（步）
    custom_params: Dict[str, Any] = field(default_factory=dict)
    
    def get_param(self, key: str, default: Any = None) -> Any:
        """获取自定义参数"""
        return self.custom_params.get(key, default)
    
    def set_param(self, key: str, value: Any) -> None:
        """设置自定义参数"""
        self.custom_params[key] = value


@dataclass
class ModuleParam:
    """
    模块参数基类
    """
    module_id: ModuleID = field(default_factory=lambda: ModuleID())
    module_name: str = ""
    module_type: ModuleType = ModuleType.CONTROL
    module_level: ModuleLevel = ModuleLevel.LEVEL1
    parent_module_id: Optional[ModuleID] = None
    config: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# 5. 初始化结果类型 (Initialization Result Types)
# =============================================================================

@dataclass
class InitResult:
    """
    初始化结果
    """
    success: bool
    module_id: ModuleID
    message: str = ""
    error_code: Optional[str] = None
    error_detail: Optional[str] = None
    init_timestamp: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def success_result(cls, module_id: ModuleID, message: str = "初始化成功") -> "InitResult":
        """创建成功结果"""
        return cls(success=True, module_id=module_id, message=message)
    
    @classmethod
    def failure_result(cls, module_id: ModuleID, error_code: str, error_detail: str) -> "InitResult":
        """创建失败结果"""
        return cls(
            success=False,
            module_id=module_id,
            message="初始化失败",
            error_code=error_code,
            error_detail=error_detail
        )


# =============================================================================
# 6. 模块输入输出类型 (Module Input/Output Types)
# =============================================================================

@dataclass
class ModuleInput:
    """
    模块输入
    """
    task_id: TaskID
    data: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """获取输入数据"""
        return self.data.get(key, default)
    
    def set_data(self, key: str, value: Any) -> None:
        """设置输入数据"""
        self.data[key] = value


@dataclass
class ModuleOutput:
    """
    模块输出
    """
    task_id: TaskID
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    error_code: Optional[str] = None
    error_detail: Optional[str] = None
    execution_time_ms: int = 0
    output_timestamp: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def success_output(cls, task_id: TaskID, data: Dict[str, Any] = None, message: str = "") -> "ModuleOutput":
        """创建成功输出"""
        return cls(
            task_id=task_id,
            success=True,
            data=data or {},
            message=message or "执行成功"
        )
    
    @classmethod
    def failure_output(cls, task_id: TaskID, error_code: str, error_detail: str) -> "ModuleOutput":
        """创建失败输出"""
        return cls(
            task_id=task_id,
            success=False,
            error_code=error_code,
            error_detail=error_detail,
            message="执行失败"
        )


# =============================================================================
# 7. 校验结果类型 (Validation Result Types)
# =============================================================================

@dataclass
class CheckResult:
    """
    校验结果
    """
    passed: bool
    check_type: str
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    severity: str = "info"  # info, warning, error, critical
    
    @classmethod
    def passed_result(cls, check_type: str, message: str = "校验通过") -> "CheckResult":
        """创建通过结果"""
        return cls(passed=True, check_type=check_type, message=message)
    
    @classmethod
    def failed_result(cls, check_type: str, message: str, severity: str = "error") -> "CheckResult":
        """创建失败结果"""
        return cls(passed=False, check_type=check_type, message=message, severity=severity)


@dataclass
class ValidationReport:
    """
    校验报告
    汇总多个校验结果
    """
    task_id: TaskID
    overall_passed: bool
    results: List[CheckResult] = field(default_factory=list)
    summary: str = ""
    validation_timestamp: datetime = field(default_factory=datetime.now)
    
    def add_result(self, result: CheckResult) -> None:
        """添加校验结果"""
        self.results.append(result)
        if not result.passed and result.severity in ["error", "critical"]:
            self.overall_passed = False


# =============================================================================
# 8. 快照数据类型 (Snapshot Data Types)
# =============================================================================

@dataclass
class SnapshotData:
    """
    快照数据
    用于断点续跑和状态恢复
    """
    module_id: ModuleID
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    snapshot_version: str = "1.0"
    state_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def set_state(self, key: str, value: Any) -> None:
        """设置状态数据"""
        self.state_data[key] = value
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """获取状态数据"""
        return self.state_data.get(key, default)


@dataclass
class CheckpointData:
    """
    断点数据
    用于任务断点续跑
    """
    task_id: TaskID
    checkpoint_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    current_step: int = 0
    total_steps: int = 0
    task_state: TaskState = TaskState.EXECUTING
    module_snapshots: Dict[str, SnapshotData] = field(default_factory=dict)
    execution_context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# 9. 执行上下文类型 (Execution Context Types)
# =============================================================================

@dataclass
class ExecutionContext:
    """
    执行上下文
    记录执行过程中的上下文信息
    """
    task_id: TaskID
    current_step: int = 0
    total_steps: int = 0
    step_history: List[StepID] = field(default_factory=list)
    context_stack: List[Dict[str, Any]] = field(default_factory=list)
    parent_context: Optional["ExecutionContext"] = None
    
    def push_context(self, context: Dict[str, Any]) -> None:
        """压入上下文"""
        self.context_stack.append(context)
    
    def pop_context(self) -> Optional[Dict[str, Any]]:
        """弹出上下文"""
        if self.context_stack:
            return self.context_stack.pop()
        return None
    
    def record_step(self, step_id: StepID) -> None:
        """记录步骤"""
        self.step_history.append(step_id)
        self.current_step += 1


# =============================================================================
# 10. 事件类型 (Event Types)
# =============================================================================

class ModuleEventType(Enum):
    """
    模块事件类型
    """
    INIT_STARTED = auto()
    INIT_COMPLETED = auto()
    INIT_FAILED = auto()
    RUN_STARTED = auto()
    RUN_COMPLETED = auto()
    RUN_FAILED = auto()
    CHECK_STARTED = auto()
    CHECK_COMPLETED = auto()
    SNAPSHOT_CREATED = auto()
    SNAPSHOT_RESTORED = auto()
    STATE_CHANGED = auto()
    ERROR_OCCURRED = auto()


@dataclass
class ModuleEvent:
    """
    模块事件
    """
    event_type: ModuleEventType
    module_id: ModuleID
    task_id: Optional[TaskID] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


# =============================================================================
# 11. 工具调用类型 (Tool Call Types)
# =============================================================================

@dataclass
class ToolCall:
    """
    工具调用
    """
    tool_name: str
    tool_params: Dict[str, Any] = field(default_factory=dict)
    call_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timeout_seconds: int = 30


@dataclass
class ToolResult:
    """
    工具调用结果
    """
    call_id: str
    success: bool
    result_data: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    execution_time_ms: int = 0


# =============================================================================
# 12. 类型别名 (Type Aliases)
# =============================================================================

# 模块状态字典类型
ModuleStateDict = Dict[str, Any]

# 任务参数字典类型
TaskParamDict = Dict[str, Any]

# 执行结果字典类型
ExecutionResultDict = Dict[str, Any]


# =============================================================================
# 验证函数 (Validation Functions)
# =============================================================================

def validate_module_id(module_id: Union[str, ModuleID]) -> ModuleID:
    """验证并转换模块ID"""
    if isinstance(module_id, ModuleID):
        return module_id
    return ModuleID(module_id)


def validate_task_id(task_id: Union[str, TaskID]) -> TaskID:
    """验证并转换任务ID"""
    if isinstance(task_id, TaskID):
        return task_id
    return TaskID(task_id)


def is_valid_module_state_transition(from_state: ModuleState, to_state: ModuleState) -> bool:
    """
    验证模块状态转换是否合法
    """
    valid_transitions = {
        ModuleState.UNINITIALIZED: [ModuleState.INITIALIZING],
        ModuleState.INITIALIZING: [ModuleState.READY, ModuleState.ERROR],
        ModuleState.READY: [ModuleState.RUNNING, ModuleState.ERROR],
        ModuleState.RUNNING: [ModuleState.PAUSED, ModuleState.COMPLETED, ModuleState.ERROR],
        ModuleState.PAUSED: [ModuleState.RUNNING, ModuleState.ERROR],
        ModuleState.ERROR: [ModuleState.RECOVERING],
        ModuleState.RECOVERING: [ModuleState.READY, ModuleState.ERROR],
    }
    return to_state in valid_transitions.get(from_state, [])


# =============================================================================
# 模块导出列表
# =============================================================================

__all__ = [
    # 基础标识类型
    "ModuleID",
    "TaskID",
    "StepID",
    
    # 枚举类型
    "ModuleType",
    "ModuleLevel",
    "ModuleState",
    "TaskState",
    "StepState",
    "ModuleEventType",
    
    # 参数类型
    "TaskParam",
    "ModuleParam",
    
    # 结果类型
    "InitResult",
    "ModuleInput",
    "ModuleOutput",
    "CheckResult",
    "ValidationReport",
    
    # 快照类型
    "SnapshotData",
    "CheckpointData",
    
    # 上下文类型
    "ExecutionContext",
    
    # 事件类型
    "ModuleEvent",
    
    # 工具调用类型
    "ToolCall",
    "ToolResult",
    
    # 类型别名
    "ModuleStateDict",
    "TaskParamDict",
    "ExecutionResultDict",
    
    # 验证函数
    "validate_module_id",
    "validate_task_id",
    "is_valid_module_state_transition",
]
