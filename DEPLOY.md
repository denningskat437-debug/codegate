# CodeGate 服务器部署指南

## 服务器信息
- IP: 117.72.184.235
- 端口: 8000
- 访问地址: http://117.72.184.235:8000/api/trigger

## 第一步：准备服务器

```bash
# 更新系统
apt update

# 安装依赖
apt install -y python3 python3-pip python3-venv git

# 创建项目目录
mkdir -p /opt/codegate
cd /opt/codegate
```

## 第二步：上传代码

将以下文件上传到 `/opt/codegate/`:

```
/opt/codegate/
├── app.py
├── requirements.txt
├── configs/
│   └── risk_rules.yml
├── src/
│   ├── __init__.py
│   ├── git_handler.py
│   ├── hash_checker.py
│   ├── ai_risk_analyzer.py
│   ├── test_case_reader.py
│   ├── test_executor.py
│   ├── report_generator.py
│   └── response_builder.py
├── test_cases/
│   └── test_sample.xlsx
├── cache/
│   └── hashes/
├── reports/
└── logs/
```

## 第三步：安装依赖

```bash
cd /opt/codegate

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

## 第四步：配置环境变量

```bash
# 设置 Anthropic API Key
export ANTHROPIC_API_KEY="your_api_key_here"

# 或写入 ~/.bashrc
echo 'export ANTHROPIC_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

## 第五步：启动服务

### 方式一：直接启动（测试用）

```bash
cd /opt/codegate
source venv/bin/activate
python app.py
```

### 方式二：使用 systemd（生产环境推荐）

```bash
# 创建服务文件
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

# 启动服务
systemctl daemon-reload
systemctl enable codegate
systemctl start codegate

# 检查状态
systemctl status codegate
```

## 第六步：验证服务

```bash
# 健康检查
curl http://localhost:8000/api/health

# 测试接口
curl -X POST http://localhost:8000/api/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "test",
    "repo_url": "https://github.com/your/repo.git",
    "test_case_file": "test_cases/test_sample.xlsx"
  }'
```

## 防火墙配置

```bash
# 开放 8000 端口
ufw allow 8000

# 或使用 iptables
iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
```

## 日志查看

```bash
# 查看日志
tail -f /opt/codegate/logs/codegate.log

# systemd 日志
journalctl -u codegate -f
```
