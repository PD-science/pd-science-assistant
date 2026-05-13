import re
import unicodedata
from pathlib import Path
import fitz

PDF_DIR = Path('.')

TYPE_KEYWORDS = [
    ('RCT', ['randomized', 'randomised', 'double-blind', 'placebo', 'randomized controlled trial', 'randomised controlled trial', 'phase 3', 'phase 2', 'randomly assigned', 'sham stimulation', 'sham surgery', 'sham control']),
    ('review', ['systematic review', 'meta-analysis', 'meta analysis', 'review', 'overview', 'narrative review', 'primer', 'perspective', 'update', 'state of the art', 'scoping review']),
    ('cohort', ['cohort', 'prospective', 'longitudinal', 'follow-up study', 'observational study', 'registry']),
    ('case-control', ['case-control', 'case control']),
    ('guideline', ['guideline', 'clinical diagnostic criteria', 'practice parameter', 'statement', 'guidance', 'recommendations', 'consensus statement', 'diagnostic criteria']),
    ('consensus', ['consensus', 'task force', 'expert opinion']),
    ('basic research', ['mechanism', 'pathophysiology', 'animal model', 'in vitro', 'in vivo', 'cell line', 'mice', 'rat', 'model', 'proteomic', 'genetic', 'biomarker', 'molecular', 'immunohistochemistry', 'western blot', 'knockout', 'transgenic', 'cryo-em', 'cryo em', 'structural basis', 'crystal structure']),
]

TYPE_MAP = {
    'guideline': '指南',
    'review': '系统综述',
    'RCT': '随机对照试验',
    'cohort': '队列研究',
    'case-control': '病例对照',
    'basic research': '基础研究',
    'consensus': '专家共识',
}

GRADE_DEFAULT = {
    'guideline': '1a',
    'review': '1a',
    'RCT': '1b',
    'cohort': '2b',
    'case-control': '2b',
    'basic research': '4',
    'consensus': '4',
}

TAG_KEYWORDS = {
    'drug:levodopa': ['levodopa', 'l-dopa', 'dopa'],
    'drug:rasagiline': ['rasagiline'],
    'drug:amantadine': ['amantadine'],
    'drug:exenatide': ['exenatide'],
    'drug:glp-1': ['glp-1', 'glp1', 'glucagon-like peptide'],
    'symptom:dyskinesia': ['dyskinesia'],
    'symptom:freezing': ['freezing', 'gait freezing'],
    'symptom:tremor': ['tremor'],
    'symptom:bradykinesia': ['bradykinesia'],
    'symptom:rigidity': ['rigidity'],
    'outcome:motor': ['motor', 'movement', 'UPDRS', 'MDS-UPDRS', 'motor function'],
    'outcome:cognitive': ['cognitive', 'memory', 'dementia', 'PD-MCI', 'PDD'],
    'outcome:quality-of-life': ['quality of life', 'qol', 'quality-of-life', 'well-being'],
    'outcome:adverse-event': ['adverse event', 'side effect', 'safety', 'serious adverse'],
    'topic:drug-therapy': ['levodopa', 'dopamine', 'drug', 'therapy', 'treatment', 'medication', 'pharmacological'],
    'topic:biomarker': ['biomarker', 'marker', 'imaging', 'plasma', 'MRI', 'PET', 'SPECT', 'DAT'],
    'topic:genetics': ['genetic', 'gene', 'genome', 'gwas', 'mutation', 'genomic', 'variant', 'locus'],
    'topic:non-motor': ['cognitive', 'autonomic', 'pain', 'sleep', 'non-motor', 'nonmotor'],
    'topic:rehabilitation': ['exercise', 'rehabilitation', 'physical therapy', 'physiotherapy', 'movement disorder'],
    'topic:DBS': ['deep brain stimulation', 'DBS', 'subthalamic nucleus', 'STN', 'globus pallidus', 'GPi'],
    'topic:ultrasound': ['focused ultrasound', 'MRgFUS', 'transcranial ultrasound'],
    'topic:gene-therapy': ['gene therapy', 'AAV', 'viral vector', 'gene delivery'],
    'topic:alpha-synuclein': ['alpha-synuclein', 'α-synuclein', 'synuclein', 'α-syn', 'a-syn'],
    'topic:mitochondria': ['mitochondria', 'mitochondrial', 'oxidative stress', 'complex I'],
    'topic:neuroinflammation': ['inflammation', 'immune', 'microglia', 'astrocyte', 'neuroinflam'],
    'topic:gut-brain': ['gut', 'microbiota', 'microbiome', 'enteric', 'gut-brain'],
    'topic:diagnosis': ['diagnosis', 'diagnostic', 'prodromal', 'early detection'],
    'mechanism:dopamine': ['dopamine', 'dopaminergic', 'nigrostriatal'],
    'mechanism:alpha-synuclein': ['alpha-synuclein', 'α-synuclein', 'synuclein', 'α-syn', 'a-syn'],
    'mechanism:inflammation': ['inflammation', 'immune', 'microglia', 'neuroinflammation'],
    'mechanism:mitochondria': ['mitochondria', 'mitochondrial', 'oxidative stress'],
    'mechanism:autophagy': ['autophagy', 'lysosome', 'proteasome', 'clearance', 'degradation'],
    'mechanism:genetics': ['genetic', 'mutation', 'gene', 'lrrk2', 'parkin', 'pink1', 'dj-1', 'gba'],
}


