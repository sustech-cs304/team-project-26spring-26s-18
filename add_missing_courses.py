import json

f = open('file_helper/user_config.json', encoding='utf-8')
data = json.load(f)
f.close()

existing_codes = {c['code'] for c in data['courses']}

missing = [
    {"code": "CS201", "name": "离散数学"},
    {"code": "CS303", "name": "操作系统"},
    {"code": "CS304", "name": "软件工程"},
    {"code": "CS305", "name": "编译原理"},
    {"code": "CS306", "name": "计算机体系结构"},
    {"code": "CS401", "name": "人工智能"},
    {"code": "CS402", "name": "机器学习"},
    {"code": "MATH205", "name": "数值分析"},
    {"code": "EE101", "name": "电路基础"},
    {"code": "PHYS101", "name": "大学物理"},
]

added = []
for c in missing:
    if c['code'] not in existing_codes:
        data['courses'].append(c)
        added.append(f"{c['code']} - {c['name']}")

f = open('file_helper/user_config.json', 'w', encoding='utf-8')
json.dump(data, f, ensure_ascii=False, indent=2)
f.close()

print(f"新增 {len(added)} 门课程:")
for a in added:
    print(" ", a)
