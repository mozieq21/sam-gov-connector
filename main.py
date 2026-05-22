"""
SAM.gov MCP Connector
Connects Claude to the US Government's System for Award Management (SAM.gov).
Built with FastMCP (Python). Deploy on Railway.
"""

import os
import httpx
from typing import Optional
from mcp.server.fastmcp import FastMCP

# ── Configuration ─────────────────────────────────────────────────────────────
API_KEY = os.getenv("SAM_API_KEY", "VHu23zpvOirNifNM2o9ewSeu6XvyjGlGvkSlM9y7")
BASE_URL = "https://api.sam.gov"

mcp = FastMCP("SAM.gov Connector")

# ── Helper ────────────────────────────────────────────────────────────────────
def _get(path: str, params: dict) -> dict:
    params["api_key"] = API_KEY
    params = {k: v for k, v in params.items() if v is not None}
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{BASE_URL}{path}", params=params)
        resp.raise_for_status()
        return resp.json()


# ── Tool 1: Search Contract Opportunities ─────────────────────────────────────
@mcp.tool()
def search_opportunities(
    keywords: Optional[str] = None,
    naics_code: Optional[str] = None,
    agency: Optional[str] = None,
    set_aside_type: Optional[str] = None,
    notice_type: Optional[str] = None,
    posted_from: Optional[str] = None,
    posted_to: Optional[str] = None,
    state: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
) -> dict:
    """
    Search for active federal contract opportunities on SAM.gov.

    Args:
        keywords:       Search terms (e.g. "telecom fiber network")
        naics_code:     NAICS industry code (e.g. "517311" for wired telecom)
        agency:         Department or agency name (e.g. "DEPT OF DEFENSE")
        set_aside_type: SBA=Small Business, 8A=8(a) Sole Source,
                        HZC=HUBZone, SDVOSBC=Service-Disabled Veteran,
                        WOSB=Women-Owned
        notice_type:    o=Solicitation, p=Presolicitation, k=Combined Synopsis,
                        r=Sources Sought, a=Award Notice, s=Special Notice
        posted_from:    Notices posted on or after this date (MM/dd/yyyy)
        posted_to:      Notices posted on or before this date (MM/dd/yyyy)
        state:          Place of performance state code (e.g. "VA", "TX")
        limit:          Number of results (max 100, default 10)
        offset:         Pagination offset (default 0)
    """
    params = {
        "keywords": keywords,
        "ncode": naics_code,
        "deptname": agency,
        "typeOfSetAside": set_aside_type,
        "ptype": notice_type,
        "postedFrom": posted_from,
        "postedTo": posted_to,
        "state": state,
        "limit": min(limit, 100),
        "offset": offset,
    }
    data = _get("/opportunities/v2/search", params)
    opps = data.get("opportunitiesData", [])
    return {
        "total_records": data.get("totalRecords", 0),
        "returned": len(opps),
        "offset": offset,
        "opportunities": [
            {
                "notice_id":            o.get("noticeId"),
                "title":                o.get("title"),
                "type":                 o.get("type"),
                "posted_date":          o.get("postedDate"),
                "response_deadline":    o.get("responseDeadLine"),
                "naics_code":           o.get("naicsCode"),
                "agency":               o.get("fullParentPathName"),
                "set_aside":            o.get("typeOfSetAside"),
                "place_of_performance": o.get("placeOfPerformance"),
                "description":          (o.get("description") or "")[:500],
                "link":                 f"https://sam.gov/opp/{o.get('noticeId')}/view",
            }
            for o in opps
        ],
    }


# ── Tool 2: Get Full Opportunity Details ──────────────────────────────────────
@mcp.tool()
def get_opportunity(notice_id: str) -> dict:
    """
    Retrieve full details of a specific SAM.gov contract opportunity.

    Args:
        notice_id: The unique Notice ID (e.g. "SPE4A624R0022")
    """
    data = _get("/opportunities/v2/search", {"noticeid": notice_id, "limit": 1})
    opps = data.get("opportunitiesData", [])
    if not opps:
        return {"error": f"No opportunity found with notice_id: {notice_id}"}
    o = opps[0]
    return {
        "notice_id":             o.get("noticeId"),
        "title":                 o.get("title"),
        "solicitation_number":   o.get("solicitationNumber"),
        "type":                  o.get("type"),
        "posted_date":           o.get("postedDate"),
        "response_deadline":     o.get("responseDeadLine"),
        "archive_date":          o.get("archiveDate"),
        "naics_code":            o.get("naicsCode"),
        "naics_description":     o.get("naicsDescription"),
        "product_service_code":  o.get("classificationCode"),
        "agency":                o.get("fullParentPathName"),
        "office_address":        o.get("officeAddress"),
        "set_aside":             o.get("typeOfSetAside"),
        "place_of_performance":  o.get("placeOfPerformance"),
        "description":           o.get("description"),
        "point_of_contact":      o.get("pointOfContact"),
        "attachments":           o.get("resourceLinks"),
        "award":                 o.get("award"),
        "sam_url":               f"https://sam.gov/opp/{o.get('noticeId')}/view",
    }


