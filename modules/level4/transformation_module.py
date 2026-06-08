"""
阶段47：四级数据转换模块
Level4TransformationModule

职责定义：
- 数据转换
- 映射规则
- 格式转换
"""

from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

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


class TransformationType(Enum):
    """转换类型"""
    MAP = "map"
    FILTER = "filter"
    AGGREGATE = "aggregate"
    FORMAT = "format"
    ENRICH = "enrich"
    NORMALIZE = "normalize"
    CUSTOM = "custom"


class DataFormat(Enum):
    """数据格式"""
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    YAML = "yaml"
    DICT = "dict"
    STRING = "string"


@dataclass
class TransformationRule:
    """转换规则"""
    rule_id: str
    name: str
    transformation_type: TransformationType
    source_field: str
    target_field: str
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "transformation_type": self.transformation_type.value,
            "source_field": self.source_field,
            "target_field": self.target_field,
            "params": self.params,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }


@dataclass
class TransformationResult:
    """转换结果"""
    result_id: str
    rule_id: str
    success: bool
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    timestamp: datetime
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "rule_id": self.rule_id,
            "success": self.success,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "timestamp": self.timestamp.isoformat(),
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


@dataclass
class MappingSchema:
    """映射模式"""
    schema_id: str
    name: str
    mappings: List[TransformationRule] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "name": self.name,
            "mapping_count": len(self.mappings),
            "metadata": self.metadata,
            "mappings": [m.to_dict() for m in self.mappings],
        }


