# File Helper - 文件管理助手设计文档

## 设计理念

**原子化函数 + 灵活组合**：不写大而全的函数，而是写很多最小粒度的原子函数，通过意图解析动态组合它们来完成任意复杂任务。

---

## 一、用户需求分类

### 1. 文件分类与整理
- "把这个文件夹里的文件按类型分类"
- "帮我把下载文件夹整理一下"
- "把所有的图片移到Photos文件夹"
- "按日期整理这些文件"
- "把大于100MB的文件单独放一个文件夹"

### 2. 文件重命名
- "把这些文件批量重命名"
- "给所有文件加上日期前缀"
- "把文件名中的空格换成下划线"
- "按顺序给文件编号"

### 3. 文件删除与清理
- "删除所有的临时文件"
- "清理重复文件"
- "删除30天前的日志文件"
- "清空回收站"
- "删除空文件夹"

### 4. 文件搜索与定位
- "帮我找到所有PDF文件"
- "搜索包含'报告'关键词的文件"
- "找出最近修改的文件"
- "哪些文件占空间最大？"

### 5. 文件移动与复制
- "把这些文档备份到D盘"
- "把所有视频文件复制到移动硬盘"
- "同步两个文件夹"

### 6. 文件分析与统计
- "这个文件夹占多少空间？"
- "各种文件类型占比如何？"
- "帮我分析磁盘使用情况"

### 7. 高级功能
- "监控下载文件夹，有新文件自动分类"
- "定期清理临时文件"

---

## 二、原子函数库设计

### 2.1 基础操作层 (file_atomic_ops.py)
最小粒度的单一操作，每个函数只做一件事。

```python
# ===== 文件系统基础操作 =====
def get_files(path, recursive=False) -> list:
    """获取目录下所有文件"""

def get_file_info(path) -> dict:
    """获取单个文件信息（大小、创建时间、修改时间、类型等）"""

def exists(path) -> bool:
    """检查路径是否存在"""

def is_file(path) -> bool:
    """检查是否为文件"""

def is_dir(path) -> bool:
    """检查是否为目录"""

# ===== 单文件操作 =====
def move_file(src, dst) -> bool:
    """移动单个文件"""

def copy_file(src, dst) -> bool:
    """复制单个文件"""

def delete_file(path, to_trash=True) -> bool:
    """删除单个文件（可选择移至回收站）"""

def rename_file(path, new_name) -> bool:
    """重命名文件"""

def create_file(path, content="") -> bool:
    """创建文件"""

def read_file(path) -> str:
    """读取文件内容"""

def write_file(path, content) -> bool:
    """写入文件内容"""

# ===== 目录操作 =====
def create_dir(path) -> bool:
    """创建目录"""

def delete_dir(path, recursive=False) -> bool:
    """删除目录"""

def get_dirs(path, recursive=False) -> list:
    """获取目录下所有子目录"""

def is_empty_dir(path) -> bool:
    """检查目录是否为空"""

def get_dir_size(path) -> int:
    """获取目录总大小（字节）"""
```

### 2.2 查询过滤层 (file_query.py)
用于查询和过滤文件集合的原子函数。

```python
# ===== 文件列表过滤 =====
def filter_by_extension(files, extensions) -> list:
    """按扩展名过滤文件"""

def filter_by_name_pattern(files, pattern) -> list:
    """按名称模式过滤（支持通配符）"""

def filter_by_size(files, min_size=None, max_size=None) -> list:
    """按文件大小过滤"""

def filter_by_date(files, after=None, before=None) -> list:
    """按修改时间过滤"""

def filter_by_name_contains(files, keyword) -> list:
    """文件名包含关键词"""

def filter_by_name_not_contains(files, keyword) -> list:
    """文件名不包含关键词"""

# ===== 文件列表处理 =====
def sort_by_name(files, reverse=False) -> list:
    """按名称排序"""

def sort_by_size(files, reverse=True) -> list:
    """按大小排序"""

def sort_by_date(files, reverse=True) -> list:
    """按修改时间排序"""

def sort_by_extension(files) -> list:
    """按扩展名分组排序"""

def group_by_extension(files) -> dict:
    """按扩展名分组"""

def group_by_date(files, mode="month") -> dict:
    """按日期分组（year/month/day）"""

def group_by_size(files, thresholds) -> dict:
    """按大小区间分组"""

def unique_by_name(files) -> list:
    """按名称去重"""

def unique_by_content(files) -> list:
    """按内容去重（哈希）"""

def get_duplicates(files) -> list:
    """获取重复文件列表"""

# ===== 统计计算 =====
def count_files(files) -> int:
    """统计文件数量"""

def count_by_extension(files) -> dict:
    """统计各类型文件数量"""

def total_size(files) -> int:
    """计算文件总大小"""

def average_size(files) -> int:
    """计算文件平均大小"""
```

