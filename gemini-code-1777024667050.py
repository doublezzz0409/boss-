import time
import json
import re
import random
import pandas as pd
from datetime import datetime
from DrissionPage import ChromiumPage, ChromiumOptions
from openai import OpenAI

# =========================================================
# 配置区域 - 开关
# =========================================================
# 开关1: 关键词模式
AUTO_KEYWORD = False
DEFAULT_KEYWORD = "Python"

# 开关2: 爬取数量模式
AUTO_MAXJOBS = False
DEFAULT_MAXJOBS = 30

# 开关3: AI评估模式
ENABLE_AI_EVALUATION = True  # True = 启用AI评估
AI_API_KEY = " "
AI_MODEL = "doubao-seed-2-0-pro-260215"

# ======================
# AI评估个性化配置（请根据自身情况修改）
# ======================
USER_EXPECTED_JOB = "Python开发工程师"  # 期望岗位
USER_EXPECTED_SALARY = "15-25K"  # 期望薪资范围
USER_WORK_EXPERIENCE = 2  # 工作经验（年）
USER_PREFERENCES = "不接受996、不考虑外包、要求五险一金、优先大厂/上市企业"  # 核心求职偏好

# 开关4: Excel保存模式
ENABLE_EXCEL_SAVE = True  # True = 自动保存到Excel
EXCEL_FILENAME = "boss_jobs_{timestamp}.xlsx"  # 文件名模板

