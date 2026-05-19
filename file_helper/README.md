# File Helper - 文件管理助手

一个基于自然语言的文件管理工具包，采用**原子化函数 + 灵活组合**的设计理念。

## 设计思想

不写大而全的函数，而是写很多最小粒度的原子函数，通过意图解析动态组合它们来完成任意复杂任务。

## 目录结构

```
file_helper/
├── __init__.py           # 包入口
├── file_atomic_ops.py    # 基础原子操作（最底层）
├── file_query.py         # 查询过滤原子函数
├── file_batch_ops.py     # 批量操作封装
├── intent_parser.py      # 自然语言意图解析器
├── file_helper.py        # 主入口（整合所有模块）
├── plan.md               # 设计文档
└── README.md             # 本文件
```

## 快速开始

### 方式一：使用自然语言

```python
from file_helper import FileHelper, run_command

# 方法1：全局函数
run_command("把大于100MB的视频移到归档")
run_command("删除所有临时文件")
run_command("按月份整理图片")

# 方法2：实例方法
helper = FileHelper("C:/Users/Downloads")
helper.run("把pdf文件复制到文档")
```

### 方式二：使用 Python API

```python
from file_helper import FileHelper

helper = FileHelper()

# 列出文件
files = helper.list_files(recursive=True)

# 搜索文件
pdfs = helper.find(ext="pdf")
docs = helper.find(name="报告")

# 移动/复制/删除
helper.move(files, "D:/Backup")
helper.copy(pdfs, "D:/Documents")
helper.delete(temp_files)

# 分类整理
helper.organize_by_type()
helper.organize_by_date(mode="month")
helper.organize_by_size()

# 清理
helper.clean_temp()
helper.clean_empty()

# 分析
stats = helper.analyze()
print(stats)
```

## 模块说明

### 1. file_atomic_ops.py - 基础原子操作

最小粒度的单一操作，每个函数只做一件事：

```python
from file_helper import get_files, move_file, delete_file, get_file_size

# 获取文件列表
files = get_files("C:/Downloads")

# 移动单个文件
move_file("a.txt", "B/")

# 删除文件（到回收站）
delete_file("b.txt", to_trash=True)

# 获取文件大小
size = get_file_size("c.txt")
```

### 2. file_query.py - 查询过滤

用于查询和过滤文件集合：

```python
from file_helper import filter_by_extension, filter_by_size, filter_by_date

# 按扩展名过滤
pdfs = filter_by_extension(files, ["pdf", "PDF"])

# 按大小过滤（大于100MB）
large_files = filter_by_size(files, min_mb=100)

# 按日期过滤（最近7天）
recent = filter_by_date(files, days_ago=7)

# 分组
groups = group_by_extension(files)
```

### 3. file_batch_ops.py - 批量操作

基于原子操作的批量封装：

```python
from file_helper import batch_move, batch_copy, batch_delete, organize_by_type

# 批量移动
result = batch_move(files, "D:/Archive")

# 批量删除
result = batch_delete(files, to_trash=True)

# 按类型分类整理
result = organize_by_type(files, "整理后的目录")
```

### 4. intent_parser.py - 意图解析

将自然语言解析为结构化操作：

```python
from file_helper import parse_command, plan_execution

# 解析命令
plan = parse_command("把大于100MB的视频移到归档")

# 生成执行计划
steps = plan_execution("删除所有临时文件")
```

### 5. file_helper.py - 主入口

整合所有模块，对外提供统一接口：

```python
from file_helper import FileHelper

helper = FileHelper("工作目录")

# 自然语言命令
helper.run("把pdf文件移到文档")
helper.run("删除30天前的日志")

# 直接API
files = helper.list_files()
stats = helper.analyze()
```

## 常用命令示例

| 命令 | 说明 |
|------|------|
| `run_command("把pdf文件移到文档")` | 移动PDF文件 |
| `run_command("删除所有临时文件")` | 删除临时文件 |
| `run_command("按月份整理图片")` | 按月份分类图片 |
| `run_command("把大于100MB的视频移到归档")` | 移动大视频文件 |
| `run_command("清理空文件夹")` | 删除空目录 |
| `run_command("找一下所有doc文件")` | 搜索Word文档 |

## 扩展名映射

| 类型 | 扩展名 |
|------|--------|
| 图片 | jpg, jpeg, png, gif, bmp, webp, svg |
| 视频 | mp4, avi, mkv, mov, wmv, flv |
| 音频 | mp3, wav, flac, aac, ogg |
| 文档 | pdf, doc, docx, xls, xlsx, ppt, pptx, txt |
| 代码 | py, js, java, cpp, c, h, cs, go, rs |
| 压缩 | zip, rar, 7z, tar, gz |

## 注意事项

1. 删除操作默认移动到回收站，不会永久删除
2. 批量操作会返回 BatchResult 对象，包含成功/失败/跳过的详情
3. 使用前请确保有足够的权限访问目标路径
