import pytest

from scripts.rehearse import check_max_lines, check_seller_lines, service_env, speech_lines


def test_live_seller_acceptance_requires_every_line_live_and_rejects_fallback():
    offer = {"speaker": "viktor", "action": "counter", "backend": "codex"}
    ack = {"speaker": "viktor", "action": "accept", "backend": "codex"}
    for act in (1, 2, 3, 4):
        check_seller_lines([offer, ack], "codex", act)
    with pytest.raises(RuntimeError, match="fallback"):
        check_seller_lines([offer, {**ack, "fallback_reason": "TimeoutError"}], "codex", 1)
    with pytest.raises(RuntimeError, match="codex"):
        check_seller_lines([offer, {**ack, "backend": "mock"}], "codex", 1)  # scripted ack is not live
    with pytest.raises(RuntimeError, match="codex"):
        check_seller_lines([{**offer, "backend": "mock"}, ack], "codex", 2)  # staged con is live too
    scripted = [{**offer, "backend": "mock"}, {**ack, "backend": "mock"}]
    check_seller_lines(scripted, "mock", 2)
    with pytest.raises(RuntimeError, match="mock"):
        check_seller_lines([offer, scripted[1]], "mock", 1)


def test_max_lines_must_all_be_codex_except_guard_notices():
    max_line = {"speaker": "max", "backend": "codex"}
    guard = {"speaker": "max", "backend": "guard"}
    assert check_max_lines([max_line, guard, {"speaker": "viktor", "backend": "mock"}]) == [max_line]
    with pytest.raises(RuntimeError, match="fallback"):
        check_max_lines([max_line, {**max_line, "backend": "mock"}])
    with pytest.raises(RuntimeError, match="fallback"):
        check_max_lines([{**max_line, "fallback_reason": "TimeoutError"}])


def test_rehearsal_services_inherit_tokens_and_isolate_seller_state(tmp_path):
    from app.core.config import Settings
    s = Settings(api_token="buyer-token", seller_api_token="seller-token")
    env = service_env(s, tmp_path, "codex", "apify")
    assert env["API_TOKEN"] == env["VITE_API_TOKEN"] == "buyer-token"
    assert env["SELLER_API_TOKEN"] == "seller-token" and env["STRICT_LIVE"] == "1"
    assert env["SELLER_STORE_PATH"] == str(tmp_path / "seller.db")
    assert service_env(s, tmp_path, "mock", "apify")["STRICT_LIVE"] == "0"
    assert service_env(s, tmp_path, "codex", "cached")["STRICT_LIVE"] == "0"


def test_rehearsal_resolves_audio_by_full_message_identity():
    line = {"id": 1, "ts": 2.5, "deal_id": "deal", "type": "negotiation",
            "data": {"text": "Offer", "audio_url": None, "audio_status": "pending"}}
    update = {"id": 2, "ts": 3, "deal_id": "deal", "type": "audio_ready",
              "data": {"message_id": 1, "message_ts": 2.5, "audio_url": "/audio/ok.mp3", "audio_status": "ready"}}
    assert speech_lines([line])[0]["audio_status"] == "pending"
    assert speech_lines([line, update])[0]["audio_url"] == "/audio/ok.mp3"
    assert line["data"]["audio_url"] is None
    for changed in ({"deal_id": "other"}, {"data": {**update["data"], "message_ts": 1.5}}):
        assert speech_lines([line, {**update, **changed}])[0]["audio_status"] == "pending"


def test_rehearsal_preserves_legacy_audio_and_exposes_text_fallback():
    legacy = {"id": 1, "ts": 1, "deal_id": "deal", "type": "negotiation", "data": {"audio_url": "/audio/old.mp3"}}
    assert speech_lines([legacy])[0]["audio_url"] == "/audio/old.mp3"
    unavailable = {"type": "audio_ready", "deal_id": "deal", "data": {
        "message_id": 1, "message_ts": 1, "audio_url": None, "audio_status": "unavailable"}}
    assert speech_lines([legacy, unavailable])[0] == {"audio_url": None, "audio_status": "unavailable"}
    interrupted = {**unavailable, "data": {**unavailable["data"], "reason": "buyer_restarted"}}
    assert speech_lines([legacy, interrupted])[0]["audio_reason"] == "buyer_restarted"
