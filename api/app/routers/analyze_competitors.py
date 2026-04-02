"""POST /analyze-competitors endpoint — multi-round competitor validation + scoring with AI fallback."""

import asyncio
import logging
import re

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.config import settings
from app.services.html_fetcher import fetch_page_html, validate_page_html
from app.services.openrouter import call_openrouter
from app.services.scoring import build_category_scores, clamp_score, score_page

logger = logging.getLogger(__name__)

router = APIRouter()

TARGET_COMPETITORS = 3
MAX_ROUNDS = 2


async def identify_competitors(html: str, api_key: str) -> list[dict]:
    """Ask AI for 5-6 competitor product page URLs. Returns list of {"name", "url"} dicts."""
    prompt = (
        'You are an e-commerce expert. Based on this Shopify product page HTML, identify 5-6 real competitor product pages that sell similar items.'
        ' Return a JSON array of { "name": "Brand - Product Name", "url": "https://..." } with direct product page URLs (not homepages).\n'
        '\n'
        'IMPORTANT RULES:\n'
        '- Only return real, currently-accessible product page URLs from well-known brands or established online stores.\n'
        '- Prefer large retailers whose pages are reliably up (e.g. Amazon, Sephora, Target, Ulta, Nordstrom, REI, etc.)'
        ' over small DTC brands whose URLs change frequently.\n'
        '- URLs must be real product pages, not search results, category pages, or homepages.\n'
        '- Return 5-6 candidates so we have enough even if some are unavailable.\n'
        '\n'
        'HTML:\n'
        f'{html}\n'
        '\n'
        'Return ONLY a valid JSON array, no markdown.'
    )
    try:
        result = await call_openrouter(
            prompt,
            api_key,
            model="openai/gpt-5.4-nano",
            temperature=0.5,
            max_tokens=500,
            extract_array=True,
        )
        if isinstance(result, list):
            return result[:6]
        return []
    except Exception:
        return []


def _build_fallback_prompt(user_html: str, shortfall: int, existing_names: str) -> str:
    """Build the fallback prompt — verbatim from webapp/src/app/api/analyze-competitors/route.ts."""
    already_line = f"\nALREADY INCLUDED (do NOT repeat): {existing_names}" if existing_names else ""
    return (
        'You are an e-commerce conversion expert with deep knowledge of major retail product pages.\n'
        '\n'
        f'Based on this product page HTML, identify {shortfall} real competitor products and score their product pages from your knowledge.\n'
        f'{already_line}\n'
        '\n'
        'For each competitor, return your best assessment of their typical product page quality.'
        ' Use well-known brands whose product pages you know well.\n'
        '\n'
        'Return a JSON array of objects:\n'
        '[{\n'
        '  "name": "Brand - Product Name",\n'
        '  "score": number 0-100,\n'
        '  "summary": "one-sentence assessment of their product page (max 30 words)",\n'
        '  "categories": { "title": 0-100, "images": 0-100, "pricing": 0-100, "socialProof": 0-100,'
        ' "cta": 0-100, "description": 0-100, "trust": 0-100 }\n'
        '}]\n'
        '\n'
        'Be realistic \u2014 score based on what these brands\' product pages actually look like.'
        ' Big brands often score high on images and trust but can score lower on CTA urgency or pricing anchoring.\n'
        '\n'
        'HTML of the user\'s product:\n'
        f'{user_html[:5000]}\n'
        '\n'
        'Return ONLY a valid JSON array, no markdown.'
    )


_GARBAGE_PATTERN = re.compile(
    r"404|error page|cannot be assessed|not found|unable to|access denied",
    re.IGNORECASE,
)


