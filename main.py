"""
SAM.gov MCP Connector
Connects Claude to the US Government's System for Award Management (SAM.gov).
Built with FastMCP (Python). Deploy on Railway.
"""

import os
import httpx
from datetime import datetime
from typing import Optional
from mcp.server.fastmcp import FastMCP

# ── Configuration ────────────────────────────────────────────────────────────
API_KEY = os.getenv("SAM_API_KEY", "VHu23zpvOirNifNM2o9ewSeu6XvyjGlGvkSlM9y7")
BASE_URL = "https://api.sam.gov"

mcp = FastMCP("SAM.gov Connector")

# ── Helper ────────────────────────────────────────────────────────────────────
def _get(path: str, params: dict) -> dict:
    """Make an authenticated GET request to the SAM.gov API."""
    params["api_key"] = API_KEY
    # Remove None values so the API doesn't receive empty params
    params = {k: v for k, v in params.items() if v is not None}
    url = f"{BASE_URL}{path}"
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


# ── Tool 1: Search Contract Opportunities ────────────────────────────────────
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
        set_aside_type: Small business set-aside code. Common values:
                        SBA=Small Business, SBP=Small Business Set-Aside,
                        8A=8(a) Sole Source, HZC=HUBZone,
                        SDVOSBC=Service-Disabled Veteran, WOSB=Women-Owned
        notice_type:    Type of notice. Common values:
                        o=Solicitation, p=Presolicitation, k=Combined Synopsis,
                        r=Sources Sought, a=Award Notice, s=Special Notice
        posted_from:    Filter notices posted on or after this date (MM/dd/yyyy)
        posted_to:      Filter notices posted on or before this date (MM/dd/yyyy)
        state:          Place of performance state code (e.g. "VA", "TX")
        limit:          Number of results to return (max 100, default 10)
        offset:         Pagination offset (default 0)

    Returns:
        Dictionary with totalRecords count and list of opportunities.
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

    total = data.get("totalRecords", 0)
    opps = data.get("opportunitiesData", [])

    results = []
    for o in opps:
        results.append({
            "notice_id":        o.get("noticeId"),
            "title":            o.get("title"),
            "type":             o.get("type"),
            "posted_date":      o.get("postedDate"),
            "response_deadline": o.get("responseDeadLine"),
            "naics_code":       o.get("naicsCode"),
            "agency":           o.get("fullParentPathName"),
            "office":           o.get("officeAddress"),
            "set_aside":        o.get("typeOfSetAside"),
            "place_of_performance": o.get("placeOfPerformance"),
            "description":      (o.get("description") or "")[:500],  # truncate
            "link":             f"https://sam.gov/opp/{o.get('noticeId')}/view",
        })

    return {
        "total_records": total,
        "returned": len(results),
        "offset": offset,
        "opportunities": results,
    }


# ── Tool 2: Get Full Opportunity Details ──────────────────────────────────────
@mcp.tool()
def get_opportunity(notice_id: str) -> dict:
    """
    Retrieve full details of a specific SAM.gov contract opportunity.

    Args:
        notice_id: The unique Notice ID of the opportunity
                   (e.g. "SPE4A624R0022" or a UUID string)

    Returns:
        Full opportunity record including description, attachments, and contacts.
    """
    params = {
        "noticeid": notice_id,
        "limit": 1,
    }

    data = _get("/opportunities/v2/search", params)
    opps = data.get("opportunitiesData", [])

    if not opps:
        return {"error": f"No opportunity found with notice_id: {notice_id}"}

    o = opps[0]
    return {
        "notice_id":            o.get("noticeId"),
        "title":                o.get("title"),
        "solicitation_number":  o.get("solicitationNumber"),
        "type":                 o.get("type"),
        "base_type":            o.get("baseType"),
        "posted_date":          o.get("postedDate"),
        "response_deadline":    o.get("responseDeadLine"),
        "archive_date":         o.get("archiveDate"),
        "naics_code":           o.get("naicsCode"),
        "naics_description":    o.get("naicsDescription"),
        "product_service_code": o.get("classificationCode"),
        "agency":               o.get("fullParentPathName"),
        "office_address":       o.get("officeAddress"),
        "set_aside":            o.get("typeOfSetAside"),
        "set_aside_description": o.get("typeOfSetAsideDescription"),
        "place_of_performance": o.get("placeOfPerformance"),
        "description":          o.get("description"),
        "point_of_contact":     o.get("pointOfContact"),
        "links":                o.get("links"),
        "attachments":          o.get("resourceLinks"),
        "award":                o.get("award"),
        "sam_url":              f"https://sam.gov/opp/{o.get('noticeId')}/view",
    }


# ── Tool 3: Search Registered Entities (Vendors) ─────────────────────────────
@mcp.tool()
def search_entities(
    uei: Optional[str] = None,
    cage_code: Optional[str] = None,
    legal_name: Optional[str] = None,
    registration_status: str = "A",
    limit: int = 10,
) -> dict:
    """
    Search for companies/entities registered in SAM.gov.
    Useful for vendor qualification, teaming partner research, or debarment checks.

    Args:
        uei:                 Unique Entity Identifier (12-character alphanumeric)
        cage_code:           5-character CAGE code (e.g. "5N6X3")
        legal_name:          Full or partial legal business name
        registration_status: "A" for Active (default), "E" for Expired
        limit:               Number of results to return (default 10, max 100)

    Returns:
        List of matching registered entities with key compliance and contact data.
    """
    if not any([uei, cage_code, legal_name]):
        return {"error": "Provide at least one search parameter: uei, cage_code, or legal_name"}

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
    total = data.get("totalRecords", 0)

    results = []
    for e in entities:
        reg = e.get("entityRegistration", {})
        core = e.get("coreData", {})
        pocs = e.get("pointsOfContact", {})

        physical = core.get("physicalAddress", {})
        business_types = core.get("businessTypes", {})

        results.append({
            "uei":                  reg.get("ueiSAM"),
            "cage_code":            reg.get("cageCode"),
            "legal_name":           reg.get("legalBusinessName"),
            "dba_name":             reg.get("dbaName"),
            "registration_status":  reg.get("registrationStatus"),
            "activation_date":      reg.get("activationDate"),
            "expiration_date":      reg.get("registrationExpirationDate"),
            "purpose_of_registration": reg.get("purposeOfRegistrationDesc"),
            "entity_structure":     reg.get("entityStructureDesc"),
            "physical_address": {
                "street":   physical.get("addressLine1"),
                "city":     physical.get("city"),
                "state":    physical.get("stateOrProvinceCode"),
                "zip":      physical.get("zipCode"),
                "country":  physical.get("countryCode"),
            },
            "business_types":       business_types.get("businessTypeList", []),
            "naics_codes":          [
                n.get("naicsCode")
                for n in core.get("generalInformation", {}).get("entityURL", [])
                if n.get("naicsCode")
            ],
            "primary_contact":      pocs.get("governmentBusinessPOC", {}),
            "exclusion_status":     reg.get("exclusionStatusFlag"),
            "sam_url": f"https://sam.gov/entity/{reg.get('ueiSAM')}/core-data",
        })

    return {
        "total_records": total,
        "returned": len(results),
        "entities": results,
    }


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="sse")
