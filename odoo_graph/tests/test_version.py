from importlib.metadata import version

import pytest

from odoo_graph import __version__
from odoo_graph.cli import main


def test_package_version_comes_from_installed_metadata():
    assert __version__ == version("odoo-graph")


def test_cli_version_uses_package_metadata(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    assert version("odoo-graph") in capsys.readouterr().out
