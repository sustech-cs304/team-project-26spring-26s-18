import os
import sys
from pathlib import Path
import json

# 动态调整 Python 搜索路径，以便能找到 scripts 目录下的模块
sys.path.append(str(Path(__file__).parent))

from tis_agent import SUSTechTIS

def run_tis_course_fetch_test():
    """
    测试 SUSTechTIS 课程信息获取功能，并验证 config.json 的更新。
    """
    print("--- 正在测试 SUSTechTIS 课程信息获取功能 ---")

    # 提示用户输入凭据
    username = input("请输入您的学号进行测试: ")
    password = input("请输入您的CAS密码进行测试 (输入时密码不显示): ")


    tis_agent = SUSTechTIS()
    if tis_agent.login(username, password):
        print("[+] 登录成功，开始获取课程信息...")
        course_info = tis_agent.fetch_grades()

        if course_info:
            print(f"[+] 成功获取到 {len(course_info)} 门课程信息。")
            
            # 验证 config.json 是否被更新
            config_path = Path(__file__).parent / "config.json"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    student_info = json.load(f)
                
                if "courses" in student_info and student_info["courses"] == course_info:
                    print("[+] config.json 中的课程信息已成功更新。")
                else:
                    print("[x] config.json 中的课程信息未按预期更新，请检查。")
            else:
                print("[x] config.json 文件未找到，课程信息可能未保存。")
        else:
            print("[x] 未能获取课程信息。")
    else:
        print("[x] 登录失败，无法进行课程信息获取测试。")

if __name__ == "__main__":
    run_tis_course_fetch_test()