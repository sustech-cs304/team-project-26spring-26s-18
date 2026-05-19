"""
对比测试：规则解析 vs 纯AI解析

测试文件位于: d:/file_helper_demo
运行方式:
    python test_comparison.py

输出两列对比结果，直观看到两种方案的差异。
"""

import sys
import time
sys.path.insert(0, ".")

from file_helper.intent_parser import IntentParser as RuleParser
from file_helper.ai_only_parser import AIOnlyParser

# 测试用例
TEST_CASES = [
    "把大于100MB的视频移到归档",
    "找到所有的TXT文件",
    "找出所有pdf文件",
    "找所有文档",
    "把上周改过的、带报告二字的文档挪到归档",
    "用AI理解：把上周改过的、文件名里有报告的文档挪到归档",
    "删除所有大于50MB的mp4文件",
    "列出所有py文件",
    "把小于10KB的txt文件复制到d:/backup",
    "整理一下这周用过的文档",
    "找出今天修改过的文件",
    "清理重复的图片",
    "分析一下这个文件夹的文件类型分布",
]

def format_filters(filters):
    if not filters:
        return "无"
    parts = []
    for f in filters:
        t = f.get("type", "?")
        v = f.get("value", "?")
        parts.append(f"{t}={v}")
    return ", ".join(parts)

def main():
    rule_parser = RuleParser()
    ai_parser = AIOnlyParser()

    print("=" * 90)
    print(f"{'测试输入':<45} | {'规则解析':<20} | {'AI解析'}")
    print(f"{'':<45} | {'action | filters':<20} | {'action | filters'}")
    print("-" * 90)

    for text in TEST_CASES:
        # 规则解析
        start = time.time()
        rule_result = rule_parser.parse(text)
        rule_time = time.time() - start

        # AI解析
        start = time.time()
        ai_result = ai_parser.parse(text)
        ai_time = time.time() - start

        rule_action = rule_result.get("action") or "?"
        rule_filters = format_filters(rule_result.get("filters"))
        rule_summary = f"{rule_action} | {rule_filters[:18]}"

        ai_action = ai_result.get("action") or "?"
        ai_summary_str = ai_result.get("summary", "")
        ai_filters = format_filters(ai_result.get("filters"))
        ai_display = f"{ai_action} | {ai_filters[:18]}"

        # 标记是否有差异
        diff = " " if rule_action == ai_action else "*"

        print(f"{text:<45} {diff}| {rule_summary:<20} | {ai_display}")
        print(f"{'':>45}  | {f'({rule_time:.2f}s)':>20} | {f'({ai_time:.2f}s)'}")
        print()

    print("=" * 90)
    print("说明: * 表示两种方案 action 结果不同")
    print("规则解析: ~0.001s（本地，无网络延迟）")
    print("AI解析: ~1-3s（依赖网络和API响应）")

if __name__ == "__main__":
    main()
