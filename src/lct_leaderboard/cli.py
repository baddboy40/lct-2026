import argparse
import json
import sys
from typing import List, Optional

from .catalog import RuleCatalog
from .datasets import manifest_to_datasets
from .io import read_json, write_json
from .validator import validate_result_geojson


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="lct-leaderboard")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--catalog", required=True)
    validate_parser.add_argument("--result", required=True)
    validate_parser.add_argument("--input")
    validate_parser.add_argument("--out")

    import_parser = subparsers.add_parser("import-scenes")
    import_parser.add_argument("--manifest", required=True)
    import_parser.add_argument("--out", required=True)

    args = parser.parse_args(argv)

    if args.command == "validate":
        return _validate(args)
    if args.command == "import-scenes":
        return _import_scenes(args)

    parser.error(f"Unknown command: {args.command}")
    return 2


def _validate(args: argparse.Namespace) -> int:
    catalog = RuleCatalog.from_dict(read_json(args.catalog))
    result_geojson = read_json(args.result)
    input_geojson = read_json(args.input) if args.input else None
    report = validate_result_geojson(result_geojson, catalog, input_geojson)
    data = report.to_dict()

    if args.out:
        write_json(args.out, data)
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))

    return 0 if report.accepted else 1


def _import_scenes(args: argparse.Namespace) -> int:
    manifest = read_json(args.manifest)
    datasets = manifest_to_datasets(manifest)
    write_json(args.out, {"datasets": datasets})
    print(f"Imported {len(datasets)} datasets to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
