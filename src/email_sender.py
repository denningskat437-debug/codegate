"""
邮件发送模块
检测完成后发送邮件通知用户
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class EmailSender:
    """邮件发送器"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
        base_url: str = "",
        use_ssl: bool = False
    ):
        """
        初始化邮件发送器

        Args:
            smtp_host: SMTP 服务器地址
            smtp_port: SMTP 端口
            smtp_user: SMTP 用户名
            smtp_password: SMTP 密码
            from_email: 发件人邮箱
            base_url: 报告基础URL（可选）
            use_ssl: 是否使用 SSL 连接（QQ邮箱需要）
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.base_url = base_url
        self.use_ssl = use_ssl

    def send_report_email(self, to_email: str, report_data: Dict, report_url: str = '') -> bool:
        """
        发送检测报告邮件

        Args:
            to_email: 收件人邮箱
            report_data: 报告数据
            report_url: 报告URL

        Returns:
            是否发送成功
        """
        if not to_email:
            logger.warning("收件人邮箱为空，跳过邮件发送")
            return False

        if not self.smtp_host or not self.smtp_user:
            logger.warning("SMTP 配置不完整，跳过邮件发送")
            return False

        # 构建邮件内容
        subject = self._build_subject(report_data)
        body = self._build_body(report_data, report_url)

        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = self.from_email
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'html', 'utf-8'))

        # 发送邮件
        try:
            if self.use_ssl:
                # 使用 SSL 连接（QQ邮箱等）
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.from_email, to_email, msg.as_string())
            else:
                # 使用 TLS 连接
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.from_email, to_email, msg.as_string())

            logger.info(f"邮件已发送至: {to_email}")
            return True
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False

    def _build_subject(self, report_data: Dict) -> str:
        """构建邮件主题"""
        risk_level = report_data.get('risk', {}).get('level', 'unknown')
        summary = report_data.get('summary', {})
        pass_rate = summary.get('pass_rate', '0%')
        project_name = report_data.get('project_name', '未知项目')

        if risk_level == 'high':
            return f"【高风险】{project_name} 检测报告 - 需立即处理"
        elif pass_rate == '100.0%':
            return f"【通过】{project_name} 检测报告 - 可进入提测"
        else:
            return f"【待处理】{project_name} 检测报告 - 通过率 {pass_rate}"

    def _build_body(self, report_data: Dict, report_url: str) -> str:
        """构建邮件正文（HTML格式，增强版）"""
        project_name = report_data.get('project_name', '未知项目')
        task_id = report_data.get('task_id', '')
        generated_at = report_data.get('generated_at', '')
        risk = report_data.get('risk', {})
        summary = report_data.get('summary', {})
        user_info = report_data.get('user_info', {})
        code_stats = report_data.get('code_statistics', {})
        time_stats = report_data.get('test_time_statistics', {})
        aggregated = report_data.get('aggregated_analysis', {})

        # 各部分 HTML
        code_html = self._build_code_stats_section(code_stats)
        time_html = self._build_time_stats_section(time_stats)
        user_html = self._build_user_section(user_info)
        risk_html = self._build_risk_section(risk)
        test_html = self._build_test_section(summary)
        conclusion_html = self._build_conclusion_section(aggregated)

        # 报告链接
        report_link = f"{self.base_url}{report_url}" if report_url and self.base_url else ""

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .code-stats {{ background: #e3f2fd; }}
                .time-stats {{ background: #fff3e0; }}
                .conclusion {{ background: #e8f5e9; }}
                .risk-high {{ color: #d32f2f; font-weight: bold; }}
                .risk-medium {{ color: #f57c00; font-weight: bold; }}
                .risk-low {{ color: #388e3c; font-weight: bold; }}
                .pass {{ color: #388e3c; }}
                .fail {{ color: #d32f2f; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background: #f5f5f5; }}
                .btn {{ display: inline-block; padding: 10px 20px; background: #1976d2; color: white; text-decoration: none; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>CodeGate 检测报告</h2>
                    <p><strong>项目:</strong> {project_name}</p>
                    <p><strong>任务ID:</strong> {task_id}</p>
                    <p><strong>检测时间:</strong> {generated_at}</p>
                </div>

                {code_html}
                {user_html}
                {risk_html}
                {time_html}
                {test_html}
                {conclusion_html}

                <div class="section">
                    <h3>详细报告</h3>
                    <p>{f'<a href="{report_link}" class="btn">查看完整报告</a>' if report_link else '请登录系统查看详细报告'}</p>
                </div>

                <div class="section" style="background: #f9f9f9; font-size: 12px; color: #666;">
                    <p>此邮件由 CodeGate 自动发送，请勿直接回复。</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def _build_code_stats_section(self, code_stats: Dict) -> str:
        """构建代码统计部分 HTML"""
        if not code_stats:
            return ""

        total_lines = code_stats.get('total_lines', 0)
        total_files = code_stats.get('total_files', 0)
        project_type = code_stats.get('project_type', 'unknown')
        main_languages = code_stats.get('main_languages', [])

        return f"""
        <div class="section code-stats">
            <h3>代码统计</h3>
            <p><strong>代码总量:</strong> {total_lines:,} 行</p>
            <p><strong>文件数量:</strong> {total_files} 个</p>
            <p><strong>项目类型:</strong> {project_type}</p>
            <p><strong>主要语言:</strong> {', '.join(main_languages) if main_languages else '未知'}</p>
        </div>
        """

    def _build_time_stats_section(self, time_stats: Dict) -> str:
        """构建时间统计部分 HTML"""
        if not time_stats:
            return ""

        total_time = time_stats.get('total_execution_time', 0)
        avg_time = time_stats.get('average_execution_time', 0)
        min_time = time_stats.get('min_execution_time', 0)
        max_time = time_stats.get('max_execution_time', 0)
        case_count = time_stats.get('case_count', 0)

        return f"""
        <div class="section time-stats">
            <h3>测试执行时间</h3>
            <p><strong>用例数量:</strong> {case_count} 条</p>
            <p><strong>总执行时间:</strong> {total_time} 秒</p>
            <p><strong>平均执行时间:</strong> {avg_time} 秒/用例</p>
            <p><strong>最快用例:</strong> {min_time} 秒</p>
            <p><strong>最慢用例:</strong> {max_time} 秒</p>
        </div>
        """

    def _build_conclusion_section(self, aggregated: Dict) -> str:
        """构建分析结论部分 HTML"""
        if not aggregated:
            return ""

        strengths = aggregated.get('strengths', [])[:3]
        weaknesses = aggregated.get('weaknesses', [])[:3]
        conclusions = aggregated.get('conclusions', [])[:3]

        html = '<div class="section conclusion"><h3>分析结论</h3>'

        if strengths:
            html += '<p><strong>优点:</strong></p><ul>'
            for s in strengths:
                html += f'<li>{s}</li>'
            html += '</ul>'

        if weaknesses:
            html += '<p><strong>待改进:</strong></p><ul>'
            for w in weaknesses:
                html += f'<li>{w}</li>'
            html += '</ul>'

        if conclusions:
            html += '<p><strong>详细结论:</strong></p><ul>'
            for c in conclusions:
                html += f'<li>[{c.get("case_id", "")}] {c.get("conclusion", "")}</li>'
            html += '</ul>'

        html += '</div>'
        return html

    def _build_risk_section(self, risk: Dict) -> str:
        """构建风险部分 HTML"""
        level = risk.get('level', 'unknown')
        score = risk.get('score', 0)
        summary = risk.get('summary', '')
        items = risk.get('items', [])

        level_class = f"risk-{level}"
        level_text = {'high': '高风险', 'medium': '中风险', 'low': '低风险'}.get(level, level)

        items_html = ""
        if items:
            rows = []
            for item in items[:10]:
                rows.append(f"""
                    <tr>
                        <td>{item.get('type', '')}</td>
                        <td>{item.get('location', '')}</td>
                        <td>{item.get('description', '')[:100]}</td>
                    </tr>
                """)
            items_html = "<table><tr><th>风险类型</th><th>位置</th><th>描述</th></tr>" + "".join(rows) + "</table>"
            if len(items) > 10:
                items_html += f"<p>还有 {len(items) - 10} 条风险项，请查看完整报告</p>"

        return f"""
        <div class="section">
            <h3>风险评估</h3>
            <p><strong>风险等级:</strong> <span class="{level_class}">{level_text}</span></p>
            <p><strong>风险分数:</strong> {score}</p>
            <p><strong>评估摘要:</strong> {summary}</p>
            {items_html}
        </div>
        """

    def _build_test_section(self, summary: Dict) -> str:
        """构建测试结果部分 HTML"""
        total = summary.get('total', 0)
        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        pass_rate = summary.get('pass_rate', '0%')

        status = "全部通过，可进入提测" if failed == 0 else f"存在 {failed} 条失败用例"

        return f"""
        <div class="section">
            <h3>测试用例结果</h3>
            <p><strong>状态:</strong> {status}</p>
            <p><strong>总计:</strong> {total} 条</p>
            <p class="pass"><strong>通过:</strong> {passed} 条</p>
            <p class="fail"><strong>失败:</strong> {failed} 条</p>
            <p><strong>通过率:</strong> {pass_rate}</p>
        </div>
        """

    def _build_user_section(self, user_info: Dict) -> str:
        """构建用户信息部分 HTML"""
        if not user_info:
            return ""

        nickname = user_info.get('build_user_nickname', '')
        email = user_info.get('build_user_email', '')
        event = user_info.get('event', '')
        branch = user_info.get('branch', '')

        if not nickname and not email:
            return ""

        return f"""
        <div class="section">
            <h3>触发信息</h3>
            {f'<p><strong>触发者:</strong> {nickname}</p>' if nickname else ''}
            {f'<p><strong>邮箱:</strong> {email}</p>' if email else ''}
            {f'<p><strong>触发事件:</strong> {event}</p>' if event else ''}
            {f'<p><strong>分支:</strong> {branch}</p>' if branch else ''}
        </div>
        """
