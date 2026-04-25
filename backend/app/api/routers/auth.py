from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.services.email import gmail

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory state cache (single-user MVP). Migrate to Redis if multi-user.
_oauth_states: dict[str, bool] = {}


@router.get("/gmail/start")
def gmail_start():
    s = get_settings()
    if not s.google_client_id or not s.google_client_secret:
        raise HTTPException(500, "GOOGLE_CLIENT_ID / SECRET not configured")
    state = secrets.token_urlsafe(16)
    _oauth_states[state] = True
    return RedirectResponse(gmail.build_auth_url(state))


@router.get("/gmail/callback")
def gmail_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    if state not in _oauth_states:
        raise HTTPException(400, "invalid state")
    _oauth_states.pop(state, None)
    token = gmail.exchange_code_for_token(code, db)
    return {"connected": True, "user_email": token.user_email}


@router.get("/gmail/status")
def gmail_status(db: Session = Depends(get_db)):
    from app.models import OAuthToken

    t = db.query(OAuthToken).filter_by(provider="gmail").one_or_none()
    if t is None:
        return {"connected": False}
    return {
        "connected": True,
        "user_email": t.user_email,
        "last_scanned_at": t.last_scanned_at.isoformat() if t.last_scanned_at else None,
    }


@router.delete("/gmail")
def gmail_disconnect(db: Session = Depends(get_db)):
    from app.models import OAuthToken

    db.query(OAuthToken).filter_by(provider="gmail").delete()
    db.commit()
    return {"disconnected": True}
