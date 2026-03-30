import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from pseudonym import process_file, make_output_path


def test_process_file_csv(tmp_path):
    """process_file() dispatches CSV correctly and produces encrypted output."""
    src = tmp_path / "test.csv"
    src.write_text("Vorname,Familienname\nMax,Mustermann\n", encoding="utf-8")
    dst = tmp_path / "test_pseudo.csv"
    process_file(str(src), str(dst), "geheim", "encrypt", ",")
    assert dst.exists()
    content = dst.read_text(encoding="utf-8")
    assert "Max" not in content
    assert "Mustermann" not in content
    assert "Vorname" in content
    assert "Familienname" in content


def test_process_file_roundtrip(tmp_path):
    """Encrypt then decrypt produces original content."""
    original = "Vorname,Familienname\nMax,Mustermann\nEva,Testerin\n"
    src = tmp_path / "data.csv"
    src.write_text(original, encoding="utf-8")
    enc = tmp_path / "data_pseudo.csv"
    process_file(str(src), str(enc), "secret123", "encrypt", ",")
    dec = tmp_path / "data_restored.csv"
    process_file(str(enc), str(dec), "secret123", "decrypt", ",")
    restored = dec.read_text(encoding="utf-8")
    assert "Max" in restored
    assert "Mustermann" in restored
    assert "Eva" in restored
    assert "Testerin" in restored


def test_make_output_path_encrypt():
    assert make_output_path(Path("/d/students.csv"), "encrypt") == "/d/students_pseudo.csv"


def test_make_output_path_decrypt():
    assert make_output_path(Path("/d/data_pseudo.csv"), "decrypt") == "/d/data_pseudo_restored.csv"


def test_make_output_path_xlsx():
    assert make_output_path(Path("/d/data.xlsx"), "encrypt") == "/d/data_pseudo.xlsx"


def test_make_output_path_with_output_dir(tmp_path):
    result = make_output_path(Path("/d/students.csv"), "encrypt", str(tmp_path))
    assert result == str(tmp_path / "students_pseudo.csv")
