#!/usr/bin/env python3
"""
项目指标计算脚本
计算：代码行数、源文件数量、圈复杂度、依赖项数量
"""

import os
import fnmatch
import json
from pathlib import Path

def count_lines_of_code(files):
    """计算有效代码行数，排除空行和常见单行注释"""
    total_lines = 0

    for file_path in files:
        try:
            suffix = Path(file_path).suffix

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    stripped = line.strip()

                    if not stripped:
                        continue

                    if suffix == '.py' and stripped.startswith('#'):
                        continue

                    if suffix in ['.js', '.vue'] and stripped.startswith('//'):
                        continue

                    if suffix in ['.js', '.vue'] and stripped.startswith('/*'):
                        continue

                    if suffix in ['.js', '.vue'] and stripped.startswith('*'):
                        continue

                    if suffix in ['.js', '.vue'] and stripped.startswith('*/'):
                        continue

                    total_lines += 1

        except Exception as e:
            print(f"  跳过文件 {file_path}: {e}")

    return total_lines

def count_source_files(files):
    """计算源文件数量"""
    return len(files)

def calculate_cyclomatic_complexity(python_files):
    """计算圈复杂度（使用 radon 库）

    只统计：
    1. 总圈复杂度
    2. 平均每个函数/方法的圈复杂度
    """
    try:
        from radon.complexity import cc_visit

        total_complexity = 0
        function_count = 0
        files_analyzed = 0

        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    source = f.read()

                result = cc_visit(source)
                files_analyzed += 1

                for obj in result:
                    total_complexity += obj.complexity
                    function_count += 1

            except Exception as e:
                print(f"  跳过文件 {file_path}: {e}")

        if function_count > 0:
            avg_complexity = total_complexity / function_count
        else:
            avg_complexity = 0

        return {
            'total': total_complexity,
            'average_per_function': round(avg_complexity, 2),
            'functions_analyzed': function_count,
            'files_analyzed': files_analyzed
        }

    except ImportError:
        print("  警告: radon 库未安装，无法计算精确圈复杂度")
        return {
            'total': 0,
            'average_per_function': 0,
            'functions_analyzed': 0,
            'files_analyzed': 0,
            'note': '未安装 radon，请运行: pip install radon'
        }

def count_dependencies(requirements_path, package_json_path):
    """计算依赖项数量"""
    deps = {
        'python': 0,
        'python_dev': 0,
        'npm': 0,
        'npm_dev': 0
    }
    
    # Python 依赖
    if requirements_path.exists():
        with open(requirements_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    deps['python'] += 1
    
    # npm 依赖
    if package_json_path.exists():
        with open(package_json_path, 'r') as f:
            pkg = json.load(f)
            deps['npm'] = len(pkg.get('dependencies', {}))
            deps['npm_dev'] = len(pkg.get('devDependencies', {}))
    
    return deps

def get_source_files(root_dir):
    """获取所有源文件（排除废弃文件）"""
    exclude_dirs = ['scripts废案', 'file_helper已弃用', '__pycache__', '.git', 'node_modules', 'dist', '.venv']
    exclude_patterns = ['*.pyc', '*.pyo', '.DS_Store']
    
    files = {
        'python': [],
        'javascript': [],
        'vue': []
    }
    
    for path in Path(root_dir).rglob('*'):
        # 检查是否在排除目录中
        if any(excl in str(path.parent) for excl in exclude_dirs):
            continue
        
        # 检查文件模式
        if any(fnmatch.fnmatch(path.name, pattern) for pattern in exclude_patterns):
            continue
        
        # 分类文件
        if path.is_file():
            if path.suffix == '.py':
                files['python'].append(str(path))
            elif path.suffix == '.js':
                files['javascript'].append(str(path))
            elif path.suffix == '.vue':
                files['vue'].append(str(path))
    
    return files

def main():
    root_dir = Path(__file__).parent
    
    print("=" * 60)
    print("          项目指标计算工具")
    print("=" * 60)
    
    # 获取源文件
    print("\n[1/4] 收集源文件...")
    source_files = get_source_files(root_dir)
    
    # 计算源文件数量
    print("\n[2/4] 计算源文件数量...")
    total_files = sum(len(files) for files in source_files.values())
    print(f"  Python 文件: {len(source_files['python'])}")
    print(f"  JavaScript 文件: {len(source_files['javascript'])}")
    print(f"  Vue 文件: {len(source_files['vue'])}")
    print(f"  总计: {total_files}")
    
    # 计算代码行数
    print("\n[3/4] 计算代码行数...")
    all_files = []
    for files in source_files.values():
        all_files.extend(files)
    loc = count_lines_of_code(all_files)
    print(f"  总代码行数: {loc:,}")
    
    # 计算圈复杂度
    print("\n[4/4] 计算圈复杂度...")
    complexity = calculate_cyclomatic_complexity(source_files['python'])
    print(f"  总圈复杂度: {complexity['total']}")
    print(f"  平均圈复杂度: {complexity['average_per_function']}")
    print(f"  分析文件数: {complexity['files_analyzed']}")
    if 'note' in complexity:
        print(f"  备注: {complexity['note']}")
    
    # 计算依赖项数量
    print("\n[5/4] 计算依赖项数量...")
    deps = count_dependencies(
        root_dir / 'python_demo' / 'requirements.txt',
        root_dir / 'vue' / 'package.json'
    )
    print(f"  Python 依赖: {deps['python']}")
    print(f"  npm 依赖: {deps['npm']}")
    print(f"  npm 开发依赖: {deps['npm_dev']}")
    print(f"  总计: {deps['python'] + deps['npm'] + deps['npm_dev']}")
    
    # 输出汇总
    print("\n" + "=" * 60)
    print("                    指标汇总")
    print("=" * 60)
    print(f"  代码行数 (Lines of Code): {loc:,}")
    print(f"  源文件数量 (Source Files): {total_files}")
    print(f"  圈复杂度 (Cyclomatic Complexity): {complexity['total']} (平均: {complexity['average_per_function']})")
    print(f"  依赖项数量 (Dependencies): {deps['python'] + deps['npm'] + deps['npm_dev']}")
    print("=" * 60)
    
    # 生成报告内容
    report_content = f"""### 1. 指标 (2 分)

| 指标 | 值 |
|------|-----|
| **代码行数** | {loc:,} |
| **源文件数量** | {total_files} |
| **圈复杂度** | {complexity['total']} (平均: {complexity['average_per_function']}) |
| **依赖项数量** | {deps['python'] + deps['npm'] + deps['npm_dev']} |

**详细说明：**
- Python 文件: {len(source_files['python'])} 个
- JavaScript 文件: {len(source_files['javascript'])} 个  
- Vue 文件: {len(source_files['vue'])} 个
- Python 依赖: {deps['python']} 个
- npm 运行时依赖: {deps['npm']} 个
- npm 开发依赖: {deps['npm_dev']} 个
"""
    
    print("\n以下内容可直接复制到 TEAM_REPORT.md 的 1. 指标 部分：")
    print("-" * 60)
    print(report_content)
    print("-" * 60)

if __name__ == '__main__':
    main()