"""
阶段57：四级数据处理模块
Level4DataProcessorModule

职责定义：
- 数据读取
- 数据写入
- 数据转换
- 数据清洗
- 数据聚合
- 数据验证
"""

from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
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


class DataFormat(Enum):
    """数据格式"""
    JSON = "json"
    CSV = "csv"
    XML = "xml"
    YAML = "yaml"
    PLAIN = "plain"
    BINARY = "binary"


class ProcessingOperation(Enum):
    """处理操作类型"""
    PARSE = "parse"
    SERIALIZE = "serialize"
    TRANSFORM = "transform"
    FILTER = "filter"
    AGGREGATE = "aggregate"
    VALIDATE = "validate"
    CLEANSE = "cleanse"
    MERGE = "merge"
    SPLIT = "split"


@dataclass
class DataSchema:
    """数据模式定义"""
    schema_id: str
    name: str
    fields: Dict[str, str] = field(default_factory=dict)
    required_fields: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "name": self.name,
            "fields": self.fields,
            "required_fields": self.required_fields,
            "constraints": self.constraints,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class DataRecord:
    """数据记录"""
    record_id: str
    source: str
    format: DataFormat
    raw_data: Any
    parsed_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "source": self.source,
            "format": self.format.value,
            "raw_data": str(self.raw_data)[:200] if self.raw_data else None,
            "parsed_data": self.parsed_data,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "errors": self.errors,
        }


@dataclass
class ProcessingPipeline:
    """处理流水线"""
    pipeline_id: str
    name: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    input_schema: Optional[str] = None
    output_schema: Optional[str] = None
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "name": self.name,
            "steps": self.steps,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }


@dataclass
class ProcessingResult:
    """处理结果"""
    result_id: str
    pipeline_id: str
    success: bool
    input_records: int
    output_records: int
    errors: List[str] = field(default_factory=list)
    processed_data: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "pipeline_id": self.pipeline_id,
            "success": self.success,
            "input_records": self.input_records,
            "output_records": self.output_records,
            "errors": self.errors,
            "processed_data": self.processed_data[:10],  # 限制输出
            "metadata": self.metadata,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class Level4DataProcessorModule(ExecuteModuleBase):
    """
    四级数据处理模块

    职责：
    1. 数据读取与解析
    2. 数据序列化与写入
    3. 数据转换与清洗
    4. 数据过滤与聚合
    5. 数据验证与模式匹配
    6. 处理流水线管理
    """

    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL4
        self._state.module_name = "Level4DataProcessorModule"
        self._logger = Logger(f"L4DP_{self.module_id}")

        # 数据存储
        self._records: Dict[str, DataRecord] = {}
        self._schemas: Dict[str, DataSchema] = {}
        self._pipelines: Dict[str, ProcessingPipeline] = {}
        self._results: List[ProcessingResult] = []
        # 转换器注册表
        self._transformers: Dict[str, Callable] = {}
        # 验证器注册表
        self._validators: Dict[str, Callable] = {}

    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("四级数据处理模块初始化开始")

            # 1. 加载配置
            self._load_config(request)

            # 2. 初始化存储
            self._records = {}
            self._schemas = {}
            self._pipelines = {}
            self._results = []
            self._transformers = {}
            self._validators = {}

            # 3. 注册内置转换器和验证器
            self._register_builtin_transformers()
            self._register_builtin_validators()

            # 4. 加载默认模式
            self._load_default_schemas()

            self._logger.info("四级数据处理模块初始化完成")

            return InitResult.success_result(
                module_id=self.module_id,
                message="四级数据处理模块初始化成功"
            )

        except Exception as e:
            self._logger.error(f"四级数据处理模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L4DP_INIT_FAILED",
                error_detail=str(e)
            )

    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "max_records": 10000,
            "max_results": 1000,
            "default_format": "json",
            "strict_validation": True,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("data_processor_config", {})
            self._config.update(custom_config)

    def _register_builtin_transformers(self) -> None:
        """注册内置转换器"""
        self._transformers["uppercase"] = lambda x: x.upper() if isinstance(x, str) else x
        self._transformers["lowercase"] = lambda x: x.lower() if isinstance(x, str) else x
        self._transformers["strip"] = lambda x: x.strip() if isinstance(x, str) else x
        self._transformers["int"] = lambda x: int(x) if x is not None else None
        self._transformers["float"] = lambda x: float(x) if x is not None else None
        self._transformers["bool"] = lambda x: bool(x) if x is not None else None
        self._transformers["reverse"] = lambda x: x[::-1] if isinstance(x, (str, list)) else x

    def _register_builtin_validators(self) -> None:
        """注册内置验证器"""
        self._validators["not_empty"] = lambda x: x is not None and x != ""
        self._validators["is_int"] = lambda x: isinstance(x, int) or (isinstance(x, str) and x.isdigit())
        self._validators["is_positive"] = lambda x: (isinstance(x, (int, float)) and x > 0) or (isinstance(x, str) and x.replace('.', '').isdigit() and float(x) > 0)
        self._validators["is_email"] = lambda x: isinstance(x, str) and re.match(r'^[^@]+@[^@]+\.[^@]+$', x) is not None
        self._validators["max_length"] = lambda x, max_len=100: len(str(x)) <= max_len
        self._validators["min_length"] = lambda x, min_len=1: len(str(x)) >= min_len

    def _load_default_schemas(self) -> None:
        """加载默认数据模式"""
        default_schemas = [
            DataSchema(
                schema_id="schema_user",
                name="user",
                fields={"id": "int", "name": "str", "email": "str", "age": "int"},
                required_fields=["id", "name", "email"],
                constraints={"age": {"min": 0, "max": 150}},
            ),
            DataSchema(
                schema_id="schema_product",
                name="product",
                fields={"id": "str", "name": "str", "price": "float", "category": "str"},
                required_fields=["id", "name", "price"],
                constraints={"price": {"min": 0}},
            ),
        ]
        for schema in default_schemas:
            self._schemas[schema.schema_id] = schema

    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("四级数据处理模块执行开始")

        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()

            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "process_data")

            if operation == "process_data":
                result = self._process_data_operation(input_data)
            elif operation == "parse_data":
                result = self._parse_data_operation(input_data)
            elif operation == "serialize_data":
                result = self._serialize_data_operation(input_data)
            elif operation == "create_pipeline":
                result = self._create_pipeline_operation(input_data)
            elif operation == "run_pipeline":
                result = self._run_pipeline_operation(input_data)
            elif operation == "validate_data":
                result = self._validate_data_operation(input_data)
            elif operation == "transform_data":
                result = self._transform_data_operation(input_data)
            elif operation == "filter_data":
                result = self._filter_data_operation(input_data)
            elif operation == "aggregate_data":
                result = self._aggregate_data_operation(input_data)
            elif operation == "get_schema":
                result = self._get_schema_operation(input_data)
            elif operation == "get_records":
                result = self._get_records_operation(input_data)
            elif operation == "get_results":
                result = self._get_results_operation(input_data)
            else:
                result = {"error": f"未知操作: {operation}"}

            self._logger.info("四级数据处理模块执行完成")

            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level4DataProcessorModule",
                    "processor_summary": {
                        "total_records": len(self._records),
                        "total_schemas": len(self._schemas),
                        "total_pipelines": len(self._pipelines),
                        "total_results": len(self._results),
                    },
                },
                message="四级数据处理模块执行成功"
            )

        except Exception as e:
            self._logger.error(f"四级数据处理模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L4DP_EXECUTION_FAILED",
                error_detail=str(e)
            )

    def _process_data_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据"""
        import uuid

        data = input_data.get("data")
        source = input_data.get("source", "unknown")
        data_format = DataFormat(input_data.get("format", self._config.get("default_format", "json")))

        record_id = str(uuid.uuid4())
        record = DataRecord(
            record_id=record_id,
            source=source,
            format=data_format,
            raw_data=data,
            metadata=input_data.get("metadata", {}),
        )

        # 尝试解析数据
        try:
            if data_format == DataFormat.JSON and isinstance(data, str):
                record.parsed_data = json.loads(data)
            elif data_format == DataFormat.JSON and isinstance(data, dict):
                record.parsed_data = data
            else:
                record.parsed_data = {"raw": str(data)}
            record.processed_at = datetime.now()
        except Exception as e:
            record.errors.append(f"解析失败: {str(e)}")

        self._records[record_id] = record

        # 限制记录数量
        max_records = self._config.get("max_records", 10000)
        if len(self._records) > max_records:
            oldest = sorted(self._records.keys(), key=lambda k: self._records[k].created_at)[0]
            del self._records[oldest]

        return {
            "operation": "process_data",
            "record_id": record_id,
            "parsed": record.parsed_data is not None,
            "errors": record.errors,
        }

    def _parse_data_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析数据"""
        data = input_data.get("data")
        data_format = DataFormat(input_data.get("format", "json"))

        try:
            if data_format == DataFormat.JSON:
                if isinstance(data, str):
                    parsed = json.loads(data)
                else:
                    parsed = data
            elif data_format == DataFormat.CSV:
                lines = str(data).strip().split("\n")
                if lines:
                    headers = lines[0].split(",")
                    parsed = []
                    for line in lines[1:]:
                        values = line.split(",")
                        parsed.append(dict(zip(headers, values)))
                else:
                    parsed = []
            else:
                parsed = {"raw": str(data)}

            return {
                "operation": "parse_data",
                "format": data_format.value,
                "parsed": parsed,
                "success": True,
            }
        except Exception as e:
            return {
                "operation": "parse_data",
                "format": data_format.value,
                "error": str(e),
                "success": False,
            }

    def _serialize_data_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """序列化数据"""
        data = input_data.get("data")
        data_format = DataFormat(input_data.get("format", "json"))

        try:
            if data_format == DataFormat.JSON:
                serialized = json.dumps(data, ensure_ascii=False, default=str)
            elif data_format == DataFormat.PLAIN:
                serialized = str(data)
            else:
                serialized = str(data)

            return {
                "operation": "serialize_data",
                "format": data_format.value,
                "serialized": serialized,
                "success": True,
            }
        except Exception as e:
            return {
                "operation": "serialize_data",
                "format": data_format.value,
                "error": str(e),
                "success": False,
            }

    def _create_pipeline_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建处理流水线"""
        import uuid

        pipeline_id = str(uuid.uuid4())
        pipeline = ProcessingPipeline(
            pipeline_id=pipeline_id,
            name=input_data.get("name", f"pipeline_{pipeline_id[:8]}"),
            steps=input_data.get("steps", []),
            input_schema=input_data.get("input_schema"),
            output_schema=input_data.get("output_schema"),
            metadata=input_data.get("metadata", {}),
        )
        self._pipelines[pipeline_id] = pipeline

        return {
            "operation": "create_pipeline",
            "pipeline_id": pipeline_id,
            "created": True,
        }

    def _run_pipeline_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """运行处理流水线"""
        import uuid

        pipeline_id = input_data.get("pipeline_id")
        data = input_data.get("data", [])

        if not pipeline_id or pipeline_id not in self._pipelines:
            return {"operation": "run_pipeline", "error": "流水线不存在", "success": False}

        pipeline = self._pipelines[pipeline_id]
        if not pipeline.enabled:
            return {"operation": "run_pipeline", "error": "流水线已禁用", "success": False}

        result_id = str(uuid.uuid4())
        result = ProcessingResult(
            result_id=result_id,
            pipeline_id=pipeline_id,
            success=True,
            input_records=len(data) if isinstance(data, list) else 1,
            output_records=0,
        )

        processed_data = data if isinstance(data, list) else [data]

        # 执行流水线步骤
        for step in pipeline.steps:
            step_type = step.get("type")
            if step_type == "filter":
                condition = step.get("condition", lambda x: True)
                processed_data = [d for d in processed_data if condition(d)]
            elif step_type == "transform":
                transform_name = step.get("transformer")
                field = step.get("field")
                if transform_name in self._transformers and field:
                    for d in processed_data:
                        if isinstance(d, dict) and field in d:
                            d[field] = self._transformers[transform_name](d[field])
            elif step_type == "validate":
                validator_name = step.get("validator")
                field = step.get("field")
                if validator_name in self._validators and field:
                    for d in processed_data:
                        if isinstance(d, dict) and field in d:
                            if not self._validators[validator_name](d[field]):
                                result.errors.append(f"验证失败: {field}={d[field]}")
            elif step_type == "aggregate":
                group_by = step.get("group_by")
                agg_field = step.get("agg_field")
                agg_func = step.get("agg_func", "count")
                if group_by and agg_field:
                    groups = {}
                    for d in processed_data:
                        key = d.get(group_by)
                        if key not in groups:
                            groups[key] = []
                        groups[key].append(d)

                    aggregated = []
                    for key, group in groups.items():
                        if agg_func == "count":
                            val = len(group)
                        elif agg_func == "sum":
                            val = sum(d.get(agg_field, 0) for d in group if isinstance(d.get(agg_field), (int, float)))
                        elif agg_func == "avg":
                            vals = [d.get(agg_field, 0) for d in group if isinstance(d.get(agg_field), (int, float))]
                            val = sum(vals) / len(vals) if vals else 0
                        else:
                            val = len(group)
                        aggregated.append({group_by: key, agg_field: val})
                    processed_data = aggregated

        result.output_records = len(processed_data)
        result.processed_data = processed_data
        result.completed_at = datetime.now()
        self._results.append(result)

        # 限制结果数量
        max_results = self._config.get("max_results", 1000)
        if len(self._results) > max_results:
            self._results = self._results[-max_results:]

        return {
            "operation": "run_pipeline",
            "result_id": result_id,
            "input_records": result.input_records,
            "output_records": result.output_records,
            "errors": result.errors,
            "success": result.success and len(result.errors) == 0,
        }

    def _validate_data_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证数据"""
        data = input_data.get("data", {})
        schema_id = input_data.get("schema_id")

        errors = []
        validated = True

        if schema_id and schema_id in self._schemas:
            schema = self._schemas[schema_id]
            # 检查必填字段
            for field_name in schema.required_fields:
                if field_name not in data or data[field_name] is None or data[field_name] == "":
                    errors.append(f"缺少必填字段: {field_name}")
                    validated = False

            # 检查字段类型
            for field_name, field_type in schema.fields.items():
                if field_name in data and data[field_name] is not None:
                    value = data[field_name]
                    if field_type == "int" and not isinstance(value, int) and not (isinstance(value, str) and value.isdigit()):
                        errors.append(f"字段 {field_name} 应为整数类型")
                        validated = False
                    elif field_type == "float" and not isinstance(value, (int, float)):
                        errors.append(f"字段 {field_name} 应为浮点类型")
                        validated = False
                    elif field_type == "str" and not isinstance(value, str):
                        errors.append(f"字段 {field_name} 应为字符串类型")
                        validated = False

            # 检查约束
            for field_name, constraints in schema.constraints.items():
                if field_name in data and data[field_name] is not None:
                    value = data[field_name]
                    if "min" in constraints:
                        try:
                            if float(value) < constraints["min"]:
                                errors.append(f"字段 {field_name} 值 {value} 小于最小值 {constraints['min']}")
                                validated = False
                        except (ValueError, TypeError):
                            pass
                    if "max" in constraints:
                        try:
                            if float(value) > constraints["max"]:
                                errors.append(f"字段 {field_name} 值 {value} 大于最大值 {constraints['max']}")
                                validated = False
                        except (ValueError, TypeError):
                            pass
        else:
            # 无模式验证，使用通用验证
            if not isinstance(data, dict):
                errors.append("数据应为字典类型")
                validated = False

        return {
            "operation": "validate_data",
            "schema_id": schema_id,
            "validated": validated,
            "errors": errors,
        }

    def _transform_data_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """转换数据"""
        data = input_data.get("data", {})
        transformations = input_data.get("transformations", [])

        if not isinstance(data, dict):
            return {"operation": "transform_data", "error": "数据应为字典类型", "success": False}

        result = dict(data)
        applied = []

        for transform in transformations:
            field = transform.get("field")
            transform_name = transform.get("transformer")

            if field and field in result and transform_name in self._transformers:
                old_value = result[field]
                result[field] = self._transformers[transform_name](old_value)
                applied.append({"field": field, "transformer": transform_name, "old": old_value, "new": result[field]})

        return {
            "operation": "transform_data",
            "transformed": result,
            "applied": applied,
            "success": True,
        }

    def _filter_data_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """过滤数据"""
        data = input_data.get("data", [])
        conditions = input_data.get("conditions", [])

        if not isinstance(data, list):
            return {"operation": "filter_data", "error": "数据应为列表类型", "success": False}

        filtered = []
        for item in data:
            if not isinstance(item, dict):
                continue

            match = True
            for condition in conditions:
                field = condition.get("field")
                op = condition.get("op", "eq")
                value = condition.get("value")

                if field not in item:
                    match = False
                    break

                item_value = item[field]
                if op == "eq" and item_value != value:
                    match = False
                    break
                elif op == "ne" and item_value == value:
                    match = False
                    break
                elif op == "gt":
                    try:
                        if float(item_value) <= float(value):
                            match = False
                            break
                    except (ValueError, TypeError):
                        match = False
                        break
                elif op == "lt":
                    try:
                        if float(item_value) >= float(value):
                            match = False
                            break
                    except (ValueError, TypeError):
                        match = False
                        break
                elif op == "contains":
                    if value not in str(item_value):
                        match = False
                        break
                elif op == "startswith":
                    if not str(item_value).startswith(str(value)):
                        match = False
                        break

            if match:
                filtered.append(item)

        return {
            "operation": "filter_data",
            "input_count": len(data),
            "output_count": len(filtered),
            "filtered": filtered,
            "success": True,
        }

    def _aggregate_data_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """聚合数据"""
        data = input_data.get("data", [])
        group_by = input_data.get("group_by")
        aggregations = input_data.get("aggregations", [])

        if not isinstance(data, list):
            return {"operation": "aggregate_data", "error": "数据应为列表类型", "success": False}

        if not group_by:
            return {"operation": "aggregate_data", "error": "缺少group_by字段", "success": False}

        # 分组
        groups = {}
        for item in data:
            if isinstance(item, dict) and group_by in item:
                key = item[group_by]
                if key not in groups:
                    groups[key] = []
                groups[key].append(item)

        # 聚合
        result = []
        for key, group in groups.items():
            agg_result = {group_by: key}
            for agg in aggregations:
                field = agg.get("field")
                func = agg.get("func", "count")
                alias = agg.get("alias", f"{func}_{field}")

                if func == "count":
                    agg_result[alias] = len(group)
                elif func == "sum" and field:
                    vals = [item.get(field, 0) for item in group if isinstance(item.get(field), (int, float))]
                    agg_result[alias] = sum(vals)
                elif func == "avg" and field:
                    vals = [item.get(field, 0) for item in group if isinstance(item.get(field), (int, float))]
                    agg_result[alias] = sum(vals) / len(vals) if vals else 0
                elif func == "min" and field:
                    vals = [item.get(field) for item in group if isinstance(item.get(field), (int, float))]
                    agg_result[alias] = min(vals) if vals else None
                elif func == "max" and field:
                    vals = [item.get(field) for item in group if isinstance(item.get(field), (int, float))]
                    agg_result[alias] = max(vals) if vals else None

            result.append(agg_result)

        return {
            "operation": "aggregate_data",
            "group_by": group_by,
            "group_count": len(result),
            "aggregated": result,
            "success": True,
        }

    def _get_schema_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取数据模式"""
        schema_id = input_data.get("schema_id")

        if schema_id:
            if schema_id in self._schemas:
                return {
                    "operation": "get_schema",
                    "schema": self._schemas[schema_id].to_dict(),
                }
            else:
                return {"operation": "get_schema", "error": "模式不存在"}
        else:
            return {
                "operation": "get_schema",
                "schemas": [s.to_dict() for s in self._schemas.values()],
            }

    def _get_records_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取记录"""
        limit = input_data.get("limit", 100)
        source = input_data.get("source")

        records = list(self._records.values())
        if source:
            records = [r for r in records if r.source == source]

        records = sorted(records, key=lambda r: r.created_at, reverse=True)[:limit]

        return {
            "operation": "get_records",
            "total": len(self._records),
            "returned": len(records),
            "records": [r.to_dict() for r in records],
        }

    def _get_results_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取处理结果"""
        limit = input_data.get("limit", 100)
        pipeline_id = input_data.get("pipeline_id")

        results = self._results
        if pipeline_id:
            results = [r for r in results if r.pipeline_id == pipeline_id]

        results = sorted(results, key=lambda r: r.started_at, reverse=True)[:limit]

        return {
            "operation": "get_results",
            "total": len(self._results),
            "returned": len(results),
            "results": [r.to_dict() for r in results],
        }

    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("四级数据处理模块校验开始")

        checks = []

        if isinstance(self._records, dict):
            checks.append("records_valid")
        if isinstance(self._schemas, dict):
            checks.append("schemas_valid")
        if isinstance(self._pipelines, dict):
            checks.append("pipelines_valid")
        if self._state.module_level == ModuleLevel.LEVEL4:
            checks.append("level_valid")
        if isinstance(self._transformers, dict) and len(self._transformers) > 0:
            checks.append("transformers_valid")
        if isinstance(self._validators, dict) and len(self._validators) > 0:
            checks.append("validators_valid")

        all_passed = len(checks) == 6

        if all_passed:
            return CheckResult.passed_result(
                check_type="data_processor_validation",
                message="四级数据处理模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="data_processor_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )

    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("record_count", len(self._records))
        snapshot.set_state("schema_count", len(self._schemas))
        snapshot.set_state("pipeline_count", len(self._pipelines))
        snapshot.set_state("result_count", len(self._results))
        snapshot.set_state("transformer_count", len(self._transformers))
        snapshot.set_state("validator_count", len(self._validators))
        snapshot.metadata["module_type"] = "Level4DataProcessorModule"

    # 公共接口
    def process_data(self, data: Any, source: str = "unknown", data_format: str = "json") -> str:
        """处理数据并返回记录ID"""
        import uuid
        record_id = str(uuid.uuid4())
        fmt = DataFormat(data_format)
        record = DataRecord(
            record_id=record_id,
            source=source,
            format=fmt,
            raw_data=data,
        )
        try:
            if fmt == DataFormat.JSON and isinstance(data, str):
                record.parsed_data = json.loads(data)
            elif fmt == DataFormat.JSON and isinstance(data, dict):
                record.parsed_data = data
            else:
                record.parsed_data = {"raw": str(data)}
            record.processed_at = datetime.now()
        except Exception as e:
            record.errors.append(f"解析失败: {str(e)}")
        self._records[record_id] = record
        return record_id

    def create_pipeline(self, name: str, steps: List[Dict[str, Any]]) -> str:
        """创建处理流水线"""
        import uuid
        pipeline_id = str(uuid.uuid4())
        pipeline = ProcessingPipeline(
            pipeline_id=pipeline_id,
            name=name,
            steps=steps,
        )
        self._pipelines[pipeline_id] = pipeline
        return pipeline_id

    def run_pipeline(self, pipeline_id: str, data: List[Dict[str, Any]]) -> ProcessingResult:
        """运行流水线"""
        import uuid
        result = ProcessingResult(
            result_id=str(uuid.uuid4()),
            pipeline_id=pipeline_id,
            success=True,
            input_records=len(data),
            output_records=0,
        )
        result.processed_data = data
        result.output_records = len(data)
        result.completed_at = datetime.now()
        self._results.append(result)
        return result

    def register_transformer(self, name: str, transformer: Callable) -> None:
        """注册转换器"""
        self._transformers[name] = transformer

    def register_validator(self, name: str, validator: Callable) -> None:
        """注册验证器"""
        self._validators[name] = validator

    def get_record(self, record_id: str) -> Optional[DataRecord]:
        """获取记录"""
        return self._records.get(record_id)

    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level4DataProcessorModule",
    "DataFormat",
    "ProcessingOperation",
    "DataSchema",
    "DataRecord",
    "ProcessingPipeline",
    "ProcessingResult",
]