def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()


def get_pdf_metadata(doc):
    """Extract metadata from PDF info dictionary."""
    meta = doc.metadata or {}
    doi = meta.get('doi', '') or ''
    title = meta.get('title', '') or ''
    return doi, title


def extract_text_sorted(pdf_path, max_pages=None):
    """Extract text with position-based sorting for multi-column PDFs."""
    doc = fitz.open(pdf_path)
    pages = min(len(doc), max_pages) if max_pages else len(doc)
    all_text = []
    for i in range(pages):
        page = doc.load_page(i)
        blocks = page.get_text("blocks")
        blocks_sorted = sorted(blocks, key=lambda b: (round(b[1] / 20) * 20, b[0]))
        page_text = '\n'.join(b[4].strip() for b in blocks_sorted if b[6] == 0 and b[4].strip())
        all_text.append(page_text)
    doc.close()
    return '\n'.join(all_text)


def extract_first_page_font_info(pdf_path):
    """Extract text from first page with font size info for each span."""
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    dict_data = page.get_text("dict")
    doc.close()

    spans = []
    for block in dict_data["blocks"]:
        if "lines" in block:
            for line in block["lines"]:
                line_spans = []
                for span in line["spans"]:
                    line_spans.append({
                        'text': span['text'].strip(),
                        'size': round(span['size'], 1),
                        'font': span['font'],
                        'flags': span.get('flags', 0),
                        'bbox': line['bbox'],
                    })
                if line_spans:
                    spans.append(line_spans)
    return spans


def extract_title_from_pdf(pdf_path):
    """Extract title from first page using font size heuristics."""
    spans = extract_first_page_font_info(pdf_path)
    if not spans:
        return ''

    # Find the largest font size on the first page, excluding headers/footers
    all_sizes = []
    for line_spans in spans:
        for s in line_spans:
            if s['text']:
                all_sizes.append(s['size'])

    if not all_sizes:
        return ''

    # Title is typically the largest or near-largest font
    max_size = max(all_sizes)

    # Collect lines with font size close to max (title often spans multiple lines)
    title_lines = []
    for line_spans in spans:
        line_text = ' '.join(s['text'] for s in line_spans if s['text'])
        line_max_size = max((s['size'] for s in line_spans if s['text']), default=0)
        # Title is large font and not a header/footer
        if line_max_size >= max_size - 1.0 and line_max_size >= 13:
            # Filter out obvious non-title content
            if not re.search(r'\b(doi|www\.|http|download|journal|volume|issue|copyright|all rights|university|institute|department)\b', line_text, re.I):
                title_lines.append(line_text)

    title = ' '.join(title_lines)
    if title and len(title) > 10:
        return clean_text(title)

    # Fallback: try to get title from PDF metadata
    doc = fitz.open(pdf_path)
    _, meta_title = get_pdf_metadata(doc)
    doc.close()
    if meta_title:
        return clean_text(meta_title)

    return ''


