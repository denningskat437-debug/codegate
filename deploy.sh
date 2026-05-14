#!/bin/bash
# CodeGate 服务器部署脚本

set -e

echo "========== CodeGate 部署脚本 =========="

# 1. 更新系统
echo ">>> 更新系统..."
apt update

# 2. 安装依赖
echo ">>> 安装系统依赖..."
apt install -y python3 python3-pip python3-venv git

# 3. 创建项目目录
echo ">>> 创建项目目录..."
mkdir -p /opt/codegate
cd /opt/codegate

# 4. 创建虚拟环境
echo ">>> 创建虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 5. 安装 Python 依赖
echo ">>> 安装 Python 依赖..."
pip install --upgrade pip
pip install flask==3.0.0
pip install claude-agent-sdk
pip install anyio>=4.0.0
pip install pandas==2.1.0
pip install openpyxl==3.1.0
pip install pyyaml==6.0.1
pip install gunicorn

# 6. 创建目录结构
echo ">>> 创建目录结构..."
mkdir -p configs src test_cases cache/hashes reports logs

# 7. 创建 systemd 服务
echo ">>> 创建 systemd 服务..."
cat > /etc/systemd/system/codegate.service << 'EOF'
[Unit]
Description=CodeGate API Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/codegate
Environment="PATH=/opt/codegate/venv/bin"
Environment="ANTHROPIC_API_KEY=your_api_key_here"
ExecStart=/opt/codegate/venv/bin/gunicorn --workers 2 --bind 0.0.0.0:8000 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "========== 部署完成 =========="
echo ""
echo "下一步操作："
echo "1. 上传代码文件到 /opt/codegate/"
echo "2. 编辑 /etc/systemd/system/codegate.service 设置 ANTHROPIC_API_KEY"
echo "3. 运行: systemctl daemon-reload"
echo "4. 运行: systemctl enable codegate"
echo "5. 运行: systemctl start codegate"
echo "6. 检查状态: systemctl status codegate"
echo ""
echo "访问地址: http://117.72.184.235:8000/api/trigger"
