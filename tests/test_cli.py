from __future__ import annotations

from omp.cli.main import main


def test_cli_write_inspect_query(tmp_path, capsys):
    path = tmp_path / "cli.orb"

    assert (
        main(
            [
                "write",
                "--name",
                "Abhishek",
                "--out",
                str(path),
                "--memory",
                "kind:fact|summary:Building OMP|content:Portable memory|tags:protocol",
                "--pref",
                "language=English",
            ]
        )
        == 0
    )

    assert main(["inspect", str(path)]) == 0
    inspect_output = capsys.readouterr().out
    assert "OMP Tier   : OPEN (unverified)" in inspect_output

    assert main(["query", str(path), "--text", "portable"]) == 0
    query_output = capsys.readouterr().out
    assert "Building OMP" in query_output


def test_cli_proto_access(tmp_path, capsys):
    assert main(["proto", "list"]) == 0
    list_output = capsys.readouterr().out
    assert "memory.proto" in list_output

    assert main(["proto", "show", "memory"]) == 0
    show_output = capsys.readouterr().out
    assert "message MemoryRecord" in show_output

    out = tmp_path / "schema.txt"
    assert main(["proto", "bundle", "--out", str(out)]) == 0
    assert "message OrbPassport" in out.read_text(encoding="utf-8")
