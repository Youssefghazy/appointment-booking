"""The web layer: FastAPI routes.

Every route here does the same three things: read input, call into
booking_service.py to do the actual work, and render a template (or
redirect). No SQL and no business rules live in this file on purpose --
see booking_service.py for that.
"""

import calendar as calendar_module
from contextlib import asynccontextmanager
from datetime import date, datetime

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


def _build_calendar_months(available_dates: list[date], selected_date: date | None) -> list[dict]:
    """Builds one month-grid per calendar month that has at least one
    bookable day, so the booking page can show a real "pick a day" month
    calendar instead of a flat list. This is a display concern only -- it
    doesn't change what a slot *is*, so it lives here in the web layer
    rather than in booking_service.py.
    """
    if not available_dates:
        return []

    dates_by_month: dict[tuple[int, int], set[date]] = {}
    for d in available_dates:
        dates_by_month.setdefault((d.year, d.month), set()).add(d)

    cal = calendar_module.Calendar(firstweekday=0)  # weeks start on Monday
    months = []
    for year, month in sorted(dates_by_month):
        available_in_month = dates_by_month[(year, month)]
        weeks = []
        for week in cal.monthdatescalendar(year, month):
            weeks.append(
                [
                    {
                        "iso": d.isoformat(),
                        "day_number": d.day,
                        "in_month": d.month == month,
                        "has_slots": d in available_in_month,
                        "is_selected": d == selected_date,
                    }
                    for d in week
                ]
            )
        months.append({"label": date(year, month, 1).strftime("%B %Y"), "weeks": weeks})
    return months


def _render_booking_page(
    request: Request,
    *,
    day: str | None,
    error: str | None,
    form: dict,
    status_code: int = 200,
):
    """Shared rendering for the booking page: figures out which day is
    selected (from the `day` query param, falling back to the first day
    with any open slots), builds the calendar, and renders it.
    """
    conn = db.get_connection()
    try:
        grouped = booking_service.slots_by_date(conn)
    finally:
        conn.close()

    available_dates = sorted(grouped.keys())

    selected_date = None
    if day:
        try:
            candidate = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            candidate = None
        if candidate in grouped:
            selected_date = candidate
    if selected_date is None and available_dates:
        selected_date = available_dates[0]

    return templates.TemplateResponse(
        request,
        "booking.html",
        {
            "calendar_months": _build_calendar_months(available_dates, selected_date),
            "selected_date": selected_date,
            "selected_slots": grouped.get(selected_date, []) if selected_date else [],
            "has_any_slots": bool(available_dates),
            "error": error,
            "form": form,
        },
        status_code=status_code,
    )


# ---------------------------------------------------------------------------
# Customer: browse + book (User Story 1)
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def booking_page(request: Request, error: str | None = None, day: str | None = None):
    return _render_booking_page(request, day=day, error=error, form={})


@app.post("/book")
def book_slot(
    request: Request,
    slot_start: str = Form(...),
    customer_name: str = Form(...),
    customer_email: str = Form(""),
):
    # If we need to redisplay the form, keep the customer on the day they
    # were looking at rather than bouncing them back to the first day.
    submitted_day = slot_start[:10] if slot_start else None

    conn = db.get_connection()
    try:
        try:
            booking = booking_service.create_booking(
                conn, slot_start, customer_name, customer_email or None
            )
        except booking_service.InvalidBookingError as exc:
            return _render_booking_page(
                request,
                day=submitted_day,
                error=exc.message,
                form={"customer_name": customer_name, "customer_email": customer_email},
                status_code=422,
            )
        except booking_service.SlotAlreadyBookedError as exc:
            return _render_booking_page(
                request,
                day=submitted_day,
                error=str(exc),
                form={"customer_name": customer_name, "customer_email": customer_email},
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
