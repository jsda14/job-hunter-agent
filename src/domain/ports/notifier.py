from abc import ABC, abstractmethod
from typing import List, Tuple

from src.domain.models.job import JobEvaluation, JobRaw


class NotifierError(Exception):
    """Excepción base del dominio para fallos en el subsistema de notificación."""
    pass


class NotifierConfigurationError(NotifierError):
    """Lanzada cuando faltan credenciales o configuraciones requeridas para notificar."""
    pass


class NotifierDeliveryError(NotifierError):
    """Lanzada cuando falla la entrega de una notificación al canal externo (HTTP error, timeout, red)."""
    pass


class JobNotifierPort(ABC):
    """Port defining the interface for notifying or displaying evaluated jobs."""

    @abstractmethod
    async def notify(self, jobs: List[Tuple[JobRaw, JobEvaluation]]) -> int:
        """Notify or display actionable jobs.

        Args:
            jobs: List of (JobRaw, JobEvaluation) pairs.

        Returns:
            Count of successfully notified items.
        """
        raise NotImplementedError
