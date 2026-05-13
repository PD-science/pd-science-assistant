"""
RAG 知识库模块 — 基于 ChromaDB + sentence-transformers 的向量检索。
替换原来把所有内容塞进 system prompt 的 naive 方案。
"""

import os
import re
import json
import logging
from typing import List, Dict


logging.basicConfig(level=logging.INFO, format="[KB] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
COLLECTION_NAME = "pd_knowledge"

# 延迟加载，避免 import 时就加载大模型
_chroma_client = None
_embedding_model = None


def _get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    return _chroma_client


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("正在加载 embedding 模型 (首次加载需要下载 ~470MB)...")
        _embedding_model = SentenceTransformer(
            "paraphrase-multilingual-MiniLM-L12-v2"
        )
        logger.info("embedding 模型加载完成")
    return _embedding_model


def _get_collection():
    client = _get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )


# ==================== 对外 API ====================


def is_indexed() -> bool:
    """检查是否已构建索引。"""
    return _get_collection().count() > 0


def build_index(force: bool = False):
    """构建/重建向量索引。

    Args:
        force: 为 True 时删除已有索引并重建
    """
    collection = _get_collection()
    if collection.count() > 0:
        if force:
            client = _get_chroma_client()
            client.delete_collection(COLLECTION_NAME)
            collection = client.create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("已清除旧索引，开始重建...")
        else:
            logger.info(f"索引已存在 ({collection.count()} 条)，跳过。")
            return

    documents = _load_all_documents()
    if not documents:
        logger.warning("未找到任何可索引的文档。")
        return

    logger.info(f"共 {len(documents)} 个文本块，正在生成 embeddings...")
    model = _get_embedding_model()

    # 分批处理，避免 OOM
    batch_size = 32
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        ids = [d["id"] for d in batch]
        texts = [d["content"] for d in batch]
        metadatas = [{"source": d["source"], "title": d.get("title", "")}
                     for d in batch]
        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        logger.info(f"  已索引 {min(i + batch_size, len(documents))}/{len(documents)}")

    logger.info(f"索引构建完成，共 {collection.count()} 条。")


def query(question: str, n_results: int = 5) -> List[str]:
    """检索与问题最相关的文本块。"""
    collection = _get_collection()
    if collection.count() == 0:
        build_index()

    if collection.count() == 0:
        return []

    model = _get_embedding_model()
    query_embedding = model.encode([question]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(n_results, collection.count())
    )
    return results.get("documents", [[]])[0]


# ==================== 文档加载 ====================


def _load_all_documents() -> List[Dict]:
    """加载所有文档并切块。"""
    documents = []

    # 1. data/ 目录 — 精选知识库
    data_dir = os.path.join(BASE_DIR, "data")
    if os.path.exists(data_dir):
        for filename in sorted(os.listdir(data_dir)):
            if not filename.endswith(".md"):
                continue
            filepath = os.path.join(data_dir, filename)
            documents.extend(_chunk_markdown_file(filepath, prefix="data"))

    # 2. reference/research/ — 论文 .md（主要知识来源）
    research_dir = os.path.join(BASE_DIR, "reference", "research")
    if os.path.exists(research_dir):
        for filename in sorted(os.listdir(research_dir)):
            if filename.startswith("."):
                continue
            if not filename.endswith(".md"):
                continue
            filepath = os.path.join(research_dir, filename)
            documents.extend(_chunk_markdown_file(filepath, prefix="research"))

    # 3. reference/daily/ — 近7天每日文献 JSON
    daily_dir = os.path.join(BASE_DIR, "reference", "daily")
    if os.path.exists(daily_dir):
        files = sorted(
            [f for f in os.listdir(daily_dir) if f.endswith(".json")],
            reverse=True
        )[:1]  # 只取最新一天
        for filename in files:
            filepath = os.path.join(daily_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue

            papers = data if isinstance(data, list) else data.get("articles", [])
            for i, paper in enumerate(papers):
                title = paper.get("title_zh") or paper.get("title_en", "")
                abstract = paper.get("abstract", "")
                journal = paper.get("journal", "")
                impact = paper.get("impact_factor", "")
                if not (title and abstract):
                    continue
                content = f"【{journal} · IF {impact}】\n{title}\n\n{abstract}"
                documents.append({
                    "id": f"daily/{filename}/{i}",
                    "content": content,
                    "source": filename,
                    "title": title,
                })

    return documents


# ==================== 文本切分 ====================


def _chunk_markdown_file(filepath: str, prefix: str = "") -> List[Dict]:
    """按 ## 标题切分 Markdown 文件。"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return []

    filename = os.path.basename(filepath)
    chunks = []

    # 按 ## 标题分段
    sections = re.split(r"\n(?=## )", text)

    for i, section in enumerate(sections):
        section = section.strip()
        if not section or len(section) < 80:
            continue

        # 过滤掉角色设定/系统指令类内容（会干扰 AI 行为）
        if _is_role_instruction(section):
            continue

        if len(section) > 2000:
            subs = _split_long_text(section, max_chars=1500, overlap=200)
            for j, sub in enumerate(subs):
                chunks.append({
                    "id": f"{prefix}/{filename}/s{i}c{j}",
                    "content": sub,
                    "source": filename,
                    "title": filename,
                })
        else:
            chunks.append({
                "id": f"{prefix}/{filename}/s{i}",
                "content": section,
                "source": filename,
                "title": filename,
            })

    return chunks


def _is_role_instruction(text: str) -> bool:
    """检测文本块是否为角色设定/系统指令，这类内容会干扰 AI 行为。"""
    markers = [
        "机器人角色设定",
        "你是一位",
        "你的知识覆盖",
        "对话风格",
        "核心能力范围",
        "重要免责声明",
        "禁止编造",
    ]
    # 只检查文本前 200 个字符（标题 + 开头），避免误判正文
    head = text[:200]
    return any(m in head for m in markers)


def _split_long_text(text: str, max_chars: int = 1500,
                     overlap: int = 200) -> List[str]:
    """将长文本切成带重叠的块，优先在段落/句子边界断开。"""
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + max_chars
        if end >= text_len:
            chunks.append(text[start:].strip())
            break

        # 按优先级尝试找断点
        for sep in ["\n\n", "\n", "。", ". "]:
            pos = text.rfind(sep, start, end)
            if pos > start + max_chars // 2:
                end = pos + len(sep)
                break

        chunks.append(text[start:end].strip())
        start = max(start + 1, end - overlap)

    return chunks
