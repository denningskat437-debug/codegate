# CodeGate MVP 开发规格说明书

## 1. 项目名称

**CodeGate 自动化代码风险检测与测试准入 API**

## 2. 项目定位

CodeGate 是一个基于 Flask 的 API 服务，用于自动化代码风险检测和测试用例校验。

**核心功能**：
- 接收项目名称、仓库链接、测试用例文件
- 拉取代码，哈希检测代码变化
- AI 风险评估（高/中/低）
- 逐条执行测试用例校验
- 输出详细测试报告

**访问地址**：`http://服务器IP:8000/api/trigger`

## 3. 整体业务流程

```
外部调用 API（项目名称 + 仓库链接 + 测试用例）
        ↓
┌─────────────────────────────────────────────────────┐
│  第一步：拉取代码                                    │
│  - 克隆仓库到临时目录                                │
│  - 获取最新代码                                      │
└─────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────┐
│  第二步：哈希检测                                    │
│  - 计算当前代码哈希                                  │
│  - 对比缓存哈希                                      │
│  - 相同则跳过检测                                    │
└─────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────┐
│  第三步：AI 风险评估                                 │
│  - 使用 Claude Agent SDK 分析代码                   │
│  - 检查：SQL注入、XSS、敏感信息泄露等               │
│  - 输出风险等级：高 / 中 / 低                        │
│  - 高风险 → 直接打回                                │
└─────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────┐
│  第四步：测试用例校验                                │
│  - 读取 xlsx 测试用例                               │
│  - 逐条执行检测                                      │
│  - 输出：测试时间、结果、校验依据、问题代码          │
│  - 全部通过才能进入提测                              │
└─────────────────────────────────────────────────────┘
        ↓
生成报告（JSON + Excel）
```

## 4. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                   外部调用方                                 │
│  CNB流水线 / 手动调用 / 定时任务                            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Flask API 服务                             │
│  POST /api/trigger                                          │
│  参数：project_name, repo_url, test_case_file              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    核心处理层                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │GitHandler│ │HashCheck │ │AIRisk    │ │TestExec  │       │
│  │ 拉取代码 │ │ 哈希检测 │ │ 风险评估 │ │ 用例执行 │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    输出层                                   │
│  JSON 报告 │ Excel 报告                                     │
└─────────────────────────────────────────────────────────────┘
```

## 5. 目录结构

```
codegate/
├── app.py                      # Flask 主入口（API 服务）
├── requirements.txt            # 依赖清单
├── configs/
│   └── risk_rules.yml          # 风险评分规则
├── src/
│   ├── __init__.py
│   ├── git_handler.py          # Git 操作（克隆、diff）
│   ├── hash_checker.py         # 代码哈希检测模块
│   ├── ai_risk_analyzer.py     # AI 风险评估（Claude Agent SDK）
│   ├── test_case_reader.py     # 测试用例读取（xlsx）
│   ├── test_executor.py        # 测试用例执行（Claude Agent SDK）
│   ├── report_generator.py     # 报告生成（JSON + Excel）
│   └── response_builder.py     # 响应构建
├── test_cases/
│   └── example.xlsx            # 示例测试用例
├── cache/
│   └── hashes/                 # 代码哈希缓存
├── reports/
│   └── {task_id}/              # 每次检测的报告目录
│       ├── report.json
│       └── report.xlsx
└── logs/
    └── codegate.log            # 日志文件
