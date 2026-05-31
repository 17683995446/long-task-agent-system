"""
阶段19：根模块双子结构绑定
Root Module Twin Structure Binding

职责定义：
- 创建根模块并绑定一级双子子模块
- 实现根模块与一级模块的关联
- 提供模块树构建入口
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from core.base_module import BaseModule, ControlModuleBase, ExecuteModuleBase
from core.twin_container import TwinContainer, TwinContainerBuilder, TwinSlot
from core_types.core_types import (
    ModuleID, TaskID, ModuleType, ModuleState, ModuleLevel,
    InitResult, ModuleOutput, CheckResult, SnapshotData,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)
from utils.logger import Logger


class RootModule(ControlModuleBase):
    """
    根模块
    
    职责：
    1. 作为整个模块树的根节点
    2. 管理一级双子子模块（一级管控和一级执行）
    3. 提供系统级入口点
    4. 全局状态管理
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.ROOT
        self._state.module_name = "RootModule"
        self._logger = Logger(f"Root_{self.module_id}")
        self._system_config: Dict[str, Any] = {}
        self._initialized_at: Optional[datetime] = None
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """根模块初始化"""
        try:
            self._logger.info("根模块初始化开始")
            
            # 1. 加载系统配置
            self._load_system_config(request)
            
            # 2. 初始化一级子模块（如果存在）
            self._init_level1_children(request, context)
            
            self._initialized_at = datetime.now()
            
            self._logger.info("根模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="根模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"根模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="ROOT_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_system_config(self, request: InitRequest) -> None:
        """加载系统配置"""
        self._system_config = {
            "system_name": "LongTaskAgent",
            "version": "1.0.0",
            "max_module_levels": 4,
            "enable_logging": True,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("system_config", {})
            self._system_config.update(custom_config)
        self._logger.info(f"系统配置加载完成: {self._system_config}")
    
    def _init_level1_children(self, request: InitRequest, context: InitContext) -> None:
        """初始化一级子模块"""
        control_child = self.get_control_child()
        execute_child = self.get_execute_child()
        
        if control_child:
            self._logger.info(f"初始化一级管控模块: {control_child.module_id}")
            control_child.module_init(request, context)
        
        if execute_child:
            self._logger.info(f"初始化一级执行模块: {execute_child.module_id}")
            execute_child.module_init(request, context)
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """根模块执行"""
        self._logger.info("根模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 1. 检查一级子模块
            control_child = self.get_control_child()
            execute_child = self.get_execute_child()
            
            if not control_child or not execute_child:
                return ModuleOutput.failure_output(
                    task_id=task_id,
                    error_code="ROOT_MISSING_CHILDREN",
                    error_detail="根模块缺少一级子模块"
                )
            
            # 2. 先执行管控子模块（治理）
            control_result = control_child.module_run(request, context)
            if not control_result.success:
                return ModuleOutput.failure_output(
                    task_id=task_id,
                    error_code="ROOT_CONTROL_FAILED",
                    error_detail=f"一级管控模块执行失败: {control_result.error_detail}"
                )
            
            # 3. 再执行执行子模块
            execute_result = execute_child.module_run(request, context)
            if not execute_result.success:
                return ModuleOutput.failure_output(
                    task_id=task_id,
                    error_code="ROOT_EXECUTE_FAILED",
                    error_detail=f"一级执行模块执行失败: {execute_result.error_detail}"
                )
            
            self._logger.info("根模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "control_result": control_result.data,
                    "execute_result": execute_result.data,
                },
                message="根模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"根模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="ROOT_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """根模块校验"""
        self._logger.info("根模块校验开始")
        
        checks = []
        
        # 1. 校验系统配置
        if self._validate_system_config():
            checks.append("system_config_valid")
        
        # 2. 校验双子结构
        twin_report = self.validate_twin_structure()
        if twin_report.overall_passed:
            checks.append("twin_structure_valid")
        
        # 3. 校验一级子模块（只要存在即可，不要求特定层级）
        if self._validate_level1_children():
            checks.append("level1_children_valid")
        
        all_passed = len(checks) == 3
        
        self._logger.info(f"根模块校验完成: {checks}")
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="root_validation",
                message="根模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="root_validation",
                message=f"校验失败: {checks}, twin_report: {twin_report.summary if not twin_report.overall_passed else 'OK'}",
                severity="error"
            )
    
    def _validate_system_config(self) -> bool:
        """校验系统配置"""
        required_keys = ["system_name", "version"]
        return all(key in self._system_config for key in required_keys)
    
    def _validate_level1_children(self) -> bool:
        """校验一级子模块"""
        control_child = self.get_control_child()
        execute_child = self.get_execute_child()
        
        # 只要两个子模块都存在即可，不强制要求module_level（子模块可能还未初始化）
        return control_child is not None and execute_child is not None
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("system_config", self._system_config)
        snapshot.set_state("initialized_at", self._initialized_at.isoformat() if self._initialized_at else None)
        snapshot.metadata["module_type"] = "RootModule"
        snapshot.metadata["version"] = "1.0"
    
    def get_system_config(self) -> Dict[str, Any]:
        """获取系统配置"""
        return self._system_config.copy()


class RootModuleBuilder:
    """
    根模块构建器
    
    提供流式API构建根模块及其一级子模块：
    
    使用方式：
        root = (RootModuleBuilder()
            .set_level1_control(Level1ControlModule())
            .set_level1_execute(Level1ExecuteModule())
            .build())
    """
    
    def __init__(self):
        self._root_module: Optional[RootModule] = None
        self._level1_control: Optional[ControlModuleBase] = None
        self._level1_execute: Optional[ExecuteModuleBase] = None
    
    def set_root_module(self, root_module: RootModule) -> "RootModuleBuilder":
        """设置根模块"""
        self._root_module = root_module
        return self
    
    def set_level1_control(self, control_module: ControlModuleBase) -> "RootModuleBuilder":
        """设置一级管控模块"""
        self._level1_control = control_module
        return self
    
    def set_level1_execute(self, execute_module: ExecuteModuleBase) -> "RootModuleBuilder":
        """设置一级执行模块"""
        self._level1_execute = execute_module
        return self
    
    def build(self) -> RootModule:
        """构建根模块"""
        # 1. 创建根模块（如果未提供）
        if self._root_module is None:
            self._root_module = RootModule()
        
        # 2. 检查一级子模块
        if self._level1_control is None:
            raise ValueError("缺少一级管控模块")
        if self._level1_execute is None:
            raise ValueError("缺少一级执行模块")
        
        # 3. 绑定一级子模块
        self._root_module.set_control_child(self._level1_control)
        self._root_module.set_execute_child(self._level1_execute)
        
        return self._root_module


class TwinStructureBinder:
    """
    双子结构绑定器
    
    负责在模块之间建立双子结构关系
    """
    
    @staticmethod
    def bind_level1_to_root(
        root_module: RootModule,
        level1_control: ControlModuleBase,
        level1_execute: ExecuteModuleBase
    ) -> None:
        """
        将一级模块绑定到根模块
        
        Args:
            root_module: 根模块
            level1_control: 一级管控模块
            level1_execute: 一级执行模块
        """
        root_module.set_control_child(level1_control)
        root_module.set_execute_child(level1_execute)
    
    @staticmethod
    def validate_binding(parent_module: BaseModule) -> CheckResult:
        """
        验证绑定关系
        
        Args:
            parent_module: 父模块
            
        Returns:
            CheckResult: 验证结果
        """
        report = parent_module.validate_twin_structure()
        
        if report.overall_passed:
            return CheckResult.passed_result(
                check_type="binding_validation",
                message="双子结构绑定验证通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="binding_validation",
                message=f"绑定验证失败: {report.summary}",
                severity="error"
            )


__all__ = [
    "RootModule",
    "RootModuleBuilder",
    "TwinStructureBinder",
]
