"""Application-owned typed Skill graph for v1.3.

This is a small stdlib graph description, not a LangGraph runtime.  Adapters
consume its stable node/edge contracts while the deterministic executor remains
responsible for state transitions, checkpoints, evidence, and HTML artifacts.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class SkillNodeContract:
    skill_id: str
    version: str
    input_types: tuple[str, ...]
    output_types: tuple[str, ...]
    read_scopes: tuple[str, ...]
    write_scopes: tuple[str, ...]
    completion_predicate: str
    retry_policy: str
    error_classes: tuple[str, ...]
    idempotency_key: str
    independent_acceptor: str | None = None
    requires_independent_context: bool = False

    def __post_init__(self) -> None:
        if not self.skill_id or not self.version:
            raise ValueError("Skill 节点身份不能为空")
        if not self.input_types or not self.output_types:
            raise ValueError(f"Skill 节点必须声明输入和输出：{self.skill_id}")
        if not self.completion_predicate or not self.retry_policy:
            raise ValueError(f"Skill 节点必须声明完成谓词和重试策略：{self.skill_id}")
        if not self.idempotency_key:
            raise ValueError(f"Skill 节点必须声明幂等键：{self.skill_id}")
        if self.requires_independent_context and not self.independent_acceptor:
            raise ValueError(f"需要独立上下文的节点必须声明独立接受者：{self.skill_id}")


@dataclass(frozen=True)
class SkillEdge:
    source: str
    target: str
    condition: str = "always"


class TypedSkillGraph:
    """Validated immutable graph definition shared by all hosts."""

    def __init__(
        self,
        *,
        public_entry_id: str,
        nodes: Iterable[SkillNodeContract],
        edges: Iterable[SkillEdge],
    ) -> None:
        self.public_entry_id = public_entry_id
        self.nodes = tuple(nodes)
        self.edges = tuple(edges)
        self._nodes_by_id = {node.skill_id: node for node in self.nodes}
        if len(self._nodes_by_id) != len(self.nodes):
            raise ValueError("Skill 图节点标识不能重复")
        if public_entry_id not in self._nodes_by_id:
            raise ValueError("公开入口必须是图节点")
        for edge in self.edges:
            if edge.source not in self._nodes_by_id or edge.target not in self._nodes_by_id:
                raise ValueError(f"Skill 图边引用未知节点：{edge.source}->{edge.target}")
            if edge.source == edge.target:
                raise ValueError(f"Skill 图不得包含自环：{edge.source}")

    @property
    def node_ids(self) -> tuple[str, ...]:
        return tuple(node.skill_id for node in self.nodes)

    def node(self, skill_id: str) -> SkillNodeContract:
        return self._nodes_by_id[skill_id]

    def outgoing(self, skill_id: str) -> tuple[SkillEdge, ...]:
        return tuple(edge for edge in self.edges if edge.source == skill_id)


_COMMON_ERRORS = (
    "invalid_input",
    "source_unavailable",
    "access_blocked",
    "network_failure",
    "conflict",
    "independent_review_failed",
)


def _node(
    skill_id: str,
    inputs: tuple[str, ...],
    outputs: tuple[str, ...],
    writes: tuple[str, ...],
    *,
    acceptor: str | None = None,
    independent: bool = False,
) -> SkillNodeContract:
    return SkillNodeContract(
        skill_id=skill_id,
        version="1.3",
        input_types=inputs,
        output_types=outputs,
        read_scopes=("project-relative",),
        write_scopes=writes,
        completion_predicate=f"{skill_id}:complete",
        retry_policy="deterministic-replay-safe",
        error_classes=_COMMON_ERRORS,
        idempotency_key=f"{skill_id}:project:run:snapshot",
        independent_acceptor=acceptor,
        requires_independent_context=independent,
    )


V13_SKILL_NODES: tuple[SkillNodeContract, ...] = (
    SkillNodeContract(
        skill_id="competitive-intelligence-workflow",
        version="1.3",
        input_types=("PublicIntakeRequest", "optional:ResearchPackage"),
        output_types=("ProjectContract", "ReportTypeAsk"),
        read_scopes=("user-request",),
        write_scopes=("project-contract",),
        completion_predicate="intake:contract-created-or-ask-issued",
        retry_policy="idempotent-project-contract",
        error_classes=("invalid_input", "ambiguous_indication"),
        idempotency_key="intake:project:contract",
    ),
    _node(
        "intake-preflight",
        ("ProjectContract", "HostCapabilities"),
        ("CapabilityMatrix",),
        ("project-state", "receipts"),
    ),
    _node(
        "research-package",
        ("ProjectContract", "MergedSourcePlan", "optional:ResearchPackage"),
        ("ResearchPackage", "SharedExtractionSet", "RouteReceipts"),
        ("evidence", "receipts"),
    ),
    _node(
        "ontology-universe",
        ("ResearchPackage", "InnovationOntology"),
        ("UniverseClosure",),
        ("evidence", "receipts"),
        acceptor="clean-context-universe-review",
        independent=True,
    ),
    _node(
        "source-routing",
        ("ResearchPackage", "EvidenceGaps"),
        ("RouteReceipts",),
        ("receipts",),
    ),
    _node(
        "ingestion-identity",
        ("RouteReceipts", "SourceContent"),
        ("SourceVersions", "ManualSupplyGate"),
        ("evidence", "receipts"),
    ),
    _node(
        "extraction-normalization",
        ("SourceVersions",),
        ("AtomicFacts",),
        ("evidence",),
    ),
    _node(
        "identity-conflict",
        ("AtomicFacts", "SourceVersions"),
        ("ResolvedFacts", "ConflictSet"),
        ("evidence",),
        acceptor="clean-context-identity-review",
        independent=True,
    ),
    _node(
        "coverage-gates",
        ("ResolvedFacts", "GateSpec", "UniverseClosure"),
        (
            "CoverageResult",
            "WorkspaceMembership",
            "FacetPlan",
            "NumericFrameEligibility",
            "BlockerAudit",
        ),
        ("coverage", "blockers"),
    ),
    _node(
        "analysis-a",
        ("AcceptedSnapshot", "WorkspaceMembership", "FacetPlan", "NumericFrameEligibility"),
        ("ReportAView",),
        ("reports/A",),
    ),
    _node(
        "analysis-b",
        ("AcceptedSnapshot", "WorkspaceMembership", "FacetPlan", "NumericFrameEligibility"),
        ("ReportBView",),
        ("reports/B",),
    ),
    _node(
        "analysis-c",
        ("AcceptedSnapshot", "WorkspaceMembership", "FacetPlan", "NumericFrameEligibility"),
        ("ReportCView",),
        ("reports/C",),
    ),
    _node(
        "scientific-qc",
        ("ReportKind", "ReportView"),
        ("ScientificQCDecision",),
        ("qc",),
        acceptor="clean-context-scientific-review",
        independent=True,
    ),
    _node(
        "visual-design-director",
        ("AcceptedSnapshot", "PageCatalogs"),
        ("VisualPlan",),
        ("qc",),
    ),
    _node(
        "render-deliver",
        ("AcceptedSnapshot", "VisualPlan", "ScientificQCDecision"),
        ("HTMLPortals", "ArtifactManifests"),
        ("reports/A", "reports/B", "reports/C", "manifests"),
    ),
    _node(
        "visual-package-qc",
        ("HTMLPortals", "ArtifactManifests"),
        ("PackageQCDecision",),
        ("qc",),
        acceptor="clean-context-package-review",
        independent=True,
    ),
    _node(
        "correction-refresh",
        ("AcceptedSnapshot", "UserRefreshRequest"),
        ("Diff", "AcceptedSnapshot", "HTMLPortals"),
        ("corrections", "snapshots", "reports"),
    ),
)


V13_SKILL_EDGES: tuple[SkillEdge, ...] = (
    SkillEdge("competitive-intelligence-workflow", "intake-preflight"),
    SkillEdge("intake-preflight", "research-package", "ready"),
    SkillEdge("research-package", "ontology-universe"),
    SkillEdge("ontology-universe", "source-routing", "closure-or-recovery"),
    SkillEdge("source-routing", "ingestion-identity"),
    SkillEdge("ingestion-identity", "extraction-normalization"),
    SkillEdge("extraction-normalization", "identity-conflict"),
    SkillEdge("identity-conflict", "coverage-gates"),
    SkillEdge("coverage-gates", "analysis-a", "report-selected"),
    SkillEdge("coverage-gates", "analysis-b", "report-selected"),
    SkillEdge("coverage-gates", "analysis-c", "report-selected"),
    SkillEdge("analysis-a", "scientific-qc"),
    SkillEdge("analysis-b", "scientific-qc"),
    SkillEdge("analysis-c", "scientific-qc"),
    SkillEdge("scientific-qc", "visual-design-director", "accepted"),
    SkillEdge("visual-design-director", "render-deliver"),
    SkillEdge("render-deliver", "visual-package-qc"),
    SkillEdge("visual-package-qc", "correction-refresh", "user-triggered"),
)

V13_SKILL_GRAPH = TypedSkillGraph(
    public_entry_id="competitive-intelligence-workflow",
    nodes=V13_SKILL_NODES,
    edges=V13_SKILL_EDGES,
)


__all__ = [
    "SkillEdge",
    "SkillNodeContract",
    "TypedSkillGraph",
    "V13_SKILL_EDGES",
    "V13_SKILL_GRAPH",
    "V13_SKILL_NODES",
]