```

## 6. API 接口设计

### 6.1 核心接口

```
POST /api/trigger
```

### 6.2 请求参数

```json
{
  "project_name": "MrDoc",
  "repo_url": "https://cnb.cool/test-2026_513/test.git",
  "test_case_file": "test_cases/mrdoc.xlsx"
}
```

| 参数 | 必填 | 说明 |
|------|------|------|
| project_name | 是 | 项目名称（用于哈希缓存标识） |
| repo_url | 是 | 仓库链接（Git 地址） |
| test_case_file | 是 | 测试用例文件路径（服务器本地路径，xlsx格式） |

### 6.3 响应结果

#### 代码未变化

```json
{
  "code": 0,
  "message": "代码未变化，无需检测"
}
```

#### 高风险打回

```json
{
  "code": 1,
  "message": "高风险代码，已打回",
  "risk": {
    "level": "high",
    "score": 85,
    "items": [
      {
        "type": "sql_injection",
        "location": "app/db.py:45",
        "description": "存在SQL拼接，可能导致注入"
      }
    ]
  }
}
```

#### 测试结果

```json
{
  "code": 0,
  "message": "全部通过，可进入提测",
  "summary": {
    "total": 10,
    "passed": 10,
    "failed": 0
  },
  "results": [
    {
      "case_id": "TC001",
      "result": "passed",
      "test_time": "2026-05-14 10:30:00",
      "evidence": "代码中login函数实现了用户名密码校验逻辑...",
      "problem_code": ""
    }
  ],
  "report_url": "/reports/TASK20260514001/report.json"
}
```

#### 存在失败用例

```json
{
  "code": 1,
  "message": "存在失败用例，不可进入提测",
  "summary": {
    "total": 10,
    "passed": 8,
    "failed": 2
  },
  "results": [
    {
      "case_id": "TC002",
      "result": "failed",
      "test_time": "2026-05-14 10:31:00",
      "evidence": "未找到logout函数实现，用户无法正常退出登录",
      "problem_code": "app/auth.py 缺少logout方法"
    }
  ],
  "report_url": "/reports/TASK20260514001/report.json"
}
```

## 7. 测试用例格式

### 7.1 xlsx 文件列定义

| 列名 | 说明 | 示例 |
|------|------|------|
| 用例编号 | 唯一标识 | TC001 |
| 对应需求 | 需求描述 | 用户登录功能 |
| 测试点 | 具体测试点 | 验证用户名密码登录 |
| 优先级 | 高/中/低 | 高 |
| 前置条件 | 执行前条件 | 用户已注册 |
| 操作步骤 | 测试步骤 | 1.输入用户名 2.输入密码 3.点击登录 |
| 预期结果 | 期望结果 | 登录成功，跳转首页 |

### 7.2 示例数据

| 用例编号 | 对应需求 | 测试点 | 优先级 | 前置条件 | 操作步骤 | 预期结果 |
|----------|----------|--------|--------|----------|----------|----------|
| TC001 | 用户登录 | 验证正确账号密码登录 | 高 | 用户已注册 | 输入正确用户名密码，点击登录 | 登录成功，跳转首页 |
| TC002 | 用户登录 | 验证错误密码登录 | 高 | 用户已注册 | 输入正确用户名，错误密码 | 提示密码错误 |
| TC003 | 用户登出 | 验证退出登录 | 中 | 用户已登录 | 点击退出按钮 | 退出成功，跳转登录页 |

## 8. 风险评分规则

### 8.1 风险等级定义

| 等级 | 分数范围 | 处理策略 |
|------|----------|----------|
| **high** | 70-100 | 直接打回，代码就是垃圾 |
| **medium** | 40-69 | 继续测试用例校验 |
| **low** | 0-39 | 继续测试用例校验 |

### 8.2 风险检查项

| 检查项 | 权重 | 说明 |
|--------|------|------|
| SQL 注入 | 30 | 拼接 SQL 语句、未使用参数化查询 |
| XSS 攻击 | 25 | 未转义用户输入、innerHTML 使用 |
| 敏感信息泄露 | 30 | 硬编码密码、API Key、Token |
| 命令注入 | 30 | 执行用户输入的命令 |
| 权限缺失 | 20 | 未校验用户权限、越权访问 |

### 8.3 configs/risk_rules.yml

```yaml
risk_levels:
  high:
    min: 70
    max: 100
    action: "reject"

  medium:
    min: 40
    max: 69
    action: "continue"

  low:
    min: 0
    max: 39
    action: "continue"

