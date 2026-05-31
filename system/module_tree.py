"""
阶段66-70：模块树组装
Module Tree Assembly

职责定义：
- 构建完整的模块树
- 管理模块层级关系
- 提供模块查找和访问
"""

from typing import Optional, Dict, Any, List, Iterator
from collections import defaultdict

from core.base_module import BaseModule, ControlModuleBase, ExecuteModuleBase
from core_types.core_types import ModuleID, ModuleLevel
from modules.level1.root_twin_binding import RootModule, RootModuleBuilder
from modules.level1.control_module import Level1ControlModule
from modules.level1.execute_module import Level1ExecuteModule
from modules.level2 import Level2ModuleBinder
from utils.logger import Logger


class ModuleNode:
    """模块树节点"""
    
    def __init__(self, module: BaseModule, parent: Optional['ModuleNode'] = None):
        self.module = module
        self.parent = parent
        self.children: List['ModuleNode'] = []
        self.level = module.module_level
    
    def add_child(self, child: 'ModuleNode') -> None:
        """添加子节点"""
        self.children.append(child)
        child.parent = self
    
    def get_descendants(self) -> List['ModuleNode']:
        """获取所有后代节点"""
        descendants = []
        for child in self.children:
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants
    
    def __repr__(self) -> str:
        return f"ModuleNode({self.module.module_id}, level={self.level})"


class ModuleTree:
    """
    模块树
    
    管理整个系统的模块层级结构
    """
    
    def __init__(self, root_module: RootModule):
        self._root = ModuleNode(root_module)
        self._modules: Dict[ModuleID, ModuleNode] = {root_module.module_id: self._root}
        self._logger = Logger("ModuleTree")
        self._build_tree()
    
    def _build_tree(self) -> None:
        """构建模块树"""
        self._logger.info("构建模块树")
        self._add_children_recursive(self._root)
        self._logger.info(f"模块树构建完成，共 {len(self._modules)} 个模块")
    
    def _add_children_recursive(self, node: ModuleNode) -> None:
        """递归添加子模块"""
        module = node.module
        
        # 添加管控子模块
        control_child = module.get_control_child()
        if control_child:
            child_node = ModuleNode(control_child, node)
            node.add_child(child_node)
            self._modules[control_child.module_id] = child_node
            self._add_children_recursive(child_node)
        
        # 添加执行子模块
        execute_child = module.get_execute_child()
        if execute_child:
            child_node = ModuleNode(execute_child, node)
            node.add_child(child_node)
            self._modules[execute_child.module_id] = child_node
            self._add_children_recursive(child_node)
    
    def get_root(self) -> ModuleNode:
        """获取根节点"""
        return self._root
    
    def get_module(self, module_id: ModuleID) -> Optional[BaseModule]:
        """根据ID获取模块"""
        node = self._modules.get(module_id)
        return node.module if node else None
    
    def get_node(self, module_id: ModuleID) -> Optional[ModuleNode]:
        """根据ID获取节点"""
        return self._modules.get(module_id)
    
    def get_modules_by_level(self, level: ModuleLevel) -> List[BaseModule]:
        """获取指定层级的所有模块"""
        return [
            node.module for node in self._modules.values()
            if node.level == level
        ]
    
    def get_all_modules(self) -> List[BaseModule]:
        """获取所有模块"""
        return [node.module for node in self._modules.values()]
    
    def get_module_count(self) -> int:
        """获取模块总数"""
        return len(self._modules)
    
    def get_tree_depth(self) -> int:
        """获取树的深度"""
        def get_depth(node: ModuleNode) -> int:
            if not node.children:
                return 1
            return 1 + max(get_depth(child) for child in node.children)
        return get_depth(self._root)
    
    def traverse(self, order: str = "pre") -> Iterator[BaseModule]:
        """
        遍历模块树
        
        Args:
            order: 遍历顺序，"pre"(前序)、"post"(后序)、"level"(层序)
        """
        if order == "pre":
            yield from self._pre_order_traversal(self._root)
        elif order == "post":
            yield from self._post_order_traversal(self._root)
        elif order == "level":
            yield from self._level_order_traversal()
    
    def _pre_order_traversal(self, node: ModuleNode) -> Iterator[BaseModule]:
        """前序遍历"""
        yield node.module
        for child in node.children:
            yield from self._pre_order_traversal(child)
    
    def _post_order_traversal(self, node: ModuleNode) -> Iterator[BaseModule]:
        """后序遍历"""
        for child in node.children:
            yield from self._post_order_traversal(child)
        yield node.module
    
    def _level_order_traversal(self) -> Iterator[BaseModule]:
        """层序遍历"""
        from collections import deque
        queue = deque([self._root])
        while queue:
            node = queue.popleft()
            yield node.module
            queue.extend(node.children)
    
    def print_tree(self, node: Optional[ModuleNode] = None, indent: int = 0) -> str:
        """打印模块树"""
        if node is None:
            node = self._root
        
        result = "  " * indent + f"- {node.module.module_name} ({node.level.name})\n"
        for child in node.children:
            result += self.print_tree(child, indent + 1)
        return result


class ModuleTreeBuilder:
    """
    模块树构建器
    
    用于构建完整的模块树
    """
    
    def __init__(self):
        self._logger = Logger("ModuleTreeBuilder")
        self._root_module: Optional[RootModule] = None
        self._level1_control: Optional[Level1ControlModule] = None
        self._level1_execute: Optional[Level1ExecuteModule] = None
    
    def build_standard_tree(self) -> ModuleTree:
        """
        构建标准模块树
        
        结构：
        - RootModule
          - Level1ControlModule
            - Level2GovernanceModule
              - Level2MonitoringModule
          - Level1ExecuteModule
        """
        self._logger.info("构建标准模块树")
        
        # 1. 创建一级模块
        self._level1_control = Level1ControlModule()
        self._level1_execute = Level1ExecuteModule()
        
        # 2. 创建二级模块并绑定
        level2_binder = Level2ModuleBinder()
        level2_modules = level2_binder.create_full_level2_binding(
            self._level1_control,
            self._level1_execute
        )
        
        # 3. 创建根模块
        root_builder = RootModuleBuilder()
        self._root_module = root_builder.set_level1_control(
            self._level1_control
        ).set_level1_execute(
            self._level1_execute
        ).build()
        
        # 4. 构建模块树
        tree = ModuleTree(self._root_module)
        
        self._logger.info(f"标准模块树构建完成，共 {tree.get_module_count()} 个模块")
        return tree
    
    def build_minimal_tree(self) -> ModuleTree:
        """
        构建最小模块树
        
        只包含根模块和一级模块
        """
        self._logger.info("构建最小模块树")
        
        # 创建一级模块
        self._level1_control = Level1ControlModule()
        self._level1_execute = Level1ExecuteModule()
        
        # 创建根模块
        root_builder = RootModuleBuilder()
        self._root_module = root_builder.set_level1_control(
            self._level1_control
        ).set_level1_execute(
            self._level1_execute
        ).build()
        
        tree = ModuleTree(self._root_module)
        self._logger.info(f"最小模块树构建完成，共 {tree.get_module_count()} 个模块")
        return tree


__all__ = [
    "ModuleTree",
    "ModuleTreeBuilder",
    "ModuleNode",
]
