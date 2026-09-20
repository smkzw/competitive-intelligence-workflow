#!/usr/bin/env python3
"""Reproduce narrow findings without importing IO-heavy packet modules.

Default: execute transparently transcribed source excerpts shipped with this review.
--repo: AST-extract the named functions/expressions from a real checkout instead.
--assert-fixed: return 1 if desired invariants still fail (baseline failures expected).
Not an integration, browser, or release test. Uses only the Python standard library.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path
from types import SimpleNamespace
from typing import Any

BASELINE = 'd6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca'
HERE = Path(__file__).resolve().parent
PATHS = {
    'c': 'src/ci_workflow/reports/c/synthesis.py',
    'builder': 'packets/2026-09-11-pnh-vertical/build_pnh_c_audit.py',
    'category': 'src/ci_workflow/application/source_research_service.py',
    'ids': 'src/ci_workflow/domain/ids.py',
    'ingestion': 'src/ci_workflow/application/fresh_research_ingestion.py',
}
EXCERPTS = {
    'c': 'c_synthesis_extract.py', 'builder': 'c_builder_extract.py',
    'category': 'source_classifier_extract.py', 'ids': 'ids.py',
}


def load_functions(path: Path, names: set[str]) -> dict[str, Any]:
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    if {node.name for node in nodes} != names:
        raise ValueError(f'Missing source functions in {path}; remap tests explicitly, do not silently skip.')
    # Postponed annotations avoid unrelated typing imports. No module-level IO executes.
    future = ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)
    module = ast.fix_missing_locations(ast.Module(body=[future, *nodes], type_ignores=[]))
    ns = {'re': re, 'hashlib': hashlib, 'unicodedata': unicodedata,
          '_KIND_PATTERN': re.compile(r'[a-z][a-z0-9-]*')}
    exec(compile(module, str(path), 'exec'), ns)
    return ns


def version_expression(repo: Path | None) -> ast.Expression:
    if repo is None:
        expr = ast.parse('stable_id("fact-version", fact.fact_id, fact.field_id, fact.normalized_value or fact.disclosure_state, fragment_id)', mode='eval')
    else:
        tree = ast.parse((repo / PATHS['ingestion']).read_text(encoding='utf-8'))
        func = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'ingest_research_evidence')
        matches = [node.value for node in ast.walk(func) if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'version_id' for t in node.targets)]
        if len(matches) != 1:
            raise ValueError('Version identity implementation changed; port this regression to the canonical public API.')
        expr = ast.Expression(body=matches[0])
    return ast.fix_missing_locations(expr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--assert-fixed', action='store_true')
    args = parser.parse_args()
    repo = args.repo.resolve() if args.repo else None
    path = lambda key: repo / PATHS[key] if repo else HERE / 'source_extracts' / EXCERPTS[key]
    c = load_functions(path('c'), {'_normalize_text', '_compact_clause'})
    split = load_functions(path('builder'), {'_split_eligibility'})['_split_eligibility']
    category = load_functions(path('category'), {'_outcome_category'})['_outcome_category']
    stable = load_functions(path('ids'), {'stable_id', '_normalize_identity_part'})['stable_id']
    checks = []

    def add(case_id: str, invariant: str, observed: Any, passed: bool, scope: str = 'source_function') -> None:
        checks.append({'case_id': case_id, 'desired_invariant': invariant, 'observed': observed,
                       'desired_invariant_passed': passed, 'scope': scope})

    text = 'Inclusion Criteria:\n' + '\n'.join(f'- Inclusion item {i:02d} complete text' for i in range(1, 13))
    text += '\nExclusion Criteria:\n' + '\n'.join(f'- Exclusion item {i:02d} complete text' for i in range(1, 12))
    inc, exc = split(text)
    add('R01', 'Preserve all 12 inclusion and 11 exclusion clauses', {'inclusion_count': len(inc), 'exclusion_count': len(exc)}, len(inc) == 12 and len(exc) == 11)
    short, _ = split('Inclusion Criteria:\n- HIV+\n- Able to sign informed consent')
    add('R02', 'Never discard a source clause only because it is short', short, any('HIV+' in x for x in short))
    decimal = c['_compact_clause']('0.5 mg BID')
    add('R03', 'Decimal punctuation is preserved in user-visible design clauses', decimal, '0.5' in decimal)
    left, right = c['_normalize_text']('5-10 mg'), c['_normalize_text']('5.10 mg')
    add('R04', 'A dose range and decimal dose must not have the same canonical text', {'range': left, 'decimal': right}, left != right)
    nonserious = category('Adverse Events', 'Non-serious adverse events')
    add('R05', 'Non-serious AE must not be classified as SAE', nonserious, nonserious != 'sae')
    generic_ae = category('Adverse Events', 'AE')
    add('R06', 'Generic AE must not be upgraded to treatment-emergent AE without temporal evidence', generic_ae, generic_ae != 'teae')
    positive = category('Serious Adverse Events', 'SAE')
    add('R07_CONTROL', 'Explicit SAE remains SAE', positive, positive == 'sae')

    expr = compile(version_expression(repo), '<fact-version identity expression>', 'eval')
    common = {'fact_id': 'same-fact', 'field_id': 'same-field', 'normalized_value': '0'}
    old = SimpleNamespace(**common, disclosure_state='reported_value')
    new = SimpleNamespace(**common, disclosure_state='reported_zero')
    environment = {'stable_id': stable, 'fragment_id': 'same-fragment'}
    old_id = eval(expr, environment, {'fact': old})
    new_id = eval(expr, environment, {'fact': new})
    db = sqlite3.connect(':memory:')
    try:
        db.execute('CREATE TABLE probe_facts (version_id TEXT PRIMARY KEY, disclosure_state TEXT)')
        db.execute('INSERT OR IGNORE INTO probe_facts VALUES (?, ?)', (old_id, old.disclosure_state))
        db.execute('INSERT OR IGNORE INTO probe_facts VALUES (?, ?)', (new_id, new.disclosure_state))
        stored = list(db.execute('SELECT version_id, disclosure_state FROM probe_facts'))
    finally:
        db.close()
    add('R08', 'Disclosure-state change is not swallowed by version identity + INSERT OR IGNORE',
        {'old_id': old_id, 'new_id': new_id, 'stored_rows': stored}, old_id != new_id and len(stored) == 2,
        'actual_identity_expression_plus_minimal_sqlite_demonstration_not_repository_ingestion')

    output = {
        'baseline_commit': BASELINE,
        'execution_mode': 'real_checkout_ast_extraction' if repo else 'transcribed_source_excerpts',
        'python': sys.version.split()[0],
        'not_performed': ['full_repository_tests', 'real_research', 'installed_bundle', 'browser_acceptance'],
        'checks': checks,
        'desired_invariants_failed': sum(not c['desired_invariant_passed'] for c in checks),
        'controls_and_invariants_passed': sum(c['desired_invariant_passed'] for c in checks),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return int(args.assert_fixed and output['desired_invariants_failed'] > 0)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, StopIteration, SyntaxError) as exc:
        print(f'PROBE_SETUP_ERROR: {exc}', file=sys.stderr)
        raise SystemExit(2)
