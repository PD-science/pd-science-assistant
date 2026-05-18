import streamlit as st
from openai import OpenAI
import os
import sys

# 将 src 目录加入路径，以便导入 daily.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
import daily
import knowledge_base as kb
import analytics

# ========== 1. 页面配置 & UI 美化 ==========
st.set_page_config(
    page_title="PD科学 - 前沿科研助手",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ========== 2. 语言设置 ==========
if "lang" not in st.session_state:
    st.session_state.lang = "zh"


def t(key, **kwargs):
    """获取当前语言的文本。"""
    text = TEXTS.get(key, {}).get(st.session_state.lang, key)
    if kwargs:
        text = text.format(**kwargs)
    return text


TEXTS = {
    "lang_switch":       {"zh": "EN", "en": "中文"},
    "left_header":       {"zh": "📡 近7天高分文献动态", "en": "📡 Top Papers This Week"},
    "no_papers":         {"zh": "近7天暂无符合条件的文献更新。", "en": "No papers matching criteria in the last 7 days."},
    "aux_features":      {"zh": "🛠️ 辅助功能", "en": "🛠️ Tools"},
    "func_hotspot":      {"zh": "📈 科研热点趋势", "en": "📈 Research Trends"},
    "func_trial":        {"zh": "🗺️ 临床试验地图", "en": "🗺️ Clinical Trial Map"},
    "func_consensus":    {"zh": "📖 专家共识解读", "en": "📖 Expert Consensus"},
    "hotspot_info":      {"zh": "🔥 当前热点：α-突触核蛋白、FAM171A2、iPSC 疗法",
                          "en": "🔥 Hot topics: α-synuclein, FAM171A2, iPSC therapy"},
    "trial_info":        {"zh": "📍 全球 12 项 iPSC 临床试验进行中",
                          "en": "📍 12 iPSC clinical trials ongoing worldwide"},
    "consensus_info":    {"zh": "📖 正在解读：2026 帕金森病无创治疗专家共识",
                          "en": "📖 Reading: 2026 Expert Consensus on Non-invasive PD Therapies"},
    "app_title":         {"zh": "## 🧠 PD科学 - 前沿科研助手", "en": "## 🧠 PD Science — Research Assistant"},
    "app_caption":       {"zh": "基于最新研究进展，解答您关于帕金森病的问题",
                          "en": "Answering your Parkinson's disease questions based on the latest research"},
    "about_text":        {"zh": "> **PD科学助手** 致力于通过AI技术追踪帕金森病(PD)的最新研究进展。",
                          "en": "> **PD Science Assistant** tracks the latest Parkinson's disease (PD) research using AI."},
    "core_features":     {"zh": """**核心功能：**
- 🔍 **多维检索**：整合论文PDF及每日PubMed动态
- 📡 **实时追踪**：每日更新 IF > 5 的PD论文摘要
- 💬 **智能解答**：基于最新证据的深度科研问答

**数据覆盖：**
- 2025-2026 最新研究突破
- 全球顶尖PD实验室动态
- 临床试验进展与学术争议""",
                          "en": """**Core Features:**
- 🔍 **Multi-source Search**: Integrates paper PDFs and daily PubMed updates
- 📡 **Real-time Tracking**: Daily updates of PD papers with IF > 5
- 💬 **AI-Powered Q&A**: In-depth answers grounded in latest evidence

**Data Coverage:**
- 2025–2026 latest research breakthroughs
- Global top PD lab developments
- Clinical trial progress & academic debates"""},
    "disclaimer":        {"zh": "⚠️ **免责声明**：本助手提供的信息仅供科研参考，不构成任何医疗建议。具体诊疗请务必咨询专业医生。",
                          "en": "⚠️ **Disclaimer**: This assistant provides information for research reference only. It does not constitute medical advice. Please consult a qualified physician for diagnosis and treatment."},
    "chat_placeholder":  {"zh": "请输入您关于帕金森病的问题...",
                          "en": "Ask a question about Parkinson's disease..."},
    "searching":         {"zh": "检索相关研究中...", "en": "Searching relevant research..."},
    "analyzing":         {"zh": "分析中...", "en": "Analyzing..."},
    "api_key_error":     {"zh": "请在 .streamlit/secrets.toml 中配置 DEEPSEEK_API_KEY",
                          "en": "Please configure DEEPSEEK_API_KEY in .streamlit/secrets.toml"},
    "indexing":          {"zh": "首次启动，正在构建知识库索引（约需 2-5 分钟，后续启动秒开）...",
                          "en": "First launch: building knowledge base index (~2–5 min; later launches are instant)..."},
    "daily_filter_result":    {"zh": "【每日文献结构化筛选 · 共 {n} 篇】",
                               "en": "【Daily Literature Filter · {n} papers】"},
    "daily_filter_no_match":  {"zh": "近7天收录的 {total} 篇论文中，没有完全匹配「IF>{min_if:.0f}」条件的，以下是全部高分论文供参考：",
                               "en": "Among {total} papers from the last 7 days, none match IF>{min_if:.0f}. All high-impact papers below:"},
}

# ========== 2b. 自定义 CSS ==========
st.markdown("""
    <style>
    /* 整体背景 */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    /* 隐藏工具栏和页脚以保持"固定大方框"感 */
    div[data-testid="stToolbar"] { display: none; }
    footer { visibility: hidden; }

    /* 核心布局容器样式 */
    [data-testid="stHorizontalBlock"] {
        background: rgba(255, 255, 255, 0.25);
        backdrop-filter: blur(15px);
        border-radius: 25px;
        padding: 20px;
        margin-top: -30px;
    }

    /* 滚动容器高度统一 */
    .scroll-content {
        height: 535px;
        overflow: hidden;
        position: relative;
        background: rgba(255, 255, 255, 0.4);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.5);
    }

    .scroll-track {
        display: flex;
        flex-direction: column;
        animation: scrollUpDown 80s linear infinite;
        animation-play-state: paused;
    }

    .scroll-content:hover .scroll-track {
        animation-play-state: running;
    }

    @keyframes scrollUpDown {
        0%, 5% { transform: translateY(0); }
        45%, 55% { transform: translateY(calc(-100% + 480px)); }
        95%, 100% { transform: translateY(0); }
    }

    /* 文献卡片美化 */
    .paper-card {
        background: white;
        margin: 12px;
        padding: 18px;
        border-radius: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border: 1px solid #f0f0f0;
    }
    .paper-title-zh {
        font-weight: 700;
        font-size: 0.95rem;
        line-height: 1.4;
        margin-bottom: 10px;
    }
    .paper-title-zh a {
        text-decoration: none;
        color: #1e3a8a;
    }
    .paper-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        font-size: 0.75rem;
        color: #6b7280;
        border-top: 1px dashed #eee;
        padding-top: 8px;
    }
    .if-badge {
        background: linear-gradient(135deg, #ef4444, #dc2626);
        color: white;
        padding: 1px 8px;
        border-radius: 20px;
        font-weight: 800;
    }
    .journal-tag {
        color: #0369a1;
        font-weight: 600;
    }

    /* 语言切换按钮 */
    div[data-testid="stButton"] button[kind="secondary"] {
        background: rgba(255,255,255,0.85);
        backdrop-filter: blur(8px);
        border: 1px solid #d1d5db;
        border-radius: 8px;
        padding: 4px 14px;
        font-size: 0.8rem;
        font-weight: 700;
        color: #374151;
        transition: all 0.2s;
    }
    div[data-testid="stButton"] button[kind="secondary"]:hover {
        background: #fff;
        border-color: #9ca3af;
    }

    /* 让侧边栏的内容也能对齐 */
    .column-bottom-align {
        margin-top: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# ========== 2c. 语言切换按钮（右上角） ==========
_, _, _, _, lang_col = st.columns([3, 3, 3, 3, 0.6])
with lang_col:
    if st.button(t("lang_switch"), key="lang_toggle", type="secondary"):
        st.session_state.lang = "en" if st.session_state.lang == "zh" else "zh"
        st.rerun()


# ========== 3. 知识库初始化 ==========
@st.cache_resource(show_spinner=False)
def init_knowledge_base():
    """初始化向量知识库（首次运行会下载 embedding 模型并构建索引）。"""
    if not kb.is_indexed():
        with st.spinner(t("indexing")):
            kb.build_index()
    else:
        kb._get_embedding_model()
    return True


# ========== 4. 每日文献结构化筛选 ==========
def _get_daily_context(prompt: str) -> str:
    """检测用户是否在问近期/高分/特定类型文献，若是则从 daily 数据中结构化筛选。"""
    import re

    # 检测是否涉及时间、IF、文章类型
    has_time = bool(re.search(r"近\d+天|最近|今日|昨天|本周|近期|7天|today|recent|latest", prompt, re.I))
    has_if = bool(re.search(r"IF\s*[>≥]\s*\d+|影响因子\s*[>≥]\s*\d+|高分|顶刊|IF\s*\d+", prompt, re.I))
    has_type = bool(re.search(r"综述|review|RCT|临床试验|meta|荟萃|病例报告|队列研究", prompt, re.I))

    if not (has_time or has_if or has_type):
        return ""

    all_papers = daily.get_all_recent_papers(days=1)
    if not all_papers:
        return ""

    # 解析 IF 阈值
    if_match = re.search(r"IF\s*[>≥]\s*(\d+)|影响因子\s*[>≥]\s*(\d+)|IF\s*(\d+)", prompt)
    min_if = 0
    if if_match:
        min_if = float(if_match.group(1) or if_match.group(2) or if_match.group(3))

    # 解析文章类型
    type_keywords = []
    if re.search(r"综述|review", prompt, re.I):
        type_keywords.append("review")
    if re.search(r"RCT|随机对照|临床试验", prompt, re.I):
        type_keywords.append("rct")
    if re.search(r"meta|荟萃", prompt, re.I):
        type_keywords.append("meta")
    if re.search(r"病例报告|case.report", prompt, re.I):
        type_keywords.append("case")

    # 筛选
    filtered = []
    for p in all_papers:
        impact = p.get("impact_factor", 0)
        if min_if > 0 and impact < min_if:
            continue

        if type_keywords:
            text = (p.get("title_en", "") + " " + p.get("abstract", "")).lower()
            if not any(kw in text for kw in type_keywords):
                continue

        filtered.append(p)

    if not filtered:
        return t("daily_filter_no_match", total=len(all_papers), min_if=min_if) + "\n\n" + _format_papers(all_papers[:10])

    return t("daily_filter_result", n=len(filtered)) + "\n\n" + _format_papers(filtered[:15])


def _format_papers(papers: list) -> str:
    """格式化论文列表为文本（始终使用英文标题以保持学术引用准确性）。"""
    lines = []
    for p in papers:
        title = p.get("title_en", "N/A")
        journal = p.get("journal", "")
        impact = p.get("impact_factor", 0)
        pmid = p.get("pmid", "")
        abstract = p.get("abstract", "")[:500]
        lines.append(
            f"【{journal} · IF {impact}】PMID:{pmid}\n"
            f"{title}\n"
            f"{abstract}..."
        )
    return "\n\n---\n\n".join(lines)


# ========== 5. 三栏布局设计 ==========
col_left, col_mid, col_right = st.columns([1.2, 2.0, 0.9])

# ---------- 左栏：滚动文献 ----------
with col_left:
    st.markdown(f"### {t('left_header')}")
    all_recent = daily.get_all_recent_papers(days=7)

    recent_papers = sorted(all_recent, key=lambda x: x.get("impact_factor", 0), reverse=True)[:20]

    if recent_papers:
        papers_html = ""
        for paper in recent_papers:
            # 根据语言选择显示中文或英文标题
            if st.session_state.lang == "zh":
                display_title = paper.get("title_zh") or paper.get("title_en", "N/A")
            else:
                display_title = paper.get("title_en", "N/A")

            if_val = paper.get("impact_factor", 0)
            journal = paper.get("journal", "N/A")
            date = paper.get("date", "")
            pmid = paper.get("pmid", "")
            url = paper.get("url", f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/")

            card = f'<div class="paper-card">' \
                   f'<div class="paper-title-zh">📄 <a href="{url}" target="_blank">{display_title}</a></div>' \
                   f'<div class="paper-meta">' \
                   f'<span class="if-badge">IF {if_val}</span>' \
                   f'<span class="journal-tag">📘 {journal}</span>' \
                   f'<span>📅 {date}</span>' \
                   f'<span style="color:#9ca3af">ID: {pmid}</span>' \
                   f'</div></div>'
            papers_html += card

        full_scroll_html = f'<div class="scroll-content"><div class="scroll-track">{papers_html}</div></div>'
        st.write(full_scroll_html, unsafe_allow_html=True)
    else:
        st.info(t("no_papers"))

    st.divider()
    st.markdown(f"#### {t('aux_features')}")

    func_options = [t("func_hotspot"), t("func_trial"), t("func_consensus")]
    option = st.selectbox(
        "选择功能",
        func_options,
        label_visibility="collapsed"
    )
    if option == t("func_hotspot"):
        st.info(t("hotspot_info"))
    elif option == t("func_trial"):
        st.info(t("trial_info"))
    else:
        st.info(t("consensus_info"))

# ---------- 中栏：对话界面 ----------
with col_mid:
    st.markdown(t("app_title"))
    st.caption(t("app_caption"))

    init_knowledge_base()

    if "analytics_session_id" not in st.session_state:
        st.session_state.analytics_session_id = analytics.start_session()

    if "DEEPSEEK_API_KEY" not in st.secrets:
        st.error(t("api_key_error"))
        st.stop()

    client = OpenAI(
        api_key=st.secrets["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com"
    )

    SYSTEM_PROMPT = """你是帕金森病前沿科研领域的专家助手，也是一位精通帕金森病领域的专业AI。

回答规则：
1. 优先基于用户消息中提供的【参考资料】给出有依据、有出处的专业解答。
2. 当参考资料能够覆盖用户问题时，直接基于资料详细回答。
3. 当参考资料部分覆盖用户问题时，先基于资料回答已有的部分，再补充你的专业知识，补充部分需注明来源。
4. 当参考资料完全无法覆盖用户问题时：
   - 先说一句："以下内容参考资料里面目前没有，由AI基于自身知识回答："
   - 然后给出你基于自身知识的完整专业回答（不限字数，充分解答）
5. 你是一位经验丰富的神经科学专家，应该提供有深度、有价值的回答，而不是敷衍了事。"""

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    chat_container = st.container(height=640, border=False)

    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] != "system":
                display_text = msg.get("display", msg["content"])
                with st.chat_message(msg["role"]):
                    st.markdown(display_text)

    if prompt := st.chat_input(t("chat_placeholder")):
        with st.spinner(t("searching")):
            contexts = kb.query(prompt, n_results=10)

        daily_context = _get_daily_context(prompt)
        if daily_context:
            contexts = [daily_context] + contexts

        context_text = "\n\n---\n\n".join(contexts) if contexts else "暂无直接相关参考资料。"

        analytics.track_query(
            session_id=st.session_state.analytics_session_id,
            question=prompt,
            n_results=len(contexts),
            daily_context_used=bool(daily_context),
        )

        augmented_prompt = f"【参考资料】\n\n{context_text}\n\n【用户问题】\n{prompt}"
        st.session_state.messages.append({
            "role": "user",
            "content": augmented_prompt,
            "display": prompt
        })

        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner(t("analyzing")):
                    try:
                        messages_to_send = st.session_state.messages[-11:]
                        if messages_to_send[0]["role"] == "assistant":
                            messages_to_send.insert(0, st.session_state.messages[0])
                        response = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=messages_to_send,
                            stream=True
                        )
                        full_response = st.write_stream(response)
                        st.session_state.messages.append({"role": "assistant", "content": full_response})
                    except Exception as e:
                        st.error(f"调用出错: {e}")

        st.rerun()

# ---------- 右栏：项目信息 ----------
with col_right:
    if os.path.exists("images/PD-science-logo.png"):
        st.image("images/PD-science-logo.png", use_container_width=True)

    st.markdown(t("about_text"))

    st.markdown(f"""
    <div style="font-size: 0.9rem; color: #4b5563; line-height: 1;">

    {t('core_features')}

    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.caption(t("disclaimer"))
