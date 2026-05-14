#!/bin/bash

#==============================================================================
# CodeGate 部署脚本
# 用途：一键部署 CodeGate 服务到服务器
#==============================================================================

set -e

#------------------------------------------------------------------------------
# 配置项
#------------------------------------------------------------------------------

# 项目名称
PROJECT_NAME="codegate"

# 部署目录
DEPLOY_DIR="/opt/${PROJECT_NAME}"

# Git 仓库地址（可选，用于拉取代码）
# GIT_REPO="https://github.com/your-repo/codegate.git"

# Git 分支
GIT_BRANCH="main"

# 服务端口
SERVICE_PORT=8000

# Gunicorn 工作进程数
WORKERS=2

# Python 版本
PYTHON_VERSION="python3"

# 日志文件
LOG_FILE="/tmp/codegate_deploy.log"

#------------------------------------------------------------------------------
# 颜色输出
#------------------------------------------------------------------------------

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "${LOG_FILE}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "${LOG_FILE}"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "${LOG_FILE}"
}

#------------------------------------------------------------------------------
# 检查函数
#------------------------------------------------------------------------------

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 用户或 sudo 执行此脚本"
        exit 1
    fi
}

check_python() {
    if ! command -v ${PYTHON_VERSION} &> /dev/null; then
        log_error "Python 未安装，请先安装 Python 3.9+"
        exit 1
    fi

    PYTHON_VER=$(${PYTHON_VERSION} --version 2>&1 | awk '{print $2}')
    log_info "Python 版本: ${PYTHON_VER}"
}

check_pip() {
    if ! command -v pip3 &> /dev/null; then
        log_error "pip 未安装，请先安装 pip"
        exit 1
    fi
}

check_git() {
    if ! command -v git &> /dev/null; then
        log_warn "Git 未安装，将跳过代码拉取"
        return 1
    fi
    return 0
}

#------------------------------------------------------------------------------
# 部署函数
#------------------------------------------------------------------------------

install_dependencies() {
    log_info "安装系统依赖..."

    apt-get update -qq
    apt-get install -y -qq \
        python3 \
        python3-pip \
        python3-venv \
        git \
        curl \
        > /dev/null

    log_success "系统依赖安装完成"
}

create_directories() {
    log_info "创建目录结构..."

    mkdir -p "${DEPLOY_DIR}"
    mkdir -p "${DEPLOY_DIR}/cache/hashes"
    mkdir -p "${DEPLOY_DIR}/reports"
    mkdir -p "${DEPLOY_DIR}/logs"
    mkdir -p "${DEPLOY_DIR}/configs"
    mkdir -p "${DEPLOY_DIR}/src"
    mkdir -p "${DEPLOY_DIR}/test_cases"
    mkdir -p "${DEPLOY_DIR}/scripts"

    log_success "目录创建完成"
}

copy_files() {
    log_info "复制项目文件..."

    # 获取脚本所在目录
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # 复制核心文件
    cp -f "${SCRIPT_DIR}/../app.py" "${DEPLOY_DIR}/" 2>/dev/null || true
    cp -f "${SCRIPT_DIR}/../requirements.txt" "${DEPLOY_DIR}/" 2>/dev/null || true

    # 复制源代码
    cp -rf "${SCRIPT_DIR}/../src/"* "${DEPLOY_DIR}/src/" 2>/dev/null || true

    # 复制配置
    cp -rf "${SCRIPT_DIR}/../configs/"* "${DEPLOY_DIR}/configs/" 2>/dev/null || true

    # 复制脚本
    cp -rf "${SCRIPT_DIR}/"*.sh "${DEPLOY_DIR}/scripts/" 2>/dev/null || true

    # 复制测试用例
    cp -rf "${SCRIPT_DIR}/../test_cases/"* "${DEPLOY_DIR}/test_cases/" 2>/dev/null || true

    log_success "文件复制完成"
}

pull_code() {
    if [ -n "${GIT_REPO}" ]; then
        log_info "从 Git 仓库拉取代码..."

        if [ -d "${DEPLOY_DIR}/.git" ]; then
            cd "${DEPLOY_DIR}"
            git pull origin "${GIT_BRANCH}"
        else
            git clone -b "${GIT_BRANCH}" "${GIT_REPO}" "${DEPLOY_DIR}"
        fi

        log_success "代码拉取完成"
    fi
}

setup_virtualenv() {
    log_info "创建虚拟环境..."

    cd "${DEPLOY_DIR}"

    if [ ! -d "venv" ]; then
        ${PYTHON_VERSION} -m venv venv
    fi

    log_success "虚拟环境创建完成"
}

install_python_packages() {
    log_info "安装 Python 依赖..."

    cd "${DEPLOY_DIR}"

    source venv/bin/activate

    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    pip install gunicorn -q

    deactivate

    log_success "Python 依赖安装完成"
}