def extract_authors_from_pdf(pdf_path):
    """Extract authors from first page using font size and position heuristics."""
    spans = extract_first_page_font_info(pdf_path)
    if not spans:
        return ''

    # Find title position (largest font) to know where authors start
    title_end_idx = 0
    max_size = max((s['size'] for line_spans in spans for s in line_spans if s['text']), default=0)
    for i, line_spans in enumerate(spans):
        line_max = max((s['size'] for s in line_spans if s['text']), default=0)
        if line_max >= max_size - 1.0:
            title_end_idx = i + 1

    # Determine typical body font size (most common font size after authors section)
    # to distinguish author lines from body text when they share the same size
    body_sizes = []
    for i in range(title_end_idx, min(title_end_idx + 30, len(spans))):
        for s in spans[i]:
            if s['text'] and s['size'] >= 7:
                body_sizes.append(s['size'])
    # Body text is usually the most common font size in the main text area
    body_size = max(set(body_sizes), key=body_sizes.count) if body_sizes else 8

    # Collect lines after title that look like author lines
    author_candidates = []
    for i in range(title_end_idx, min(title_end_idx + 25, len(spans))):
        line_spans = spans[i]
        line_text = ' '.join(s['text'] for s in line_spans if s['text'])
        line_sizes = [s['size'] for s in line_spans if s['text']]
        if not line_text or not line_sizes:
            continue
        avg_size = sum(line_sizes) / len(line_sizes)

        # Detect superscript affiliation markers: very small numbers interspersed with larger text
        has_superscripts = any(s['size'] < body_size - 1.2 for s in line_spans if s['text'] and s['size'] > 0)

        name_count = len(re.findall(r'[A-Z][a-z]{2,}', line_text))

        # Author line detection:
        # 1. Contains superscript numbers (affiliations) - strong signal
        # 2. Multiple names separated by commas
        # 3. Not a department/institution line
        is_metadata_line = bool(re.search(
            r'\b(doi|www\.|http|download|copyright|all rights|correspond|correspondence|'
            r'equal contribut|these authors|email|e-mail|©|supplementary|supplemental|'
            r'conflict|competing interest|funding|acknowledg|received|accepted|published|'
            r'abstract|summary|introduction|background|keywords?|key words?)\b',
            line_text, re.I
        ))
        is_affiliation_line = bool(re.search(
            r'\b(department|university|hospital|institute|school|college|laboratory|lab|'
            r'centre|center|clinic|academy|medical center|medical centre|faculty)\b',
            line_text, re.I
        ))

        # Author lines: have multiple names, often with superscript affiliation numbers
        has_author_pattern = bool(re.search(
            r'[A-Z][a-z]+\s+[A-Z][a-z]+.*\d+.*,|'
            r'[A-Z][a-z]+\s+[A-Z]\.\s*[A-Z]\.|'
            r'[A-Z][a-z\-]+\s+\d+[,;]',
            line_text
        ))

        is_author_line = (
            not is_metadata_line and
            not is_affiliation_line and
            name_count >= 2 and
            (
                has_superscripts or
                has_author_pattern or
                (avg_size < body_size and avg_size >= 7.5) or
                (i <= title_end_idx + 3 and name_count >= 4)  # Lines immediately after title
            )
        )

        if is_author_line:
            author_candidates.append(line_text)
        elif author_candidates:
            # Stop conditions after we've found some author lines
            if is_affiliation_line or is_metadata_line:
                break
            # Continue for multi-line author blocks with supercripts
            if has_superscripts and name_count >= 2:
                author_candidates.append(line_text)
                continue
            # Stop on long continuous text (body paragraph)
            if len(line_text) > 80 and name_count < 3 and not has_superscripts:
                break

    if not author_candidates:
        return ''

    authors_text = ' '.join(author_candidates)
    # Remove affiliation superscript numbers from the text
    authors_text = re.sub(r'\s+\d{1,3}(?=\s|,|$)', '', authors_text)
    authors_text = re.sub(r'[,;]\s*\d{1,3}\s*', ', ', authors_text)
    # Clean up extra whitespace
    authors_text = re.sub(r'\s+', ' ', authors_text)
    # Remove trailing numbers/symbols
    authors_text = re.sub(r'[\d,\s*†‡§¶#&]+$', '', authors_text)
    # Clean up common prefixes
    authors_text = re.sub(r'^\s*(authors?|by|edited by)\s*[:\-]?\s*', '', authors_text, flags=re.I)

    return clean_text(authors_text)[:500]