# ── Tool 3: Search Registered Entities (Vendors) ──────────────────────────────
@mcp.tool()
def search_entities(
    uei: Optional[str] = None,
    cage_code: Optional[str] = None,
    legal_name: Optional[str] = None,
    registration_status: str = "A",
    limit: int = 10,
) -> dict:
    """
    Search for companies registered in SAM.gov.
    Use for vendor qualification, teaming research, or debarment checks.

    Args:
        uei:                 Unique Entity Identifier (12-character alphanumeric)
        cage_code:           5-character CAGE code (e.g. "5N6X3")
        legal_name:          Full or partial legal business name
        registration_status: "A" for Active (default), "E" for Expired
        limit:               Number of results (default 10, max 100)
    """
    if not any([uei, cage_code, legal_name]):
        return {"error": "Provide at least one: uei, cage_code, or legal_name"}
    params = {
        "ueiSAM": uei,
        "cageCode": cage_code,
        "legalBusinessName": legal_name,
        "registrationStatus": registration_status,
        "includeSections": "entityRegistration,coreData,pointsOfContact",
        "limit": min(limit, 100),
    }
    data = _get("/entity-information/v3/entities", params)
    entities = data.get("entityData", [])
    results = []
    for e in entities:
        reg = e.get("entityRegistration", {})
        core = e.get("coreData", {})
        physical = core.get("physicalAddress", {})
        results.append({
            "uei":                     reg.get("ueiSAM"),
            "cage_code":               reg.get("cageCode"),
            "legal_name":              reg.get("legalBusinessName"),
            "registration_status":     reg.get("registrationStatus"),
            "expiration_date":         reg.get("registrationExpirationDate"),
            "purpose_of_registration": reg.get("purposeOfRegistrationDesc"),
            "physical_address": {
                "street":  physical.get("addressLine1"),
                "city":    physical.get("city"),
                "state":   physical.get("stateOrProvinceCode"),
                "country": physical.get("countryCode"),
            },
            "exclusion_status": reg.get("exclusionStatusFlag"),
            "sam_url": f"https://sam.gov/entity/{reg.get('ueiSAM')}/core-data",
        })
    return {
        "total_records": data.get("totalRecords", 0),
        "returned": len(results),
        "entities": results,
    }


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import JSONResponse

    async def server_card(request):
        return JSONResponse({
            "name": "SAM.gov Connector",
            "version": "1.0.0",
            "description": "Connect Claude to SAM.gov for federal contract search and vendor lookup.",
            "tools": [
                {
                    "name": "search_opportunities",
                    "description": "Search federal contracts on SAM.gov by keyword, NAICS, agency, set-aside, state and date.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "keywords": {"type": "string"},
                            "naics_code": {"type": "string"},
                            "agency": {"type": "string"},
                            "set_aside_type": {"type": "string"},
                            "notice_type": {"type": "string"},
                            "posted_from": {"type": "string"},
                            "posted_to": {"type": "string"},
                            "state": {"type": "string"},
                            "limit": {"type": "integer"},
                            "offset": {"type": "integer"},
                        },
                    },
                },
                {
                    "name": "get_opportunity",
                    "description": "Get full details of a SAM.gov opportunity by Notice ID.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "notice_id": {"type": "string"},
                        },
                        "required": ["notice_id"],
                    },
                },
                {
                    "name": "search_entities",
                    "description": "Look up SAM-registered vendors by name, UEI, or CAGE code.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "uei": {"type": "string"},
                            "cage_code": {"type": "string"},
                            "legal_name": {"type": "string"},
                            "registration_status": {"type": "string"},
                            "limit": {"type": "integer"},
                        },
                    },
                },
            ],
        })

    sse = mcp.sse_app()
    app = Starlette(routes=[
        Route("/.well-known/mcp/server-card.json", server_card),
        Mount("/", app=sse),
    ])

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
