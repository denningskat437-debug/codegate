"""
代码统计分析模块
统计代码总量、文件数量、语言分布、项目类型识别
"""
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter

logger = logging.getLogger(__name__)

LANGUAGE_EXTENSIONS = {
    '.py': 'Python',
    '.js': 'JavaScript',
    '.ts': 'TypeScript',
    '.jsx': 'JavaScript (React)',
    '.tsx': 'TypeScript (React)',
    '.java': 'Java',
    '.go': 'Go',
    '.rs': 'Rust',
    '.c': 'C',
    '.cpp': 'C++',
    '.h': 'C/C++ Header',
    '.cs': 'C#',
    '.php': 'PHP',
    '.rb': 'Ruby',
    '.swift': 'Swift',
    '.kt': 'Kotlin',
    '.vue': 'Vue',
    '.html': 'HTML',
    '.css': 'CSS',
    '.scss': 'SCSS',
    '.sql': 'SQL',
    '.sh': 'Shell',
    '.json': 'JSON',
    '.yaml': 'YAML',
    '.yml': 'YAML',
    '.xml': 'XML',
    '.md': 'Markdown',
}

PROJECT_TYPE_INDICATORS = {
    'frontend': ['package.json', 'index.html', 'vue.config.js', 'vite.config.js', 'src/App.jsx', 'src/App.tsx'],
    'backend': ['app.py', 'main.py', 'requirements.txt', 'go.mod', 'pom.xml', 'build.gradle'],
    'fullstack': ['package.json', 'app.py', 'requirements.txt'],
    'django': ['settings.py', 'urls.py', 'wsgi.py', 'asgi.py'],
    'flask': ['app.py', 'requirements.txt'],
    'spring': ['pom.xml', 'application.properties', 'application.yml'],
    'nodejs': ['package.json', 'server.js', 'index.js'],
    'react': ['package.json', 'src/App.jsx', 'src/App.tsx', 'public/index.html'],
    'vue': ['package.json', 'src/main.js', 'vue.config.js', 'vite.config.js'],
}

IGNORE_DIRS = {'node_modules', 'venv', '.venv', '__pycache__', '.git', 'dist', 'build', '.idea', '.vscode', 'target', 'bin', 'obj'}
IGNORE_FILES = {'.gitignore', '.env', 'package-lock.json', 'yarn.lock', 'Pipfile.lock', '.DS_Store'}

SOURCE_CODE_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.c', '.cpp', '.php', '.rb', '.vue', '.html', '.css', '.scss', '.sql', '.sh', '.kt', '.swift', '.rs', '.cs'}


