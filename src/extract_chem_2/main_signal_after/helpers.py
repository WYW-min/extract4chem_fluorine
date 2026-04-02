from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

ALLOWED_L1 = {
    'heterocyclic': 'heterocyclic',
    'partially_heterocyclic': 'partially_heterocyclic',
    'unmodified_linear': 'unmodified_linear',
    'modified_linear': 'modified_linear',
    'conjugated_linear': 'conjugated_linear',
}
ALLOWED_L2 = {
    'aromatic': 'aromatic',
    'aliphatic': 'aliphatic',
    'aromatic, aliphatic': 'aromatic, aliphatic',
    'aliphatic, aromatic': 'aromatic, aliphatic',
}
DOI_CORE_PATTERN = re.compile(r'(10\.\d{4,9}/[^\s;]+)', re.IGNORECASE)
SAMPLE_FORM_PATTERNS = (
    ('aerogel', ('aerogel',)),
    ('film', ('film',)),
    ('membrane', ('membrane',)),
    ('ink', ('ink',)),
    ('powder', ('powder',)),
    ('solution', ('solution',)),
    ('solid', ('solid',)),
    ('gel', ('gel',)),
    ('fiber', ('fiber', 'fibre')),
    ('foam', ('foam',)),
    ('coating', ('coating',)),
)
HETEROCYCLIC_MARKERS = (
    'heterocyclic',
    'polyimide',
    'imide',
    'imidazole',
    'benzimidazole',
    'benzoxazole',
    'oxadiazole',
    'triazine',
    'pyridine',
    'pyrrole',
    'thiophene',
    'furan',
)
CONJUGATED_MARKERS = (
    'conjugated',
    'polyaniline',
    'polypyrrole',
    'polythiophene',
    'conducting polymer',
)
PRECURSOR_MARKERS = (
    'precursor',
    'oligomer',
    'trimer',
    'tetramer',
    'polyamic acid',
    'ammonium salt',
)
MODIFIED_LINEAR_MARKERS = (
    'modified',
    'functionalized',
    'terminated',
    'substituted',
    'doped',
)
AROMATIC_MARKERS = (
    'aromatic',
    'phenyl',
    'benz',
    'aniline',
    'phenylene',
    'diphenyl',
    'aryl',
)
ALIPHATIC_MARKERS = (
    'aliphatic',
    'cellulose',
    'alkyl',
    'cyclohex',
    'ethylene',
    'propylene',
    'polyethylene',
    'polypropylene',
)
COMPOSITE_MARKERS = (
    '/',
    'composite',
    'blend',
    'hybrid',
    'doped',
    'nanoparticle',
    'filled',
    'alloy',
)
PROCESS_LIQUID_FORMS = {'solution', 'gel'}
PROCESS_FAMILY_MARKERS = (
    'precursor',
    'polyamic acid',
    'amic acid',
    'ammonium salt',
    'salt solution',
)
GENERIC_PROCESS_TOKENS = {
    'poly',
    'polymer',
    'polymeric',
    'polyamic',
    'acid',
    'amic',
    'ammonium',
    'salt',
    'precursor',
    'solution',
    'aqueous',
    'water',
    'gel',
    'resin',
    'paa',
    'paas',
}
POLYIMIDE_COMPONENT_MARKERS = {
    'PI': ('polyimide',),
    'PAA': ('polyamic acid', 'paa'),
    'PAAS': ('polyamic acid ammonium salt', 'ammonium salt', 'paas'),
    'CNC': ('cellulose nanocrystal', 'cellulose nanocrystals', 'cnc'),
    'PANI': ('polyaniline', 'pani'),
}
GENERIC_INK_TOKENS = {
    'pure',
    'neat',
    'ink',
    'printing',
    'printed',
    'printable',
    'wt',
    'cnc',
    'paa',
    'paas',
    'pi',
    'pani',
    'polyimide',
    'polyamic',
    'acid',
    'ammonium',
    'salt',
    'cellulose',
    'nanocrystal',
    'nanocrystals',
    'composite',
}


def is_good_predict_record(record: dict[str, Any]) -> bool:
    result = record.get('result')
    if not isinstance(result, dict):
        return False
    error = result.get('error')
    if isinstance(error, str) and error.strip():
        return False
    if error is not None and not isinstance(error, str):
        return False
    return isinstance(result.get('parse'), dict)


