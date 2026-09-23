import json
from pathlib import Path
from typing import List, Union

from pydantic import ValidationError

from src.domain.ports.harvester import CompanyTarget
from src.domain.ports.target_loader import TargetLoaderError, TargetLoaderPort


class JsonTargetLoaderAdapter(TargetLoaderPort):
    """Adapter for loading and validating company targets from JSON files."""

    def load_targets(self, file_path: Union[str, Path]) -> List[CompanyTarget]:
        path = Path(file_path)

        if not path.is_file():
            raise TargetLoaderError(f"Targets configuration file not found: {file_path}")

        try:
            content = path.read_text(encoding="utf-8")
        except (PermissionError, OSError) as exc:
            raise TargetLoaderError(f"Cannot read targets file '{file_path}': {exc}") from exc

        try:
            raw_data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise TargetLoaderError(f"Invalid JSON in targets file '{file_path}': {exc}") from exc

        if not isinstance(raw_data, list):
            raise TargetLoaderError(
                f"Targets configuration root must be a list, got {type(raw_data).__name__}"
            )

        targets: List[CompanyTarget] = []
        for index, item in enumerate(raw_data):
            if not isinstance(item, dict):
                raise TargetLoaderError(
                    f"Item at index {index} must be a dictionary, got {type(item).__name__}"
                )
            try:
                target = CompanyTarget.model_validate(item)
                targets.append(target)
            except (ValidationError, Exception) as exc:
                raise TargetLoaderError(
                    f"Invalid target specification at index {index}: {exc}"
                ) from exc

        return targets
