import pytest

from pipeline.registry import Registry, build_registry


@pytest.fixture(scope="session")
def registry() -> Registry:
    return build_registry()
