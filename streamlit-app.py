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

# 自定义 CSS
st.markdown("""
    <style>
    /* 整体背景 */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* 隐藏工具栏和页脚以保持“固定大方框”感 */
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
    
    /* 让侧边栏的内容也能对齐 */
    .column-bottom-align {
        margin-top: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# ========== 2. 知识库初始化 ==========
@st.cache_resource(show_spinner=False)
def init_knowledge_base():
    """初始化向量知识库（首次运行会下载 embedding 模型并构建索引）。"""
    if not kb.is_indexed():
        with st.spinner("首次启动，正在构建知识库索引（约需 2-5 分钟，后续启动秒开）..."):
            kb.build_index()
    else:
        # 静默加载模型
        kb._get_embedding_model()
    return True

# ========== 2b. 每日文献结构化筛选 ==========
def _get_daily_context(prompt: str) -> str:
    """检测用户是否在问近期/高分/特定类型文献，若是则从 daily 数据中结构化筛选。"""
    import re

    # 检测是否涉及时间、IF、文章类型
    has_time = bool(re.search(r"近\d+天|最近|今日|昨天|本周|近期|7天|today|recent|latest", prompt, re.I))
    has_if = bool(re.search(r"IF\s*[>≥]\s*\d+|影响因子\s*[>≥]\s*\d+|高分|顶刊|IF\s*\d+", prompt, re.I))
    has_type = bool(re.search(r"综述|review|RCT|临床试验|meta|荟萃|病例报告|队列研究", prompt, re.I))

    if not (has_time or has_if or has_type):
        return ""  # 普通问题，不做结构化筛选

    all_papers = daily.get_all_recent_papers(days=1)  # 只取最新一天
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
        return f"【每日文献筛选结果】\n近7天收录的 {len(all_papers)} 篇论文中，没有完全匹配「IF>{min_if:.0f}」条件的，以下是全部高分论文供参考：\n\n" + _format_papers(all_papers[:10])

    return f"【每日文献结构化筛选 · 共 {len(filtered)} 篇】\n\n" + _format_papers(filtered[:15])


def _format_papers(papers: list) -> str:
    """格式化论文列表为文本。"""
    lines = []
    for p in papers:
        title = p.get("title_zh") or p.get("title_en", "N/A")
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


# ========== 3. 三栏布局设计 ==========
col_left, col_mid, col_right = st.columns([1.2, 2.0, 0.9])

# ---------- 左栏：滚动文献 ----------
with col_left:
    st.markdown("### 📡 近7天高分文献动态")
    # 获取近7天所有高分文献
    all_recent = daily.get_all_recent_papers(days=7)
    
    # 按照影响因子排序并取前 20 名
    recent_papers = sorted(all_recent, key=lambda x: x.get("impact_factor", 0), reverse=True)[:20]
    
    if recent_papers:
        # 构建纯 HTML 字符串
        papers_html = ""
        for paper in recent_papers:
            title_zh = paper.get("title_zh") or paper.get("title_en", "N/A")
            if_val = paper.get("impact_factor", 0)
            journal = paper.get("journal", "N/A")
            date = paper.get("date", "")
            pmid = paper.get("pmid", "")
            url = paper.get("url", f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/")
            
            # 使用单行或紧凑格式避免 markdown 解析干扰
            card = f'<div class="paper-card">' \
                   f'<div class="paper-title-zh">📄 <a href="{url}" target="_blank">{title_zh}</a></div>' \
                   f'<div class="paper-meta">' \
                   f'<span class="if-badge">IF {if_val}</span>' \
                   f'<span class="journal-tag">📘 {journal}</span>' \
                   f'<span>📅 {date}</span>' \
                   f'<span style="color:#9ca3af">ID: {pmid}</span>' \
                   f'</div></div>'
            papers_html += card
        
        full_scroll_html = f'<div class="scroll-content"><div class="scroll-track">{papers_html}</div></div>'
        # 使用 st.write(..., unsafe_allow_html=True) 有时比 st.markdown 更稳定
        st.write(full_scroll_html, unsafe_allow_html=True)
    else:
        st.info("近7天暂无符合条件的文献更新。")

    st.divider()
    st.markdown("#### 🛠️ 辅助功能")
    option = st.selectbox(
        "选择功能",
        ["📈 科研热点趋势", "🗺️ 临床试验地图", "📖 专家共识解读"],
        label_visibility="collapsed"
    )
    if "热点" in option:
        st.info("🔥 当前热点：α-突触核蛋白、FAM171A2、iPSC 疗法")
    elif "地图" in option:
        st.info("📍 全球 12 项 iPSC 临床试验进行中")
    else:
        st.info("📖 正在解读：2026 帕金森病无创治疗专家共识")

# ---------- 中栏：对话界面 ----------
with col_mid:
    st.markdown("## 🧠 PD科学 - 前沿科研助手")
    st.caption("基于最新研究进展，解答您关于帕金森病的问题")

    # 初始化知识库
    init_knowledge_base()

    # 初始化 session 追踪
    if "analytics_session_id" not in st.session_state:
        st.session_state.analytics_session_id = analytics.start_session()

    # 检查 API Key
    if "DEEPSEEK_API_KEY" not in st.secrets:
        st.error("请在 .streamlit/secrets.toml 中配置 DEEPSEEK_API_KEY")
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

    # 创建对话显示容器（固定高度，自动滚动）
    chat_container = st.container(height=640, border=False)

    # 在容器中显示历史消息
    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] != "system":
                display_text = msg.get("display", msg["content"])
                with st.chat_message(msg["role"]):
                    st.markdown(display_text)

    # 提问框放在最下方
    if prompt := st.chat_input("请输入您关于帕金森病的问题..."):
        # 检索相关知识块
        with st.spinner("检索相关研究中..."):
            contexts = kb.query(prompt, n_results=10)

        # 检测是否需要结构化筛选每日文献（时间 / IF / 文章类型）
        daily_context = _get_daily_context(prompt)
        if daily_context:
            contexts = [daily_context] + contexts

        context_text = "\n\n---\n\n".join(contexts) if contexts else "暂无直接相关参考资料。"

        # 埋点：记录查询事件
        analytics.track_query(
            session_id=st.session_state.analytics_session_id,
            question=prompt,
            n_results=len(contexts),
            daily_context_used=bool(daily_context),
        )

        # 用户消息（附检索结果，仅发送给 API，界面显示原始问题）
        augmented_prompt = f"【参考资料】\n\n{context_text}\n\n【用户问题】\n{prompt}"
        st.session_state.messages.append({
            "role": "user",
            "content": augmented_prompt,
            "display": prompt  # 界面只显示原始问题
        })

        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

        # 助手回答
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("分析中..."):
                    try:
                        # 只发送最近 N 轮对话 + system prompt，避免上下文过长
                        messages_to_send = st.session_state.messages[-11:]  # system + 5轮问答
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

        # 强制刷新以更新界面（Streamlit 惯用手法确保输入框状态同步）
        st.rerun()

# ---------- 右栏：项目信息 ----------
with col_right:
    # 恢复 Logo 原始展示比例 (使用 width='stretch' 让它填充列宽)
    if os.path.exists("images/PD-science-logo.png"):
        st.image("images/PD-science-logo.png", use_container_width=True)

    # st.divider()
    # st.markdown("### ℹ️ 关于本助手")
    st.markdown("> **PD科学助手** 致力于通过AI技术追踪帕金森病(PD)的最新研究进展。")
    
    st.markdown("""
    <div style="font-size: 0.9rem; color: #4b5563; line-height: 1;">

    **核心功能：**
    - 🔍 **多维检索**：整合论文PDF及每日PubMed动态
    - 📡 **实时追踪**：每日更新 IF > 5 的PD论文摘要
    - 💬 **智能解答**：基于最新证据的深度科研问答

    **数据覆盖：**
    - 2025-2026 最新研究突破
    - 全球顶尖PD实验室动态
    - 临床试验进展与学术争议

    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.caption("⚠️ **免责声明**：本助手提供的信息仅供科研参考，不构成任何医疗建议。具体诊疗请务必咨询专业医生。")

    # ---------- 管理面板：使用统计 ----------
    with st.expander("📊 管理面板", expanded=False):
        stats = analytics.get_stats_summary()

        # 第一行：4 个核心指标
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("今日用户 (DAU)", stats["dau"])
        with c2:
            st.metric("7日用户 (WAU)", stats["wau"])
        with c3:
            st.metric("今日查询", stats["daily_queries"])
        with c4:
            st.metric("7日查询", stats["weekly_queries"])

        # 第二行：检索质量 + 用户粘性
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("检索命中率", f"{stats['search_hit_rate']}%")
        with c2:
            st.metric("平均查询/会话", stats["avg_q_per_session"])
        with c3:
            st.metric("累计总用户", stats["total_users_all_time"])
        with c4:
            st.metric("累计总查询", stats["total_queries_all_time"])

        # 第三行：用户使用次数排行
        if stats["top_users"]:
            st.caption("👥 用户使用次数排行 (Top 10)")
            import pandas as pd
            df = pd.DataFrame(stats["top_users"])
            df.columns = ["匿名ID", "累计查询", "最近IP", "首次访问", "最近访问"]
            df["匿名ID"] = df["匿名ID"].str[:8]
            st.dataframe(df, use_container_width=True, hide_index=True)

        # 第四行：最近活跃 IP
        if stats["recent_ips"]:
            st.caption("📍 近7天活跃用户地址")
            ip_list = "\n".join(
                f"- `{r['ip']}`" for r in stats["recent_ips"]
            )
            st.markdown(ip_list)
