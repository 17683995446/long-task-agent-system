#!/usr/bin/env python3
"""
阶段91-95：CLI工具
CLI Tools

命令行接口工具，提供以下命令：
- init: 初始化系统
- run: 执行任务
- status: 查看系统状态
- monitor: 启动监控面板
- validate: 验证模块
- snapshot: 创建快照
"""

import argparse
import sys
import json
from typing import Optional

sys.path.insert(0, '/workspace')

from system.module_tree import ModuleTreeBuilder
from system.execution_engine import ExecutionEngine
from system.monitoring_dashboard import MonitoringDashboard
from core_types.core_types import TaskID, ModuleInput, ModuleParam
from interfaces.module_interface import InitRequest, InitContext


class CLI:
    """命令行接口"""

    def __init__(self):
        self.parser = self._create_parser()
        self.module_tree = None
        self.execution_engine = None
        self.dashboard = None

    def _create_parser(self) -> argparse.ArgumentParser:
        """创建参数解析器"""
        parser = argparse.ArgumentParser(
            prog='longtask-agent',
            description='LongTaskAgent - 超长任务Agent执行系统'
        )

        subparsers = parser.add_subparsers(dest='command', help='可用命令')

        # init 命令
        init_parser = subparsers.add_parser('init', help='初始化系统')
        init_parser.add_argument('--minimal', action='store_true', help='使用最小配置')

        # run 命令
        run_parser = subparsers.add_parser('run', help='执行任务')
        run_parser.add_argument('--task-id', type=str, help='任务ID')
        run_parser.add_argument('--data', type=str, help='任务数据（JSON格式）')
        run_parser.add_argument('--module-id', type=str, help='目标模块ID')

        # status 命令
        status_parser = subparsers.add_parser('status', help='查看系统状态')
        status_parser.add_argument('--module-id', type=str, help='查看特定模块状态')

        # monitor 命令
        monitor_parser = subparsers.add_parser('monitor', help='启动监控面板')
        monitor_parser.add_argument('--port', type=int, default=8080, help='监控面板端口')

        # validate 命令
        validate_parser = subparsers.add_parser('validate', help='验证模块')
        validate_parser.add_argument('--module-id', type=str, help='要验证的模块ID')
        validate_parser.add_argument('--all', action='store_true', help='验证所有模块')

        # snapshot 命令
        snapshot_parser = subparsers.add_parser('snapshot', help='创建快照')
        snapshot_parser.add_argument('--output', type=str, help='输出文件路径')

        # tree 命令
        tree_parser = subparsers.add_parser('tree', help='显示模块树')

        return parser

    def init(self, args) -> int:
        """初始化系统"""
        print("正在初始化系统...")

        builder = ModuleTreeBuilder()
        if args.minimal:
            self.module_tree = builder.build_minimal_tree()
            print("已构建最小模块树")
        else:
            self.module_tree = builder.build_standard_tree()
            print("已构建标准模块树")

        # 初始化所有模块
        for module in self.module_tree.get_all_modules():
            init_request = InitRequest(
                module_id=module.module_id,
                module_param=ModuleParam(module_id=module.module_id),
            )
            result = module.module_init(init_request, InitContext())
            if result.success:
                print(f"  ✓ {module.module_name}")
            else:
                print(f"  ✗ {module.module_name}: {result.error_detail}")

        # 创建执行引擎和监控面板
        self.execution_engine = ExecutionEngine(self.module_tree)
        self.dashboard = MonitoringDashboard(self.module_tree, self.execution_engine)

        print(f"\n系统初始化完成！共 {self.module_tree.get_module_count()} 个模块")
        return 0

    def run(self, args) -> int:
        """执行任务"""
        if not self.module_tree:
            print("错误：系统未初始化，请先运行 'init' 命令")
            return 1

        task_id = TaskID(args.task_id) if args.task_id else TaskID()
        data = json.loads(args.data) if args.data else {}
        module_input = ModuleInput(task_id=task_id, data=data)

        target_module_id = args.module_id if args.module_id else None

        print(f"正在执行任务: {task_id}")
        record = self.execution_engine.execute_task(
            task_id, module_input, target_module_id
        )

        print(f"\n执行结果:")
        print(f"  状态: {record.status.name}")
        if record.result:
            print(f"  数据: {json.dumps(record.result.data, indent=2, default=str)}")
        if record.error:
            print(f"  错误: {record.error}")

        return 0 if record.status.name == "COMPLETED" else 1

    def status(self, args) -> int:
        """查看系统状态"""
        if not self.module_tree:
            print("错误：系统未初始化，请先运行 'init' 命令")
            return 1

        if args.module_id:
            status = self.dashboard.get_module_status(args.module_id)
            print(json.dumps(status, indent=2, default=str))
        else:
            summary = self.dashboard.get_dashboard_summary()
            print(json.dumps(summary, indent=2, default=str))

        return 0

    def monitor(self, args) -> int:
        """启动监控面板"""
        if not self.module_tree:
            print("错误：系统未初始化，请先运行 'init' 命令")
            return 1

        print(f"启动监控面板在端口 {args.port}...")
        print("按 Ctrl+C 停止")

        # 简单的HTTP服务器实现
        try:
            import http.server
            import socketserver

            class Handler(http.server.SimpleHTTPRequestHandler):
                def do_GET(self):
                    if self.path == '/':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        summary = self.server.dashboard.get_dashboard_summary()
                        self.wfile.write(json.dumps(summary, indent=2, default=str).encode())
                    elif self.path == '/health':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        health = self.server.dashboard.check_health()
                        self.wfile.write(json.dumps(health.to_dict(), indent=2, default=str).encode())
                    else:
                        self.send_response(404)
                        self.end_headers()

            with socketserver.TCPServer(("", args.port), Handler) as httpd:
                httpd.dashboard = self.dashboard
                print(f"监控面板已启动: http://localhost:{args.port}")
                httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n监控面板已停止")

        return 0

    def validate(self, args) -> int:
        """验证模块"""
        if not self.module_tree:
            print("错误：系统未初始化，请先运行 'init' 命令")
            return 1

        if args.all:
            print("验证所有模块...")
            modules = self.module_tree.get_all_modules()
        elif args.module_id:
            module = self.module_tree.get_module(args.module_id)
            if not module:
                print(f"错误：模块未找到: {args.module_id}")
                return 1
            modules = [module]
        else:
            print("错误：请指定 --module-id 或 --all")
            return 1

        all_passed = True
        for module in modules:
            from interfaces.module_interface import ValidationRequest, ValidationContext
            result = module.module_check(ValidationRequest(), ValidationContext())
            status = "✓" if result.passed else "✗"
            print(f"  {status} {module.module_name}")
            if not result.passed:
                all_passed = False

        return 0 if all_passed else 1

    def snapshot(self, args) -> int:
        """创建快照"""
        if not self.module_tree:
            print("错误：系统未初始化，请先运行 'init' 命令")
            return 1

        print("创建系统快照...")
        snapshots = {}
        for module in self.module_tree.get_all_modules():
            from interfaces.module_interface import SnapshotRequest, SnapshotContext
            snapshot = module.create_snapshot(SnapshotRequest(), SnapshotContext())
            snapshots[str(module.module_id)] = {
                "module_name": module.module_name,
                "state_data": snapshot.state_data,
                "metadata": snapshot.metadata,
            }

        output = args.output or "snapshot.json"
        with open(output, 'w') as f:
            json.dump(snapshots, f, indent=2, default=str)

        print(f"快照已保存到: {output}")
        return 0

    def tree(self, args) -> int:
        """显示模块树"""
        if not self.module_tree:
            print("错误：系统未初始化，请先运行 'init' 命令")
            return 1

        print(self.module_tree.print_tree())
        return 0

    def execute(self, args=None) -> int:
        """执行命令"""
        if args is None:
            args = self.parser.parse_args()

        if not args.command:
            self.parser.print_help()
            return 1

        # 自动初始化（除了init命令）
        if args.command != 'init':
            builder = ModuleTreeBuilder()
            self.module_tree = builder.build_minimal_tree()
            for module in self.module_tree.get_all_modules():
                init_request = InitRequest(
                    module_id=module.module_id,
                    module_param=ModuleParam(module_id=module.module_id),
                )
                module.module_init(init_request, InitContext())
            self.execution_engine = ExecutionEngine(self.module_tree)
            self.dashboard = MonitoringDashboard(self.module_tree, self.execution_engine)

        command_func = getattr(self, args.command, None)
        if command_func:
            return command_func(args)
        else:
            print(f"错误：未知命令: {args.command}")
            return 1


def main():
    """主入口"""
    cli = CLI()
    return cli.execute()


if __name__ == "__main__":
    sys.exit(main())
