# CodeGate API 接口文档

## 概述

CodeGate 提供 RESTful API 接口，用于触发代码检测、查询报告等操作。

**基础地址：** `http://服务器IP:8000`

**请求格式：** JSON

**响应格式：** JSON

---

## 接口列表

| 接口 | 方法 | 说明 |
|-----|------|------|
| /api/trigger | POST | 触发代码检测 |
| /api/health | GET | 健康检查 |
| /api/reports | GET | 获取报告列表 |
| /api/reports/{task_id} | GET | 获取指定报告 |
| /reports/{task_id}/{filename} | GET | 下载报告文件 |

---

## 1. 触发检测

### 接口信息

```
POST /api/trigger
```

触发代码风险检测和测试用例校验。

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| project_name | string | 是 | 项目名称，用于标识项目和缓存 |
| repo_url | string | 是 | Git 仓库地址 |
| test_case_file | string | 是 | 测试用例文件路径（相对于项目根目录） |
| branch | string | 否 | 分支名称，默认 main |
| event | string | 否 | 触发事件类型，如 push |
| build_user | string | 否 | 触发者用户名 |
| build_user_nickname | string | 否 | 触发者昵称 |
| commit_id | string | 否 | 提交ID |
| committer | string | 否 | 提交者用户名（用于从用户映射查找邮箱） |

### 请求示例

```bash
curl -X POST http://localhost:8000/api/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "MrDoc",
    "repo_url": "https://github.com/user/mrdoc.git",
    "test_case_file": "test_cases/mrdoc.xlsx",
    "branch": "main",
    "event": "push",
    "build_user": "developer",
    "build_user_nickname": "开发者",
    "commit_id": "abc123",
    "committer": "zhangsan"
  }'
```

### 响应参数

| 参数 | 类型 | 说明 |
|-----|------|------|
| code | int | 状态码，0 表示成功 |
| message | string | 状态消息 |
| summary | object | 检测结果摘要 |
| summary.total | int | 测试用例总数 |
| summary.passed | int | 通过数 |
| summary.failed | int | 失败数 |
| summary.pass_rate | string | 通过率 |
| code_statistics | object | 代码统计信息（新增） |
| code_statistics.total_lines | int | 代码总量（行） |
| code_statistics.total_files | int | 文件数量 |
| code_statistics.project_type | string | 项目类型 |
| code_statistics.main_languages | array | 主要语言列表 |
| test_time_statistics | object | 测试执行时间统计（新增） |
| test_time_statistics.total_execution_time | float | 总执行时间（秒） |
| test_time_statistics.average_execution_time | float | 平均执行时间（秒/用例） |
| results | array | 测试结果列表 |
| report_url | string | 报告下载地址 |

### 响应示例

