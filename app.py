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
from src.config_manager import config
from src.email_sender import EmailSender
from src.code_analyzer import CodeAnalyzer


def _resolve_committer_email(user_info: dict) -> str:
    """从用户映射 Excel 文件获取提交者邮箱"""
    committer = user_info.get('committer', '')

    if not committer:
        logger.warning("未提供提交者用户名，无法查找邮箱")
        return ''

    if not config.get('user_mapping.enabled', False):
        logger.warning("用户映射功能未启用")
        return ''

    try:
        from src.user_mapping_reader import UserMappingReader
        mapping_file = config.get('user_mapping.file', 'data/user_mapping.xlsx')
        reader = UserMappingReader(mapping_file)
        mapped_email = reader.get_email(committer)
        if mapped_email:
            logger.info(f"从用户映射获取提交者邮箱: {committer} -> {mapped_email}")
            return mapped_email
        else:
            logger.warning(f"用户映射中未找到用户: {committer}")
    except FileNotFoundError:
        logger.warning(f"用户映射文件不存在: {mapping_file}")
    except Exception as e:
        logger.warning(f"读取用户映射失败: {e}")

    return ''


def _send_email_notification(project_name: str, risk_result: dict, test_results: list, user_info: dict, report: dict):
    """发送邮件通知（统一处理高风险和正常流程）"""
    if not config.get('email.enabled', False):
        return

    try:
        email_sender = EmailSender(
            smtp_host=config.get('email.smtp_host', ''),
            smtp_port=config.get('email.smtp_port', 465),
            smtp_user=config.get('email.smtp_user', ''),
            smtp_password=os.getenv('SMTP_PASSWORD', config.get('email.smtp_password', '')),
            from_email=config.get('email.from_email', ''),
            base_url=config.get('email.base_url', ''),
            use_ssl=config.get('email.use_ssl', False)
        )

        # 从已生成的报告获取数据
        report_json_path = Path('reports') / report.get('task_id') / 'report.json'
        if report_json_path.exists():
            import json
            with open(report_json_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
        else:
            passed_count = sum(1 for r in test_results if r.get('result') == 'passed')
            report_data = {
                'task_id': report.get('task_id', ''),
                'project_name': project_name,
                'risk': risk_result,
                'summary': {
                    'total': len(test_results),
                    'passed': passed_count,
                    'failed': len(test_results) - passed_count,
                    'pass_rate': f"{passed_count/len(test_results)*100:.1f}%" if test_results else "0%"
                },
                'user_info': user_info
            }

        # 获取提交者邮箱
        to_email = _resolve_committer_email(user_info)

        if to_email:
            email_sender.send_report_email(to_email, report_data, report.get('url', ''))
        else:
            logger.warning("无有效提交者邮箱，跳过邮件发送")

    except Exception as e:
        logger.warning(f"邮件发送异常: {e}")


# 配置日志
logging.basicConfig(
    level=getattr(logging, config.get('logging.level', 'INFO')),
    format=config.get('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.get('logging.file', 'logs/codegate.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 创建 Flask 应用
app = Flask(__name__)

# 确保必要目录存在
Path(config.get('paths.cache_dir', 'cache/hashes')).mkdir(parents=True, exist_ok=True)
Path(config.get('paths.report_dir', 'reports')).mkdir(parents=True, exist_ok=True)
Path(config.get('paths.log_dir', 'logs')).mkdir(parents=True, exist_ok=True)


@app.route('/api/trigger', methods=['POST'])
def trigger():
    """
    触发检测接口

    请求参数：
    - project_name: 项目名称（必填）
    - repo_url: 仓库链接（必填）
    - test_case_file: 测试用例文件路径（必填）
    - branch: 分支名称（可选，默认 main）
    - build_user: 触发者用户名（可选）
    - build_user_nickname: 触发者昵称（可选）
    - build_user_email: 触发者邮箱（可选）
    - event: 触发事件（可选）
    - commit_id: 提交ID（可选）
    - committer: 提交者（可选）

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

    # 新增用户相关参数
    build_user = data.get('build_user', '')
    build_user_nickname = data.get('build_user_nickname', '')
    event = data.get('event', '')
    commit_id = data.get('commit_id', '')
    committer = data.get('committer', '')

    user_info = {
        'build_user': build_user,
        'build_user_nickname': build_user_nickname,
        'event': event,
        'branch': branch,
        'commit_id': commit_id,
        'committer': committer
    }

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
    if build_user_nickname:
        logger.info(f"触发用户: {build_user_nickname}")

    git = None
    code_stats = None
    try:
        # ========== 第一步：拉取代码 ==========
        logger.info(">>> 第一步：拉取代码")
        git = GitHandler(repo_url, branch)
        code_path = git.clone()

        # ========== 第二步：代码统计分析 ==========
        logger.info(">>> 第二步：代码统计分析")
        code_analyzer = CodeAnalyzer(code_path)
        code_stats = code_analyzer.analyze()

        logger.info(f"代码总量: {code_stats.get('total_lines')} 行")
        logger.info(f"文件数量: {code_stats.get('total_files')} 个")
        logger.info(f"项目类型: {code_stats.get('project_type')}")

        # ========== 第三步：哈希检测 ==========
        logger.info(">>> 第三步：哈希检测")
        hash_checker = HashChecker()
        current_hash = hash_checker.get_hash(code_path)
        cached_hash = hash_checker.get_cached_hash(project_name)

        if current_hash == cached_hash:
            logger.info("代码未变化，跳过检测")
            git.cleanup()
            return jsonify(ResponseBuilder.no_change())

        logger.info(f"代码已变化: {current_hash[:8]}...")

        # ========== 第四步：风险评估 ==========
        logger.info(">>> 第四步：AI 风险评估")
        risk_analyzer = AIRiskAnalyzer(code_path)
        risk_result = risk_analyzer.analyze()

        logger.info(f"风险等级: {risk_result.get('level')}")
        logger.info(f"风险分数: {risk_result.get('score')}")

        # 高风险直接打回
        if risk_result.get('level') == 'high':
            logger.warning("高风险代码，直接打回")

            commit_info = git.get_commit_info()

            report_gen = ReportGenerator()
            report = report_gen.generate(
                project_name, risk_result, [], commit_info, user_info,
                code_stats=code_stats, time_stats={'total_time': 0, 'average_time': 0}
            )

            _send_email_notification(project_name, risk_result, [], user_info, report)

            git.cleanup()
            return jsonify(ResponseBuilder.risk_reject(risk_result, report.get('url')))

        # ========== 第五步：测试用例校验 ==========
        logger.info(">>> 第五步：测试用例校验")

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

        # 执行测试用例（增强版，返回结果和时间统计）
        executor = TestExecutor(code_path, code_stats=code_stats, project_type=code_stats.get('project_type'))
        execution_result = executor.execute_all(test_cases)
        test_results = execution_result['results']
        time_stats = execution_result['time_stats']

        logger.info(f"总执行时间: {time_stats.get('total_time')} 秒")
        logger.info(f"平均执行时间: {time_stats.get('average_time')} 秒/用例")

        # 判断是否全部通过
        all_passed = all(r.get('result') == 'passed' for r in test_results)

        # ========== 第六步：生成报告 ==========
        logger.info(">>> 第六步：生成报告")
        commit_info = git.get_commit_info()

        report_gen = ReportGenerator()
        report = report_gen.generate(
            project_name, risk_result, test_results, commit_info, user_info,
            code_stats=code_stats, time_stats=time_stats
        )

        # ========== 第七步：更新哈希缓存 ==========
        if all_passed:
            hash_checker.save_hash(project_name, current_hash)
            logger.info("已更新哈希缓存")

        # ========== 第八步：清理并返回 ==========
        git.cleanup()

        logger.info(f"检测完成: {'全部通过' if all_passed else '存在失败'}")
        logger.info("=" * 50)

        # ========== 第九步：发送邮件通知 ==========
        _send_email_notification(project_name, risk_result, test_results, user_info, report)

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
    host = config.get('server.host', '0.0.0.0')
    port = config.get('server.port', 8000)
    debug = config.get('server.debug', False)

    logger.info("CodeGate 服务启动")
    logger.info(f"监听地址: http://{host}:{port}")
    logger.info("API 文档: POST /api/trigger")
    app.run(host=host, port=port, debug=debug)
