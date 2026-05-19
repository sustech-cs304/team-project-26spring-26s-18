#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 intent_parser 的解析能力
"""
import sys
sys.path.insert(0, ".")

from file_helper import FileHelper

helper = FileHelper(".")

test_cases = [
    # 搜索/查询类
    "找所有pdf文件",
    "搜索包含报告的文档",
    "找出大于100MB的视频",
    "列出所有图片",

    # 移动/复制类
    "把大于100MB的视频移到归档",
    "复制所有pdf到d:/docs",
    "把图片移到桌面",

    # 重命名类
    "给所有文件加上日期前缀",
    "把文件名中的空格换成下划线",
    "按顺序给文件编号",

    # 分类整理类
    "按类型整理这个文件夹",
    "按月份整理照片",
    "按大小分类文件",

    # 清理类
    "清理临时文件",
    "删除30天前的日志",
    "清理空文件夹",
    "删除所有tmp文件",
]

print("=" * 60)
print("  FileHelper 意图解析测试")
print("=" * 60)

for i, cmd in enumerate(test_cases, 1):
    print(f"\n[测试 {i}] 输入: {cmd}")
    try:
        intent = helper.parse(cmd)
        action = intent.get("action", "unknown")
        filters = intent.get("filters", [])
        target = intent.get("target", "-")
        params = intent.get("params", {})

        print(f"  → 动作: {action}")
        if target != "-":
            print(f"  → 目标: {target}")
        if filters:
            print(f"  → 过滤条件: {[f['type'] for f in filters]}")
        if params:
            print(f"  → 参数: {params}")
        print("  [OK] 解析成功")
    except Exception as e:
        print(f"  [FAIL] 解析失败: {e}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
