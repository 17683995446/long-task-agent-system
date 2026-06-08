"""
阶段34：三级审计模块
Level3AuditModule

职责定义：
- 操作审计
- 合规检查
- 审计报告生成
"""

from typing import Optional, Dict, Any, List
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


class AuditEventType(Enum):
    """审计事件类型"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    LOGIN = "login"
    LOGOUT = "logout"
    CONFIG_CHANGE = "config_change"
    ACCESS_DENIED = "access_denied"


class AuditSeverity(Enum):
    """审计严重级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """审计事件"""
    event_id: str
    event_type: AuditEventType
    actor: str
    resource: str
    action: str
    timestamp: datetime
    severity: AuditSeverity = AuditSeverity.INFO
    details: Dict[str, Any] = field(default_factory=dict)
    result: str = "success"
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "actor": self.actor,
            "resource": self.resource,
            "action": self.action,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "details": self.details,
            "result": self.result,
            "ip_address": self.ip_address,
            "session_id": self.session_id,
        }


@dataclass
class ComplianceRule:
    """合规规则"""
    rule_id: str
    rule_name: str
    description: str
    required_events: List[str]
    forbidden_events: List[str]
    max_event_age_hours: int = 24
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "description": self.description,
            "required_events": self.required_events,
            "forbidden_events": self.forbidden_events,
            "max_event_age_hours": self.max_event_age_hours,
            "enabled": self.enabled,
        }


@dataclass
class ComplianceReport:
    """合规报告"""
    report_id: str
    generated_at: datetime
    overall_compliant: bool
    rule_results: List[Dict[str, Any]] = field(default_factory=list)
    violations: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "overall_compliant": self.overall_compliant,
            "rule_results": self.rule_results,
            "violations": self.violations,
            "summary": self.summary,
        }


