# 阶段86-90：Docker容器化
# LongTaskAgent Docker Image

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY core/ /app/core/
COPY core_types/ /app/core_types/
COPY interfaces/ /app/interfaces/
COPY modules/ /app/modules/
COPY system/ /app/system/
COPY utils/ /app/utils/
COPY requirements.txt /app/
COPY README.md /app/

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 设置环境变量
ENV PYTHONPATH=/app
ENV LONG_TASK_AGENT_ENV=production

# 暴露端口（用于监控面板）
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from system.monitoring_dashboard import MonitoringDashboard; print('OK')" || exit 1

# 默认命令
CMD ["python", "-m", "cli.main"]
