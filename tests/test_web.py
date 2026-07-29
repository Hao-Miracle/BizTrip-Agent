from datetime import datetime
from http.client import HTTPConnection
from threading import Thread

from http.server import ThreadingHTTPServer

from biztrip_agent.cli import main
from biztrip_agent.web import BizTripWebHandler, _run_demo, render_home


def test_web_home_contains_local_workflows():
    html = render_home()

    assert "BizTrip Agent" in html
    assert 'action="/demo"' in html
    assert 'action="/rebuild"' in html
    assert "records_YYYYMMDD.json" in html


def test_web_rejects_invalid_port():
    assert main(["web", "--port", "70000"]) == 2


def test_web_demo_form_generates_files(tmp_path):
    html = _run_demo({"output_dir": str(tmp_path), "review": "on"})

    today = datetime.now().strftime("%Y%m%d")
    assert "Demo 已生成" in html
    assert (tmp_path / f"差旅汇总_demo_{today}.xlsx").exists()
    assert (tmp_path / f"review_{today}.html").exists()


def test_web_home_supports_head_request():
    server = ThreadingHTTPServer(("127.0.0.1", 0), BizTripWebHandler)
    thread = Thread(target=server.serve_forever)
    thread.start()
    try:
        conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
        conn.request("HEAD", "/")
        response = conn.getresponse()
        response.read()
        conn.close()
    finally:
        server.shutdown()
        thread.join()
        server.server_close()

    assert response.status == 200
    assert int(response.getheader("Content-Length")) > 0
