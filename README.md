# CodeGate

自动化代码风险检测与测试准入平台

## 项目简介

CodeGate 是一个自动化的代码质量门禁系统，在代码提交后自动进行安全风险评估和测试用例校验，确保只有通过检测的代码才能进入提测流程。

## 核心功能

- **代码拉取与变更检测** - 自动克隆仓库，智能检测代码变化，避免重复检测
- **代码统计分析** - 统计代码总量、文件数量、语言分布、项目类型识别
- **AI 安全风险评估** - 使用 Claude Agent SDK 进行代码安全分析
- **测试用例自动校验** - 基于 Excel 测试用例自动验证代码实现，记录执行时间
- **检测报告生成** - 生成 JSON 和 Excel 格式的详细报告（10个工作表）
- **邮件通知** - 检测完成后自动发送邮件通知提交者

## 快速开始

### 环境要求

- Python 3.9+
- Git 2.0+

### 安装步骤

```bash
# 克隆项目
git clone https://github.com/your-repo/codegate.git
cd codegate

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
export ANTHROPIC_API_KEY="your_api_key_here"

# 启动服务
python app.py
```

### 快速测试

```bash
# 健康检查
curl http://localhost:8000/api/health

# 触发检测
curl -X POST http://localhost:8000/api/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "my-project",
    "repo_url": "https://github.com/user/repo.git",
    "test_case_file": "test_cases/test_cases.xlsx",
    "branch": "main"
  }'
```

## API 接口

### POST /api/trigger

触发代码检测

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| project_name | string | 是 | 项目名称 |
| repo_url | string | 是 | Git 仓库地址 |
| test_case_file | string | 是 | 测试用例文件路径 |
| branch | string | 否 | 分支名称，默认 main |
| build_user | string | 否 | 触发者用户名 |
| build_user_nickname | string | 否 | 触发者昵称 |
| event | string | 否 | 触发事件类型 |
| commit_id | string | 否 | 提交ID |
| committer | string | 否 | 提交者用户名（用于从用户映射查找邮箱） |

**响应示例：**

```json
{
  "code": 0,
  "message": "全部通过，可进入提测",
  "summary": {
    "total": 10,
    "passed": 10,
    "failed": 0,
    "pass_rate": "100.0%"
  },
  "results": [...],
  "report_url": "/reports/TASK20260515120000/report.json"
}
```

### GET /api/health

健康检查接口

### GET /api/reports

获取报告列表

### GET /api/reports/{task_id}

获取指定任务报告

## 目录结构

```
codegate/
├── app.py                      # Flask 主入口
├── requirements.txt            # 依赖清单
├── configs/
│   ├── config.yml              # 主配置文件
│   ├── risk_rules.yml          # 风险评分规则
│   └── .cnb.yml                # CNB 流水线配置
├── src/
│   ├── __init__.py
│   ├── git_handler.py          # Git 操作
│   ├── hash_checker.py         # 哈希检测
│   ├── code_analyzer.py        # 代码统计分析
│   ├── ai_risk_analyzer.py     # AI 风险评估
│   ├── test_case_reader.py     # 测试用例读取
│   ├── test_executor.py        # 测试用例执行
│   ├── report_generator.py     # 报告生成
│   ├── response_builder.py     # 响应构建
│   ├── email_sender.py         # 邮件发送
│   ├── user_mapping_reader.py  # 用户映射读取
│   └── config_manager.py       # 配置管理
├── data/
│   └── user_mapping.xlsx       # 用户映射文件
├── test_cases/                 # 测试用例目录
├── cache/
│   └── hashes/                 # 哈希缓存
├── reports/                    # 报告目录
└── logs/                       # 日志目录
```

## 检测流程

```
代码提交 → 拉取代码 → 代码统计分析 → 哈希检测 → AI风险评估 → 测试用例校验 → 生成报告 → 邮件通知
                ↓
           代码未变化 → 跳过检测
                
           高风险代码 → 直接打回 → 发送邮件
```

## 风险等级

| 等级 | 分数范围 | 处理方式 |
|-----|---------|---------|
| high | 90-100 | 打回，不可提测 |
| medium | 40-89 | 继续，记录风险 |
| low | 0-39 | 继续 |

## 测试用例格式

测试用例使用 Excel 文件（.xlsx），包含以下列：

| 列名 | 说明 |
|-----|------|
| 用例编号 | 唯一标识 |
| 对应需求 | 关联需求 |
| 测试点 | 测试关注点 |
| 优先级 | P0/P1/P2 |
| 前置条件 | 执行前准备 |
| 操作步骤 | 测试步骤 |
| 预期结果 | 期望结果 |

## 部署说明

详见 [DEPLOY.md](DEPLOY.md)

## 邮件配置

邮件通知功能需要配置 SMTP 服务器，在 `configs/config.yml` 中配置：

```yaml
email:
  enabled: true
  smtp_host: "smtp.qq.com"      # SMTP 服务器地址
  smtp_port: 465                 # SMTP 端口（SSL）
  use_ssl: true                  # 是否使用 SSL
  smtp_user: "your@qq.com"       # SMTP 用户名
  from_email: "your@qq.com"      # 发件人邮箱
  base_url: "http://your-server:8000"  # 报告访问地址
```

SMTP 密码建议通过环境变量设置：
```bash
export SMTP_PASSWORD="your_smtp_password"
```

## 用户映射

如果提交者邮箱未传入，系统会从用户映射文件中查找。映射文件位于 `data/user_mapping.xlsx`：

| username | email |
|----------|-------|
| zhangsan | zhangsan@company.com |
| lisi | lisi@company.com |

## 相关文档

- [部署指南](DEPLOY.md)
- [API文档](API文档.md)
- [工具交付逻辑](工具交付逻辑.md)
- [工程落地指南](工程落地.md)

## 许可证

MIT License
