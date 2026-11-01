# public image proxy, today only for football-data crests and competition logos
# the download + cache lives in services/crest_cache.py

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from services.crest_cache import CrestCache, CrestNotAllowed, CrestUpstreamError, get_crest_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/img", tags=["img"])

# a crest url never changes its picture, so browsers may keep it for a week
CREST_CACHE_CONTROL = "public, max-age=604800, immutable"


# HEAD too, so `curl -I` and link checkers get the real headers
@router.api_route(
    "/crest",
    methods=["GET", "HEAD"],
    response_class=Response,
    responses={200: {"content": {"image/png": {}, "image/svg+xml": {}}}, 400: {}, 502: {}},
)
def get_crest(
    url: str = Query(..., description="https://crests.football-data.org/..."),
    cache: CrestCache = Depends(get_crest_cache),
) -> Response:
    try:
        data, content_type = cache.get(url)
    except CrestNotAllowed:
        raise HTTPException(status_code=400, detail="Niedozwolony adres obrazka")
    except CrestUpstreamError as exc:
        logger.warning("crest proxy: %s", exc)
        raise HTTPException(status_code=502, detail="Nie udało się pobrać obrazka")
    headers = {"Cache-Control": CREST_CACHE_CONTROL, "X-Content-Type-Options": "nosniff"}
    # svg could carry scripts, keep it inert when opened directly
    if content_type == "image/svg+xml":
        headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
    return Response(content=data, media_type=content_type, headers=headers)
