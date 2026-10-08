"""Actual HTTP connections: idle seller sessions cannot poison the next offer."""

import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
import threading

import httpx
import pytest

from app.buyer.app import create_app
from app.core.config import Settings
from app.core.models import JobSpec
from app.seller.job import sample_flats


@pytest.mark.anyio
async def test_buyer_completes_with_seller_that_drops_reused_connections(tmp_path):
    requests = []
    rounds = []

    class Seller(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def respond(self):
            # Deterministically model an idle HTTP connection closing just as the
            # next request arrives. Each newly accepted connection starts healthy.
            if getattr(self, "used", False):
                self.connection.shutdown(socket.SHUT_RDWR)
                self.close_connection = True
                return
            self.used = True
            requests.append(self.path)
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if self.path == "/negotiate":
                rounds.append((body["deal_id"], body["round"]))
                reply = {"deal_id": body["deal_id"], "round": body["round"], "price": 7,
                         "action": "accept" if body["action"] == "accept" else "counter", "message": "Seven."}
            elif self.path == "/start_job":
                reply = {"status": "success", "job_id": "job", "price": 7}
            else:
                reply = {"status": "completed", "job_id": "job", "result": {
                    "source": "sample", "flats": [f.model_dump() for f in sample_flats(JobSpec())]}}
            encoded = json.dumps(reply).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        do_POST = respond
        do_GET = respond

    server = ThreadingHTTPServer(("127.0.0.1", 0), Seller)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    try:
        settings = Settings(llm_mode="mock", seller_llm_mode="mock", tts_mode="off", payments_mode="simulated",
                            ledger_path=str(tmp_path / "buyer.db"), audio_dir=str(tmp_path / "audio"),
                            seller_url=f"http://127.0.0.1:{server.server_port}", poll_seconds=0.01)
        buyer = create_app(settings)
        async with buyer.router.lifespan_context(buyer):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=buyer), base_url="http://buyer") as client:
                assert (await client.post("/tasks", json={})).status_code == 200
                await asyncio.wait_for(asyncio.gather(*buyer.state.orch.tasks), 5)
                events = buyer.state.bus.history
                assert "released" in {event.type for event in events}
                assert "error" not in {event.type for event in events}
                assert (await client.get("/balances")).json()["seller"] == 7
        assert requests.count("/start_job") == 1
        assert len(rounds) >= 2 and len(rounds) == len(set(rounds))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
