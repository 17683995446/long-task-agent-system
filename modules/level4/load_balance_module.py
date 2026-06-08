"""
阶段44：四级负载均衡模块
Level4LoadBalanceModule

职责定义：
- 负载均衡
- 健康检查
- 权重管理
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import random

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


class LoadBalanceStrategy(Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    IP_HASH = "ip_hash"


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class BackendServer:
    """后端服务器"""
    server_id: str
    host: str
    port: int
    weight: int = 1
    current_connections: int = 0
    health_status: HealthStatus = HealthStatus.UNKNOWN
    last_health_check: Optional[datetime] = None
    total_requests: int = 0
    failed_requests: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "server_id": self.server_id,
            "host": self.host,
            "port": self.port,
            "weight": self.weight,
            "current_connections": self.current_connections,
            "health_status": self.health_status.value,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "metadata": self.metadata,
        }


@dataclass
class LoadBalancer:
    """负载均衡器"""
    balancer_id: str
    name: str
    strategy: LoadBalanceStrategy
    servers: List[BackendServer] = field(default_factory=list)
    enabled: bool = True
    health_check_interval: int = 30
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "balancer_id": self.balancer_id,
            "name": self.name,
            "strategy": self.strategy.value,
            "server_count": len(self.servers),
            "enabled": self.enabled,
            "health_check_interval": self.health_check_interval,
            "metadata": self.metadata,
            "servers": [s.to_dict() for s in self.servers],
        }


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    check_id: str
    server_id: str
    status: HealthStatus
    timestamp: datetime
    response_time_ms: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "server_id": self.server_id,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


class Level4LoadBalanceModule(ExecuteModuleBase):
    """
    四级负载均衡模块
    
    职责：
    1. 负载均衡
    2. 健康检查
    3. 权重管理
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL4
        self._state.module_name = "Level4LoadBalanceModule"
        self._logger = Logger(f"L4LB_{self.module_id}")
        
        # 负载均衡器存储
        self._balancers: Dict[str, LoadBalancer] = {}
        # 轮询计数器
        self._round_robin_counters: Dict[str, int] = {}
        # 健康检查记录
        self._health_checks: List[HealthCheckResult] = []
        # 加权轮询权重表
        self._weighted_indices: Dict[str, List[int]] = {}
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("四级负载均衡模块初始化开始")
            
            # 1. 加载配置
            self._load_config(request)
            
            # 2. 初始化存储
            self._balancers = {}
            self._round_robin_counters = {}
            self._health_checks = []
            self._weighted_indices = {}
            
            self._logger.info("四级负载均衡模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="四级负载均衡模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级负载均衡模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L4LB_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "default_strategy": "round_robin",
            "health_check_enabled": True,
            "health_check_timeout": 5,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("load_balance_config", {})
            self._config.update(custom_config)
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("四级负载均衡模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "create_balancer")
            
            if operation == "create_balancer":
                result = self._create_balancer_operation(input_data)
            elif operation == "add_server":
                result = self._add_server_operation(input_data)
            elif operation == "select_server":
                result = self._select_server_operation(input_data)
            elif operation == "health_check":
                result = self._health_check_operation(input_data)
            elif operation == "get_balancer":
                result = self._get_balancer_operation(input_data)
            elif operation == "remove_server":
                result = self._remove_server_operation(input_data)
            elif operation == "update_weight":
                result = self._update_weight_operation(input_data)
            elif operation == "get_stats":
                result = self._get_stats_operation()
            else:
                result = {"error": f"未知操作: {operation}"}
            
            self._logger.info("四级负载均衡模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level4LoadBalanceModule",
                    "load_balance_summary": {
                        "total_balancers": len(self._balancers),
                        "total_servers": sum(len(b.servers) for b in self._balancers.values()),
                        "total_health_checks": len(self._health_checks),
                    },
                },
                message="四级负载均衡模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级负载均衡模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L4LB_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _create_balancer_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建负载均衡器"""
        import uuid
        
        balancer_id = str(uuid.uuid4())
        strategy = LoadBalanceStrategy(input_data.get("strategy", self._config.get("default_strategy", "round_robin")))
        
        balancer = LoadBalancer(
            balancer_id=balancer_id,
            name=input_data.get("name", f"balancer_{balancer_id[:8]}"),
            strategy=strategy,
            health_check_interval=input_data.get("health_check_interval", 30),
            metadata=input_data.get("metadata", {}),
        )
        self._balancers[balancer_id] = balancer
        self._round_robin_counters[balancer_id] = 0
        self._weighted_indices[balancer_id] = []
        
        return {
            "operation": "create_balancer",
            "balancer_id": balancer_id,
            "strategy": strategy.value,
            "created": True,
        }
    
    def _add_server_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加服务器"""
        balancer_id = input_data.get("balancer_id")
        if not balancer_id or balancer_id not in self._balancers:
            return {"operation": "add_server", "error": "负载均衡器不存在", "success": False}
        
        balancer = self._balancers[balancer_id]
        
        server = BackendServer(
            server_id=input_data.get("server_id", ""),
            host=input_data.get("host", ""),
            port=input_data.get("port", 80),
            weight=input_data.get("weight", 1),
            metadata=input_data.get("metadata", {}),
        )
        balancer.servers.append(server)
        
        # 更新加权轮询索引
        self._update_weighted_indices(balancer_id)
        
        return {
            "operation": "add_server",
            "balancer_id": balancer_id,
            "server_id": server.server_id,
            "added": True,
        }
    
    def _update_weighted_indices(self, balancer_id: str) -> None:
        """更新加权轮询索引"""
        balancer = self._balancers[balancer_id]
        indices = []
        for i, server in enumerate(balancer.servers):
            if server.health_status != HealthStatus.UNHEALTHY:
                indices.extend([i] * server.weight)
        self._weighted_indices[balancer_id] = indices
    
    def _select_server_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """选择服务器"""
        balancer_id = input_data.get("balancer_id")
        client_ip = input_data.get("client_ip", "")
        
        if not balancer_id or balancer_id not in self._balancers:
            return {"operation": "select_server", "error": "负载均衡器不存在", "success": False}
        
        balancer = self._balancers[balancer_id]
        
        # 过滤健康的服务器
        healthy_servers = [s for s in balancer.servers if s.health_status != HealthStatus.UNHEALTHY]
        
        if not healthy_servers:
            return {"operation": "select_server", "error": "没有可用的健康服务器", "success": False}
        
        if balancer.strategy == LoadBalanceStrategy.ROUND_ROBIN:
            server = self._round_robin_select(balancer_id, healthy_servers)
        elif balancer.strategy == LoadBalanceStrategy.RANDOM:
            server = random.choice(healthy_servers)
        elif balancer.strategy == LoadBalanceStrategy.WEIGHTED_ROUND_ROBIN:
            server = self._weighted_round_robin_select(balancer_id, healthy_servers)
        elif balancer.strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            server = min(healthy_servers, key=lambda s: s.current_connections)
        elif balancer.strategy == LoadBalanceStrategy.IP_HASH:
            server = self._ip_hash_select(client_ip, healthy_servers)
        else:
            server = random.choice(healthy_servers)
        
        # 更新连接数
        server.current_connections += 1
        server.total_requests += 1
        
        return {
            "operation": "select_server",
            "balancer_id": balancer_id,
            "server_id": server.server_id,
            "host": server.host,
            "port": server.port,
            "strategy": balancer.strategy.value,
        }
    
    def _round_robin_select(self, balancer_id: str, servers: List[BackendServer]) -> BackendServer:
        """轮询选择"""
        counter = self._round_robin_counters.get(balancer_id, 0)
        server = servers[counter % len(servers)]
        self._round_robin_counters[balancer_id] = (counter + 1) % len(servers)
        return server
    
    def _weighted_round_robin_select(self, balancer_id: str, servers: List[BackendServer]) -> BackendServer:
        """加权轮询选择"""
        indices = self._weighted_indices.get(balancer_id, [])
        if not indices:
            return random.choice(servers)
        
        counter = self._round_robin_counters.get(balancer_id, 0)
        idx = indices[counter % len(indices)]
        self._round_robin_counters[balancer_id] = (counter + 1) % len(indices)
        return servers[idx]
    
    def _ip_hash_select(self, client_ip: str, servers: List[BackendServer]) -> BackendServer:
        """IP哈希选择"""
        if not client_ip:
            return random.choice(servers)
        
        # 简单哈希
        hash_value = sum(ord(c) for c in client_ip)
        return servers[hash_value % len(servers)]
    
    def _health_check_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行健康检查"""
        import uuid
        
        balancer_id = input_data.get("balancer_id")
        server_id = input_data.get("server_id")
        
        if not balancer_id or balancer_id not in self._balancers:
            return {"operation": "health_check", "error": "负载均衡器不存在", "success": False}
        
        balancer = self._balancers[balancer_id]
        
        if server_id:
            # 检查单个服务器
            server = next((s for s in balancer.servers if s.server_id == server_id), None)
            if not server:
                return {"operation": "health_check", "error": "服务器不存在", "success": False}
            
            result = self._check_server_health(server)
            self._health_checks.append(result)
            
            return {
                "operation": "health_check",
                "server_id": server_id,
                "status": result.status.value,
                "response_time_ms": result.response_time_ms,
            }
        else:
            # 检查所有服务器
            results = []
            for server in balancer.servers:
                result = self._check_server_health(server)
                self._health_checks.append(result)
                results.append({
                    "server_id": server.server_id,
                    "status": result.status.value,
                    "response_time_ms": result.response_time_ms,
                })
            
            # 更新加权索引
            self._update_weighted_indices(balancer_id)
            
            return {
                "operation": "health_check",
                "results": results,
                "checked_count": len(results),
            }
    
    def _check_server_health(self, server: BackendServer) -> HealthCheckResult:
        """检查服务器健康状态"""
        import uuid
        import time
        
        start_time = time.time()
        
        # 模拟健康检查
        # 根据失败率决定健康状态
        failure_rate = server.failed_requests / server.total_requests if server.total_requests > 0 else 0
        
        if failure_rate > 0.5:
            status = HealthStatus.UNHEALTHY
            error_message = f"Failure rate too high: {failure_rate:.2%}"
        elif failure_rate > 0.2:
            status = HealthStatus.DEGRADED
            error_message = f"Elevated failure rate: {failure_rate:.2%}"
        else:
            status = HealthStatus.HEALTHY
            error_message = None
        
        response_time = (time.time() - start_time) * 1000 + random.uniform(1, 50)
        
        server.health_status = status
        server.last_health_check = datetime.now()
        
        return HealthCheckResult(
            check_id=str(uuid.uuid4()),
            server_id=server.server_id,
            status=status,
            timestamp=datetime.now(),
            response_time_ms=response_time,
            error_message=error_message,
        )
    
    def _get_balancer_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取负载均衡器信息"""
        balancer_id = input_data.get("balancer_id")
        if not balancer_id or balancer_id not in self._balancers:
            return {"operation": "get_balancer", "error": "负载均衡器不存在"}
        
        balancer = self._balancers[balancer_id]
        return {
            "operation": "get_balancer",
            "balancer": balancer.to_dict(),
        }
    
    def _remove_server_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """移除服务器"""
        balancer_id = input_data.get("balancer_id")
        server_id = input_data.get("server_id")
        
        if not balancer_id or balancer_id not in self._balancers:
            return {"operation": "remove_server", "error": "负载均衡器不存在", "success": False}
        
        balancer = self._balancers[balancer_id]
        balancer.servers = [s for s in balancer.servers if s.server_id != server_id]
        
        # 更新加权索引
        self._update_weighted_indices(balancer_id)
        
        return {
            "operation": "remove_server",
            "balancer_id": balancer_id,
            "server_id": server_id,
            "removed": True,
        }
    
    def _update_weight_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新服务器权重"""
        balancer_id = input_data.get("balancer_id")
        server_id = input_data.get("server_id")
        weight = input_data.get("weight", 1)
        
        if not balancer_id or balancer_id not in self._balancers:
            return {"operation": "update_weight", "error": "负载均衡器不存在", "success": False}
        
        balancer = self._balancers[balancer_id]
        server = next((s for s in balancer.servers if s.server_id == server_id), None)
        
        if not server:
            return {"operation": "update_weight", "error": "服务器不存在", "success": False}
        
        server.weight = weight
        self._update_weighted_indices(balancer_id)
        
        return {
            "operation": "update_weight",
            "balancer_id": balancer_id,
            "server_id": server_id,
            "new_weight": weight,
            "success": True,
        }
    
    def _get_stats_operation(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_servers = sum(len(b.servers) for b in self._balancers.values())
        healthy_servers = sum(
            sum(1 for s in b.servers if s.health_status == HealthStatus.HEALTHY)
            for b in self._balancers.values()
        )
        
        return {
            "operation": "get_stats",
            "total_balancers": len(self._balancers),
            "total_servers": total_servers,
            "healthy_servers": healthy_servers,
            "unhealthy_servers": total_servers - healthy_servers,
            "total_requests": sum(s.total_requests for b in self._balancers.values() for s in b.servers),
            "total_health_checks": len(self._health_checks),
        }
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("四级负载均衡模块校验开始")
        
        checks = []
        
        if isinstance(self._balancers, dict):
            checks.append("balancers_valid")
        if isinstance(self._health_checks, list):
            checks.append("health_checks_valid")
        if self._state.module_level == ModuleLevel.LEVEL4:
            checks.append("level_valid")
        if isinstance(self._round_robin_counters, dict):
            checks.append("counters_valid")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="load_balance_validation",
                message="四级负载均衡模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="load_balance_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("balancers", {bid: b.to_dict() for bid, b in self._balancers.items()})
        snapshot.set_state("health_check_count", len(self._health_checks))
        snapshot.metadata["module_type"] = "Level4LoadBalanceModule"
    
    # 公共接口
    def create_balancer(self, name: str, strategy: LoadBalanceStrategy = None) -> LoadBalancer:
        """创建负载均衡器"""
        import uuid
        balancer = LoadBalancer(
            balancer_id=str(uuid.uuid4()),
            name=name,
            strategy=strategy or LoadBalanceStrategy.ROUND_ROBIN,
        )
        self._balancers[balancer.balancer_id] = balancer
        self._round_robin_counters[balancer.balancer_id] = 0
        return balancer
    
    def select_server(self, balancer_id: str, client_ip: str = "") -> Optional[BackendServer]:
        """选择服务器"""
        result = self._select_server_operation({"balancer_id": balancer_id, "client_ip": client_ip})
        if result.get("success") is False:
            return None
        server_id = result.get("server_id")
        balancer = self._balancers.get(balancer_id)
        if balancer:
            return next((s for s in balancer.servers if s.server_id == server_id), None)
        return None
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level4LoadBalanceModule",
    "BackendServer",
    "LoadBalancer",
    "HealthCheckResult",
    "LoadBalanceStrategy",
    "HealthStatus",
]
