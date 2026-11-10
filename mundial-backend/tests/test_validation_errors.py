# 422 answers in Polish, same list shape as FastAPI's (the front reads loc / type / ctx / msg),
# and big responses are gzipped

from fastapi.testclient import TestClient

import main as main_module
from routers.validation import polish_message

client = TestClient(main_module.app)


def test_short_password_gets_a_polish_message_and_keeps_the_list_shape():
    resp = client.post("/auth/register", json={"nick": "ala", "email": "ala@example.com", "password": "krotkie"})
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert isinstance(detail, list)
    item = detail[0]
    assert item["loc"] == ["body", "password"]
    assert item["type"] == "string_too_short"
    assert item["ctx"] == {"min_length": 8}
    assert item["msg"] == "Hasło: jest za krótkie (min. 8 znaków)"


def test_missing_fields_and_bad_email_are_polish():
    detail = client.post("/auth/register", json={"email": "nie-mail"}).json()["detail"]
    msgs = {tuple(d["loc"]): d["msg"] for d in detail}
    assert msgs[("body", "nick")] == "Nick: to pole jest wymagane"
    assert msgs[("body", "email")] == "E-mail: nieprawidłowy adres e-mail"
    assert msgs[("body", "password")] == "Hasło: to pole jest wymagane"


def test_query_number_limits_are_polish():
    assert polish_message({"type": "less_than_equal", "loc": ("query", "days"), "ctx": {"le": 30}}) == (
        "days: musi być nie większe niż 30"
    )
    assert polish_message({"type": "int_parsing", "loc": ("path", "match_id")}) == "match_id: musi być liczbą całkowitą"


def test_custom_validator_message_is_kept_and_unknown_types_have_a_fallback():
    assert polish_message({"type": "value_error", "loc": ("body",), "ctx": {"error": ValueError("Zły termin")}}) == (
        "Zły termin"
    )
    assert polish_message({"type": "something_new", "loc": ("body", "x")}) == "x: nieprawidłowa wartość"


def test_large_responses_are_gzipped_small_ones_are_not():
    big = client.get("/openapi.json", headers={"Accept-Encoding": "gzip"})
    assert big.headers.get("content-encoding") == "gzip"
    small = client.get("/health/live", headers={"Accept-Encoding": "gzip"})
    assert "content-encoding" not in small.headers
