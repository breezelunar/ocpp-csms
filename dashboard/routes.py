import os
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database.repositories import ChargePointRepository, IdTagRepository, TransactionRepository

BASE_DIR = os.path.dirname(__file__)

app = FastAPI(title="OCPP CSMS Dashboard")

app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "static")),
    name="static",
)

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# ── HTML pages ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    charge_points = await ChargePointRepository.list_all()
    transactions = await TransactionRepository.list_all(limit=10)
    id_tags = await IdTagRepository.list_all()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "charge_points": charge_points,
            "transactions": transactions,
            "id_tags": id_tags,
        },
    )


@app.get("/charge-points", response_class=HTMLResponse)
async def charge_points_page(request: Request) -> HTMLResponse:
    charge_points = await ChargePointRepository.list_all()
    return templates.TemplateResponse(
        "charge_points.html",
        {"request": request, "charge_points": charge_points},
    )


@app.get("/transactions", response_class=HTMLResponse)
async def transactions_page(request: Request) -> HTMLResponse:
    transactions = await TransactionRepository.list_all()
    return templates.TemplateResponse(
        "transactions.html",
        {"request": request, "transactions": transactions},
    )


@app.get("/id-tags", response_class=HTMLResponse)
async def id_tags_page(request: Request) -> HTMLResponse:
    id_tags = await IdTagRepository.list_all()
    return templates.TemplateResponse(
        "id_tags.html",
        {"request": request, "id_tags": id_tags},
    )


# ── REST API endpoints ───────────────────────────────────────────────────────

@app.get("/api/charge-points", response_class=JSONResponse)
async def api_list_charge_points() -> Any:
    items = await ChargePointRepository.list_all()
    for item in items:
        item["id"] = item.pop("_id", None)
    return items


@app.get("/api/charge-points/{charge_point_id}", response_class=JSONResponse)
async def api_get_charge_point(charge_point_id: str) -> Any:
    item = await ChargePointRepository.get(charge_point_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Charge point not found")
    item["id"] = item.pop("_id", None)
    return item


@app.get("/api/transactions", response_class=JSONResponse)
async def api_list_transactions() -> Any:
    items = await TransactionRepository.list_all()
    for item in items:
        item["id"] = item.pop("_id", None)
    return items


@app.get("/api/transactions/{transaction_id}", response_class=JSONResponse)
async def api_get_transaction(transaction_id: int) -> Any:
    item = await TransactionRepository.get(transaction_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    item["id"] = item.pop("_id", None)
    return item


@app.get("/api/id-tags", response_class=JSONResponse)
async def api_list_id_tags() -> Any:
    items = await IdTagRepository.list_all()
    for item in items:
        item["id"] = item.pop("_id", None)
    return items


@app.get("/api/id-tags/{id_tag}", response_class=JSONResponse)
async def api_get_id_tag(id_tag: str) -> Any:
    item = await IdTagRepository.get(id_tag)
    if item is None:
        raise HTTPException(status_code=404, detail="ID tag not found")
    item["id"] = item.pop("_id", None)
    return item


@app.post("/api/id-tags", response_class=JSONResponse, status_code=201)
async def api_create_id_tag(payload: Dict[str, Any]) -> Any:
    id_tag = payload.get("id_tag")
    if not id_tag:
        raise HTTPException(status_code=400, detail="id_tag field is required")
    status = payload.get("status", "Accepted")
    await IdTagRepository.upsert(id_tag, {"status": status})
    return {"id": id_tag, "status": status}


@app.delete("/api/id-tags/{id_tag}", status_code=204)
async def api_delete_id_tag(id_tag: str) -> None:
    item = await IdTagRepository.get(id_tag)
    if item is None:
        raise HTTPException(status_code=404, detail="ID tag not found")
    await IdTagRepository.delete(id_tag)
