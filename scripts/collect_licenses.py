"""Bundle distribution license texts and a complete dependency version inventory."""

import importlib.metadata
import json
import sys
from pathlib import Path


def main():
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    inventory = {}
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata["Name"]
        inventory[name] = distribution.version
        for relative in distribution.files or []:
            if any(
                term in relative.name.lower()
                for term in ("license", "copying", "notice")
            ):
                source = distribution.locate_file(relative)
                if source.is_file():
                    target = destination / name / str(relative)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(source.read_bytes())
    (destination / "dependencies.json").write_text(
        json.dumps(inventory, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
