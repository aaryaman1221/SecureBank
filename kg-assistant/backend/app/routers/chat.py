"""
Chat router — streaming chat endpoint.
Stub for Phase 1; full implementation in Phase 4.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.post("/chat")
async def chat(request: Request):
    """
    Streaming chat endpoint via SSE.
    Phase 1: Returns a stub response.
    Phase 4: Will do GraphRAG retrieval + Gemini streaming.
    """
    body = await request.json()
    chat_req = ChatRequest(**body)

    async def event_generator():
        # Stub: echo back the question with a placeholder answer
        intro = f"Chat is not yet connected to the knowledge graph. You asked: \"{chat_req.question}\""
        for word in intro.split(" "):
            if await request.is_disconnected():
                break
            yield {
                "event": "token",
                "data": json.dumps({"type": "token", "content": word + " "}),
            }

        yield {
            "event": "done",
            "data": json.dumps({"type": "done", "content": ""}),
        }

    return EventSourceResponse(event_generator())
