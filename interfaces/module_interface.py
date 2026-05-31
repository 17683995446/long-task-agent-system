"""
超长任务Agent树形双生子模块化执行系统 - 标准接口协议定义
Standard Interface Protocol Definition for Long-Task Agent Twin-Module Execution System

阶段2：标准接口协议定义
遵循原则：图难于其易，为大于其细
遵循原则：接口隔离原则（ISP）
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from dataclasses import dataclass, field
from datetime import datetime
import uuid

# 导入第1阶段定义的核心类型
from core_types.core_types import (
    ModuleID, TaskID, StepID,
    ModuleType, ModuleLevel, ModuleState,
    TaskParam, ModuleParam,
    InitResult, ModuleInput, ModuleOutput,
    CheckResult, ValidationReport,
    SnapshotData, CheckpointData,
    ExecutionContext,
    ModuleEvent, ModuleEventType,
)


# =============================================================================
# 1. 接口元数据类型 (Interface Metadata Types)
# =============================================================================

@dataclass
class InterfaceMetadata:
    """
    接口元数据
    描述接口的基本信息
    """
    interface_name: str
    interface_version: str = "1.0"
    description: str = ""
    author: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "interface_name": self.interface_name,
            "interface_version": self.interface_version,
            "description": self.description,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat(),
        }


@dataclass
class InterfaceCapability:
    """
    接口能力描述
    描述接口支持的功能特性
    """
    capability_name: str
    capability_version: str = "1.0"
    is_required: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def supports(self, feature: str) -> bool:
        """检查是否支持特定功能"""
        return feature in self.parameters.get("supported_features", [])


# =============================================================================
# 2. 模块初始化接口 (Module Initialization Interface)
# =============================================================================

@dataclass
class InitRequest:
    """
    初始化请求
    """
    module_id: ModuleID
    module_param: ModuleParam
    task_param: Optional[TaskParam] = None
    parent_module_id: Optional[ModuleID] = None
    init_options: Dict[str, Any] = field(default_factory=dict)
    request_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class InitContext:
    """
    初始化上下文
    记录初始化过程中的上下文信息
    """
    init_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    init_sequence: int = 0
    dependencies: List[ModuleID] = field(default_factory=list)
    config_overrides: Dict[str, Any] = field(default_factory=dict)
    environment_vars: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class IModuleInit(Protocol):
    """
    模块初始化接口协议
    
    功能：模块加载、参数解析、私有空间初始化、规则加载
    调用时机：模块实例化后首次使用
    约束：每个模块生命周期内只能初始化一次
    """
    
    @abstractmethod
    def module_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """
        模块初始化
        
        Args:
            request: 初始化请求
            context: 初始化上下文
            
        Returns:
            InitResult: 初始化结果
            
        Raises:
            InitException: 初始化失败时抛出
        """
        ...
    
    @abstractmethod
    def get_init_metadata(self) -> InterfaceMetadata:
        """
        获取初始化接口元数据
        
        Returns:
            InterfaceMetadata: 接口元数据
        """
        ...
    
    @abstractmethod
    def get_init_capabilities(self) -> List[InterfaceCapability]:
        """
        获取初始化接口能力列表
        
        Returns:
            List[InterfaceCapability]: 能力列表
        """
        ...
    
    @abstractmethod
    def validate_init_params(self, request: InitRequest) -> ValidationReport:
        """
        验证初始化参数
        
        Args:
            request: 初始化请求
            
        Returns:
            ValidationReport: 验证报告
        """
        ...


# =============================================================================
# 3. 模块执行接口 (Module Execution Interface)
# =============================================================================

@dataclass
class ExecutionRequest:
    """
    执行请求
    """
    module_input: ModuleInput
    execution_options: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    priority: int = 5  # 1-10, 10为最高优先级
    request_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionContext:
    """
    执行上下文（接口层）
    与core_types中的ExecutionContext不同，这是接口层面的上下文
    """
    execution_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_execution_id: Optional[str] = None
    execution_depth: int = 0
    call_chain: List[str] = field(default_factory=list)
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    
    def enter_sub_execution(self, module_name: str) -> "ExecutionContext":
        """进入子执行上下文"""
        return ExecutionContext(
            execution_id=uuid.uuid4().hex[:16],
            parent_execution_id=self.execution_id,
            execution_depth=self.execution_depth + 1,
            call_chain=self.call_chain + [module_name],
            resource_limits=self.resource_limits.copy(),
        )


@dataclass
class ExecutionMetrics:
    """
    执行指标
    """
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    cpu_time_ms: int = 0
    memory_peak_mb: int = 0
    io_read_bytes: int = 0
    io_write_bytes: int = 0
    
    @property
    def execution_duration_ms(self) -> int:
        """计算执行时长（毫秒）"""
        if self.end_time:
            return int((self.end_time - self.start_time).total_seconds() * 1000)
        return 0


@runtime_checkable
class IModuleRun(Protocol):
    """
    模块执行接口协议
    
    功能：模块核心业务逻辑执行，唯一对外执行入口
    调用时机：模块初始化完成后，执行业务逻辑时
    约束：执行前必须已完成初始化
    """
    
    @abstractmethod
    def module_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """
        模块执行
        
        Args:
            request: 执行请求
            context: 执行上下文
            
        Returns:
            ModuleOutput: 模块输出
            
        Raises:
            RunException: 执行失败时抛出
        """
        ...
    
    @abstractmethod
    def get_run_metadata(self) -> InterfaceMetadata:
        """
        获取执行接口元数据
        
        Returns:
            InterfaceMetadata: 接口元数据
        """
        ...
    
    @abstractmethod
    def get_run_capabilities(self) -> List[InterfaceCapability]:
        """
        获取执行接口能力列表
        
        Returns:
            List[InterfaceCapability]: 能力列表
        """
        ...
    
    @abstractmethod
    def can_execute(self, module_input: ModuleInput) -> CheckResult:
        """
        检查是否可以执行
        
        Args:
            module_input: 模块输入
            
        Returns:
            CheckResult: 检查结果
        """
        ...
    
    @abstractmethod
    def get_execution_metrics(self) -> ExecutionMetrics:
        """
        获取执行指标
        
        Returns:
            ExecutionMetrics: 执行指标
        """
        ...


# =============================================================================
# 4. 模块校验接口 (Module Validation Interface)
# =============================================================================

@dataclass
class ValidationRequest:
    """
    校验请求
    """
    check_type: str  # 校验类型标识
    check_data: Dict[str, Any] = field(default_factory=dict)
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    strict_mode: bool = False  # 严格模式：任何失败都导致整体失败
    request_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ValidationContext:
    """
    校验上下文
    """
    validation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    validation_sequence: int = 0
    previous_results: List[CheckResult] = field(default_factory=list)
    reference_data: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class IModuleCheck(Protocol):
    """
    模块校验接口协议
    
    功能：执行结果校验、偏差检测、合法性判断
    调用时机：执行完成后，或需要验证状态时
    约束：校验不通过时应提供修正建议
    """
    
    @abstractmethod
    def module_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """
        模块校验
        
        Args:
            request: 校验请求
            context: 校验上下文
            
        Returns:
            CheckResult: 校验结果
            
        Raises:
            CheckException: 校验过程异常时抛出
        """
        ...
    
    @abstractmethod
    def get_check_metadata(self) -> InterfaceMetadata:
        """
        获取校验接口元数据
        
        Returns:
            InterfaceMetadata: 接口元数据
        """
        ...
    
    @abstractmethod
    def get_check_capabilities(self) -> List[InterfaceCapability]:
        """
        获取校验接口能力列表
        
        Returns:
            List[InterfaceCapability]: 能力列表
        """
        ...
    
    @abstractmethod
    def get_supported_check_types(self) -> List[str]:
        """
        获取支持的校验类型列表
        
        Returns:
            List[str]: 校验类型列表
        """
        ...
    
    @abstractmethod
    def validate_and_fix(self, request: ValidationRequest, context: ValidationContext) -> tuple[CheckResult, Optional[Any]]:
        """
        校验并尝试修正
        
        Args:
            request: 校验请求
            context: 校验上下文
            
        Returns:
            tuple[CheckResult, Optional[Any]]: (校验结果, 修正后的数据)
        """
        ...


# =============================================================================
# 5. 模块快照接口 (Module Snapshot Interface)
# =============================================================================

@dataclass
class SnapshotRequest:
    """
    快照请求
    """
    snapshot_type: str = "full"  # full, delta, minimal
    include_metadata: bool = True
    compression_level: int = 5  # 0-9
    encryption_key: Optional[str] = None
    request_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RestoreRequest:
    """
    恢复请求
    """
    snapshot_data: SnapshotData
    restore_options: Dict[str, Any] = field(default_factory=dict)
    validate_before_restore: bool = True
    request_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SnapshotContext:
    """
    快照上下文
    """
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_snapshot_id: Optional[str] = None
    snapshot_sequence: int = 0
    snapshot_chain: List[str] = field(default_factory=list)


@dataclass
class SnapshotInfo:
    """
    快照信息
    """
    snapshot_id: str
    module_id: ModuleID
    created_at: datetime
    snapshot_size_bytes: int
    snapshot_version: str
    checksum: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class IModuleSnapshot(Protocol):
    """
    模块快照接口协议
    
    功能：导出当前模块私有状态，用于持久化与断点续跑
    调用时机：需要保存状态、断点续跑时
    约束：快照应包含完整恢复所需的所有状态
    """
    
    @abstractmethod
    def create_snapshot(self, request: SnapshotRequest, context: SnapshotContext) -> SnapshotData:
        """
        创建快照
        
        Args:
            request: 快照请求
            context: 快照上下文
            
        Returns:
            SnapshotData: 快照数据
            
        Raises:
            SnapshotException: 创建快照失败时抛出
        """
        ...
    
    @abstractmethod
    def restore_from_snapshot(self, request: RestoreRequest) -> InitResult:
        """
        从快照恢复
        
        Args:
            request: 恢复请求
            
        Returns:
            InitResult: 恢复结果（作为初始化结果返回）
            
        Raises:
            RestoreException: 恢复失败时抛出
        """
        ...
    
    @abstractmethod
    def get_snapshot_metadata(self) -> InterfaceMetadata:
        """
        获取快照接口元数据
        
        Returns:
            InterfaceMetadata: 接口元数据
        """
        ...
    
    @abstractmethod
    def get_snapshot_capabilities(self) -> List[InterfaceCapability]:
        """
        获取快照接口能力列表
        
        Returns:
            List[InterfaceCapability]: 能力列表
        """
        ...
    
    @abstractmethod
    def validate_snapshot(self, snapshot_data: SnapshotData) -> CheckResult:
        """
        验证快照有效性
        
        Args:
            snapshot_data: 快照数据
            
        Returns:
            CheckResult: 验证结果
        """
        ...
    
    @abstractmethod
    def get_snapshot_info(self, snapshot_data: SnapshotData) -> SnapshotInfo:
        """
        获取快照信息
        
        Args:
            snapshot_data: 快照数据
            
        Returns:
            SnapshotInfo: 快照信息
        """
        ...


# =============================================================================
# 6. 总接口聚合 (Aggregate Interface)
# =============================================================================

@runtime_checkable
class IModule(Protocol):
    """
    模块总接口
    
    聚合所有4类标准接口，是模块的完整接口定义
    所有模块必须实现此接口
    """
    
    # 模块属性
    @property
    @abstractmethod
    def module_id(self) -> ModuleID:
        """模块ID"""
        ...
    
    @property
    @abstractmethod
    def module_type(self) -> ModuleType:
        """模块类型（管控/执行）"""
        ...
    
    @property
    @abstractmethod
    def module_level(self) -> ModuleLevel:
        """模块层级"""
        ...
    
    @property
    @abstractmethod
    def module_state(self) -> ModuleState:
        """模块状态"""
        ...
    
    @property
    @abstractmethod
    def parent_module_id(self) -> Optional[ModuleID]:
        """父模块ID"""
        ...
    
    # 子模块管理（双子结构）
    @abstractmethod
    def get_control_child(self) -> Optional["IModule"]:
        """
        获取管控子模块（左节点）
        
        Returns:
            Optional[IModule]: 管控子模块，如果没有则返回None
        """
        ...
    
    @abstractmethod
    def get_execute_child(self) -> Optional["IModule"]:
        """
        获取执行子模块（右节点）
        
        Returns:
            Optional[IModule]: 执行子模块，如果没有则返回None
        """
        ...
    
    @abstractmethod
    def set_control_child(self, child: "IModule") -> None:
        """设置管控子模块"""
        ...
    
    @abstractmethod
    def set_execute_child(self, child: "IModule") -> None:
        """设置执行子模块"""
        ...
    
    @abstractmethod
    def has_children(self) -> bool:
        """是否有子模块"""
        ...
    
    @abstractmethod
    def validate_twin_structure(self) -> ValidationReport:
        """验证双子结构"""
        ...
    
    # 继承自4类标准接口的方法
    # IModuleInit
    @abstractmethod
    def module_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """模块初始化"""
        ...
    
    # IModuleRun
    @abstractmethod
    def module_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """模块执行"""
        ...
    
    # IModuleCheck
    @abstractmethod
    def module_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """模块校验"""
        ...
    
    # IModuleSnapshot
    @abstractmethod
    def create_snapshot(self, request: SnapshotRequest, context: SnapshotContext) -> SnapshotData:
        """创建快照"""
        ...
    
    @abstractmethod
    def restore_from_snapshot(self, request: RestoreRequest) -> InitResult:
        """从快照恢复"""
        ...


# =============================================================================
# 7. 接口工具函数 (Interface Utility Functions)
# =============================================================================

def create_default_init_request(module_id: ModuleID, module_name: str = "") -> InitRequest:
    """
    创建默认初始化请求
    
    Args:
        module_id: 模块ID
        module_name: 模块名称
        
    Returns:
        InitRequest: 初始化请求
    """
    module_param = ModuleParam(
        module_id=module_id,
        module_name=module_name,
    )
    return InitRequest(
        module_id=module_id,
        module_param=module_param,
    )


def create_default_execution_request(task_id: TaskID, data: Dict[str, Any] = None) -> ExecutionRequest:
    """
    创建默认执行请求
    
    Args:
        task_id: 任务ID
        data: 输入数据
        
    Returns:
        ExecutionRequest: 执行请求
    """
    module_input = ModuleInput(
        task_id=task_id,
        data=data or {},
    )
    return ExecutionRequest(
        module_input=module_input,
    )


def create_default_validation_request(check_type: str, check_data: Dict[str, Any] = None) -> ValidationRequest:
    """
    创建默认校验请求
    
    Args:
        check_type: 校验类型
        check_data: 校验数据
        
    Returns:
        ValidationRequest: 校验请求
    """
    return ValidationRequest(
        check_type=check_type,
        check_data=check_data or {},
    )


def create_default_snapshot_request(snapshot_type: str = "full") -> SnapshotRequest:
    """
    创建默认快照请求
    
    Args:
        snapshot_type: 快照类型
        
    Returns:
        SnapshotRequest: 快照请求
    """
    return SnapshotRequest(
        snapshot_type=snapshot_type,
    )


def validate_interface_implementation(module: Any, interface_type: type) -> ValidationReport:
    """
    验证模块是否实现了指定接口
    
    Args:
        module: 模块实例
        interface_type: 接口类型
        
    Returns:
        ValidationReport: 验证报告
    """
    task_id = TaskID()
    report = ValidationReport(
        task_id=task_id,
        overall_passed=True,
    )
    
    # 检查是否是Protocol的实例
    if not isinstance(module, interface_type):
        report.add_result(CheckResult.failed_result(
            "interface_check",
            f"模块未实现接口 {interface_type.__name__}",
            "error"
        ))
        return report
    
    report.add_result(CheckResult.passed_result(
        "interface_check",
        f"模块已实现接口 {interface_type.__name__}"
    ))
    
    return report


# =============================================================================
# 8. 接口版本管理 (Interface Version Management)
# =============================================================================

INTERFACE_VERSION = "1.0.0"

COMPATIBLE_VERSIONS = ["1.0.0"]


def get_interface_version() -> str:
    """获取当前接口版本"""
    return INTERFACE_VERSION


def check_version_compatibility(version: str) -> bool:
    """
    检查版本兼容性
    
    Args:
        version: 待检查版本
        
    Returns:
        bool: 是否兼容
    """
    return version in COMPATIBLE_VERSIONS


# =============================================================================
# 模块导出列表
# =============================================================================

__all__ = [
    # 接口元数据类型
    "InterfaceMetadata",
    "InterfaceCapability",
    
    # 初始化接口
    "InitRequest",
    "InitContext",
    "IModuleInit",
    
    # 执行接口
    "ExecutionRequest",
    "ExecutionContext",
    "ExecutionMetrics",
    "IModuleRun",
    
    # 校验接口
    "ValidationRequest",
    "ValidationContext",
    "IModuleCheck",
    
    # 快照接口
    "SnapshotRequest",
    "RestoreRequest",
    "SnapshotContext",
    "SnapshotInfo",
    "IModuleSnapshot",
    
    # 总接口
    "IModule",
    
    # 工具函数
    "create_default_init_request",
    "create_default_execution_request",
    "create_default_validation_request",
    "create_default_snapshot_request",
    "validate_interface_implementation",
    
    # 版本管理
    "get_interface_version",
    "check_version_compatibility",
    "INTERFACE_VERSION",
    "COMPATIBLE_VERSIONS",
]
