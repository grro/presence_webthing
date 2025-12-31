import json
import threading
import logging
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
from presence import Presence
from typing import List, Dict, Any


class SimpleRequestHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # suppress access logging
        pass

    def do_GET(self):
        presences: List[Presence] = self.server.presences
        parsed_url = urlparse(self.path)
        presence_name = parsed_url.path.lstrip("/")
        presence = next((s for s in presences if s.name == presence_name), None)
        if presence:
            self._send_json(200, {'is_presence': str(presence.is_presence), 'last_seen': presence.last_time_presence.strftime("%Y-%m-%dT%H:%M")})
        else:
            html = "<h1>available presences</h1><ul>"
            for s in presences:
                html += f"<li><a href='/{s.name}'>{s.name}</a></li>"
            html += "</ul>"
            self._send_html(200, html)

    def _send_html(self, status, message):
        self.send_response(status)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(message.encode("utf-8"))

    def _send_json(self, status, data: Dict[str, Any]):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

class PresenceWebServer:
    def __init__(self, presences: List[Presence],  host='0.0.0.0', port=8000):
        self.host = host
        self.port = port
        self.address = (self.host, self.port)
        self.server = HTTPServer(self.address, SimpleRequestHandler)
        self.server.presences = presences
        self.server_thread = None

    def start(self):
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        logging.info(f"web server started http://{self.host}:{self.port}")

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        logging.info("web server stopped")

