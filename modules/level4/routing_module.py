"""
阶段48：四级路由模块
Level4RoutingModule

职责定义：
- 请求路由
- 路由规则
- 路由表管理
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re

from core.base_module import ExecuteModuleBase
from core_types.core_types import (
    ModuleID, TaskID, ModuleLevel,
    InitResult, ModuleOutput, CheckResult, SnapshotData,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)
from utils.logger import Logger


class RouteMethod(Enum):
    """路由方法"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    ALL = "*"


class RouteType(Enum):
    """路由类型"""
    EXACT = "exact"
    PREFIX = "prefix"
    REGEX = "regex"
    PARAMETERIZED = "parameterized"
    WILDCARD = "wildcard"


@dataclass
class Route:
    """路由定义"""
    route_id: str
    name: str
    path: str
    method: RouteMethod
    route_type: RouteType
    target: str
    priority: int = 0
    enabled: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "route_id": self.route_id,
            "name": self.name,
            "path": self.path,
            "method": self.method.value,
            "route_type": self.route_type.value,
            "target": self.target,
            "priority": self.priority,
            "enabled": self.enabled,
            "conditions": self.conditions,
            "metadata": self.metadata,
        }


@dataclass
class RouteMatch:
    """路由匹配结果"""
    match_id: str
    route_id: str
    path: str
    method: str
    matched: bool
    parameters: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "route_id": self.route_id,
            "path": self.path,
            "method": self.method,
            "matched": self.matched,
            "parameters": self.parameters,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RouteTable:
    """路由表"""
    table_id: str
    name: str
    routes: List[Route] = field(default_factory=list)
    default_target: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_id": self.table_id,
            "name": self.name,
            "route_count": len(self.routes),
            "default_target": self.default_target,
            "metadata": self.metadata,
            "routes": [r.to_dict() for r in self.routes],
        }


