from slopmeter.cli import main


def test_version_and_list_checks(capsys):
    assert main(["--list-checks"]) == 0
    output = capsys.readouterr().out
    assert "H1\tCommit depth" in output
    assert "I1\tAI-assistance disclosure" in output


def test_explain(capsys):
    assert main(["--explain", "C1"]) == 0
    assert "Claims have receipts" in capsys.readouterr().out


def test_local_analysis_json_and_fail_under(tmp_path, capsys):
    (tmp_path / "README.md").write_text("# Tiny\n\nA small local project.\n", encoding="utf-8")
    assert main([str(tmp_path), "--format", "json", "--fail-under", "100"]) == 1
    output = capsys.readouterr().out
    assert '"schema_version": 1' in output
