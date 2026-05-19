#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
file_helper 测试脚本
"""
import sys
sys.path.insert(0, '.')

from file_helper import FileHelper

def test_parse():
    helper = FileHelper()
    helper.set_workspace("d:/test_folder")
    
    test_commands = [
        "找所有pdf",
        "dry 把大于100MB的视频移到归档",
        "dry 整理downloads文件夹",
        "dry 清理临时文件",
        "dry 删除30天前的日志",
    ]
    
    print("=" * 50)
    print("file_helper 功能测试")
    print("=" * 50)
    print(f"工作目录: {helper.workspace}")
    print()
    
    for cmd in test_commands:
        print("-" * 50)
        print(f"命令: {cmd}")
        
        # 去掉 dry 前缀，只解析
        if cmd.startswith("dry "):
            cmd = cmd[4:]
        
        result = helper.parse(cmd)
        print(f"解析结果:")
        print(f"  动作: {result.get('action', '未知')}")
        print(f"  目标: {result.get('target', '-')}")
        
        filters = result.get('filters', [])
        if filters:
            print(f"  过滤条件:")
            for f in filters:
                print(f"    - {f['type']}: {f}")
        
        params = result.get('params', {})
        if params:
            print(f"  参数: {params}")
        
        print()

if __name__ == "__main__":
    test_parse()
