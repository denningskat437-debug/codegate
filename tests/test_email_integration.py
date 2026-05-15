"""
邮件发送集成测试
测试真实的 SMTP 邮件发送功能
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from src.email_sender import EmailSender


class TestEmailSenderQQSMTP:
    """QQ 邮箱 SMTP 测试"""

    @pytest.fixture
    def qq_email_sender(self):
        """创建 QQ 邮箱发送器"""
        return EmailSender(
            smtp_host="smtp.qq.com",
            smtp_port=465,
            smtp_user="842588869@qq.com",
            smtp_password="gomctkpdckfdbdgd",
            from_email="842588869@qq.com",
            base_url="http://117.72.191.205:8000"
        )

    @pytest.fixture
    def report_data(self):
        """测试报告数据"""
        return {
            'task_id': 'TASK_TEST_001',
            'project_name': '测试项目',
            'generated_at': '2026-05-15 10:00:00',
            'risk': {
                'level': 'medium',
                'score': 45,
                'summary': '发现中风险问题，建议修复后提交',
                'items': [
                    {
                        'type': '代码规范',
                        'location': 'src/main.py:100',
                        'description': '函数复杂度过高，建议拆分'
                    }
                ]
            },
            'summary': {
                'total': 10,
                'passed': 8,
                'failed': 2,
                'pass_rate': '80.0%'
            },
            'user_info': {
                'build_user': 'abc1',
                'build_user_nickname': '测试用户',
                'build_user_email': '842588869@qq.com',
                'event': 'push',
                'branch': 'main',
                'commit_id': 'abc123',
                'commit_message': '测试提交',
                'committer': 'abc4',
                'committer_email': '19837229903@163.com'
            }
        }

    @pytest.mark.skip(reason="需要真实 SMTP 连接，跳过")
    def test_send_email_to_163_receiver(self, qq_email_sender, report_data):
        """测试发送邮件到 163 邮箱"""
        import smtplib
        from email.mime.multipart import MIMEMultipart

        # 使用 SSL 连接发送
        try:
            with smtplib.SMTP_SSL(qq_email_sender.smtp_host, qq_email_sender.smtp_port) as server:
                server.login(qq_email_sender.smtp_user, qq_email_sender.smtp_password)

                # 构建邮件
                subject = qq_email_sender._build_subject(report_data)
                body = qq_email_sender._build_body(report_data, '/reports/TASK_TEST_001/report.json')

                msg = MIMEMultipart()
                msg['From'] = qq_email_sender.from_email
                msg['To'] = '19837229903@163.com'
                msg['Subject'] = subject
                msg.attach(__import__('email.mime.text', fromlist=['MIMEText']).MIMEText(body, 'html', 'utf-8'))

                # 发送
                server.sendmail(qq_email_sender.from_email, '19837229903@163.com', msg.as_string())
                print(f"邮件发送成功: {qq_email_sender.from_email} -> 19837229903@163.com")
                assert True
        except Exception as e:
            pytest.fail(f"邮件发送失败: {e}")

    @pytest.mark.skip(reason="需要真实 SMTP 连接，跳过")
    def test_send_high_risk_email(self, qq_email_sender):
        """测试高风险邮件"""
        report_data = {
            'task_id': 'TASK_HIGH_RISK',
            'project_name': '高风险测试项目',
            'generated_at': '2026-05-15 10:00:00',
            'risk': {
                'level': 'high',
                'score': 85,
                'summary': '发现严重安全漏洞，需立即处理',
                'items': [
                    {'type': 'SQL注入', 'location': 'api/user.py:50', 'description': '用户输入未过滤'},
                    {'type': 'XSS漏洞', 'location': 'templates/index.html:20', 'description': '输出未转义'}
                ]
            },
            'summary': {'total': 5, 'passed': 2, 'failed': 3, 'pass_rate': '40.0%'},
            'user_info': {'committer': 'developer', 'committer_email': '19837229903@163.com'}
        }

        result = qq_email_sender.send_report_email('19837229903@163.com', report_data, '/reports/TASK_HIGH_RISK')
        assert result is True

    @pytest.mark.skip(reason="需要真实 SMTP 连接，跳过")
    def test_send_pass_email(self, qq_email_sender):
        """测试通过邮件"""
        report_data = {
            'task_id': 'TASK_PASS',
            'project_name': '通过测试项目',
            'generated_at': '2026-05-15 10:00:00',
            'risk': {
                'level': 'low',
                'score': 15,
                'summary': '代码质量良好，无重大风险'
            },
            'summary': {'total': 10, 'passed': 10, 'failed': 0, 'pass_rate': '100.0%'},
            'user_info': {'committer': 'developer', 'committer_email': '19837229903@163.com'}
        }

        result = qq_email_sender.send_report_email('19837229903@163.com', report_data, '/reports/TASK_PASS')
        assert result is True


class TestEmailSenderConfig:
    """邮件配置测试"""

    def test_qq_smtp_config(self):
        """测试 QQ 邮箱 SMTP 配置"""
        sender = EmailSender(
            smtp_host="smtp.qq.com",
            smtp_port=465,
            smtp_user="842588869@qq.com",
            smtp_password="gomctkpdckfdbdgd",
            from_email="842588869@qq.com"
        )

        assert sender.smtp_host == "smtp.qq.com"
        assert sender.smtp_port == 465
        assert sender.smtp_user == "842588869@qq.com"

    def test_build_email_subject_high_risk(self):
        """测试高风险邮件主题"""
        sender = EmailSender("smtp.qq.com", 465, "user", "pass", "from@qq.com")
        report = {'project_name': '测试项目', 'risk': {'level': 'high'}, 'summary': {'pass_rate': '50%'}}
        subject = sender._build_subject(report)
        assert '高风险' in subject

    def test_build_email_subject_passed(self):
        """测试通过邮件主题"""
        sender = EmailSender("smtp.qq.com", 465, "user", "pass", "from@qq.com")
        report = {'project_name': '测试项目', 'risk': {'level': 'low'}, 'summary': {'pass_rate': '100.0%'}}
        subject = sender._build_subject(report)
        assert '通过' in subject
