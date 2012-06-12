import time
import json

import requests

from . import AuthenticationError, USER_AGENT
from . import ReconnectImmediatelyError, ReconnectLinearlyError, ReconnectExponentiallyError


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
      shutdown in these cases. The default is None (i.e., no timeout).
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

    def __init__(self, username, password,
                 catchup=None, raw=False, timeout=None, url=None):
        self._conn = None
        self._rate_ts = None
        self._rate_cnt = 0
        self._username = username
        self._password = password
        self._catchup_count = catchup
        self._raw_mode = raw
        self._timeout = timeout
        self._iter = self.__iter__()

        self.rate_period = 10  # in seconds
        self.connected = False
        self.starttime = None
        self.count = 0
        self.rate = 0
        self.user_agent = USER_AGENT
        if url: self.url = url

        self._client = None

    def __enter__(self):
        return self

    def __exit__(self, *params):
        self.close()
        return False

    def _init_conn(self):
        """Open the connection to the twitter server"""

        if not self._client:
            headers = {'User-Agent': self.user_agent}
            auth = (self._username, self._password)
            config = {'danger_mode': True, 'keep_alive': False}
            self._client = requests.session(headers=headers,
                                            auth=auth,
                                            timeout=self._timeout,
                                            config=config)

        postdata = self._get_post_data() or {}
        if self._catchup_count:
            postdata["count"] = self._catchup_count

        req_method = 'post' if postdata else 'get'

        # If connecting fails, convert to ReconnectExponentiallyError so
        # clients can implement appropriate backoff.
        try:
            self._conn = self._client.request(req_method, self.url, data=postdata)
        except requests.HTTPError, e:
            code = e.response.status_code
            if code == 401:
                raise AuthenticationError("Access denied")
            elif code == 404:
                raise ReconnectExponentiallyError("%s: %s" % (self.url, e))
            else:
                raise ReconnectExponentiallyError(str(e))
        except requests.ConnectionError, e:
            raise ReconnectExponentiallyError(str(e))
        else:
            self.connected = True

        if not self.starttime:
            self.starttime = time.time()
        if not self._rate_ts:
            self._rate_ts = time.time()

    def _get_post_data(self):
        """Subclasses that need to add post data to the request can override
        this method and return post data. The data should be in the format
        returned by urllib.urlencode."""
        return None

    def _update_rate(self):
        rate_time = time.time() - self._rate_ts
        if not self._rate_ts or rate_time > self.rate_period:
            self.rate = self._rate_cnt / rate_time
            self._rate_cnt = 0
            self._rate_ts = time.time()

    def __iter__(self):
        # buf = b""
        while True:
            try:
                if not self.connected:
                    self._init_conn()

                for line in self._conn.iter_lines(chunk_size=1):
                    if (self._raw_mode):
                        tweet = line
                    else:
                        line = line.decode("utf8")
                        try:
                            tweet = json.loads(line)
                        except ValueError, e:
                            self.close()
                            raise ReconnectImmediatelyError("Got invalid data from twitter", details=line)

                    if 'text' in tweet:
                        self.count += 1
                        self._rate_cnt += 1
                    yield tweet

            except RuntimeError, e:
                self.close()
                raise ReconnectImmediatelyError("Server disconnected: %s" % (e, ))

    def next(self):
        """Return the next available tweet. This call is blocking!"""
        return self._iter.next()

    def close(self):
        """
        Close the connection to the streaming server.
        """
        self.connected = False
        if self._conn:
            self._conn.raw.release_conn()


class SampleStream(BaseStream):
    url = "https://stream.twitter.com/1/statuses/sample.json"


class FilterStream(BaseStream):
    url = "https://stream.twitter.com/1/statuses/filter.json"

    def __init__(self, username, password, follow=None, locations=None,
                 track=None, catchup=None, raw=False, timeout=None, url=None):
        self._follow = follow
        self._locations = locations
        self._track = track
        # remove follow, locations, track
        BaseStream.__init__(self, username, password,
                            raw=raw, timeout=timeout, url=url)

    def _get_post_data(self):
        postdata = {}
        if self._follow: postdata["follow"] = ",".join([str(e) for e in self._follow])
        if self._locations: postdata["locations"] = ",".join(self._locations)
        if self._track: postdata["track"] = ",".join(self._track)
        return postdata
