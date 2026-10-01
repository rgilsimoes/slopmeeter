from slopmeter.cli import main


def test_version_and_list_checks(capsys):
    assert main(["--list-checks"]) == 0
    output = capsys.readouterr().out
    assert "H1\tCommit depth" in output
    assert "I1\tAI-assistance disclosure" in output


def test_explain(capsys):
    assert main(["--explain", "C1"]) == 0
    assert "Claims have receipts" in capsys.readouterr().out

