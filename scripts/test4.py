# -*- coding:utf-8 -*-
from tis_toscore import TIS


def get_username_password():
    # 正式使用时取消注释以下两行
    username = input("请输入你的学号: ")
    password = input("请输入你的密码: ")
    
    return username, password


def main():
    print("=" * 50)
    print("TIS 成绩获取工具")
    print("=" * 50)
    
    sid, pwd = get_username_password()
    tis_session = TIS(sid, pwd)
    
    try:
        # 1. 登录
        tis_session.login()
        
        # 2. 导出成绩（会自动保存 Excel、JSON 和更新 config.json）
        output_file = tis_session.export_gradebook()
        
        print("\n" + "=" * 50)
        print("完成！生成的文件：")
        print("  - gradebook.xlsx  (Excel 格式)")
        print("  - gradebook.json  (JSON 格式)")
        print("  - config.json    (课程信息已更新)")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n[-] 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        tis_session.close()


if __name__ == '__main__':
    main()