def extract_journal_from_pdf(pdf_path):
    """Extract journal name from first page."""
    spans = extract_first_page_font_info(pdf_path)
    if not spans:
        return ''

    # Check first few lines for journal name patterns
    first_page_text = '\n'.join(
        ' '.join(s['text'] for s in ls if s['text'])
        for ls in spans[:20]
    )

    # Known journal patterns
    journal_patterns = [
        r'(N Engl J Med|New England Journal of Medicine)',
        r'(The Lancet|Lancet\s+(?:Neurology|Neurol))',
        r'(Nature\s*(?:Reviews?\s*)?(?:Neurology|Medicine|Neuroscience|Communications)?)',
        r'(Science\s*(?:Translational Medicine)?)',
        r'(Brain)',
        r'(Neurology)',
        r'(Movement Disorders?)',
        r'(Annals of Neurology)',
        r'(JAMA\s*(?:Neurology)?)',
        r'(Journal of\s+(?:Neurology|Neuroscience|Parkinson))',
        r'(npj\s+Parkinson)',
        r'(Cell)',
        r'(Neuron)',
        r'(PNAS|Proceedings of the National Academy)',
        r'(BMJ)',
        r'(European Journal of Neurology)',
        r'(Parkinsonism[\s&]+Related Disorders)',
    ]
    for pat in journal_patterns:
        m = re.search(pat, first_page_text, re.I)
        if m:
            return clean_text(m.group(1))

    # Try from PDF metadata
    doc = fitz.open(pdf_path)
    meta = doc.metadata or {}
    doc.close()
    journal = meta.get('journal', '') or meta.get('subject', '') or ''
    if journal and len(journal) < 100:
        return clean_text(journal)

    return ''


def extract_doi(text, pdf_path=''):
    """Extract DOI with multiple fallback strategies."""
    # Strategy 1: DOI URL
    m = re.search(r'https?://doi\.org/\s*([^\s\n]{3,})', text, re.I)
    if m:
        doi = re.sub(r'\s+', '', m.group(1))
        # Remove trailing punctuation that's unlikely part of DOI
        doi = re.sub(r'[.,;:]+$', '', doi)
        if doi.startswith('10.'):
            return doi

    # Strategy 2: "DOI:" prefix
    m = re.search(r'DOI[:\s]+\s*(10\.\d{4,}/[^\s\n]{3,})', text, re.I)
    if m:
        doi = re.sub(r'\s+', '', m.group(1))
        doi = re.sub(r'[.,;:]+$', '', doi)
        return doi

    # Strategy 3: Generic DOI pattern
    m = re.search(r'(10\.\d{4,}/[^\s]{3,})', text)
    if m:
        doi = m.group(1)
        doi = re.sub(r'[.,;:]+$', '', doi)
        # Filter false positives
        if not re.match(r'^\d+(\.\d+)+$', doi[:20]):
            return doi

    # Strategy 4: From PDF metadata
    if pdf_path:
        doc = fitz.open(pdf_path)
        meta = doc.metadata or {}
        doc.close()
        doi = meta.get('doi', '') or ''
        if doi and doi.startswith('10.'):
            return clean_text(doi)

    return ''


def extract_pmid(text):
    """Extract PubMed ID."""
    m = re.search(r'PMID[:\s]*(\d{7,8})', text, re.I)
    if m:
        return m.group(1)
    # PMC ID
    m = re.search(r'PMCID[:\s]*(PMC\d+)', text, re.I)
    if m:
        return m.group(1)
    return ''