# =========================================================
# 模块0：AI评估模块
# =========================================================
def evaluate_job_with_ai(job_data):
    """
    使用AI模型评估单个工作岗位的好坏
    
    参数:
        job_data: 岗位数据字典
    返回:
        dict: AI评估结果
    """
    if not ENABLE_AI_EVALUATION:
        return {
            "score": None,
            "match_reason": None,
            "pros": None,
            "cons": None,
            "risk_warning": None,
            "suggestion": "AI评估未启用",
            "is_reject": False
        }
    
    try:
        # 初始化AI客户端
        client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=AI_API_KEY,
        )
        
        # 构建提示词
        prompt = f"""
请作为专业的求职顾问，从求职者角度严格评估以下工作岗位，评估时优先参考求职者的核心诉求。

求职者核心诉求：
- 期望岗位：{USER_EXPECTED_JOB}
- 期望薪资：{USER_EXPECTED_SALARY}
- 工作经验：{USER_WORK_EXPERIENCE}年
- 核心偏好：{USER_PREFERENCES}

岗位信息：
- 职位名称：{job_data['job_name']}
- 薪资：{job_data['salary']}
- 公司：{job_data['company']}
- 地址：{job_data['address']}
- 岗位描述：{job_data['description'][:800] if job_data['description'] else '无描述'}

评分规则（严格执行）：
1. 1-3分：完全不匹配（岗位要求远高于/低于你的能力、薪资远低于预期、是培训机构/外包/虚假岗位）
2. 4-6分：基本匹配（满足基本要求，但有明显缺点，可作为备选）
3. 7-8分：良好匹配（符合大部分要求，值得投递）
4. 9-10分：完美匹配（完全符合所有诉求，优先级最高）

返回JSON格式：
{{
  "score": 8,
  "match_reason": "岗位要求与你的工作经验匹配，薪资符合预期",
  "pros": ["薪资有竞争力", "发展前景好", "团队氛围好"],
  "cons": ["加班较多", "通勤距离远", "福利一般"],
  "risk_warning": "岗位描述中提到需要接受996，请注意",
  "suggestion": "建议投递，简历中重点突出Python开发和项目经验",
  "is_reject": false
}}

要求：
- is_reject: 布尔值，不符合核心诉求的岗位直接设为true（如要求经验远超你的年限、是外包、薪资低于最低期望等）
- match_reason: 明确说明匹配/不匹配的核心原因
- risk_warning: 指出岗位的潜在坑点，没有则填空字符串
- pros/cons: 3-5条，每条突出一个核心点
- suggestion: 给出具体的行动建议，不要空泛
- 只返回JSON，不要其他文字！
"""
        
        # 调用AI API
        response = client.responses.create(
            model=AI_MODEL,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        
        # 解析AI返回结果 - 健壮性检查
        ai_text = ""
        try:
            # 逐层检查返回结构
            if not response.output or len(response.output) == 0:
                raise Exception("response.output为空")
            
            # 查找正确的output项（可能是reasoning或message类型）
            output_item = None
            for item in response.output:
                if hasattr(item, 'content') and item.content:
                    output_item = item
                    break
            
            if not output_item:
                raise Exception("未找到有效的output项")
            
            if not output_item.content or len(output_item.content) == 0:
                raise Exception("output.content为空")
            
            content_item = output_item.content[0]
            if hasattr(content_item, 'text'):
                ai_text = content_item.text
            else:
                raise Exception("content项没有text属性")
            
        except Exception as e:
            print(f"  [AI解析警告] {e}")
            return {
                "score": None,
                "match_reason": None,
                "pros": None,
                "cons": None,
                "risk_warning": None,
                "suggestion": f"AI返回解析失败: {str(e)[:50]}",
                "is_reject": False
            }
        
        # 尝试提取JSON
        try:
            # 清理可能的markdown代码块标记
            ai_text_clean = ai_text.strip()
            if ai_text_clean.startswith('```'):
                ai_text_clean = ai_text_clean[ai_text_clean.find('\n')+1:]
                if ai_text_clean.endswith('```'):
                    ai_text_clean = ai_text_clean[:-3]
            
            result = json.loads(ai_text_clean.strip())
            return result
        except:
            # 如果JSON解析失败，返回简单格式
            return {
                "score": None,
                "match_reason": None,
                "pros": None,
                "cons": None,
                "risk_warning": None,
                "suggestion": ai_text[:100] if ai_text else "AI返回格式异常",
                "is_reject": False
            }
    
    except Exception as e:
        print(f"AI评估出错: {e}")
        return {
            "score": None,
            "match_reason": None,
            "pros": None,
            "cons": None,
            "risk_warning": None,
            "suggestion": f"AI评估失败: {str(e)[:50]}",
            "is_reject": False
        }

# =========================================================
# 模块0.5：薪资结构化解析
# =========================================================
def parse_salary(salary_str):
    """
    解析薪资字符串为结构化数值
    参数:
        salary_str: 原始薪资格式字符串，如"15-25K·14薪"、"300元/天"、"面议"等
    返回:
        dict: {
            "salary_min": float,  # 最低月薪（单位：K）
            "salary_max": float,  # 最高月薪（单位：K）
            "annual_salary_range": str,  # 年薪范围（单位：万），如"21-35万"
            "salary_type": str  # 薪资类型：monthly/ daily /面议/未知
        }
    """
    if not salary_str or any(keyword in salary_str for keyword in ["提取失败", "超时", "跳过", "面议", "未公布", "薪资保密", "JSON解析键错误", "接口匹配跳过", "监听超时/缓存"]):
        return {
            "salary_min": None,
            "salary_max": None,
            "annual_salary_range": None,
            "salary_type": "面议"
        }
    
    salary_str = salary_str.replace(' ', '').upper()
    
    # 匹配日薪格式：300-400元/天、500元/天
    if '元/天' in salary_str or '/天' in salary_str:
        match = re.match(r'(\d+)(?:-(\d+))?元?/天', salary_str)
        if match:
            min_daily = int(match.group(1))
            max_daily = int(match.group(2)) if match.group(2) else min_daily
            # 按每月22天，12个月计算年薪，转成万
            min_annual = round(min_daily * 22 * 12 / 10000, 1)
            max_annual = round(max_daily * 22 * 12 / 10000, 1)
            return {
                "salary_min": round(min_daily * 22 / 1000, 1),
                "salary_max": round(max_daily * 22 / 1000, 1),
                "annual_salary_range": f"{min_annual}-{max_annual}万",
                "salary_type": "daily"
            }
    
    # 匹配月薪格式：15-25K·14薪、20K·13薪、25-35K
    match = re.match(r'(\d+)(?:-(\d+))?K(?:·(\d+)薪)?', salary_str)
    if match:
        min_month = int(match.group(1))
        max_month = int(match.group(2)) if match.group(2) else min_month
        months = int(match.group(3)) if match.group(3) else 12
        min_annual = round(min_month * months / 10, 1)
        max_annual = round(max_month * months / 10, 1)
        return {
            "salary_min": float(min_month),
            "salary_max": float(max_month),
            "annual_salary_range": f"{min_annual}-{max_annual}万",
            "salary_type": "monthly"
        }
    
    # 无法解析的格式
    return {
        "salary_min": None,
        "salary_max": None,
        "annual_salary_range": None,
        "salary_type": "未知"
    }

# =========================================================
# 模块0.6：Excel保存功能
# =========================================================
_excel_filename = None  # 全局保存文件名

def save_to_excel(jobs_list, filename_template="boss_jobs_{timestamp}.xlsx"):
    """
    将职位数据保存到Excel
    
    参数:
        jobs_list: 职位数据列表
        filename_template: 文件名模板，支持 {timestamp} 占位符
    """
    global _excel_filename
    
    if not ENABLE_EXCEL_SAVE:
        return
    
    try:
        # 准备数据
        data_rows = []
        for job in jobs_list:
            row = {
                "序号": job.get("index", ""),
                "职位名称": job.get("job_name", ""),
                "薪资": job.get("salary", ""),
                "最低月薪(K)": job.get("salary_min", ""),
                "最高月薪(K)": job.get("salary_max", ""),
                "年薪范围": job.get("annual_salary_range", ""),
                "薪资类型": job.get("salary_type", ""),
                "公司名称": job.get("company", ""),
                "地址": job.get("address", ""),
                "职位描述": job.get("description", ""),
            }
            
            # 添加AI评估数据（如果有）
            ai_eval = job.get("ai_evaluation", {})
            if ai_eval:
                row["AI评分"] = ai_eval.get("score", "")
                row["匹配原因"] = ai_eval.get("match_reason", "")
                row["AI优点"] = " | ".join(ai_eval.get("pros", [])) if ai_eval.get("pros") else ""
                row["AI缺点"] = " | ".join(ai_eval.get("cons", [])) if ai_eval.get("cons") else ""
                row["风险警告"] = ai_eval.get("risk_warning", "")
                row["AI建议"] = ai_eval.get("suggestion", "")
                row["是否不推荐"] = "是" if ai_eval.get("is_reject") else "否"
            
            data_rows.append(row)
        
        # 首次生成文件名，之后保持不变
        if _excel_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            _excel_filename = filename_template.format(timestamp=timestamp)
        
        # 保存到Excel
        df = pd.DataFrame(data_rows)
        df.to_excel(_excel_filename, index=False, engine='openpyxl')
        print(f"  [Excel保存] 已保存 {len(jobs_list)} 个职位")
        
    except Exception as e:
        print(f"  [Excel保存失败] {e}")

# =========================================================
# 模块1：搜索防检测流程
# =========================================================
def perform_search(page, keyword="Python"):
    print(">>> 场景1：检测到不在结果页，开始自动搜索流程 <<<")
    
    print("访问首页...")
    page.get('https://www.zhipin.com/')
    page.wait(2, 5)

    print("正在定位搜索框...")
    search_input = page.ele('.ipt-search')

    if not search_input:
        print("未能定位到搜索框！请检查页面状态。")
        return False
    
    search_input.click()
    page.wait(0.5, 1.2)
    search_input.clear()

    print(f"开始逐字输入关键词: {keyword} ...")
    for char in keyword:
        search_input.input(char)
        page.wait(0.2, 0.5)

    page.wait(1, 2)

    print("提交搜索请求...")
    page.actions.type('\n')

    print("等待页面跳转中...")
    page.wait(5, 8)

    if 'job' in page.url:
        print("--- 成功进入结果页，准备交接给抓取模块 ---")
        return True
    else:
        print(f"跳转异常，当前网址: {page.url}")
        return False

# =========================================================
# 模块2：数据提取流程，返回结构化数据
# =========================================================
def boss_ultimate_spider_logic(page, max_jobs=30):
    print(f">>> 启动数据提取核心逻辑，目标爬取 {max_jobs} 个职位 <<<")
    
    results = []
    
    page.listen.start(['search/job.json', 'job/detail.json'])

    print("--- 正在预留渲染时间，请稍候 ---")
    page.wait(4)  # 增加1秒等待，确保页面完全稳定

    processed_count = 0
    last_item_count = 0
    no_new_items_count = 0
    max_no_new = 3

    while processed_count < max_jobs:
        items = page.eles('css:.job-card-box')
        current_item_count = len(items)
        
        print(f"当前页面有 {current_item_count} 个职位，已处理 {processed_count} 个")

        if current_item_count <= last_item_count:
            no_new_items_count += 1
            print(f"  未发现新职位，尝试滚动加载... ({no_new_items_count}/{max_no_new})")
            
            if no_new_items_count >= max_no_new:
                print("  多次滚动后仍无新职位，可能已到底部，提前结束")
                break
            
            page.scroll.to_bottom()
            page.wait(2, 4)
            continue
        
        no_new_items_count = 0
        last_item_count = current_item_count

        for index in range(processed_count, current_item_count):
            if processed_count >= max_jobs:
                break
            
            item = items[index]
            
            try:
                job_name = item.ele('.job-name').text
                company = item.ele('.boss-name').text if item.ele('.boss-name') else "未知公司"

                page.scroll.to_see(item)
                page.wait(0.5)
                
                # 第一个职位增加额外的页面稳定时间
                if processed_count == 0:
                    page.wait(1.5)
                
                item.click(by_js=True)

                # 第一个职位使用更长的超时时间
                wait_time = 8 if processed_count == 0 else 3
                res = page.listen.wait(timeout=wait_time)
                
                if processed_count == 0 and not res:
                    print(f"  [调试] 第1个职位首次监听失败，开始重试...")
                    for retry in range(3):
                        page.actions.click((10, 10))
                        page.wait(1.5)  # 增加重试等待时间
                        item.click(by_js=True)
                        res = page.listen.wait(timeout=7)  # 增加重试超时时间
                        if res:
                            print(f"  [调试] 第{retry + 1}次重试成功！")
                            break
                        else:
                            print(f"  [调试] 第{retry + 1}次重试失败，继续...")

                salary = "提取失败"
                full_desc = "未找到描述"

                if res:
                    payload = res.response.body
                    if 'jobInfo' in str(payload):
                        try:
                            salary = payload['zpData']['jobInfo']['salaryDesc']
                            full_desc = payload['zpData']['jobInfo']['postDescription']
                        except (KeyError, TypeError):
                            salary = "JSON解析键错误"
                    else:
                        salary = "接口匹配跳过"
                else:
                    salary = "监听超时/缓存"

                page.wait(1)
                address_ele = page.ele('.job-address-desc')
                address = address_ele.text if address_ele else "地址加载中"

                # 解析结构化薪资
                salary_info = parse_salary(salary)

                job_data = {
                    "index": processed_count + 1,
                    "job_name": job_name,
                    "salary": salary,
                    "salary_min": salary_info["salary_min"],
                    "salary_max": salary_info["salary_max"],
                    "annual_salary_range": salary_info["annual_salary_range"],
                    "salary_type": salary_info["salary_type"],
                    "company": company,
                    "address": address,
                    "description": full_desc,
                    "ai_evaluation": None
                }
                
                # AI评估岗位
                if ENABLE_AI_EVALUATION:
                    print(f"  [AI评估] 正在评估岗位 {processed_count + 1}...")
                    job_data["ai_evaluation"] = evaluate_job_with_ai(job_data)
                
                results.append(job_data)

                print(f"[{processed_count + 1}/{max_jobs}] 职位: {job_name}")
                print(f"    薪资: {salary} (来自接口数据)")
                print(f"    公司: {company}")
                print(f"    地址: {address}")
                
                # 显示AI评估结果
                if job_data["ai_evaluation"] and job_data["ai_evaluation"]["score"] is not None:
                    ai_eval = job_data["ai_evaluation"]
                    reject_tag = "⚠️ 不推荐" if ai_eval["is_reject"] else "✅ 推荐"
                    print(f"    [AI评分] {ai_eval['score']}分 | {reject_tag}")
                    if ai_eval["match_reason"]:
                        print(f"    [匹配原因] {ai_eval['match_reason']}")
                    if ai_eval["risk_warning"]:
                        print(f"    [风险警告] {ai_eval['risk_warning']}")
                    print(f"    [AI建议] {ai_eval['suggestion']}")
                
                clean_desc = full_desc.replace('\n', ' ').strip()
                print(f"    描述: {clean_desc[:100]}...")
                print("-" * 70)
                
                # 每处理完一个职位就保存一次Excel
                if ENABLE_EXCEL_SAVE:
                    save_to_excel(results, EXCEL_FILENAME)

                processed_count += 1
                page.wait(random.uniform(2, 4))

            except Exception as e:
                print(f"处理第 {processed_count + 1} 个职位时出错: {e}")
                processed_count += 1
                continue

    print(f"抓取完成！共处理 {processed_count} 个职位")
    return results

# =========================================================
# 模块3：手动输入获取参数
# =========================================================
def get_manual_params():
    """从用户输入获取关键词和爬取数量"""
    print("\n" + "="*70)
    print("手动输入模式")
    print("="*70)
    
    keyword = None
    max_jobs = None
    
    if not AUTO_KEYWORD:
        while True:
            keyword = input("请输入搜索关键词: ").strip()
            if keyword:
                break
            print("关键词不能为空，请重新输入！")
    else:
        keyword = DEFAULT_KEYWORD
        print(f"使用自动关键词: {keyword}")
    
    if not AUTO_MAXJOBS:
        while True:
            try:
                max_jobs_input = input("请输入要爬取的职位数量: ").strip()
                max_jobs = int(max_jobs_input)
                if max_jobs > 0:
                    break
                print("数量必须大于0，请重新输入！")
            except ValueError:
                print("请输入有效的数字！")
    else:
        max_jobs = DEFAULT_MAXJOBS
        print(f"使用自动数量: {max_jobs}")
    
    print("="*70 + "\n")
    return keyword, max_jobs

# =========================================================
# 模块4：AI模型对接接口 - 主入口
# =========================================================
def run_zhipin_spider(keyword="Python", max_jobs=30):
    """
    BOSS直聘爬虫主接口，供AI模型调用
    
    参数:
        keyword (str): 搜索关键词，默认"Python"
        max_jobs (int): 要爬取的职位数量，默认30
    
    返回:
        dict: 包含状态信息和爬取结果的字典
        {
            "success": bool,
            "keyword": str,
            "target_count": int,
            "actual_count": int,
            "jobs": list[dict],
            "error": str (如果失败)
        }
    """
    co = ChromiumOptions().set_paths(browser_path=None)
    co.set_local_port(9222)
    co.set_argument('--disable-blink-features=AutomationControlled')
    
    result = {
        "success": False,
        "keyword": keyword,
        "target_count": max_jobs,
        "actual_count": 0,
        "jobs": [],
        "error": None
    }

    try:
        print("正在接管 9222 端口的浏览器...")
        page = ChromiumPage(co)
        
        current_url = page.url
        print(f"当前页面URL: {current_url}")
        
        if 'zhipin.com' in current_url and 'job' in current_url:
            print(f"检测到当前已在结果页 (URL: {current_url})")
            print(">>> 场景2：跳过搜索流程，直接启动数据提取 <<<")
        else:
            print(f"未检测到结果页特征 (URL: {current_url})")
            is_search_success = perform_search(page, keyword=keyword)
            if not is_search_success:
                print("⚠️ 搜索流程似乎未正常跳转至结果页，程序仍将尝试提取，请注意页面状态。")

        jobs = boss_ultimate_spider_logic(page, max_jobs=max_jobs)
        
        result["success"] = True
        result["actual_count"] = len(jobs)
        result["jobs"] = jobs
        
    except Exception as e:
        print(f"DrissionPage 运行异常或页面出错: {e}")
        result["error"] = str(e)
    
    return result

# =========================================================
# 模块5：结果汇总和展示
# =========================================================
def print_final_summary(result):
    """打印最终汇总结果，包括AI评估排名"""
    print("\n" + "="*70)
    print("最终结果摘要")
    print("="*70)
    print(f"关键词: {result['keyword']}")
    print(f"目标数量: {result['target_count']}")
    print(f"实际爬取: {result['actual_count']}")
    print(f"成功状态: {result['success']}")
    
    if result['error']:
        print(f"错误信息: {result['error']}")
    
    # AI评估排名
    if ENABLE_AI_EVALUATION and result['jobs']:
        print("\n" + "="*70)
        print("岗位AI评估排名（按评分从高到低）")
        print("="*70)
        
        # 筛选有评分的岗位
        jobs_with_score = [job for job in result['jobs'] 
                          if job.get('ai_evaluation') and job['ai_evaluation'].get('score') is not None]
        
        if jobs_with_score:
            # 按评分排序
            sorted_jobs = sorted(jobs_with_score, 
                                key=lambda x: x['ai_evaluation']['score'], 
                                reverse=True)
            
            # 过滤掉不推荐的岗位
            sorted_jobs = [job for job in sorted_jobs if not job['ai_evaluation']['is_reject']]
            
            for idx, job in enumerate(sorted_jobs, 1):
                eval_data = job['ai_evaluation']
                print(f"\n[{idx}] {job['job_name']} ({job['company']})")
                print(f"    评分: {eval_data['score']}分 | 薪资: {job['salary']} | 年薪: {job['annual_salary_range']}")
                print(f"    匹配原因: {eval_data['match_reason']}")
                if eval_data['risk_warning']:
                    print(f"    风险警告: {eval_data['risk_warning']}")
                print(f"    建议: {eval_data['suggestion']}")
        else:
            print("暂无有效的AI评估结果")
    
    # 薪资排名
    print("\n" + "="*70)
    print("岗位薪资排名（按最高月薪从高到低，Top10）")
    print("="*70)
    
    # 筛选有薪资数据的岗位
    jobs_with_salary = [job for job in result['jobs'] 
                      if job.get('salary_max') is not None]
    
    if jobs_with_salary:
        # 按最高薪资排序
        sorted_salary_jobs = sorted(jobs_with_salary, 
                            key=lambda x: x['salary_max'], 
                            reverse=True)
        
        for idx, job in enumerate(sorted_salary_jobs[:10], 1):
            print(f"\n[{idx}] {job['job_name']} ({job['company']})")
            print(f"    薪资: {job['salary']} | 年薪: {job['annual_salary_range']}")
            print(f"    地址: {job['address']}")
            if job.get('ai_evaluation') and job['ai_evaluation'].get('score'):
                print(f"    AI评分: {job['ai_evaluation']['score']}分 | 建议: {job['ai_evaluation']['suggestion']}")
    else:
        print("暂无有效的薪资数据")
    
    print("="*70)

# =========================================================
# 主函数
# =========================================================
def main():
    print("="*70)
    print("BOSS直聘爬虫启动")
    print(f"关键词模式: {'自动' if AUTO_KEYWORD else '手动'}")
    print(f"数量模式: {'自动' if AUTO_MAXJOBS else '手动'}")
    print(f"AI评估: {'已启用' if ENABLE_AI_EVALUATION else '已禁用'}")
    print("="*70)
    
    keyword, max_jobs = get_manual_params()
    
    result = run_zhipin_spider(keyword=keyword, max_jobs=max_jobs)
    
    print_final_summary(result)
    
    return result

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("程序已手动停止")
