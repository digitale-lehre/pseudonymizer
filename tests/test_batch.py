import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from pseudonym import process_file, make_output_path, collect_input_files, create_output_zip


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


def test_collect_input_files_plain(tmp_path):
    f1 = tmp_path / "a.csv"
    f1.write_text("Vorname\nMax\n")
    f2 = tmp_path / "b.csv"
    f2.write_text("Vorname\nEva\n")
    result = collect_input_files([str(f1), str(f2)])
    assert [Path(r) for r in result] == [f1, f2]


def test_collect_input_files_zip(tmp_path):
    csv1 = tmp_path / "data.csv"
    csv1.write_text("Vorname\nMax\n")
    txt = tmp_path / "readme.txt"
    txt.write_text("ignore me")
    zp = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.write(csv1, "data.csv")
        zf.write(txt, "readme.txt")
    result = collect_input_files([str(zp)])
    assert len(result) == 1
    assert result[0].name == "data.csv"


def test_collect_input_files_mixed(tmp_path):
    plain = tmp_path / "plain.csv"
    plain.write_text("Vorname\nEva\n")
    inner = tmp_path / "inner.csv"
    inner.write_text("Vorname\nMax\n")
    zp = tmp_path / "archive.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.write(inner, "inner.csv")
    result = collect_input_files([str(plain), str(zp)])
    assert len(result) == 2
    names = [r.name for r in result]
    assert "plain.csv" in names
    assert "inner.csv" in names


def test_create_output_zip(tmp_path):
    f1 = tmp_path / "a_pseudo.csv"
    f1.write_text("encrypted_a")
    f2 = tmp_path / "b_pseudo.csv"
    f2.write_text("encrypted_b")
    zip_path = tmp_path / "output.zip"
    create_output_zip([(str(f1), str(f1)), (str(f2), str(f2))], str(zip_path))
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert "a_pseudo.csv" in names
        assert "b_pseudo.csv" in names
        assert zf.read("a_pseudo.csv").decode() == "encrypted_a"
