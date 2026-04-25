from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.schemas import ProfileIn, ProfileOut, ResumeVariantOut
from app.db import get_db
from app.models import Profile, ResumeVariant

RESUME_DIR = Path("/app/storage/resumes")
RESUME_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileOut | None)
def get_profile(db: Session = Depends(get_db)) -> Profile | None:
    return db.query(Profile).first()


@router.put("", response_model=ProfileOut)
def upsert_profile(payload: ProfileIn, db: Session = Depends(get_db)) -> Profile:
    p = db.query(Profile).first()
    data = payload.model_dump()
    if p is None:
        p = Profile(**data)
        db.add(p)
    else:
        for k, v in data.items():
            setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@router.get("/resumes", response_model=list[ResumeVariantOut])
def list_resumes(db: Session = Depends(get_db)) -> list[ResumeVariant]:
    return db.query(ResumeVariant).all()


@router.post("/resumes", response_model=ResumeVariantOut, status_code=201)
def upload_resume(
    name: str = Form(...),
    tags: str = Form(""),  # comma-separated
    is_default: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ResumeVariant:
    profile = db.query(Profile).first()
    if profile is None:
        raise HTTPException(400, "Create profile first")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "PDF only")

    out_path = RESUME_DIR / f"{uuid4()}.pdf"
    with open(out_path, "wb") as f:
        f.write(file.file.read())

    parsed = _try_parse_pdf(out_path)
    if is_default:
        for v in db.query(ResumeVariant).filter_by(profile_id=profile.id).all():
            v.is_default = False
    rv = ResumeVariant(
        profile_id=profile.id,
        name=name,
        tags=[t.strip() for t in tags.split(",") if t.strip()],
        pdf_path=str(out_path),
        parsed_text=parsed,
        is_default=is_default,
    )
    db.add(rv)
    db.commit()
    db.refresh(rv)
    return rv


@router.delete("/resumes/{variant_id}", status_code=204)
def delete_resume(variant_id: UUID, db: Session = Depends(get_db)) -> None:
    rv = db.get(ResumeVariant, variant_id)
    if rv is None:
        return
    try:
        Path(rv.pdf_path).unlink(missing_ok=True)
    except Exception:
        pass
    db.delete(rv)
    db.commit()


def _try_parse_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    except Exception:
        return ""
