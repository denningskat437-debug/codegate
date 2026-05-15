# CodeGate 部署指南

## 服务器信息

- 默认端口：8000
- 访问地址：http://服务器IP:8000

---

## 一、服务器准备

### 1.1 系统要求

| 项目 | 最低要求 | 推荐配置 |
|-----|---------|---------|
| 操作系统 | Ubuntu 20.04 | Ubuntu 22.04 LTS |
| CPU | 1核 | 2核+ |
| 内存 | 2GB | 4GB+ |
| 磁盘 | 20GB | 50GB+ |

### 1.2 系统初始化

```bash
# 更新系统
apt update && apt upgrade -y

# 安装基础依赖
apt install -y python3 python3-pip python3-venv git curl

# 创建项目目录
mkdir -p /opt/codegate
cd /opt/codegate
```

---

## 二、代码部署

### 2.1 方式一：Git 克隆（推荐）

```bash
cd /opt
git clone https://github.com/your-repo/codegate.git
cd codegate
```

### 2.2 方式二：文件上传

使用 scp 上传：
```bash
scp -r ./codegate root@server_ip:/opt/
```

或使用 sftp 工具上传。

---

## 三、环境配置

### 3.1 创建虚拟环境

```bash
cd /opt/codegate

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
pip install --upgrade pip
```

### 3.2 安装依赖

```bash
# 安装项目依赖
pip install -r requirements.txt

# 安装生产服务器
pip install gunicorn
```

### 3.3 配置环境变量

```bash
# 方式一：临时配置（测试用）
export ANTHROPIC_API_KEY="your_api_key_here"

# 方式二：永久配置
echo 'export ANTHROPIC_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc

# 方式三：写入 systemd 服务配置（推荐）
# 见下文服务配置部分

# SMTP 密码配置（邮件通知需要）
export SMTP_PASSWORD="your_smtp_password_here"
```

---

## 四、配置文件

### 4.1 主配置文件

创建 `configs/config.yml`：

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  debug: false

paths:
  cache_dir: "cache/hashes"
  report_dir: "reports"
  log_dir: "logs"

email:
  enabled: true
  smtp_host: "smtp.qq.com"
  smtp_port: 465
  use_ssl: true
  smtp_user: "your@qq.com"
  from_email: "your@qq.com"
  base_url: "http://your-server:8000"

user_mapping:
  enabled: true
  file: "data/user_mapping.xlsx"

risk:
  thresholds:
    high:
      min: 70
      action: "reject"
    medium:
      min: 40
      action: "continue"
    low:
      min: 0
      action: "continue"

logging:
  level: "INFO"
  file: "logs/codegate.log"
```

### 4.2 用户映射文件

创建 `data/user_mapping.xlsx`：

| username | email |
|----------|-------|
| zhangsan | zhangsan@company.com |
| lisi | lisi@company.com |

---

## 四、目录初始化

```bash
cd /opt/codegate

# 创建必要目录
mkdir -p cache/hashes
mkdir -p reports
mkdir -p logs
mkdir -p data

# 设置权限
chmod -R 755 cache reports logs data
```

---

## 五、服务配置

### 5.1 创建 systemd 服务

```bash
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
Environment="SMTP_PASSWORD=your_smtp_password_here"
ExecStart=/opt/codegate/venv/bin/gunicorn \
  --workers 2 \
  --threads 4 \
  --bind 0.0.0.0:8000 \
  --timeout 300 \
  --access-logfile /opt/codegate/logs/access.log \
  --error-logfile /opt/codegate/logs/error.log \
  app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### 5.2 Gunicorn 参数说明

| 参数 | 说明 | 建议值 |
|-----|------|-------|
| workers | 工作进程数 | CPU核心数 × 2 + 1 |
| threads | 每进程线程数 | 2-4 |
| bind | 监听地址 | 0.0.0.0:8000 |
| timeout | 超时时间 | 300（AI分析需要较长时间） |

### 5.3 启动服务

```bash
# 重载 systemd 配置
systemctl daemon-reload

# 启动服务
systemctl start codegate

# 设置开机自启
systemctl enable codegate

# 检查状态
systemctl status codegate
```

---

## 六、防火墙配置

### 6.1 使用 ufw

