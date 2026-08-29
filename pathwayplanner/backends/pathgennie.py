"""PathGennie backend adapter (stub).

The ONLY module allowed to import pathgennie. Will map run_bursts onto
PathGennie's Engine protocol / driver swarm cycle.
"""

from __future__ import annotations

try:
    import pathgennie  # noqa: F401

    HAVE_PATHGENNIE = True
except ImportError:
    HAVE_PATHGENNIE = False


def make_backend(*args, **kwargs):
    """Construct a PathGennie-backed Backend. Not yet implemented."""
    if not HAVE_PATHGENNIE:
        raise ImportError(
            "pathgennie is not installed; install with pathwayplanner[pathgennie]"
        )
    raise NotImplementedError("PathGennie backend adapter is not yet implemented")
