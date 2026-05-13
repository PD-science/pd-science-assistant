import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAILY_DIR = os.path.join(BASE_DIR, "reference", "daily")

def get_latest_daily_data():
    if not os.path.exists(DAILY_DIR): return []
    files = sorted([f for f in os.listdir(DAILY_DIR) if f.endswith(".json")], reverse=True)
    if not files: return []
    try:
        with open(os.path.join(DAILY_DIR, files[0]), "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list): return data
            return data.get("articles", [])
    except: return []

def get_all_recent_papers(days=7):
    all_papers = []
    if not os.path.exists(DAILY_DIR): return []

    files = sorted([f for f in os.listdir(DAILY_DIR) if f.endswith(".json")], reverse=True)

    for file in files[:days]:
        path = os.path.join(DAILY_DIR, file)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_papers.extend(data)
                elif isinstance(data, dict) and "articles" in data:
                    for art in data["articles"]:
                        all_papers.append({
                            "title_en": art.get("title", ""),
                            "title_zh": art.get("title_zh", art.get("title", "")),
                            "journal": art.get("journal", ""),
                            "impact_factor": art.get("impact_factor", 0),
                            "abstract": art.get("abstract", ""),
                            "date": art.get("publication_date", art.get("date", "")),
                            "pmid": art.get("pubmed_id", art.get("pmid", "")),
                            "url": art.get("url", f"https://pubmed.ncbi.nlm.nih.gov/{art.get('pubmed_id', art.get('pmid', ''))}/")
                        })
        except Exception as e:
            print(f"解析 {file} 失败: {e}")

    # 过滤无效数据并去重（按 PMID）
    seen_pmids = set()
    seen_titles = set()
    valid_papers = []
    for p in all_papers:
        if not isinstance(p, dict) or not p.get("title_en"):
            continue
        pmid = p.get("pmid", "")
        title = p.get("title_en", "")
        if pmid and pmid in seen_pmids:
            continue
        if not pmid and title in seen_titles:
            continue
        if pmid:
            seen_pmids.add(pmid)
        if not pmid:
            seen_titles.add(title)
        valid_papers.append(p)

    valid_papers.sort(key=lambda x: x.get("impact_factor", 0) if isinstance(x.get("impact_factor"), (int, float)) else 0, reverse=True)
    return valid_papers
