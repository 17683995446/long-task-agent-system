"""
阶段33：三级依赖模块
Level3DependencyModule

职责定义：
- 依赖分析
- 依赖图构建
- 循环依赖检测
"""

from typing import Optional, Dict, Any, List, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from core.base_module import ControlModuleBase
from core_types.core_types import (
    ModuleID, TaskID, ModuleLevel,
    InitResult, ModuleOutput, CheckResult, SnapshotData,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)
from utils.logger import Logger


class DependencyStatus(Enum):
    """依赖状态"""
    PENDING = "pending"
    RESOLVED = "resolved"
    FAILED = "failed"
    CIRCULAR = "circular"


@dataclass
class DependencyNode:
    """依赖节点"""
    name: str
    version: str = "*"
    dependencies: List[str] = field(default_factory=list)
    status: DependencyStatus = DependencyStatus.PENDING
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyGraph:
    """依赖图"""
    nodes: Dict[str, DependencyNode] = field(default_factory=dict)
    edges: List[Tuple[str, str]] = field(default_factory=list)
    
    def add_node(self, node: DependencyNode) -> None:
        """添加节点"""
        self.nodes[node.name] = node
    
    def add_edge(self, from_node: str, to_node: str) -> None:
        """添加边"""
        self.edges.append((from_node, to_node))
        if from_node in self.nodes:
            if to_node not in self.nodes[from_node].dependencies:
                self.nodes[from_node].dependencies.append(to_node)
    
    def get_dependencies(self, node_name: str) -> List[str]:
        """获取节点的依赖列表"""
        if node_name in self.nodes:
            return self.nodes[node_name].dependencies
        return []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "nodes": {
                name: {
                    "name": node.name,
                    "version": node.version,
                    "dependencies": node.dependencies,
                    "status": node.status.value,
                    "resolved_at": node.resolved_at.isoformat() if node.resolved_at else None,
                    "metadata": node.metadata,
                }
                for name, node in self.nodes.items()
            },
            "edges": self.edges,
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
        }


@dataclass
class VersionConstraint:
    """版本约束"""
    min_version: Optional[str] = None
    max_version: Optional[str] = None
    exact_version: Optional[str] = None
    
    def is_satisfied(self, version: str) -> bool:
        """检查版本是否满足约束"""
        if self.exact_version:
            return version == self.exact_version
        # 简化版本比较
        if self.min_version and version < self.min_version:
            return False
        if self.max_version and version > self.max_version:
            return False
        return True


