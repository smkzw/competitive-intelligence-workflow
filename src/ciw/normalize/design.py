"""Shared source design fields, source roles and threshold markup; no rendering or inference."""
import re

_THRESHOLD = re.compile(
    r"(?:>=|<=|≥|≤|>|<|至少|不低于|不超过|大于|小于|不少于|不大于|at least|at most|"
    r"greater than(?: or equal to)?|less than(?: or equal to)?)\s*\d+(?:\.\d+)?"
    r"(?:\s*(?:%|points?\b|分|岁|years?\b|mg(?:/dL)?\b|g/L\b|mL/min\b))?"
    r"|\d+(?:\.\d+)?\s*(?:or (?:more|greater|less)|及以上|及以下)"
    r"|\bbetween\s+\d+(?:\.\d+)?\s+and\s+\d+(?:\.\d+)?"
    r"|(?<![A-Za-z0-9])\d+(?:\.\d+)?\s*(?:–|—|-|to|至)\s*\d+(?:\.\d+)?\s*"
    r"(?:years?|months?|weeks?|days?|points?|岁|分|mL/min|mg/dL|g/24\s*h|g/L|g/g|RU/mL|%)(?![A-Za-z])",
    re.I,
)


def threshold_spans(text: str) -> list[dict]:
    return [{"start": m.start(), "end": m.end()} for m in _THRESHOLD.finditer(text)]


def _criterion_role(text, excerpt):
    roles = set()
    pattern = r"inclusion(?: criteria)?|exclusion(?: criteria)?|入选(?:标准)?|排除(?:标准)?"
    for occurrence in re.finditer(re.escape(excerpt), text):
        headings = list(re.finditer(pattern, text[:occurrence.end()], re.I))
        roles.add(("exclusion" if re.search(r"exclusion|排除", headings[-1][0], re.I) else "inclusion")
                  if headings else "unspecified")
    return next(iter(roles)) if len(roles) == 1 else "unspecified"


def design_passages(trial):
    """One shared inventory of original design fields for indexing and source checking."""
    passages = [("入排标准", trial.design.eligibility_text, "eligibility")]
    passages += [
        ("研究摘要", trial.design.brief_summary, "brief_summary"),
        ("研究描述", trial.design.detailed_description, "detailed_description"),
        ("设计描述", trial.design.model_description, "model_description"),
    ]
    passages += [(a.label, a.description, f"arm:{a.arm_id}") for a in trial.arms]
    passages += [("背景治疗", value, f"background:{i}") for i, value in enumerate(trial.design.background_therapy)]
    passages += [(o.title, o.description, f"outcome:{i}") for i, o in enumerate(trial.outcomes_planned)]
    passages += [("终点名称", o.title, f"outcome:{i}:title") for i, o in enumerate(trial.outcomes_planned)]
    passages += [("终点时点", o.timeframe, f"outcome:{i}:timeframe") for i, o in enumerate(trial.outcomes_planned)]
    return passages


def source_cohort_heading(trial, field, excerpt):
    """Bind a whole literal excerpt to one explicitly named source section, never allocate N."""
    if len(set(trial.conditions)) < 2 or not excerpt:
        return None
    source = dict((key, text) for _, text, key in design_passages(trial)).get(field, "")
    names = set(trial.conditions)
    for condition in trial.conditions:
        names.add(re.sub(r"\s*\([^()]+\)", "", condition).strip())
        names.update(re.findall(r"\(([A-Za-z][A-Za-z0-9-]{2,})\)", condition))
    pattern = r"(?:for\s+)?(?:(?:patients?|participants?|subjects?)\s+with\s+)?" + \
        r"(?:(?:primary|idiopathic|secondary)\s+)?(?:" + "|".join(re.escape(n) for n in names if n) + \
        r")(?:\s*\([A-Za-z][A-Za-z0-9-]{1,}\))?(?:\s+(?:cohort|group|patients?))?"
    regions, active, offset = [], None, 0
    for line in source.splitlines(keepends=True):
        content = _BULLET.sub("", line).strip()
        heading = re.split(r"[:：]", content, maxsplit=1)[0].strip()
        named = bool(re.fullmatch(pattern, heading, re.I))
        if named or _SECTION.match(line) or content.endswith((":", "：")):
            if active:
                regions.append((active, offset))
            active = dict(quote=heading, start=offset+line.index(heading),
                          end=offset+line.index(heading)+len(heading), section_start=offset) if named else None
        offset += len(line)
    if active:
        regions.append((active, len(source)))
    occurrences = list(re.finditer(re.escape(excerpt), source))
    bindings = [heading for occurrence in occurrences for heading, end in regions
                if heading["section_start"] < occurrence.end() and occurrence.start() < end]
    if len(bindings) != len(occurrences) or not bindings or any(h != bindings[0] for h in bindings):
        return None
    end = next(end for heading, end in regions if heading == bindings[0])
    start = bindings[0]["section_start"]
    if any(occurrence.end() > end or (occurrence.start() < start and not
            LOGICAL_PARENT.search(source[occurrence.start():start])) for occurrence in occurrences):
        return None
    return {key: value for key, value in bindings[0].items() if key != "section_start"} | dict(
        source_id=trial.locator.source_id, field=field, label=bindings[0]["quote"])


