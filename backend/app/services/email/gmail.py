from __future__ import annotations

import base64
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.token import OAuthToken

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _client_config() -> dict[str, Any]:
    s = get_settings()
    return {
        "web": {
            "client_id": s.google_client_id,
            "client_secret": s.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [s.google_redirect_uri],
        }
    }


def build_auth_url(state: str) -> tuple[str, str | None]:
    s = get_settings()
    flow = Flow.from_client_config(
        _client_config(),
        scopes=GMAIL_SCOPES,
        state=state,
        autogenerate_code_verifier=True,
    )
    flow.redirect_uri = s.google_redirect_uri
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    return auth_url, flow.code_verifier


def exchange_code_for_token(
    code: str,
    db: Session,
    *,
    state: str | None = None,
    code_verifier: str | None = None,
) -> OAuthToken:
    s = get_settings()
    flow = Flow.from_client_config(
        _client_config(),
        scopes=GMAIL_SCOPES,
        state=state,
        code_verifier=code_verifier,
    )
    flow.redirect_uri = s.google_redirect_uri
    flow.fetch_token(code=code)
    creds = flow.credentials

    # Pull profile email
    user_email = ""
    try:
        svc = build("gmail", "v1", credentials=creds, cache_discovery=False)
        prof = svc.users().getProfile(userId="me").execute()
        user_email = prof.get("emailAddress", "")
    except Exception:
        pass

    token = db.query(OAuthToken).filter_by(provider="gmail").one_or_none()
    if token is None:
        token = OAuthToken(provider="gmail")
        db.add(token)
    token.access_token = creds.token
    token.refresh_token = creds.refresh_token or token.refresh_token
    token.token_uri = creds.token_uri
    token.client_id = creds.client_id
    token.client_secret = creds.client_secret
    token.scopes = " ".join(creds.scopes or [])
    token.expires_at = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None
    token.user_email = user_email
    db.commit()
    db.refresh(token)
    return token


def credentials_from_token(token: OAuthToken) -> Credentials:
    creds = Credentials(
        token=token.access_token,
        refresh_token=token.refresh_token,
        token_uri=token.token_uri,
        client_id=token.client_id,
        client_secret=token.client_secret,
        scopes=(token.scopes or "").split(" ") if token.scopes else GMAIL_SCOPES,
    )
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
    return creds


def get_gmail_service(token: OAuthToken):
    creds = credentials_from_token(token)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def list_message_ids(service, query: str, max_results: int = 200) -> list[str]:
    """Return message IDs matching the Gmail search query."""
    out: list[str] = []
    next_token: str | None = None
    while len(out) < max_results:
        req = service.users().messages().list(
            userId="me",
            q=query,
            pageToken=next_token,
            maxResults=min(100, max_results - len(out)),
        )
        resp = req.execute()
        out.extend(m["id"] for m in resp.get("messages", []))
        next_token = resp.get("nextPageToken")
        if not next_token:
            break
    return out


def fetch_message(service, message_id: str) -> dict[str, Any]:
    """Fetch a full message and return a normalized dict."""
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    sender = headers.get("from", "")
    subject = headers.get("subject", "")
    date_str = headers.get("date", "")
    received_at = parsedate_to_datetime(date_str) if date_str else datetime.now(timezone.utc)
    if received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=timezone.utc)

    body_text = _extract_body_text(msg.get("payload", {}))

    return {
        "gmail_message_id": msg["id"],
        "gmail_thread_id": msg["threadId"],
        "sender": sender,
        "subject": subject,
        "snippet": msg.get("snippet", ""),
        "body_text": body_text,
        "received_at": received_at,
    }


def _extract_body_text(payload: dict[str, Any]) -> str:
    """Walk the MIME tree and return the concatenated text/plain (or stripped HTML)."""
    if not payload:
        return ""
    mime = payload.get("mimeType", "")
    body = payload.get("body", {})
    data = body.get("data")
    if mime == "text/plain" and data:
        return _b64(data)
    if mime == "text/html" and data:
        return _strip_html(_b64(data))
    parts = payload.get("parts") or []
    chunks: list[str] = []
    for p in parts:
        chunks.append(_extract_body_text(p))
    return "\n".join(c for c in chunks if c)


def _b64(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode()).decode("utf-8", errors="replace")


def _strip_html(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    return soup.get_text("\n", strip=True)
