from __future__ import annotations

from enum import Enum


class ReportKind(Enum):
    A = "A"
    B = "B"
    C = "C"


class OutputFormat(Enum):
    HTML = "html"


class RouteAttemptResult(Enum):
    SUCCESS_WITH_EVIDENCE = "success_with_evidence"
    SUCCESS_IRRELEVANT_ONLY = "success_irrelevant_only"
    SEARCHED_NO_EVIDENCE = "searched_no_evidence"
    NOT_PUBLICLY_DISCLOSED = "not_publicly_disclosed"
    ACCESS_OR_PERMISSION_BLOCKED = "access_or_permission_blocked"
    TRANSIENT_NETWORK_FAILURE = "transient_network_failure"
    RATE_LIMITED = "rate_limited"
    ANTI_BOT_OR_CAPTCHA = "anti_bot_or_captcha"
    SOURCE_UNAVAILABLE = "source_unavailable"
    PARSER_OR_SCHEMA_FAILURE = "parser_or_schema_failure"
    TOOL_CAPABILITY_GAP = "tool_capability_gap"
    CONTENT_TRUNCATED = "content_truncated"


class RouteCompletion(Enum):
    COMPLETED = "completed"
    NOT_APPLICABLE = "not_applicable"
    ACCESS_BLOCKED = "access_blocked"


class FactDisclosureState(Enum):
    REPORTED_VALUE = "reported_value"
    REPORTED_ZERO = "reported_zero"
    NOT_REPORTED = "not_reported"
    BELOW_REPORTING_THRESHOLD = "below_reporting_threshold"
    NOT_PUBLICLY_DISCLOSED = "not_publicly_disclosed"
    NOT_APPLICABLE = "not_applicable"
    CONFLICTING = "conflicting"
    UNRESOLVED_DUE_TO_ROUTE = "unresolved_due_to_route"


class FactReviewState(Enum):
    CANDIDATE = "candidate"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ProjectRunState(Enum):
    RUNNING = "running"
    AWAITING_USER = "awaiting_user"
    PARTIALLY_DELIVERED = "partially_delivered"
    PARTIAL_DELIVERY_BLOCKED = "partial_delivery_blocked"
    BLOCKED = "blocked"
    COMPLETE = "complete"


class ReportEvidenceState(Enum):
    QUEUED = "queued"
    COLLECTING = "collecting"
    RECOVERING = "recovering"
    AWAITING_USER = "awaiting_user"
    SCIENTIFIC_QC = "scientific_qc"
    SNAPSHOT_LOCKED = "snapshot_locked"
    EVIDENCE_BLOCKED = "evidence_blocked"
    SUPERSEDED = "superseded"


class FormatArtifactState(Enum):
    QUEUED = "queued"
    GENERATING = "generating"
    QUALITY_CHECK = "quality_check"
    PASSED = "passed"
    DELIVERY_READY = "delivery_ready"
    BLOCKED = "blocked"
    SUPERSEDED = "superseded"


class DownloadRequestState(Enum):
    AWAITING_USER = "awaiting_user"
    FILE_DETECTED = "file_detected"
    MATCHED = "matched"
    ACCEPTED = "accepted"
    NEEDS_RE_DOWNLOAD = "needs_re_download"
    NOT_REQUIRED = "not_required"


class RevisionApprovalState(Enum):
    SUBMITTED = "submitted"
    NEEDS_EVIDENCE = "needs_evidence"
    REJECTED = "rejected"
    VALIDATED_PENDING_USER_APPROVAL = "validated_pending_user_approval"
    APPROVED = "approved"
    PUBLISHED = "published"
