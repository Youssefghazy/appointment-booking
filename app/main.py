"""The web layer: FastAPI routes.

Every route here does the same three things: read input, call into
booking_service.py to do the actual work, and render a template (or
redirect). No SQL and no business rules live in this file on purpose --
see booking_service.py for that.
"""

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


def _long_date(d: date) -> str:
    """Formats like 'Wednesday, August 19, 2026' -- built manually rather
    than with a no-leading-zero strftime flag (`%-d`) because that flag
    isn't portable to Windows, and this app is meant to run there too.
    """
    return f"{d.strftime('%A, %B')} {d.day}, {d.year}"


def _short_date(d: date) -> str:
    """Formats like 'Wednesday, August 19' -- same portability note as
    _long_date, just without the year (used in on-page headings where
    the year is implied)."""
    return f"{d.strftime('%A, %B')} {d.day}"


def _format_slot(slot_start_str: str) -> str:
    """Jinja filter: the raw stored `slot_start` ("2026-08-19T09:00:00")
    into something a customer or owner would actually want to read
    ("Wednesday, August 19 at 09:00 AM"). Registered as `format_slot`
    below so every template shows times the same way.
    """
    dt = datetime.strptime(slot_start_str, booking_service.SLOT_FORMAT)
    return f"{dt.strftime('%A, %B')} {dt.day} at {dt.strftime('%I:%M %p')}"


templates.env.filters["format_slot"] = _format_slot


def _build_day_cards(available_dates: list[date]) -> list[dict]:
    """One compact card per bookable day -- weekday + month + day number,
    e.g. "WED" / "Aug 19" -- for the day-picking stage. Deliberately not
    a month calendar grid: with a 30-day window there's no real need to
    show which weekday-of-the-month something falls on, and a plain
    scannable list of only the days that actually have openings is both
    shorter and easier to pick from than a grid mostly full of blanks.
    Already-passed days are never in `available_dates` in the first
    place (booking_service excludes them), so there's nothing to filter
    out here -- they just never existed on this list.
    """
    return [
        {
            "iso": d.isoformat(),
            "weekday": d.strftime("%a").upper(),
            "label": f"{d.strftime('%b')} {d.day}",
            "aria_label": _long_date(d),
        }
        for d in available_dates
    ]


def _render_booking_page(
    request: Request,
    *,
    day: str | None,
    slot: str | None,
    error: str | None,
    form: dict,
    status_code: int = 200,
):
    """Shared rendering for the booking page. The page has exactly three
    stages, driven entirely by which of the `day`/`slot` query params
    resolve to something real -- no day picked yet means stage "day", a
    valid day but no valid slot means stage "time", and both valid means
    stage "details". Each stage shows only itself: the customer is never
    looking at the day list and the time grid (or the time grid and the
    details form) at the same time.
    """
    conn = db.get_connection()
    try:
        grouped = booking_service.slots_by_date(conn)
    finally:
        conn.close()

    available_dates = sorted(grouped.keys())

    selected_date = None
    day_error = None
    if day:
        try:
            candidate = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            candidate = None
        if candidate in grouped:
            selected_date = candidate
        else:
            # A day link/bookmark that no longer resolves to anything
            # bookable -- most likely every slot on that day got taken
            # between page load and click. Don't fail silently; say so
            # and fall back to the day-picking stage.
            day_error = "That day is no longer available. Please pick another."

    selected_slot = None
    slot_error = None
    if selected_date and slot:
        try:
            candidate_slot = datetime.strptime(slot, booking_service.SLOT_FORMAT)
        except ValueError:
            candidate_slot = None
        if candidate_slot and candidate_slot in grouped[selected_date]:
            selected_slot = candidate_slot
        else:
            slot_error = "That time was just taken. Please pick another."

    if selected_slot is not None:
        stage = "details"
    elif selected_date is not None:
        stage = "time"
    else:
        stage = "day"

    return templates.TemplateResponse(
        request,
        "booking.html",
        {
            "stage": stage,
            "day_cards": _build_day_cards(available_dates),
            "selected_date": selected_date,
            "selected_date_label": _short_date(selected_date) if selected_date else None,
            "selected_slots": grouped.get(selected_date, []) if selected_date else [],
            "selected_slot": selected_slot,
            "booking_summary": (
                _format_slot(selected_slot.strftime(booking_service.SLOT_FORMAT))
                if selected_slot
                else None
            ),
            "has_any_slots": bool(available_dates),
            "error": error or day_error or slot_error,
            "form": form,
        },
        status_code=status_code,
    )


# ---------------------------------------------------------------------------
# Customer: browse + book (User Story 1)
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def booking_page(
    request: Request,
    error: str | None = None,
    day: str | None = None,
    slot: str | None = None,
):
    return _render_booking_page(request, day=day, slot=slot, error=error, form={})


@app.post("/book")
def book_slot(
    request: Request,
    slot_start: str = Form(...),
    customer_name: str = Form(...),
    customer_email: str = Form(""),
):
    # If we need to redisplay the form, keep the customer where they were:
    # a bad name/email should redisplay the details stage with the same
    # slot still selected, while a slot that just got taken naturally
    # falls back to the time stage, since it won't resolve as valid
    # anymore (see _render_booking_page).
    submitted_day = slot_start[:10] if slot_start else None
    submitted_slot = slot_start or None

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
                slot=submitted_slot,
                error=exc.message,
                form={"customer_name": customer_name, "customer_email": customer_email},
                status_code=422,
            )
        except booking_service.SlotAlreadyBookedError as exc:
            return _render_booking_page(
                request,
                day=submitted_day,
                slot=submitted_slot,
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