risk_items:
  sql_injection:
    weight: 30
    description: "SQL注入风险"

  xss:
    weight: 25
    description: "XSS跨站脚本"

  sensitive_data:
    weight: 30
    description: "敏感信息泄露"

  command_injection:
    weight: 30
    description: "命令注入风险"

  auth_missing:
    weight: 20
    description: "权限校验缺失"
```

## 9. 核心模块设计

### 9.1 app.py - Flask 主入口

```python
from flask import Flask, request, jsonify
from src.git_handler import GitHandler
from src.hash_checker import HashChecker
from src.ai_risk_analyzer import AIRiskAnalyzer
from src.test_case_reader import TestCaseReader
from src.test_executor import TestExecutor
from src.report_generator import ReportGenerator

app = Flask(__name__)

@app.route('/api/trigger', methods=['POST'])
def trigger():
    """
    触发检测接口

    参数：
    - project_name: 项目名称
    - repo_url: 仓库链接
    - test_case_file: 测试用例文件路径
    """
    data = request.json
    project_name = data.get('project_name')
    repo_url = data.get('repo_url')
    test_case_file = data.get('test_case_file')

    # 参数校验
    if not all([project_name, repo_url, test_case_file]):
        return jsonify({'code': 1001, 'message': '参数缺失'}), 400

    try:
        # 1. 拉取代码
        git = GitHandler(repo_url)
        code_path = git.clone()

        # 2. 哈希检测（代码是否变化）
        hash_checker = HashChecker()
        current_hash = hash_checker.get_hash(code_path)
        cached_hash = hash_checker.get_cached_hash(project_name)

        if current_hash == cached_hash:
            git.cleanup()
            return jsonify({'code': 0, 'message': '代码未变化，无需检测'})

        # 3. 风险评估
        risk_analyzer = AIRiskAnalyzer(code_path)
        risk_result = risk_analyzer.analyze()

        # 高风险直接打回
        if risk_result['level'] == 'high':
            report = ReportGenerator().generate(
                project_name, risk_result, [], code_path
            )
            git.cleanup()
            return jsonify({
                'code': 1,
                'message': '高风险代码，已打回',
                'risk': risk_result,
                'report_url': report['url']
            })

        # 4. 测试用例校验
        test_reader = TestCaseReader(test_case_file)
        test_cases = test_reader.read()

        executor = TestExecutor(code_path)
        test_results = executor.execute_all(test_cases)

        # 5. 判断是否全部通过
        all_passed = all(r['result'] == 'passed' for r in test_results)

        # 6. 生成报告
        report = ReportGenerator().generate(
            project_name, risk_result, test_results, code_path
        )

        # 7. 更新哈希缓存
        hash_checker.save_hash(project_name, current_hash)

        # 8. 清理临时目录
        git.cleanup()

        return jsonify({
            'code': 0 if all_passed else 1,
            'message': '全部通过，可进入提测' if all_passed else '存在失败用例，不可进入提测',
            'summary': {
                'total': len(test_results),
                'passed': sum(1 for r in test_results if r['result'] == 'passed'),
                'failed': sum(1 for r in test_results if r['result'] == 'failed')
            },
            'results': test_results,
            'report_url': report['url']
        })

    except Exception as e:
        return jsonify({'code': 5001, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

### 9.2 git_handler.py - Git 操作

```python
import subprocess
import os
import tempfile
import shutil

class GitHandler:
    """Git 操作处理器"""

    def __init__(self, repo_url: str, branch: str = 'main'):
        self.repo_url = repo_url
        self.branch = branch
        self.repo_dir = None

    def clone(self) -> str:
        """
        克隆仓库到临时目录

        Returns:
            代码目录路径
        """
        self.repo_dir = tempfile.mkdtemp(prefix='codegate_')
        subprocess.run(
            ['git', 'clone', '-b', self.branch, '--depth', '2', self.repo_url, self.repo_dir],
            capture_output=True,
            check=True
        )
        return self.repo_dir

    def get_diff(self, base: str = 'HEAD~1') -> str:
        """获取代码变更"""
        result = subprocess.check_output(
            ['git', 'diff', base, 'HEAD'],
            cwd=self.repo_dir
        )
        return result.decode()

    def cleanup(self):
        """清理临时目录"""
        if self.repo_dir and os.path.exists(self.repo_dir):
            shutil.rmtree(self.repo_dir)
```

### 9.3 hash_checker.py - 哈希检测模块

```python
import hashlib
import os
import subprocess
from pathlib import Path

class HashChecker:
    """代码哈希检测器"""

    def __init__(self, cache_dir: str = 'cache/hashes'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_hash(self, code_path: str) -> str:
        """
        计算代码目录的哈希值
        优先使用 git commit hash
        """
        try:
            result = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'],
                cwd=code_path
            )
            return result.decode().strip()
        except:
            return self._calculate_file_hash(code_path)

    def _calculate_file_hash(self, code_path: str) -> str:
        """计算所有文件的哈希"""
        hasher = hashlib.sha256()
        for root, dirs, files in os.walk(code_path):
            # 排除 .git 目录
            dirs[:] = [d for d in dirs if d != '.git']
            for file in sorted(files):
                file_path = os.path.join(root, file)
                with open(file_path, 'rb') as f:
                    hasher.update(file_path.encode())
                    hasher.update(f.read())
        return hasher.hexdigest()

    def get_cached_hash(self, project_name: str) -> str:
        """获取缓存的哈希值"""
        cache_file = self.cache_dir / f"{project_name}.hash"
        if cache_file.exists():
            return cache_file.read_text()
        return None

    def save_hash(self, project_name: str, hash_value: str):
        """保存哈希值到缓存"""
        cache_file = self.cache_dir / f"{project_name}.hash"
        cache_file.write_text(hash_value)
```

### 9.4 ai_risk_analyzer.py - AI 风险评估

```python
import anyio
import json
import re
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage
from claude_agent_sdk.types import TextBlock

class AIRiskAnalyzer:
    """AI 风险评估器 - 使用 Claude Agent SDK"""

    def __init__(self, code_path: str):
        self.code_path = code_path

    def analyze(self) -> dict:
        """执行风险评估"""
        return anyio.run(self._analyze_async)

    async def _analyze_async(self) -> dict:
        prompt = """
请对代码进行全面安全风险检查：

1. SQL 注入风险 - 检查是否存在拼接SQL语句
2. XSS 跨站脚本攻击 - 检查是否转义用户输入
3. 敏感信息泄露 - 检查是否有硬编码密码、API Key
4. 命令注入风险 - 检查是否执行用户输入的命令
5. 权限校验缺失 - 检查是否有未校验权限的接口

请按以下 JSON 格式输出评估结果：
{
    "level": "high/medium/low",
    "score": 0-100,
    "items": [
        {
            "type": "风险类型",
            "location": "文件路径:行号",
            "description": "问题描述"
        }
    ],
    "summary": "总体评估摘要"
}
"""

        options = ClaudeAgentOptions(
            allowed_tools=["Read", "Glob", "Grep"],
            permission_mode="acceptEdits",
            cwd=self.code_path
        )

        result_text = ""
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        result_text += block.text

        return self._parse_result(result_text)

    def _parse_result(self, text: str) -> dict:
        """解析 AI 返回结果"""
        try:
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                result = json.loads(match.group())
                # 确保必要字段存在
                result.setdefault('level', 'medium')
                result.setdefault('score', 50)
                result.setdefault('items', [])
                result.setdefault('summary', '')
                return result
        except:
            pass

        return {
            "level": "medium",
            "score": 50,
            "items": [],
            "summary": text[:500] if text else "无法解析评估结果"
        }
```

### 9.5 test_case_reader.py - 测试用例读取

```python
import pandas as pd
from typing import List, Dict

class TestCaseReader:
    """测试用例读取器"""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def read(self) -> List[Dict]:
        """
        读取 xlsx 测试用例

        Returns:
            测试用例列表
        """
        df = pd.read_excel(self.file_path)
        test_cases = []

        for _, row in df.iterrows():
            test_cases.append({
                'case_id': str(row.get('用例编号', '')),
                'requirement': str(row.get('对应需求', '')),
                'test_point': str(row.get('测试点', '')),
                'priority': str(row.get('优先级', '')),
                'precondition': str(row.get('前置条件', '')),
                'steps': str(row.get('操作步骤', '')),
                'expected': str(row.get('预期结果', ''))
            })

        return test_cases
```

### 9.6 test_executor.py - 测试用例执行

```python
import anyio
import json
import re
from datetime import datetime
from typing import List, Dict
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage
from claude_agent_sdk.types import TextBlock

class TestExecutor:
    """测试用例执行器"""

    def __init__(self, code_path: str):
        self.code_path = code_path

    def execute_all(self, test_cases: List[Dict]) -> List[Dict]:
        """执行所有测试用例"""
        results = []
        for case in test_cases:
            result = self.execute_one(case)
            results.append(result)
        return results

    def execute_one(self, case: Dict) -> Dict:
        """执行单个测试用例"""
        return anyio.run(self._execute_async, case)

    async def _execute_async(self, case: Dict) -> Dict:
        prompt = f"""
请检查代码是否满足以下测试用例要求：

【用例编号】{case['case_id']}
【对应需求】{case['requirement']}
【测试点】{case['test_point']}
【优先级】{case['priority']}
【前置条件】{case['precondition']}
【操作步骤】{case['steps']}
【预期结果】{case['expected']}

请判断代码是否实现了该测试用例的要求。
输出 JSON 格式：
{{
    "result": "passed/failed",
    "evidence": "校验依据（有理有据，说明为什么通过或失败）",
    "problem_code": "问题代码位置（如有失败，指出具体文件和代码）"
}}
"""

        options = ClaudeAgentOptions(
            allowed_tools=["Read", "Glob", "Grep"],
            permission_mode="acceptEdits",
            cwd=self.code_path
        )

        result_text = ""
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        result_text += block.text

        result = self._parse_result(result_text)
        result['case_id'] = case['case_id']
        result['test_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        result['requirement'] = case['requirement']
        result['test_point'] = case['test_point']
        return result

    def _parse_result(self, text: str) -> Dict:
        """解析结果"""
        try:
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                result = json.loads(match.group())
                result.setdefault('result', 'failed')
                result.setdefault('evidence', '')
                result.setdefault('problem_code', '')
                return result
        except:
            pass

        return {
            "result": "failed",
            "evidence": text[:500] if text else "无法解析结果",
            "problem_code": ""
        }
```

### 9.7 report_generator.py - 报告生成

```python
import json
import os
from datetime import datetime
from pathlib import Path
import pandas as pd

class ReportGenerator:
    """报告生成器 - 输出 JSON 和 Excel 格式"""

    def __init__(self, report_dir: str = 'reports'):
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, project_name: str, risk_result: dict,
                 test_results: list, code_path: str = '') -> dict:
        """
        生成报告

        Returns:
            包含报告路径的字典
        """
        # 生成任务ID
        task_id = f"TASK{datetime.now().strftime('%Y%m%d%H%M%S')}"
        task_dir = self.report_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # 构建报告数据
        report_data = {
            'task_id': task_id,
            'project_name': project_name,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'risk': risk_result,
            'test_results': test_results,
            'summary': {
                'total': len(test_results),
                'passed': sum(1 for r in test_results if r.get('result') == 'passed'),
                'failed': sum(1 for r in test_results if r.get('result') == 'failed')
            }
        }

        # 生成 JSON 报告
        json_path = task_dir / 'report.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        # 生成 Excel 报告
        excel_path = task_dir / 'report.xlsx'
        self._generate_excel(test_results, excel_path)

        return {
            'task_id': task_id,
            'url': f'/reports/{task_id}/report.json',
            'json_path': str(json_path),
            'excel_path': str(excel_path)
        }

    def _generate_excel(self, test_results: list, excel_path: Path):
        """生成 Excel 报告"""
        if not test_results:
            return

        df = pd.DataFrame(test_results)
        columns = ['case_id', 'requirement', 'test_point', 'result',
                   'test_time', 'evidence', 'problem_code']
        df = df[[c for c in columns if c in df.columns]]
        df.columns = ['用例编号', '对应需求', '测试点', '测试结果',
                      '测试时间', '校验依据', '问题代码']
        df.to_excel(excel_path, index=False)
```

## 10. 依赖清单

```txt
# Flask 后端
flask==3.0.0

# Claude Agent SDK（AI 风险评估核心）
claude-agent-sdk>=0.1.0
anyio>=4.0.0

# 数据处理
pandas==2.1.0
openpyxl==3.1.0

# 配置
pyyaml==6.0.1
```

## 11. 错误码定义

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1 | 检测失败（高风险或测试用例失败） |
| 1001 | 参数缺失 |
| 1002 | 参数格式错误 |
| 2001 | 测试用例文件不存在 |
| 5001 | 服务器内部错误 |
| 5002 | Git 操作失败 |
| 5003 | AI 分析异常 |

## 12. 开发里程碑

### 阶段一：基础框架（1天）
- [ ] 创建目录结构
- [ ] 编写 app.py 主入口
- [ ] 编写 git_handler.py（克隆代码）
- [ ] 编写 hash_checker.py（哈希检测）

### 阶段二：AI 风险评估（1天）
- [ ] 编写 ai_risk_analyzer.py
- [ ] 配置 risk_rules.yml
- [ ] 实现风险评分逻辑

### 阶段三：测试用例执行（1天）
- [ ] 编写 test_case_reader.py（读取xlsx）
- [ ] 编写 test_executor.py（逐条执行）
- [ ] 实现结果输出格式

### 阶段四：报告与部署（1天）
- [ ] 编写 report_generator.py（JSON + Excel）
- [ ] 测试完整流程
- [ ] 编写 Dockerfile
- [ ] 部署测试

## 13. 验收标准

| 验收项 | 成功标准 |
|--------|----------|
| API 接口 | POST /api/trigger 可正常调用 |
| 参数校验 | 缺少参数时返回错误码 1001 |
| Git 操作 | 能克隆仓库并获取代码 |
| 哈希检测 | 代码未变化时返回"代码未变化" |
| 风险评估 | 能输出风险等级和具体问题 |
| 高风险打回 | 高风险时返回 code=1 |
| 测试用例读取 | 能正确读取 xlsx 文件 |
| 测试用例执行 | 能逐条执行并输出详细结果 |
| 报告生成 | 能生成 JSON 和 Excel 报告 |

## 14. 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 创建必要目录
mkdir -p cache/hashes reports logs test_cases

# 3. 启动服务
python app.py

# 4. 测试接口
curl -X POST http://localhost:8000/api/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "MrDoc",
    "repo_url": "https://cnb.cool/test-2026_513/test.git",
    "test_case_file": "test_cases/mrdoc.xlsx"
  }'
```

## 15. 扩展说明

### 15.1 后续可扩展功能

| 功能 | 说明 |
|------|------|
| 数据库存储 | 使用 SQLite 存储检测历史 |
| Web 界面 | 添加前端页面查看报告 |
| 通知功能 | 邮件/飞书/企业微信通知 |
| 定时任务 | 定时检测代码变化 |
| 多项目配置 | 支持配置文件管理多项目 |

### 15.2 模块扩展点

- `ai_risk_analyzer.py`：可替换为其他 AI 模型
- `test_executor.py`：可添加更多测试类型支持
- `report_generator.py`：可添加更多报告格式
