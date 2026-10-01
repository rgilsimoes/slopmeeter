from calibration.calibrate import main, read_labels, summarize


def test_empty_calibration_file_runs(tmp_path, capsys):
    path = tmp_path / "labels.csv"
    path.write_text("repo_url,label,notes\n", encoding="utf-8")
    assert main([str(path)]) == 0
    output = capsys.readouterr().out
    assert "solid,0,n/a,n/a,n/a" in output
    assert "separation_min_adjacent_mean_gap,n/a" in output


def test_read_labels_rejects_invented_category(tmp_path):
    path = tmp_path / "labels.csv"
    path.write_text("repo_url,label,notes\n.,excellent,nope\n", encoding="utf-8")
    try:
        read_labels(path)
    except ValueError as exc:
        assert "unsupported label" in str(exc)
    else:
        raise AssertionError("invalid labels must be rejected")


def test_separation_metric():
    output = summarize({"solid": [90, 80], "mixed": [60], "slop": [20, 40]})
    assert "separation_min_adjacent_mean_gap,25.00" in output

