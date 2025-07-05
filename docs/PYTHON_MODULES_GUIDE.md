# Python常用模块安装指南 - WSL环境

## 🚀 快速安装

### 自动安装脚本
```bash
./install_python_modules.sh
```

### 手动安装命令
```bash
# 添加pip到PATH
export PATH=$PATH:/home/pepsi/.local/bin

# 基础包
pip3 install --break-system-packages --user numpy pandas matplotlib requests
```

## 📦 推荐模块清单

### 1. 数据科学核心
```bash
# 数值计算
numpy                  # 数组和数值计算
pandas                 # 数据处理和分析
scipy                  # 科学计算库

# 可视化
matplotlib             # 基础绘图
seaborn               # 统计图表
plotly                # 交互式图表
```

### 2. 机器学习
```bash
# 传统机器学习
scikit-learn          # 机器学习算法
xgboost               # 梯度提升

# 深度学习
tensorflow            # Google深度学习框架
torch                 # PyTorch深度学习
keras                 # 高级神经网络API
```

### 3. 图像和视频处理
```bash
# 图像处理
pillow                # Python图像库(PIL)
opencv-python         # 计算机视觉
imageio               # 图像I/O操作
scikit-image          # 图像处理算法

# 视频处理
moviepy               # 视频编辑
```

### 4. 网络和爬虫
```bash
# 网络请求
requests              # HTTP请求库
urllib3               # HTTP客户端
aiohttp               # 异步HTTP

# 网页解析
beautifulsoup4        # HTML/XML解析
lxml                  # XML/HTML解析器
selenium              # 浏览器自动化

# API开发
fastapi               # 现代API框架
flask                 # 轻量级Web框架
django                # 全功能Web框架
```

### 5. 数据库
```bash
# SQL数据库
sqlalchemy            # SQL ORM
pymysql               # MySQL连接器
psycopg2              # PostgreSQL适配器

# NoSQL数据库
pymongo               # MongoDB驱动
redis                 # Redis客户端
```

### 6. 文件和配置
```bash
# 配置文件
pyyaml                # YAML解析
toml                  # TOML解析
configparser          # INI配置解析
python-dotenv         # 环境变量管理

# 文件处理
openpyxl              # Excel文件操作
xlrd                  # Excel读取
csvkit                # CSV工具集
```

### 7. 开发工具
```bash
# 测试
pytest                # 测试框架
unittest              # 内置测试框架
mock                  # 模拟对象

# 代码质量
black                 # 代码格式化
flake8                # 代码检查
mypy                  # 类型检查
autopep8              # PEP8格式化

# 调试和性能
pdb                   # 调试器(内置)
memory_profiler       # 内存分析
line_profiler         # 性能分析
```

### 8. 时间和日期
```bash
arrow                 # 现代日期时间库
pendulum             # 时区感知日期时间
dateutil             # 日期工具扩展
```

### 9. 加密和安全
```bash
cryptography         # 加密库
bcrypt               # 密码哈希
hashlib              # 哈希算法(内置)
secrets              # 安全随机数(内置)
```

### 10. 并发和异步
```bash
asyncio              # 异步编程(内置)
threading            # 线程(内置)
multiprocessing      # 多进程(内置)
concurrent.futures   # 并发执行(内置)
celery               # 分布式任务队列
```

## 🔧 安装方法

### WSL环境特殊配置
```bash
# 永久添加pip到PATH
echo 'export PATH=$PATH:/home/pepsi/.local/bin' >> ~/.bashrc
source ~/.bashrc

# 使用--break-system-packages标志
pip3 install --break-system-packages --user <package_name>
```

### 批量安装示例
```bash
# 数据科学套装
pip3 install --break-system-packages --user \
  numpy pandas matplotlib seaborn scipy scikit-learn jupyter

# Web开发套装
pip3 install --break-system-packages --user \
  requests beautifulsoup4 flask fastapi

# 机器学习套装
pip3 install --break-system-packages --user \
  tensorflow torch scikit-learn xgboost
```

## 📋 验证安装

### 检查重要包
```python
import sys

packages = [
    'numpy', 'pandas', 'matplotlib', 'requests', 
    'sklearn', 'scipy', 'PIL', 'cv2', 'yaml'
]

for pkg in packages:
    try:
        __import__(pkg)
        print(f'✅ {pkg} - 已安装')
    except ImportError:
        print(f'❌ {pkg} - 未安装')
```

### 测试核心功能
```python
# 测试numpy
import numpy as np
print("NumPy版本:", np.__version__)
arr = np.array([1, 2, 3, 4, 5])
print("数组:", arr)

# 测试pandas
import pandas as pd
print("Pandas版本:", pd.__version__)
df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
print("DataFrame:\n", df)

# 测试matplotlib
import matplotlib.pyplot as plt
print("Matplotlib版本:", plt.matplotlib.__version__)

# 测试requests
import requests
print("Requests版本:", requests.__version__)
```

## 🚨 常见问题

### 1. pip不在PATH中
```bash
# 临时解决
export PATH=$PATH:/home/pepsi/.local/bin

# 永久解决
echo 'export PATH=$PATH:/home/pepsi/.local/bin' >> ~/.bashrc
source ~/.bashrc
```

### 2. 权限问题
```bash
# 使用--user标志
pip3 install --user <package>

# 或使用--break-system-packages
pip3 install --break-system-packages --user <package>
```

### 3. 网络超时
```bash
# 使用国内镜像源
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple/ <package>

# 增加超时时间
pip3 install --timeout 1000 <package>
```

### 4. 依赖冲突
```bash
# 创建虚拟环境
python3 -m venv myenv
source myenv/bin/activate
pip install <package>
```

## 🎯 使用建议

### 1. 按需安装
- 不要一次性安装所有包
- 根据项目需求选择性安装
- 定期清理不用的包

### 2. 版本管理
```bash
# 查看已安装包
pip3 list

# 导出依赖列表
pip3 freeze > requirements.txt

# 从文件安装
pip3 install -r requirements.txt
```

### 3. 性能优化
- 大型包（如tensorflow）建议在需要时再安装
- 使用轻量级替代方案（如使用requests而不是urllib）
- 考虑使用conda管理科学计算包

## 📚 学习资源

### 官方文档
- [NumPy](https://numpy.org/doc/)
- [Pandas](https://pandas.pydata.org/docs/)
- [Matplotlib](https://matplotlib.org/stable/contents.html)
- [Requests](https://docs.python-requests.org/)
- [Scikit-learn](https://scikit-learn.org/stable/)

### 中文教程
- [NumPy中文文档](https://www.numpy.org.cn/)
- [Pandas中文文档](https://www.pypandas.cn/)
- [Python爬虫教程](https://scrapy-chs.readthedocs.io/)

现在您可以在WSL环境中愉快地使用Python进行开发了！🐍