class Level4RoutingModule(ExecuteModuleBase):
    """
    四级路由模块
    
    职责：
    1. 请求路由
    2. 路由规则
    3. 路由表管理
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL4
        self._state.module_name = "Level4RoutingModule"
        self._logger = Logger(f"L4R_{self.module_id}")
        
        # 路由表存储
        self._route_tables: Dict[str, RouteTable] = {}
        # 当前路由表
        self._active_table: Optional[RouteTable] = None
        # 路由匹配记录
        self._matches: List[RouteMatch] = []
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("四级路由模块初始化开始")
            
            # 1. 加载配置
            self._load_config(request)
            
            # 2. 初始化存储
            self._route_tables = {}
            self._active_table = None
            self._matches = []
            
            # 3. 加载默认路由
            self._load_default_routes()
            
            self._logger.info("四级路由模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="四级路由模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级路由模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L4R_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "case_sensitive": False,
            "log_matches": True,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("routing_config", {})
            self._config.update(custom_config)
    
    def _load_default_routes(self) -> None:
        """加载默认路由"""
        import uuid
        
        table = RouteTable(
            table_id=str(uuid.uuid4()),
            name="default",
            default_target="default_handler",
        )
        
        default_routes = [
            Route(
                route_id="route_health",
                name="健康检查",
                path="/health",
                method=RouteMethod.GET,
                route_type=RouteType.EXACT,
                target="health_handler",
                priority=100,
            ),
            Route(
                route_id="route_api",
                name="API路由",
                path="/api/*",
                method=RouteMethod.ALL,
                route_type=RouteType.PREFIX,
                target="api_handler",
                priority=50,
            ),
            Route(
                route_id="route_static",
                name="静态资源",
                path="/static/*",
                method=RouteMethod.GET,
                route_type=RouteType.PREFIX,
                target="static_handler",
                priority=10,
            ),
        ]
        table.routes.extend(default_routes)
        self._route_tables[table.table_id] = table
        self._active_table = table
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("四级路由模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "route")
            
            if operation == "route":
                result = self._route_operation(input_data)
            elif operation == "add_route":
                result = self._add_route_operation(input_data)
            elif operation == "create_table":
                result = self._create_table_operation(input_data)
            elif operation == "get_table":
                result = self._get_table_operation(input_data)
            elif operation == "switch_table":
                result = self._switch_table_operation(input_data)
            elif operation == "get_matches":
                result = self._get_matches_operation(input_data)
            elif operation == "remove_route":
                result = self._remove_route_operation(input_data)
            elif operation == "list_tables":
                result = self._list_tables_operation()
            else:
                result = {"error": f"未知操作: {operation}"}
            
            self._logger.info("四级路由模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level4RoutingModule",
                    "routing_summary": {
                        "total_tables": len(self._route_tables),
                        "active_table": self._active_table.table_id if self._active_table else None,
                        "total_matches": len(self._matches),
                    },
                },
                message="四级路由模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级路由模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L4R_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _route_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行路由"""
        import uuid
        
        path = input_data.get("path", "")
        method = input_data.get("method", "GET")
        context_data = input_data.get("context", {})
        
        if not self._active_table:
            return {"operation": "route", "error": "没有活跃的路由表", "success": False}
        
        # 查找匹配的路由
        matched_route, parameters = self._find_route(path, method, context_data)
        
        match = RouteMatch(
            match_id=str(uuid.uuid4()),
            route_id=matched_route.route_id if matched_route else None,
            path=path,
            method=method,
            matched=matched_route is not None,
            parameters=parameters,
        )
        self._matches.append(match)
        
        if matched_route:
            return {
                "operation": "route",
                "path": path,
                "method": method,
                "matched": True,
                "route_id": matched_route.route_id,
                "route_name": matched_route.name,
                "target": matched_route.target,
                "parameters": parameters,
            }
        else:
            return {
                "operation": "route",
                "path": path,
                "method": method,
                "matched": False,
                "default_target": self._active_table.default_target,
            }
    
    def _find_route(self, path: str, method: str, context_data: Dict[str, Any]) -> tuple:
        """查找匹配的路由"""
        if not self._active_table:
            return None, {}
        
        # 按优先级排序
        sorted_routes = sorted(self._active_table.routes, key=lambda r: r.priority, reverse=True)
        
        for route in sorted_routes:
            if not route.enabled:
                continue
            
            # 检查方法匹配
            if route.method != RouteMethod.ALL and route.method.value != method:
                continue
            
            # 检查路径匹配
            matched, parameters = self._match_path(route, path)
            if not matched:
                continue
            
            # 检查条件
            if route.conditions and not self._evaluate_conditions(route.conditions, context_data):
                continue
            
            return route, parameters
        
        return None, {}
    
    def _match_path(self, route: Route, path: str) -> tuple:
        """匹配路径"""
        case_sensitive = self._config.get("case_sensitive", False)
        
        if not case_sensitive:
            route_path = route.path.lower()
            check_path = path.lower()
        else:
            route_path = route.path
            check_path = path
        
        if route.route_type == RouteType.EXACT:
            return route_path == check_path, {}
        
        elif route.route_type == RouteType.PREFIX:
            if route_path.endswith("*"):
                prefix = route_path[:-1]
                if check_path.startswith(prefix):
                    remainder = check_path[len(prefix):]
                    return True, {"*": remainder}
            return check_path.startswith(route_path), {}
        
        elif route.route_type == RouteType.REGEX:
            try:
                pattern = re.compile(route.path)
                match = pattern.match(check_path)
                if match:
                    return True, match.groupdict()
            except re.error:
                pass
            return False, {}
        
        elif route.route_type == RouteType.PARAMETERIZED:
            # 简单参数化路由匹配，如 /users/{id}
            route_parts = route_path.split("/")
            path_parts = check_path.split("/")
            
            if len(route_parts) != len(path_parts):
                return False, {}
            
            parameters = {}
            for rp, pp in zip(route_parts, path_parts):
                if rp.startswith("{") and rp.endswith("}"):
                    param_name = rp[1:-1]
                    parameters[param_name] = pp
                elif rp != pp:
                    return False, {}
            
            return True, parameters
        
        elif route.route_type == RouteType.WILDCARD:
            return True, {}
        
        return False, {}
    
    def _evaluate_conditions(self, conditions: Dict[str, Any], context_data: Dict[str, Any]) -> bool:
        """评估条件"""
        for key, expected in conditions.items():
            actual = context_data.get(key)
            if actual != expected:
                return False
        return True
    
    def _add_route_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加路由"""
        table_id = input_data.get("table_id")
        if not table_id or table_id not in self._route_tables:
            return {"operation": "add_route", "error": "路由表不存在", "success": False}
        
        table = self._route_tables[table_id]
        
        route = Route(
            route_id=input_data.get("route_id", ""),
            name=input_data.get("name", ""),
            path=input_data.get("path", ""),
            method=RouteMethod(input_data.get("method", "GET")),
            route_type=RouteType(input_data.get("route_type", "exact")),
            target=input_data.get("target", ""),
            priority=input_data.get("priority", 0),
            enabled=input_data.get("enabled", True),
            conditions=input_data.get("conditions", {}),
            metadata=input_data.get("metadata", {}),
        )
        table.routes.append(route)
        
        return {"operation": "add_route", "route_id": route.route_id, "added": True}
    
    def _create_table_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建路由表"""
        import uuid
        
        table_id = str(uuid.uuid4())
        table = RouteTable(
            table_id=table_id,
            name=input_data.get("name", f"table_{table_id[:8]}"),
            default_target=input_data.get("default_target"),
            metadata=input_data.get("metadata", {}),
        )
        self._route_tables[table_id] = table
        
        return {"operation": "create_table", "table_id": table_id, "created": True}
    
    def _get_table_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取路由表"""
        table_id = input_data.get("table_id")
        if not table_id or table_id not in self._route_tables:
            return {"operation": "get_table", "error": "路由表不存在"}
        
        table = self._route_tables[table_id]
        return {"operation": "get_table", "table": table.to_dict()}
    
    def _switch_table_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """切换路由表"""
        table_id = input_data.get("table_id")
        if not table_id or table_id not in self._route_tables:
            return {"operation": "switch_table", "error": "路由表不存在", "success": False}
        
        self._active_table = self._route_tables[table_id]
        
        return {
            "operation": "switch_table",
            "table_id": table_id,
            "table_name": self._active_table.name,
            "switched": True,
        }
    
    def _get_matches_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取匹配记录"""
        limit = input_data.get("limit", 100)
        matches = sorted(self._matches, key=lambda m: m.timestamp, reverse=True)[:limit]
        
        return {
            "operation": "get_matches",
            "total": len(self._matches),
            "returned": len(matches),
            "matches": [m.to_dict() for m in matches],
        }
    
    def _remove_route_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """移除路由"""
        table_id = input_data.get("table_id")
        route_id = input_data.get("route_id")
        
        if not table_id or table_id not in self._route_tables:
            return {"operation": "remove_route", "error": "路由表不存在", "success": False}
        
        table = self._route_tables[table_id]
        table.routes = [r for r in table.routes if r.route_id != route_id]
        
        return {"operation": "remove_route", "route_id": route_id, "removed": True}
    
    def _list_tables_operation(self) -> Dict[str, Any]:
        """列出所有路由表"""
        return {
            "operation": "list_tables",
            "tables": [t.to_dict() for t in self._route_tables.values()],
        }
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("四级路由模块校验开始")
        
        checks = []
        
        if isinstance(self._route_tables, dict):
            checks.append("route_tables_valid")
        if isinstance(self._matches, list):
            checks.append("matches_valid")
        if self._state.module_level == ModuleLevel.LEVEL4:
            checks.append("level_valid")
        if self._active_table is not None:
            checks.append("active_table_valid")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="routing_validation",
                message="四级路由模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="routing_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("route_tables", {tid: t.to_dict() for tid, t in self._route_tables.items()})
        snapshot.set_state("active_table", self._active_table.table_id if self._active_table else None)
        snapshot.set_state("match_count", len(self._matches))
        snapshot.metadata["module_type"] = "Level4RoutingModule"
    
    # 公共接口
    def route(self, path: str, method: str = "GET", context: Dict[str, Any] = None) -> Dict[str, Any]:
        """路由请求"""
        return self._route_operation({"path": path, "method": method, "context": context or {}})
    
    def add_route(self, table_id: str, route: Route) -> None:
        """添加路由"""
        if table_id in self._route_tables:
            self._route_tables[table_id].routes.append(route)
    
    def create_route_table(self, name: str, default_target: str = None) -> RouteTable:
        """创建路由表"""
        import uuid
        table = RouteTable(
            table_id=str(uuid.uuid4()),
            name=name,
            default_target=default_target,
        )
        self._route_tables[table.table_id] = table
        return table
    
    def switch_table(self, table_id: str) -> bool:
        """切换路由表"""
        if table_id in self._route_tables:
            self._active_table = self._route_tables[table_id]
            return True
        return False
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level4RoutingModule",
    "Route",
    "RouteMatch",
    "RouteTable",
    "RouteMethod",
    "RouteType",
]
