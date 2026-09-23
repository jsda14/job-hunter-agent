from typing import Dict, List, Optional

from src.domain.models.job import JobRaw, SourcePlatform
from src.domain.ports.harvester import (
    CompanyTarget,
    HarvesterConnectionError,
    JobHarvesterPort,
    UnsupportedPlatformError,
)


class CompositeHarvesterAdapter:
    """Composite adapter that registers and dispatches job harvesting across multiple platforms."""

    def __init__(
        self,
        harvesters: Optional[Dict[SourcePlatform, JobHarvesterPort]] = None,
    ) -> None:
        """Initialize the composite with an optional dictionary of harvesters indexed by SourcePlatform."""
        self._harvesters: Dict[SourcePlatform, JobHarvesterPort] = {}
        if harvesters:
            self._harvesters.update(harvesters)

    def register(self, platform: SourcePlatform, harvester: JobHarvesterPort) -> None:
        """Register or overwrite a harvester adapter for a specific platform."""
        self._harvesters[platform] = harvester

    async def fetch_jobs_from_targets(self, targets: List[CompanyTarget]) -> List[JobRaw]:
        """Dispatch harvesting to registered platform adapters and consolidate results.

        Args:
            targets: List of structured CompanyTarget instances.

        Returns:
            Consolidated list of JobRaw from all successful company queries.

        Raises:
            UnsupportedPlatformError: If any target specifies an unregistered platform.
        """
        if not targets:
            return []

        # RN-05: Validation of supported platforms
        for target in targets:
            if target.platform not in self._harvesters:
                raise UnsupportedPlatformError(
                    f"Platform '{target.platform.value}' is not registered in CompositeHarvesterAdapter"
                )

        consolidated_jobs: List[JobRaw] = []

        # RN-01, RN-03, RN-04: Dispatch, fault isolation, and consolidation
        for target in targets:
            harvester = self._harvesters[target.platform]
            try:
                jobs = await harvester.fetch_jobs(target.company_slug)
                consolidated_jobs.extend(jobs)
            except HarvesterConnectionError:
                # Isolate connection error per target so other targets continue
                continue

        return consolidated_jobs
