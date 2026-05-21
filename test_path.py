import json
from pathlib import Path

# 模拟前端发送的数据
raw_json = '{"workspace":"D:\\\\file_helper_demo","command":"test"}'
print('Raw JSON:', repr(raw_json))

data = json.loads(raw_json)
workspace = data.get('workspace', '')
print('Parsed workspace:', repr(workspace))
print('Type:', type(workspace))

# 检查路径是否存在
p = Path(workspace)
print('Path exists:', p.exists())
print('Path repr:', repr(str(p)))

# 尝试替换反斜杠
workspace2 = workspace.replace('\\', '/')
print('After replace:', repr(workspace2))
print('Exists after replace:', Path(workspace2).exists())
