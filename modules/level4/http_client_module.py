"""
阶段58：四级HTTP客户端模块
Level4HttpClientModule

职责定义：
- HTTP请求
- 响应处理
- 重试机制
- 连接池管理
- 超时控制
- 请求拦截
"""

from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import urllib.request
import urllib.parse
import json
import ssl

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


class HttpMethod(Enum):
    """HTTP方法"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class HttpStatusCategory(Enum):
    """HTTP状态分类"""
    INFORMATIONAL = "informational"  # 1xx
    SUCCESS = "success"  # 2xx
    REDIRECTION = "redirection"  # 3xx
    CLIENT_ERROR = "client_error"  # 4xx
    SERVER_ERROR = "server_error"  # 5xx


@dataclass
class HttpRequest:
    """HTTP请求"""
    request_id: str
    method: HttpMethod
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, str] = field(default_factory=dict)
    body: Optional[Any] = None
    timeout: int = 30
    retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "method": self.method.value,
            "url": self.url,
            "headers": self.headers,
            "params": self.params,
            "body": self.body,
            "timeout": self.timeout,
            "retries": self.retries,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class HttpResponse:
    """HTTP响应"""
    response_id: str
    request_id: str
    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[Any] = None
    content_type: str = ""
    content_length: int = 0
    elapsed_ms: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    received_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id": self.response_id,
            "request_id": self.request_id,
            "status_code": self.status_code,
            "headers": self.headers,
            "body": str(self.body)[:500] if self.body else None,
            "content_type": self.content_type,
            "content_length": self.content_length,
            "elapsed_ms": self.elapsed_ms,
            "error": self.error,
            "metadata": self.metadata,
            "received_at": self.received_at.isoformat(),
        }

    def is_success(self) -> bool:
        """是否成功响应"""
        return 200 <= self.status_code < 300

    def get_status_category(self) -> HttpStatusCategory:
        """获取状态分类"""
        if 100 <= self.status_code < 200:
            return HttpStatusCategory.INFORMATIONAL
        elif 200 <= self.status_code < 300:
            return HttpStatusCategory.SUCCESS
        elif 300 <= self.status_code < 400:
            return HttpStatusCategory.REDIRECTION
        elif 400 <= self.status_code < 500:
            return HttpStatusCategory.CLIENT_ERROR
        else:
            return HttpStatusCategory.SERVER_ERROR


@dataclass
class ConnectionPool:
    """连接池"""
    pool_id: str
    host: str
    port: int
    max_connections: int = 10
    idle_timeout: int = 60
    active_connections: int = 0
    idle_connections: int = 0
    total_requests: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pool_id": self.pool_id,
            "host": self.host,
            "port": self.port,
            "max_connections": self.max_connections,
            "idle_timeout": self.idle_timeout,
            "active_connections": self.active_connections,
            "idle_connections": self.idle_connections,
            "total_requests": self.total_requests,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class RetryPolicy:
    """重试策略"""
    policy_id: str
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_multiplier: float = 2.0
    max_delay: float = 60.0
    retry_on_status: List[int] = field(default_factory=lambda: [500, 502, 503, 504])
    retry_on_exceptions: List[str] = field(default_factory=lambda: ["TimeoutError", "ConnectionError"])
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "backoff_multiplier": self.backoff_multiplier,
            "max_delay": self.max_delay,
            "retry_on_status": self.retry_on_status,
            "retry_on_exceptions": self.retry_on_exceptions,
            "metadata": self.metadata,
        }


class Level4HttpClientModule(ExecuteModuleBase):
    """
    四级HTTP客户端模块

    职责：
    1. HTTP请求发送与响应处理
    2. 连接池管理
    3. 重试机制
    4. 超时控制
    5. 请求拦截与响应处理
    6. 请求/响应日志记录
    """

    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL4
        self._state.module_name = "Level4HttpClientModule"
        self._logger = Logger(f"L4HC_{self.module_id}")

        # 请求存储
        self._requests: Dict[str, HttpRequest] = {}
        # 响应存储
        self._responses: Dict[str, HttpResponse] = {}
        # 连接池
        self._connection_pools: Dict[str, ConnectionPool] = {}
        # 重试策略
        self._retry_policies: Dict[str, RetryPolicy] = {}
        # 请求拦截器
        self._request_interceptors: List[Callable] = []
        # 响应拦截器
        self._response_interceptors: List[Callable] = []
        # 请求历史
        self._request_history: List[Dict[str, Any]] = []

    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("四级HTTP客户端模块初始化开始")

            # 1. 加载配置
            self._load_config(request)

            # 2. 初始化存储
            self._requests = {}
            self._responses = {}
            self._connection_pools = {}
            self._retry_policies = {}
            self._request_interceptors = []
            self._response_interceptors = []
            self._request_history = []

            # 3. 加载默认重试策略
            self._load_default_retry_policies()

            self._logger.info("四级HTTP客户端模块初始化完成")

            return InitResult.success_result(
                module_id=self.module_id,
                message="四级HTTP客户端模块初始化成功"
            )

        except Exception as e:
            self._logger.error(f"四级HTTP客户端模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L4HC_INIT_FAILED",
                error_detail=str(e)
            )

    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "default_timeout": 30,
            "default_retries": 3,
            "max_history": 1000,
            "verify_ssl": True,
            "follow_redirects": True,
            "default_headers": {
                "User-Agent": "Level4HttpClient/1.0",
                "Accept": "application/json",
            },
        }
        if request.task_param:
            custom_config = request.task_param.get_param("http_client_config", {})
            self._config.update(custom_config)

    def _load_default_retry_policies(self) -> None:
        """加载默认重试策略"""
        default_policies = [
            RetryPolicy(
                policy_id="policy_default",
                max_retries=3,
                retry_delay=1.0,
                backoff_multiplier=2.0,
                max_delay=30.0,
                retry_on_status=[500, 502, 503, 504],
            ),
            RetryPolicy(
                policy_id="policy_aggressive",
                max_retries=5,
                retry_delay=0.5,
                backoff_multiplier=1.5,
                max_delay=60.0,
                retry_on_status=[408, 429, 500, 502, 503, 504],
            ),
        ]
        for policy in default_policies:
            self._retry_policies[policy.policy_id] = policy

    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("四级HTTP客户端模块执行开始")

        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()

            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "send_request")

            if operation == "send_request":
                result = self._send_request_operation(input_data)
            elif operation == "create_pool":
                result = self._create_pool_operation(input_data)
            elif operation == "get_pool":
                result = self._get_pool_operation(input_data)
            elif operation == "add_retry_policy":
                result = self._add_retry_policy_operation(input_data)
            elif operation == "get_request":
                result = self._get_request_operation(input_data)
            elif operation == "get_response":
                result = self._get_response_operation(input_data)
            elif operation == "get_history":
                result = self._get_history_operation(input_data)
            elif operation == "get_stats":
                result = self._get_stats_operation()
            elif operation == "clear_history":
                result = self._clear_history_operation()
            else:
                result = {"error": f"未知操作: {operation}"}

            self._logger.info("四级HTTP客户端模块执行完成")

            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level4HttpClientModule",
                    "http_client_summary": {
                        "total_requests": len(self._requests),
                        "total_responses": len(self._responses),
                        "total_pools": len(self._connection_pools),
                        "total_policies": len(self._retry_policies),
                        "history_size": len(self._request_history),
                    },
                },
                message="四级HTTP客户端模块执行成功"
            )

        except Exception as e:
            self._logger.error(f"四级HTTP客户端模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L4HC_EXECUTION_FAILED",
                error_detail=str(e)
            )

    def _send_request_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """发送HTTP请求"""
        import uuid
        import time

        method = HttpMethod(input_data.get("method", "GET"))
        url = input_data.get("url", "")
        headers = input_data.get("headers", {})
        params = input_data.get("params", {})
        body = input_data.get("body")
        timeout = input_data.get("timeout", self._config.get("default_timeout", 30))
        retries = input_data.get("retries", self._config.get("default_retries", 3))
        policy_id = input_data.get("policy_id", "policy_default")

        if not url:
            return {"operation": "send_request", "error": "URL不能为空", "success": False}

        request_id = str(uuid.uuid4())

        # 合并默认请求头
        default_headers = self._config.get("default_headers", {})
        merged_headers = {**default_headers, **headers}

        http_request = HttpRequest(
            request_id=request_id,
            method=method,
            url=url,
            headers=merged_headers,
            params=params,
            body=body,
            timeout=timeout,
            retries=retries,
            metadata=input_data.get("metadata", {}),
        )
        self._requests[request_id] = http_request

        # 执行请求拦截器
        for interceptor in self._request_interceptors:
            try:
                interceptor(http_request)
            except Exception as e:
                self._logger.warning(f"请求拦截器执行失败: {e}")

        # 发送请求（带重试）
        response = self._execute_request_with_retry(http_request, policy_id)

        # 执行响应拦截器
        for interceptor in self._response_interceptors:
            try:
                interceptor(response)
            except Exception as e:
                self._logger.warning(f"响应拦截器执行失败: {e}")

        self._responses[response.response_id] = response

        # 记录历史
        self._request_history.append({
            "request_id": request_id,
            "method": method.value,
            "url": url,
            "status_code": response.status_code,
            "elapsed_ms": response.elapsed_ms,
            "timestamp": datetime.now().isoformat(),
            "success": response.is_success(),
        })

        # 限制历史记录数量
        max_history = self._config.get("max_history", 1000)
        if len(self._request_history) > max_history:
            self._request_history = self._request_history[-max_history:]

        return {
            "operation": "send_request",
            "request_id": request_id,
            "response_id": response.response_id,
            "status_code": response.status_code,
            "success": response.is_success(),
            "elapsed_ms": response.elapsed_ms,
            "error": response.error,
        }

    def _execute_request_with_retry(self, http_request: HttpRequest, policy_id: str) -> HttpResponse:
        """带重试执行请求"""
        import uuid
        import time

        policy = self._retry_policies.get(policy_id, RetryPolicy(policy_id="default"))
        response_id = str(uuid.uuid4())

        last_error = None
        delay = policy.retry_delay

        for attempt in range(policy.max_retries + 1):
            start_time = time.time()
            try:
                response = self._execute_single_request(http_request, response_id)
                elapsed_ms = (time.time() - start_time) * 1000
                response.elapsed_ms = elapsed_ms

                # 检查是否需要重试
                if not response.is_success() and response.status_code in policy.retry_on_status:
                    if attempt < policy.max_retries:
                        last_error = f"HTTP {response.status_code}"
                        time.sleep(delay)
                        delay = min(delay * policy.backoff_multiplier, policy.max_delay)
                        continue

                return response

            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                last_error = str(e)

                # 检查是否需要重试
                if attempt < policy.max_retries:
                    time.sleep(delay)
                    delay = min(delay * policy.backoff_multiplier, policy.max_delay)
                    continue

                # 所有重试失败
                return HttpResponse(
                    response_id=response_id,
                    request_id=http_request.request_id,
                    status_code=0,
                    error=last_error,
                    elapsed_ms=elapsed_ms,
                )

        return HttpResponse(
            response_id=response_id,
            request_id=http_request.request_id,
            status_code=0,
            error=last_error or "未知错误",
            elapsed_ms=0,
        )

    def _execute_single_request(self, http_request: HttpRequest, response_id: str) -> HttpResponse:
        """执行单次请求"""
        try:
            # 构建URL
            url = http_request.url
            if http_request.params:
                query_string = urllib.parse.urlencode(http_request.params)
                url = f"{url}?{query_string}"

            # 构建请求体
            data = None
            if http_request.body is not None:
                if isinstance(http_request.body, dict):
                    data = json.dumps(http_request.body).encode("utf-8")
                else:
                    data = str(http_request.body).encode("utf-8")

            # 创建请求
            req = urllib.request.Request(
                url=url,
                data=data,
                method=http_request.method.value,
                headers=http_request.headers,
            )

            # SSL配置
            context = ssl.create_default_context()
            if not self._config.get("verify_ssl", True):
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

            # 发送请求
            with urllib.request.urlopen(req, timeout=http_request.timeout, context=context) as resp:
                body = resp.read().decode("utf-8")
                headers = dict(resp.headers)
                content_type = headers.get("Content-Type", "")

                # 尝试解析JSON
                parsed_body = body
                if "application/json" in content_type:
                    try:
                        parsed_body = json.loads(body)
                    except json.JSONDecodeError:
                        parsed_body = body

                return HttpResponse(
                    response_id=response_id,
                    request_id=http_request.request_id,
                    status_code=resp.status,
                    headers=headers,
                    body=parsed_body,
                    content_type=content_type,
                    content_length=len(body),
                )

        except urllib.error.HTTPError as e:
            return HttpResponse(
                response_id=response_id,
                request_id=http_request.request_id,
                status_code=e.code,
                headers=dict(e.headers) if e.headers else {},
                body=e.read().decode("utf-8") if e.fp else None,
                error=str(e),
            )
        except Exception as e:
            return HttpResponse(
                response_id=response_id,
                request_id=http_request.request_id,
                status_code=0,
                error=str(e),
            )

    def _create_pool_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建连接池"""
        import uuid

        pool_id = str(uuid.uuid4())
        host = input_data.get("host", "localhost")
        port = input_data.get("port", 80)

        pool = ConnectionPool(
            pool_id=pool_id,
            host=host,
            port=port,
            max_connections=input_data.get("max_connections", 10),
            idle_timeout=input_data.get("idle_timeout", 60),
            metadata=input_data.get("metadata", {}),
        )
        self._connection_pools[pool_id] = pool

        return {
            "operation": "create_pool",
            "pool_id": pool_id,
            "host": host,
            "port": port,
            "created": True,
        }

    def _get_pool_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取连接池信息"""
        pool_id = input_data.get("pool_id")

        if not pool_id or pool_id not in self._connection_pools:
            return {"operation": "get_pool", "error": "连接池不存在"}

        pool = self._connection_pools[pool_id]
        return {
            "operation": "get_pool",
            "pool": pool.to_dict(),
        }

    def _add_retry_policy_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加重试策略"""
        import uuid

        policy_id = str(uuid.uuid4())
        policy = RetryPolicy(
            policy_id=policy_id,
            max_retries=input_data.get("max_retries", 3),
            retry_delay=input_data.get("retry_delay", 1.0),
            backoff_multiplier=input_data.get("backoff_multiplier", 2.0),
            max_delay=input_data.get("max_delay", 60.0),
            retry_on_status=input_data.get("retry_on_status", [500, 502, 503, 504]),
            retry_on_exceptions=input_data.get("retry_on_exceptions", ["TimeoutError", "ConnectionError"]),
            metadata=input_data.get("metadata", {}),
        )
        self._retry_policies[policy_id] = policy

        return {
            "operation": "add_retry_policy",
            "policy_id": policy_id,
            "added": True,
        }

    def _get_request_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取请求信息"""
        request_id = input_data.get("request_id")

        if not request_id or request_id not in self._requests:
            return {"operation": "get_request", "error": "请求不存在"}

        request = self._requests[request_id]
        return {
            "operation": "get_request",
            "request": request.to_dict(),
        }

    def _get_response_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取响应信息"""
        response_id = input_data.get("response_id")

        if not response_id or response_id not in self._responses:
            return {"operation": "get_response", "error": "响应不存在"}

        response = self._responses[response_id]
        return {
            "operation": "get_response",
            "response": response.to_dict(),
        }

    def _get_history_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取请求历史"""
        limit = input_data.get("limit", 100)
        method = input_data.get("method")

        history = self._request_history
        if method:
            history = [h for h in history if h["method"] == method]

        history = sorted(history, key=lambda h: h["timestamp"], reverse=True)[:limit]

        return {
            "operation": "get_history",
            "total": len(self._request_history),
            "returned": len(history),
            "history": history,
        }

    def _get_stats_operation(self) -> Dict[str, Any]:
        """获取统计信息"""
        success_count = sum(1 for r in self._request_history if r.get("success", False))
        total_count = len(self._request_history)

        status_distribution = {}
        for h in self._request_history:
            status = h.get("status_code", 0)
            category = f"{status // 100}xx"
            status_distribution[category] = status_distribution.get(category, 0) + 1

        avg_elapsed = sum(h.get("elapsed_ms", 0) for h in self._request_history) / total_count if total_count > 0 else 0

        return {
            "operation": "get_stats",
            "total_requests": total_count,
            "success_count": success_count,
            "failure_count": total_count - success_count,
            "success_rate": success_count / total_count if total_count > 0 else 0,
            "status_distribution": status_distribution,
            "avg_elapsed_ms": round(avg_elapsed, 2),
            "active_pools": len(self._connection_pools),
            "total_policies": len(self._retry_policies),
        }

    def _clear_history_operation(self) -> Dict[str, Any]:
        """清除历史记录"""
        count = len(self._request_history)
        self._request_history = []

        return {
            "operation": "clear_history",
            "cleared_count": count,
            "success": True,
        }

    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("四级HTTP客户端模块校验开始")

        checks = []

        if isinstance(self._requests, dict):
            checks.append("requests_valid")
        if isinstance(self._responses, dict):
            checks.append("responses_valid")
        if isinstance(self._connection_pools, dict):
            checks.append("pools_valid")
        if isinstance(self._retry_policies, dict) and len(self._retry_policies) > 0:
            checks.append("policies_valid")
        if self._state.module_level == ModuleLevel.LEVEL4:
            checks.append("level_valid")
        if isinstance(self._request_history, list):
            checks.append("history_valid")

        all_passed = len(checks) == 6

        if all_passed:
            return CheckResult.passed_result(
                check_type="http_client_validation",
                message="四级HTTP客户端模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="http_client_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )

    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("request_count", len(self._requests))
        snapshot.set_state("response_count", len(self._responses))
        snapshot.set_state("pool_count", len(self._connection_pools))
        snapshot.set_state("policy_count", len(self._retry_policies))
        snapshot.set_state("history_count", len(self._request_history))
        snapshot.metadata["module_type"] = "Level4HttpClientModule"

    # 公共接口
    def send_request(self, method: str, url: str, headers: Dict[str, str] = None,
                     params: Dict[str, str] = None, body: Any = None,
                     timeout: int = 30) -> HttpResponse:
        """发送HTTP请求"""
        import uuid
        request_id = str(uuid.uuid4())
        http_request = HttpRequest(
            request_id=request_id,
            method=HttpMethod(method),
            url=url,
            headers=headers or {},
            params=params or {},
            body=body,
            timeout=timeout,
        )
        self._requests[request_id] = http_request
        response = self._execute_request_with_retry(http_request, "policy_default")
        self._responses[response.response_id] = response
        return response

    def get(self, url: str, params: Dict[str, str] = None, headers: Dict[str, str] = None) -> HttpResponse:
        """发送GET请求"""
        return self.send_request("GET", url, headers=headers, params=params)

    def post(self, url: str, body: Any = None, headers: Dict[str, str] = None) -> HttpResponse:
        """发送POST请求"""
        return self.send_request("POST", url, headers=headers, body=body)

    def add_request_interceptor(self, interceptor: Callable) -> None:
        """添加请求拦截器"""
        self._request_interceptors.append(interceptor)

    def add_response_interceptor(self, interceptor: Callable) -> None:
        """添加响应拦截器"""
        self._response_interceptors.append(interceptor)

    def create_connection_pool(self, host: str, port: int, max_connections: int = 10) -> str:
        """创建连接池"""
        import uuid
        pool_id = str(uuid.uuid4())
        pool = ConnectionPool(
            pool_id=pool_id,
            host=host,
            port=port,
            max_connections=max_connections,
        )
        self._connection_pools[pool_id] = pool
        return pool_id

    def get_request_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取请求历史"""
        return self._request_history[-limit:]

    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level4HttpClientModule",
    "HttpMethod",
    "HttpStatusCategory",
    "HttpRequest",
    "HttpResponse",
    "ConnectionPool",
    "RetryPolicy",
]
