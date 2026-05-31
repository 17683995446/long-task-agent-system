"""
超长任务Agent树形双生子模块化执行系统 - 模块基类实现
Base Module Implementation for Long-Task Agent Twin-Module Execution System

阶段3：模块基类实现
遵循原则：图难于其易，为大于其细
遵循原则：接口隔离原则（ISP）
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import threading
import uuid

# 导入第1阶段定义的核心类型
from core_types.core_types import (
    ModuleID, TaskID, StepID,
    ModuleType, ModuleLevel, ModuleState,
    TaskParam, ModuleParam,
    InitResult, ModuleInput, ModuleOutput,
    CheckResult, ValidationReport,
    SnapshotData, CheckpointData,
    ExecutionContext as CoreExecutionContext,
    ModuleEvent, ModuleEventType,
)

# 导入第2阶段定义的接口协议
from interfaces.module_interface import (
    # 接口元数据
    InterfaceMetadata, InterfaceCapability,
    # 初始化接口
    InitRequest, InitContext, IModuleInit,
    # 执行接口
    ExecutionRequest, ExecutionContext, ExecutionMetrics, IModuleRun,
    # 校验接口
    ValidationRequest, ValidationContext, IModuleCheck,
    # 快照接口
    SnapshotRequest, RestoreRequest, SnapshotContext, SnapshotInfo, IModuleSnapshot,
    # 总接口
    IModule,
    # 工具函数
    create_default_init_request,
    create_default_execution_request,
    create_default_validation_request,
    create_default_snapshot_request,
)


# =============================================================================
# 1. 模块私有状态容器 (Module Private State Container)
# =============================================================================

@dataclass
class ModulePrivateState:
    """
    模块私有状态容器
    封装模块内部状态，禁止外部直接访问
    """
    # 基础状态
    module_id: ModuleID
    module_name: str = ""
    module_type: ModuleType = ModuleType.CONTROL
    module_level: ModuleLevel = ModuleLevel.LEVEL1
    module_state: ModuleState = ModuleState.UNINITIALIZED
    
    # 层级关系
    parent_module_id: Optional[ModuleID] = None
    control_child: Optional["BaseModule"] = None
    execute_child: Optional["BaseModule"] = None
    
    # 配置与参数
    module_param: Optional[ModuleParam] = None
    task_param: Optional[TaskParam] = None
    config: Dict[str, Any] = field(default_factory=dict)
    
    # 运行时状态
    init_result: Optional[InitResult] = None
    execution_count: int = 0
    last_execution_time: Optional[datetime] = None
    
    # 执行指标
    execution_metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)
    
    # 内部数据存储（完全私有）
    _internal_data: Dict[str, Any] = field(default_factory=dict)
    
    def set_data(self, key: str, value: Any) -> None:
        """设置内部数据"""
        self._internal_data[key] = value
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """获取内部数据"""
        return self._internal_data.get(key, default)
    
    def has_data(self, key: str) -> bool:
        """检查是否存在内部数据"""
        return key in self._internal_data
    
    def clear_data(self) -> None:
        """清空内部数据"""
        self._internal_data.clear()
    
    def get_all_data(self) -> Dict[str, Any]:
        """获取所有内部数据（用于快照）"""
        return self._internal_data.copy()
    
    def restore_data(self, data: Dict[str, Any]) -> None:
        """恢复内部数据（从快照）"""
        self._internal_data = data.copy()


# =============================================================================
# 2. 模块基类 (Base Module)
# =============================================================================

class BaseModule(ABC, IModuleInit, IModuleRun, IModuleCheck, IModuleSnapshot, IModule):
    """
    模块抽象基类
    
    所有模块的基类，实现4类标准接口的抽象方法框架。
    严格遵循接口隔离原则，模块内部状态完全封装。
    
    属性:
        - module_id: 模块唯一标识
        - module_type: 模块类型（管控/执行）
        - module_level: 模块层级
        - module_state: 模块状态
        - parent_module_id: 父模块ID
    
    子模块管理:
        - 严格双子结构：1个管控子模块 + 1个执行子模块
        - 通过 get_control_child() / get_execute_child() 访问
        - 通过 set_control_child() / set_execute_child() 设置
    """
    
    def __init__(self, module_id: Optional[ModuleID] = None):
        """
        初始化模块基类
        
        Args:
            module_id: 模块ID，如果为None则自动生成
        """
        # 初始化私有状态
        self._state = ModulePrivateState(
            module_id=module_id or ModuleID(),
        )
        
        # 线程锁（用于线程安全）
        self._lock = threading.RLock()
        
        # 事件监听器集合
        self._event_listeners: Set[callable] = set()
        
        # 初始化标记
        self._initialized = False
        
        # 接口元数据缓存
        self._init_metadata: Optional[InterfaceMetadata] = None
        self._run_metadata: Optional[InterfaceMetadata] = None
        self._check_metadata: Optional[InterfaceMetadata] = None
        self._snapshot_metadata: Optional[InterfaceMetadata] = None
    
    # =====================================================================
    # 属性访问（只读）
    # =====================================================================
    
    @property
    def module_id(self) -> ModuleID:
        """模块ID（只读）"""
        return self._state.module_id
    
    @property
    def module_type(self) -> ModuleType:
        """模块类型（只读）"""
        return self._state.module_type
    
    @property
    def module_level(self) -> ModuleLevel:
        """模块层级（只读）"""
        return self._state.module_level
    
    @property
    def module_state(self) -> ModuleState:
        """模块状态（只读）"""
        return self._state.module_state
    
    @property
    def parent_module_id(self) -> Optional[ModuleID]:
        """父模块ID（只读）"""
        return self._state.parent_module_id
    
    @property
    def module_name(self) -> str:
        """模块名称（只读）"""
        return self._state.module_name
    
    # =====================================================================
    # 子模块管理（双子结构）
    # =====================================================================
    
    def get_control_child(self) -> Optional["BaseModule"]:
        """
        获取管控子模块（左节点）
        
        Returns:
            Optional[BaseModule]: 管控子模块，如果没有则返回None
        """
        return self._state.control_child
    
    def get_execute_child(self) -> Optional["BaseModule"]:
        """
        获取执行子模块（右节点）
        
        Returns:
            Optional[BaseModule]: 执行子模块，如果没有则返回None
        """
        return self._state.execute_child
    
    def set_control_child(self, child: "BaseModule") -> None:
        """
        设置管控子模块
        
        Args:
            child: 管控子模块
            
        Raises:
            ValueError: 如果子模块类型不匹配
        """
        with self._lock:
            if child.module_type != ModuleType.CONTROL:
                raise ValueError(f"管控子模块必须是CONTROL类型，但传入的是{child.module_type}")
            child._state.parent_module_id = self.module_id
            self._state.control_child = child
    
    def set_execute_child(self, child: "BaseModule") -> None:
        """
        设置执行子模块
        
        Args:
            child: 执行子模块
            
        Raises:
            ValueError: 如果子模块类型不匹配
        """
        with self._lock:
            if child.module_type != ModuleType.EXECUTE:
                raise ValueError(f"执行子模块必须是EXECUTE类型，但传入的是{child.module_type}")
            child._state.parent_module_id = self.module_id
            self._state.execute_child = child
    
    def has_children(self) -> bool:
        """
        是否有子模块
        
        Returns:
            bool: 是否有子模块
        """
        return self._state.control_child is not None or self._state.execute_child is not None
    
    def validate_twin_structure(self) -> ValidationReport:
        """
        验证双子结构
        
        检查：
        1. 子模块数量是否为0或2（严格双子约束）
        2. 管控子模块类型是否正确
        3. 执行子模块类型是否正确
        
        Returns:
            ValidationReport: 验证报告
        """
        task_id = TaskID()
        report = ValidationReport(
            task_id=task_id,
            overall_passed=True,
        )
        
        control_child = self._state.control_child
        execute_child = self._state.execute_child
        
        # 检查1：子模块数量必须是0或2
        if (control_child is None) != (execute_child is None):
            report.add_result(CheckResult.failed_result(
                "twin_structure_check",
                f"双子结构违反：子模块数量必须是0或2，当前有管控子模块({control_child is not None})和执行子模块({execute_child is not None})",
                "critical"
            ))
            return report
        
        # 检查2：管控子模块类型
        if control_child is not None:
            if control_child.module_type != ModuleType.CONTROL:
                report.add_result(CheckResult.failed_result(
                    "control_child_type_check",
                    f"管控子模块类型错误：期望CONTROL，实际{control_child.module_type}",
                    "error"
                ))
        
        # 检查3：执行子模块类型
        if execute_child is not None:
            if execute_child.module_type != ModuleType.EXECUTE:
                report.add_result(CheckResult.failed_result(
                    "execute_child_type_check",
                    f"执行子模块类型错误：期望EXECUTE，实际{execute_child.module_type}",
                    "error"
                ))
        
        # 如果所有检查都通过
        if report.overall_passed:
            report.add_result(CheckResult.passed_result(
                "twin_structure_check",
                "双子结构验证通过"
            ))
        
        return report
    
    def get_all_children(self) -> List["BaseModule"]:
        """
        获取所有子模块
        
        Returns:
            List[BaseModule]: 子模块列表
        """
        children = []
        if self._state.control_child:
            children.append(self._state.control_child)
        if self._state.execute_child:
            children.append(self._state.execute_child)
        return children
    
    # =====================================================================
    # 状态管理
    # =====================================================================
    
    def _set_state(self, new_state: ModuleState) -> None:
        """
        设置模块状态（内部方法）
        
        Args:
            new_state: 新状态
        """
        with self._lock:
            old_state = self._state.module_state
            self._state.module_state = new_state
            self._emit_event(ModuleEventType.STATE_CHANGED, {
                "old_state": old_state,
                "new_state": new_state,
            })
    
    def _check_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized and self._state.module_state in [
            ModuleState.READY,
            ModuleState.RUNNING,
            ModuleState.PAUSED,
        ]
    
    # =====================================================================
    # 事件系统
    # =====================================================================
    
    def add_event_listener(self, listener: callable) -> None:
        """添加事件监听器"""
        self._event_listeners.add(listener)
    
    def remove_event_listener(self, listener: callable) -> None:
        """移除事件监听器"""
        self._event_listeners.discard(listener)
    
    def _emit_event(self, event_type: ModuleEventType, data: Dict[str, Any] = None) -> None:
        """
        发射事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        event = ModuleEvent(
            event_type=event_type,
            module_id=self.module_id,
            data=data or {},
        )
        for listener in self._event_listeners:
            try:
                listener(event)
            except Exception:
                # 监听器异常不应影响主流程
                pass
    
    # =====================================================================
    # IModuleInit 接口实现
    # =====================================================================
    
    def module_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """
        模块初始化
        
        模板方法模式：
        1. 验证参数
        2. 执行前置初始化
        3. 执行具体初始化逻辑（子类实现）
        4. 执行后置初始化
        5. 返回结果
        
        Args:
            request: 初始化请求
            context: 初始化上下文
            
        Returns:
            InitResult: 初始化结果
        """
        with self._lock:
            # 检查状态
            if self._state.module_state != ModuleState.UNINITIALIZED:
                return InitResult.failure_result(
                    self.module_id,
                    "INIT_STATE_ERROR",
                    f"模块状态不正确，当前状态：{self._state.module_state}"
                )
            
            self._set_state(ModuleState.INITIALIZING)
            self._emit_event(ModuleEventType.INIT_STARTED)
            
            try:
                # 1. 验证参数
                validation_report = self.validate_init_params(request)
                if not validation_report.overall_passed:
                    self._set_state(ModuleState.ERROR)
                    self._emit_event(ModuleEventType.INIT_FAILED, {
                        "reason": "参数验证失败",
                        "report": validation_report.summary,
                    })
                    return InitResult.failure_result(
                        self.module_id,
                        "INIT_VALIDATION_FAILED",
                        validation_report.summary
                    )
                
                # 2. 保存参数
                self._state.module_param = request.module_param
                self._state.task_param = request.task_param
                self._state.parent_module_id = request.parent_module_id
                self._state.module_name = request.module_param.module_name
                # module_type 由子类在构造函数中设置，不在这里覆盖
                self._state.module_level = request.module_param.module_level
                
                # 3. 执行前置初始化
                self._before_init(request, context)
                
                # 4. 执行具体初始化逻辑（子类实现）
                init_result = self._do_init(request, context)
                
                if not init_result.success:
                    self._set_state(ModuleState.ERROR)
                    self._emit_event(ModuleEventType.INIT_FAILED, {
                        "error_code": init_result.error_code,
                        "error_detail": init_result.error_detail,
                    })
                    return init_result
                
                # 5. 执行后置初始化
                self._after_init(request, context)
                
                # 6. 标记初始化完成
                self._initialized = True
                self._set_state(ModuleState.READY)
                self._state.init_result = init_result
                self._emit_event(ModuleEventType.INIT_COMPLETED)
                
                return InitResult.success_result(
                    self.module_id,
                    f"模块 {self._state.module_name} 初始化成功"
                )
                
            except Exception as e:
                self._set_state(ModuleState.ERROR)
                self._emit_event(ModuleEventType.INIT_FAILED, {
                    "exception": str(e),
                })
                return InitResult.failure_result(
                    self.module_id,
                    "INIT_EXCEPTION",
                    str(e)
                )
    
    @abstractmethod
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """
        执行具体初始化逻辑（子类必须实现）
        
        Args:
            request: 初始化请求
            context: 初始化上下文
            
        Returns:
            InitResult: 初始化结果
        """
        pass
    
    def _before_init(self, request: InitRequest, context: InitContext) -> None:
        """
        前置初始化（子类可重写）
        
        Args:
            request: 初始化请求
            context: 初始化上下文
        """
        pass
    
    def _after_init(self, request: InitRequest, context: InitContext) -> None:
        """
        后置初始化（子类可重写）
        
        Args:
            request: 初始化请求
            context: 初始化上下文
        """
        pass
    
    def get_init_metadata(self) -> InterfaceMetadata:
        """获取初始化接口元数据"""
        if self._init_metadata is None:
            self._init_metadata = InterfaceMetadata(
                interface_name="IModuleInit",
                interface_version="1.0",
                description="模块初始化接口",
            )
        return self._init_metadata
    
    def get_init_capabilities(self) -> List[InterfaceCapability]:
        """获取初始化接口能力列表"""
        return [
            InterfaceCapability(
                capability_name="standard_init",
                is_required=True,
            ),
        ]
    
    def validate_init_params(self, request: InitRequest) -> ValidationReport:
        """
        验证初始化参数
        
        Args:
            request: 初始化请求
            
        Returns:
            ValidationReport: 验证报告
        """
        task_id = TaskID()
        report = ValidationReport(
            task_id=task_id,
            overall_passed=True,
        )
        
        # 验证模块ID
        if request.module_id is None:
            report.add_result(CheckResult.failed_result(
                "module_id_check",
                "模块ID不能为空",
                "error"
            ))
        
        # 验证模块参数
        if request.module_param is None:
            report.add_result(CheckResult.failed_result(
                "module_param_check",
                "模块参数不能为空",
                "error"
            ))
        
        if report.overall_passed:
            report.add_result(CheckResult.passed_result(
                "init_params_check",
                "初始化参数验证通过"
            ))
        
        return report
    
    # =====================================================================
    # IModuleRun 接口实现
    # =====================================================================
    
    def module_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """
        模块执行
        
        模板方法模式：
        1. 检查是否可以执行
        2. 执行前置处理
        3. 执行具体业务逻辑（子类实现）
        4. 执行后置处理
        5. 返回结果
        
        Args:
            request: 执行请求
            context: 执行上下文
            
        Returns:
            ModuleOutput: 模块输出
        """
        with self._lock:
            # 检查初始化状态
            if not self._check_initialized():
                return ModuleOutput.failure_output(
                    request.module_input.task_id,
                    "RUN_NOT_INITIALIZED",
                    "模块未初始化或状态不正确"
                )
            
            # 检查是否可以执行
            check_result = self.can_execute(request.module_input)
            if not check_result.passed:
                return ModuleOutput.failure_output(
                    request.module_input.task_id,
                    "RUN_CHECK_FAILED",
                    check_result.message
                )
            
            self._set_state(ModuleState.RUNNING)
            self._emit_event(ModuleEventType.RUN_STARTED)
            
            # 记录执行开始时间
            import time
            start_time = time.time()
            
            try:
                # 1. 执行前置处理
                self._before_run(request, context)
                
                # 2. 执行具体业务逻辑（子类实现）
                output = self._do_run(request, context)
                
                # 3. 执行后置处理
                self._after_run(request, context, output)
                
                # 4. 更新执行指标
                execution_time_ms = int((time.time() - start_time) * 1000)
                output.execution_time_ms = execution_time_ms
                self._state.execution_count += 1
                self._state.last_execution_time = datetime.now()
                
                # 5. 更新状态
                if output.success:
                    self._set_state(ModuleState.READY)
                    self._emit_event(ModuleEventType.RUN_COMPLETED, {
                        "execution_time_ms": execution_time_ms,
                    })
                else:
                    self._set_state(ModuleState.ERROR)
                    self._emit_event(ModuleEventType.RUN_FAILED, {
                        "error_code": output.error_code,
                        "error_detail": output.error_detail,
                    })
                
                return output
                
            except Exception as e:
                self._set_state(ModuleState.ERROR)
                self._emit_event(ModuleEventType.RUN_FAILED, {
                    "exception": str(e),
                })
                return ModuleOutput.failure_output(
                    request.module_input.task_id,
                    "RUN_EXCEPTION",
                    str(e)
                )
    
    @abstractmethod
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """
        执行具体业务逻辑（子类必须实现）
        
        Args:
            request: 执行请求
            context: 执行上下文
            
        Returns:
            ModuleOutput: 模块输出
        """
        pass
    
    def _before_run(self, request: ExecutionRequest, context: ExecutionContext) -> None:
        """
        前置执行处理（子类可重写）
        
        Args:
            request: 执行请求
            context: 执行上下文
        """
        pass
    
    def _after_run(self, request: ExecutionRequest, context: ExecutionContext, output: ModuleOutput) -> None:
        """
        后置执行处理（子类可重写）
        
        Args:
            request: 执行请求
            context: 执行上下文
            output: 执行输出
        """
        pass
    
    def get_run_metadata(self) -> InterfaceMetadata:
        """获取执行接口元数据"""
        if self._run_metadata is None:
            self._run_metadata = InterfaceMetadata(
                interface_name="IModuleRun",
                interface_version="1.0",
                description="模块执行接口",
            )
        return self._run_metadata
    
    def get_run_capabilities(self) -> List[InterfaceCapability]:
        """获取执行接口能力列表"""
        return [
            InterfaceCapability(
                capability_name="standard_run",
                is_required=True,
            ),
        ]
    
    def can_execute(self, module_input: ModuleInput) -> CheckResult:
        """
        检查是否可以执行
        
        Args:
            module_input: 模块输入
            
        Returns:
            CheckResult: 检查结果
        """
        # 默认实现：总是可以执行
        return CheckResult.passed_result(
            "can_execute_check",
            "可以执行"
        )
    
    def get_execution_metrics(self) -> ExecutionMetrics:
        """获取执行指标"""
        return self._state.execution_metrics
    
    # =====================================================================
    # IModuleCheck 接口实现
    # =====================================================================
    
    def module_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """
        模块校验
        
        模板方法模式：
        1. 执行前置校验
        2. 执行具体校验逻辑（子类实现）
        3. 执行后置校验
        4. 返回结果
        
        Args:
            request: 校验请求
            context: 校验上下文
            
        Returns:
            CheckResult: 校验结果
        """
        self._emit_event(ModuleEventType.CHECK_STARTED)
        
        try:
            # 1. 执行前置校验
            self._before_check(request, context)
            
            # 2. 执行具体校验逻辑（子类实现）
            result = self._do_check(request, context)
            
            # 3. 执行后置校验
            self._after_check(request, context, result)
            
            self._emit_event(ModuleEventType.CHECK_COMPLETED, {
                "passed": result.passed,
                "check_type": result.check_type,
            })
            
            return result
            
        except Exception as e:
            return CheckResult.failed_result(
                request.check_type,
                f"校验异常: {str(e)}",
                "error"
            )
    
    @abstractmethod
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """
        执行具体校验逻辑（子类必须实现）
        
        Args:
            request: 校验请求
            context: 校验上下文
            
        Returns:
            CheckResult: 校验结果
        """
        pass
    
    def _before_check(self, request: ValidationRequest, context: ValidationContext) -> None:
        """
        前置校验处理（子类可重写）
        
        Args:
            request: 校验请求
            context: 校验上下文
        """
        pass
    
    def _after_check(self, request: ValidationRequest, context: ValidationContext, result: CheckResult) -> None:
        """
        后置校验处理（子类可重写）
        
        Args:
            request: 校验请求
            context: 校验上下文
            result: 校验结果
        """
        pass
    
    def get_check_metadata(self) -> InterfaceMetadata:
        """获取校验接口元数据"""
        if self._check_metadata is None:
            self._check_metadata = InterfaceMetadata(
                interface_name="IModuleCheck",
                interface_version="1.0",
                description="模块校验接口",
            )
        return self._check_metadata
    
    def get_check_capabilities(self) -> List[InterfaceCapability]:
        """获取校验接口能力列表"""
        return [
            InterfaceCapability(
                capability_name="standard_check",
                is_required=True,
            ),
        ]
    
    def get_supported_check_types(self) -> List[str]:
        """
        获取支持的校验类型列表
        
        Returns:
            List[str]: 校验类型列表
        """
        # 默认实现：返回空列表，子类应重写
        return []
    
    def validate_and_fix(self, request: ValidationRequest, context: ValidationContext) -> tuple[CheckResult, Optional[Any]]:
        """
        校验并尝试修正
        
        默认实现：只执行校验，不做修正
        子类可重写以实现自动修正功能
        
        Args:
            request: 校验请求
            context: 校验上下文
            
        Returns:
            tuple[CheckResult, Optional[Any]]: (校验结果, 修正后的数据)
        """
        result = self.module_check(request, context)
        return result, None
    
    # =====================================================================
    # IModuleSnapshot 接口实现
    # =====================================================================
    
    def create_snapshot(self, request: SnapshotRequest, context: SnapshotContext) -> SnapshotData:
        """
        创建快照
        
        模板方法模式：
        1. 执行前置快照处理
        2. 收集模块状态
        3. 执行具体快照逻辑（子类实现）
        4. 执行后置快照处理
        5. 返回快照数据
        
        Args:
            request: 快照请求
            context: 快照上下文
            
        Returns:
            SnapshotData: 快照数据
        """
        self._emit_event(ModuleEventType.SNAPSHOT_CREATED)
        
        # 1. 执行前置快照处理
        self._before_snapshot(request, context)
        
        # 2. 创建基础快照数据
        snapshot = SnapshotData(
            module_id=self.module_id,
            snapshot_version=request.snapshot_type,
        )
        
        # 3. 保存模块基础状态
        snapshot.set_state("module_name", self._state.module_name)
        snapshot.set_state("module_type", self._state.module_type.name)
        snapshot.set_state("module_level", self._state.module_level.name)
        snapshot.set_state("module_state", self._state.module_state.name)
        snapshot.set_state("execution_count", self._state.execution_count)
        snapshot.set_state("initialized", self._initialized)
        
        # 4. 保存内部数据
        snapshot.set_state("internal_data", self._state.get_all_data())
        
        # 5. 执行具体快照逻辑（子类实现）
        self._do_snapshot(request, context, snapshot)
        
        # 6. 执行后置快照处理
        self._after_snapshot(request, context, snapshot)
        
        # 7. 保存元数据
        if request.include_metadata:
            snapshot.metadata["created_at"] = datetime.now().isoformat()
            snapshot.metadata["snapshot_type"] = request.snapshot_type
        
        return snapshot
    
    @abstractmethod
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """
        执行具体快照逻辑（子类必须实现）
        
        Args:
            request: 快照请求
            context: 快照上下文
            snapshot: 快照数据（已包含基础状态）
        """
        pass
    
    def _before_snapshot(self, request: SnapshotRequest, context: SnapshotContext) -> None:
        """
        前置快照处理（子类可重写）
        
        Args:
            request: 快照请求
            context: 快照上下文
        """
        pass
    
    def _after_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """
        后置快照处理（子类可重写）
        
        Args:
            request: 快照请求
            context: 快照上下文
            snapshot: 快照数据
        """
        pass
    
    def restore_from_snapshot(self, request: RestoreRequest) -> InitResult:
        """
        从快照恢复
        
        Args:
            request: 恢复请求
            
        Returns:
            InitResult: 恢复结果
        """
        with self._lock:
            try:
                # 1. 验证快照
                if request.validate_before_restore:
                    check_result = self.validate_snapshot(request.snapshot_data)
                    if not check_result.passed:
                        return InitResult.failure_result(
                            self.module_id,
                            "SNAPSHOT_VALIDATION_FAILED",
                            check_result.message
                        )
                
                # 2. 恢复基础状态
                snapshot = request.snapshot_data
                self._state.module_name = snapshot.get_state("module_name", "")
                self._state.module_type = ModuleType[snapshot.get_state("module_type", "CONTROL")]
                self._state.module_level = ModuleLevel[snapshot.get_state("module_level", "LEVEL1")]
                self._state.module_state = ModuleState[snapshot.get_state("module_state", "UNINITIALIZED")]
                self._state.execution_count = snapshot.get_state("execution_count", 0)
                self._initialized = snapshot.get_state("initialized", False)
                
                # 3. 恢复内部数据
                internal_data = snapshot.get_state("internal_data", {})
                self._state.restore_data(internal_data)
                
                # 4. 执行具体恢复逻辑（子类实现）
                self._do_restore(request)
                
                self._emit_event(ModuleEventType.SNAPSHOT_RESTORED)
                
                return InitResult.success_result(
                    self.module_id,
                    "从快照恢复成功"
                )
                
            except Exception as e:
                return InitResult.failure_result(
                    self.module_id,
                    "RESTORE_EXCEPTION",
                    str(e)
                )
    
    def _do_restore(self, request: RestoreRequest) -> None:
        """
        执行具体恢复逻辑（子类可重写）
        
        Args:
            request: 恢复请求
        """
        pass
    
    def get_snapshot_metadata(self) -> InterfaceMetadata:
        """获取快照接口元数据"""
        if self._snapshot_metadata is None:
            self._snapshot_metadata = InterfaceMetadata(
                interface_name="IModuleSnapshot",
                interface_version="1.0",
                description="模块快照接口",
            )
        return self._snapshot_metadata
    
    def get_snapshot_capabilities(self) -> List[InterfaceCapability]:
        """获取快照接口能力列表"""
        return [
            InterfaceCapability(
                capability_name="standard_snapshot",
                is_required=True,
            ),
            InterfaceCapability(
                capability_name="restore_from_snapshot",
                is_required=True,
            ),
        ]
    
    def validate_snapshot(self, snapshot_data: SnapshotData) -> CheckResult:
        """
        验证快照有效性
        
        Args:
            snapshot_data: 快照数据
            
        Returns:
            CheckResult: 验证结果
        """
        # 验证模块ID匹配
        if snapshot_data.module_id != self.module_id:
            return CheckResult.failed_result(
                "snapshot_validation",
                f"快照模块ID不匹配：期望{self.module_id}，实际{snapshot_data.module_id}",
                "error"
            )
        
        # 验证快照版本
        if not snapshot_data.snapshot_version:
            return CheckResult.failed_result(
                "snapshot_validation",
                "快照版本不能为空",
                "error"
            )
        
        return CheckResult.passed_result(
            "snapshot_validation",
            "快照验证通过"
        )
    
    def get_snapshot_info(self, snapshot_data: SnapshotData) -> SnapshotInfo:
        """
        获取快照信息
        
        Args:
            snapshot_data: 快照数据
            
        Returns:
            SnapshotInfo: 快照信息
        """
        import json
        
        # 计算快照大小（近似值）
        snapshot_json = json.dumps(snapshot_data.state_data, default=str)
        size_bytes = len(snapshot_json.encode('utf-8'))
        
        return SnapshotInfo(
            snapshot_id=snapshot_data.snapshot_id,
            module_id=snapshot_data.module_id,
            created_at=snapshot_data.created_at,
            snapshot_size_bytes=size_bytes,
            snapshot_version=snapshot_data.snapshot_version,
            checksum="",  # 可由子类计算
            metadata=snapshot_data.metadata,
        )
    
    # =====================================================================
    # 工具方法
    # =====================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典表示
        
        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "module_id": str(self.module_id),
            "module_name": self.module_name,
            "module_type": self.module_type.name,
            "module_level": self.module_level.name,
            "module_state": self.module_state.name,
            "parent_module_id": str(self.parent_module_id) if self.parent_module_id else None,
            "has_control_child": self._state.control_child is not None,
            "has_execute_child": self._state.execute_child is not None,
            "execution_count": self._state.execution_count,
            "initialized": self._initialized,
        }
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"{self.__class__.__name__}(id={self.module_id}, type={self.module_type.name}, state={self.module_state.name})"


# =============================================================================
# 3. 管控模块基类 (Control Module Base)
# =============================================================================

class ControlModuleBase(BaseModule):
    """
    管控模块基类
    
    所有管控类模块的基类，module_type固定为CONTROL
    """
    
    def __init__(self, module_id: Optional[ModuleID] = None):
        super().__init__(module_id)
        self._state.module_type = ModuleType.CONTROL


# =============================================================================
# 4. 执行模块基类 (Execute Module Base)
# =============================================================================

class ExecuteModuleBase(BaseModule):
    """
    执行模块基类
    
    所有执行类模块的基类，module_type固定为EXECUTE
    """
    
    def __init__(self, module_id: Optional[ModuleID] = None):
        super().__init__(module_id)
        self._state.module_type = ModuleType.EXECUTE


# =============================================================================
# 模块导出列表
# =============================================================================

__all__ = [
    # 私有状态容器
    "ModulePrivateState",
    
    # 模块基类
    "BaseModule",
    "ControlModuleBase",
    "ExecuteModuleBase",
]
