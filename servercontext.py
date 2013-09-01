import socket
import random
import threading
import contextlib
from wsgiref.simple_server import make_server
try:
    from http.server import BaseHTTPRequestHandler
except ImportError:
    from BaseHTTPServer import BaseHTTPRequestHandler

# Python 3
try:
    unicode
except NameError:
    basestring = (str, bytes)

http_responses = BaseHTTPRequestHandler.responses
http_responses.update({
    420: ('Enhance your calm', 'Increase your relaxation'),
    418: ("I'm a teapot", 'Short and stout'),
})


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

    def __init__(self, response, status, headers):
        self.address = 'localhost'
        self.port = None
        self._app = self._make_app(response, status, headers)
        self._server = None
        self.error = None

        self.startup_finished = threading.Event()

        threading.Thread.__init__(self)

    def _format_status(self, status):
        if isinstance(status, int):
            reason_phrase = http_responses[status][0]
            status = '{0} {1}'.format(status, reason_phrase)
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
                        yield x.encode('utf-8')
                else:
                    yield response.encode('utf-8')

        return app

    def _init_server(self, app):
        attempts = 0
        while attempts < 10:
            self.port = random.randint(1025, 49151)
            try:
                self._server = make_server(self.address, self.port, app)
            except socket.error as exc:
                self.error = exc
                attempts += 1
            else:
                self.error = None
                self._server.timeout = 0.1
                self._server.allow_reuse_address = True
                return

    def stop(self):
        self._server.shutdown()

    def run(self):
        self._init_server(self._app)

        if self._server:
            # Wait for a handle_request call to time out so we know we're ready
            self._server.handle_request()
            self.startup_finished.set()

            self._server.serve_forever(poll_interval=0.1)
        else:
            # Something went wrong spinning up server
            self.startup_finished.set()


@contextlib.contextmanager
def test_server(response=None, status='200 OK', headers=[]):
    """Context that makes available a web server in a separate thread"""

    thread = TestServerThread(response=response, status=status,
                              headers=headers)
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
