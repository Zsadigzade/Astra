from scripts.rehearse import speech_lines


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
