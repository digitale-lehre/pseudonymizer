"""Tests fuer die Kommandozeile (main) und die Sammlung der Eingabedateien.

Alle Testdaten sind erfunden."""
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

import pseudonym as ps

GOOD = "Vorname;Familienname\nMax;Muster\n"
BAD = "Fach;Punkte\nAnatomie;5\n"


def write(path, text=GOOD):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_batch_continues_after_a_file_without_identity_columns(tmp_path, capsys):
    a, b, c = (write(tmp_path / "a.csv"), write(tmp_path / "b.csv", BAD), write(tmp_path / "c.csv"))
    rc = ps.main(["encrypt", str(a), str(b), str(c), "--secret", "s"])
    assert rc == 1
    assert (tmp_path / "a_pseudo.csv").exists() and (tmp_path / "c_pseudo.csv").exists()
    assert not (tmp_path / "b_pseudo.csv").exists()
    assert "2 erfolgreich, 1 fehlgeschlagen" in capsys.readouterr().out


def test_zip_temp_dir_is_removed_even_when_a_file_fails(tmp_path, monkeypatch):
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    monkeypatch.setattr("tempfile.tempdir", str(tmp))
    zp = tmp_path / "export.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.writestr("a.csv", GOOD)
        zf.writestr("b.csv", BAD)
    assert ps.main(["encrypt", str(zp), "--secret", "s"]) == 1
    assert list(tmp.iterdir()) == []
    assert (tmp_path / "a_pseudo.csv").exists()


def test_same_file_names_from_two_folders_do_not_overwrite_each_other(tmp_path):
    x, y = write(tmp_path / "x" / "liste.csv"), write(tmp_path / "y" / "liste.csv", "Vorname\nEva\n")
    out = tmp_path / "neu" / "aus"
    assert ps.main(["encrypt", str(x), str(y), "--secret", "s", "--output-dir", str(out)]) == 0
    assert sorted(p.name for p in out.iterdir()) == ["liste_pseudo.csv", "liste_pseudo_1.csv"]


def test_directory_as_input(tmp_path):
    write(tmp_path / "in" / "a.csv")
    write(tmp_path / "in" / "b.tsv", "Vorname\tPunkte\nEva\t1\n")
    write(tmp_path / "in" / "notiz.md", "kein Datenformat")
    write(tmp_path / "in" / "~$a.csv")
    assert ps.main(["encrypt", str(tmp_path / "in"), "--secret", "s"]) == 0
    assert sorted(p.name for p in (tmp_path / "in").glob("*_pseudo.*")) == ["a_pseudo.csv", "b_pseudo.tsv"]


def test_wildcard_as_input(tmp_path):
    """Windows-Konsolen loesen *.csv nicht auf; das Programm tut es selbst."""
    write(tmp_path / "a.csv")
    write(tmp_path / "b.csv")
    assert ps.main(["encrypt", str(tmp_path / "*.csv"), "--secret", "s"]) == 0
    assert (tmp_path / "a_pseudo.csv").exists() and (tmp_path / "b_pseudo.csv").exists()


def test_unsupported_file_is_reported(tmp_path, capsys):
    write(tmp_path / "a.csv")
    (tmp_path / "alt.xls").write_bytes(b"x")
    ps.main(["encrypt", str(tmp_path / "a.csv"), str(tmp_path / "alt.xls"), "--secret", "s"])
    assert "alt.xls" in capsys.readouterr().out


def test_sep_accepts_backslash_t(tmp_path):
    f = write(tmp_path / "a.txt", "Vorname\tPunkte\nMax\t1\n")
    assert ps.main(["encrypt", str(f), "--secret", "s", "--sep", "\\t"]) == 0
    assert b"Max" not in (tmp_path / "a_pseudo.txt").read_bytes()


def test_secret_from_prompt_is_asked_twice_for_encrypt(tmp_path, monkeypatch):
    f = write(tmp_path / "a.csv")
    answers = iter(["geheim", "geheim"])
    monkeypatch.delenv("PSEUDONYM_SECRET", raising=False)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(answers))
    assert ps.main(["encrypt", str(f)]) == 0
    expected = ps.encrypt_value(ps.derive_key("geheim"), "Max")
    assert expected in (tmp_path / "a_pseudo.csv").read_text(encoding="utf-8")
    assert next(answers, None) is None


def test_secret_prompt_mismatch_aborts(tmp_path, monkeypatch):
    f = write(tmp_path / "a.csv")
    answers = iter(["geheim", "gehiem"])
    monkeypatch.delenv("PSEUDONYM_SECRET", raising=False)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(answers))
    assert ps.main(["encrypt", str(f)]) == 1
    assert not (tmp_path / "a_pseudo.csv").exists()


def test_secret_from_environment(tmp_path, monkeypatch):
    f = write(tmp_path / "a.csv")
    monkeypatch.setenv("PSEUDONYM_SECRET", "ausUmgebung")
    assert ps.main(["encrypt", str(f)]) == 0
    assert ps.encrypt_value(ps.derive_key("ausUmgebung"), "Max") in (tmp_path / "a_pseudo.csv").read_text()


def test_anonymize_needs_no_secret(tmp_path, monkeypatch):
    f = write(tmp_path / "a.csv")
    monkeypatch.delenv("PSEUDONYM_SECRET", raising=False)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": pytest.fail("darf nicht fragen"))
    assert ps.main(["anonymize", str(f)]) == 0
    assert (tmp_path / "a_anonym.csv").read_text(encoding="utf-8") == "Vorname;Familienname\n;\n"