**成功响应（全部通过）：**

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
  "code_statistics": {
    "total_lines": 50000,
    "total_files": 120,
    "project_type": "backend",
    "main_languages": ["Python", "JavaScript"]
  },
  "test_time_statistics": {
    "total_execution_time": 150.5,
    "average_execution_time": 15.05,
    "min_execution_time": 8.2,
    "max_execution_time": 25.3
  },
  "results": [
    {
      "case_id": "TC001",
      "requirement": "用户登录",
      "test_point": "登录验证",
      "priority": "P0",
      "result": "passed",
      "execution_time": 12.5,
      "test_time": "2026-05-15 12:00:00",
      "evidence": "代码中 login 函数实现了登录验证功能，位于 app/auth.py 第 45 行",
      "problem_code": "",
      "analysis": {
        "conclusion": "登录功能实现完整，符合预期",
        "strengths": ["代码结构清晰", "有完善的错误处理"],
        "weaknesses": []
      }
    }
  ],
  "report_url": "/reports/TASK20260515120000/report.json"
}
```

**失败响应（存在失败用例）：**

```json
{
  "code": 1,
  "message": "存在失败用例，不可进入提测",
  "summary": {
    "total": 10,
    "passed": 8,
    "failed": 2,
    "pass_rate": "80.0%"
  },
  "results": [
    {
      "case_id": "TC005",
      "requirement": "数据导出",
      "test_point": "Excel导出",
      "priority": "P1",
      "result": "failed",
      "test_time": "2026-05-15 12:00:00",
      "evidence": "未找到 Excel 导出功能的实现",
      "problem_code": "app/export.py 缺少 export_excel 方法"
    }
  ],
  "report_url": "/reports/TASK20260515120000/report.json"
}
```

**高风险打回响应：**

```json
{
  "code": 1,
  "message": "高风险代码，已打回",
  "risk": {
    "level": "high",
    "score": 95,
    "items": [
      {
        "type": "sql_injection",
        "location": "app/db.py:45",
        "description": "存在SQL拼接，可能导致注入攻击"
      },
      {
        "type": "sensitive_data",
        "location": "config.py:10",
        "description": "硬编码数据库密码"
      }
    ],
    "summary": "发现SQL注入风险和敏感信息泄露，建议立即修复"
  },
  "report_url": "/reports/TASK20260515120000/report.json"
}
```

**代码未变化响应：**

```json
{
  "code": 0,
  "message": "代码未变化，无需检测"
}
```

---

## 2. 健康检查

### 接口信息

```
GET /api/health
```

检查服务运行状态。

### 请求示例

```bash
curl http://localhost:8000/api/health
```

### 响应示例

```json
{
  "status": "healthy",
  "service": "CodeGate",
  "time": "2026-05-15 12:00:00"
}
```

---

## 3. 获取报告列表

### 接口信息

```
GET /api/reports
```

获取最近生成的报告列表。

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| limit | int | 否 | 返回数量，默认 20 |

### 请求示例

```bash
curl "http://localhost:8000/api/reports?limit=10"
```

### 响应示例

```json
{
  "code": 0,
  "data": [
    {
      "task_id": "TASK20260515120000",
      "project_name": "MrDoc",
      "generated_at": "2026-05-15 12:00:00",
      "summary": {
        "total": 10,
        "passed": 10,
        "failed": 0,
        "pass_rate": "100.0%"
      }
    },
    {
      "task_id": "TASK20260515110000",
      "project_name": "MrDoc",
      "generated_at": "2026-05-15 11:00:00",
      "summary": {
        "total": 10,
        "passed": 8,
        "failed": 2,
        "pass_rate": "80.0%"
      }
    }
  ]
}
```

---

## 4. 获取指定报告

### 接口信息

```
GET /api/reports/{task_id}
```

获取指定任务的完整报告。

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| task_id | string | 是 | 任务ID，路径参数 |

### 请求示例

```bash
curl http://localhost:8000/api/reports/TASK20260515120000
```

### 响应示例

```json
{
  "task_id": "TASK20260515120000",
  "project_name": "MrDoc",
  "generated_at": "2026-05-15 12:00:00",
  "commit_info": {
    "commit_id": "abc123def456",
    "author": "developer",
    "message": "feat: add login feature"
  },
  "risk": {
    "level": "low",
    "score": 15,
    "items": [],
    "summary": "未发现明显安全风险"
  },
  "test_results": [
    {
      "case_id": "TC001",
      "requirement": "用户登录",
      "test_point": "登录验证",
      "priority": "P0",
      "result": "passed",
      "test_time": "2026-05-15 12:00:00",
      "evidence": "代码实现符合预期",
      "problem_code": ""
    }
  ],
  "summary": {
    "total": 10,
    "passed": 10,
    "failed": 0,
    "pass_rate": "100.0%"
  }
}
```

---

## 5. 下载报告文件

### 接口信息

```
GET /reports/{task_id}/{filename}
```

下载报告文件（JSON 或 Excel）。

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| task_id | string | 是 | 任务ID |
| filename | string | 是 | 文件名：report.json 或 report.xlsx |

### 请求示例

```bash
# 下载 JSON 报告
curl -O http://localhost:8000/reports/TASK20260515120000/report.json

