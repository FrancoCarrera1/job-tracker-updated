from __future__ import annotations

import httpx
import structlog

from app.config import get_settings

log = structlog.get_logger()


def send_telegram(text: str, parse_mode: str = "Markdown") -> bool:
    """Send a message via Telegram Bot API. Returns True on 200 OK."""
    s = get_settings()
    if not s.telegram_bot_token or not s.telegram_chat_id:
        log.warning("telegram.skip", reason="not_configured")
        return False
    url = f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage"
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(
                url,
                json={
                    "chat_id": s.telegram_chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                },
            )
        if r.status_code != 200:
            log.warning("telegram.failed", status=r.status_code, body=r.text)
            return False
        return True
    except Exception as e:
        log.warning("telegram.error", error=str(e))
        return False


def notify_paused(
    *,
    company: str,
    role: str,
    ats: str,
    reason: str,
    paused_session_id: str,
    message: str,
) -> bool:
    s = get_settings()
    deep_link = f"{s.dashboard_base_url}/paused/{paused_session_id}"
    body = (
        f"*Paused — human input needed*\n\n"
        f"*{role}* @ *{company}*\n"
        f"ATS: `{ats}` · Reason: `{reason}`\n\n"
        f"{message}\n\n"
        f"[Open in dashboard]({deep_link})"
    )
    return send_telegram(body)


def notify_applied(*, company: str, role: str, dry_run: bool) -> bool:
    prefix = "[DRY-RUN] " if dry_run else ""
    return send_telegram(f"{prefix}Applied: *{role}* @ *{company}*")


def notify_kill_switch() -> bool:
    return send_telegram("Kill switch tripped — all automation halted.")
