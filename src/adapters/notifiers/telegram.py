import html
import os
from typing import List, Optional, Tuple
import httpx

from src.domain.models.job import JobEvaluation, JobRaw
from src.domain.ports.notifier import (
    JobNotifierPort,
    NotifierConfigurationError,
    NotifierDeliveryError,
)


class TelegramNotifierAdapter(JobNotifierPort):
    """Adaptador de notificación vía Telegram Bot API utilizando httpx asíncrono."""

    TELEGRAM_API_BASE_URL: str = "https://api.telegram.org"

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """Inicializa el adaptador resolviendo credenciales vía argumentos o variables de entorno.

        Args:
            bot_token: Token del bot de Telegram. Si es None, lee TELEGRAM_BOT_TOKEN de entorno.
            chat_id: ID del chat o canal receptor. Si es None, lee TELEGRAM_CHAT_ID de entorno.
            client: Instancia opcional inyectada de httpx.AsyncClient para pruebas o reuso de conexiones.
        """
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.client = client

    def _format_message(self, job: JobRaw, evaluation: JobEvaluation) -> str:
        """Genera el cuerpo del mensaje en formato HTML seguro para Telegram.

        Args:
            job: Instancia canónica de JobRaw.
            evaluation: Evaluación asociada con score, stack y pitch.

        Returns:
            String formateado en HTML apto para parse_mode="HTML" en Telegram.
        """
        title_escaped = html.escape(job.title, quote=False)
        company_escaped = html.escape(job.company, quote=False)

        stack_list = evaluation.tech_stack_detected or []
        stack_str = ", ".join(stack_list) if stack_list else "N/A"
        stack_escaped = html.escape(stack_str, quote=False)

        pitch_raw = evaluation.tailored_pitch
        if not pitch_raw or not pitch_raw.strip():
            pitch_str = "Sin pitch generado"
        else:
            pitch_str = pitch_raw
        pitch_escaped = html.escape(pitch_str, quote=False)

        message = (
            f"<b>🎯 [VACANTE]</b> <a href=\"{job.url}\">{title_escaped}</a>\n"
            f"<b>🏢 [EMPRESA]</b> {company_escaped}\n"
            f"<b>📊 [FIT]</b> {evaluation.fit_score:.1f}%\n"
            f"<b>🛠 [STACK]</b> {stack_escaped}\n\n"
            f"<b>💡 [PITCH PROPUESTO]</b>\n"
            f"<pre>{pitch_escaped}</pre>"
        )
        return message

    async def notify(self, jobs: List[Tuple[JobRaw, JobEvaluation]]) -> int:
        """Envía cada vacante accionable como mensaje individual a Telegram.

        Args:
            jobs: Lista de tuplas (JobRaw, JobEvaluation).

        Returns:
            Número total de mensajes entregados exitosamente.

        Raises:
            NotifierConfigurationError: Si bot_token o chat_id no están definidos al procesar vacantes.
            NotifierDeliveryError: Si ocurre un error de red, timeout o respuesta HTTP >= 400 de Telegram.
        """
        if not jobs:
            return 0

        if not self.bot_token or not self.bot_token.strip() or not self.chat_id or not self.chat_id.strip():
            raise NotifierConfigurationError(
                "Credenciales de Telegram incompletas o no configuradas. "
                "Asegúrate de definir TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID."
            )

        url = f"{self.TELEGRAM_API_BASE_URL}/bot{self.bot_token.strip()}/sendMessage"

        if self.client is not None:
            return await self._dispatch_jobs(self.client, url, jobs)

        async with httpx.AsyncClient(timeout=10.0) as client:
            return await self._dispatch_jobs(client, url, jobs)

    async def _dispatch_jobs(
        self,
        client: httpx.AsyncClient,
        url: str,
        jobs: List[Tuple[JobRaw, JobEvaluation]],
    ) -> int:
        """Despacha secuencialmente las notificaciones de vacantes mediante el cliente HTTP."""
        count = 0
        for job, evaluation in jobs:
            text = self._format_message(job, evaluation)
            payload = {
                "chat_id": self.chat_id.strip(),
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }

            try:
                response = await client.post(url, json=payload)
                if response.status_code >= 400:
                    raise NotifierDeliveryError(
                        f"Fallo al entregar notificación a Telegram (HTTP {response.status_code}): {response.text}"
                    )
            except httpx.RequestError as exc:
                raise NotifierDeliveryError(
                    f"Error de red o timeout al comunicar con Telegram API: {exc}"
                ) from exc

            count += 1

        return count
