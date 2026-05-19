# -*- coding: utf-8 -*-
import os, shutil

test_dir = 'D:/file_helper_demo/11'
os.chdir('d:/team-project-26spring-26s-18')

# 把所有文件从子目录回收回根目录
print('=== 恢复测试文件到根目录 ===')
restored = 0
for root, dirs, files in os.walk(test_dir):
    for f in files:
        src = os.path.join(root, f)
        dst = os.path.join(test_dir, f)
        if src != dst and not root.startswith(test_dir + os.sep + '.'):
            shutil.copy2(src, dst)
            print('  restored:', f)
            restored += 1
print('Restored %d files' % restored)

# 删除子目录（保留 .ipynb_checkpoints）
for item in os.listdir(test_dir):
    path = os.path.join(test_dir, item)
    if os.path.isdir(path) and not item.startswith('.'):
        shutil.rmtree(path)
        print('  removed dir:', item)

print()
print('=== 根目录文件列表 ===')
for f in sorted(os.listdir(test_dir)):
    print(' ', f)

print()
print('=== 执行按课程分类 ===')
from file_helper import FileHelper
helper = FileHelper(workspace=test_dir)
result = helper.run('把所有文件按课程归类')
print('Result: ok=%d fail=%d' % (len(result.success), len(result.failed)))

print()
print('=== 最终目录结构 ===')
for root, dirs, files in os.walk(test_dir):
    level = root.replace(test_dir, '').count(os.sep)
    indent = '  ' * level
    rel = root.replace(test_dir, '').lstrip(os.sep)
    if rel:
        print(indent + rel + '/')
    for f in sorted(files):
        print(indent + '  ' + f)