### 2.3 批量操作层 (file_batch_ops.py)
基于原子操作的批量封装，但仍然保持可拆分性。

```python
# ===== 批量移动/复制/删除 =====
def batch_move(files, dest_dir) -> dict:
    """批量移动文件，返回成功/失败列表"""

def batch_copy(files, dest_dir) -> dict:
    """批量复制文件，返回成功/失败列表"""

def batch_delete(files, to_trash=True) -> dict:
    """批量删除文件，返回成功/失败列表"""

def batch_rename(files, pattern, replacement) -> dict:
    """批量重命名（正则替换）"""

def batch_add_prefix(files, prefix) -> dict:
    """批量添加前缀"""

def batch_add_suffix(files, suffix) -> dict:
    """批量添加后缀"""

def batch_remove_pattern(files, pattern) -> dict:
    """批量移除匹配的模式"""

def batch_numbering(files, start=1, pattern="{n}_{name}") -> dict:
    """批量编号"""

# ===== 分类整理 =====
def organize_by_type(files, base_dir) -> dict:
    """按文件类型分类到不同文件夹"""

def organize_by_date(files, base_dir, mode="month") -> dict:
    """按日期分类"""

def organize_by_size(files, base_dir, thresholds) -> dict:
    """按大小分类"""

def create_structure(base_dir, categories) -> dict:
    """创建分类目录结构"""
```

### 2.4 意图解析层 (intent_parser.py)
将自然语言解析为函数调用计划。

```python
# ===== 意图解析 =====
def parse_command(text) -> dict:
    """解析用户命令，返回操作计划"""
    # 输入: "把大于100MB的文件移到归档"
    # 输出: {
    #     "action": "move",
    #     "filters": [{"type": "size", "min": "100MB"}],
    #     "target": "归档文件夹"
    # }

def extract_path(text) -> str:
    """提取目标路径"""

def extract_action(text) -> str:
    """提取操作类型（move/copy/delete/rename/organize/search/analyze）"""

def extract_filters(text) -> list:
    """提取过滤条件"""

def extract_parameters(text) -> dict:
    """提取参数（日期、大小、数量等）"""

# ===== 操作计划执行 =====
def create_execution_plan(parsed) -> list:
    """根据解析结果创建执行计划（函数调用序列）"""

def execute_plan(plan) -> dict:
    """执行计划，返回执行结果"""
```

---

## 三、函数组合示例

### 示例1: "删除所有临时文件"
```
parse_command("删除所有临时文件")
  → action: "delete"
  → filters: [{"type": "name_contains", "value": "tmp"}]

执行计划:
1. get_files("当前目录", recursive=True)
2. filter_by_name_contains(文件列表, "tmp")
3. batch_delete(过滤后的文件)
```

### 示例2: "把大于100MB的视频移到归档"
```
parse_command("把大于100MB的视频移到归档")
  → action: "move"
  → filters: [
      {"type": "extension", "value": ["mp4", "avi", "mkv"]},
      {"type": "size", "min": "100MB"}
    ]
  → target: "归档"

执行计划:
1. get_files("当前目录", recursive=True)
2. filter_by_extension(文件列表, ["mp4", "avi", "mkv"])
3. filter_by_size(文件列表, min="100MB")
4. batch_move(过滤后的文件, "归档")
```

### 示例3: "按月份整理图片"
```
parse_command("按月份整理图片")
  → action: "organize"
  → filters: [{"type": "extension", "value": ["jpg", "png", "gif"]}]
  → group_mode: "month"

执行计划:
1. get_files("当前目录", recursive=True)
2. filter_by_extension(文件列表, ["jpg", "png", "gif"])
3. group_by_date(文件列表, mode="month")
4. create_structure("当前目录", 分组结果)
5. batch_move(各组文件, 对应月份文件夹)
```

---

## 四、文件结构

```
file_helper/
├── plan.md                 # 本文档
├── file_atomic_ops.py      # 基础原子操作
├── file_query.py           # 查询过滤原子函数
├── file_batch_ops.py       # 批量操作封装
├── intent_parser.py        # 意图解析器
├── file_helper.py          # 主入口，对外统一接口
└── config.py               # 配置文件
```

---

## 五、实现顺序

1. `file_atomic_ops.py` - 基础操作层（最底层，无依赖）
2. `file_query.py` - 查询过滤层（依赖原子操作）
3. `file_batch_ops.py` - 批量操作层（依赖前两层）
4. `intent_parser.py` - 意图解析层（可独立）
5. `file_helper.py` - 主入口（整合所有模块）
