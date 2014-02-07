from __future__ import unicode_literals

import time
import json
import ssl

import requests
try:
    from http.client import IncompleteRead
except ImportError:
    from httplib import IncompleteRead

from . import USER_AGENT
from .exceptions import (
    ReconnectImmediatelyError, ReconnectLinearlyError, EnhanceYourCalmError,
    ReconnectExponentiallyError, AuthenticationError, FatalError,
)


class BaseStream(object):
    """A network connection to Twitters streaming API

    :param username: Twitter username for the account accessing the API.
    :param password: Twitter password for the account accessing the API.
    :keyword count: Number of tweets from the past to get before switching to
      live stream.
    :keyword raw: If True, return each tweet's raw data direct from the socket,
      without UTF8 decoding or parsing, rather than a parsed object. The
      default is False.
    :keyword timeout: If non-None, set a timeout in seconds on the receiving
      socket. Certain types of network problems (e.g., disconnecting a VPN)
      can cause the connection to hang, leading to indefinite blocking that
      requires kill -9 to resolve. Setting a timeout leads to an orderly
      shutdown in these cases. The default is Twitter's suggested 90 seconds.
    :keyword url: Endpoint URL for the object. Note: you should not
      need to edit this. It's present to make testing easier.

    .. attribute:: connected

        True if the object is currently connected to the stream.

    .. attribute:: url

        The URL to which the object is connected

    .. attribute:: starttime

        The timestamp, in seconds since the epoch, the object connected to the
        streaming api.

    .. attribute:: count

        The number of tweets that have been returned by the object.

    .. attribute:: rate

        The rate at which tweets have been returned from the object as a
        float. see also :attr: `rate_period`.

    .. attribute:: rate_period

        The ammount of time to sample tweets to calculate tweet rate. By
        default 10 seconds. Changes to this attribute will not be reflected
        until the next time the rate is calculated. The rate of tweets vary
        with time of day etc. so it's usefull to set this to something
        sensible.

    .. attribute:: user_agent

        User agent string that will be included in the request. NOTE: This can
        not be changed after the connection has been made. This property must
        thus be set before accessing the iterator. The default is set in
        :attr: `USER_AGENT`.
    """

    def __init__(self, auth=None, session=None, catchup=None, parse_json=True,
                 decode_unicode=True, timeout=90, url=None):
        self._conn = None
        self._rate_ts = None
        self._rate_cnt = 0
        self._auth = auth
        self._catchup_count = catchup
        if parse_json and not decode_unicode:
            raise ValueError('Cannot parse json without first decoding.')
        self._parse_json = parse_json
        self._decode_unicode = decode_unicode
        self._timeout = timeout
        self._iter = self.__iter__()

        self.rate_period = 10  # in seconds
        self.connected = False
        self.starttime = None
        self.count = 0
        self.rate = 0
        self.user_agent = USER_AGENT
        if url: self.url = url

        self._auth = auth
        self._client = session

    def __enter__(self):
        return self

    def __exit__(self, *params):
        self.close()
        return False

    def _init_conn(self):
        """Open the connection to the twitter server"""

        if not self._client:
            self._client = requests.Session()

        self._client.headers.update({'User-Agent': self.user_agent})

        if self._auth:
            self._client.auth = self._auth

        postdata = self._get_post_data() or {}
        if self._catchup_count:
            postdata["count"] = self._catchup_count

        req_method = 'post' if postdata else 'get'

        # If connecting fails, convert to ReconnectExponentiallyError so
        # clients can implement appropriate backoff.
        try:
            self._conn = self._client.request(req_method, self.url, data=postdata,
                                              stream=True, timeout=self._timeout)
            self._conn.raise_for_status()
        except requests.HTTPError as e:
            code = e.response.status_code
            if code == 401:
                raise AuthenticationError("Access denied")
            elif code == 404:
                raise FatalError("%s: %s" % (self.url, e))
            elif code in (406, 413, 416):
                raise FatalError(str(e))
            elif code == 420:
                raise EnhanceYourCalmError
            else:
                raise ReconnectExponentiallyError(str(e))
        except requests.ConnectionError as e:
            raise ReconnectExponentiallyError(str(e))
        else:
            self.connected = True
        if not self.starttime:
            self.starttime = time.time()

    def _get_post_data(self):
        """Subclasses that need to add post data to the request can override
        this method and return post data. The data should be in the format
        returned by urllib.urlencode."""
        return None

    def _iter_lines(self):
        buf = b""

        for chunk in self._conn.iter_content(chunk_size=1):
            buf += chunk

            if buf == b"":  # something is wrong
                self.close()
                raise ReconnectLinearlyError("Got entry of length 0. Disconnected")

            if buf.isspace():
                buf = b""
                continue
            elif b"\r\n" not in buf:  # not enough data yet. Loop around
                continue

            lines = buf.splitlines()
            if lines and lines[-1] and chunk and lines[-1][-1] == chunk[-1]:
                buf = lines.pop()
            else:
                buf = b""

            for line in lines:
                if line:
                    yield line

    def __iter__(self):
        if not self.connected:
            self._init_conn()
        try:
            for line in self._iter_lines():
                if self._decode_unicode:
                    try:
                        line = line.decode('utf-8')
                    except UnicodeError:
                        raise ReconnectImmediatelyError("Could not decode as unicode")
                if self._parse_json:
                    try:
                        tweet = json.loads(line)
                    except ValueError:
                        self.close()
                        raise ReconnectImmediatelyError("Got invalid data from twitter", details=line)
                else:
                    tweet = line

                if 'text' in tweet:
                    self.count += 1
                yield tweet
        except (requests.Timeout, ssl.SSLError) as e:
            if isinstance(e, ssl.SSLError):
                # When using https timeouts cause a generic SSLError to be raised
                # so we need to check the error text.
                if not 'timed out' in e.message:
                    raise
                else:
                    raise ReconnectImmediatelyError("Stream timed out.")
        except IncompleteRead as e:
            raise ReconnectImmediatelyError(str(e))

        raise ReconnectImmediatelyError("Server disconnected.")

    def __next__(self):
        """Return the next available tweet. This call is blocking!"""
        return next(self._iter)

    next = __next__

    def close(self):
        """
        Close the connection to the streaming server.
        """
        self.connected = False
        if self._conn:
            self._conn.close()


class SampleStream(BaseStream):
    url = "https://stream.twitter.com/1.1/statuses/sample.json"


class FilterStream(BaseStream):
    url = "https://stream.twitter.com/1.1/statuses/filter.json"

    def __init__(self, auth=None, follow=None, locations=None,
                 track=None, catchup=None, parse_json=True,
                 decode_unicode=True, timeout=90, url=None):
        if not track and not follow:
            raise ValueError('Must specify at least one track or follow.')

        self.parameters = dict(
            track=track, follow=follow, locations=locations
        )

        BaseStream.__init__(self, auth=auth, parse_json=parse_json,
                            decode_unicode=decode_unicode, timeout=timeout,
                            url=url)

    def _get_post_data(self):
        post_data = {}
        for key, value in self.parameters.items():
            if value:
                post_data[key] = ','.join(value)
        return post_data