class CodeAnalyzer:
    """代码统计分析器"""

    def __init__(self, code_path: str):
        """
        初始化代码分析器

        Args:
            code_path: 代码目录路径
        """
        self.code_path = Path(code_path)
        self._stats_cache: Optional[Dict] = None

    def analyze(self) -> Dict:
        """
        执行代码统计分析

        Returns:
            {
                'total_lines': int,
                'total_files': int,
                'source_files': int,
                'language_distribution': Dict[str, int],
                'project_type': str,
                'project_indicators_found': List[str],
                'top_files': List[Dict]
            }
        """
        if self._stats_cache is not None:
            return self._stats_cache

        stats = {
            'total_lines': 0,
            'total_files': 0,
            'source_files': 0,
            'language_distribution': Counter(),
            'project_type': 'unknown',
            'project_indicators_found': [],
            'top_files': []
        }

        for root, dirs, files in os.walk(self.code_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for file in files:
                if file in IGNORE_FILES:
                    continue

                file_path = Path(root) / file
                ext = file_path.suffix.lower()

                stats['total_files'] += 1

                if ext in LANGUAGE_EXTENSIONS:
                    stats['language_distribution'][LANGUAGE_EXTENSIONS[ext]] += 1

                if ext in SOURCE_CODE_EXTENSIONS:
                    stats['source_files'] += 1
                    try:
                        lines = self._count_lines(file_path)
                        stats['total_lines'] += lines
                        stats['top_files'].append({
                            'path': str(file_path.relative_to(self.code_path)),
                            'language': LANGUAGE_EXTENSIONS.get(ext, 'Unknown'),
                            'lines': lines
                        })
                    except Exception as e:
                        logger.warning(f"无法读取文件 {file_path}: {e}")

        stats['project_type'] = self._identify_project_type()
        stats['project_indicators_found'] = self._get_found_indicators()
        stats['language_distribution'] = dict(stats['language_distribution'])
        stats['top_files'] = sorted(stats['top_files'], key=lambda x: x['lines'], reverse=True)[:20]
        stats['main_languages'] = list(stats['language_distribution'].keys())[:5]

        self._stats_cache = stats
        logger.info(f"代码统计完成: {stats['total_lines']} 行, {stats['total_files']} 文件, 类型={stats['project_type']}")
        return stats

    def _count_lines(self, file_path: Path) -> int:
        """统计文件行数"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except:
            return 0

    def _identify_project_type(self) -> str:
        """识别项目类型"""
        found_types = []

        for type_name, indicators in PROJECT_TYPE_INDICATORS.items():
            matches = sum(1 for ind in indicators if (self.code_path / ind).exists())
            if matches > 0:
                found_types.append((type_name, matches))

        if found_types:
            found_types.sort(key=lambda x: x[1], reverse=True)
            return found_types[0][0]

        return 'unknown'

    def _get_found_indicators(self) -> List[str]:
        """获取找到的项目类型指示文件"""
        found = []
        for type_name, indicators in PROJECT_TYPE_INDICATORS.items():
            for ind in indicators:
                if (self.code_path / ind).exists() and ind not in found:
                    found.append(ind)
        return found

    def analyze_project_match(self, claimed_type: str = None) -> Dict:
        """
        分析项目类型匹配

        Args:
            claimed_type: 声称的项目类型（来自测试用例或请求参数）

        Returns:
            {
                'actual_type': str,
                'claimed_type': str,
                'match_score': float,
                'match_analysis': str,
                'recommendations': List[str]
            }
        """
        stats = self.analyze()
        actual_type = stats['project_type']

        if not claimed_type:
            return {
                'actual_type': actual_type,
                'claimed_type': '未指定',
                'match_score': 0.0,
                'match_analysis': f"项目实际类型为 {actual_type}，未提供预期类型描述",
                'recommendations': ['建议在测试用例或请求参数中明确项目类型']
            }

        match_score = self._calculate_type_match(actual_type, claimed_type)

        if match_score >= 0.8:
            analysis = f"项目类型匹配良好，实际为 {actual_type}，描述为 {claimed_type}"
            recommendations = []
        elif match_score >= 0.5:
            analysis = f"项目类型部分匹配，实际为 {actual_type}，描述为 {claimed_type}，可能存在定位偏差"
            recommendations = ['建议核实项目定位，确保测试用例与实际代码类型一致']
        else:
            analysis = f"项目类型不匹配，实际为 {actual_type}，描述为 {claimed_type}，测试用例可能不适用"
            recommendations = ['项目类型与描述不符，请重新评估测试用例适用性', '建议调整测试用例以匹配实际项目类型']

        return {
            'actual_type': actual_type,
            'claimed_type': claimed_type,
            'match_score': match_score,
            'match_analysis': analysis,
            'recommendations': recommendations
        }

    def _calculate_type_match(self, actual: str, claimed: str) -> float:
        """计算类型匹配分数"""
        type_similarity = {
            ('frontend', 'frontend'): 1.0,
            ('backend', 'backend'): 1.0,
            ('fullstack', 'frontend'): 0.7,
            ('fullstack', 'backend'): 0.7,
            ('django', 'backend'): 0.9,
            ('flask', 'backend'): 0.9,
            ('spring', 'backend'): 0.9,
            ('nodejs', 'backend'): 0.8,
            ('react', 'frontend'): 0.9,
            ('vue', 'frontend'): 0.9,
        }

        actual_lower = actual.lower()
        claimed_lower = claimed.lower()

        if actual_lower == claimed_lower:
            return 1.0

        for (a, c), score in type_similarity.items():
            if (actual_lower == a and claimed_lower == c) or (actual_lower == c and claimed_lower == a):
                return score

        if actual_lower in claimed_lower or claimed_lower in actual_lower:
            return 0.6

        return 0.0

    def reload(self) -> None:
        """重新加载统计缓存"""
        self._stats_cache = None
        logger.info("代码统计缓存已清除")