def extract_abstract(text):
    """Extract abstract section with multiple strategies."""
    # Normalize: collapse broken labels (e.g., "ABSTR ACT" -> "ABSTRACT")
    text_normalized = re.sub(r'(ABSTR)\s+(ACT)', r'\1\2', text)
    text_normalized = re.sub(r'(abstr)\s+(act)', r'\1\2', text_normalized, flags=re.I)

    # Sections that are PART OF a structured abstract (NEJM, Lancet, etc.)
    structured_abstract_sections = [
        'BACKGROUND', 'METHODS?', 'FINDINGS?', 'RESULTS?',
        'CONCLUSIONS?', 'INTERPRETATION',
    ]
    # Sections that END the abstract / start the main article
    abstract_end_sections = [
        'INTRODUCTION', 'DISCUSSION', 'ACKNOWLEDGMENTS?', 'REFERENCES?',
        'FUNDING', 'COMPETING\\s+INTERESTS', 'AUTHOR\\s+CONTRIBUTIONS?',
        'ABBREVIATIONS?', 'HIGHLIGHTS?', 'KEYWORDS?', 'KEY\\s+WORDS?',
        'TABLE\\s+\\d+', 'FIGURE\\s+\\d+',
        'CORRESPONDENCE', 'CORRESPONDING\\s+AUTHOR',
        'SUPPLEMENTARY', 'SUPPLEMENTAL',
        'https?://doi\\.org', 'doi[:\s]',
        '\\(C\\)|Copyright|All\\s+Rights\\s+Reserved',
    ]
    end_pattern = re.compile(
        r'\n\s*(?:' + '|'.join(abstract_end_sections) + r')\b',
        re.I
    )

    # Strategy 1: Look for Abstract/Summary heading
    for label in ['abstract', 'summary']:
        for match in re.finditer(rf'(?:^|\n)\s*{label}\s*\n+', text_normalized, re.I):
            idx = match.end()
            # Use the match position from text_normalized, but map to original text
            # Normalization only removes spaces, so positions differ by a few chars
            sub = text[idx: idx + 5000]
            parts = end_pattern.split(sub, 1)
            abstract = clean_text(parts[0])
            if len(abstract) > 100:
                return abstract

    # Strategy 2: Look for ABSTRACT in uppercase (matches normalized broken text)
    m = re.search(r'(?:^|\n)(ABSTRACT)\s*\n+', text_normalized)
    if m:
        idx = m.end()
        sub = text[idx: idx + 5000]
        parts = end_pattern.split(sub, 1)
        abstract = clean_text(parts[0])
        if len(abstract) > 100:
            return abstract

    # Strategy 3: For structured abstracts where the label wasn't detected
    # but the abstract content starts with BACKGROUND (NEJM style)
    m = re.search(r'(?:^|\n)\s*(BACKGROUND)\s*\n+', text, re.I)
    if m:
        idx = m.start()
        sub = text[idx: idx + 5000]
        parts = end_pattern.split(sub, 1)
        abstract = clean_text(parts[0])
        if len(abstract) > 100 and re.search(r'\b(METHODS?|RESULTS?)\b', abstract, re.I):
            return abstract

    # Strategy 4: For papers with ABSTRACT in text body (not as a clear heading)
    m = re.search(r'(?:^|\n)(?:ABSTRACT|Abstract)\s*[:.\-—–]\s*', text)
    if m:
        idx = m.end()
        sub = text[idx: idx + 5000]
        parts = end_pattern.split(sub, 1)
        abstract = clean_text(parts[0])
        if len(abstract) > 100:
            return abstract

    # Strategy 5: For papers without labeled abstract (e.g., Science),
    # take first substantial paragraphs after title/authors
    paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 200]
    for p in paragraphs[:5]:
        if re.search(r'\b(fig\.|figure|table|supplementary|supplemental|'
                      r'et al\.\s*\d|references?|acknowledgments?)', p[:80], re.I):
            continue
        if len(p) > 200:
            return clean_text(p)

    return ''


