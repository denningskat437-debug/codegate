"""
邮件发送模块单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.email_sender import EmailSender


class TestEmailSenderInit:
    """初始化测试"""

    def test_init_with_all_params(self):
        """测试完整参数初始化"""
        sender = EmailSender(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="user@test.com",
            smtp_password="password",
            from_email="user@test.com",
            base_url="http://test.com"
        )
        assert sender.smtp_host == "smtp.test.com"
        assert sender.smtp_port == 587
        assert sender.smtp_user == "user@test.com"
        assert sender.smtp_password == "password"
        assert sender.from_email == "user@test.com"
        assert sender.base_url == "http://test.com"

    def test_init_with_default_base_url(self):
        """测试默认 base_url"""
        sender = EmailSender(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="user@test.com",
            smtp_password="password",
            from_email="user@test.com"
        )
        assert sender.base_url == ""


class TestEmailSenderSendReportEmail:
    """send_report_email 方法测试"""

    @pytest.fixture
    def sender(self):
        return EmailSender(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="user@test.com",
            smtp_password="password",
            from_email="sender@test.com",
            base_url="http://test.com"
        )

    @pytest.fixture
    def report_data(self):
        return {
            'task_id': 'TASK001',
            'project_name': 'Test Project',
            'generated_at': '2024-01-01 12:00:00',
            'risk': {'level': 'low', 'score': 10, 'summary': 'Low risk'},
            'summary': {'total': 10, 'passed': 10, 'failed': 0, 'pass_rate': '100.0%'},
            'user_info': {'build_user_nickname': 'Test User'}
        }

    def test_send_email_empty_recipient(self, sender, report_data):
        """测试空收件人"""
        result = sender.send_report_email('', report_data)
        assert result is False

    def test_send_email_missing_smtp_config(self, report_data):
        """测试 SMTP 配置缺失"""
        sender = EmailSender('', 587, '', '', '')
        result = sender.send_report_email('test@test.com', report_data)
        assert result is False

    @patch('src.email_sender.smtplib.SMTP')
    def test_send_email_success(self, mock_smtp, sender, report_data):
        """测试成功发送邮件"""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = sender.send_report_email('test@test.com', report_data)

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.sendmail.assert_called_once()

    @patch('src.email_sender.smtplib.SMTP')
    def test_send_email_smtp_error(self, mock_smtp, sender, report_data):
        """测试 SMTP 错误"""
        mock_smtp.return_value.__enter__.return_value.login.side_effect = Exception("SMTP Error")

        result = sender.send_report_email('test@test.com', report_data)

        assert result is False


class TestEmailSenderBuildSubject:
    """_build_subject 方法测试"""

    @pytest.fixture
    def sender(self):
        return EmailSender("smtp.test.com", 587, "user", "pass", "from@test.com")

    def test_build_subject_high_risk(self, sender):
        """测试高风险主题"""
        report_data = {
            'project_name': 'Test Project',
            'risk': {'level': 'high', 'score': 80},
            'summary': {'pass_rate': '50.0%'}
        }
        subject = sender._build_subject(report_data)
        assert '高风险' in subject
        assert 'Test Project' in subject

    def test_build_subject_all_passed(self, sender):
        """测试全部通过主题"""
        report_data = {
            'project_name': 'Test Project',
            'risk': {'level': 'low'},
            'summary': {'pass_rate': '100.0%'}
        }
        subject = sender._build_subject(report_data)
        assert '通过' in subject

    def test_build_subject_partial_passed(self, sender):
        """测试部分通过主题"""
        report_data = {
            'project_name': 'Test Project',
            'risk': {'level': 'low'},
            'summary': {'pass_rate': '80.0%'}
        }
        subject = sender._build_subject(report_data)
        assert '待处理' in subject
        assert '80.0%' in subject


class TestEmailSenderBuildBody:
    """_build_body 方法测试"""

    @pytest.fixture
    def sender(self):
        return EmailSender("smtp.test.com", 587, "user", "pass", "from@test.com", "http://test.com")

    def test_build_body_contains_project_name(self, sender):
        """测试正文包含项目名"""
        report_data = {
            'task_id': 'TASK001',
            'project_name': 'Test Project',
            'generated_at': '2024-01-01 12:00:00',
            'risk': {'level': 'low', 'score': 10, 'summary': 'Low risk'},
            'summary': {'total': 10, 'passed': 10, 'failed': 0, 'pass_rate': '100.0%'},
            'user_info': {}
        }
        body = sender._build_body(report_data, '/reports/TASK001')
        assert 'Test Project' in body
        assert 'TASK001' in body

    def test_build_body_with_report_url(self, sender):
        """测试正文包含报告链接"""
        report_data = {
            'task_id': 'TASK001',
            'project_name': 'Test',
            'generated_at': '2024-01-01',
            'risk': {'level': 'low', 'score': 10, 'summary': ''},
            'summary': {'total': 1, 'passed': 1, 'failed': 0, 'pass_rate': '100%'},
            'user_info': {}
        }
        body = sender._build_body(report_data, '/reports/TASK001')
        assert 'http://test.com/reports/TASK001' in body

    def test_build_body_without_report_url(self, sender):
        """测试正文无报告链接"""
        report_data = {
            'task_id': 'TASK001',
            'project_name': 'Test',
            'generated_at': '2024-01-01',
            'risk': {'level': 'low', 'score': 10, 'summary': ''},
            'summary': {'total': 1, 'passed': 1, 'failed': 0, 'pass_rate': '100%'},
            'user_info': {}
        }
        body = sender._build_body(report_data, '')
        assert '查看完整报告' not in body or '请登录系统查看' in body


class TestEmailSenderBuildRiskSection:
    """_build_risk_section 方法测试"""

    @pytest.fixture
    def sender(self):
        return EmailSender("smtp.test.com", 587, "user", "pass", "from@test.com")

    def test_build_risk_section_high(self, sender):
        """测试高风险部分"""
        risk = {'level': 'high', 'score': 80, 'summary': 'High risk detected'}
        html = sender._build_risk_section(risk)
        assert '高风险' in html
        assert '80' in html

    def test_build_risk_section_with_items(self, sender):
        """测试包含风险项"""
        risk = {
            'level': 'medium',
            'score': 50,
            'summary': 'Medium risk',
            'items': [
                {'type': 'SQL注入', 'location': 'file.py:10', 'description': 'SQL injection risk'}
            ]
        }
        html = sender._build_risk_section(risk)
        assert 'SQL注入' in html
        assert 'file.py:10' in html


class TestEmailSenderBuildTestSection:
    """_build_test_section 方法测试"""

    @pytest.fixture
    def sender(self):
        return EmailSender("smtp.test.com", 587, "user", "pass", "from@test.com")

    def test_build_test_section_all_passed(self, sender):
        """测试全部通过"""
        summary = {'total': 10, 'passed': 10, 'failed': 0, 'pass_rate': '100.0%'}
        html = sender._build_test_section(summary)
        assert '全部通过' in html
        assert '10' in html

    def test_build_test_section_some_failed(self, sender):
        """测试部分失败"""
        summary = {'total': 10, 'passed': 8, 'failed': 2, 'pass_rate': '80.0%'}
        html = sender._build_test_section(summary)
        assert '2 条失败' in html


class TestEmailSenderBuildUserSection:
    """_build_user_section 方法测试"""

    @pytest.fixture
    def sender(self):
        return EmailSender("smtp.test.com", 587, "user", "pass", "from@test.com")

    def test_build_user_section_with_info(self, sender):
        """测试包含用户信息"""
        user_info = {
            'build_user_nickname': 'Test User',
            'build_user_email': 'test@test.com',
            'event': 'push',
            'branch': 'main'
        }
        html = sender._build_user_section(user_info)
        assert 'Test User' in html
        assert 'test@test.com' in html
        assert 'push' in html
        assert 'main' in html

    def test_build_user_section_empty(self, sender):
        """测试空用户信息"""
        html = sender._build_user_section({})
        assert html == ""

    def test_build_user_section_with_committer(self, sender):
        """测试包含提交者信息 - 当前版本只显示触发者"""
        user_info = {
            'committer': 'committer_user',
            'committer_email': 'committer@test.com'
        }
        html = sender._build_user_section(user_info)
        # 当前版本只显示触发者信息，提交者信息需要扩展
        # 如果没有触发者信息，返回空字符串
        assert html == ""
