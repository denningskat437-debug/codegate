"""
报告生成模块
生成 JSON 和 Excel 格式的测试报告（增强版）
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd

from src.concurrency_manager import task_id_generator

logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成器 - 输出 JSON 和 Excel 格式（增强版）"""

    def __init__(self, report_dir: str = 'reports'):
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        project_name: str,
        risk_result: Dict,
        test_results: List[Dict],
        commit_info: Dict = None,
        user_info: Dict = None,
        code_stats: Dict = None,
        time_stats: Dict = None
    ) -> Dict:
        """
        生成增强报告

        Args:
            project_name: 项目名称
            risk_result: 风险评估结果
            test_results: 测试用例执行结果
            commit_info: 提交信息（可选）
            user_info: 用户信息（可选）
            code_stats: 代码统计信息（新增）
            time_stats: 测试时间统计（新增）

        Returns:
            包含报告路径信息的字典
        """
        task_id = task_id_generator.generate("TASK")
        task_dir = self.report_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        total = len(test_results)
        passed = sum(1 for r in test_results if r.get('result') == 'passed')
        failed = total - passed

        # 构建增强报告数据
        report_data = {
            'task_id': task_id,
            'project_name': project_name,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'commit_info': commit_info or {},
            'user_info': user_info or {},

            # 新增：代码统计信息
            'code_statistics': {
                'total_lines': code_stats.get('total_lines', 0) if code_stats else 0,
                'total_files': code_stats.get('total_files', 0) if code_stats else 0,
                'source_files': code_stats.get('source_files', 0) if code_stats else 0,
                'language_distribution': code_stats.get('language_distribution', {}) if code_stats else {},
                'project_type': code_stats.get('project_type', 'unknown') if code_stats else 'unknown',
                'main_languages': code_stats.get('main_languages', []) if code_stats else []
            },

            # 原有：风险评估
            'risk': risk_result,

            # 新增：测试时间统计
            'test_time_statistics': {
                'total_execution_time': time_stats.get('total_time', 0) if time_stats else 0,
                'average_execution_time': time_stats.get('average_time', 0) if time_stats else 0,
                'min_execution_time': time_stats.get('min_time', 0) if time_stats else 0,
                'max_execution_time': time_stats.get('max_time', 0) if time_stats else 0,
                'start_time': time_stats.get('start_time', '') if time_stats else '',
                'end_time': time_stats.get('end_time', '') if time_stats else '',
                'case_count': time_stats.get('case_count', 0) if time_stats else 0
            },

            # 原有：测试结果
            'test_results': test_results,

            # 原有：测试摘要
            'summary': {
                'total': total,
                'passed': passed,
                'failed': failed,
                'pass_rate': f"{passed/total*100:.1f}%" if total > 0 else "0%"
            },

            # 新增：汇总分析（从测试结果中提取）
            'aggregated_analysis': self._aggregate_analysis(test_results)
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
            self._generate_excel_enhanced(report_data, excel_path)
            logger.info(f"Excel 报告已生成: {excel_path}")
        except Exception as e:
            logger.error(f"生成 Excel 报告失败: {e}")

        return {
            'task_id': task_id,
            'url': f'/reports/{task_id}/report.json',
            'json_path': str(json_path),
            'excel_path': str(excel_path)
        }

    def _aggregate_analysis(self, test_results: List[Dict]) -> Dict:
        """汇总所有测试用例的分析结果"""
        all_frontend_issues = []
        all_backend_issues = []
        all_key_evidence = []
        all_strengths = []
        all_weaknesses = []
        all_potential_issues = []
        conclusions = []

        for result in test_results:
            analysis = result.get('analysis', {})

            # 汇总前端问题
            for issue in analysis.get('frontend_issues', []):
                issue['case_id'] = result.get('case_id', '')
                all_frontend_issues.append(issue)

            # 汇总后端问题
            for issue in analysis.get('backend_issues', []):
                issue['case_id'] = result.get('case_id', '')
                all_backend_issues.append(issue)

            # 汇总关键证据
            for evidence in analysis.get('key_evidence', []):
                all_key_evidence.append({
                    'case_id': result.get('case_id', ''),
                    'evidence': evidence
                })

            # 汇总优劣势
            all_strengths.extend(analysis.get('strengths', []))
            all_weaknesses.extend(analysis.get('weaknesses', []))

            # 汇总潜在问题
            for issue in analysis.get('potential_issues', []):
                issue['case_id'] = result.get('case_id', '')
                all_potential_issues.append(issue)

            # 收集结论
            if analysis.get('conclusion'):
                conclusions.append({
                    'case_id': result.get('case_id', ''),
                    'conclusion': analysis.get('conclusion')
                })

        # 去重
        all_strengths = list(dict.fromkeys(all_strengths))[:10]
        all_weaknesses = list(dict.fromkeys(all_weaknesses))[:10]

        return {
            'frontend_issues': all_frontend_issues,
            'backend_issues': all_backend_issues,
            'key_evidence': all_key_evidence,
            'strengths': all_strengths,
            'weaknesses': all_weaknesses,
            'potential_issues': all_potential_issues,
            'conclusions': conclusions
        }

    def _generate_excel_enhanced(self, report_data: Dict, excel_path: Path):
        """生成增强版 Excel 报告（10个工作表）"""
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:

            # 工作表1：概览
            code_stats = report_data.get('code_statistics', {})
            time_stats = report_data.get('test_time_statistics', {})
            summary = report_data.get('summary', {})
            risk = report_data.get('risk', {})

            overview_data = {
                '项目名称': [report_data.get('project_name')],
                '任务ID': [report_data.get('task_id')],
                '检测时间': [report_data.get('generated_at')],
                '代码总量（行）': [code_stats.get('total_lines')],
                '文件数量': [code_stats.get('total_files')],
                '源代码文件': [code_stats.get('source_files')],
                '项目类型': [code_stats.get('project_type')],
                '主要语言': [str(code_stats.get('main_languages', []))],
                '总执行时间（秒）': [time_stats.get('total_execution_time')],
                '平均执行时间（秒）': [time_stats.get('average_execution_time')],
                '用例总数': [summary.get('total')],
                '通过数': [summary.get('passed')],
                '失败数': [summary.get('failed')],
                '通过率': [summary.get('pass_rate')],
                '风险等级': [risk.get('level')],
                '风险分数': [risk.get('score')]
            }
            df_overview = pd.DataFrame(overview_data)
            df_overview.to_excel(writer, sheet_name='概览', index=False)

            # 工作表2：测试结果（增强）
            test_results = report_data.get('test_results', [])
            if test_results:
                rows = []
                for r in test_results:
                    rows.append({
                        '用例编号': r.get('case_id'),
                        '对应需求': r.get('requirement'),
                        '测试点': r.get('test_point'),
                        '优先级': r.get('priority'),
                        '测试结果': r.get('result'),
                        '执行时长(秒)': r.get('execution_time'),
                        '完成时间': r.get('test_time'),
                        '校验依据': r.get('evidence'),
                        '问题代码': r.get('problem_code'),
                        '分析结论': r.get('analysis', {}).get('conclusion', '')
                    })
                df_tests = pd.DataFrame(rows)
                df_tests.to_excel(writer, sheet_name='测试结果', index=False)

            # 工作表3：语言分布
            lang_dist = code_stats.get('language_distribution', {})
            if lang_dist:
                df_lang = pd.DataFrame([
                    {'语言': lang, '文件数': count}
                    for lang, count in sorted(lang_dist.items(), key=lambda x: x[1], reverse=True)
                ])
                df_lang.to_excel(writer, sheet_name='语言分布', index=False)

            # 工作表4：风险评估
            risk_data = {
                '风险等级': [risk.get('level')],
                '风险分数': [risk.get('score')],
                '评估摘要': [risk.get('summary')]
            }
            df_risk = pd.DataFrame(risk_data)
            df_risk.to_excel(writer, sheet_name='风险评估', index=False)

            # 工作表5：风险详情
            risk_items = risk.get('items', [])
            if risk_items:
                df_items = pd.DataFrame(risk_items)
                if 'type' in df_items.columns:
                    df_items = df_items.rename(columns={'type': '风险类型'})
                if 'location' in df_items.columns:
                    df_items = df_items.rename(columns={'location': '位置'})
                if 'description' in df_items.columns:
                    df_items = df_items.rename(columns={'description': '描述'})
                df_items.to_excel(writer, sheet_name='风险详情', index=False)

            # 工作表6：问题分类
            aggregated = report_data.get('aggregated_analysis', {})
            all_issues = []

            for issue in aggregated.get('frontend_issues', []):
                all_issues.append({
                    '分类': '前端问题',
                    '用例编号': issue.get('case_id', ''),
                    '问题描述': issue.get('issue', ''),
                    '位置': issue.get('location', ''),
                    '证据': issue.get('evidence', '')
                })

            for issue in aggregated.get('backend_issues', []):
                all_issues.append({
                    '分类': '后端问题',
                    '用例编号': issue.get('case_id', ''),
                    '问题描述': issue.get('issue', ''),
                    '位置': issue.get('location', ''),
                    '证据': issue.get('evidence', '')
                })

            if all_issues:
                df_issues = pd.DataFrame(all_issues)
                df_issues.to_excel(writer, sheet_name='问题分类', index=False)

            # 工作表7：关键证据
            evidence_list = aggregated.get('key_evidence', [])
            if evidence_list:
                df_evidence = pd.DataFrame([
                    {'用例编号': e.get('case_id'), '证据内容': e.get('evidence')}
                    for e in evidence_list
                ])
                df_evidence.to_excel(writer, sheet_name='关键证据', index=False)

            # 工作表8：优劣势分析
            sw_data = []
            for s in aggregated.get('strengths', []):
                sw_data.append({'类型': '优势', '内容': s})
            for w in aggregated.get('weaknesses', []):
                sw_data.append({'类型': '劣势', '内容': w})
            if sw_data:
                df_sw = pd.DataFrame(sw_data)
                df_sw.to_excel(writer, sheet_name='优劣势分析', index=False)

            # 工作表9：分析结论
            conclusions = aggregated.get('conclusions', [])
            if conclusions:
                df_conclusions = pd.DataFrame(conclusions)
                df_conclusions = df_conclusions.rename(columns={'case_id': '用例编号', 'conclusion': '分析结论'})
                df_conclusions.to_excel(writer, sheet_name='分析结论', index=False)

            # 工作表10：潜在问题
            potential_issues = aggregated.get('potential_issues', [])
            if potential_issues:
                df_potential = pd.DataFrame([
                    {
                        '用例编号': issue.get('case_id', ''),
                        '潜在问题': issue.get('issue', ''),
                        '可能性': issue.get('probability', ''),
                        '证据': issue.get('evidence', '')
                    }
                    for issue in potential_issues
                ])
                df_potential.to_excel(writer, sheet_name='潜在问题', index=False)

    def get_report(self, task_id: str) -> Dict:
        """获取已生成的报告"""
        json_path = self.report_dir / task_id / 'report.json'
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def list_reports(self, limit: int = 20) -> List[Dict]:
        """列出最近的报告"""
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
