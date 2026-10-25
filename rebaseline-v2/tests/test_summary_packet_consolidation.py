"""Complete evidence packets use the existing hard bound without a second low ceiling."""
from test_summary_evidence_budget import evidence_setup

from ciw2.pipeline import stages, summary_budget


def test_neighboring_complete_records_share_a_packet_within_the_existing_evidence_bound(settings, monkeypatch):
    rc, inputs, verified, _, _ = evidence_setup(settings, monkeypatch, count=18, quote_chars=4500)
    projected, refs, basis = stages._summary_basis(rc, inputs, verified)
    task = {'data': {'candidate_findings': projected}, 'verified_fact_ids': sorted(refs),
            'finding_basis_sha256': basis, 'mode': 'synthesis', 'finding_limit': 6}
    costs = summary_budget.read_costs(rc, refs)
    packets = summary_budget.packets([task], costs, lambda _: False)
    assert len(packets) == 2
    assert [row for packet in packets for row in packet['data']['candidate_findings']] == projected
    assert all(summary_budget.context_chars(packet, costs) <= summary_budget.MAX_CONTEXT_CHARS
               for packet in packets)
    assert any(summary_budget.context_chars(packet, costs) > 24000 for packet in packets)
