"""doctor's money check: payments are SIMULATED USD only; Masumi is dormant and must not be advertised."""
import pytest

import scripts.doctor as doctor
from app.core.config import Settings


@pytest.fixture(autouse=True)
def fresh_rows():
    doctor.rows.clear()
    yield
    doctor.rows.clear()


def test_stale_masumi_mode_is_reported_as_refused():
    doctor.check_money(Settings(payments_mode="masumi"), live=True)
    assert [r[1] for r in doctor.rows] == [doctor.FAIL]
    assert "Masumi payments are disabled" in doctor.rows[0][2]


def test_simulated_mode_no_longer_suggests_switching_to_masumi():
    doctor.check_money(Settings(payments_mode="simulated"), live=False)
    text = " ".join(" ".join(r) for r in doctor.rows)
    assert "SIMULATED" in text and "USD" in text and "PAYMENTS_MODE=masumi" not in text
