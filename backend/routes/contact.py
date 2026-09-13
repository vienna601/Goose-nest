"""Inquiry endpoints — the contract in frontend/README.md. Logic lives in
services/agent_service.py (owner: A)."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services import agent_service as svc

router = APIRouter()


class CreateInquiryBody(BaseModel):
    listing_id: str
    message: str = ""            # preview only; the backend composes what gets typed
    sender_name: str = ""
    sender_email: str = ""
    sender_phone: Optional[str] = None
    questions: list[str] = []
    preferred_times: list[str] = []   # "MM/DD/YYYY HH:MM", up to 3


class ApproveBody(BaseModel):
    approved_by: str = ""


def _http(exc: svc.ServiceError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=str(exc))


@router.post("/inquiries")
async def create_inquiry(body: CreateInquiryBody):
    try:
        inquiry = await svc.start(body.listing_id, body.sender_name, body.sender_email,
                                  body.sender_phone, body.questions, body.preferred_times)
    except svc.ServiceError as exc:
        raise _http(exc) from None
    return inquiry.model_dump(mode="json")


@router.get("/inquiries/{inquiry_id}")
def get_inquiry(inquiry_id: str):
    try:
        return svc.get(inquiry_id).model_dump(mode="json")
    except svc.ServiceError as exc:
        raise _http(exc) from None


@router.post("/inquiries/{inquiry_id}/approve")
async def approve_inquiry(inquiry_id: str, body: ApproveBody):
    try:
        return (await svc.approve(inquiry_id, body.approved_by)).model_dump(mode="json")
    except svc.ServiceError as exc:
        raise _http(exc) from None


@router.post("/inquiries/{inquiry_id}/cancel")
async def cancel_inquiry(inquiry_id: str):
    try:
        return (await svc.cancel(inquiry_id)).model_dump(mode="json")
    except svc.ServiceError as exc:
        raise _http(exc) from None


@router.get("/inquiries/{inquiry_id}/events")
async def inquiry_events(inquiry_id: str):
    try:
        svc.get(inquiry_id)          # 404 before opening a stream
    except svc.ServiceError as exc:
        raise _http(exc) from None
    return StreamingResponse(
        svc.events(inquiry_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
