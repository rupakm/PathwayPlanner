"""Trails-MD backend adapter (stub).

The ONLY module allowed to import trails_md. Will map run_bursts onto
Trails-MD's walker execution machinery once the programmatic burst API
lands there (see docs/NOTES.md, logistics discussion).
"""

from __future__ import annotations

try:
    import trails_md  # noqa: F401

    HAVE_TRAILS_MD = True
except ImportError:
    HAVE_TRAILS_MD = False


def make_backend(*args, **kwargs):
    """Construct a Trails-MD-backed Backend. Not yet implemented."""
    if not HAVE_TRAILS_MD:
        raise ImportError(
            "trails-md is not installed; install with pathwayplanner[trailsmd]"
        )
    raise NotImplementedError("Trails-MD backend adapter is not yet implemented")
