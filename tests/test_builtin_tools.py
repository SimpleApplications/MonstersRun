"""Tests for builtin tools beyond the basics covered in test_tools.py."""

import os

from project_june.builtin_tools import list_directory, write_file


def test_list_directory(tmp_path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    out = list_directory.run(path=str(tmp_path))
    assert "a.txt" in out
    assert "sub/" in out  # directories get a trailing slash


def test_list_directory_not_a_dir(tmp_path):
    f = tmp_path / "f.txt"
    f.write_text("x", encoding="utf-8")
    assert "not a directory" in list_directory.run(path=str(f))


def test_write_file_inside_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = write_file.run(path="notes/hello.txt", content="hi there")
    assert "wrote 8 chars" in out
    assert (tmp_path / "notes" / "hello.txt").read_text() == "hi there"


def test_write_file_refuses_escape(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = write_file.run(path="../escape.txt", content="nope")
    assert "refusing to write outside" in out
    assert not (tmp_path.parent / "escape.txt").exists()


def test_write_file_refuses_absolute_escape(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = os.path.join(os.sep, "tmp", "june_should_not_write.txt")
    out = write_file.run(path=target, content="nope")
    assert "refusing to write outside" in out
