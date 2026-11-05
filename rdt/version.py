"""Version lookup for installed distributions and source checkouts."""

from importlib.metadata import PackageNotFoundError, version

from rdt import __version__


def get_version() -> str:
    """Prefer canonical metadata, then legacy metadata, then the source version."""
    for distribution in ("rdt-rambo", "locker-room-tolls-rdt"):
        try:
            return version(distribution)
        except PackageNotFoundError:
            continue
    return __version__
