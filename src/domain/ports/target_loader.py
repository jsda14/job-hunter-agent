from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Union

from src.domain.ports.harvester import CompanyTarget


class TargetLoaderError(Exception):
    """Domain exception raised when loading or validating target company configurations fails."""
    pass


class TargetLoaderPort(ABC):
    """Port defining the interface for loading and parsing company targets from configuration."""

    @abstractmethod
    def load_targets(self, file_path: Union[str, Path]) -> List[CompanyTarget]:
        """Read and validate a configuration file returning a list of CompanyTarget.

        Args:
            file_path: Path to configuration file.

        Returns:
            List of validated CompanyTarget instances.

        Raises:
            TargetLoaderError: If file does not exist, has invalid JSON syntax or schema errors.
        """
        raise NotImplementedError