@router.post("/analyze-competitors")
async def analyze_competitors(request: Request):
    try:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "URL is required"})

        url = body.get("url") if isinstance(body, dict) else None
        if not url or not isinstance(url, str) or not url.strip():
            return JSONResponse(status_code=400, content={"error": "URL is required"})

        url = url.strip()

        api_key = settings.openai_api_key
        if not api_key:
            return JSONResponse(
                status_code=500,
                content={"error": "Server configuration error"},
            )

        # Step 1: Fetch the user's page
        try:
            user_html = await fetch_page_html(url)
        except Exception:
            return JSONResponse(
                status_code=400,
                content={"error": "Could not fetch that URL. Make sure it's accessible."},
            )

        # Step 2: Score user's page + identify competitors in parallel
        user_analysis, initial_candidates = await asyncio.gather(
            score_page(user_html, api_key),
            identify_competitors(user_html, api_key),
        )

        # Step 3: Multi-round validate → score loop
        scored_competitors: list[dict] = []
        tried_urls: set[str] = set()
        candidates = initial_candidates

        for round_num in range(MAX_ROUNDS):
            if len(scored_competitors) >= TARGET_COMPETITORS:
                break

            untried = [c for c in candidates if c.get("url") and c["url"] not in tried_urls]
            if not untried:
                break

            # Phase A: Validate URLs in parallel
            async def _validate_one(comp: dict) -> tuple[dict, str] | None:
                tried_urls.add(comp["url"])
                html = await validate_page_html(comp["url"])
                return (comp, html) if html else None

            validation_results = await asyncio.gather(
                *[_validate_one(c) for c in untried]
            )
            reachable = [r for r in validation_results if r is not None]

            # Phase B: Score reachable pages in parallel
            needed = TARGET_COMPETITORS - len(scored_competitors)
            to_score = reachable[: needed + 2]  # extras in case of garbage

            async def _score_one(comp: dict, html: str) -> dict | None:
                try:
                    analysis = await score_page(html, api_key)
                    cat_sum = sum(analysis["categories"].values())
                    if (
                        analysis["score"] == 0
                        or cat_sum == 0
                        or _GARBAGE_PATTERN.search(analysis["summary"])
                    ):
                        return None
                    return {
                        "name": comp["name"],
                        "url": comp["url"],
                        "score": analysis["score"],
                        "summary": analysis["summary"],
                        "categories": analysis["categories"],
                    }
                except Exception:
                    return None

            score_results = await asyncio.gather(
                *[_score_one(c, h) for c, h in to_score]
            )
            for result in score_results:
                if result and len(scored_competitors) < TARGET_COMPETITORS:
                    scored_competitors.append(result)

            # If still short, ask for more candidates
            if len(scored_competitors) < TARGET_COMPETITORS and round_num < MAX_ROUNDS - 1:
                already_names = ", ".join(
                    [c["name"] for c in scored_competitors] + list(tried_urls)
                )
                candidates = await identify_competitors(
                    user_html + f"\n\n<!-- EXCLUDE THESE (already tried): {already_names} -->",
                    api_key,
                )

        # Step 4: Fallback — generate AI-based competitor scores if still short
        if len(scored_competitors) < TARGET_COMPETITORS:
            try:
                existing_names = ", ".join(c["name"] for c in scored_competitors)
                shortfall = TARGET_COMPETITORS - len(scored_competitors)
                fallback_prompt = _build_fallback_prompt(user_html, shortfall, existing_names)

                fallbacks = await call_openrouter(
                    fallback_prompt,
                    api_key,
                    model="openai/gpt-5.4-nano",
                    temperature=0.4,
                    max_tokens=800,
                    extract_array=True,
                )

                if isinstance(fallbacks, list):
                    for fb in fallbacks:
                        if len(scored_competitors) >= TARGET_COMPETITORS:
                            break
                        if not isinstance(fb, dict):
                            continue
                        fb_name = fb.get("name", "")
                        if any(c["name"] == fb_name for c in scored_competitors):
                            continue
                        cats = build_category_scores(fb.get("categories", {}))
                        cat_sum = sum(cats.values())
                        score = clamp_score(fb.get("score", 0))
                        if score == 0 or cat_sum == 0:
                            continue
                        scored_competitors.append({
                            "name": fb_name,
                            "url": "",
                            "score": score,
                            "summary": fb.get("summary", "Scored from known brand data."),
                            "categories": cats,
                        })
            except Exception:
                logger.exception("Fallback competitor scoring failed")

        # Step 5: Return response (camelCase keys)
        return {
            "yourPage": {
                "score": user_analysis["score"],
                "summary": user_analysis["summary"],
                "tips": user_analysis["tips"],
                "categories": user_analysis["categories"],
                "url": url,
            },
            "competitors": scored_competitors,
        }

    except Exception:
        logger.exception("Competitor analysis error")
        return JSONResponse(
            status_code=500,
            content={"error": "Something went wrong"},
        )