class Level3AuditModule(ControlModuleBase):
    """
    三级审计模块
    
    职责：
    1. 操作审计
    2. 合规检查
    3. 审计报告生成
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL3
        self._state.module_name = "Level3AuditModule"
        self._logger = Logger(f"L3A_{self.module_id}")
        
        # 审计事件存储
        self._audit_events: List[AuditEvent] = []
        # 合规规则
        self._compliance_rules: List[ComplianceRule] = []
        # 审计报告历史
        self._audit_reports: List[ComplianceReport] = []
        # 事件统计
        self._event_stats: Dict[str, int] = {}
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("三级审计模块初始化开始")
            
            # 1. 加载配置
            self._load_config(request)
            
            # 2. 初始化审计存储
            self._audit_events = []
            self._compliance_rules = []
            self._audit_reports = []
            self._event_stats = {}
            
            # 3. 加载默认合规规则
            self._load_default_rules()
            
            self._logger.info("三级审计模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="三级审计模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"三级审计模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L3A_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "max_events": 10000,
            "retention_days": 30,
            "auto_compliance_check": True,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("audit_config", {})
            self._config.update(custom_config)
    
    def _load_default_rules(self) -> None:
        """加载默认合规规则"""
        default_rules = [
            ComplianceRule(
                rule_id="RULE_001",
                rule_name="登录审计",
                description="所有登录操作必须被记录",
                required_events=["login", "logout"],
                forbidden_events=[],
                max_event_age_hours=24,
            ),
            ComplianceRule(
                rule_id="RULE_002",
                rule_name="数据修改审计",
                description="数据修改操作必须被记录",
                required_events=["create", "update", "delete"],
                forbidden_events=[],
                max_event_age_hours=24,
            ),
            ComplianceRule(
                rule_id="RULE_003",
                rule_name="访问控制审计",
                description="禁止未授权访问",
                required_events=[],
                forbidden_events=["access_denied"],
                max_event_age_hours=1,
            ),
        ]
        self._compliance_rules.extend(default_rules)
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("三级审计模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "record_event")
            
            if operation == "record_event":
                result = self._record_event_operation(input_data)
            elif operation == "query_events":
                result = self._query_events_operation(input_data)
            elif operation == "compliance_check":
                result = self._compliance_check_operation(input_data)
            elif operation == "generate_report":
                result = self._generate_report_operation(input_data)
            elif operation == "add_rule":
                result = self._add_rule_operation(input_data)
            elif operation == "get_stats":
                result = self._get_stats_operation()
            else:
                result = {"error": f"未知操作: {operation}"}
            
            self._logger.info("三级审计模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level3AuditModule",
                    "audit_summary": {
                        "total_events": len(self._audit_events),
                        "total_rules": len(self._compliance_rules),
                        "total_reports": len(self._audit_reports),
                    },
                },
                message="三级审计模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"三级审计模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L3A_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _record_event_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """记录审计事件"""
        import uuid
        
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AuditEventType(input_data.get("event_type", "execute")),
            actor=input_data.get("actor", "unknown"),
            resource=input_data.get("resource", "unknown"),
            action=input_data.get("action", "unknown"),
            timestamp=datetime.now(),
            severity=AuditSeverity(input_data.get("severity", "info")),
            details=input_data.get("details", {}),
            result=input_data.get("result", "success"),
            ip_address=input_data.get("ip_address"),
            session_id=input_data.get("session_id"),
        )
        
        self._audit_events.append(event)
        
        # 更新统计
        event_type_str = event.event_type.value
        self._event_stats[event_type_str] = self._event_stats.get(event_type_str, 0) + 1
        
        # 检查最大事件数
        max_events = self._config.get("max_events", 10000)
        if len(self._audit_events) > max_events:
            self._audit_events = self._audit_events[-max_events:]
        
        # 自动合规检查
        if self._config.get("auto_compliance_check", True):
            self._check_compliance_for_event(event)
        
        return {
            "operation": "record_event",
            "event_id": event.event_id,
            "recorded": True,
            "timestamp": event.timestamp.isoformat(),
        }
    
    def _query_events_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """查询审计事件"""
        filters = input_data.get("filters", {})
        limit = input_data.get("limit", 100)
        offset = input_data.get("offset", 0)
        
        filtered_events = self._audit_events
        
        # 应用过滤器
        if "event_type" in filters:
            filtered_events = [e for e in filtered_events if e.event_type.value == filters["event_type"]]
        if "actor" in filters:
            filtered_events = [e for e in filtered_events if e.actor == filters["actor"]]
        if "severity" in filters:
            filtered_events = [e for e in filtered_events if e.severity.value == filters["severity"]]
        if "result" in filters:
            filtered_events = [e for e in filtered_events if e.result == filters["result"]]
        if "start_time" in filters:
            start = datetime.fromisoformat(filters["start_time"])
            filtered_events = [e for e in filtered_events if e.timestamp >= start]
        if "end_time" in filters:
            end = datetime.fromisoformat(filters["end_time"])
            filtered_events = [e for e in filtered_events if e.timestamp <= end]
        
        # 排序（最新的在前）
        filtered_events = sorted(filtered_events, key=lambda e: e.timestamp, reverse=True)
        
        total = len(filtered_events)
        paginated = filtered_events[offset:offset + limit]
        
        return {
            "operation": "query_events",
            "total": total,
            "returned": len(paginated),
            "offset": offset,
            "limit": limit,
            "events": [e.to_dict() for e in paginated],
        }
    
    def _compliance_check_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行合规检查"""
        report = self._generate_compliance_report()
        self._audit_reports.append(report)
        
        return {
            "operation": "compliance_check",
            "report_id": report.report_id,
            "overall_compliant": report.overall_compliant,
            "violations_count": len(report.violations),
            "report": report.to_dict(),
        }
    
    def _generate_report_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成审计报告"""
        report_type = input_data.get("report_type", "summary")
        
        if report_type == "summary":
            result = self._generate_summary_report()
        elif report_type == "detailed":
            result = self._generate_detailed_report()
        elif report_type == "trend":
            result = self._generate_trend_report()
        else:
            result = self._generate_summary_report()
        
        return {
            "operation": "generate_report",
            "report_type": report_type,
            "generated_at": datetime.now().isoformat(),
            "report": result,
        }
    
    def _add_rule_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加合规规则"""
        rule_data = input_data.get("rule", {})
        rule = ComplianceRule(
            rule_id=rule_data.get("rule_id", ""),
            rule_name=rule_data.get("rule_name", ""),
            description=rule_data.get("description", ""),
            required_events=rule_data.get("required_events", []),
            forbidden_events=rule_data.get("forbidden_events", []),
            max_event_age_hours=rule_data.get("max_event_age_hours", 24),
            enabled=rule_data.get("enabled", True),
        )
        self._compliance_rules.append(rule)
        
        return {
            "operation": "add_rule",
            "rule_id": rule.rule_id,
            "added": True,
        }
    
    def _get_stats_operation(self) -> Dict[str, Any]:
        """获取统计信息"""
        severity_counts = {}
        for event in self._audit_events:
            sev = event.severity.value
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        return {
            "operation": "get_stats",
            "total_events": len(self._audit_events),
            "event_type_stats": self._event_stats.copy(),
            "severity_stats": severity_counts,
            "time_range": {
                "first_event": self._audit_events[0].timestamp.isoformat() if self._audit_events else None,
                "last_event": self._audit_events[-1].timestamp.isoformat() if self._audit_events else None,
            },
        }
    
    def _check_compliance_for_event(self, event: AuditEvent) -> None:
        """针对单个事件检查合规性"""
        for rule in self._compliance_rules:
            if not rule.enabled:
                continue
            
            # 检查禁止事件
            if event.event_type.value in rule.forbidden_events:
                self._logger.warning(f"合规违规: 规则 {rule.rule_id} 禁止事件 {event.event_type.value}")
    
    def _generate_compliance_report(self) -> ComplianceReport:
        """生成合规报告"""
        import uuid
        
        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(),
            overall_compliant=True,
        )
        
        for rule in self._compliance_rules:
            if not rule.enabled:
                continue
            
            rule_result = {
                "rule_id": rule.rule_id,
                "rule_name": rule.rule_name,
                "compliant": True,
                "violations": [],
            }
            
            # 检查必需事件
            cutoff_time = datetime.now() - __import__('datetime').timedelta(hours=rule.max_event_age_hours)
            recent_events = [e for e in self._audit_events if e.timestamp >= cutoff_time]
            recent_event_types = {e.event_type.value for e in recent_events}
            
            for required in rule.required_events:
                if required not in recent_event_types:
                    rule_result["compliant"] = False
                    report.overall_compliant = False
                    violation = {
                        "type": "missing_required_event",
                        "event_type": required,
                        "message": f"缺少必需事件: {required}",
                    }
                    rule_result["violations"].append(violation)
                    report.violations.append(violation)
            
            # 检查禁止事件
            for forbidden in rule.forbidden_events:
                forbidden_events = [e for e in recent_events if e.event_type.value == forbidden]
                if forbidden_events:
                    rule_result["compliant"] = False
                    report.overall_compliant = False
                    for e in forbidden_events:
                        violation = {
                            "type": "forbidden_event_occurred",
                            "event_type": forbidden,
                            "event_id": e.event_id,
                            "message": f"发生禁止事件: {forbidden}",
                        }
                        rule_result["violations"].append(violation)
                        report.violations.append(violation)
            
            report.rule_results.append(rule_result)
        
        report.summary = {
            "total_rules_checked": len([r for r in self._compliance_rules if r.enabled]),
            "compliant_rules": sum(1 for r in report.rule_results if r["compliant"]),
            "non_compliant_rules": sum(1 for r in report.rule_results if not r["compliant"]),
            "total_violations": len(report.violations),
        }
        
        return report
    
    def _generate_summary_report(self) -> Dict[str, Any]:
        """生成摘要报告"""
        return {
            "type": "summary",
            "total_events": len(self._audit_events),
            "event_stats": self._event_stats.copy(),
            "active_rules": len([r for r in self._compliance_rules if r.enabled]),
            "total_rules": len(self._compliance_rules),
        }
    
    def _generate_detailed_report(self) -> Dict[str, Any]:
        """生成详细报告"""
        return {
            "type": "detailed",
            "events": [e.to_dict() for e in self._audit_events[-100:]],
            "rules": [r.to_dict() for r in self._compliance_rules],
            "stats": self._get_stats_operation(),
        }
    
    def _generate_trend_report(self) -> Dict[str, Any]:
        """生成趋势报告"""
        hourly_counts: Dict[str, int] = {}
        for event in self._audit_events:
            hour_key = event.timestamp.strftime("%Y-%m-%d %H:00")
            hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1
        
        return {
            "type": "trend",
            "hourly_counts": hourly_counts,
            "peak_hour": max(hourly_counts, key=hourly_counts.get) if hourly_counts else None,
        }
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("三级审计模块校验开始")
        
        checks = []
        
        # 1. 校验审计事件存储
        if isinstance(self._audit_events, list):
            checks.append("events_store_valid")
        
        # 2. 校验合规规则
        if isinstance(self._compliance_rules, list):
            checks.append("rules_valid")
        
        # 3. 校验模块状态
        if self._state.module_level == ModuleLevel.LEVEL3:
            checks.append("level_valid")
        
        # 4. 校验配置
        if self._config.get("enabled", False):
            checks.append("audit_enabled")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="audit_validation",
                message="三级审计模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="audit_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("event_count", len(self._audit_events))
        snapshot.set_state("event_stats", self._event_stats)
        snapshot.set_state("rules", [r.to_dict() for r in self._compliance_rules])
        snapshot.set_state("report_count", len(self._audit_reports))
        snapshot.metadata["module_type"] = "Level3AuditModule"
    
    # =====================================================================
    # 公共接口
    # =====================================================================
    
    def record_event(self, event: AuditEvent) -> None:
        """记录审计事件"""
        self._audit_events.append(event)
        self._event_stats[event.event_type.value] = self._event_stats.get(event.event_type.value, 0) + 1
    
    def get_events(self, limit: int = 100) -> List[AuditEvent]:
        """获取审计事件"""
        return self._audit_events[-limit:]
    
    def add_compliance_rule(self, rule: ComplianceRule) -> None:
        """添加合规规则"""
        self._compliance_rules.append(rule)
    
    def get_compliance_rules(self) -> List[ComplianceRule]:
        """获取合规规则"""
        return self._compliance_rules
    
    def generate_compliance_report(self) -> ComplianceReport:
        """生成合规报告"""
        return self._generate_compliance_report()
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level3AuditModule",
    "AuditEvent",
    "AuditEventType",
    "AuditSeverity",
    "ComplianceRule",
    "ComplianceReport",
]
