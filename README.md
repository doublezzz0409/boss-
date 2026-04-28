# boss-
# BOSS直聘智能爬虫

基于 Python + DrissionPage 的 BOSS直聘职位爬虫，集成 AI 智能评估功能。

## 功能特点

- 🔍 关键词搜索职位
- 📊 自动滚动加载更多职位
- 💰 网络抓包获取真实薪资
- 🤖 AI 智能评估岗位（豆包API）
- 📈 评分排序展示
- 📄 自动保存到 Excel（每处理完一个职位就保存）
- 🎛️ 灵活的开关配置

## 环境准备

### 1. 安装依赖

```bash
pip install drissionpage openai pandas openpyxl
```

### 2. 启动 Chrome（重要！）

使用以下命令启动 Chrome，开启远程调试端口：

```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\selenium_profile"
```

**参数说明：**
- `--remote-debugging-port=9222`：开启远程调试，端口9222
- `--user-data-dir="C:\selenium_profile"`：独立的用户数据目录，保存登录状态

### 3. 浏览器配置

在打开的 Chrome 中：
1. 登录 BOSS直聘
2. （可选）设置好地区、薪资等筛选条件

## 快速开始

### 方式1：直接运行

```bash
python gemini-code-1777024667050.py
```

### 方式2：作为模块调用

```python
from gemini-code-1777024667050 import run_zhipin_spider

# 调用API
result = run_zhipin_spider(keyword="Python", max_jobs=10)

# 使用结果
if result["success"]:
    print(f"共爬取 {result['actual_count']} 个职位")
    for job in result["jobs"]:
        print(job["job_name"], job["salary"])
```

## 配置说明

在文件开头有4个独立开关：

```python
# 开关1：关键词模式
AUTO_KEYWORD = False          # True=自动使用默认值，False=手动输入
DEFAULT_KEYWORD = "Python"     # 默认关键词

# 开关2：爬取数量模式
AUTO_MAXJOBS = False          # True=自动使用默认值，False=手动输入
DEFAULT_MAXJOBS = 30          # 默认爬取数量

# 开关3：AI评估模式
ENABLE_AI_EVALUATION = True   # True=启用AI评估，False=禁用
AI_API_KEY = "xxx"            # 豆包API Key
AI_MODEL = "doubao-seed-2-0-pro-260215"

# 开关4：Excel保存模式
ENABLE_EXCEL_SAVE = True      # True=自动保存到Excel，False=禁用
EXCEL_FILENAME = "boss_jobs_{timestamp}.xlsx"  # 文件名模板
```

## API 接口文档

### `run_zhipin_spider(keyword="Python", max_jobs=30)`

主入口函数，执行搜索和爬取。

**参数：**
- `keyword` (str): 搜索关键词，默认 "Python"
- `max_jobs` (int): 爬取数量，默认 30

**返回：**
```python
{
    "success": bool,          # 是否成功
    "keyword": str,           # 搜索关键词
    "target_count": int,      # 目标数量
    "actual_count": int,      # 实际爬取数量
    "jobs": [Job对象...],     # 职位列表
    "error": str | None       # 错误信息
}
```

### Job 对象结构

```python
{
    "index": 1,
    "job_name": "全栈工程师（Python+AI）",
    "salary": "8-12K",
    "company": "融媒科技",
    "address": "太原迎泽区永达大厦1楼",
    "description": "岗位职责...",
    "ai_evaluation": {  # （可选）AI评估结果
        "score": 8,
        "pros": ["薪资有竞争力", "发展前景好", "团队氛围好"],
        "cons": ["加班较多", "通勤距离远", "福利一般"],
        "suggestion": "可以考虑投递"
    }
}
```

## 模块说明

### 模块0：AI评估模块
- `evaluate_job_with_ai(job_data)`：使用豆包API评估岗位

### 模块1：搜索流程
- `perform_search(page, keyword)`：执行搜索，跳转到结果页

### 模块2：数据抓取
- `boss_ultimate_spider_logic(page, max_jobs)`：核心抓取逻辑

### 模块3：参数获取
- `get_manual_params()`：根据开关决定手动/自动获取参数

### 模块4：结果展示
- `print_final_summary(result)`：打印最终结果和AI排名

## 二次开发指南

### 1. 修改提示词

找到 `evaluate_job_with_ai` 函数，修改 `prompt` 变量：

```python
prompt = f"""
你的自定义提示词...
{job_data['job_name']}
...
"""
```

### 2. 添加更多字段

在 `boss_ultimate_spider_logic` 中修改 `job_data` 字典：

```python
job_data = {
    "index": processed_count + 1,
    "job_name": job_name,
    "salary": salary,
    "company": company,
    "address": address,
    "description": full_desc,
    "your_custom_field": value  # 添加自定义字段
}
```

### 3. 接入其他AI模型

修改 `evaluate_job_with_ai` 函数，替换为你的AI调用逻辑。

### 4. 保存数据

添加保存功能（示例）：

```python
# 在 main() 函数最后添加
with open("result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
```

## 项目结构

```
NEW_AI_CODE/
├── gemini-code-1777024667050.py  # 主程序
├── README.md                      # 本文档
├── bug分析.md                     # Bug分析文档
├── chromedriver.exe               # (可选) Chrome驱动
├── 调用ai大模型api资料/
│   ├── 参考资料调用豆包api示例代码.py
│   └── 调用豆包api返回结果示例.txt
└── (其他文件...)
```

## 常见问题

### Q: 提示"无法连接到浏览器"？
A: 确保已使用正确的命令启动 Chrome，端口9222没有被占用。

### Q: 薪资显示"监听超时/缓存"？
A: 网络请求捕获失败，检查页面是否正常加载，或增加等待时间。

### Q: AI评估不工作？
A: 检查 API Key 是否正确，确认 `ENABLE_AI_EVALUATION = True`。

### Q: 如何更换为其他AI模型？
A: 修改 `evaluate_job_with_ai` 函数中的 API 调用逻辑。

## 许可证

本项目仅供学习交流使用，请勿用于商业用途。

## 贡献

欢迎提交 Issue 和 PR！
