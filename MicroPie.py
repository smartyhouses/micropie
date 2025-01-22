"""
MicroPie: A simple Python ultra-micro web framework with WSGI
support. https://patx.github.io/micropie

 Copyright Harrison Erd

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from this
   software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import http.server
import socketserver
import time
import uuid
import inspect
from urllib.parse import parse_qs, urlparse

try:
    from jinja2 import Environment, FileSystemLoader
    JINJA_INSTALLED = True
except ImportError:
    JINJA_INSTALLED = False


class Server:
    """
    A lightweight class providing basic routing, session handling, and
    template rendering using Jinja2 if installed. This class offers both a
    built-in HTTP server mode and a WSGI-compatible application method.
    """

    SESSION_TIMEOUT = 8 * 3600  # 8 hours

    def __init__(self):
        """
        Initialize the Server instance with an optional Jinja2 environment and
        a session store.
        """
        if JINJA_INSTALLED:
            self.env = Environment(loader=FileSystemLoader("templates"))

        self.sessions = {}
        self.request = None
        self.query_params = {}
        self.body_params = {}
        self.path_params = []
        self.session = {}

    def run(self, host="127.0.0.1", port=8080):
        """
        Start the built-in HTTP server, binding to the specified host and port.
        """

        class DynamicRequestHandler(http.server.SimpleHTTPRequestHandler):
            """
            A dynamically generated request handler that dispatches to the
            Server instance's methods for routing and request processing.
            """

            def do_GET(self):
                self._handle_request("GET")

            def do_POST(self):
                self._handle_request("POST")

            def _handle_request(self, method):
                instance = self.server.instance
                parsed_path = urlparse(self.path)
                path_parts = parsed_path.path.strip("/").split("/")

                # Serve static files if requested
                if path_parts[0] == "static":
                    file_path = "/".join(path_parts)
                    static_file_path = f"static/{'/'.join(path_parts[1:])}"
                    try:
                        with open(static_file_path, "rb") as file:
                            self.send_response(200)
                            self.send_header(
                                "Content-Type",
                                self.guess_type(file_path)
                            )
                            self.end_headers()
                            self.wfile.write(file.read())
                        return
                    except FileNotFoundError:
                        self.send_error(404, "Static file not found")
                        return

                func_name = path_parts[0] or "index"
                func = getattr(instance, func_name, None)

                if not func:
                    self.send_error(404, "Not Found")
                    return

                instance.session = instance.get_session(self)
                instance.request = method
                instance.query_params = parse_qs(parsed_path.query)
                instance.path_params = path_parts[1:]
                instance.body_params = {}

                if method == "POST":
                    content_length = int(
                        self.headers.get("Content-Length", 0)
                    )
                    body = self.rfile.read(content_length).decode("utf-8")
                    instance.body_params = parse_qs(body)

                if not instance.validate_request(method):
                    self.send_error(400, "Invalid Request")
                    return

                try:
                    func_args = self._get_func_args(
                        func,
                        instance.query_params,
                        instance.body_params,
                        instance.path_params,
                        method
                    )
                    response = func(*func_args)
                    self._send_response(response)
                except Exception as e:
                    print(f"Error handling request: {e}")
                    self.send_error(500, f"Internal Server Error: {e}")

            def _get_func_args(self, func, query_params, body_params,
                               path_params, method):
                """
                Build the argument list for the function based on its signature,
                using path, query, and body parameters as needed.
                """
                sig = inspect.signature(func)
                args = []

                for param in sig.parameters.values():
                    if path_params:
                        args.append(path_params.pop(0))
                    elif method == "GET" and param.name in query_params:
                        args.append(query_params[param.name][0])
                    elif method == "POST" and param.name in body_params:
                        args.append(body_params[param.name][0])
                    elif param.default is not param.empty:
                        args.append(param.default)
                    else:
                        raise ValueError(
                            f"Missing required parameter: {param.name}"
                        )
                return args

            def _send_response(self, response):
                """
                Send HTTP response based on the handler function return value.
                """
                try:
                    if isinstance(response, str):
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html")
                        self.end_headers()
                        self.wfile.write(response.encode("utf-8"))
                    elif (
                        isinstance(response, tuple) and len(response) == 2
                    ):
                        status, body = response
                        self.send_response(status)
                        self.send_header("Content-Type", "text/html")
                        self.end_headers()
                        self.wfile.write(body.encode("utf-8"))
                    else:
                        self.send_error(500, "Invalid response format")
                except Exception as e:
                    print(f"Error sending response: {e}")
                    self.send_error(500, f"Internal Server Error: {e}")

        handler = DynamicRequestHandler

        with socketserver.TCPServer((host, port), handler) as httpd:
            httpd.instance = self
            print(f"Serving on {host}:{port}")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nShutting down...")

    def get_session(self, request_handler):
        """
        Retrieve or create a session for the current client, setting necessary
        cookies if a new session is created.
        """
        cookie = request_handler.headers.get("Cookie")
        session_id = None

        # Extract session ID from cookies if present
        if cookie:
            cookies = {
                item.split("=")[0].strip(): item.split("=")[1].strip()
                for item in cookie.split(";")
            }
            session_id = cookies.get("session_id")

        # Create a new session if needed
        if not session_id or session_id not in self.sessions:
            session_id = str(uuid.uuid4())
            self.sessions[session_id] = {"last_access": time.time()}
            request_handler.send_response(200)
            request_handler.send_header(
                "Set-Cookie", f"session_id={session_id}; Path=/"
            )
            request_handler.end_headers()
            print(f"New session created: {session_id}")

        # Update last access
        session = self.sessions.get(session_id)
        if session:
            session["last_access"] = time.time()
        else:
            # Should rarely happen unless manually removed
            session = {"last_access": time.time()}
            self.sessions[session_id] = session

        print(f"Session data: {session_id} -> {session}")
        return session

    def cleanup_sessions(self):
        """
        Remove sessions not accessed within SESSION_TIMEOUT.
        """
        now = time.time()
        self.sessions = {
            sid: data
            for sid, data in self.sessions.items()
            if data.get("last_access", now) + self.SESSION_TIMEOUT > now
        }

    def redirect(self, location):
        """
        Return a 302 redirect response to the specified location.
        """
        return (
            302,
            (
                "<html><head>"
                f"<meta http-equiv='refresh' content='0;url={location}'>"
                "</head></html>"
            ),
        )

    def render_template(self, name, **kwargs):
        """
        Render a Jinja2 template if jinja2 is installed; otherwise raise
        an ImportError.
        """
        if not JINJA_INSTALLED:
            raise ImportError("Jinja2 is not installed.")
        return self.env.get_template(name).render(kwargs)

    def validate_request(self, method):
        """
        Validate incoming request data for both GET and POST.
        """
        try:
            if method == "GET":
                for key, value in self.query_params.items():
                    if (
                        not isinstance(key, str)
                        or not all(isinstance(v, str) for v in value)
                    ):
                        print(f"Invalid query parameter: {key} -> {value}")
                        return False

            if method == "POST":
                for key, value in self.body_params.items():
                    if (
                        not isinstance(key, str)
                        or not all(isinstance(v, str) for v in value)
                    ):
                        print(f"Invalid body parameter: {key} -> {value}")
                        return False

            return True
        except Exception as e:
            print(f"Error during request validation: {e}")
            return False

    def wsgi_app(self, environ, start_response):
        """
        A WSGI-compatible application method that processes incoming requests,
        manages sessions, dispatches to the correct handler function,
        and supports streaming/generator responses.
        """

        path = environ["PATH_INFO"].strip("/")
        method = environ["REQUEST_METHOD"]

        # Default to "index" if root is accessed
        if not path:
            path = "index"

        # Parse query parameters
        self.query_params = parse_qs(environ["QUERY_STRING"])

        path_parts = path.split("/")
        func_name = path_parts[0]
        self.path_params = path_parts[1:]

        # Mock request handler to manage headers and cookies
        class MockRequestHandler:
            def __init__(self, environ):
                self.environ = environ
                self.headers = {
                    key[5:].replace("_", "-").lower(): value
                    for key, value in environ.items()
                    if key.startswith("HTTP_")
                }
                self.cookies = self._parse_cookies()
                self._headers_to_send = []

            def _parse_cookies(self):
                cookies = {}
                if "HTTP_COOKIE" in self.environ:
                    cookie_header = self.environ["HTTP_COOKIE"]
                    for cookie in cookie_header.split(";"):
                        if "=" in cookie:
                            k, v = cookie.strip().split("=", 1)
                            cookies[k] = v
                return cookies

            def send_response(self, code):
                pass  # Not setting status here; done in start_response

            def send_header(self, key, value):
                self._headers_to_send.append((key, value))

            def end_headers(self):
                pass

        request_handler = MockRequestHandler(environ)

        # Ensure session persistence
        session_id = request_handler.cookies.get("session_id")
        if session_id and session_id in self.sessions:
            self.session = self.sessions[session_id]
            self.session["last_access"] = time.time()
            print(f"Using existing session: {session_id}")
        else:
            session_id = str(uuid.uuid4())
            self.session = {"last_access": time.time()}
            self.sessions[session_id] = self.session
            request_handler.send_header(
                "Set-Cookie", f"session_id={session_id}; Path=/; HttpOnly"
            )
            print(f"New session created: {session_id}")

        print(f"Session data: {session_id} -> {self.session}")

        self.request = method
        self.body_params = {}

        if method == "POST":
            try:
                content_length = int(environ.get("CONTENT_LENGTH", 0) or 0)
                body = environ["wsgi.input"].read(content_length).decode(
                    "utf-8", "ignore"
                )
                self.body_params = parse_qs(body)
                print("POST data:", self.body_params)
            except Exception as e:
                start_response("400 Bad Request", [("Content-Type", "text/html")])
                return [f"400 Bad Request: {str(e)}".encode("utf-8")]

        # Find the requested handler
        handler_function = getattr(self, func_name, None)
        if not handler_function:
            start_response("404 Not Found", [("Content-Type", "text/html")])
            return [b"404 Not Found"]

        # Build function arguments
        sig = inspect.signature(handler_function)
        func_args = []

        for param in sig.parameters.values():
            if self.path_params:
                func_args.append(self.path_params.pop(0))
            elif param.name in self.query_params:
                func_args.append(self.query_params[param.name][0])
            elif param.name in self.body_params:
                func_args.append(self.body_params[param.name][0])
            elif param.default is not param.empty:
                func_args.append(param.default)
            else:
                msg = f"400 Bad Request: Missing required parameter '{param.name}'"
                start_response("400 Bad Request", [("Content-Type", "text/html")])
                return [msg.encode("utf-8")]

        # Invoke the handler
        try:
            response = handler_function(*func_args)

            if isinstance(response, tuple) and len(response) == 2:
                status_code, response_body = response
            else:
                status_code, response_body = 200, response

            # Convert code to standard string
            status_map = {
                302: "302 Found",
                404: "404 Not Found",
                500: "500 Internal Server Error",
            }
            status_str = status_map.get(status_code, f"{status_code} OK")

            headers = request_handler._headers_to_send
            if not any(h[0].lower() == "content-type" for h in headers):
                headers.append(("Content-Type", "text/html; charset=utf-8"))

            # Handle streaming (generator) response
            if (
                hasattr(response_body, "__iter__")
                and not isinstance(response_body, (bytes, str))
            ):
                start_response(status_str, headers)

                def byte_stream(gen):
                    for chunk in gen:
                        if isinstance(chunk, str):
                            yield chunk.encode("utf-8")
                        else:
                            yield chunk

                return byte_stream(response_body)

            # Handle standard response
            if isinstance(response_body, str):
                response_body = response_body.encode("utf-8")
            elif not isinstance(response_body, (bytes, bytearray)):
                response_body = str(response_body).encode("utf-8")

            start_response(status_str, headers)
            return [response_body]

        except Exception as e:
            print(f"Error processing request: {e}")
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            return [f"500 Internal Server Error: {str(e)}".encode("utf-8")]

