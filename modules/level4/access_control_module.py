"""
阶段41：四级访问控制模块
Level4AccessControlModule

职责定义：
- 访问控制
- 权限管理
- 角色管理
"""

from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

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


class Permission(Enum):
    """权限枚举"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"
    CREATE = "create"
    UPDATE = "update"


class AccessDecision(Enum):
    """访问决策"""
    ALLOW = "allow"
    DENY = "deny"
    ABSTAIN = "abstain"


@dataclass
class Role:
    """角色定义"""
    role_id: str
    name: str
    description: str = ""
    permissions: List[Permission] = field(default_factory=list)
    parent_roles: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "name": self.name,
            "description": self.description,
            "permissions": [p.value for p in self.permissions],
            "parent_roles": self.parent_roles,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class AccessPolicy:
    """访问策略"""
    policy_id: str
    name: str
    resource: str
    action: str
    decision: AccessDecision
    conditions: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "resource": self.resource,
            "action": self.action,
            "decision": self.decision.value,
            "conditions": self.conditions,
            "priority": self.priority,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }


@dataclass
class AccessRequest:
    """访问请求"""
    request_id: str
    subject: str
    resource: str
    action: str
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "subject": self.subject,
            "resource": self.resource,
            "action": self.action,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AccessLog:
    """访问日志"""
    log_id: str
    request_id: str
    subject: str
    resource: str
    action: str
    decision: AccessDecision
    timestamp: datetime
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "request_id": self.request_id,
            "subject": self.subject,
            "resource": self.resource,
            "action": self.action,
            "decision": self.decision.value,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
            "metadata": self.metadata,
        }


class Level4AccessControlModule(ExecuteModuleBase):
    """
    四级访问控制模块
    
    职责：
    1. 访问控制决策
    2. 权限管理
    3. 角色管理
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL4
        self._state.module_name = "Level4AccessControlModule"
        self._logger = Logger(f"L4AC_{self.module_id}")
        
        # 角色存储
        self._roles: Dict[str, Role] = {}
        # 用户角色映射
        self._user_roles: Dict[str, List[str]] = {}
        # 访问策略
        self._policies: List[AccessPolicy] = []
        # 访问日志
        self._access_logs: List[AccessLog] = []
        # 默认决策
        self._default_decision: AccessDecision = AccessDecision.DENY
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("四级访问控制模块初始化开始")
            
            # 1. 加载配置
            self._load_config(request)
            
            # 2. 初始化存储
            self._roles = {}
            self._user_roles = {}
            self._policies = []
            self._access_logs = []
            
            # 3. 加载默认角色和策略
            self._load_default_roles()
            self._load_default_policies()
            
            self._logger.info("四级访问控制模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="四级访问控制模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级访问控制模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L4AC_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "default_decision": "deny",
            "log_access": True,
            "max_logs": 10000,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("access_control_config", {})
            self._config.update(custom_config)
        
        self._default_decision = AccessDecision(self._config.get("default_decision", "deny"))
    
    def _load_default_roles(self) -> None:
        """加载默认角色"""
        default_roles = [
            Role(
                role_id="role_admin",
                name="admin",
                description="管理员角色，拥有所有权限",
                permissions=list(Permission),
            ),
            Role(
                role_id="role_reader",
                name="reader",
                description="只读角色",
                permissions=[Permission.READ],
            ),
            Role(
                role_id="role_writer",
                name="writer",
                description="读写角色",
                permissions=[Permission.READ, Permission.WRITE, Permission.CREATE, Permission.UPDATE],
            ),
            Role(
                role_id="role_executor",
                name="executor",
                description="执行角色",
                permissions=[Permission.READ, Permission.EXECUTE],
            ),
        ]
        for role in default_roles:
            self._roles[role.role_id] = role
    
    def _load_default_policies(self) -> None:
        """加载默认策略"""
        default_policies = [
            AccessPolicy(
                policy_id="policy_admin_all",
                name="管理员全权限",
                resource="*",
                action="*",
                decision=AccessDecision.ALLOW,
                conditions={"role": "admin"},
                priority=100,
            ),
            AccessPolicy(
                policy_id="policy_deny_guest",
                name="拒绝访客删除",
                resource="*",
                action="delete",
                decision=AccessDecision.DENY,
                conditions={"role": "guest"},
                priority=90,
            ),
        ]
        self._policies.extend(default_policies)
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("四级访问控制模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "check_access")
            
            if operation == "check_access":
                result = self._check_access_operation(input_data)
            elif operation == "add_role":
                result = self._add_role_operation(input_data)
            elif operation == "assign_role":
                result = self._assign_role_operation(input_data)
            elif operation == "add_policy":
                result = self._add_policy_operation(input_data)
            elif operation == "get_user_permissions":
                result = self._get_user_permissions_operation(input_data)
            elif operation == "get_roles":
                result = self._get_roles_operation()
            elif operation == "get_access_logs":
                result = self._get_access_logs_operation(input_data)
            elif operation == "revoke_role":
                result = self._revoke_role_operation(input_data)
            else:
                result = {"error": f"未知操作: {operation}"}
            
            self._logger.info("四级访问控制模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level4AccessControlModule",
                    "access_summary": {
                        "total_roles": len(self._roles),
                        "total_policies": len(self._policies),
                        "total_logs": len(self._access_logs),
                        "total_users": len(self._user_roles),
                    },
                },
                message="四级访问控制模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级访问控制模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L4AC_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _check_access_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查访问权限"""
        import uuid
        
        subject = input_data.get("subject", "anonymous")
        resource = input_data.get("resource", "")
        action = input_data.get("action", "")
        context = input_data.get("context", {})
        
        access_request = AccessRequest(
            request_id=str(uuid.uuid4()),
            subject=subject,
            resource=resource,
            action=action,
            context=context,
        )
        
        # 评估策略
        decision = self._evaluate_policies(access_request)
        
        # 记录访问日志
        if self._config.get("log_access", True):
            self._log_access(access_request, decision, "policy_evaluation")
        
        return {
            "operation": "check_access",
            "request_id": access_request.request_id,
            "subject": subject,
            "resource": resource,
            "action": action,
            "decision": decision.value,
            "allowed": decision == AccessDecision.ALLOW,
        }
    
    def _evaluate_policies(self, access_request: AccessRequest) -> AccessDecision:
        """评估策略"""
        # 按优先级排序
        sorted_policies = sorted(self._policies, key=lambda p: p.priority, reverse=True)
        
        for policy in sorted_policies:
            if not policy.enabled:
                continue
            
            # 检查资源匹配
            if not self._match_pattern(policy.resource, access_request.resource):
                continue
            
            # 检查动作匹配
            if not self._match_pattern(policy.action, access_request.action):
                continue
            
            # 检查条件
            if self._evaluate_conditions(policy.conditions, access_request):
                return policy.decision
        
        # 检查角色权限
        user_role_ids = self._user_roles.get(access_request.subject, [])
        for role_id in user_role_ids:
            if role_id in self._roles:
                role = self._roles[role_id]
                for perm in role.permissions:
                    if perm.value == access_request.action or perm == Permission.ADMIN:
                        return AccessDecision.ALLOW
        
        return self._default_decision
    
    def _match_pattern(self, pattern: str, value: str) -> bool:
        """模式匹配"""
        if pattern == "*":
            return True
        return pattern == value
    
    def _evaluate_conditions(self, conditions: Dict[str, Any], access_request: AccessRequest) -> bool:
        """评估条件"""
        if not conditions:
            return True
        
        for key, expected in conditions.items():
            if key == "role":
                user_roles = self._user_roles.get(access_request.subject, [])
                role_names = [self._roles[r].name for r in user_roles if r in self._roles]
                if expected not in role_names:
                    return False
            elif key == "time_after":
                current_hour = access_request.timestamp.hour
                if current_hour < expected:
                    return False
            elif key == "time_before":
                current_hour = access_request.timestamp.hour
                if current_hour > expected:
                    return False
            else:
                actual = access_request.context.get(key)
                if actual != expected:
                    return False
        
        return True
    
    def _add_role_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加角色"""
        role_id = input_data.get("role_id")
        permissions = [Permission(p) for p in input_data.get("permissions", [])]
        
        role = Role(
            role_id=role_id,
            name=input_data.get("name", role_id),
            description=input_data.get("description", ""),
            permissions=permissions,
            parent_roles=input_data.get("parent_roles", []),
            metadata=input_data.get("metadata", {}),
        )
        self._roles[role_id] = role
        
        return {
            "operation": "add_role",
            "role_id": role_id,
            "added": True,
        }
    
    def _assign_role_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """分配角色给用户"""
        user_id = input_data.get("user_id")
        role_id = input_data.get("role_id")
        
        if role_id not in self._roles:
            return {"operation": "assign_role", "error": f"角色 {role_id} 不存在", "success": False}
        
        if user_id not in self._user_roles:
            self._user_roles[user_id] = []
        
        if role_id not in self._user_roles[user_id]:
            self._user_roles[user_id].append(role_id)
        
        return {
            "operation": "assign_role",
            "user_id": user_id,
            "role_id": role_id,
            "assigned": True,
        }
    
    def _add_policy_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加策略"""
        import uuid
        
        policy = AccessPolicy(
            policy_id=str(uuid.uuid4()),
            name=input_data.get("name", ""),
            resource=input_data.get("resource", "*"),
            action=input_data.get("action", "*"),
            decision=AccessDecision(input_data.get("decision", "allow")),
            conditions=input_data.get("conditions", {}),
            priority=input_data.get("priority", 0),
            enabled=input_data.get("enabled", True),
            metadata=input_data.get("metadata", {}),
        )
        self._policies.append(policy)
        
        return {
            "operation": "add_policy",
            "policy_id": policy.policy_id,
            "added": True,
        }
    
    def _get_user_permissions_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取用户权限"""
        user_id = input_data.get("user_id")
        role_ids = self._user_roles.get(user_id, [])
        
        permissions: Set[str] = set()
        role_details = []
        
        for role_id in role_ids:
            if role_id in self._roles:
                role = self._roles[role_id]
                for perm in role.permissions:
                    permissions.add(perm.value)
                role_details.append(role.to_dict())
        
        return {
            "operation": "get_user_permissions",
            "user_id": user_id,
            "roles": role_details,
            "permissions": list(permissions),
        }
    
    def _get_roles_operation(self) -> Dict[str, Any]:
        """获取所有角色"""
        return {
            "operation": "get_roles",
            "roles": [role.to_dict() for role in self._roles.values()],
        }
    
    def _get_access_logs_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取访问日志"""
        limit = input_data.get("limit", 100)
        subject = input_data.get("subject")
        
        logs = self._access_logs
        if subject:
            logs = [log for log in logs if log.subject == subject]
        
        logs = sorted(logs, key=lambda l: l.timestamp, reverse=True)[:limit]
        
        return {
            "operation": "get_access_logs",
            "total": len(self._access_logs),
            "returned": len(logs),
            "logs": [log.to_dict() for log in logs],
        }
    
    def _revoke_role_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """撤销用户角色"""
        user_id = input_data.get("user_id")
        role_id = input_data.get("role_id")
        
        if user_id in self._user_roles and role_id in self._user_roles[user_id]:
            self._user_roles[user_id].remove(role_id)
        
        return {
            "operation": "revoke_role",
            "user_id": user_id,
            "role_id": role_id,
            "revoked": True,
        }
    
    def _log_access(self, access_request: AccessRequest, decision: AccessDecision, reason: str) -> None:
        """记录访问日志"""
        import uuid
        
        log = AccessLog(
            log_id=str(uuid.uuid4()),
            request_id=access_request.request_id,
            subject=access_request.subject,
            resource=access_request.resource,
            action=access_request.action,
            decision=decision,
            timestamp=datetime.now(),
            reason=reason,
        )
        self._access_logs.append(log)
        
        # 限制日志数量
        max_logs = self._config.get("max_logs", 10000)
        if len(self._access_logs) > max_logs:
            self._access_logs = self._access_logs[-max_logs:]
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("四级访问控制模块校验开始")
        
        checks = []
        
        if isinstance(self._roles, dict):
            checks.append("roles_valid")
        if isinstance(self._policies, list):
            checks.append("policies_valid")
        if self._state.module_level == ModuleLevel.LEVEL4:
            checks.append("level_valid")
        if isinstance(self._access_logs, list):
            checks.append("logs_valid")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="access_control_validation",
                message="四级访问控制模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="access_control_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("roles", {rid: r.to_dict() for rid, r in self._roles.items()})
        snapshot.set_state("user_roles", self._user_roles)
        snapshot.set_state("policies", [p.to_dict() for p in self._policies])
        snapshot.set_state("log_count", len(self._access_logs))
        snapshot.metadata["module_type"] = "Level4AccessControlModule"
    
    # 公共接口
    def check_access(self, subject: str, resource: str, action: str,
                     context: Dict[str, Any] = None) -> AccessDecision:
        """检查访问权限"""
        import uuid
        access_request = AccessRequest(
            request_id=str(uuid.uuid4()),
            subject=subject,
            resource=resource,
            action=action,
            context=context or {},
        )
        return self._evaluate_policies(access_request)
    
    def add_role(self, role: Role) -> None:
        """添加角色"""
        self._roles[role.role_id] = role
    
    def assign_role(self, user_id: str, role_id: str) -> None:
        """分配角色"""
        if user_id not in self._user_roles:
            self._user_roles[user_id] = []
        if role_id not in self._user_roles[user_id]:
            self._user_roles[user_id].append(role_id)
    
    def get_user_permissions(self, user_id: str) -> Set[str]:
        """获取用户权限"""
        role_ids = self._user_roles.get(user_id, [])
        permissions: Set[str] = set()
        for role_id in role_ids:
            if role_id in self._roles:
                for perm in self._roles[role_id].permissions:
                    permissions.add(perm.value)
        return permissions
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._default_decision = AccessDecision(self._config.get("default_decision", "deny"))
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level4AccessControlModule",
    "Role",
    "AccessPolicy",
    "AccessRequest",
    "AccessLog",
    "Permission",
    "AccessDecision",
]