def extract_keywords(text):
    """Extract keywords with multiple patterns."""
    patterns = [
        r'(?:^|\n)\s*keywords?\s*[:\-—–]\s*(.+?)(?:\n\s*\n|\n\s*[A-Z][A-Z\s]{2,30}\n)',
        r'(?:^|\n)\s*key\s+words?\s*[:\-—–]\s*(.+?)(?:\n\s*\n|\n\s*[A-Z][A-Z\s]{2,30}\n)',
        r'(?:^|\n)\s*KEYWORDS?\s*[:\-—–]\s*(.+?)(?:\n\s*\n)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I | re.S)
        if m:
            raw = m.group(1).strip()
            kws = [w.strip(' .;•·-–—\'\"') for w in re.split(r'[;,•·\n]', raw) if w.strip() and len(w.strip()) > 2]
            if kws:
                return kws[:15]
    return []


def detect_type(text, title):
    """Detect study type from text and title."""
    combined = f"{title}\n{text}".lower()
    scores = {}
    for key, patterns in TYPE_KEYWORDS:
        score = 0
        for pat in patterns:
            if pat in combined:
                score += 1
        if score > 0:
            scores[key] = score

    if not scores:
        return 'basic research'

    # Return type with most matching keywords
    return max(scores, key=scores.get)


def detect_tags(text):
    """Detect tags from standardized vocabulary."""
    tags = set()
    text_l = text.lower()
    for tag, patterns in TAG_KEYWORDS.items():
        for p in patterns:
            if p.lower() in text_l:
                tags.add(tag)
                break
    if not any(t.startswith('type:') for t in tags):
        tags.add('type:basic')
    return sorted(tags)


def extract_section(text, heading):
    """Extract content under a given heading."""
    pattern = re.compile(
        rf'(?:^|\n)\s*{re.escape(heading)}\s*\n+(.*?)(?=\n\s*[A-Z][A-Z\s/&]{{3,40}}\n|\n\s*\n\s*[A-Z][A-Z\s/&]{{3,40}}\n|$)',
        re.I | re.S
    )
    match = pattern.search(text)
    if match:
        return clean_text(match.group(1))
    return ''


def first_sentence(text):
    """Get first complete sentence."""
    text = clean_text(text)
    match = re.match(r'(.+?[。\.\!\?])\s', text)
    if match:
        return match.group(1)
    return text[:200]


def split_sentences(text, limit=2):
    """Get first N sentences."""
    text = clean_text(text)
    sentences = re.split(r'(?<=[。\.\!\?])\s+', text)
    return ' '.join(sentences[:limit])


def infer_background_gap_objective(abstract, title='', doc_type=''):
    """Infer background, knowledge gap, and objective from abstract."""
    if not abstract:
        return '', '', ''

    # Background: first 2 sentences
    background = split_sentences(abstract, 2)

    # Try to find explicit objective/aim
    objective = ''
    aim_patterns = [
        r'([^.。]*(?:aim|objective|purpose|goal|intend|sought|designed)[^.。]*[.。])',
        r'([^.。]*(?:we\s+(?:evaluated|assessed|examined|investigated|studied|tested|compared|analyzed|performed|conducted|report|present|describe|sought|aim|hypothesize))[^.。]*[.。])',
        r'([^.。]*(?:this\s+(?:study|trial|review|report|paper|article|work|analysis|meta-analysis)\s+(?:aim|evaluat|assess|examin|investigat|compare|analyz|report|present|describ))[^.。]*[.。])',
    ]
    for pat in aim_patterns:
        match = re.search(pat, abstract, re.I)
        if match:
            objective = clean_text(match.group(0))
            break

    if not objective:
        if doc_type == 'review' and title:
            objective = f'To summarize and critically evaluate current evidence on {title}.'
        else:
            objective = split_sentences(abstract, 1)

    # Try to find knowledge gap
    gap = ''
    gap_patterns = [
        r'([^.。]*(?:lack|unclear|remain|unknown|limited|poorly understood|elusive|controversial|not fully|not well|not yet|unresolved|incompletely)[^.。]*[.。])',
    ]
    for pat in gap_patterns:
        match = re.search(pat, abstract, re.I)
        if match:
            gap = clean_text(match.group(0))
            break

    if not gap:
        gap = '当前研究对该领域核心机制或治疗策略的理解仍不充分，需进一步探索。'

    return background, gap, objective


def infer_methods_results_conclusions(abstract, doc_type=''):
    """Infer methods, results, and conclusions from abstract."""
    if not abstract:
        return '', '', ''

    # Methods
    methods = ''
    if doc_type == 'review':
        methods = 'Systematic literature search and synthesis of published evidence. Review methodology follows standard practices for evidence synthesis in the field.'
    else:
        methods_keywords = [
            r'([^.。]*\b(?:randomi[sz]ed|enroll|recruit|\d+\s*(?:patient|subject|participant|case|individual)|double.?blind|placebo.?controlled|prospective|retrospective|cohort|case.?control|trial|RCT)\b[^.。]*[.。])',
        ]
        for pat in methods_keywords:
            match = re.search(pat, abstract, re.I)
            if match:
                methods = clean_text(match.group(0))
                break
        if not methods:
            methods = split_sentences(abstract, 2)

    # Results
    results = ''
    result_indicators = [
        r'\b(?:result|find|show|demonstrat|reveal|indicat|observ|report|suggest|identif|confirm|detect|discover|uncover|correlat|associat|predict|lead to|linked to|related to|reduced|increased|improved|decreased|significant)\b'
    ]
    result_sentences = []
    sentences = re.split(r'(?<=[。\.\!\?])\s+', abstract)
    for s in sentences:
        if re.search(result_indicators[0], s, re.I):
            result_sentences.append(s)
    if result_sentences:
        results = ' '.join(result_sentences[:3])
    else:
        results = split_sentences(abstract, 2)

    # Conclusions
    conclusions = ''
    conclusion_indicators = [
        r'\b(?:conclusion|conclude|finding|interpretation|implication|significance|overall|in summary|taken together|these (?:data|results|findings)|our (?:data|results|findings|study))\b'
    ]
    sentences = re.split(r'(?<=[。\.\!\?])\s+', abstract)
    for s in reversed(sentences):
        if re.search(conclusion_indicators[0], s, re.I) or s == sentences[-1]:
            conclusions = clean_text(s)
            break
    if not conclusions:
        conclusions = sentences[-1] if sentences else ''

    return methods, results, conclusions


def extract_core_value(abstract, title, conclusions=''):
    """Extract a one-sentence core value summary."""
    if conclusions and len(conclusions) > 30:
        return conclusions[:300]
    if abstract:
        # Try to find the most impactful sentence
        sentences = re.split(r'(?<=[。\.\!\?])\s+', abstract)
        for s in reversed(sentences):
            if re.search(r'\b(?:finding|result|conclusion|demonstrat|show|reveal|suggest|lead to|important|critical|key|significant|novel|new|first)\b', s, re.I):
                return clean_text(s)[:300]
        return sentences[-1][:300] if sentences else first_sentence(abstract)[:300]
    return title


def extract_excerpt(abstract, text, max_chars=500):
    """Extract a meaningful excerpt from the paper."""
    if abstract and len(abstract) > 100:
        return abstract[:max_chars]
    # Fall back to first substantive paragraph
    paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 100]
    for p in paragraphs[:5]:
        if not re.search(r'\b(fig\.|figure|table|supplementary|supplemental|references?|acknowledgments?|conflict|competing|funding)\b', p[:50], re.I):
            return clean_text(p)[:max_chars]
    return ''


