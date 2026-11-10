# password change / reset on a real Postgres: both stamp users.password_changed_at
# (migration 015) and get_user_by_id hands it to the auth dependency

from datetime import datetime, timedelta, timezone

import pytest

from db.queries import (
    change_password,
    create_password_reset_token,
    get_user_by_id,
    reset_password_with_token,
)
from tests.integration.sync_fakes import create_user, scalar
from tests.integration.wc_dataset import migrate_to


@pytest.fixture
def user_id(conn, app_pool):
    migrate_to(conn)
    return create_user(conn, "ala")


def test_new_user_has_no_password_change(user_id):
    assert get_user_by_id(user_id)["password_changed_at"] is None


def test_change_password_stamps_the_given_time(conn, user_id):
    at = datetime(2026, 11, 6, 12, 0, 0, 500_000, tzinfo=timezone.utc)
    change_password(user_id, "new-hash", at)

    assert get_user_by_id(user_id)["password_changed_at"] == at
    assert scalar(conn, "SELECT password_hash FROM users WHERE id = %s", (user_id,)) == "new-hash"


def test_reset_password_stamps_the_time_too(user_id):
    now = datetime.now(timezone.utc)
    create_password_reset_token(user_id, "token-hash", now + timedelta(hours=1))

    assert reset_password_with_token("token-hash", "reset-hash", now) is not None
    assert get_user_by_id(user_id)["password_changed_at"] == now