def test_output_option_is_refused_for_zip_with_several_files(tmp_path, capsys):
    zp = tmp_path / "export.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.writestr("a.csv", GOOD)
        zf.writestr("b.csv", GOOD)
    assert ps.main(["encrypt", str(zp), "--secret", "s", "--output", str(tmp_path / "x.csv")]) == 1
    assert not (tmp_path / "x.csv").exists()


def test_error_messages_are_german_sentences(tmp_path, capsys):
    (tmp_path / "kaputt.xlsx").write_bytes(b"das ist keine Excel-Datei")
    assert ps.main(["encrypt", str(tmp_path / "kaputt.xlsx"), "--secret", "s"]) == 1
    err = capsys.readouterr().err
    assert "Excel" in err and "zip file" not in err
    assert ps.main(["encrypt", str(tmp_path / "fehlt.csv"), "--secret", "s"]) == 1
    assert "nicht gefunden" in capsys.readouterr().err


def test_many_files_in_one_run(tmp_path):
    for i in range(60):
        write(tmp_path / "in" / f"liste_{i:03d}.csv", f"Vorname;Matrikelnummer\nPerson{i};{10000000 + i}\n")
    assert ps.main(["encrypt", str(tmp_path / "in"), "--secret", "s", "--output-dir", str(tmp_path / "out")]) == 0
    assert len(list((tmp_path / "out").iterdir())) == 60


# ---------- Fehlende Python-Pakete ----------

INSTALL = "-m pip install cryptography openpyxl"


def run_without(package, args, cwd):
    """Startet die Kommandozeile in einem eigenen Prozess, in dem sich ein Paket nicht laden laesst."""
    code = ("import sys; sys.modules[%r] = None; import pseudonym; "
            "sys.exit(pseudonym.main(sys.argv[1:]))" % package)
    env = dict(os.environ, PYTHONPATH=str(Path(ps.__file__).resolve().parent),
               PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8",
               COLUMNS="30")  # schmale Konsole: der Installationsbefehl darf nicht umbrechen
    env.pop("PSEUDONYM_SECRET", None)
    return subprocess.run([sys.executable, "-c", code] + args, cwd=str(cwd), env=env,
                          stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, encoding="utf-8", timeout=120)


def write_xlsx(path):
    from openpyxl import Workbook
    wb = Workbook()
    wb.active.append(["Vorname", "Familienname"])
    wb.active.append(["Max", "Muster"])
    wb.save(str(path))
    return path


def test_missing_cryptography_is_explained_before_the_secret_prompt(tmp_path):
    f = write(tmp_path / "a.csv")
    r = run_without("cryptography", ["encrypt", str(f)], tmp_path)
    assert r.returncode == 1
    assert "Traceback" not in r.stderr
    assert "FEHLER" in r.stderr and "'cryptography'" in r.stderr
    assert INSTALL in r.stderr and sys.executable in r.stderr
    assert "Secret:" not in r.stderr + r.stdout
    assert not (tmp_path / "a_pseudo.csv").exists()


def test_anonymize_works_without_cryptography(tmp_path):
    f = write(tmp_path / "a.csv")
    r = run_without("cryptography", ["anonymize", str(f)], tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "a_anonym.csv").exists()


def test_missing_openpyxl_stops_a_run_with_excel_files_before_anything_is_written(tmp_path):
    write(tmp_path / "in" / "a.csv")
    write_xlsx(tmp_path / "in" / "t.xlsx")
    r = run_without("openpyxl", ["encrypt", str(tmp_path / "in"), "--secret", "s",
                                 "--output-dir", str(tmp_path / "out")], tmp_path)
    assert r.returncode == 1
    assert "Traceback" not in r.stderr
    assert "'openpyxl'" in r.stderr and INSTALL in r.stderr
    assert not (tmp_path / "out").exists()


def test_csv_files_work_without_openpyxl(tmp_path):
    f = write(tmp_path / "a.csv")
    r = run_without("openpyxl", ["encrypt", str(f), "--secret", "s"], tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "a_pseudo.csv").exists()


def test_version_output_names_missing_packages(tmp_path):
    r = run_without("cryptography", ["--version"], tmp_path)
    assert r.returncode == 0
    assert ps.__version__ in r.stdout
    assert "'cryptography'" in r.stdout and INSTALL in r.stdout
    assert sys.executable + " " + INSTALL in r.stdout.replace('"', "")


def test_package_hint_uses_singular_and_plural():
    assert ps.package_hint(["openpyxl"]).startswith("Python-Paket 'openpyxl' fehlt oder laesst sich")
    assert ps.package_hint(["cryptography", "openpyxl"]).startswith(
        "Python-Pakete 'cryptography' und 'openpyxl' fehlen oder lassen sich")


def test_version_output_is_plain_when_all_packages_are_there(tmp_path, capsys):
    with pytest.raises(SystemExit):
        ps.main(["--version"])
    assert capsys.readouterr().out.strip().endswith(ps.__version__)


def test_library_calls_report_a_missing_package_as_pseudo_error(tmp_path, monkeypatch):
    xlsx = write_xlsx(tmp_path / "t.xlsx")
    monkeypatch.setitem(sys.modules, "openpyxl", None)
    with pytest.raises(ps.PseudoError, match="openpyxl"):
        ps.process_file(str(xlsx), str(tmp_path / "t_pseudo.xlsx"), "s", "encrypt")
    monkeypatch.setattr(ps, "Cipher", None)
    with pytest.raises(ps.PseudoError, match="cryptography"):
        ps.derive_key("s")