def parse_year(filename):
    """Extract year from filename."""
    m = re.search(r'(19\d{2}|20\d{2})', filename)
    return m.group(0) if m else ''


def sanitize_filename(name):
    """Make a safe filename."""
    return re.sub(r'[\\/:*?"<>|]+', '_', name).replace(' ', '_')


def build_md(md_path, docid, doc_type, year, title, authors, journal, doi, pmid,
             keywords, core_value, background, gap, objective, methods, results,
             conclusions, notes, tags, excerpt):
    """Build structured markdown file for agent learning."""
    lines = []
    lines.append(f"文献标题（原文完整标题）\n{title}\n")
    lines.append(f"一句话核心价值：\n{core_value}\n")
    lines.append("📌 元数据\n")
    lines.append("字段\t内容\n")
    lines.append(f"文献ID\t{docid}\n")
    lines.append(f"文献类型\t{TYPE_MAP.get(doc_type, '基础研究')}\n")
    lines.append(f"作者（年份）\t{authors} ({year})\n")
    lines.append(f"期刊\t{journal or ''}\n")
    lines.append(f"DOI / PMID\t{doi or pmid or ''}\n")
    lines.append(f"证据等级\t{GRADE_DEFAULT.get(doc_type, '4')}\n")

    kw_display = ', '.join(f'`{kw}`' for kw in keywords) if keywords else ''
    lines.append(f"关键词\t{kw_display}\n")

    lines.append("🔍 文献背景与定位\n")
    lines.append(f"1. 研究或综述要回答的核心问题：\n{objective or '未从摘要自动提取到目标。'}\n")
    lines.append(f"2. 已知背景：\n{background or '未从摘要自动提取到背景。'}\n")
    lines.append(f"3. 知识缺口：\n{gap or '未从摘要自动提取到知识缺口。'}\n")
    lines.append(f"4. 本文目标：\n{objective or '未从摘要自动提取到目标。'}\n")

    lines.append("🔬 方法学\n")
    lines.append(f"{methods or '未从摘要或首页自动提取到方法学内容。'}\n")
    lines.append("📊 核心结果\n")
    lines.append(f"{results or '未从摘要或首页自动提取到结果。'}\n")
    lines.append("🧠 结论与讨论\n")
    lines.append(f"{conclusions or '未从摘要或首页自动提取到结论。'}\n")

    lines.append("📌 本知识库的扩展注解\n")
    lines.append(f"{notes}\n")

    lines.append("🔗 标准化标签\n")
    lines.extend(tags)
    lines.append('')

    lines.append("📖 原文精选片段\n")
    lines.append(f"{excerpt or '未提取到原文精选句子。'}\n")

    lines.append("🔗 关联文件与备注\n")
    lines.append("请根据全文补充关联文献ID和推荐阅读顺序。\n")

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main():
    pdf_files = sorted(PDF_DIR.glob('*.pdf'))

    if not pdf_files:
        print('No PDF files found.')
        return

    # Remove duplicate .pdf.pdf files
    valid_pdfs = [p for p in pdf_files if not p.name.endswith('.pdf.pdf')]

    type_counters = {}

    for pdf_path in valid_pdfs:
        print(f'\nProcessing: {pdf_path.name}')

        # Extract full text (first 15 pages for speed, enough for most metadata)
        text = extract_text_sorted(pdf_path, max_pages=15)

        # Title: try font-based extraction first, fall back to filename
        extracted_title = extract_title_from_pdf(str(pdf_path))
        if extracted_title and len(extracted_title) > 10:
            title = extracted_title
            print(f'  Title (extracted): {title[:80]}...')
        else:
            title = pdf_path.stem
            print(f'  Title (filename): {title[:80]}...')

        # Authors
        authors = extract_authors_from_pdf(str(pdf_path))
        if not authors:
            # Fall back to text-based parsing
            authors = parse_authors_fallback(text)
        print(f'  Authors: {authors[:80]}...' if authors else '  Authors: NOT FOUND')

        # Journal
        journal = extract_journal_from_pdf(str(pdf_path))
        if not journal:
            journal = parse_journal_fallback(text)
        print(f'  Journal: {journal}' if journal else '  Journal: NOT FOUND')

        # Abstract
        abstract = extract_abstract(text)
        print(f'  Abstract: {len(abstract)} chars' if abstract else '  Abstract: NOT FOUND')

        # DOI / PMID
        doi = extract_doi(text, str(pdf_path))
        pmid = extract_pmid(text)
        print(f'  DOI: {doi}' if doi else f'  PMID: {pmid}' if pmid else '  DOI/PMID: NOT FOUND')

        # Keywords
        keywords = extract_keywords(text)
        print(f'  Keywords: {keywords}' if keywords else '  Keywords: NOT FOUND')

        # Type detection
        doc_type = detect_type(text, title)
        type_counters.setdefault(doc_type, 0)
        type_counters[doc_type] += 1
        docid = f"PD-{doc_type[:3].upper()}-{type_counters[doc_type]:03d}"
        print(f'  Type: {doc_type} -> ID: {docid}')

        # Year
        year = parse_year(pdf_path.name)

        # Tags
        tags = detect_tags(text)

        # Content inference
        core_value = extract_core_value(abstract, title)
        background, gap, objective = infer_background_gap_objective(abstract, title, doc_type)
        methods, results, conclusions = infer_methods_results_conclusions(abstract, doc_type)

        # Excerpt
        excerpt = extract_excerpt(abstract, text)

        # Notes
        notes = '此文件基于自动抽取生成，建议结合全文审校并补充证据等级、资助来源、详细数据和结论。'

        # Output filename: use original PDF stem
        md_name = sanitize_filename(pdf_path.stem) + '.md'
        md_path = PDF_DIR / md_name

        build_md(md_path, docid, doc_type, year, title, authors, journal, doi, pmid,
                 keywords, core_value, background, gap, objective, methods, results,
                 conclusions, notes, tags, excerpt)

        print(f'  ✓ Generated {md_name}')


