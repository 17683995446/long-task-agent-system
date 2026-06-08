"""
阶段35：三级安全模块
Level3SecurityModule

职责定义：
- 身份验证与授权
- 权限检查
- 安全策略执行
- 安全审计日志
"""

from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import secrets

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


class Permission(Enum):
    """权限枚举"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ADMIN = "admin"


class SecurityLevel(Enum):
    """安全级别"""
    PUBLIC = 1
    INTERNAL = 2
    CONFIDENTIAL = 3
    SECRET = 4
    TOP_SECRET = 5


@dataclass
class Identity:
    """身份定义"""
    identity_id: str
    name: str
    credentials_hash: str
    security_level: SecurityLevel
    permissions: Set[Permission] = field(default_factory=set)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_authenticated: Optional[str] = None
    failed_attempts: int = 0
    locked_until: Optional[str] = None


@dataclass
class SecurityAuditRecord:
    """安全审计记录"""
    record_id: str
    timestamp: str
    identity_id: Optional[str]
    action: str
    resource: str
    result: str  # "allowed" | "denied" | "error"
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class Level3SecurityModule(ControlModuleBase):
    """
    三级安全模块
    
    职责：
    1. 身份验证（用户名/密码、令牌）
    2. 权限检查（RBAC模型）
    3. 安全策略执行（访问控制、限流）
    4. 安全审计日志
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL3
        self._state.module_name = "Level3SecurityModule"
        self._logger = Logger(f"L3S_{self.module_id}")
        
        # 身份存储
        self._identities: Dict[str, Identity] = {}
        
        # 审计日志
        self._audit_log: List[SecurityAuditRecord] = []
        
        # 安全配置
        self._security_config: Dict[str, Any] = {
            "max_failed_attempts": 5,
            "lockout_duration_minutes": 30,
            "session_timeout_minutes": 60,
            "require_strong_password": True,
        }
        
        # 访问计数（用于限流）
        self._access_counts: Dict[str, List[datetime]] = {}
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化安全模块"""
        try:
            self._logger.info("安全模块初始化开始")
            
            # 1. 加载安全配置
            if request.task_param:
                custom_config = request.task_param.get_param("security_config", {})
                self._security_config.update(custom_config)
            
            # 2. 加载默认身份
            self._load_default_identities()
            
            self._logger.info(f"安全模块初始化完成，身份数量: {len(self._identities)}")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message=f"安全模块初始化成功，身份数量: {len(self._identities)}"
            )
            
        except Exception as e:
            self._logger.error(f"安全模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L3S_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_default_identities(self) -> None:
        """加载默认身份"""
        # 创建系统管理员身份
        admin = Identity(
            identity_id="system_admin",
            name="系统管理员",
            credentials_hash=self._hash_credentials("admin_password"),
            security_level=SecurityLevel.TOP_SECRET,
            permissions={Permission.READ, Permission.WRITE, Permission.EXECUTE, Permission.DELETE, Permission.ADMIN},
        )
        self._identities[admin.identity_id] = admin
        
        # 创建只读用户身份
        readonly = Identity(
            identity_id="readonly_user",
            name="只读用户",
            credentials_hash=self._hash_credentials("readonly_password"),
            security_level=SecurityLevel.INTERNAL,
            permissions={Permission.READ},
        )
        self._identities[readonly.identity_id] = readonly
    
    def _hash_credentials(self, credentials: str) -> str:
        """哈希凭证"""
        salt = secrets.token_hex(16)
        return hashlib.sha256(f"{credentials}{salt}".encode()).hexdigest() + ":" + salt
    
    def _verify_credentials(self, credentials: str, stored_hash: str) -> bool:
        """验证凭证"""
        try:
            hash_value, salt = stored_hash.split(":")
            computed = hashlib.sha256(f"{credentials}{salt}".encode()).hexdigest()
            return secrets.compare_digest(computed, hash_value)
        except ValueError:
            return False
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行安全策略"""
        self._logger.info("安全模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 1. 解析安全请求
            security_request = self._parse_security_request(request)
            
            # 2. 执行身份验证
            auth_result = self._authenticate(security_request)
            
            # 3. 执行权限检查
            authz_result = self._authorize(security_request, auth_result)
            
            # 4. 执行访问控制
            access_result = self._check_access_control(security_request)
            
            # 5. 记录审计日志
            self._record_audit(security_request, auth_result, authz_result, access_result)
            
            self._logger.info(f"安全策略执行完成: auth={auth_result['success']}, authz={authz_result['allowed']}")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "authentication": auth_result,
                    "authorization": authz_result,
                    "access_control": access_result,
                    "module": "Level3SecurityModule",
                },
                message="安全模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"安全模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L3S_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _parse_security_request(self, request: ExecutionRequest) -> Dict[str, Any]:
        """解析安全请求"""
        data = request.module_input.data if request.module_input and hasattr(request.module_input, 'data') else {}
        return {
            "identity_id": data.get("identity_id"),
            "credentials": data.get("credentials"),
            "action": data.get("action", "read"),
            "resource": data.get("resource", "default"),
            "requested_permissions": data.get("permissions", ["read"]),
        }
    
    def _authenticate(self, security_request: Dict[str, Any]) -> Dict[str, Any]:
        """身份验证"""
        identity_id = security_request.get("identity_id")
        credentials = security_request.get("credentials")
        
        if not identity_id or not credentials:
            return {"success": False, "reason": "缺少身份凭证", "identity": None}
        
        identity = self._identities.get(identity_id)
        if not identity:
            return {"success": False, "reason": "身份不存在", "identity": None}
        
        # 检查是否被锁定
        if identity.locked_until:
            locked_until = datetime.fromisoformat(identity.locked_until)
            if datetime.now() < locked_until:
                return {"success": False, "reason": "身份已锁定", "identity": None}
        
        # 验证凭证
        if self._verify_credentials(credentials, identity.credentials_hash):
            identity.last_authenticated = datetime.now().isoformat()
            identity.failed_attempts = 0
            return {
                "success": True,
                "reason": "验证成功",
                "identity": {
                    "id": identity.identity_id,
                    "name": identity.name,
                    "level": identity.security_level.name,
                }
            }
        else:
            identity.failed_attempts += 1
            max_attempts = self._security_config.get("max_failed_attempts", 5)
            
            if identity.failed_attempts >= max_attempts:
                lockout_minutes = self._security_config.get("lockout_duration_minutes", 30)
                identity.locked_until = (datetime.now() + timedelta(minutes=lockout_minutes)).isoformat()
                return {"success": False, "reason": f"身份已锁定 {lockout_minutes} 分钟", "identity": None}
            
            return {
                "success": False,
                "reason": f"凭证错误，剩余尝试次数: {max_attempts - identity.failed_attempts}",
                "identity": None
            }
    
    def _authorize(self, security_request: Dict[str, Any], auth_result: Dict[str, Any]) -> Dict[str, Any]:
        """权限检查"""
        if not auth_result["success"]:
            return {"allowed": False, "reason": "未通过身份验证", "permissions": []}
        
        identity_id = security_request.get("identity_id")
        requested_perms = security_request.get("requested_permissions", [])
        
        identity = self._identities.get(identity_id)
        if not identity:
            return {"allowed": False, "reason": "身份不存在", "permissions": []}
        
        # 检查权限
        granted = []
        denied = []
        
        for perm_name in requested_perms:
            try:
                perm = Permission(perm_name)
                if perm in identity.permissions:
                    granted.append(perm_name)
                else:
                    denied.append(perm_name)
            except ValueError:
                denied.append(perm_name)
        
        allowed = len(denied) == 0
        
        return {
            "allowed": allowed,
            "reason": "权限检查通过" if allowed else f"缺少权限: {denied}",
            "granted_permissions": granted,
            "denied_permissions": denied,
        }
    
    def _check_access_control(self, security_request: Dict[str, Any]) -> Dict[str, Any]:
        """访问控制检查"""
        resource = security_request.get("resource", "default")
        identity_id = security_request.get("identity_id")
        
        # 限流检查
        now = datetime.now()
        if identity_id not in self._access_counts:
            self._access_counts[identity_id] = []
        
        # 清理过期记录（1分钟前）
        self._access_counts[identity_id] = [
            t for t in self._access_counts[identity_id]
            if now - t < timedelta(minutes=1)
        ]
        
        # 检查是否超过限流
        max_requests = self._security_config.get("max_requests_per_minute", 100)
        if len(self._access_counts[identity_id]) >= max_requests:
            return {
                "allowed": False,
                "reason": f"超过限流: {max_requests} 请求/分钟",
                "current_count": len(self._access_counts[identity_id]),
            }
        
        self._access_counts[identity_id].append(now)
        
        return {
            "allowed": True,
            "reason": "访问控制通过",
            "current_count": len(self._access_counts[identity_id]),
        }
    
    def _record_audit(
        self,
        security_request: Dict[str, Any],
        auth_result: Dict[str, Any],
        authz_result: Dict[str, Any],
        access_result: Dict[str, Any]
    ) -> None:
        """记录审计日志"""
        record = SecurityAuditRecord(
            record_id=f"audit_{datetime.now().isoformat()}_{secrets.token_hex(4)}",
            timestamp=datetime.now().isoformat(),
            identity_id=security_request.get("identity_id"),
            action=security_request.get("action", "unknown"),
            resource=security_request.get("resource", "default"),
            result="allowed" if (auth_result["success"] and authz_result["allowed"] and access_result["allowed"]) else "denied",
            reason=f"auth:{auth_result['reason']}; authz:{authz_result['reason']}; access:{access_result['reason']}",
            metadata={
                "auth_success": auth_result["success"],
                "authz_allowed": authz_result["allowed"],
                "access_allowed": access_result["allowed"],
            }
        )
        self._audit_log.append(record)
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验安全模块"""
        self._logger.info("安全模块校验开始")
        
        checks = []
        
        # 1. 校验身份存储
        if isinstance(self._identities, dict):
            checks.append("identity_store_valid")
        
        # 2. 校验审计日志
        if isinstance(self._audit_log, list):
            checks.append("audit_log_valid")
        
        # 3. 校验安全配置
        required_keys = ["max_failed_attempts", "lockout_duration_minutes", "session_timeout_minutes"]
        if all(k in self._security_config for k in required_keys):
            checks.append("security_config_valid")
        
        # 4. 校验模块层级
        if self._state.module_level == ModuleLevel.LEVEL3:
            checks.append("level_valid")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="security_validation",
                message=f"安全模块校验通过，身份数量: {len(self._identities)}"
            )
        else:
            return CheckResult.failed_result(
                check_type="security_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建安全模块快照"""
        snapshot.set_state("identities", {
            iid: {
                "name": i.name,
                "security_level": i.security_level.name,
                "permissions": [p.value for p in i.permissions],
                "failed_attempts": i.failed_attempts,
            }
            for iid, i in self._identities.items()
        })
        snapshot.set_state("audit_log_count", len(self._audit_log))
        snapshot.set_state("security_config", self._security_config)
        snapshot.metadata["module_type"] = "Level3SecurityModule"
        snapshot.metadata["identity_count"] = len(self._identities)
    
    # =====================================================================
    # 安全管理公共接口
    # =====================================================================
    
    def register_identity(
        self,
        identity_id: str,
        name: str,
        credentials: str,
        security_level: str = "INTERNAL",
        permissions: List[str] = None,
    ) -> bool:
        """
        注册新身份
        
        Args:
            identity_id: 身份唯一标识
            name: 身份名称
            credentials: 凭证（密码）
            security_level: 安全级别 (PUBLIC/INTERNAL/CONFIDENTIAL/SECRET/TOP_SECRET)
            permissions: 权限列表 (read/write/execute/delete/admin)
            
        Returns:
            bool: 是否注册成功
        """
        try:
            if identity_id in self._identities:
                self._logger.warning(f"身份已存在: {identity_id}")
                return False
            
            level = SecurityLevel[security_level.upper()]
            perms = {Permission(p) for p in (permissions or ["read"])}
            
            identity = Identity(
                identity_id=identity_id,
                name=name,
                credentials_hash=self._hash_credentials(credentials),
                security_level=level,
                permissions=perms,
            )
            self._identities[identity_id] = identity
            
            self._logger.info(f"身份注册成功: {identity_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"身份注册失败: {e}")
            return False
    
    def revoke_identity(self, identity_id: str) -> bool:
        """撤销身份"""
        if identity_id in self._identities:
            del self._identities[identity_id]
            self._logger.info(f"身份已撤销: {identity_id}")
            return True
        return False
    
    def get_identity(self, identity_id: str) -> Optional[Identity]:
        """获取身份"""
        return self._identities.get(identity_id)
    
    def get_audit_log(
        self,
        identity_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> List[SecurityAuditRecord]:
        """获取审计日志"""
        records = self._audit_log
        
        if identity_id:
            records = [r for r in records if r.identity_id == identity_id]
        
        if start_time:
            records = [r for r in records if r.timestamp >= start_time]
        
        if end_time:
            records = [r for r in records if r.timestamp <= end_time]
        
        return records
    
    def get_security_stats(self) -> Dict[str, Any]:
        """获取安全统计"""
        return {
            "total_identities": len(self._identities),
            "audit_records": len(self._audit_log),
            "locked_identities": sum(
                1 for i in self._identities.values()
                if i.locked_until and datetime.now() < datetime.fromisoformat(i.locked_until)
            ),
            "by_security_level": {
                level.name: sum(1 for i in self._identities.values() if i.security_level == level)
                for level in SecurityLevel
            },
        }


__all__ = [
    "Level3SecurityModule",
    "Identity",
    "Permission",
    "SecurityLevel",
    "SecurityAuditRecord",
]
