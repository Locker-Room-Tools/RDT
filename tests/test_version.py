"""Version lookup across supported installation identities."""

from importlib.metadata import PackageNotFoundError

import pytest
from pytest import MonkeyPatch

import rdt
from rdt import version as version_module


@pytest.mark.parametrize(
    ("available", "expected"),
    [
        ({"rdt-rambo": "3.0"}, "3.0"),
        ({"locker-room-tolls-rdt": "2.0"}, "2.0"),
        ({"rdt-rambo": "3.0", "locker-room-tolls-rdt": "2.0"}, "3.0"),
        ({}, rdt.__version__),
    ],
)
def test_version_metadata_fallback(monkeypatch: MonkeyPatch, available: dict[str, str], expected: str) -> None:
    def lookup(name: str) -> str:
        if name not in available:
            raise PackageNotFoundError(name)
        return available[name]

    monkeypatch.setattr(version_module, "version", lookup)
    assert version_module.get_version() == expected


def test_version_does_not_hide_unrelated_metadata_errors(monkeypatch: MonkeyPatch) -> None:
    def fail(name: str) -> str:
        raise ValueError(name)

    monkeypatch.setattr(version_module, "version", fail)
    with pytest.raises(ValueError):
        version_module.get_version()
