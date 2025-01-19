"""
MicroPie: A simple and lightweight Python micro webframework.
https://patx.github.io/micropie
"""
import http.server
import socketserver
from urllib.parse import parse_qs, urlparse
from jinja2 import Environment, FileSystemLoader
import uuid
import time

class Server:
    SESSION_TIMEOUT = 8 * 3600  # 8 hours

    def __init__(self):
        self.handlers = {}
        self.env = Environment(loader=FileSystemLoader("templates"))
        self.sessions = {}  # Store session data

    def run(self, host="127.0.0.1", port=8080):
        """Start the HTTP server."""
        handler = self._create_handler()
        with socketserver.TCPServer((host, port), handler) as httpd:
            print(f"Serving on {host}:{port}")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nShutting down...")

    def _create_handler(self):
        """Create a request handler class."""
        instance = self

        class RequestHandler(http.server.SimpleHTTPRequestHandler):
            def _handle_request(self, method):
                parsed_path = urlparse(self.path)
                func_name = parsed_path.path.strip("/") or "index"
                func = getattr(instance, func_name, None)

                if func:
                    # Retrieve or create a session for this request
                    instance.session = instance.get_session(self)

                    instance.request = method
                    instance.query_params = parse_qs(parsed_path.query)

                    if method == "POST":
                        content_length = int(self.headers.get('Content-Length', 0))
                        body = self.rfile.read(content_length).decode('utf-8')
                        instance.body_params = parse_qs(body)

                    # Validate request
                    if not instance.validate_request(method):
                        self.send_error(400, "Invalid Request")
                        return

                    try:
                        response = func()
                        self._send_response(response)
                    except Exception as e:
                        print(f"Error in handling request: {e}")
                        self.send_error(500, f"Internal Server Error: {e}")
                else:
                    self.send_error(404, "Not Found")

            def do_GET(self):
                self._handle_request("GET")

            def do_POST(self):
                self._handle_request("POST")

            def _send_response(self, response):
                try:
                    if isinstance(response, str):
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html")
                        self.end_headers()
                        self.wfile.write(response.encode("utf-8"))
                    elif isinstance(response, tuple) and len(response) == 2:
                        status, body = response
                        self.send_response(status)
                        self.send_header("Content-Type", "text/html")
                        self.end_headers()
                        self.wfile.write(body.encode("utf-8"))
                    else:
                        self.send_error(500, "Invalid response format")
                except Exception as e:
                    print(f"Error in sending response: {e}")
                    self.send_error(500, f"Internal Server Error: {e}")

        return RequestHandler

    def get_session(self, request_handler):
        """Retrieve the session for the current client, creating one if necessary."""
        cookie = request_handler.headers.get('Cookie')
        session_id = None

        # Extract session ID from cookies
        if cookie:
            cookies = {item.split('=')[0].strip(): item.split('=')[1].strip() for item in cookie.split(';')}
            session_id = cookies.get('session_id')

        # Create a new session if one doesn't exist
        if not session_id or session_id not in self.sessions:
            session_id = str(uuid.uuid4())
            self.sessions[session_id] = {"last_access": time.time()}
            request_handler.send_response(200)
            request_handler.send_header('Set-Cookie', f'session_id={session_id}; Path=/')
            request_handler.end_headers()
            print(f"New session created: {session_id}")

        # Update session last access time (reset timeout)
        session = self.sessions.get(session_id)
        if session:
            session['last_access'] = time.time()
        else:
            print("Session unexpectedly missing, creating a new one.")
            session = {"last_access": time.time()}
            self.sessions[session_id] = session

        print(f"Session data: {session_id} -> {session}")
        return session

    def cleanup_sessions(self):
        """Clean up expired sessions."""
        now = time.time()
        self.sessions = {sid: data for sid, data in self.sessions.items() if data.get('last_access', now) + self.SESSION_TIMEOUT > now}

    def redirect(self, location):
        return (302, f"<html><head><meta http-equiv='refresh' content='0;url={location}'></head></html>")

    def render_template(self, name, **args):
        return self.env.get_template(name).render(args)

    def validate_request(self, method):
        """Validate incoming request data."""
        try:
            # Example: Validate query parameters
            if method == "GET":
                for key, value in self.query_params.items():
                    if not isinstance(key, str) or not all(isinstance(v, str) for v in value):
                        print(f"Invalid query parameter: {key} -> {value}")
                        return False

            # Example: Validate body parameters for POST
            if method == "POST":
                for key, value in self.body_params.items():
                    if not isinstance(key, str) or not all(isinstance(v, str) for v in value):
                        print(f"Invalid body parameter: {key} -> {value}")
                        return False

            # Add header validation logic here if required

            return True
        except Exception as e:
            print(f"Error during request validation: {e}")
            return False

