"""
阶段59：四级文件处理模块
Level4FileHandlerModule

职责定义：
- 文件读取
- 文件写入
- 文件监控
- 文件转换
- 文件校验
- 文件归档
"""

from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import os
import hashlib
import json
import base64

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


class FileOperation(Enum):
    """文件操作类型"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    COPY = "copy"
    MOVE = "move"
    RENAME = "rename"
    APPEND = "append"


class FileType(Enum):
    """文件类型"""
    TEXT = "text"
    BINARY = "binary"
    JSON = "json"
    CSV = "csv"
    XML = "xml"
    YAML = "yaml"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    ARCHIVE = "archive"
    UNKNOWN = "unknown"


@dataclass
class FileInfo:
    """文件信息"""
    file_id: str
    path: str
    name: str
    size: int
    file_type: FileType
    mime_type: str
    checksum: str
    created_at: datetime
    modified_at: datetime
    permissions: str
    is_directory: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_id": self.file_id,
            "path": self.path,
            "name": self.name,
            "size": self.size,
            "file_type": self.file_type.value,
            "mime_type": self.mime_type,
            "checksum": self.checksum,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "permissions": self.permissions,
            "is_directory": self.is_directory,
            "metadata": self.metadata,
        }


@dataclass
class FileContent:
    """文件内容"""
    content_id: str
    file_id: str
    data: Any
    encoding: str
    line_count: int
    word_count: int
    char_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    read_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_id": self.content_id,
            "file_id": self.file_id,
            "data_preview": str(self.data)[:200] if self.data else None,
            "encoding": self.encoding,
            "line_count": self.line_count,
            "word_count": self.word_count,
            "char_count": self.char_count,
            "metadata": self.metadata,
            "read_at": self.read_at.isoformat(),
        }


@dataclass
class FileWatcher:
    """文件监控器"""
    watcher_id: str
    path: str
    recursive: bool
    events: List[str]
    callback: Optional[str] = None
    enabled: bool = True
    last_check: Optional[datetime] = None
    change_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "watcher_id": self.watcher_id,
            "path": self.path,
            "recursive": self.recursive,
            "events": self.events,
            "callback": self.callback,
            "enabled": self.enabled,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "change_count": self.change_count,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class FileArchive:
    """文件归档"""
    archive_id: str
    name: str
    source_paths: List[str]
    archive_path: str
    compression: str
    size_before: int
    size_after: int
    file_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "archive_id": self.archive_id,
            "name": self.name,
            "source_paths": self.source_paths,
            "archive_path": self.archive_path,
            "compression": self.compression,
            "size_before": self.size_before,
            "size_after": self.size_after,
            "file_count": self.file_count,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class Level4FileHandlerModule(ExecuteModuleBase):
    """
    四级文件处理模块

    职责：
    1. 文件读取与解析
    2. 文件写入与序列化
    3. 文件监控
    4. 文件转换
    5. 文件校验（校验和）
    6. 文件归档
    7. 文件元数据管理
    """

    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL4
        self._state.module_name = "Level4FileHandlerModule"
        self._logger = Logger(f"L4FH_{self.module_id}")

        # 文件信息存储
        self._files: Dict[str, FileInfo] = {}
        # 文件内容缓存
        self._contents: Dict[str, FileContent] = {}
        # 文件监控器
        self._watchers: Dict[str, FileWatcher] = {}
        # 归档记录
        self._archives: List[FileArchive] = []
        # 文件操作历史
        self._operation_history: List[Dict[str, Any]] = []
        # 允许的操作路径
        self._allowed_paths: List[str] = []

    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("四级文件处理模块初始化开始")

            # 1. 加载配置
            self._load_config(request)

            # 2. 初始化存储
            self._files = {}
            self._contents = {}
            self._watchers = {}
            self._archives = []
            self._operation_history = []

            self._logger.info("四级文件处理模块初始化完成")

            return InitResult.success_result(
                module_id=self.module_id,
                message="四级文件处理模块初始化成功"
            )

        except Exception as e:
            self._logger.error(f"四级文件处理模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L4FH_INIT_FAILED",
                error_detail=str(e)
            )

    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "max_file_size_mb": 100,
            "allowed_extensions": [".txt", ".json", ".csv", ".xml", ".yaml", ".log"],
            "max_history": 1000,
            "cache_content": True,
            "default_encoding": "utf-8",
        }
        if request.task_param:
            custom_config = request.task_param.get_param("file_handler_config", {})
            self._config.update(custom_config)

    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("四级文件处理模块执行开始")

        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()

            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "read_file")

            if operation == "read_file":
                result = self._read_file_operation(input_data)
            elif operation == "write_file":
                result = self._write_file_operation(input_data)
            elif operation == "delete_file":
                result = self._delete_file_operation(input_data)
            elif operation == "copy_file":
                result = self._copy_file_operation(input_data)
            elif operation == "move_file":
                result = self._move_file_operation(input_data)
            elif operation == "get_file_info":
                result = self._get_file_info_operation(input_data)
            elif operation == "list_directory":
                result = self._list_directory_operation(input_data)
            elif operation == "create_watcher":
                result = self._create_watcher_operation(input_data)
            elif operation == "check_watcher":
                result = self._check_watcher_operation(input_data)
            elif operation == "calculate_checksum":
                result = self._calculate_checksum_operation(input_data)
            elif operation == "convert_file":
                result = self._convert_file_operation(input_data)
            elif operation == "get_history":
                result = self._get_history_operation(input_data)
            elif operation == "get_stats":
                result = self._get_stats_operation()
            else:
                result = {"error": f"未知操作: {operation}"}

            self._logger.info("四级文件处理模块执行完成")

            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level4FileHandlerModule",
                    "file_handler_summary": {
                        "total_files": len(self._files),
                        "total_watchers": len(self._watchers),
                        "total_archives": len(self._archives),
                        "history_size": len(self._operation_history),
                    },
                },
                message="四级文件处理模块执行成功"
            )

        except Exception as e:
            self._logger.error(f"四级文件处理模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L4FH_EXECUTION_FAILED",
                error_detail=str(e)
            )

    def _read_file_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """读取文件"""
        import uuid

        file_path = input_data.get("file_path", "")
        encoding = input_data.get("encoding", self._config.get("default_encoding", "utf-8"))
        as_binary = input_data.get("as_binary", False)

        if not file_path:
            return {"operation": "read_file", "error": "文件路径不能为空", "success": False}

        try:
            if as_binary:
                with open(file_path, "rb") as f:
                    data = f.read()
                content_data = base64.b64encode(data).decode("utf-8")
                line_count = 0
                word_count = 0
                char_count = len(data)
            else:
                with open(file_path, "r", encoding=encoding) as f:
                    data = f.read()
                content_data = data
                line_count = len(data.splitlines())
                word_count = len(data.split())
                char_count = len(data)

            file_id = str(uuid.uuid4())
            content_id = str(uuid.uuid4())

            # 获取文件信息
            stat = os.stat(file_path)
            file_type = self._detect_file_type(file_path)
            mime_type = self._get_mime_type(file_type)
            checksum = self._calculate_checksum_file(file_path)

            file_info = FileInfo(
                file_id=file_id,
                path=file_path,
                name=os.path.basename(file_path),
                size=stat.st_size,
                file_type=file_type,
                mime_type=mime_type,
                checksum=checksum,
                created_at=datetime.fromtimestamp(stat.st_ctime),
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                permissions=oct(stat.st_mode)[-3:],
                is_directory=os.path.isdir(file_path),
                metadata=input_data.get("metadata", {}),
            )
            self._files[file_id] = file_info

            file_content = FileContent(
                content_id=content_id,
                file_id=file_id,
                data=content_data,
                encoding=encoding,
                line_count=line_count,
                word_count=word_count,
                char_count=char_count,
            )
            if self._config.get("cache_content", True):
                self._contents[content_id] = file_content

            # 记录操作
            self._record_operation("read", file_path, True)

            return {
                "operation": "read_file",
                "file_id": file_id,
                "content_id": content_id,
                "file_info": file_info.to_dict(),
                "content_preview": str(content_data)[:200] if content_data else None,
                "line_count": line_count,
                "word_count": word_count,
                "char_count": char_count,
                "success": True,
            }

        except FileNotFoundError:
            self._record_operation("read", file_path, False, "文件不存在")
            return {"operation": "read_file", "error": "文件不存在", "success": False}
        except PermissionError:
            self._record_operation("read", file_path, False, "权限不足")
            return {"operation": "read_file", "error": "权限不足", "success": False}
        except Exception as e:
            self._record_operation("read", file_path, False, str(e))
            return {"operation": "read_file", "error": str(e), "success": False}

    def _write_file_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """写入文件"""
        import uuid

        file_path = input_data.get("file_path", "")
        data = input_data.get("data", "")
        encoding = input_data.get("encoding", self._config.get("default_encoding", "utf-8"))
        append = input_data.get("append", False)

        if not file_path:
            return {"operation": "write_file", "error": "文件路径不能为空", "success": False}

        try:
            mode = "a" if append else "w"
            with open(file_path, mode, encoding=encoding) as f:
                if isinstance(data, dict):
                    f.write(json.dumps(data, ensure_ascii=False, indent=2))
                elif isinstance(data, list):
                    for item in data:
                        f.write(str(item) + "\n")
                else:
                    f.write(str(data))

            file_id = str(uuid.uuid4())
            stat = os.stat(file_path)
            file_type = self._detect_file_type(file_path)

            file_info = FileInfo(
                file_id=file_id,
                path=file_path,
                name=os.path.basename(file_path),
                size=stat.st_size,
                file_type=file_type,
                mime_type=self._get_mime_type(file_type),
                checksum=self._calculate_checksum_file(file_path),
                created_at=datetime.fromtimestamp(stat.st_ctime),
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                permissions=oct(stat.st_mode)[-3:],
            )
            self._files[file_id] = file_info

            self._record_operation("write", file_path, True)

            return {
                "operation": "write_file",
                "file_id": file_id,
                "path": file_path,
                "bytes_written": stat.st_size,
                "success": True,
            }

        except PermissionError:
            self._record_operation("write", file_path, False, "权限不足")
            return {"operation": "write_file", "error": "权限不足", "success": False}
        except Exception as e:
            self._record_operation("write", file_path, False, str(e))
            return {"operation": "write_file", "error": str(e), "success": False}

    def _delete_file_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """删除文件"""
        file_path = input_data.get("file_path", "")

        if not file_path:
            return {"operation": "delete_file", "error": "文件路径不能为空", "success": False}

        try:
            if os.path.isdir(file_path):
                os.rmdir(file_path)
            else:
                os.remove(file_path)

            self._record_operation("delete", file_path, True)

            return {
                "operation": "delete_file",
                "path": file_path,
                "deleted": True,
                "success": True,
            }

        except FileNotFoundError:
            self._record_operation("delete", file_path, False, "文件不存在")
            return {"operation": "delete_file", "error": "文件不存在", "success": False}
        except PermissionError:
            self._record_operation("delete", file_path, False, "权限不足")
            return {"operation": "delete_file", "error": "权限不足", "success": False}
        except Exception as e:
            self._record_operation("delete", file_path, False, str(e))
            return {"operation": "delete_file", "error": str(e), "success": False}

    def _copy_file_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """复制文件"""
        import shutil

        source_path = input_data.get("source_path", "")
        dest_path = input_data.get("dest_path", "")

        if not source_path or not dest_path:
            return {"operation": "copy_file", "error": "源路径和目标路径不能为空", "success": False}

        try:
            if os.path.isdir(source_path):
                shutil.copytree(source_path, dest_path)
            else:
                shutil.copy2(source_path, dest_path)

            self._record_operation("copy", f"{source_path} -> {dest_path}", True)

            return {
                "operation": "copy_file",
                "source": source_path,
                "destination": dest_path,
                "copied": True,
                "success": True,
            }

        except FileNotFoundError:
            return {"operation": "copy_file", "error": "源文件不存在", "success": False}
        except Exception as e:
            return {"operation": "copy_file", "error": str(e), "success": False}

    def _move_file_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """移动文件"""
        import shutil

        source_path = input_data.get("source_path", "")
        dest_path = input_data.get("dest_path", "")

        if not source_path or not dest_path:
            return {"operation": "move_file", "error": "源路径和目标路径不能为空", "success": False}

        try:
            shutil.move(source_path, dest_path)

            self._record_operation("move", f"{source_path} -> {dest_path}", True)

            return {
                "operation": "move_file",
                "source": source_path,
                "destination": dest_path,
                "moved": True,
                "success": True,
            }

        except FileNotFoundError:
            return {"operation": "move_file", "error": "源文件不存在", "success": False}
        except Exception as e:
            return {"operation": "move_file", "error": str(e), "success": False}

    def _get_file_info_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取文件信息"""
        file_path = input_data.get("file_path", "")

        if not file_path:
            return {"operation": "get_file_info", "error": "文件路径不能为空", "success": False}

        try:
            stat = os.stat(file_path)
            file_type = self._detect_file_type(file_path)

            return {
                "operation": "get_file_info",
                "path": file_path,
                "name": os.path.basename(file_path),
                "size": stat.st_size,
                "file_type": file_type.value,
                "mime_type": self._get_mime_type(file_type),
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "permissions": oct(stat.st_mode)[-3:],
                "is_directory": os.path.isdir(file_path),
                "exists": True,
                "success": True,
            }

        except FileNotFoundError:
            return {"operation": "get_file_info", "path": file_path, "exists": False, "success": False}
        except Exception as e:
            return {"operation": "get_file_info", "error": str(e), "success": False}

    def _list_directory_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """列出目录内容"""
        dir_path = input_data.get("dir_path", ".")
        recursive = input_data.get("recursive", False)

        try:
            entries = []
            if recursive:
                for root, dirs, files in os.walk(dir_path):
                    for name in dirs:
                        full_path = os.path.join(root, name)
                        entries.append({
                            "name": name,
                            "path": full_path,
                            "type": "directory",
                        })
                    for name in files:
                        full_path = os.path.join(root, name)
                        stat = os.stat(full_path)
                        entries.append({
                            "name": name,
                            "path": full_path,
                            "type": "file",
                            "size": stat.st_size,
                            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        })
            else:
                for name in os.listdir(dir_path):
                    full_path = os.path.join(dir_path, name)
                    if os.path.isdir(full_path):
                        entries.append({"name": name, "path": full_path, "type": "directory"})
                    else:
                        stat = os.stat(full_path)
                        entries.append({
                            "name": name,
                            "path": full_path,
                            "type": "file",
                            "size": stat.st_size,
                            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        })

            return {
                "operation": "list_directory",
                "path": dir_path,
                "recursive": recursive,
                "entry_count": len(entries),
                "entries": entries,
                "success": True,
            }

        except FileNotFoundError:
            return {"operation": "list_directory", "error": "目录不存在", "success": False}
        except PermissionError:
            return {"operation": "list_directory", "error": "权限不足", "success": False}
        except Exception as e:
            return {"operation": "list_directory", "error": str(e), "success": False}

    def _create_watcher_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建文件监控器"""
        import uuid

        watcher_id = str(uuid.uuid4())
        path = input_data.get("path", ".")
        recursive = input_data.get("recursive", False)
        events = input_data.get("events", ["modify", "create", "delete"])

        watcher = FileWatcher(
            watcher_id=watcher_id,
            path=path,
            recursive=recursive,
            events=events,
            callback=input_data.get("callback"),
            metadata=input_data.get("metadata", {}),
        )
        self._watchers[watcher_id] = watcher

        return {
            "operation": "create_watcher",
            "watcher_id": watcher_id,
            "path": path,
            "events": events,
            "created": True,
        }

    def _check_watcher_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查文件监控器"""
        watcher_id = input_data.get("watcher_id")

        if not watcher_id or watcher_id not in self._watchers:
            return {"operation": "check_watcher", "error": "监控器不存在", "success": False}

        watcher = self._watchers[watcher_id]

        # 模拟检查文件变化
        changes = []
        try:
            if os.path.exists(watcher.path):
                current_mtime = os.path.getmtime(watcher.path)
                if watcher.last_check:
                    if current_mtime > watcher.last_check.timestamp():
                        changes.append({"path": watcher.path, "event": "modify"})
                        watcher.change_count += 1
                watcher.last_check = datetime.now()
        except Exception:
            pass

        return {
            "operation": "check_watcher",
            "watcher_id": watcher_id,
            "path": watcher.path,
            "changes_detected": len(changes),
            "changes": changes,
            "total_changes": watcher.change_count,
            "success": True,
        }

    def _calculate_checksum_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """计算文件校验和"""
        file_path = input_data.get("file_path", "")
        algorithm = input_data.get("algorithm", "sha256")

        if not file_path:
            return {"operation": "calculate_checksum", "error": "文件路径不能为空", "success": False}

        try:
            checksum = self._calculate_checksum_file(file_path, algorithm)
            return {
                "operation": "calculate_checksum",
                "path": file_path,
                "algorithm": algorithm,
                "checksum": checksum,
                "success": True,
            }
        except FileNotFoundError:
            return {"operation": "calculate_checksum", "error": "文件不存在", "success": False}
        except Exception as e:
            return {"operation": "calculate_checksum", "error": str(e), "success": False}

    def _convert_file_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """转换文件格式"""
        source_path = input_data.get("source_path", "")
        dest_path = input_data.get("dest_path", "")
        source_format = input_data.get("source_format", "json")
        dest_format = input_data.get("dest_format", "csv")

        if not source_path or not dest_path:
            return {"operation": "convert_file", "error": "源路径和目标路径不能为空", "success": False}

        try:
            # 读取源文件
            with open(source_path, "r", encoding="utf-8") as f:
                data = f.read()

            # 解析源格式
            if source_format == "json":
                parsed = json.loads(data)
            else:
                parsed = data

            # 转换为目标格式
            if dest_format == "json":
                if isinstance(parsed, str):
                    converted = json.dumps({"data": parsed}, ensure_ascii=False, indent=2)
                else:
                    converted = json.dumps(parsed, ensure_ascii=False, indent=2)
            elif dest_format == "csv":
                if isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                    headers = list(parsed[0].keys())
                    lines = [",".join(headers)]
                    for item in parsed:
                        line = ",".join(str(item.get(h, "")) for h in headers)
                        lines.append(line)
                    converted = "\n".join(lines)
                else:
                    converted = str(parsed)
            else:
                converted = str(parsed)

            # 写入目标文件
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(converted)

            return {
                "operation": "convert_file",
                "source": source_path,
                "destination": dest_path,
                "source_format": source_format,
                "dest_format": dest_format,
                "converted": True,
                "success": True,
            }

        except FileNotFoundError:
            return {"operation": "convert_file", "error": "源文件不存在", "success": False}
        except json.JSONDecodeError:
            return {"operation": "convert_file", "error": "JSON解析失败", "success": False}
        except Exception as e:
            return {"operation": "convert_file", "error": str(e), "success": False}

    def _get_history_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取操作历史"""
        limit = input_data.get("limit", 100)
        operation_type = input_data.get("operation_type")

        history = self._operation_history
        if operation_type:
            history = [h for h in history if h.get("operation") == operation_type]

        history = sorted(history, key=lambda h: h["timestamp"], reverse=True)[:limit]

        return {
            "operation": "get_history",
            "total": len(self._operation_history),
            "returned": len(history),
            "history": history,
        }

    def _get_stats_operation(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_ops = len(self._operation_history)
        success_ops = sum(1 for h in self._operation_history if h.get("success", False))

        op_distribution = {}
        for h in self._operation_history:
            op = h.get("operation", "unknown")
            op_distribution[op] = op_distribution.get(op, 0) + 1

        return {
            "operation": "get_stats",
            "total_operations": total_ops,
            "success_count": success_ops,
            "failure_count": total_ops - success_ops,
            "success_rate": success_ops / total_ops if total_ops > 0 else 0,
            "operation_distribution": op_distribution,
            "tracked_files": len(self._files),
            "active_watchers": len([w for w in self._watchers.values() if w.enabled]),
            "total_archives": len(self._archives),
        }

    def _detect_file_type(self, file_path: str) -> FileType:
        """检测文件类型"""
        ext = os.path.splitext(file_path)[1].lower()
        type_map = {
            ".txt": FileType.TEXT,
            ".json": FileType.JSON,
            ".csv": FileType.CSV,
            ".xml": FileType.XML,
            ".yaml": FileType.YAML,
            ".yml": FileType.YAML,
            ".log": FileType.TEXT,
            ".py": FileType.TEXT,
            ".js": FileType.TEXT,
            ".html": FileType.TEXT,
            ".css": FileType.TEXT,
            ".jpg": FileType.IMAGE,
            ".jpeg": FileType.IMAGE,
            ".png": FileType.IMAGE,
            ".gif": FileType.IMAGE,
            ".mp4": FileType.VIDEO,
            ".mp3": FileType.AUDIO,
            ".zip": FileType.ARCHIVE,
            ".tar": FileType.ARCHIVE,
            ".gz": FileType.ARCHIVE,
        }
        return type_map.get(ext, FileType.UNKNOWN)

    def _get_mime_type(self, file_type: FileType) -> str:
        """获取MIME类型"""
        mime_map = {
            FileType.TEXT: "text/plain",
            FileType.JSON: "application/json",
            FileType.CSV: "text/csv",
            FileType.XML: "application/xml",
            FileType.YAML: "application/yaml",
            FileType.BINARY: "application/octet-stream",
            FileType.IMAGE: "image/*",
            FileType.VIDEO: "video/*",
            FileType.AUDIO: "audio/*",
            FileType.ARCHIVE: "application/zip",
            FileType.UNKNOWN: "application/octet-stream",
        }
        return mime_map.get(file_type, "application/octet-stream")

    def _calculate_checksum_file(self, file_path: str, algorithm: str = "sha256") -> str:
        """计算文件校验和"""
        hash_obj = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()

    def _record_operation(self, operation: str, path: str, success: bool, error: str = "") -> None:
        """记录文件操作"""
        self._operation_history.append({
            "operation": operation,
            "path": path,
            "success": success,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        })

        max_history = self._config.get("max_history", 1000)
        if len(self._operation_history) > max_history:
            self._operation_history = self._operation_history[-max_history:]

    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("四级文件处理模块校验开始")

        checks = []

        if isinstance(self._files, dict):
            checks.append("files_valid")
        if isinstance(self._watchers, dict):
            checks.append("watchers_valid")
        if isinstance(self._operation_history, list):
            checks.append("history_valid")
        if self._state.module_level == ModuleLevel.LEVEL4:
            checks.append("level_valid")
        if isinstance(self._archives, list):
            checks.append("archives_valid")
        if isinstance(self._contents, dict):
            checks.append("contents_valid")

        all_passed = len(checks) == 6

        if all_passed:
            return CheckResult.passed_result(
                check_type="file_handler_validation",
                message="四级文件处理模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="file_handler_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )

    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("file_count", len(self._files))
        snapshot.set_state("watcher_count", len(self._watchers))
        snapshot.set_state("archive_count", len(self._archives))
        snapshot.set_state("history_count", len(self._operation_history))
        snapshot.set_state("content_count", len(self._contents))
        snapshot.metadata["module_type"] = "Level4FileHandlerModule"

    # 公共接口
    def read_file(self, file_path: str, encoding: str = "utf-8") -> Optional[str]:
        """读取文件内容"""
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except Exception:
            return None

    def write_file(self, file_path: str, data: Any, encoding: str = "utf-8") -> bool:
        """写入文件"""
        try:
            with open(file_path, "w", encoding=encoding) as f:
                if isinstance(data, dict):
                    f.write(json.dumps(data, ensure_ascii=False, indent=2))
                else:
                    f.write(str(data))
            return True
        except Exception:
            return False

    def create_watcher(self, path: str, events: List[str] = None) -> str:
        """创建文件监控器"""
        import uuid
        watcher_id = str(uuid.uuid4())
        watcher = FileWatcher(
            watcher_id=watcher_id,
            path=path,
            recursive=False,
            events=events or ["modify", "create", "delete"],
        )
        self._watchers[watcher_id] = watcher
        return watcher_id

    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        try:
            stat = os.stat(file_path)
            file_type = self._detect_file_type(file_path)
            return {
                "path": file_path,
                "name": os.path.basename(file_path),
                "size": stat.st_size,
                "file_type": file_type.value,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_directory": os.path.isdir(file_path),
            }
        except Exception:
            return None

    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level4FileHandlerModule",
    "FileOperation",
    "FileType",
    "FileInfo",
    "FileContent",
    "FileWatcher",
    "FileArchive",
]
