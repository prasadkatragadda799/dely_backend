"""Public legal HTML routes (Privacy Policy, Terms, index)."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.web.legal_content import PRIVACY_POLICY_BODY, TERMS_AND_CONDITIONS_BODY
from app.web.legal_template import render_legal_index, render_legal_page

router = APIRouter(tags=["Legal"])


@router.get("/legal", response_class=HTMLResponse)
def legal_centre():
    return HTMLResponse(content=render_legal_index())


@router.get("/privacy-policy", response_class=HTMLResponse)
def privacy_policy():
    html = render_legal_page(
        title="Privacy Policy",
        body_html=PRIVACY_POLICY_BODY,
        active="privacy",
        meta_description="Dely Cart Privacy Policy — how we handle your personal information.",
    )
    return HTMLResponse(content=html)


@router.get("/terms-and-conditions", response_class=HTMLResponse)
def terms_and_conditions():
    html = render_legal_page(
        title="Terms & Conditions",
        body_html=TERMS_AND_CONDITIONS_BODY,
        active="terms",
        meta_description="Dely Cart Terms & Conditions — rules for using our B2B platform.",
    )
    return HTMLResponse(content=html)
