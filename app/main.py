"""The web layer: FastAPI routes.

Every route here does the same three things: read input, call into
booking_service.py to do the actual work, and render a template (or
redirect). No SQL and no business rules live in this file on purpose --
see booking_service.py for that.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app import booking_service, config, db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fails fast and loudly if OWNER_PASSCODE isn't configured, rather
    # than silently starting an owner view nothing can ever unlock.
    config.require_owner_passcode()
    db.init_db()
    yield


app = FastAPI(title="Appointment Booking", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# ---------------------------------------------------------------------------
# Customer: browse + book (User Story 1)
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def booking_page(request: Request, error: str | None = None):
    conn = db.get_connection()
    try:
        slots = booking_service.list_available_slots(conn)
    finally:
        conn.close()
    return templates.TemplateResponse(
        request,
        "booking.html",
        {"slots": slots, "error": error, "form": {}},
    )


@app.post("/book")
def book_slot(
    request: Request,
    slot_start: str = Form(...),
    customer_name: str = Form(...),
    customer_phone: str = Form(...),
    customer_email: str = Form(""),
):
    conn = db.get_connection()
    try:
        try:
            booking = booking_service.create_booking(
                conn, slot_start, customer_name, customer_phone, customer_email or None
            )
        except booking_service.InvalidBookingError as exc:
            slots = booking_service.list_available_slots(conn)
            return templates.TemplateResponse(
                request,
                "booking.html",
                {
                    "slots": slots,
                    "error": exc.message,
                    "form": {
                        "customer_name": customer_name,
                        "customer_phone": customer_phone,
                        "customer_email": customer_email,
                    },
                },
                status_code=422,
            )
        except booking_service.SlotAlreadyBookedError as exc:
            slots = booking_service.list_available_slots(conn)
            return templates.TemplateResponse(
                request,
                "booking.html",
                {
                    "slots": slots,
                    "error": str(exc),
                    "form": {
                        "customer_name": customer_name,
                        "customer_phone": customer_phone,
                        "customer_email": customer_email,
                    },
                },
                status_code=409,
            )
    finally:
        conn.close()

    return RedirectResponse(url=f"/confirmation/{booking['cancel_token']}", status_code=303)


@app.get("/confirmation/{cancel_token}", response_class=HTMLResponse)
def confirmation_page(request: Request, cancel_token: str):
    conn = db.get_connection()
    try:
        booking = booking_service.get_booking_by_token(conn, cancel_token)
    finally:
        conn.close()

    if booking is None:
        return templates.TemplateResponse(
            request, "confirmation.html", {"booking": None}, status_code=404
        )
    return templates.TemplateResponse(request, "confirmation.html", {"booking": booking})


# ---------------------------------------------------------------------------
# Customer: self-service cancellation (User Story 3)
# ---------------------------------------------------------------------------


@app.get("/cancel/{cancel_token}", response_class=HTMLResponse)
def cancel_prompt(request: Request, cancel_token: str):
    conn = db.get_connection()
    try:
        booking = booking_service.get_booking_by_token(conn, cancel_token)
    finally:
        conn.close()

    if booking is None or booking["status"] == "cancelled":
        return templates.TemplateResponse(
            request, "cancel.html", {"booking": booking, "already_done": True}
        )
    return templates.TemplateResponse(
        request, "cancel.html", {"booking": booking, "already_done": False}
    )


@app.post("/cancel/{cancel_token}", response_class=HTMLResponse)
def cancel_submit(request: Request, cancel_token: str):
    conn = db.get_connection()
    try:
        result = booking_service.cancel_booking(conn, cancel_token=cancel_token, by="customer")
        booking = booking_service.get_booking_by_token(conn, cancel_token)
    finally:
        conn.close()

    return templates.TemplateResponse(
        request,
        "cancel.html",
        {"booking": booking, "already_done": True, "just_cancelled": result["ok"]},
    )


# ---------------------------------------------------------------------------
# Owner: passcode-gated view + cancel (User Story 2)
# ---------------------------------------------------------------------------


def _owner_is_authenticated(request: Request) -> bool:
    return bool(request.session.get("owner_authenticated"))


@app.get("/owner", response_class=HTMLResponse)
def owner_login_page(request: Request, error: str | None = None):
    if _owner_is_authenticated(request):
        return RedirectResponse(url="/owner/bookings", status_code=303)
    return templates.TemplateResponse(request, "owner_login.html", {"error": error})


@app.post("/owner")
def owner_login_submit(request: Request, passcode: str = Form(...)):
    if passcode == config.require_owner_passcode():
        request.session["owner_authenticated"] = True
        return RedirectResponse(url="/owner/bookings", status_code=303)

    # Deliberately generic: never reveal whether bookings exist, just
    # that the passcode was wrong (FR-010).
    return templates.TemplateResponse(
        request,
        "owner_login.html",
        {"error": "Incorrect passcode."},
        status_code=401,
    )


@app.get("/owner/bookings", response_class=HTMLResponse)
def owner_bookings_page(request: Request):
    if not _owner_is_authenticated(request):
        return RedirectResponse(url="/owner", status_code=303)

    conn = db.get_connection()
    try:
        bookings = booking_service.list_active_bookings(conn)
    finally:
        conn.close()
    return templates.TemplateResponse(request, "owner_bookings.html", {"bookings": bookings})


@app.post("/owner/bookings/{booking_id}/cancel")
def owner_cancel_booking(request: Request, booking_id: int):
    if not _owner_is_authenticated(request):
        return RedirectResponse(url="/owner", status_code=303)

    conn = db.get_connection()
    try:
        booking_service.cancel_booking(conn, booking_id=booking_id, by="owner")
    finally:
        conn.close()
    return RedirectResponse(url="/owner/bookings", status_code=303)


@app.post("/owner/logout")
def owner_logout(request: Request):
    request.session.pop("owner_authenticated", None)
    return RedirectResponse(url="/owner", status_code=303)
