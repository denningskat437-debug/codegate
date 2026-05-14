# CodeGate

自动化代码风险检测与测试准入平台

## 功能特性

- 代码拉取与哈希检测
- AI 风险评估（使用 Claude Agent SDK）
- 测试用例校验
- JSON/Excel 报告生成

## API 接口

### POST /api/trigger

触发检测接口

**请求参数：**
```json
{
  "project_name": "项目名称",
  "repo_url": "仓库链接",
  "test_case_file": "测试用例文件路径",
  "branch": "分支名称（可选，默认 main）"
}
```

### GET /api/health

健康检查接口

## 部署

详见 [DEPLOY.md](DEPLOY.md)

## 目录结构

```
codegate/
├── app.py                      # Flask 主入口
├── requirements.txt            # 依赖清单
├── configs/
│   └── risk_rules.yml          # 风险评分规则
├── src/
│   ├── git_handler.py          # Git 操作
│   ├── hash_checker.py         # 哈希检测
│   ├── ai_risk_analyzer.py     # AI 风险评估
│   ├── test_case_reader.py     # 测试用例读取
│   ├── test_executor.py        # 测试用例执行
│   ├── report_generator.py     # 报告生成
│   └── response_builder.py     # 响应构建
├── test_cases/                 # 测试用例目录
├── cache/                      # 缓存目录
├── reports/                    # 报告目录
└── logs/                       # 日志目录
```