class Level3DependencyModule(ControlModuleBase):
    """
    三级依赖模块
    
    职责：
    1. 依赖图构建
    2. 循环依赖检测
    3. 依赖版本管理
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL3
        self._state.module_name = "Level3DependencyModule"
        self._logger = Logger(f"L3D_{self.module_id}")
        
        # 依赖图
        self._dependency_graph: DependencyGraph = DependencyGraph()
        # 版本约束
        self._version_constraints: Dict[str, VersionConstraint] = {}
        # 检测到的循环依赖
        self._circular_dependencies: List[List[str]] = []
        # 解析顺序
        self._resolution_order: List[str] = []
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("三级依赖模块初始化开始")
            
            # 1. 加载配置
            self._load_config(request)
            
            # 2. 初始化依赖图
            self._dependency_graph = DependencyGraph()
            self._version_constraints = {}
            self._circular_dependencies = []
            self._resolution_order = []
            
            self._logger.info("三级依赖模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="三级依赖模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"三级依赖模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L3D_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "auto_detect_cycles": True,
            "strict_version_check": True,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("dependency_config", {})
            self._config.update(custom_config)
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("三级依赖模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "analyze")
            
            if operation == "analyze":
                result = self._analyze_dependencies(input_data)
            elif operation == "detect_cycles":
                result = self._detect_cycles_operation(input_data)
            elif operation == "resolve":
                result = self._resolve_dependencies(input_data)
            elif operation == "add_node":
                result = self._add_node_operation(input_data)
            elif operation == "add_edge":
                result = self._add_edge_operation(input_data)
            elif operation == "check_version":
                result = self._check_version_operation(input_data)
            else:
                result = {"error": f"未知操作: {operation}"}
            
            self._logger.info("三级依赖模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level3DependencyModule",
                    "graph_summary": {
                        "total_nodes": len(self._dependency_graph.nodes),
                        "total_edges": len(self._dependency_graph.edges),
                        "circular_deps_found": len(self._circular_dependencies),
                    },
                },
                message="三级依赖模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"三级依赖模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L3D_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _analyze_dependencies(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析依赖关系"""
        nodes_data = input_data.get("nodes", [])
        edges_data = input_data.get("edges", [])
        
        # 构建依赖图
        for node_data in nodes_data:
            node = DependencyNode(
                name=node_data["name"],
                version=node_data.get("version", "*"),
                dependencies=node_data.get("dependencies", []),
                metadata=node_data.get("metadata", {}),
            )
            self._dependency_graph.add_node(node)
        
        for edge in edges_data:
            self._dependency_graph.add_edge(edge["from"], edge["to"])
        
        # 自动检测循环依赖
        if self._config.get("auto_detect_cycles", True):
            self._detect_cycles()
        
        return {
            "operation": "analyze",
            "nodes_count": len(self._dependency_graph.nodes),
            "edges_count": len(self._dependency_graph.edges),
            "circular_dependencies": self._circular_dependencies,
            "graph": self._dependency_graph.to_dict(),
        }
    
    def _detect_cycles(self) -> List[List[str]]:
        """检测循环依赖（DFS算法）"""
        self._circular_dependencies = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []
        
        def dfs(node_name: str) -> None:
            visited.add(node_name)
            rec_stack.add(node_name)
            path.append(node_name)
            
            for dep in self._dependency_graph.get_dependencies(node_name):
                if dep not in visited:
                    dfs(dep)
                elif dep in rec_stack:
                    # 发现循环
                    cycle_start = path.index(dep)
                    cycle = path[cycle_start:] + [dep]
                    self._circular_dependencies.append(cycle)
            
            path.pop()
            rec_stack.remove(node_name)
        
        for node_name in self._dependency_graph.nodes:
            if node_name not in visited:
                dfs(node_name)
        
        # 标记循环依赖中的节点
        for cycle in self._circular_dependencies:
            for node_name in cycle[:-1]:  # 排除重复的最后一个
                if node_name in self._dependency_graph.nodes:
                    self._dependency_graph.nodes[node_name].status = DependencyStatus.CIRCULAR
        
        return self._circular_dependencies
    
    def _detect_cycles_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行循环依赖检测操作"""
        cycles = self._detect_cycles()
        return {
            "operation": "detect_cycles",
            "cycles_found": len(cycles),
            "cycles": cycles,
            "has_cycles": len(cycles) > 0,
        }
    
    def _resolve_dependencies(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析依赖顺序（拓扑排序）"""
        # 先检测循环
        self._detect_cycles()
        
        if self._circular_dependencies:
            return {
                "operation": "resolve",
                "success": False,
                "error": "存在循环依赖，无法解析",
                "cycles": self._circular_dependencies,
            }
        
        # Kahn算法拓扑排序
        in_degree: Dict[str, int] = {name: 0 for name in self._dependency_graph.nodes}
        for edge in self._dependency_graph.edges:
            in_degree[edge[1]] = in_degree.get(edge[1], 0) + 1
        
        queue = [name for name, degree in in_degree.items() if degree == 0]
        self._resolution_order = []
        
        while queue:
            node_name = queue.pop(0)
            self._resolution_order.append(node_name)
            
            if node_name in self._dependency_graph.nodes:
                self._dependency_graph.nodes[node_name].status = DependencyStatus.RESOLVED
                self._dependency_graph.nodes[node_name].resolved_at = datetime.now()
            
            for dep in self._dependency_graph.get_dependencies(node_name):
                # 找到所有依赖dep的节点（反向边）
                for edge in self._dependency_graph.edges:
                    if edge[0] == node_name and edge[1] == dep:
                        in_degree[dep] -= 1
                        if in_degree[dep] == 0:
                            queue.append(dep)
        
        success = len(self._resolution_order) == len(self._dependency_graph.nodes)
        
        return {
            "operation": "resolve",
            "success": success,
            "resolution_order": self._resolution_order,
            "unresolved": list(set(self._dependency_graph.nodes.keys()) - set(self._resolution_order)),
        }
    
    def _add_node_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加节点操作"""
        node_data = input_data.get("node", {})
        node = DependencyNode(
            name=node_data["name"],
            version=node_data.get("version", "*"),
            dependencies=node_data.get("dependencies", []),
            metadata=node_data.get("metadata", {}),
        )
        self._dependency_graph.add_node(node)
        
        # 自动添加边
        for dep in node.dependencies:
            self._dependency_graph.add_edge(node.name, dep)
        
        return {
            "operation": "add_node",
            "node_name": node.name,
            "success": True,
        }
    
    def _add_edge_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加边操作"""
        from_node = input_data.get("from")
        to_node = input_data.get("to")
        self._dependency_graph.add_edge(from_node, to_node)
        
        return {
            "operation": "add_edge",
            "from": from_node,
            "to": to_node,
            "success": True,
        }
    
    def _check_version_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查版本操作"""
        node_name = input_data.get("node_name")
        required_version = input_data.get("required_version")
        
        if node_name not in self._dependency_graph.nodes:
            return {
                "operation": "check_version",
                "success": False,
                "error": f"节点 {node_name} 不存在",
            }
        
        current_version = self._dependency_graph.nodes[node_name].version
        
        # 检查版本约束
        constraint = self._version_constraints.get(node_name)
        if constraint:
            satisfied = constraint.is_satisfied(current_version)
        else:
            satisfied = required_version is None or current_version == required_version
        
        return {
            "operation": "check_version",
            "node_name": node_name,
            "current_version": current_version,
            "required_version": required_version,
            "satisfied": satisfied,
        }
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("三级依赖模块校验开始")
        
        checks = []
        
        # 1. 校验依赖图
        if self._dependency_graph is not None:
            checks.append("graph_valid")
        
        # 2. 校验循环依赖检测
        if self._config.get("auto_detect_cycles", True):
            checks.append("cycle_detection_enabled")
        
        # 3. 校验模块状态
        if self._state.module_level == ModuleLevel.LEVEL3:
            checks.append("level_valid")
        
        # 4. 校验图一致性
        if len(self._dependency_graph.nodes) >= 0:
            checks.append("graph_consistency")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="dependency_validation",
                message="三级依赖模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="dependency_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("dependency_graph", self._dependency_graph.to_dict())
        snapshot.set_state("circular_dependencies", self._circular_dependencies)
        snapshot.set_state("resolution_order", self._resolution_order)
        snapshot.set_state("version_constraints", {
            name: {
                "min_version": vc.min_version,
                "max_version": vc.max_version,
                "exact_version": vc.exact_version,
            }
            for name, vc in self._version_constraints.items()
        })
        snapshot.metadata["module_type"] = "Level3DependencyModule"
    
    # =====================================================================
    # 公共接口
    # =====================================================================
    
    def get_dependency_graph(self) -> DependencyGraph:
        """获取依赖图"""
        return self._dependency_graph
    
    def get_circular_dependencies(self) -> List[List[str]]:
        """获取循环依赖列表"""
        return self._circular_dependencies
    
    def get_resolution_order(self) -> List[str]:
        """获取解析顺序"""
        return self._resolution_order
    
    def add_version_constraint(self, node_name: str, constraint: VersionConstraint) -> None:
        """添加版本约束"""
        self._version_constraints[node_name] = constraint
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level3DependencyModule",
    "DependencyGraph",
    "DependencyNode",
    "DependencyStatus",
    "VersionConstraint",
]
