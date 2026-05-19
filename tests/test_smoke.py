"""Sanity check: package imports and exposes a version."""

import memory_graph


def test_package_has_version():
    assert memory_graph.__version__
    assert isinstance(memory_graph.__version__, str)