class Level4TransformationModule(ExecuteModuleBase):
    """
    四级数据转换模块
    
    职责：
    1. 数据转换
    2. 映射规则
    3. 格式转换
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL4
        self._state.module_name = "Level4TransformationModule"
        self._logger = Logger(f"L4T_{self.module_id}")
        
        # 规则存储
        self._rules: Dict[str, TransformationRule] = {}
        # 映射模式
        self._schemas: Dict[str, MappingSchema] = {}
        # 转换结果
        self._results: List[TransformationResult] = []
        # 自定义转换器
        self._custom_transformers: Dict[str, Callable] = {}
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("四级数据转换模块初始化开始")
            
            # 1. 加载配置
            self._load_config(request)
            
            # 2. 初始化存储
            self._rules = {}
            self._schemas = {}
            self._results = []
            self._custom_transformers = {}
            
            # 3. 加载默认规则
            self._load_default_rules()
            
            self._logger.info("四级数据转换模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="四级数据转换模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级数据转换模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L4T_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "default_format": "json",
            "log_transformations": True,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("transformation_config", {})
            self._config.update(custom_config)
    
    def _load_default_rules(self) -> None:
        """加载默认规则"""
        default_rules = [
            TransformationRule(
                rule_id="rule_uppercase",
                name="转大写",
                transformation_type=TransformationType.FORMAT,
                source_field="*",
                target_field="*",
                params={"operation": "uppercase"},
            ),
            TransformationRule(
                rule_id="rule_date_format",
                name="日期格式化",
                transformation_type=TransformationType.FORMAT,
                source_field="date",
                target_field="formatted_date",
                params={"from_format": "iso", "to_format": "yyyy-MM-dd"},
            ),
        ]
        for rule in default_rules:
            self._rules[rule.rule_id] = rule
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("四级数据转换模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "transform")
            
            if operation == "transform":
                result = self._transform_operation(input_data)
            elif operation == "add_rule":
                result = self._add_rule_operation(input_data)
            elif operation == "create_schema":
                result = self._create_schema_operation(input_data)
            elif operation == "apply_schema":
                result = self._apply_schema_operation(input_data)
            elif operation == "format_convert":
                result = self._format_convert_operation(input_data)
            elif operation == "get_results":
                result = self._get_results_operation(input_data)
            elif operation == "register_transformer":
                result = self._register_transformer_operation(input_data)
            else:
                result = {"error": f"未知操作: {operation}"}
            
            self._logger.info("四级数据转换模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level4TransformationModule",
                    "transformation_summary": {
                        "total_rules": len(self._rules),
                        "total_schemas": len(self._schemas),
                        "total_results": len(self._results),
                    },
                },
                message="四级数据转换模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级数据转换模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L4T_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _transform_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行转换"""
        import uuid
        
        data = input_data.get("data", {})
        rule_ids = input_data.get("rule_ids", [])
        
        if not rule_ids:
            return {"operation": "transform", "error": "未指定规则", "success": False}
        
        output_data = dict(data)
        applied_rules = []
        failed_rules = []
        
        for rule_id in rule_ids:
            if rule_id not in self._rules:
                failed_rules.append({"rule_id": rule_id, "error": "规则不存在"})
                continue
            
            rule = self._rules[rule_id]
            if not rule.enabled:
                failed_rules.append({"rule_id": rule_id, "error": "规则已禁用"})
                continue
            
            try:
                output_data = self._apply_rule(rule, output_data)
                applied_rules.append(rule_id)
            except Exception as e:
                failed_rules.append({"rule_id": rule_id, "error": str(e)})
        
        # 记录结果
        result = TransformationResult(
            result_id=str(uuid.uuid4()),
            rule_id=",".join(rule_ids),
            success=len(failed_rules) == 0,
            input_data=data,
            output_data=output_data,
            timestamp=datetime.now(),
            error_message="; ".join(f["error"] for f in failed_rules) if failed_rules else None,
        )
        self._results.append(result)
        
        return {
            "operation": "transform",
            "result_id": result.result_id,
            "success": result.success,
            "applied_rules": applied_rules,
            "failed_rules": failed_rules,
            "output_data": output_data,
        }
    
    def _apply_rule(self, rule: TransformationRule, data: Dict[str, Any]) -> Dict[str, Any]:
        """应用单个规则"""
        result = dict(data)
        
        if rule.transformation_type == TransformationType.MAP:
            # 字段映射
            source = rule.source_field
            target = rule.target_field
            if source in result:
                result[target] = result[source]
                if rule.params.get("remove_source", False):
                    del result[source]
        
        elif rule.transformation_type == TransformationType.FORMAT:
            # 格式转换
            field = rule.source_field
            if field == "*":
                # 应用到所有字段
                for key in list(result.keys()):
                    result[key] = self._format_value(result[key], rule.params)
            elif field in result:
                result[rule.target_field or field] = self._format_value(result[field], rule.params)
        
        elif rule.transformation_type == TransformationType.FILTER:
            # 过滤
            condition = rule.params.get("condition")
            if condition:
                result = {k: v for k, v in result.items() if self._evaluate_condition(k, v, condition)}
        
        elif rule.transformation_type == TransformationType.AGGREGATE:
            # 聚合
            fields = rule.params.get("fields", [])
            operation = rule.params.get("operation", "sum")
            values = [result.get(f) for f in fields if f in result]
            try:
                numeric_values = [float(v) for v in values if v is not None]
                if operation == "sum":
                    result[rule.target_field] = sum(numeric_values)
                elif operation == "avg":
                    result[rule.target_field] = sum(numeric_values) / len(numeric_values) if numeric_values else 0
                elif operation == "count":
                    result[rule.target_field] = len(numeric_values)
                elif operation == "min":
                    result[rule.target_field] = min(numeric_values) if numeric_values else None
                elif operation == "max":
                    result[rule.target_field] = max(numeric_values) if numeric_values else None
            except (ValueError, TypeError):
                pass
        
        elif rule.transformation_type == TransformationType.ENRICH:
            # 数据增强
            enrichments = rule.params.get("enrichments", {})
            for key, value in enrichments.items():
                if key not in result:
                    result[key] = value
        
        elif rule.transformation_type == TransformationType.NORMALIZE:
            # 标准化
            field = rule.source_field
            if field in result:
                result[rule.target_field or field] = self._normalize_value(result[field], rule.params)
        
        elif rule.transformation_type == TransformationType.CUSTOM:
            # 自定义转换
            transformer_name = rule.params.get("transformer")
            if transformer_name and transformer_name in self._custom_transformers:
                transformer = self._custom_transformers[transformer_name]
                field = rule.source_field
                if field in result:
                    result[rule.target_field or field] = transformer(result[field], rule.params)
        
        return result
    
    def _format_value(self, value: Any, params: Dict[str, Any]) -> Any:
        """格式化值"""
        operation = params.get("operation")
        
        if operation == "uppercase" and isinstance(value, str):
            return value.upper()
        elif operation == "lowercase" and isinstance(value, str):
            return value.lower()
        elif operation == "trim" and isinstance(value, str):
            return value.strip()
        elif operation == "to_string":
            return str(value)
        elif operation == "to_int":
            try:
                return int(value)
            except (ValueError, TypeError):
                return value
        elif operation == "to_float":
            try:
                return float(value)
            except (ValueError, TypeError):
                return value
        elif operation == "to_bool":
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "on")
            return bool(value)
        
        return value
    
    def _evaluate_condition(self, key: str, value: Any, condition: Dict[str, Any]) -> bool:
        """评估条件"""
        op = condition.get("op", "eq")
        target = condition.get("value")
        
        if op == "eq":
            return value == target
        elif op == "ne":
            return value != target
        elif op == "gt":
            try:
                return float(value) > float(target)
            except (ValueError, TypeError):
                return False
        elif op == "lt":
            try:
                return float(value) < float(target)
            except (ValueError, TypeError):
                return False
        elif op == "contains":
            return target in str(value)
        elif op == "startswith":
            return str(value).startswith(str(target))
        elif op == "endswith":
            return str(value).endswith(str(target))
        
        return True
    
    def _normalize_value(self, value: Any, params: Dict[str, Any]) -> Any:
        """标准化值"""
        method = params.get("method", "none")
        
        if method == "lowercase" and isinstance(value, str):
            return value.lower().strip()
        elif method == "uppercase" and isinstance(value, str):
            return value.upper().strip()
        elif method == "trim" and isinstance(value, str):
            return value.strip()
        elif method == "remove_special" and isinstance(value, str):
            import re
            return re.sub(r'[^\w\s]', '', value)
        
        return value
    
    def _add_rule_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加规则"""
        rule_id = input_data.get("rule_id")
        
        rule = TransformationRule(
            rule_id=rule_id,
            name=input_data.get("name", ""),
            transformation_type=TransformationType(input_data.get("transformation_type", "map")),
            source_field=input_data.get("source_field", ""),
            target_field=input_data.get("target_field", ""),
            params=input_data.get("params", {}),
            enabled=input_data.get("enabled", True),
            metadata=input_data.get("metadata", {}),
        )
        self._rules[rule_id] = rule
        
        return {"operation": "add_rule", "rule_id": rule_id, "added": True}
    
    def _create_schema_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建映射模式"""
        import uuid
        
        schema_id = str(uuid.uuid4())
        schema = MappingSchema(
            schema_id=schema_id,
            name=input_data.get("name", f"schema_{schema_id[:8]}"),
            metadata=input_data.get("metadata", {}),
        )
        self._schemas[schema_id] = schema
        
        return {"operation": "create_schema", "schema_id": schema_id, "created": True}
    
    def _apply_schema_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """应用映射模式"""
        schema_id = input_data.get("schema_id")
        data = input_data.get("data", {})
        
        if not schema_id or schema_id not in self._schemas:
            return {"operation": "apply_schema", "error": "模式不存在", "success": False}
        
        schema = self._schemas[schema_id]
        output_data = dict(data)
        
        for rule in schema.mappings:
            if rule.enabled:
                output_data = self._apply_rule(rule, output_data)
        
        return {
            "operation": "apply_schema",
            "schema_id": schema_id,
            "output_data": output_data,
        }
    
    def _format_convert_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式转换"""
        data = input_data.get("data")
        from_format = input_data.get("from_format", "dict")
        to_format = input_data.get("to_format", "json")
        
        try:
            # 先解析为Python对象
            if from_format == "json" and isinstance(data, str):
                parsed = json.loads(data)
            elif from_format == "dict":
                parsed = data
            else:
                parsed = data
            
            # 再转换为目标格式
            if to_format == "json":
                result = json.dumps(parsed, ensure_ascii=False, indent=2)
            elif to_format == "dict":
                result = parsed
            elif to_format == "string":
                result = str(parsed)
            else:
                result = parsed
            
            return {
                "operation": "format_convert",
                "from_format": from_format,
                "to_format": to_format,
                "result": result,
                "success": True,
            }
        except Exception as e:
            return {
                "operation": "format_convert",
                "error": str(e),
                "success": False,
            }
    
    def _get_results_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取转换结果"""
        limit = input_data.get("limit", 50)
        results = sorted(self._results, key=lambda r: r.timestamp, reverse=True)[:limit]
        
        return {
            "operation": "get_results",
            "total": len(self._results),
            "returned": len(results),
            "results": [r.to_dict() for r in results],
        }
    
    def _register_transformer_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """注册自定义转换器"""
        transformer_name = input_data.get("transformer_name")
        return {
            "operation": "register_transformer",
            "transformer_name": transformer_name,
            "registered": True,
            "note": "自定义转换器需要通过代码注册",
        }
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("四级数据转换模块校验开始")
        
        checks = []
        
        if isinstance(self._rules, dict):
            checks.append("rules_valid")
        if isinstance(self._schemas, dict):
            checks.append("schemas_valid")
        if self._state.module_level == ModuleLevel.LEVEL4:
            checks.append("level_valid")
        if isinstance(self._results, list):
            checks.append("results_valid")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="transformation_validation",
                message="四级数据转换模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="transformation_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("rules", {rid: r.to_dict() for rid, r in self._rules.items()})
        snapshot.set_state("schemas", {sid: s.to_dict() for sid, s in self._schemas.items()})
        snapshot.set_state("result_count", len(self._results))
        snapshot.metadata["module_type"] = "Level4TransformationModule"
    
    # 公共接口
    def transform(self, data: Dict[str, Any], rule_ids: List[str]) -> Dict[str, Any]:
        """转换数据"""
        result = self._transform_operation({"data": data, "rule_ids": rule_ids})
        return result.get("output_data", data)
    
    def add_rule(self, rule: TransformationRule) -> None:
        """添加规则"""
        self._rules[rule.rule_id] = rule
    
    def register_transformer(self, name: str, transformer: Callable) -> None:
        """注册自定义转换器"""
        self._custom_transformers[name] = transformer
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level4TransformationModule",
    "TransformationRule",
    "TransformationResult",
    "MappingSchema",
    "TransformationType",
    "DataFormat",
]
