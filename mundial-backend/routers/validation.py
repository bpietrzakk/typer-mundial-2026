# 422 answers in Polish. FastAPI's list shape stays (loc, type, ctx, msg),
# the front builds its own text from type + ctx, login / register show msg

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# request field -> name the user knows
_FIELD_LABELS = {
    "nick": "Nick",
    "email": "E-mail",
    "password": "Hasło",
    "current_password": "Obecne hasło",
    "new_password": "Nowe hasło",
    "token": "Token",
    "name": "Nazwa",
    "join_code": "Kod zaproszenia",
    "pred_home": "Gole gospodarzy",
    "pred_away": "Gole gości",
    "home_goals": "Gole gospodarzy",
    "away_goals": "Gole gości",
    "coupon_size": "Rozmiar kuponu",
    "points": "Punkty",
    "deadline_at": "Termin",
    "season_id": "Sezon",
    "team_id": "Drużyna",
}

# pydantic error type -> text, ctx holds the limits (le / ge / min_length ...)
_TYPE_MESSAGES = {
    "missing": lambda ctx: "to pole jest wymagane",
    "int_type": lambda ctx: "musi być liczbą całkowitą",
    "int_parsing": lambda ctx: "musi być liczbą całkowitą",
    "int_from_float": lambda ctx: "musi być liczbą całkowitą",
    "float_type": lambda ctx: "musi być liczbą",
    "float_parsing": lambda ctx: "musi być liczbą",
    "bool_type": lambda ctx: "nieprawidłowa wartość",
    "bool_parsing": lambda ctx: "nieprawidłowa wartość",
    "string_type": lambda ctx: "musi być tekstem",
    "list_type": lambda ctx: "musi być listą",
    "date_type": lambda ctx: "nieprawidłowa data",
    "date_parsing": lambda ctx: "nieprawidłowa data",
    "datetime_type": lambda ctx: "nieprawidłowa data",
    "datetime_parsing": lambda ctx: "nieprawidłowa data",
    "datetime_from_date_parsing": lambda ctx: "nieprawidłowa data",
    "less_than_equal": lambda ctx: f"musi być nie większe niż {ctx.get('le')}",
    "less_than": lambda ctx: f"musi być mniejsze niż {ctx.get('lt')}",
    "greater_than_equal": lambda ctx: f"musi być nie mniejsze niż {ctx.get('ge')}",
    "greater_than": lambda ctx: f"musi być większe niż {ctx.get('gt')}",
    "string_too_short": lambda ctx: f"jest za krótkie (min. {ctx.get('min_length')} znaków)",
    "string_too_long": lambda ctx: f"jest za długie (max {ctx.get('max_length')} znaków)",
    "too_short": lambda ctx: f"za mało elementów (min. {ctx.get('min_length')})",
    "too_long": lambda ctx: f"za dużo elementów (max {ctx.get('max_length')})",
    "literal_error": lambda ctx: "niedozwolona wartość",
    "enum": lambda ctx: "niedozwolona wartość",
    "json_invalid": lambda ctx: "nieprawidłowy JSON",
    "model_attributes_type": lambda ctx: "nieprawidłowe dane",
    "dict_type": lambda ctx: "nieprawidłowe dane",
}


def polish_message(error: dict) -> str:
    # one pydantic error -> "Pole: co jest nie tak"
    loc = error.get("loc") or ()
    field = next((part for part in reversed(loc) if isinstance(part, str) and part not in ("body", "query", "path")), None)
    ctx = error.get("ctx") or {}
    kind = error.get("type")
    if kind == "value_error" and field == "email":
        text = "nieprawidłowy adres e-mail"
    elif kind == "value_error" and ctx.get("error") is not None:
        # our own validators already raise Polish messages
        return str(ctx["error"])
    else:
        make = _TYPE_MESSAGES.get(kind)
        text = make(ctx) if make else "nieprawidłowa wartość"
    label = _FIELD_LABELS.get(field, field) if field else None
    return f"{label}: {text}" if label else text


async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    # same 422 + detail list as FastAPI, only msg is Polish
    detail = [{**error, "msg": polish_message(error)} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(detail)})
