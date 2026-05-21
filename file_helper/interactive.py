#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
file_helper 交互式命令行

在终端输入自然语言命令，实时查看解析和执行结果。
使用百炼大模型（qwen-turbo）理解自然语言，自动识别文件操作意图。

确认逻辑统一在 file_helper.py 的 run() 中处理，
interactive.py 只负责 I/O（输入、打印解析、打印执行结果）。
"""
import os
import sys

# 设置 UTF-8 输出
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from file_helper import FileHelper


def print_header():
    print("=" * 60)
    print("  [FileHelper] 自然语言文件管理器")
    print("=" * 60)
    print("  输入命令自动解析执行，输入 help 查看帮助")
    print("  输入 exit 或 quit 退出")
    print("=" * 60)
    print()


def print_help():
    print("""
可用命令示例：
  移动/复制/删除：
    - 把大于100MB的视频移到 d:/backup
    - 复制所有pdf到 d:/docs
    - 删除所有tmp文件

  按类型整理：
    - 整理downloads文件夹
    - 按类型分类这个目录

  搜索过滤：
    - 找所有pdf
    - 查找大于100MB的视频

  其他：
    - 分析这个文件夹
    - 清理临时文件
    - 删除空文件夹

特殊命令：
    set workspace <路径>  - 设置工作目录
    show config           - 显示当前配置
    dry <命令>           - 只解析不执行
    help / h             - 显示此帮助
    exit / quit          - 退出
""")


def format_intent(intent):
    """格式化解析结果（支持单动作和多动作）"""
    lines = []
    lines.append("  [AI解析]")

    # 多动作格式
    if "actions" in intent and intent["actions"]:
        lines.append(f"  动作数: {len(intent['actions'])} 个动作")
        for idx, act in enumerate(intent["actions"]):
            lines.append(f"  [{idx + 1}] {act.get('action', '未知')}")
            if act.get('source'):
                lines.append(f"      来源: {act.get('source')}")
            if act.get('target'):
                lines.append(f"      目标: {act.get('target')}")
            if act.get('filters'):
                lines.append(f"      过滤: {act.get('filters')}")
        if intent.get('summary'):
            lines.append(f"  理解: {intent['summary']}")
        return "\n".join(lines)

    # 单动作格式（兼容）
    lines.append(f"  动作: {intent.get('action', '未知')}")
    lines.append(f"  来源: {intent.get('source', '当前目录')}")
    lines.append(f"  目标: {intent.get('target', '-')}")

    if intent.get('summary'):
        lines.append(f"  理解: {intent['summary']}")

    filters = intent.get('filters', [])
    if filters:
        lines.append(f"  过滤条件:")
        for f in filters:
            ftype = f['type']
            display = {k: v for k, v in f.items() if k != 'type' and v not in ('', [], None)}
            lines.append(f"    - {ftype}: {display}")

    params = intent.get('params', {})
    if params:
        lines.append(f"  参数: {params}")

    return "\n".join(lines)


def main():
    print_header()

    # 创建助手实例
    helper = FileHelper()

    # 启动时让用户指定工作目录
    default_workspace = r"D:\file_helper_demo"
    if not os.path.isdir(default_workspace):
        default_workspace = os.getcwd()
    print(f"请输入工作目录（直接回车使用默认目录: {default_workspace}）：", end="")
    user_input_path = input().strip()

    if user_input_path:
        if os.path.isdir(user_input_path):
            workspace = user_input_path
        else:
            print(f"[警告] 目录不存在: {user_input_path}，使用当前目录")
            workspace = default_workspace
    else:
        workspace = default_workspace

    helper.set_workspace(workspace)
    print(f"[目录] 工作目录: {workspace}\n")

    print(f"AI引擎: 百炼 qwen-turbo（网络调用，约2-3秒/次）\n")

    while True:
        try:
            user_input = input(f"[{helper.workspace}]\n>>> ").strip()

            if not user_input:
                continue

            # 退出命令
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("再见!")
                break

            # 帮助命令
            if user_input.lower() in ['help', 'h', '?']:
                print_help()
                continue

            # 显示配置
            if user_input.lower() == 'show config':
                print(f"\n[配置]")
                print(f"   工作目录: {helper.workspace}")
                print(f"   AI引擎: 百炼 qwen-turbo")
                continue

            # 设置命令
            if user_input.lower().startswith('set workspace '):
                new_path = user_input[14:].strip()
                if os.path.exists(new_path):
                    helper.set_workspace(new_path)
                    print(f"[OK] 工作目录已设置为: {new_path}")
                else:
                    print(f"[ERROR] 目录不存在: {new_path}")
                continue

            # 解析命令
            print("-" * 40)
            print("[解析]")
            print("-" * 40)

            print("  正在解析...", end="", flush=True)
            intent = helper.parse(user_input)
            print("\r" + " " * 20 + "\r", end="", flush=True)  # 清除提示行

            if intent:
                print(format_intent(intent))
            else:
                print("  [警告] 无法理解此命令")
                continue

            # 干跑模式
            if user_input.lower().startswith('dry '):
                print("\n[干跑模式] 未执行\n")
                continue

            # 执行
            print("\n" + "-" * 40)
            print("[执行]")
            print("-" * 40)
            result = helper.run(user_input, verbose=True)

            # search 操作：输出匹配的文件名
            if intent.get("action") == "search":
                found = result.success
                if found:
                    print(f"\n找到 {len(found)} 个文件：")
                    for item in found:
                        path = item["path"] if isinstance(item, dict) else item
                        print(f"  - {os.path.basename(path)}")
                else:
                    print("\n没有找到匹配的文件")

            print(f"\n[完成]")

        except KeyboardInterrupt:
            print("\n\n再见!")
            break
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
