"""Tests for the file writer module."""

from bakec.writer import write_generated_files


def test_write_creates_directory(tmp_path):
    output_dir = tmp_path / "new_dir"
    files = {"test.c": "int main(void) { return 0; }\n"}
    results = write_generated_files(files, output_dir)
    assert output_dir.is_dir()
    assert len(results) == 1
    assert results[0][0] == "test.c"


def test_write_file_contents(tmp_path):
    content = "typedef float real_T;\n"
    files = {"types.h": content}
    write_generated_files(files, tmp_path)
    written = (tmp_path / "types.h").read_text(encoding="utf-8")
    assert written == content


def test_write_line_count(tmp_path):
    content = "line1\nline2\nline3\n"
    files = {"test.c": content}
    results = write_generated_files(files, tmp_path)
    assert results[0][1] == 3


def test_write_multiple_files(tmp_path):
    files = {
        "controller.c": "void step(void) {}\n",
        "controller.h": "#ifndef H\n#endif\n",
        "types.h": "typedef float real_T;\n",
    }
    results = write_generated_files(files, tmp_path)
    assert len(results) == 3
    assert all((tmp_path / name).exists() for name in files)


def test_write_overwrites_existing(tmp_path):
    path = tmp_path / "test.c"
    path.write_text("old content", encoding="utf-8")
    files = {"test.c": "new content\n"}
    write_generated_files(files, tmp_path)
    assert path.read_text(encoding="utf-8") == "new content\n"


def test_write_nested_directory(tmp_path):
    output_dir = tmp_path / "a" / "b" / "c"
    files = {"test.c": "int x;\n"}
    write_generated_files(files, output_dir)
    assert (output_dir / "test.c").exists()
