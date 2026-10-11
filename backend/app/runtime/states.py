"""Terminal states are final, including when an interrupted worker returns late."""
from app.runtime.contracts import TaskState as S

_NEXT = {
    S.CREATED: frozenset({S.PENDING}),
    S.PENDING: frozenset({S.READY, S.BLOCKED}),
    S.READY: frozenset({S.RUNNING, S.BLOCKED}),
    S.RUNNING: frozenset({S.SUCCESS, S.FAILED, S.WAITING_REVIEW}),
}


def transition(current: S, target: S) -> S:
    current, target = S(current), S(target)
    if target not in _NEXT.get(current, frozenset()):
        raise ValueError('Illegal task state transition')
    return target
