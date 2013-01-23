import socket
import threading
import contextlib
from wsgiref.simple_server import make_server
try:
    from http.server import BaseHTTPRequestHandler
except ImportError:
    from BaseHTTPServer import BaseHTTPRequestHandler

http_responses = BaseHTTPRequestHandler.responses


class ServerContext(object):
    """Context object with information about a running test server."""

    def __init__(self, address, port):
        self.address = address
        self.port = port

    @property
    def baseurl(self):
        return "http://%s:%s" % (self.address, self.port)

    def __repr__(self):
        return "<ServerContext %s >" % self.baseurl

    __str__ = __repr__


class TestServerThread(threading.Thread):
    """Thread class for a running test server"""

    daemon = True

    def __init__(self, response, status, headers, address, port):
        self.address = address
        self.port = port
        self._app = self._make_app(response, status, headers)
        self._server = None
        self.error = None

        self.startup_finished = threading.Event()

        threading.Thread.__init__(self)

    def _format_status(self, status):
        if isinstance(status, int):
            reason_phrase = http_responses[status][0]
            status = '{} {}'.format(status, reason_phrase)
        elif not isinstance(status, basestring):
            raise ValueError('Status must be string or int')
        return status

    def _make_app(self, response, status, headers):
        status = self._format_status(status)

        def app(environ, start_response):
            start_response(status, list(headers))
            if response:
                iter_resp = None
                if callable(response):
                    iter_resp = response()
                elif hasattr(response, '__iter__'):
                    iter_resp = response
                if iter_resp:
                    for x in iter_resp:
                        yield x
                else:
                    yield response

        return app

    def _init_server(self, address, port, app):
        try:
            self._server = make_server(address, port, app)
        except socket.error as exc:
            self.error = exc
            return
        else:
            self._server.timeout = 0.1
            self._server.allow_reuse_address = True

    def stop(self):
        self._server.shutdown()

    def run(self):
        self._init_server(self.address, self.port, self._app)

        if self._server:
            # Wait for a handle_request call to time out so we know we're ready
            self._server.handle_request()
            self.startup_finished.set()

            self._server.serve_forever(poll_interval=0.1)
        else:
            # Something went wrong spinning up server
            self.startup_finished.set()


@contextlib.contextmanager
def test_server(response=None, status='200 OK', headers=[],
                address='localhost', port=8514):
    """Context that makes available a web server in a separate thread"""

    thread = TestServerThread(response=response, status=status,
                              headers=headers, address=address, port=port)
    thread.start()
    thread.startup_finished.wait()
    if thread.error:
        raise thread.error

    try:
        yield ServerContext(thread.address, thread.port)
    finally:
        thread.stop()
        thread.join(5)
        if thread.isAlive():
            raise Warning("Test server could not be stopped")
