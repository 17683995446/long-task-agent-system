"""
超长任务Agent树形双生子模块化执行系统 - 双子模块容器实现
Twin Container Implementation for Long-Task Agent Twin-Module Execution System

阶段4：双子模块容器实现
遵循原则：图难于其易，为大于其细
核心约束：直接子模块数量恒等于2，全局零特例
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from core_types.core_types import (
    ModuleID, TaskID,
    ModuleType, ModuleLevel, ModuleState,
    CheckResult, ValidationReport,
)

# 前向引用，避免循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.base_module import BaseModule


# =============================================================================
# 1. 双子容器异常类型 (Twin Container Exception Types)
# =============================================================================

class TwinContainerError(Exception):
    """双子容器基础异常"""
    pass


class TwinStructureViolationError(TwinContainerError):
    """双子结构违反异常"""
    pass


class ChildTypeError(TwinContainerError):
    """子模块类型错误异常"""
    pass


class DuplicateChildError(TwinContainerError):
    """重复子模块异常"""
    pass


class ChildNotFoundError(TwinContainerError):
    """子模块未找到异常"""
    pass


# =============================================================================
# 2. 双子槽位枚举 (Twin Slot Enumeration)
# =============================================================================

class TwinSlot(Enum):
    """
    双子槽位枚举
    定义双子结构中两个固定槽位
    """
    CONTROL = auto()   # 左节点：管控类模块
    EXECUTE = auto()   # 右节点：执行类模块


# =============================================================================
# 3. 子模块注册记录 (Child Registration Record)
# =============================================================================

@dataclass
class ChildRecord:
    """
    子模块注册记录
    记录子模块的注册信息
    """
    module: "BaseModule"
    slot: TwinSlot
    registered_at: datetime = field(default_factory=datetime.now)
    
    @property
    def module_id(self) -> ModuleID:
        """获取模块ID"""
        return self.module.module_id
    
    @property
    def module_type(self) -> ModuleType:
        """获取模块类型"""
        return self.module.module_type
    
    @property
    def module_name(self) -> str:
        """获取模块名称"""
        return self.module.module_name


# =============================================================================
# 4. 双子模块容器 (Twin Module Container)
# =============================================================================

class TwinContainer:
    """
    双子模块容器
    
    严格管理模块的双子结构，确保：
    1. 直接子模块数量恒等于2
    2. 左节点为管控类模块（CONTROL）
    3. 右节点为执行类模块（EXECUTE）
    4. 禁止添加第3个子模块
    5. 禁止跨槽位类型混淆
    
    使用方式：
        container = TwinContainer(parent_id)
        container.add_control_child(control_module)
        container.add_execute_child(execute_module)
    """
    
    def __init__(self, parent_id: ModuleID):
        """
        初始化双子容器
        
        Args:
            parent_id: 父模块ID
        """
        self._parent_id = parent_id
        self._children: Dict[TwinSlot, ChildRecord] = {}
        self._sealed = False  # 是否已封印（封印后不可修改）
    
    # =====================================================================
    # 属性访问
    # =====================================================================
    
    @property
    def parent_id(self) -> ModuleID:
        """父模块ID"""
        return self._parent_id
    
    @property
    def child_count(self) -> int:
        """当前子模块数量"""
        return len(self._children)
    
    @property
    def is_complete(self) -> bool:
        """双子结构是否完整（2个子模块）"""
        return len(self._children) == 2
    
    @property
    def is_empty(self) -> bool:
        """是否没有子模块"""
        return len(self._children) == 0
    
    @property
    def is_sealed(self) -> bool:
        """是否已封印"""
        return self._sealed
    
    @property
    def has_control_child(self) -> bool:
        """是否有管控子模块"""
        return TwinSlot.CONTROL in self._children
    
    @property
    def has_execute_child(self) -> bool:
        """是否有执行子模块"""
        return TwinSlot.EXECUTE in self._children
    
    # =====================================================================
    # 子模块添加（核心方法）
    # =====================================================================
    
    def add_control_child(self, child: "BaseModule") -> None:
        """
        添加管控子模块（左节点）
        
        Args:
            child: 管控类模块
            
        Raises:
            TwinContainerError: 容器已封印
            ChildTypeError: 子模块类型不是CONTROL
            DuplicateChildError: 已存在管控子模块
        """
        self._validate_before_add(child, TwinSlot.CONTROL)
        self._children[TwinSlot.CONTROL] = ChildRecord(
            module=child,
            slot=TwinSlot.CONTROL,
        )
        child._state.parent_module_id = self._parent_id
    
    def add_execute_child(self, child: "BaseModule") -> None:
        """
        添加执行子模块（右节点）
        
        Args:
            child: 执行类模块
            
        Raises:
            TwinContainerError: 容器已封印
            ChildTypeError: 子模块类型不是EXECUTE
            DuplicateChildError: 已存在执行子模块
        """
        self._validate_before_add(child, TwinSlot.EXECUTE)
        self._children[TwinSlot.EXECUTE] = ChildRecord(
            module=child,
            slot=TwinSlot.EXECUTE,
        )
        child._state.parent_module_id = self._parent_id
    
    def _validate_before_add(self, child: "BaseModule", slot: TwinSlot) -> None:
        """
        添加子模块前的校验
        
        Args:
            child: 待添加的子模块
            slot: 目标槽位
            
        Raises:
            TwinContainerError: 容器已封印
            ChildTypeError: 子模块类型不匹配
            DuplicateChildError: 槽位已被占用
        """
        # 检查1：容器是否已封印
        if self._sealed:
            raise TwinContainerError(
                f"容器已封印，无法添加子模块到槽位 {slot.name}"
            )
        
        # 检查2：子模块类型是否匹配
        expected_type = ModuleType.CONTROL if slot == TwinSlot.CONTROL else ModuleType.EXECUTE
        if child.module_type != expected_type:
            raise ChildTypeError(
                f"槽位 {slot.name} 期望模块类型为 {expected_type.name}，"
                f"但传入的模块类型为 {child.module_type.name}"
            )
        
        # 检查3：槽位是否已被占用
        if slot in self._children:
            existing = self._children[slot]
            raise DuplicateChildError(
                f"槽位 {slot.name} 已被模块 {existing.module_id} 占用，"
                f"无法添加模块 {child.module_id}"
            )
        
        # 检查4：是否已存在相同模块
        for existing_record in self._children.values():
            if existing_record.module_id == child.module_id:
                raise DuplicateChildError(
                    f"模块 {child.module_id} 已存在于槽位 {existing_record.slot.name}"
                )
    
    # =====================================================================
    # 子模块获取
    # =====================================================================
    
    def get_control_child(self) -> Optional["BaseModule"]:
        """
        获取管控子模块（左节点）
        
        Returns:
            Optional[BaseModule]: 管控子模块，不存在则返回None
        """
        record = self._children.get(TwinSlot.CONTROL)
        return record.module if record else None
    
    def get_execute_child(self) -> Optional["BaseModule"]:
        """
        获取执行子模块（右节点）
        
        Returns:
            Optional[BaseModule]: 执行子模块，不存在则返回None
        """
        record = self._children.get(TwinSlot.EXECUTE)
        return record.module if record else None
    
    def get_child(self, slot: TwinSlot) -> Optional["BaseModule"]:
        """
        根据槽位获取子模块
        
        Args:
            slot: 槽位
            
        Returns:
            Optional[BaseModule]: 子模块，不存在则返回None
        """
        record = self._children.get(slot)
        return record.module if record else None
    
    def get_child_record(self, slot: TwinSlot) -> Optional[ChildRecord]:
        """
        根据槽位获取子模块注册记录
        
        Args:
            slot: 槽位
            
        Returns:
            Optional[ChildRecord]: 注册记录，不存在则返回None
        """
        return self._children.get(slot)
    
    def get_all_children(self) -> List["BaseModule"]:
        """
        获取所有子模块（按槽位顺序：CONTROL, EXECUTE）
        
        Returns:
            List[BaseModule]: 子模块列表
        """
        children = []
        if TwinSlot.CONTROL in self._children:
            children.append(self._children[TwinSlot.CONTROL].module)
        if TwinSlot.EXECUTE in self._children:
            children.append(self._children[TwinSlot.EXECUTE].module)
        return children
    
    def get_all_records(self) -> List[ChildRecord]:
        """
        获取所有子模块注册记录
        
        Returns:
            List[ChildRecord]: 注册记录列表
        """
        return list(self._children.values())
    
    # =====================================================================
    # 子模块移除
    # =====================================================================
    
    def remove_control_child(self) -> "BaseModule":
        """
        移除管控子模块
        
        Returns:
            BaseModule: 被移除的子模块
            
        Raises:
            TwinContainerError: 容器已封印
            ChildNotFoundError: 管控子模块不存在
        """
        return self._remove_child(TwinSlot.CONTROL)
    
    def remove_execute_child(self) -> "BaseModule":
        """
        移除执行子模块
        
        Returns:
            BaseModule: 被移除的子模块
            
        Raises:
            TwinContainerError: 容器已封印
            ChildNotFoundError: 执行子模块不存在
        """
        return self._remove_child(TwinSlot.EXECUTE)
    
    def _remove_child(self, slot: TwinSlot) -> "BaseModule":
        """
        移除指定槽位的子模块
        
        Args:
            slot: 槽位
            
        Returns:
            BaseModule: 被移除的子模块
        """
        if self._sealed:
            raise TwinContainerError(f"容器已封印，无法移除槽位 {slot.name} 的子模块")
        
        record = self._children.pop(slot, None)
        if record is None:
            raise ChildNotFoundError(f"槽位 {slot.name} 没有子模块")
        
        # 清除父模块引用
        record.module._state.parent_module_id = None
        return record.module
    
    def clear_children(self) -> None:
        """
        清空所有子模块
        
        Raises:
            TwinContainerError: 容器已封印
        """
        if self._sealed:
            raise TwinContainerError("容器已封印，无法清空子模块")
        
        for record in self._children.values():
            record.module._state.parent_module_id = None
        self._children.clear()
    
    # =====================================================================
    # 容器封印
    # =====================================================================
    
    def seal(self) -> None:
        """
        封印容器
        
        封印后：
        - 不可添加子模块
        - 不可移除子模块
        - 不可清空子模块
        
        Raises:
            TwinStructureViolationError: 双子结构不完整时尝试封印
        """
        if not self.is_complete:
            raise TwinStructureViolationError(
                f"双子结构不完整（当前 {self.child_count}/2），无法封印。"
                f"管控子模块: {'存在' if self.has_control_child else '缺失'}，"
                f"执行子模块: {'存在' if self.has_execute_child else '缺失'}"
            )
        self._sealed = True
    
    def unseal(self) -> None:
        """解封容器"""
        self._sealed = False
    
    # =====================================================================
    # 结构校验
    # =====================================================================
    
    def validate_structure(self) -> ValidationReport:
        """
        验证双子结构
        
        检查项：
        1. 子模块数量是否为2
        2. 管控子模块类型是否正确
        3. 执行子模块类型是否正确
        4. 子模块父引用是否正确
        5. 子模块是否有重复
        
        Returns:
            ValidationReport: 验证报告
        """
        task_id = TaskID()
        report = ValidationReport(
            task_id=task_id,
            overall_passed=True,
        )
        
        # 检查1：子模块数量
        if self.child_count != 2:
            report.add_result(CheckResult.failed_result(
                "child_count_check",
                f"子模块数量不正确：期望2，实际{self.child_count}",
                "critical"
            ))
            return report
        
        report.add_result(CheckResult.passed_result(
            "child_count_check",
            "子模块数量正确（2个）"
        ))
        
        # 检查2：管控子模块类型
        control_record = self._children.get(TwinSlot.CONTROL)
        if control_record:
            if control_record.module_type != ModuleType.CONTROL:
                report.add_result(CheckResult.failed_result(
                    "control_type_check",
                    f"管控子模块类型错误：期望CONTROL，实际{control_record.module_type.name}",
                    "error"
                ))
            else:
                report.add_result(CheckResult.passed_result(
                    "control_type_check",
                    "管控子模块类型正确"
                ))
        
        # 检查3：执行子模块类型
        execute_record = self._children.get(TwinSlot.EXECUTE)
        if execute_record:
            if execute_record.module_type != ModuleType.EXECUTE:
                report.add_result(CheckResult.failed_result(
                    "execute_type_check",
                    f"执行子模块类型错误：期望EXECUTE，实际{execute_record.module_type.name}",
                    "error"
                ))
            else:
                report.add_result(CheckResult.passed_result(
                    "execute_type_check",
                    "执行子模块类型正确"
                ))
        
        # 检查4：子模块父引用
        for record in self._children.values():
            if record.module.parent_module_id != self._parent_id:
                report.add_result(CheckResult.failed_result(
                    "parent_reference_check",
                    f"子模块 {record.module_id} 的父引用不正确："
                    f"期望 {self._parent_id}，实际 {record.module.parent_module_id}",
                    "warning"
                ))
        
        if report.overall_passed:
            report.add_result(CheckResult.passed_result(
                "twin_structure_check",
                "双子结构验证通过"
            ))
        
        return report
    
    # =====================================================================
    # 查询方法
    # =====================================================================
    
    def contains(self, module_id: ModuleID) -> bool:
        """
        检查是否包含指定模块
        
        Args:
            module_id: 模块ID
            
        Returns:
            bool: 是否包含
        """
        for record in self._children.values():
            if record.module_id == module_id:
                return True
        return False
    
    def find_slot(self, module_id: ModuleID) -> Optional[TwinSlot]:
        """
        查找模块所在的槽位
        
        Args:
            module_id: 模块ID
            
        Returns:
            Optional[TwinSlot]: 槽位，未找到则返回None
        """
        for slot, record in self._children.items():
            if record.module_id == module_id:
                return slot
        return None
    
    # =====================================================================
    # 树形遍历辅助
    # =====================================================================
    
    def get_structure_summary(self, indent: int = 0) -> str:
        """
        获取结构摘要（用于日志和调试）
        
        Args:
            indent: 缩进级别
            
        Returns:
            str: 结构摘要字符串
        """
        prefix = "  " * indent
        lines = [f"{prefix}TwinContainer(parent={self._parent_id}):"]
        
        control_record = self._children.get(TwinSlot.CONTROL)
        if control_record:
            lines.append(
                f"{prefix}  [左节点/CONTROL] {control_record.module_name} "
                f"(id={control_record.module_id})"
            )
        else:
            lines.append(f"{prefix}  [左节点/CONTROL] <空>")
        
        execute_record = self._children.get(TwinSlot.EXECUTE)
        if execute_record:
            lines.append(
                f"{prefix}  [右节点/EXECUTE] {execute_record.module_name} "
                f"(id={execute_record.module_id})"
            )
        else:
            lines.append(f"{prefix}  [右节点/EXECUTE] <空>")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典表示
        
        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "parent_id": str(self._parent_id),
            "child_count": self.child_count,
            "is_complete": self.is_complete,
            "is_sealed": self._sealed,
            "control_child": {
                "module_id": str(self._children[TwinSlot.CONTROL].module_id),
                "module_name": self._children[TwinSlot.CONTROL].module_name,
            } if TwinSlot.CONTROL in self._children else None,
            "execute_child": {
                "module_id": str(self._children[TwinSlot.EXECUTE].module_id),
                "module_name": self._children[TwinSlot.EXECUTE].module_name,
            } if TwinSlot.EXECUTE in self._children else None,
        }
    
    def __repr__(self) -> str:
        return (
            f"TwinContainer(parent={self._parent_id}, "
            f"children={self.child_count}/2, "
            f"sealed={self._sealed})"
        )
    
    def __len__(self) -> int:
        return self.child_count
    
    def __iter__(self):
        """迭代子模块（按槽位顺序）"""
        return iter(self.get_all_children())
    
    def __contains__(self, module_id: ModuleID) -> bool:
        return self.contains(module_id)


# =============================================================================
# 5. 双子容器构建器 (Twin Container Builder)
# =============================================================================

class TwinContainerBuilder:
    """
    双子容器构建器
    
    提供流式API构建双子容器：
    
    使用方式：
        container = (TwinContainerBuilder(parent_id)
            .set_control_child(control_module)
            .set_execute_child(execute_module)
            .build())
    """
    
    def __init__(self, parent_id: ModuleID):
        """
        初始化构建器
        
        Args:
            parent_id: 父模块ID
        """
        self._parent_id = parent_id
        self._control_child: Optional["BaseModule"] = None
        self._execute_child: Optional["BaseModule"] = None
        self._auto_seal: bool = True
    
    def set_control_child(self, child: "BaseModule") -> "TwinContainerBuilder":
        """
        设置管控子模块
        
        Args:
            child: 管控类模块
            
        Returns:
            TwinContainerBuilder: 自身（支持链式调用）
        """
        if child.module_type != ModuleType.CONTROL:
            raise ChildTypeError(
                f"管控子模块必须是CONTROL类型，但传入的是{child.module_type.name}"
            )
        self._control_child = child
        return self
    
    def set_execute_child(self, child: "BaseModule") -> "TwinContainerBuilder":
        """
        设置执行子模块
        
        Args:
            child: 执行类模块
            
        Returns:
            TwinContainerBuilder: 自身（支持链式调用）
        """
        if child.module_type != ModuleType.EXECUTE:
            raise ChildTypeError(
                f"执行子模块必须是EXECUTE类型，但传入的是{child.module_type.name}"
            )
        self._execute_child = child
        return self
    
    def auto_seal(self, enabled: bool = True) -> "TwinContainerBuilder":
        """
        设置是否自动封印
        
        Args:
            enabled: 是否启用自动封印
            
        Returns:
            TwinContainerBuilder: 自身（支持链式调用）
        """
        self._auto_seal = enabled
        return self
    
    def build(self) -> TwinContainer:
        """
        构建双子容器
        
        Returns:
            TwinContainer: 构建完成的双子容器
            
        Raises:
            TwinStructureViolationError: 双子结构不完整
        """
        if self._control_child is None or self._execute_child is None:
            missing = []
            if self._control_child is None:
                missing.append("管控子模块")
            if self._execute_child is None:
                missing.append("执行子模块")
            raise TwinStructureViolationError(
                f"双子结构不完整，缺少：{', '.join(missing)}"
            )
        
        container = TwinContainer(self._parent_id)
        container.add_control_child(self._control_child)
        container.add_execute_child(self._execute_child)
        
        if self._auto_seal:
            container.seal()
        
        return container


# =============================================================================
# 模块导出列表
# =============================================================================

__all__ = [
    # 异常类型
    "TwinContainerError",
    "TwinStructureViolationError",
    "ChildTypeError",
    "DuplicateChildError",
    "ChildNotFoundError",
    
    # 枚举
    "TwinSlot",
    
    # 数据类
    "ChildRecord",
    
    # 容器
    "TwinContainer",
    
    # 构建器
    "TwinContainerBuilder",
]
