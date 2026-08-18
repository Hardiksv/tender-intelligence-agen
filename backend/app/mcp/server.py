"""
Bonus 2 — MCP Server
Exposes search_tenders, get_tender, and ask_tenders as Model Context Protocol tools.
Reuses all existing application services without duplicating logic.
"""
import asyncio
import json
import sys
import os

# Add backend to sys.path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from app.db.database import SessionLocal
from app.db.models import Tender, ScreeningResult
from app.schemas.chat import ChatRequest
from app.services.rag import answer_tender_question
from app.core.logging import log_action

server = Server("tender-intelligence-agent")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_tenders",
            description="Search stored bus operations tenders by keyword, state, city, verdict, or deadline range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword search in title or authority"},
                    "state": {"type": "string", "description": "Filter by state name"},
                    "city": {"type": "string", "description": "Filter by city name"},
                    "verdict": {"type": "string", "enum": ["GO", "NO-GO", "REVIEW"], "description": "Filter by screening verdict"}
                }
            }
        ),
        types.Tool(
            name="get_tender",
            description="Get full details of a specific tender by its ID, including eligibility criteria and screening verdict with reasoning.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tender_id": {"type": "string", "description": "UUID of the tender"}
                },
                "required": ["tender_id"]
            }
        ),
        types.Tool(
            name="ask_tenders",
            description="Ask any natural language question about stored tenders. Answers are strictly grounded in stored documents with citations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Your question about the tenders"},
                    "tender_id": {"type": "string", "description": "Optional: restrict search to a specific tender"}
                },
                "required": ["question"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    log_action("MCP_TOOL_CALLED", status="CALLED", details={"tool": name, "args": arguments})
    db = SessionLocal()

    try:
        if name == "search_tenders":
            query = arguments.get("query", "").lower()
            state_filter = arguments.get("state", "").lower()
            city_filter = arguments.get("city", "").lower()
            verdict_filter = arguments.get("verdict", "").upper()

            tenders = db.query(Tender).all()
            results = []

            for t in tenders:
                if query and query not in t.title.lower() and query not in t.issuing_authority.lower():
                    continue
                if state_filter and t.state and state_filter not in t.state.lower():
                    continue
                if city_filter and t.city and city_filter not in t.city.lower():
                    continue
                if verdict_filter and t.screening_results:
                    latest = sorted(t.screening_results, key=lambda x: x.screened_at, reverse=True)[0]
                    if latest.verdict != verdict_filter:
                        continue

                verdict = "PENDING"
                if t.screening_results:
                    latest = sorted(t.screening_results, key=lambda x: x.screened_at, reverse=True)[0]
                    verdict = latest.verdict

                results.append({
                    "id": str(t.id),
                    "title": t.title,
                    "issuing_authority": t.issuing_authority,
                    "city": t.city,
                    "state": t.state,
                    "submission_deadline": t.submission_deadline.isoformat(),
                    "emd_amount": float(t.emd_amount) if t.emd_amount else None,
                    "emd_breakdown": t.emd_breakdown,
                    "verdict": verdict
                })

            return [types.TextContent(type="text", text=json.dumps({"total": len(results), "tenders": results}, indent=2))]

        elif name == "get_tender":
            tender_id = arguments.get("tender_id")
            t = db.query(Tender).filter(Tender.id == tender_id).first()

            if not t:
                return [types.TextContent(type="text", text=json.dumps({"error": f"Tender {tender_id} not found."}))]

            screening_data = None
            if t.screening_results:
                latest = sorted(t.screening_results, key=lambda x: x.screened_at, reverse=True)[0]
                screening_data = {
                    "verdict": latest.verdict,
                    "reasoning": latest.reasoning,
                    "criteria_results": latest.criteria_results
                }

            eligibility_data = None
            if t.eligibility:
                e = t.eligibility
                eligibility_data = {
                    "minimum_fleet_size": e.minimum_fleet_size,
                    "minimum_annual_turnover": float(e.minimum_annual_turnover) if e.minimum_annual_turnover else None,
                    "minimum_experience_years": e.minimum_experience_years,
                    "minimum_past_contract_value": float(e.minimum_past_contract_value) if e.minimum_past_contract_value else None,
                    "required_geographies": e.required_geographies,
                    "other_requirements": e.other_requirements
                }

            result = {
                "id": str(t.id),
                "title": t.title,
                "issuing_authority": t.issuing_authority,
                "city": t.city,
                "state": t.state,
                "submission_deadline": t.submission_deadline.isoformat(),
                "emd_amount": float(t.emd_amount) if t.emd_amount else None,
                "emd_breakdown": t.emd_breakdown,
                "scope_summary": t.scope_summary,
                "eligibility": eligibility_data,
                "screening": screening_data
            }

            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "ask_tenders":
            question = arguments.get("question")
            tender_id = arguments.get("tender_id")

            chat_req = ChatRequest(question=question, tender_id=tender_id)
            response = answer_tender_question(db, chat_req)

            output = {
                "question": response.question,
                "answer": response.answer,
                "citations": [
                    {
                        "tender_title": c.tender_title,
                        "document_name": c.document_name,
                        "page_number": c.page_number,
                        "snippet": c.snippet
                    }
                    for c in response.citations
                ],
                "model_used": response.model_used
            }

            return [types.TextContent(type="text", text=json.dumps(output, indent=2))]

        else:
            return [types.TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    except Exception as e:
        return [types.TextContent(type="text", text=json.dumps({"error": str(e)}))]
    finally:
        db.close()


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