# 下载 Excel 报告
curl -O http://localhost:8000/reports/TASK20260515120000/report.xlsx
```

### 响应

返回文件内容，浏览器会自动下载。

---

## 错误码说明

| 错误码 | 说明 |
|-------|------|
| 0 | 成功 |
| 1 | 检测失败（存在失败用例或高风险） |
| 1001 | 参数缺失 |
| 1002 | 参数格式错误 |
| 2001 | 测试用例文件不存在 |
| 2002 | 测试用例文件格式错误 |
| 5001 | 服务器内部错误 |
| 5002 | Git 操作失败 |
| 5003 | AI 分析异常 |

---

## 错误响应示例

### 参数缺失

```json
{
  "code": 1001,
  "message": "参数缺失：project_name"
}
```

### 测试用例文件不存在

```json
{
  "code": 2001,
  "message": "测试用例文件不存在: test_cases/missing.xlsx"
}
```

### Git 操作失败

```json
{
  "code": 5002,
  "message": "Git 操作失败",
  "details": "克隆仓库失败: https://github.com/user/repo.git"
}
```

---

## 调用示例

### Python 示例

```python
import requests

# 触发检测
response = requests.post(
    'http://localhost:8000/api/trigger',
    json={
        'project_name': 'MrDoc',
        'repo_url': 'https://github.com/user/mrdoc.git',
        'test_case_file': 'test_cases/mrdoc.xlsx',
        'branch': 'main'
    }
)

result = response.json()
if result['code'] == 0:
    print(f"检测通过: {result['summary']['pass_rate']}")
else:
    print(f"检测失败: {result['message']}")
```

### JavaScript 示例

```javascript
// 触发检测
async function triggerCheck() {
  const response = await fetch('http://localhost:8000/api/trigger', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      project_name: 'MrDoc',
      repo_url: 'https://github.com/user/mrdoc.git',
      test_case_file: 'test_cases/mrdoc.xlsx',
      branch: 'main'
    })
  });

  const result = await response.json();
  console.log(result);
}
```

### Shell 脚本示例

```bash
#!/bin/bash

# 触发检测并检查结果
response=$(curl -s -X POST http://localhost:8000/api/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "MrDoc",
    "repo_url": "https://github.com/user/mrdoc.git",
    "test_case_file": "test_cases/mrdoc.xlsx",
    "branch": "main"
  }')

# 解析响应
code=$(echo $response | jq -r '.code')
message=$(echo $response | jq -r '.message')

if [ "$code" == "0" ]; then
  echo "✓ $message"
  exit 0
else
  echo "✗ $message"
  exit 1
fi
```

---

## 注意事项

1. **超时设置** - AI 分析可能需要较长时间，建议客户端超时设置为 5 分钟以上
2. **并发限制** - 建议控制并发请求数，避免服务器过载
3. **重试机制** - 遇到 500 错误时，建议等待后重试
4. **网络访问** - 服务器需要能访问 Git 仓库和 Claude API
5. **邮件通知** - 需要配置 SMTP 服务器，邮件会发送给用户映射文件中匹配的邮箱
6. **用户映射** - 系统根据 `committer` 用户名从用户映射 Excel 文件中查找邮箱

---

## 邮件配置

邮件通知功能需要在 `configs/config.yml` 中配置：

```yaml
email:
  enabled: true                    # 是否启用邮件通知
  smtp_host: "smtp.qq.com"         # SMTP 服务器地址
  smtp_port: 465                   # SMTP 端口
  use_ssl: true                    # 是否使用 SSL
  smtp_user: "your@qq.com"         # SMTP 用户名
  from_email: "your@qq.com"        # 发件人邮箱
  base_url: "http://server:8000"   # 报告访问地址

user_mapping:
  enabled: true                    # 是否启用用户映射
  file: "data/user_mapping.xlsx"   # 用户映射文件路径
```

SMTP 密码通过环境变量设置：
```bash
export SMTP_PASSWORD="your_smtp_password"
```

用户映射文件格式（Excel）：

| username | email |
|----------|-------|
| zhangsan | zhangsan@company.com |
| lisi | lisi@company.com |

---

## 版本历史

| 版本 | 日期 | 说明 |
|-----|------|------|
| v1.0 | 2026-05-15 | 初始版本 |