create_systemd_service() {
    log_info "创建 systemd 服务..."

    # 获取 API Key
    read -p "请输入 ANTHROPIC_API_KEY: " API_KEY

    cat > /etc/systemd/system/${PROJECT_NAME}.service << EOF
[Unit]
Description=CodeGate API Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${DEPLOY_DIR}
Environment="PATH=${DEPLOY_DIR}/venv/bin"
Environment="ANTHROPIC_API_KEY=${API_KEY}"
ExecStart=${DEPLOY_DIR}/venv/bin/gunicorn \\
    --workers ${WORKERS} \\
    --threads 4 \\
    --bind 0.0.0.0:${SERVICE_PORT} \\
    --timeout 300 \\
    --access-logfile ${DEPLOY_DIR}/logs/access.log \\
    --error-logfile ${DEPLOY_DIR}/logs/error.log \\
    app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload

    log_success "systemd 服务创建完成"
}

configure_firewall() {
    log_info "配置防火墙..."

    if command -v ufw &> /dev/null; then
        ufw allow ${SERVICE_PORT}/tcp
        log_success "防火墙规则已添加 (ufw)"
    elif command -v iptables &> /dev/null; then
        iptables -A INPUT -p tcp --dport ${SERVICE_PORT} -j ACCEPT
        log_success "防火墙规则已添加 (iptables)"
    else
        log_warn "未检测到防火墙，请手动配置"
    fi
}

start_service() {
    log_info "启动服务..."

    systemctl enable ${PROJECT_NAME}
    systemctl start ${PROJECT_NAME}

    sleep 3

    if systemctl is-active --quiet ${PROJECT_NAME}; then
        log_success "服务启动成功"
    else
        log_error "服务启动失败，请检查日志"
        journalctl -u ${PROJECT_NAME} -n 20
        exit 1
    fi
}

verify_deployment() {
    log_info "验证部署..."

    sleep 2

    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${SERVICE_PORT}/api/health)

    if [ "${RESPONSE}" = "200" ]; then
        log_success "部署验证成功！"
        log_info "服务地址: http://$(hostname -I | awk '{print $1}'):${SERVICE_PORT}"
        log_info "健康检查: http://$(hostname -I | awk '{print $1}'):${SERVICE_PORT}/api/health"
    else
        log_error "部署验证失败，HTTP 状态码: ${RESPONSE}"
        exit 1
    fi
}

#------------------------------------------------------------------------------
# 主程序
#------------------------------------------------------------------------------

show_banner() {
    echo ""
    echo "=========================================="
    echo "       CodeGate 部署脚本 v1.0"
    echo "=========================================="
    echo ""
}

show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  install     完整安装部署"
    echo "  update      更新代码并重启服务"
    echo "  start       启动服务"
    echo "  stop        停止服务"
    echo "  restart     重启服务"
    echo "  status      查看服务状态"
    echo "  logs        查看服务日志"
    echo "  uninstall   卸载服务"
    echo "  help        显示帮助信息"
    echo ""
}

do_install() {
    show_banner
    check_root
    check_python

    install_dependencies
    create_directories
    copy_files
    setup_virtualenv
    install_python_packages
    create_systemd_service
    configure_firewall
    start_service
    verify_deployment

    echo ""
    log_success "========== 部署完成 =========="
}

do_update() {
    log_info "更新部署..."

    copy_files
    pull_code

    cd "${DEPLOY_DIR}"
    source venv/bin/activate
    pip install -r requirements.txt -q
    deactivate

    systemctl restart ${PROJECT_NAME}

    log_success "更新完成"
}

do_start() {
    systemctl start ${PROJECT_NAME}
    log_success "服务已启动"
}

do_stop() {
    systemctl stop ${PROJECT_NAME}
    log_info "服务已停止"
}

do_restart() {
    systemctl restart ${PROJECT_NAME}
    log_success "服务已重启"
}

do_status() {
    systemctl status ${PROJECT_NAME}
}

do_logs() {
    journalctl -u ${PROJECT_NAME} -f
}

do_uninstall() {
    log_warn "即将卸载 CodeGate 服务..."
    read -p "确认卸载？(y/N): " CONFIRM

    if [ "${CONFIRM}" = "y" ] || [ "${CONFIRM}" = "Y" ]; then
        systemctl stop ${PROJECT_NAME}
        systemctl disable ${PROJECT_NAME}
        rm -f /etc/systemd/system/${PROJECT_NAME}.service
        systemctl daemon-reload
        rm -rf "${DEPLOY_DIR}"
        log_success "卸载完成"
    else
        log_info "取消卸载"
    fi
}

# 主入口
case "${1}" in
    install)
        do_install
        ;;
    update)
        do_update
        ;;
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    restart)
        do_restart
        ;;
    status)
        do_status
        ;;
    logs)
        do_logs
        ;;
    uninstall)
        do_uninstall
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        show_help
        exit 1
        ;;
esac
