from __future__ import annotations

import argparse
import sys
from pathlib import Path

import omp
from omp.exceptions import OMPError
from omp.schema.convert import to_json, to_markdown
from omp.schema.version import PACKAGE_VERSION, PROTOCOL_VERSION


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except OMPError as exc:
        print(f"omp: {exc}", file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="omp")
    sub = parser.add_subparsers(required=True)

    write = sub.add_parser("write", help="create a .orb file")
    write.add_argument("--name", default="", help="identity display name")
    write.add_argument("--out", required=True, help="output .orb path")
    write.add_argument("--memory", action="append", default=[], help="kind:fact|summary:...|tags:a,b")
    write.add_argument("--pref", action="append", default=[], help="key=value")
    write.add_argument("--compress", action="store_true", help="zstd-compress chunks")
    write.set_defaults(func=_cmd_write)

    read = sub.add_parser("read", help="read a .orb file")
    read.add_argument("path")
    read.add_argument("--format", choices=["json", "text", "markdown"], default="text")
    read.add_argument("--out")
    read.set_defaults(func=_cmd_read)

    inspect = sub.add_parser("inspect", help="show a human-readable summary")
    inspect.add_argument("path")
    inspect.set_defaults(func=_cmd_inspect)

    query = sub.add_parser("query", help="query memories")
    query.add_argument("path")
    query.add_argument("--text", default="")
    query.add_argument("--kind")
    query.add_argument("--tag", action="append", default=[])
    query.add_argument("--limit", type=int, default=5)
    query.set_defaults(func=_cmd_query)

    merge = sub.add_parser("merge", help="merge two passports")
    merge.add_argument("a")
    merge.add_argument("b")
    merge.add_argument("--out", required=True)
    merge.add_argument(
        "--strategy",
        choices=["latest", "union", "source_a", "source_b"],
        default="latest",
    )
    merge.set_defaults(func=_cmd_merge)

    export = sub.add_parser("export", help="export a .orb file")
    export.add_argument("path")
    export.add_argument("--format", choices=["json", "markdown"], required=True)
    export.add_argument("--out", required=True)
    export.set_defaults(func=_cmd_export)

    proto = sub.add_parser("proto", help="inspect bundled protobuf schemas")
    proto_sub = proto.add_subparsers(required=True)
    proto_list = proto_sub.add_parser("list", help="list bundled .proto files")
    proto_list.set_defaults(func=_cmd_proto_list)
    proto_show = proto_sub.add_parser("show", help="print one bundled .proto file")
    proto_show.add_argument("name")
    proto_show.set_defaults(func=_cmd_proto_show)
    proto_bundle = proto_sub.add_parser("bundle", help="print or write all bundled .proto files")
    proto_bundle.add_argument("--out")
    proto_bundle.set_defaults(func=_cmd_proto_bundle)

    verify = sub.add_parser("verify", help="verify checksum and open-tier status")
    verify.add_argument("path")
    verify.set_defaults(func=_cmd_verify)

    version = sub.add_parser("version", help="show package and protocol versions")
    version.set_defaults(func=_cmd_version)
    return parser


def _cmd_write(args: argparse.Namespace) -> int:
    memories = [_parse_memory(value) for value in args.memory]
    preferences = dict(_parse_pref(value) for value in args.pref)
    omp.write(
        args.out,
        identity={"display_name": args.name},
        memories=memories,
        preferences=preferences,
        compress=args.compress,
    )
    print(f"wrote {args.out}")
    return 0


def _cmd_read(args: argparse.Namespace) -> int:
    passport = omp.read(args.path)
    if args.format == "json":
        output = to_json(passport)
    elif args.format == "markdown":
        output = to_markdown(passport)
    else:
        output = omp.inject(passport, target="generic")
    _write_or_print(output, args.out)
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    omp.inspect(args.path)
    return 0


def _cmd_query(args: argparse.Namespace) -> int:
    passport = omp.read(args.path)
    matches = omp.query(
        passport,
        text=args.text,
        kind=args.kind,
        tags=args.tag,
        limit=args.limit,
    )
    for match in matches:
        print(f"{match.score:.3f}\t{match.memory.summary}")
    return 0


def _cmd_merge(args: argparse.Namespace) -> int:
    merged = omp.merge(omp.read(args.a), omp.read(args.b), strategy=args.strategy)
    omp.write(args.out, passport=merged)
    print(f"wrote {args.out}")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    passport = omp.read(args.path)
    omp.export(passport, format=args.format, path=args.out)
    print(f"wrote {args.out}")
    return 0


def _cmd_proto_list(args: argparse.Namespace) -> int:
    for name in omp.list_proto_files():
        print(name)
    return 0


def _cmd_proto_show(args: argparse.Namespace) -> int:
    print(omp.get_proto_source(args.name), end="")
    return 0


def _cmd_proto_bundle(args: argparse.Namespace) -> int:
    output = omp.get_proto_bundle()
    _write_or_print(output, args.out)
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    passport = omp.read(args.path)
    print("checksum valid")
    print("signature none (open tier)")
    print(f"verified {passport.verified}")
    return 0


def _cmd_version(args: argparse.Namespace) -> int:
    print(f"omp package {PACKAGE_VERSION}")
    print(f"protocol {PROTOCOL_VERSION}")
    return 0


def _parse_memory(value: str) -> dict:
    result: dict[str, object] = {}
    for part in value.split("|"):
        if not part:
            continue
        key, sep, raw = part.partition(":")
        if not sep:
            raise OMPError(f"invalid --memory segment: {part}")
        if key == "tags":
            result[key] = [tag.strip() for tag in raw.split(",") if tag.strip()]
        else:
            result[key] = raw
    return result


def _parse_pref(value: str) -> tuple[str, str]:
    key, sep, raw = value.partition("=")
    if not sep:
        raise OMPError(f"invalid --pref value: {value}")
    return key, raw


def _write_or_print(output: str, path: str | None) -> None:
    if path:
        Path(path).write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    raise SystemExit(main())
