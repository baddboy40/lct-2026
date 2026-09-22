import json
import zipfile
from pathlib import Path
from typing import Any, Dict, Union


JsonObject = Dict[str, Any]


def read_text(path: Union[str, Path]) -> str:
    return read_bytes(path).decode("utf-8-sig")


def read_bytes(path: Union[str, Path]) -> bytes:
    raw_path = str(path)
    if ".zip!" in raw_path:
        archive_path, member_path = raw_path.split(".zip!", 1)
        archive_path = archive_path + ".zip"
        member_path = member_path.lstrip("/\\")
        with zipfile.ZipFile(archive_path) as archive:
            with archive.open(member_path) as file:
                return file.read()

    return Path(raw_path).read_bytes()


def read_json(path: Union[str, Path]) -> JsonObject:
    return json.loads(read_text(path))


def write_json(path: Union[str, Path], data: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
