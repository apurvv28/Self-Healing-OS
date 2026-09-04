"""Tests for LogPreprocessor module."""

from ai.preprocessor import LogPreprocessor


def test_clean_text_strips_entities():
    raw_log = "kernel: [ 1234.567] Out of memory: Kill process 9999 (mysqld) score 850 at 0x00007f9a path /var/log/syslog"
    cleaned = LogPreprocessor.clean_text(raw_log)

    assert "1234.567" not in cleaned
    assert "0x00007f9a" not in cleaned
    assert "/var/log/syslog" not in cleaned
    assert "out of memory" in cleaned
    assert "mysqld" in cleaned


def test_build_vectorizer():
    vectorizer = LogPreprocessor.build_vectorizer(max_features=100)
    corpus = [
        "out of memory kill process",
        "systemd service failed to start",
    ]
    matrix = vectorizer.fit_transform(corpus)
    assert matrix.shape[0] == 2
    assert matrix.shape[1] > 0