def topic_catalog(topics):
    return [dict(topic_id=f"design-topic-{i}", label=t.label.replace("入组阈值", "入排阈值"),
                 kind=t.kind, aliases=t.aliases)
            for i, t in enumerate(topics)]


def topic_field_matches(kind, field):
    if kind == "eligibility_threshold":
        return field == "eligibility"
    if kind == "endpoint_definition":
        return bool(re.fullmatch(r"outcome:\d+", field))
    if kind in {"treatment_duration", "dosing_regimen", "background_therapy", "follow_up"}:
        return field not in {"eligibility"} and not field.startswith("outcome:")
    return True


LOGICAL_PARENT = re.compile(r"[^.;\n]*(?:\ball\b|\bany\b|\bone\b|\bfollowing\b|全部|任一|以下)[^.;\n]*[:：]", re.I)
_SECTION = re.compile(r"^\s*(?:[*+•-]+\s*|\d+[.)]\s*)?(?:(?:key|main|major|general|principal)\s+)?"
                      r"(?:inclusion(?: criteria)?|exclusion(?: criteria)?|入选(?:标准)?|排除(?:标准)?)\s*[:：]", re.I)
_BULLET = re.compile(r"^(\s*)([*+•-]|\d+[.)]|[a-zA-Z][.)])\s+")


def _marker(line):
    marker = _BULLET.match(line)
    if not marker:
        return None
    return len(marker[1].expandtabs()), ("bullet" if marker[2] in "*+•-" else
                                       "number" if marker[2][0].isdigit() else "letter")


def logical_contexts(text, excerpt):
    """Preserve introduced child lists, ending them at a new section or explicit peer bullet."""
    contexts, parents, offset = [], [], 0
    occurrences = list(re.finditer(re.escape(excerpt), text))
    for line in text.splitlines(keepends=True):
        marker = _marker(line)
        if _SECTION.match(line):
            parents.clear()
        else:
            while parents and marker and parents[-1]["marker"] and (
                    marker[1] == parents[-1]["marker"][1] and marker[0] <= parents[-1]["marker"][0]):
                parents.pop()
            if intro := LOGICAL_PARENT.search(line):
                parents.append(dict(start=offset+intro.start(), end=offset+intro.end(), marker=marker))
        if not parents:
            offset += len(line)
            continue
        for occurrence in occurrences:
            if offset <= occurrence.start() < offset + len(line):
                end = text.find("\n", occurrence.end())
                contexts.append(dict(condition=text[parents[0]["start"]:parents[-1]["end"]],
                    context=text[parents[0]["start"]:end if end >= 0 else len(text)]))
        offset += len(line)
    return contexts


def source_sentences(text, excerpt, anchor=""):
    """Literal sentences overlapping the selected source span, constrained by its unique quote."""
    separated = "".join(
        "\n\n" + line[heading.end():] if (heading := _SECTION.match(line) or _BULLET.match(line)) else line
        for line in text.splitlines(keepends=True))
    sentences = re.split(r"\n\s*\n|(?<=[.!?])\s+(?=[A-Z])|(?<=[。！？])\s*", separated)
    start = text.index(anchor) if anchor and text.count(anchor) == 1 else None
    selections = [m for m in re.finditer(re.escape(excerpt), text)
                  if start is None or start <= m.start() and m.end() <= start+len(anchor)]
    contexts = []
    for sentence in sentences:
        sentence = _BULLET.sub("", sentence.strip(), count=1)
        if not sentence:
            continue
        if not any(occurrence.start() < selected.end() and selected.start() < occurrence.end()
                for occurrence in re.finditer(re.escape(sentence), text)
                for selected in selections):
            continue
        contexts.append(sentence)
    return list(dict.fromkeys(contexts))


def dependency_contexts(text, excerpt, anchor=""):
    """Keep the complete dependency predicate; retain branch labels in the enclosing source scope."""
    connectors = re.compile(r"\b(?:based on|provided that|subject to|only if|contingent (?:on|upon)|"
                            r"on condition that|defined (?:as|by)|and|or)\b|基于|前提|须经|需经|定义为|且|或", re.I)
    def required(value):
        # 'greater than or equal to' / 'between N and M' are one numeric comparison, not branches.
        return connectors.search(_THRESHOLD.sub("", value))
    contexts = []
    for sentence in source_sentences(text, excerpt, anchor):
        predicate = sentence
        while True:
            parts = re.split(r"(?<!\d):\s+(?=[A-Za-z\u4e00-\u9fff])", predicate, maxsplit=1)
            if len(parts) != 2 or required(parts[0]) or not required(parts[1]):
                break
            predicate = parts[1]
        if required(predicate):
            contexts.append(predicate.rstrip(".。!?！？"))
    return contexts