def split_keywords(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        raw_items = value
    else:
        text = str(value).strip()
        if not text:
            return []
        raw_items = re.split(r'[;；]', text) if (';' in text or '；' in text) else [text]
    items: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        text = str(item).strip()
        if not text:
            continue
        key = text.lower()
        if key not in seen:
            seen.add(key)
            items.append(text)
    return items


def make_identity_identifier(literature_id: str | None, doc_id: str) -> str:
    text = normalize_literature_identifier(literature_id) or ''
    return text or doc_id


def normalize_literature_identifier(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r'\s+', '', str(value).strip())
    if not text:
        return None
    text = text.rstrip('.,;)')
    lowered = text.lower()
    if lowered.startswith('https://doi.org/') or lowered.startswith('http://doi.org/'):
        core = re.sub(r'^https?://doi\.org/', '', text, flags=re.IGNORECASE)
        return f'doi:{core}'
    if lowered.startswith('doi:'):
        core = re.sub(r'^doi:\s*', '', text, flags=re.IGNORECASE)
        return f'doi:{core}'
    match = DOI_CORE_PATTERN.search(text)
    if match:
        return f'doi:{match.group(1)}'
    return text


def normalize_l1(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    return ALLOWED_L1.get(raw.lower(), raw)


def normalize_l2(value: Any) -> str | None:
    if value is None:
        return None
    raw = re.sub(r'\s+', ' ', str(value).strip())
    if not raw:
        return None
    return ALLOWED_L2.get(raw.lower(), raw)


def normalize_free_text(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r'\s+', ' ', str(value).strip())
    return text or None


def normalize_compact_token(value: str) -> str:
    text = re.sub(r'\s*/\s*', '/', value)
    text = re.sub(r'\s*-\s*', '-', text)
    return text.strip()


def normalize_category_code(value: Any) -> str | None:
    text = normalize_free_text(value)
    if not text:
        return None
    normalized = normalize_compact_token(text)
    aliases = {
        'POLYIMIDE': 'PI',
        'POLYAMIC ACID': 'PAA',
        'POLYAMIC ACID AMMONIUM SALT': 'PAAS',
        'CELLULOSE NANOCRYSTAL': 'CNC',
        'CELLULOSE NANOCRYSTALS': 'CNC',
        'PI/AUNPS': 'PI/AuNPs',
        'PANI/AUNPS': 'PANI/AuNPs',
    }
    return aliases.get(normalized.upper(), normalized)


def normalize_sample_form(name: str, code: str | None, value: Any, *, context_text: str) -> str | None:
    del code, context_text
    raw = normalize_free_text(value)
    lowered_form = (raw or '').lower()
    lowered_name = normalize_free_text(name).lower() if normalize_free_text(name) else ''

    if raw:
        for canonical, patterns in SAMPLE_FORM_PATTERNS:
            if any(pattern in lowered_form for pattern in patterns):
                return canonical.title()
        return raw

    for canonical, patterns in SAMPLE_FORM_PATTERNS:
        if any(pattern in lowered_name for pattern in patterns):
            return canonical.title()
    return None


def normalize_polymer_name(name: str, code: str | None, *, context_text: str) -> str:
    del code, context_text
    text = normalize_free_text(name) or ''
    if not text:
        return text
    text = normalize_compact_token(text)
    text = re.sub(r'\(\s+', '(', text)
    text = re.sub(r'\s+\)', ')', text)
    return text


def normalize_category_name(name: str, code: str | None, value: Any, *, context_text: str) -> str | None:
    del name, context_text
    raw = normalize_free_text(value)
    if raw:
        return normalize_compact_token(raw)
    normalized_code = normalize_category_code(code)
    fallback = {
        'PI': 'Polyimide',
        'PAA': 'Polyamic Acid',
        'PAAS': 'Polyamic Acid Ammonium Salt',
        'CNC': 'Cellulose Nanocrystal',
    }
    return fallback.get(normalized_code)


def infer_structure_features(polymer: dict[str, Any]) -> tuple[str | None, str | None]:
    name = str(polymer.get('名称') or '').lower()
    category = str(polymer.get('聚合物分类名称') or '').lower()
    code = str(polymer.get('聚合物分类编码') or '').lower()
    text = ' '.join(part for part in [name, category, code] if part)

    has_heterocycle = any(marker in text for marker in HETEROCYCLIC_MARKERS)
    has_conjugated = any(marker in text for marker in CONJUGATED_MARKERS)
    has_precursor = any(marker in text for marker in PRECURSOR_MARKERS)
    has_modified_linear = any(marker in text for marker in MODIFIED_LINEAR_MARKERS)
    has_aromatic = any(marker in text for marker in AROMATIC_MARKERS)
    has_aliphatic = any(marker in text for marker in ALIPHATIC_MARKERS)
    has_composite = any(marker in text for marker in COMPOSITE_MARKERS)

    l1 = None
    l2 = None

    if has_conjugated:
        l1 = 'conjugated_linear'
    elif has_heterocycle:
        l1 = 'partially_heterocyclic' if (has_composite or has_aliphatic) else 'heterocyclic'
    elif has_precursor:
        l1 = 'modified_linear' if has_modified_linear else 'unmodified_linear'

    if has_aromatic and has_aliphatic:
        l2 = 'aromatic, aliphatic'
    elif has_aromatic:
        l2 = 'aromatic'
    elif has_aliphatic:
        l2 = 'aliphatic'

    return l1, l2


def resolve_structure_features(polymer: dict[str, Any]) -> tuple[str | None, str | None]:
    l1 = normalize_l1(polymer.get('结构特征_L1'))
    l2 = normalize_l2(polymer.get('结构特征_L2'))
    infer_l1, infer_l2 = infer_structure_features(polymer)
    return l1 or infer_l1, l2 or infer_l2


def normalize_name_key(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', value.lower())


def record_text(record: dict[str, Any]) -> str:
    return ' '.join(
        part.lower()
        for part in [
            normalize_free_text(record.get('名称')) or '',
            normalize_free_text(record.get('聚合物分类名称')) or '',
            normalize_free_text(record.get('聚合物分类编码')) or '',
        ]
        if part
    )


def is_generic_process_liquid(record: dict[str, Any]) -> bool:
    sample_form = str(record.get('样本形态') or '').strip().lower()
    if sample_form not in PROCESS_LIQUID_FORMS:
        return False

    text = record_text(record)

    if not any(marker in text for marker in PROCESS_FAMILY_MARKERS):
        return False
    if re.search(r'\d', text):
        return False
    if any(marker in text for marker in COMPOSITE_MARKERS):
        return False

    tokens = re.findall(r'[a-z0-9]+', text)
    meaningful_tokens = [
        token for token in tokens
        if token not in GENERIC_PROCESS_TOKENS and len(token) >= 3
    ]
    return not meaningful_tokens


def is_ink_record(record: dict[str, Any]) -> bool:
    return str(record.get('样本形态') or '').strip().lower() == 'ink'


def infer_component_codes(record: dict[str, Any]) -> set[str]:
    components: set[str] = set()
    code = normalize_category_code(record.get('聚合物分类编码')) or ''
    if '/' in code:
        for piece in code.split('/'):
            part = piece.strip().upper()
            if part:
                components.add(part)
        return components
    if code:
        components.add(code.strip().upper())
        return components

    text = record_text(record)
    for component, markers in POLYIMIDE_COMPONENT_MARKERS.items():
        if any(marker in text for marker in markers):
            components.add(component)
    return components


def is_composite_ink_record(record: dict[str, Any]) -> bool:
    if not is_ink_record(record):
        return False
    text = record_text(record)
    components = infer_component_codes(record)
    return len(components) >= 2 or any(marker in text for marker in COMPOSITE_MARKERS)


def is_generic_single_component_ink(record: dict[str, Any], *, composite_components: set[str]) -> bool:
    if not is_ink_record(record) or is_composite_ink_record(record):
        return False

    components = infer_component_codes(record)
    if len(components) != 1 or not components.issubset(composite_components):
        return False

    text = record_text(record)
    if any(marker in text for marker in ('control', 'reference', 'blank', 'compare', 'comparison')):
        return False

    tokens = re.findall(r'[a-z0-9]+', text)
    meaningful_tokens = [
        token for token in tokens
        if token not in GENERIC_INK_TOKENS
        and len(token) >= 3
        and not token.isdigit()
        and not re.fullmatch(r'\d+wt', token)
    ]
    return not meaningful_tokens


def record_info_score(record: dict[str, Any]) -> int:
    score = 0
    for key in ['聚合物分类名称', '聚合物分类编码', '名称', '样本形态', '结构特征_L1', '结构特征_L2']:
        value = record.get(key)
        if isinstance(value, str):
            if value.strip():
                score += 1
        elif value is not None:
            score += 1
    return score


def merge_record_fields(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in incoming.items():
        current = merged.get(key)
        if current in (None, '', [], {}) and value not in (None, '', [], {}):
            merged[key] = value
    return merged


def filter_and_deduplicate_polymers(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    has_non_process_object = any(
        str(record.get('样本形态') or '').strip().lower() not in PROCESS_LIQUID_FORMS
        for record in records
    )
    composite_ink_records = [record for record in records if is_composite_ink_record(record)]
    composite_ink_components: set[str] = set()
    for record in composite_ink_records:
        composite_ink_components.update(infer_component_codes(record))

    deduped: list[dict[str, Any]] = []
    index_by_key: dict[tuple[str, str, str], int] = {}
    for record in records:
        if has_non_process_object and is_generic_process_liquid(record):
            continue
        if len(composite_ink_records) >= 2 and is_generic_single_component_ink(
            record,
            composite_components=composite_ink_components,
        ):
            continue
        key = (
            normalize_name_key(str(record.get('名称') or '')),
            str(record.get('聚合物分类编码') or ''),
            str(record.get('样本形态') or ''),
        )
        existing_idx = index_by_key.get(key)
        if existing_idx is None:
            index_by_key[key] = len(deduped)
            deduped.append(record)
            continue

        existing = deduped[existing_idx]
        merged = merge_record_fields(existing, record)
        if record_info_score(record) > record_info_score(existing):
            merged = merge_record_fields(record, existing)
        deduped[existing_idx] = merged

    return deduped


def build_final_result(parsed: dict[str, Any], *, doc_id: str, context_text: str = '') -> dict[str, Any]:
    literature = parsed.get('文献信息') or {}
    polymers = parsed.get('聚合物') or []
    identifier_prefix = make_identity_identifier(literature.get('唯一文献标识'), doc_id)

    final_literature = {
        '唯一文献标识': normalize_literature_identifier(literature.get('唯一文献标识')),
        '论文标题': literature.get('论文标题'),
        '作者列表': literature.get('作者列表') or [],
        '期刊名称': literature.get('期刊名称'),
        '年份': literature.get('年份'),
        '卷号': literature.get('卷号'),
        '页码': literature.get('页码'),
        '文档类型': literature.get('文档类型'),
        '语言': literature.get('语言'),
        '关键词': split_keywords(literature.get('关键词')),
    }

    normalized_polymers: list[dict[str, Any]] = []
    for polymer in polymers:
        code = normalize_category_code(polymer.get('聚合物分类编码'))
        name = normalize_polymer_name(
            (polymer.get('名称') or '').strip(),
            code,
            context_text=context_text,
        )
        if not name:
            continue
        feature_l1, feature_l2 = resolve_structure_features(polymer)
        category_name = normalize_category_name(
            name,
            code,
            polymer.get('聚合物分类名称'),
            context_text=context_text,
        )
        sample_form = normalize_sample_form(
            name,
            code,
            polymer.get('样本形态'),
            context_text=context_text,
        )
        normalized_polymers.append(
            {
                '聚合物分类名称': category_name,
                '聚合物分类编码': code,
                '名称': name,
                '样本形态': sample_form,
                '结构特征_L1': feature_l1,
                '结构特征_L2': feature_l2,
                '表征': {},
                '性质': [],
                '工艺流程': [],
            }
        )

    normalized_polymers = filter_and_deduplicate_polymers(normalized_polymers)

    counters: defaultdict[str, int] = defaultdict(int)
    final_polymers: list[dict[str, Any]] = []
    for polymer in normalized_polymers:
        name = str(polymer['名称'])
        key = name.lower()
        counters[key] += 1
        final_polymers.append(
            {
                **polymer,
                '身份标识': f'{identifier_prefix}_{name}_{counters[key]:02d}',
            }
        )

    return {
        '文献信息': final_literature,
        '聚合物': final_polymers,
    }


def build_output_record(task: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any]:
    chain_input = task.get('chain_input') or {}
    return {
        'run_id': task['run_id'],
        'doc_id': task['doc_id'],
        'task_id': task['task_id'],
        'file_name': task.get('file_name'),
        'source_refs': task.get('source_refs', []),
        'result': build_final_result(
            parsed,
            doc_id=task['doc_id'],
            context_text=str(chain_input.get('text') or ''),
        ),
    }
