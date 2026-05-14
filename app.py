"""
CodeGate Flask 主入口
自动化代码风险检测与测试准入 API
"""
import logging
import os
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from pathlib import Path

# 导入核心模块
from src.git_handler import GitHandler
from src.hash_checker import HashChecker
from src.ai_risk_analyzer import AIRiskAnalyzer
from src.test_case_reader import TestCaseReader
from src.test_executor import TestExecutor
from src.report_generator import ReportGenerator
from src.response_builder import ResponseBuilder

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/codegate.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 创建 Flask 应用
app = Flask(__name__)

# 确保必要目录存在
Path('cache/hashes').mkdir(parents=True, exist_ok=True)
Path('reports').mkdir(parents=True, exist_ok=True)
Path('logs').mkdir(parents=True, exist_ok=True)


@app.route('/api/trigger', methods=['POST'])
def trigger():
    """
    触发检测接口

    请求参数：
    - project_name: 项目名称（必填）
    - repo_url: 仓库链接（必填）
    - test_case_file: 测试用例文件路径（必填）
    - branch: 分支名称（可选，默认 main）

    返回：
    - code: 状态码
    - message: 消息
    - data: 结果数据
    """
    logger.info("=" * 50)
    logger.info("收到检测请求")

    # 获取请求参数
    data = request.json or {}
    project_name = data.get('project_name')
    repo_url = data.get('repo_url')
    test_case_file = data.get('test_case_file')
    branch = data.get('branch', 'main')

    # 参数校验
    if not project_name:
        return jsonify(ResponseBuilder.error(1001, '参数缺失：project_name')), 400
    if not repo_url:
        return jsonify(ResponseBuilder.error(1001, '参数缺失：repo_url')), 400
    if not test_case_file:
        return jsonify(ResponseBuilder.error(1001, '参数缺失：test_case_file')), 400

    logger.info(f"项目: {project_name}")
    logger.info(f"仓库: {repo_url}")
    logger.info(f"分支: {branch}")
    logger.info(f"测试用例: {test_case_file}")

    git = None
    try:
        # ========== 第一步：拉取代码 ==========
        logger.info(">>> 第一步：拉取代码")
        git = GitHandler(repo_url, branch)
        code_path = git.clone()

        # ========== 第二步：哈希检测 ==========
        logger.info(">>> 第二步：哈希检测")
        hash_checker = HashChecker()
        current_hash = hash_checker.get_hash(code_path)
        cached_hash = hash_checker.get_cached_hash(project_name)

        if current_hash == cached_hash:
            logger.info("代码未变化，跳过检测")
            git.cleanup()
            return jsonify(ResponseBuilder.no_change())

        logger.info(f"代码已变化: {current_hash[:8]}...")

        # ========== 第三步：风险评估 ==========
        logger.info(">>> 第三步：AI 风险评估")
        risk_analyzer = AIRiskAnalyzer(code_path)
        risk_result = risk_analyzer.analyze()

        logger.info(f"风险等级: {risk_result.get('level')}")
        logger.info(f"风险分数: {risk_result.get('score')}")

        # 高风险直接打回
        if risk_result.get('level') == 'high':
            logger.warning("高风险代码，直接打回")

            # 获取提交信息
            commit_info = git.get_commit_info()

            # 生成报告
            report_gen = ReportGenerator()
            report = report_gen.generate(project_name, risk_result, [], commit_info)

            git.cleanup()
            return jsonify(ResponseBuilder.risk_reject(risk_result, report.get('url')))

        # ========== 第四步：测试用例校验 ==========
        logger.info(">>> 第四步：测试用例校验")

        # 读取测试用例
        test_reader = TestCaseReader(test_case_file)
        try:
            test_cases = test_reader.read()
        except FileNotFoundError:
            git.cleanup()
            return jsonify(ResponseBuilder.error(2001, f'测试用例文件不存在: {test_case_file}')), 400
        except ValueError as e:
            git.cleanup()
            return jsonify(ResponseBuilder.error(2002, str(e))), 400

        if not test_cases:
            git.cleanup()
            return jsonify(ResponseBuilder.error(2002, '测试用例文件为空')), 400

        logger.info(f"读取到 {len(test_cases)} 条测试用例")

        # 执行测试用例
        executor = TestExecutor(code_path)
        test_results = executor.execute_all(test_cases)

        # 判断是否全部通过
        all_passed = all(r.get('result') == 'passed' for r in test_results)

        # ========== 第五步：生成报告 ==========
        logger.info(">>> 第五步：生成报告")
        commit_info = git.get_commit_info()

        report_gen = ReportGenerator()
        report = report_gen.generate(project_name, risk_result, test_results, commit_info)

        # ========== 第六步：更新哈希缓存 ==========
        if all_passed:
            hash_checker.save_hash(project_name, current_hash)
            logger.info("已更新哈希缓存")

        # ========== 第七步：清理并返回 ==========
        git.cleanup()

        logger.info(f"检测完成: {'全部通过' if all_passed else '存在失败'}")
        logger.info("=" * 50)

        return jsonify(ResponseBuilder.test_result(test_results, all_passed, report.get('url')))

    except RuntimeError as e:
        logger.error(f"运行时错误: {e}")
        if git:
            git.cleanup()
        return jsonify(ResponseBuilder.error(5002, str(e))), 500

    except Exception as e:
        logger.exception(f"未知错误: {e}")
        if git:
            git.cleanup()
        return jsonify(ResponseBuilder.error(5001, str(e))), 500


@app.route('/api/health', methods=['GET'])
def health():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'service': 'CodeGate',
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@app.route('/api/reports/<task_id>', methods=['GET'])
def get_report(task_id):
    """获取报告"""
    report_gen = ReportGenerator()
    report = report_gen.get_report(task_id)

    if report:
        return jsonify(report)
    return jsonify({'code': 404, 'message': '报告不存在'}), 404


@app.route('/api/reports', methods=['GET'])
def list_reports():
    """列出最近的报告"""
    limit = request.args.get('limit', 20, type=int)
    report_gen = ReportGenerator()
    reports = report_gen.list_reports(limit)
    return jsonify({'code': 0, 'data': reports})


@app.route('/reports/<task_id>/<filename>', methods=['GET'])
def download_report(task_id, filename):
    """下载报告文件"""
    file_path = Path('reports') / task_id / filename
    if file_path.exists():
        return send_file(file_path)
    return jsonify({'code': 404, 'message': '文件不存在'}), 404


if __name__ == '__main__':
    logger.info("CodeGate 服务启动")
    logger.info("监听地址: http://0.0.0.0:8000")
    logger.info("API 文档: POST /api/trigger")
    app.run(host='0.0.0.0', port=8000, debug=False)
