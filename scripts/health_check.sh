#!/bin/bash

#==============================================================================
# CodeGate 健康检查脚本
# 用途：定期检查 CodeGate 服务运行状态，异常时发送告警
# 使用：添加到 crontab 定时执行
#==============================================================================

#------------------------------------------------------------------------------
# 配置项
#------------------------------------------------------------------------------

# CodeGate 服务地址
CODEGATE_URL="${CODEGATE_URL:-http://localhost:8000}"

# 健康检查接口
HEALTH_ENDPOINT="/api/health"

# 完整检查地址
HEALTH_URL="${CODEGATE_URL}${HEALTH_ENDPOINT}"

# 连接超时时间（秒）
TIMEOUT=10

# 最大重试次数
MAX_RETRIES=3

# 重试间隔（秒）
RETRY_INTERVAL=5

# 日志文件路径
LOG_DIR="/opt/codegate/logs"
LOG_FILE="${LOG_DIR}/health_check.log"

# 告警配置（可选）
# ALERT_EMAIL="admin@company.com"
# ALERT_WEBHOOK="https://your-webhook-url"

#------------------------------------------------------------------------------
# 初始化
#------------------------------------------------------------------------------

# 创建日志目录
mkdir -p "${LOG_DIR}"

# 获取当前时间
CURRENT_TIME=$(date '+%Y-%m-%d %H:%M:%S')

#------------------------------------------------------------------------------
# 函数定义
#------------------------------------------------------------------------------

# 日志函数
log() {
    local level=$1
    local message=$2
    echo "[${CURRENT_TIME}] [${level}] ${message}" >> "${LOG_FILE}"

    # 如果是 ERROR 级别，同时输出到标准错误
    if [ "${level}" = "ERROR" ]; then
        echo "[${CURRENT_TIME}] [${level}] ${message}" >&2
    fi
}

# 发送告警（可根据需要扩展）
send_alert() {
    local message=$1

    log "ALERT" "${message}"

    # 邮件告警（需要配置邮件服务）
    # if [ -n "${ALERT_EMAIL}" ]; then
    #     echo "${message}" | mail -s "CodeGate Alert" "${ALERT_EMAIL}"
    # fi

    # Webhook 告警（如钉钉、企业微信等）
    # if [ -n "${ALERT_WEBHOOK}" ]; then
    #     curl -s -X POST "${ALERT_WEBHOOK}" \
    #         -H "Content-Type: application/json" \
    #         -d "{\"message\": \"${message}\"}"
    # fi
}

# 检查服务状态
check_health() {
    local retry_count=0
    local http_code=""
    local response=""

    while [ ${retry_count} -lt ${MAX_RETRIES} ]; do
        # 发送健康检查请求
        response=$(curl -s -o /tmp/codegate_health_response.txt \
            -w "%{http_code}" \
            --connect-timeout ${TIMEOUT} \
            --max-time ${TIMEOUT} \
            "${HEALTH_URL}" 2>/dev/null)

        http_code=$?

        # 检查 curl 是否成功执行
        if [ ${http_code} -eq 0 ]; then
            # 读取响应内容
            local body=$(cat /tmp/codegate_health_response.txt 2>/dev/null)

            # 检查响应是否包含 healthy
            if echo "${body}" | grep -q '"status".*"healthy"'; then
                log "INFO" "服务正常 - HTTP ${response}"
                return 0
            else
                log "WARN" "服务响应异常 - 响应内容: ${body}"
            fi
        fi

        retry_count=$((retry_count + 1))

        if [ ${retry_count} -lt ${MAX_RETRIES} ]; then
            log "INFO" "第 ${retry_count} 次检查失败，${RETRY_INTERVAL} 秒后重试..."
            sleep ${RETRY_INTERVAL}
        fi
    done

    # 所有重试都失败
    log "ERROR" "服务异常 - 连续 ${MAX_RETRIES} 次检查失败"
    return 1
}

# 检查进程是否存在
check_process() {
    local process_count=$(pgrep -f "gunicorn.*codegate" | wc -l)

    if [ ${process_count} -eq 0 ]; then
        log "ERROR" "CodeGate 进程不存在"
        return 1
    fi

    log "INFO" "发现 ${process_count} 个 CodeGate 进程"
    return 0
}

# 检查端口是否监听
check_port() {
    local port=$(echo "${CODEGATE_URL}" | grep -oE ':[0-9]+' | tr -d ':')

    if [ -z "${port}" ]; then
        port=8000
    fi

    if ! netstat -tlnp 2>/dev/null | grep -q ":${port} "; then
        if ! ss -tlnp 2>/dev/null | grep -q ":${port} "; then
            log "ERROR" "端口 ${port} 未监听"
            return 1
        fi
    fi

    log "INFO" "端口 ${port} 正在监听"
    return 0
}

# 检查磁盘空间
check_disk() {
    local disk_usage=$(df -h /opt/codegate 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%')

    if [ -n "${disk_usage}" ] && [ ${disk_usage} -gt 90 ]; then
        log "WARN" "磁盘使用率过高: ${disk_usage}%"
    fi

    log "INFO" "磁盘使用率: ${disk_usage}%"
    return 0
}

# 尝试重启服务
restart_service() {
    log "INFO" "尝试重启 CodeGate 服务..."

    systemctl restart codegate

    if [ $? -eq 0 ]; then
        log "INFO" "服务重启成功"
        # 等待服务启动
        sleep 10
        # 再次检查
        if check_health; then
            send_alert "CodeGate 服务已恢复"
            return 0
        fi
    fi

    log "ERROR" "服务重启失败"
    return 1
}

#------------------------------------------------------------------------------
# 主程序
#------------------------------------------------------------------------------

main() {
    log "INFO" "========== 开始健康检查 =========="

    local has_error=0

    # 1. 检查进程
    if ! check_process; then
        has_error=1
    fi

    # 2. 检查端口
    if ! check_port; then
        has_error=1
    fi

    # 3. 检查健康接口
    if ! check_health; then
        has_error=1
    fi

    # 4. 检查磁盘
    check_disk

    # 清理临时文件
    rm -f /tmp/codegate_health_response.txt

    # 处理检查结果
    if [ ${has_error} -eq 1 ]; then
        send_alert "CodeGate 服务异常，请及时处理！"

        # 可选：自动尝试重启
        # restart_service

        log "INFO" "========== 健康检查失败 =========="
        exit 1
    fi

    log "INFO" "========== 健康检查通过 =========="
    exit 0
}

# 执行主程序
main