def parse_authors_fallback(text):
    """Fallback author extraction from text (original approach, improved)."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    abstract_idx = next((i for i, ln in enumerate(lines) if re.match(r'^(abstract|摘要|summary)\b', ln, re.I)), len(lines))
    pre = lines[:abstract_idx]
    candidates = []
    for ln in pre:
        if re.search(r'\b(and|,|et al\.)\b', ln, re.I) and len(re.findall(r'[A-Z][a-z]+', ln)) >= 3:
            # Exclude affiliation/metadata lines
            if not re.search(r'\b(doi:|department|university|hospital|institute|school|college|laboratory|lab|centre|center|clinic|email|e-mail|correspondence|n engl|www\.|copyright)\b', ln, re.I):
                candidates.append(ln)
    if candidates:
        return clean_text(' '.join(candidates[-2:]))
    return ''


def parse_journal_fallback(text):
    """Fallback journal extraction from text."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    journal_patterns = [
        r'\b(N Engl J Med|New England Journal of Medicine)\b',
        r'\b(Lancet\s*(?:Neurology|Neurol)?)\b',
        r'\b(Nature\s*(?:Reviews?\s*)?(?:Neurology|Medicine|Neuroscience|Communications)?)\b',
        r'\b(Science\s*(?:Translational Medicine)?)\b',
        r'\b(Brain)\b',
        r'\b(Neurology)\b',
        r'\b(Movement\s+Disorders?)\b',
        r'\b(Annals\s+of\s+Neurology)\b',
        r'\b(JAMA\s*(?:Neurology)?)\b',
        r'\b(Journal\s+of\s+(?:Neurology|Neuroscience|Parkinson))\b',
        r'\b(npj\s+Parkinson)\b',
        r'\b(Cell)\b',
        r'\b(Neuron)\b',
        r'\b(PNAS)\b',
        r'\b(BMJ)\b',
    ]
    for ln in lines[:30]:
        for pat in journal_patterns:
            if re.search(pat, ln, re.I):
                return clean_text(ln)
    return ''


if __name__ == '__main__':
    main()
