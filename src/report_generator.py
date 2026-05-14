"""
报告生成模块
生成 JSON 和 Excel 格式的测试报告
"""
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd

logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成器 - 输出 JSON 和 Excel 格式"""

    def __init__(self, report_dir: str = 'reports'):
        """
        初始化报告生成器

        Args:
            report_dir: 报告输出目录
        """
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        project_name: str,
        risk_result: Dict,
        test_results: List[Dict],
        commit_info: Dict = None
    ) -> Dict:
        """
        生成报告

        Args:
            project_name: 项目名称
            risk_result: 风险评估结果
            test_results: 测试用例执行结果
            commit_info: 提交信息（可选）

        Returns:
            包含报告路径信息的字典
        """
        # 生成任务ID
        task_id = f"TASK{datetime.now().strftime('%Y%m%d%H%M%S')}"
        task_dir = self.report_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # 计算统计信息
        total = len(test_results)
        passed = sum(1 for r in test_results if r.get('result') == 'passed')
        failed = total - passed

        # 构建报告数据
        report_data = {
            'task_id': task_id,
            'project_name': project_name,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'commit_info': commit_info or {},
            'risk': risk_result,
            'test_results': test_results,
            'summary': {
                'total': total,
                'passed': passed,
                'failed': failed,
                'pass_rate': f"{passed/total*100:.1f}%" if total > 0 else "0%"
            }
        }

        # 生成 JSON 报告
        json_path = task_dir / 'report.json'
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            logger.info(f"JSON 报告已生成: {json_path}")
        except Exception as e:
            logger.error(f"生成 JSON 报告失败: {e}")

        # 生成 Excel 报告
        excel_path = task_dir / 'report.xlsx'
        try:
            self._generate_excel(test_results, risk_result, excel_path)
            logger.info(f"Excel 报告已生成: {excel_path}")
        except Exception as e:
            logger.error(f"生成 Excel 报告失败: {e}")

        return {
            'task_id': task_id,
            'url': f'/reports/{task_id}/report.json',
            'json_path': str(json_path),
            'excel_path': str(excel_path)
        }

    def _generate_excel(
        self,
        test_results: List[Dict],
        risk_result: Dict,
        excel_path: Path
    ):
        """
        生成 Excel 报告

        Args:
            test_results: 测试结果列表
            risk_result: 风险评估结果
            excel_path: Excel 文件路径
        """
        # 创建多个工作表
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # 工作表1：测试结果
            if test_results:
                df_tests = pd.DataFrame(test_results)
                columns = ['case_id', 'requirement', 'test_point', 'priority',
                          'result', 'test_time', 'evidence', 'problem_code']
                df_tests = df_tests[[c for c in columns if c in df_tests.columns]]
                df_tests.columns = ['用例编号', '对应需求', '测试点', '优先级',
                                    '测试结果', '测试时间', '校验依据', '问题代码']
                df_tests.to_excel(writer, sheet_name='测试结果', index=False)

            # 工作表2：风险评估
            risk_data = {
                '风险等级': [risk_result.get('level', '')],
                '风险分数': [risk_result.get('score', 0)],
                '评估摘要': [risk_result.get('summary', '')]
            }
            df_risk = pd.DataFrame(risk_data)
            df_risk.to_excel(writer, sheet_name='风险评估', index=False)

            # 工作表3：风险详情
            risk_items = risk_result.get('items', [])
            if risk_items:
                df_items = pd.DataFrame(risk_items)
                df_items.columns = ['风险类型', '位置', '描述']
                df_items.to_excel(writer, sheet_name='风险详情', index=False)

    def get_report(self, task_id: str) -> Dict:
        """
        获取已生成的报告

        Args:
            task_id: 任务ID

        Returns:
            报告数据，不存在则返回 None
        """
        json_path = self.report_dir / task_id / 'report.json'
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def list_reports(self, limit: int = 20) -> List[Dict]:
        """
        列出最近的报告

        Args:
            limit: 最大返回数量

        Returns:
            报告列表
        """
        reports = []
        for task_dir in sorted(self.report_dir.iterdir(), reverse=True):
            if task_dir.is_dir() and task_dir.name.startswith('TASK'):
                json_path = task_dir / 'report.json'
                if json_path.exists():
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        reports.append({
                            'task_id': data.get('task_id'),
                            'project_name': data.get('project_name'),
                            'generated_at': data.get('generated_at'),
                            'summary': data.get('summary')
                        })

                        if len(reports) >= limit:
                            break

        return reports