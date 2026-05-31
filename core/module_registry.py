"""
超长任务Agent树形双生子模块化执行系统 - 模块注册中心实现
Module Registry Implementation for Long-Task Agent Twin-Module Execution System

阶段5：模块注册中心实现
遵循原则：图难于其易，为大于其细
核心约束：全局唯一注册中心，支持树形结构遍历
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from core_types.core_types import (
    ModuleID, TaskID,
    ModuleType, ModuleLevel, ModuleState,
    CheckResult, ValidationReport,
)

# 前向引用
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.base_module import BaseModule


# =============================================================================
# 1. 注册异常类型 (Registry Exception Types)
# =============================================================================

class RegistryError(Exception):
    """注册中心基础异常"""
    pass


class ModuleAlreadyRegisteredError(RegistryError):
    """模块已注册异常"""
    pass


class ModuleNotRegisteredError(RegistryError):
    """模块未注册异常"""
    pass


class DuplicateModuleIDError(RegistryError):
    """重复模块ID异常"""
    pass


# =============================================================================
# 2. 模块注册记录 (Module Registration Record)
# =============================================================================

@dataclass
class ModuleRegistryRecord:
    """
    模块注册记录
    记录模块在注册中心中的完整信息
    """
    module: "BaseModule"
    registered_at: datetime = field(default_factory=datetime.now)
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def module_id(self) -> ModuleID:
        return self.module.module_id
    
    @property
    def module_name(self) -> str:
        return self.module.module_name
    
    @property
    def module_type(self) -> ModuleType:
        return self.module.module_type
    
    @property
    def module_level(self) -> ModuleLevel:
        return self.module.module_level
    
    @property
    def module_state(self) -> ModuleState:
        return self.module.module_state
    
    def add_tag(self, tag: str) -> None:
        """添加标签"""
        self.tags.add(tag)
    
    def remove_tag(self, tag: str) -> None:
        """移除标签"""
        self.tags.discard(tag)
    
    def has_tag(self, tag: str) -> bool:
        """检查是否有标签"""
        return tag in self.tags


# =============================================================================
# 3. 模块注册中心 (Module Registry)
# =============================================================================

class ModuleRegistry:
    """
    模块注册中心
    
    全局唯一的模块注册中心，提供：
    1. 模块注册与注销
    2. 按ID查询模块
    3. 按类型/层级/标签筛选
    4. 树形结构遍历
    5. 注册统计
    
    使用方式：
        registry = ModuleRegistry.instance()
        registry.register(module)
        module = registry.get_by_id(module_id)
    """
    
    _instance: Optional["ModuleRegistry"] = None
    
    def __init__(self):
        """私有初始化"""
        self._modules: Dict[ModuleID, ModuleRegistryRecord] = {}
        self._id_to_parent: Dict[ModuleID, Optional[ModuleID]] = {}
        self._id_to_children: Dict[ModuleID, List[ModuleID]] = {}
        self._tag_index: Dict[str, Set[ModuleID]] = {}
        self._type_index: Dict[ModuleType, Set[ModuleID]] = {
            ModuleType.CONTROL: set(),
            ModuleType.EXECUTE: set(),
        }
        self._level_index: Dict[ModuleLevel, Set[ModuleID]] = {
            ModuleLevel.ROOT: set(),
            ModuleLevel.LEVEL1: set(),
            ModuleLevel.LEVEL2: set(),
            ModuleLevel.LEVEL3: set(),
            ModuleLevel.LEVEL4: set(),
        }
        self._registration_order: List[ModuleID] = []
    
    # =====================================================================
    # 单例模式
    # =====================================================================
    
    @classmethod
    def instance(cls) -> "ModuleRegistry":
        """
        获取注册中心单例
        
        Returns:
            ModuleRegistry: 注册中心实例
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """重置注册中心（仅用于测试）"""
        cls._instance = None
    
    # =====================================================================
    # 模块注册
    # =====================================================================
    
    def register(self, module: "BaseModule", tags: Optional[List[str]] = None) -> None:
        """
        注册模块
        
        Args:
            module: 待注册的模块
            tags: 标签列表
            
        Raises:
            ModuleAlreadyRegisteredError: 模块已注册
        """
        module_id = module.module_id
        
        if module_id in self._modules:
            raise ModuleAlreadyRegisteredError(
                f"模块 {module_id} 已注册"
            )
        
        # 创建注册记录
        record = ModuleRegistryRecord(module=module)
        if tags:
            for tag in tags:
                record.add_tag(tag)
        
        # 存储记录
        self._modules[module_id] = record
        self._registration_order.append(module_id)
        
        # 更新索引
        self._type_index[module.module_type].add(module_id)
        self._level_index[module.module_level].add(module_id)
        
        for tag in record.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(module_id)
        
        # 更新父子关系
        parent_id = module.parent_module_id
        self._id_to_parent[module_id] = parent_id
        if parent_id is not None:
            if parent_id not in self._id_to_children:
                self._id_to_children[parent_id] = []
            self._id_to_children[parent_id].append(module_id)
    
    def unregister(self, module_id: ModuleID) -> None:
        """
        注销模块
        
        Args:
            module_id: 模块ID
            
        Raises:
            ModuleNotRegisteredError: 模块未注册
        """
        if module_id not in self._modules:
            raise ModuleNotRegisteredError(
                f"模块 {module_id} 未注册"
            )
        
        record = self._modules[module_id]
        
        # 清除索引
        self._type_index[record.module_type].discard(module_id)
        self._level_index[record.module_level].discard(module_id)
        
        for tag in record.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(module_id)
        
        # 清除父子关系
        parent_id = self._id_to_parent.pop(module_id, None)
        if parent_id is not None and parent_id in self._id_to_children:
            self._id_to_children[parent_id] = [
                cid for cid in self._id_to_children[parent_id] if cid != module_id
            ]
        
        # 清除子模块引用
        if module_id in self._id_to_children:
            del self._id_to_children[module_id]
        
        # 清除注册记录
        del self._modules[module_id]
        self._registration_order.remove(module_id)
    
    def is_registered(self, module_id: ModuleID) -> bool:
        """
        检查模块是否已注册
        
        Args:
            module_id: 模块ID
            
        Returns:
            bool: 是否已注册
        """
        return module_id in self._modules
    
    # =====================================================================
    # 模块查询
    # =====================================================================
    
    def get_by_id(self, module_id: ModuleID) -> Optional["BaseModule"]:
        """
        根据ID获取模块
        
        Args:
            module_id: 模块ID
            
        Returns:
            Optional[BaseModule]: 模块实例，未找到则返回None
        """
        record = self._modules.get(module_id)
        return record.module if record else None
    
    def get_record(self, module_id: ModuleID) -> Optional[ModuleRegistryRecord]:
        """
        根据ID获取注册记录
        
        Args:
            module_id: 模块ID
            
        Returns:
            Optional[ModuleRegistryRecord]: 注册记录
        """
        return self._modules.get(module_id)
    
    def get_by_name(self, name: str) -> List["BaseModule"]:
        """
        根据名称获取模块（可能有多个同名模块）
        
        Args:
            name: 模块名称
            
        Returns:
            List[BaseModule]: 模块列表
        """
        results = []
        for record in self._modules.values():
            if record.module_name == name:
                results.append(record.module)
        return results
    
    # =====================================================================
    # 按类型/层级/标签筛选
    # =====================================================================
    
    def get_by_type(self, module_type: ModuleType) -> List["BaseModule"]:
        """
        根据类型获取模块
        
        Args:
            module_type: 模块类型
            
        Returns:
            List[BaseModule]: 模块列表
        """
        ids = self._type_index.get(module_type, set())
        return [self._modules[mid].module for mid in ids if mid in self._modules]
    
    def get_by_level(self, module_level: ModuleLevel) -> List["BaseModule"]:
        """
        根据层级获取模块
        
        Args:
            module_level: 模块层级
            
        Returns:
            List[BaseModule]: 模块列表
        """
        ids = self._level_index.get(module_level, set())
        return [self._modules[mid].module for mid in ids if mid in self._modules]
    
    def get_by_tag(self, tag: str) -> List["BaseModule"]:
        """
        根据标签获取模块
        
        Args:
            tag: 标签
            
        Returns:
            List[BaseModule]: 模块列表
        """
        ids = self._tag_index.get(tag, set())
        return [self._modules[mid].module for mid in ids if mid in self._modules]
    
    def get_by_type_and_level(self, module_type: ModuleType, module_level: ModuleLevel) -> List["BaseModule"]:
        """
        根据类型和层级获取模块
        
        Args:
            module_type: 模块类型
            module_level: 模块层级
            
        Returns:
            List[BaseModule]: 模块列表
        """
        type_ids = self._type_index.get(module_type, set())
        level_ids = self._level_index.get(module_level, set())
        common_ids = type_ids & level_ids
        return [self._modules[mid].module for mid in common_ids if mid in self._modules]
    
    # =====================================================================
    # 父子关系查询
    # =====================================================================
    
    def get_parent(self, module_id: ModuleID) -> Optional["BaseModule"]:
        """
        获取父模块
        
        Args:
            module_id: 模块ID
            
        Returns:
            Optional[BaseModule]: 父模块，无父模块则返回None
        """
        parent_id = self._id_to_parent.get(module_id)
        if parent_id is None:
            return None
        return self.get_by_id(parent_id)
    
    def get_children(self, module_id: ModuleID) -> List["BaseModule"]:
        """
        获取直接子模块
        
        Args:
            module_id: 模块ID
            
        Returns:
            List[BaseModule]: 子模块列表
        """
        child_ids = self._id_to_children.get(module_id, [])
        return [self.get_by_id(cid) for cid in child_ids if self.get_by_id(cid) is not None]
    
    def get_ancestors(self, module_id: ModuleID) -> List["BaseModule"]:
        """
        获取所有祖先模块（从直接父到根）
        
        Args:
            module_id: 模块ID
            
        Returns:
            List[BaseModule]: 祖先模块列表（从近到远）
        """
        ancestors = []
        current_id = module_id
        visited = set()
        
        while current_id is not None and current_id not in visited:
            visited.add(current_id)
            parent_id = self._id_to_parent.get(current_id)
            if parent_id is None:
                break
            parent = self.get_by_id(parent_id)
            if parent is None:
                break
            ancestors.append(parent)
            current_id = parent_id
        
        return ancestors
    
    def get_descendants(self, module_id: ModuleID) -> List["BaseModule"]:
        """
        获取所有后代模块（广度优先）
        
        Args:
            module_id: 模块ID
            
        Returns:
            List[BaseModule]: 后代模块列表
        """
        descendants = []
        queue = [module_id]
        visited = {module_id}
        
        while queue:
            current_id = queue.pop(0)
            child_ids = self._id_to_children.get(current_id, [])
            for cid in child_ids:
                if cid not in visited:
                    visited.add(cid)
                    child_module = self.get_by_id(cid)
                    if child_module is not None:
                        descendants.append(child_module)
                        queue.append(cid)
        
        return descendants
    
    def get_root_modules(self) -> List["BaseModule"]:
        """
        获取所有根模块（没有父模块的模块）
        
        Returns:
            List[BaseModule]: 根模块列表
        """
        roots = []
        for mid, record in self._modules.items():
            parent_id = self._id_to_parent.get(mid)
            if parent_id is None:
                roots.append(record.module)
        return roots
    
    def get_depth(self, module_id: ModuleID) -> int:
        """
        获取模块在树中的深度
        
        Args:
            module_id: 模块ID
            
        Returns:
            int: 深度（根模块为0）
        """
        return len(self.get_ancestors(module_id))
    
    # =====================================================================
    # 树形结构输出
    # =====================================================================
    
    def get_tree_structure(self, root_id: Optional[ModuleID] = None, max_depth: int = -1) -> str:
        """
        获取树形结构字符串
        
        Args:
            root_id: 根模块ID，如果为None则从所有根模块开始
            max_depth: 最大深度，-1表示不限制
            
        Returns:
            str: 树形结构字符串
        """
        lines = []
        
        if root_id is not None:
            self._build_tree_lines(root_id, lines, "", 0, max_depth)
        else:
            roots = self.get_root_modules()
            for i, root in enumerate(roots):
                self._build_tree_lines(root.module_id, lines, "", 0, max_depth)
                if i < len(roots) - 1:
                    lines.append("")
        
        return "\n".join(lines)
    
    def _build_tree_lines(
        self,
        module_id: ModuleID,
        lines: List[str],
        prefix: str,
        current_depth: int,
        max_depth: int,
    ) -> None:
        """递归构建树形结构行"""
        if max_depth >= 0 and current_depth > max_depth:
            return
        
        record = self._modules.get(module_id)
        if record is None:
            return
        
        # 构建当前行
        type_marker = "[控]" if record.module_type == ModuleType.CONTROL else "[执]"
        state_marker = f"({record.module_state.name})"
        line = f"{prefix}{type_marker} {record.module_name} {state_marker}"
        lines.append(line)
        
        # 递归子模块
        child_ids = self._id_to_children.get(module_id, [])
        for i, cid in enumerate(child_ids):
            child_record = self._modules.get(cid)
            if child_record is None:
                continue
            
            is_last = (i == len(child_ids) - 1)
            child_prefix = prefix + ("    " if is_last else "│   ")
            connector = "└── " if is_last else "├── "
            
            child_type_marker = "[控]" if child_record.module_type == ModuleType.CONTROL else "[执]"
            child_state_marker = f"({child_record.module_state.name})"
            child_line = f"{prefix}{connector}{child_type_marker} {child_record.module_name} {child_state_marker}"
            lines.append(child_line)
            
            # 递归
            self._build_tree_lines(cid, lines, child_prefix, current_depth + 1, max_depth)
    
    # =====================================================================
    # 注册统计
    # =====================================================================
    
    @property
    def total_count(self) -> int:
        """已注册模块总数"""
        return len(self._modules)
    
    @property
    def control_count(self) -> int:
        """管控类模块数量"""
        return len(self._type_index[ModuleType.CONTROL])
    
    @property
    def execute_count(self) -> int:
        """执行类模块数量"""
        return len(self._type_index[ModuleType.EXECUTE])
    
    def count_by_level(self, level: ModuleLevel) -> int:
        """按层级统计数量"""
        return len(self._level_index.get(level, set()))
    
    def get_all_tags(self) -> Set[str]:
        """获取所有标签"""
        return set(self._tag_index.keys())
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取注册统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "total_count": self.total_count,
            "control_count": self.control_count,
            "execute_count": self.execute_count,
            "root_count": len(self.get_root_modules()),
            "level_distribution": {
                level.name: len(ids) for level, ids in self._level_index.items()
            },
            "tag_count": len(self._tag_index),
            "all_tags": list(self.get_all_tags()),
        }
    
    # =====================================================================
    # 标签管理
    # =====================================================================
    
    def add_tag(self, module_id: ModuleID, tag: str) -> None:
        """
        为模块添加标签
        
        Args:
            module_id: 模块ID
            tag: 标签
        """
        record = self._modules.get(module_id)
        if record is None:
            raise ModuleNotRegisteredError(f"模块 {module_id} 未注册")
        
        record.add_tag(tag)
        if tag not in self._tag_index:
            self._tag_index[tag] = set()
        self._tag_index[tag].add(module_id)
    
    def remove_tag(self, module_id: ModuleID, tag: str) -> None:
        """
        移除模块标签
        
        Args:
            module_id: 模块ID
            tag: 标签
        """
        record = self._modules.get(module_id)
        if record is None:
            raise ModuleNotRegisteredError(f"模块 {module_id} 未注册")
        
        record.remove_tag(tag)
        if tag in self._tag_index:
            self._tag_index[tag].discard(module_id)
    
    # =====================================================================
    # 批量操作
    # =====================================================================
    
    def register_batch(self, modules: List["BaseModule"], tags: Optional[List[str]] = None) -> List[ModuleID]:
        """
        批量注册模块
        
        Args:
            modules: 模块列表
            tags: 公共标签列表
            
        Returns:
            List[ModuleID]: 注册成功的模块ID列表
        """
        registered_ids = []
        for module in modules:
            try:
                self.register(module, tags=tags)
                registered_ids.append(module.module_id)
            except ModuleAlreadyRegisteredError:
                pass  # 跳过已注册的模块
        return registered_ids
    
    def unregister_all(self) -> int:
        """
        注销所有模块
        
        Returns:
            int: 注销的模块数量
        """
        count = self.total_count
        self._modules.clear()
        self._id_to_parent.clear()
        self._id_to_children.clear()
        self._tag_index.clear()
        for key in self._type_index:
            self._type_index[key].clear()
        for key in self._level_index:
            self._level_index[key].clear()
        self._registration_order.clear()
        return count
    
    def get_all_modules(self) -> List["BaseModule"]:
        """
        获取所有已注册模块（按注册顺序）
        
        Returns:
            List[BaseModule]: 模块列表
        """
        return [
            self._modules[mid].module
            for mid in self._registration_order
            if mid in self._modules
        ]
    
    # =====================================================================
    # 结构校验
    # =====================================================================
    
    def validate_registry(self) -> ValidationReport:
        """
        验证注册中心完整性
        
        检查项：
        1. 父子关系一致性
        2. 索引一致性
        3. 孤儿模块检测
        
        Returns:
            ValidationReport: 验证报告
        """
        task_id = TaskID()
        report = ValidationReport(task_id=task_id, overall_passed=True)
        
        # 检查1：父子关系一致性
        for mid, parent_id in self._id_to_parent.items():
            if parent_id is not None and parent_id not in self._modules:
                report.add_result(CheckResult.failed_result(
                    "parent_consistency_check",
                    f"模块 {mid} 的父模块 {parent_id} 未注册",
                    "warning"
                ))
        
        # 检查2：子模块引用一致性
        for parent_id, child_ids in self._id_to_children.items():
            for cid in child_ids:
                if cid not in self._modules:
                    report.add_result(CheckResult.failed_result(
                        "child_consistency_check",
                        f"父模块 {parent_id} 的子模块 {cid} 未注册",
                        "warning"
                    ))
        
        # 检查3：类型索引一致性
        for module_type, ids in self._type_index.items():
            for mid in ids:
                if mid not in self._modules:
                    report.add_result(CheckResult.failed_result(
                        "type_index_check",
                        f"类型索引中模块 {mid} 未注册",
                        "warning"
                    ))
        
        if report.overall_passed:
            report.add_result(CheckResult.passed_result(
                "registry_validation",
                "注册中心验证通过"
            ))
        
        return report
    
    def __repr__(self) -> str:
        return f"ModuleRegistry(modules={self.total_count})"


# =============================================================================
# 模块导出列表
# =============================================================================

__all__ = [
    # 异常类型
    "RegistryError",
    "ModuleAlreadyRegisteredError",
    "ModuleNotRegisteredError",
    "DuplicateModuleIDError",
    
    # 注册记录
    "ModuleRegistryRecord",
    
    # 注册中心
    "ModuleRegistry",
]
