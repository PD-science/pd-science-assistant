import time
import json
import os
import re
import requests
from datetime import datetime, timedelta
import pandas as pd
from Bio import Entrez
from Bio import Medline

from bs4 import BeautifulSoup

try:
    from paperscraper.impact import Impactor
except ImportError:
    Impactor = None

# ================= 配置区 =================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAILY_DIR = os.path.join(BASE_DIR, "reference", "daily")
SECRETS_PATH = os.path.join(BASE_DIR, ".streamlit", "secrets.toml")
Entrez.email = "pd_science_agent@example.com"
MAX_RESULTS = 100  # 恢复到 100，近7天的高质量 PD 文章通常不会超过这个数
MIN_IF = 5.0

def get_deepseek_client():
    """尝试从环境变量或 streamlit secrets 获取 API Key"""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key and os.path.exists(SECRETS_PATH):
        try:
            import tomllib
            with open(SECRETS_PATH, "rb") as f:
                secrets = tomllib.load(f)
                api_key = secrets.get("DEEPSEEK_API_KEY")
        except:
            try:
                # 兼容旧版 python
                import toml
                secrets = toml.load(SECRETS_PATH)
                api_key = secrets.get("DEEPSEEK_API_KEY")
            except: pass
    
    if api_key and api_key != "sk-dummy":
        try:
            from openai import OpenAI
            return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        except: return None
    return None

# 影响因子缓存，避免重复查询
if_cache = {}

# ================= 期刊名清洗 & IF 查询 =================
def clean_journal_name(name):
    if not isinstance(name, str): return ""
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"\(.*", "", name)
    if ":" in name: name = name.split(":")[0]
    name = re.sub(r"\.\s*Supplement.*", "", name, flags=re.IGNORECASE)
    return " ".join(name.strip().split())

LETPUB_URL = "https://www.letpub.com.cn/index.php?page=journalapp&view=search"

def get_if(journal_name, impactor):
    if not journal_name or journal_name == "N/A": return 0.0
    
    # 统一清洗名称用于缓存键
    search_name = clean_journal_name(journal_name)
    if search_name in if_cache:
        return if_cache[search_name]

    # 1. 尝试 paperscraper 本地库
    if impactor:
        try:
            res = impactor.search(search_name)
            if res: 
                factor = float(res[0]['factor'])
                if_cache[search_name] = factor
                return factor
        except: pass

    # 2. 尝试 LetPub 在线查询
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.letpub.com.cn/index.php?page=journalapp"
    }
    
    # 尝试原始名称和清洗后的名称
    for name_to_try in [journal_name, search_name]:
        params = {"searchname": name_to_try, "searchissn": "", "searchfield": "", "searchimpact": ""}
        try:
            resp = requests.get(LETPUB_URL, params=params, timeout=15, headers=headers)
            if "过快" in resp.text or "频繁" in resp.text:
                continue
                
            soup = BeautifulSoup(resp.text, "lxml")
            # LetPub 的结果通常在 class 为 table_style 的表格中
            table = soup.find("table", class_="table_style")
            if not table:
                # 尝试更宽泛的表格搜索
                tables = soup.find_all("table")
                for t in tables:
                    if "影响因子" in t.get_text():
                        table = t
                        break
            
            if table:
                for row in table.find_all("tr"):
                    cells = row.find_all("td")
                    if len(cells) >= 3:
                        row_text = row.get_text().lower()
                        # 只要行内包含目标名称的部分关键字
                        if name_to_try.lower() in row_text or search_name.lower() in row_text:
                            for cell in cells:
                                cell_text = cell.get_text(strip=True)
                                # 匹配数字格式 (例如 8.2, 12.555)
                                match = re.search(r"^(\d+\.\d+)$", cell_text)
                                if match:
                                    factor = float(match.group(1))
                                    if_cache[search_name] = factor
                                    return factor
        except Exception as e:
            print(f"  [调试] 查询 {name_to_try} 出错: {e}")
            continue

    if_cache[search_name] = 0.0
    return 0.0

def translate_title(title, client=None):
    if not title: return title
    if not client: return title # 没有有效 client 则跳过翻译
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的生物医学翻译，请将以下论文标题准确翻译为中文，只输出翻译结果。"},
                {"role": "user", "content": title}
            ]
        )
        return resp.choices[0].message.content.strip()
    except: return title

def get_pd_query():
    today = datetime.now()
    date_str = (today - timedelta(days=7)).strftime("%Y/%m/%d")
    return f'("Parkinson Disease"[MeSH Terms] OR "Parkinson"[Title/Abstract]) AND ("{date_str}"[Date - Publication] : "3000"[Date - Publication])'

def search_pubmed(query):
    handle = Entrez.esearch(db="pubmed", term=query, retmax=MAX_RESULTS)
    record = Entrez.read(handle)
    handle.close()
    return record["IdList"]

def fetch_details(id_list):
    if not id_list: return []
    handle = Entrez.efetch(db="pubmed", id=",".join(id_list), rettype="medline", retmode="text")
    records = Medline.parse(handle)
    papers = list(records)
    handle.close()
    return papers

def run_agent():
    print(f"--- 每日文献 Agent 启动 ({datetime.now().strftime('%Y-%m-%d')}) ---")
    impactor = Impactor() if Impactor else None
    client = get_deepseek_client()
    if not client:
        print("[提示] 未检测到有效的 DEEPSEEK_API_KEY，将跳过中文翻译步骤。")

    id_list = search_pubmed(get_pd_query())
    if not id_list:
        print("今日无符合条件的新文献。")
        return

    papers = fetch_details(id_list)
    results = []
    
    filename = f"{datetime.now().strftime('%Y-%m-%d')}.json"
    filepath = os.path.join(DAILY_DIR, filename)

    for paper in papers:
        journal_full = paper.get("JT", "")
        journal_abbr = paper.get("TA", "")
        
        title_en = paper.get("TI", "N/A")
        pmid = paper.get("PMID", "")

        # 优先用全称查，再用缩写查
        impact_factor = get_if(journal_full, impactor)
        if impact_factor == 0.0 and journal_abbr:
            impact_factor = get_if(journal_abbr, impactor)
            
        print(f"  检查: {journal_full or journal_abbr} -> IF: {impact_factor}")

        if impact_factor < MIN_IF: continue

        # 命中高分文献
        title_zh = translate_title(title_en, client)
        abstract = paper.get("AB", "暂无摘要")
        date = paper.get("DP", "N/A")

        results.append({
            "title_en": title_en,
            "title_zh": title_zh,
            "journal": journal_full or journal_abbr,
            "impact_factor": round(impact_factor, 2),
            "abstract": abstract,
            "date": date,
            "pmid": pmid,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        })
        print(f"  [命中] {title_en[:50]}... (IF: {impact_factor})")
        
        # 实时保存，防止中断导致数据丢失
        results.sort(key=lambda x: x['impact_factor'], reverse=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"--- 任务完成，共保存 {len(results)} 篇高分文献 ---")

if __name__ == "__main__":
    run_agent()
