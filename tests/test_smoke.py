import pytest

import ragforge


def test_main_prints_greeting(capsys: pytest.CaptureFixture[str]) -> None:
    ragforge.main()

    assert capsys.readouterr().out == "Hello from ragforge!\n"
