"""Fixed server-owned rule list; input cannot disable or register a check."""
from app.integration.completion import check_completion
from app.integration.integrity import check_integrity
from app.integration.evidence import check_evidence
from app.integration.consistency import check_consistency
from app.integration.objective import check_objective
from app.integration.freshness import check_freshness

RULES=(('completion',check_completion),('integrity',check_integrity),('evidence',check_evidence),
       ('consistency',check_consistency),('objective',check_objective),('freshness',check_freshness))
def registered_checks():return RULES