```bash
# 开放 8000 端口
ufw allow 8000/tcp

# 重新加载
ufw reload

# 查看状态
ufw status
```

### 6.2 使用 iptables

```bash
# 开放 8000 端口
iptables -A INPUT -p tcp --dport 8000 -j ACCEPT

# 保存规则
iptables-save > /etc/iptables/rules.v4
```

---

## 七、验证部署

### 7.1 本地验证

```bash
# 健康检查
curl http://localhost:8000/api/health

# 预期响应
# {"status": "healthy", "service": "CodeGate", "time": "2026-05-15 12:00:00"}
```

### 7.2 外部验证

```bash
# 从外部访问
curl http://服务器IP:8000/api/health
```

### 7.3 功能验证

```bash
curl -X POST http://localhost:8000/api/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "test",
    "repo_url": "https://github.com/user/test.git",
    "test_case_file": "test_cases/test_sample.xlsx",
    "branch": "main"
  }'
```

---

## 八、日志管理

### 8.1 日志文件

| 日志文件 | 说明 |
|---------|------|
| logs/codegate.log | 应用日志 |
| logs/access.log | 访问日志 |
| logs/error.log | 错误日志 |

### 8.2 查看日志

```bash
# 实时查看应用日志
tail -f /opt/codegate/logs/codegate.log

# 查看 systemd 日志
journalctl -u codegate -f

# 查看最近 100 行
journalctl -u codegate -n 100
```

### 8.3 日志轮转

```bash
cat > /etc/logrotate.d/codegate << 'EOF'
/opt/codegate/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}
EOF
```

---

## 九、服务管理

### 9.1 常用命令

```bash
# 启动服务
systemctl start codegate

# 停止服务
systemctl stop codegate

# 重启服务
systemctl restart codegate

# 查看状态
systemctl status codegate

# 查看日志
journalctl -u codegate -f
```

### 9.2 更新部署

```bash
cd /opt/codegate

# 拉取最新代码
git pull

# 激活虚拟环境
source venv/bin/activate

# 更新依赖
pip install -r requirements.txt

# 重启服务
systemctl restart codegate
```

---

## 十、性能调优

### 10.1 Gunicorn 调优

根据服务器配置调整：

**2核4GB 服务器：**
```bash
--workers 2 --threads 4
```

**4核8GB 服务器：**
```bash
--workers 4 --threads 4
```

### 10.2 系统调优

```bash
# 增加文件描述符限制
echo "* soft nofile 65535" >> /etc/security/limits.conf
echo "* hard nofile 65535" >> /etc/security/limits.conf
```

---

## 十一、常见问题

### Q1: 端口被占用

```bash
# 查看端口占用
lsof -i:8000

# 杀掉进程
kill -9 <PID>
```

### Q2: 服务启动失败

```bash
# 查看详细错误
journalctl -u codegate -n 50

# 检查配置
systemctl cat codegate
```

### Q3: Claude API 调用失败

- 检查 ANTHROPIC_API_KEY 是否正确
- 检查网络是否能访问 Claude API
- 检查 API Key 是否有余额

### Q4: Git 克隆超时

```bash
# 增加 Git 克隆超时时间
# 修改 app.py 中的 timeout 参数
```

### Q5: 邮件发送失败

- 检查 SMTP 配置是否正确（smtp_host, smtp_port, smtp_user）
- 检查 SMTP_PASSWORD 环境变量是否设置
- 检查是否使用 SSL 连接（QQ邮箱需要 use_ssl: true）
- 检查 SMTP 授权码是否正确（不是邮箱密码）
- 查看日志中的具体错误信息：`tail -f logs/codegate.log`

### Q6: 用户映射无效

- 检查 user_mapping.enabled 是否为 true
- 检查 data/user_mapping.xlsx 文件是否存在
- 检查 Excel 文件格式是否正确（username, email 两列）

---

## 十二、安全建议

1. **使用 HTTPS** - 配置 Nginx 反向代理和 SSL 证书
2. **限制访问** - 只允许内网 IP 访问
3. **定期更新** - 定期更新依赖包
4. **日志审计** - 定期检查访问日志
5. **备份配置** - 定期备份配置文件和报告

---

## 十三、联系支持

如有问题，请联系开发团队。
