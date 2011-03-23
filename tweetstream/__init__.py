"""
Simple Twitter streaming API access
"""
__version__ = "0.3.6"
__author__ = "Rune Halvorsen <runefh@gmail.com>"
__homepage__ = "http://bitbucket.org/runeh/tweetstream/"
__docformat__ = "restructuredtext"

import urllib
import urllib2
import socket
import time
import anyjson


"""
 .. data:: USER_AGENT

     The default user agent string for stream objects
"""

USER_AGENT = "TweetStream %s" % __version__


class TweetStreamError(Exception):
    """Base class for all tweetstream errors"""
    pass


class AuthenticationError(TweetStreamError):
    """Exception raised if the username/password is not accepted"""
    pass


class ConnectionError(TweetStreamError):
    """Raised when there are network problems. This means when there are
    dns errors, network errors, twitter issues"""

    def __init__(self, reason, details=None):
        self.reason = reason
        self.details = details

    def __str__(self):
        return '<ConnectionError %s>' % self.reason


class BaseStream(object):
    """A network connection to Twitters streaming API

    :param username: Twitter username for the account accessing the API.
    :param password: Twitter password for the account accessing the API.
    :keyword count: Number of tweets from the past to get before switching to
      live stream.
    :keyword url: Endpoint URL for the object. Note: you should not
      need to edit this. It's present to make testing easier.

    .. attribute:: connected

        True if the object is currently connected to the stream.

    .. attribute:: url

        The URL to which the object is connected

    .. attribute:: starttime

        The timestamp, in seconds since the epoch, the object connected to the
        streaming api.

    .. attribute:: catchup

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

    def __init__(self, username, password, catchup=None, url=None):
        self._conn = None
        self._rate_ts = None
        self._rate_cnt = 0
        self._username = username
        self._password = password
        self._catchup_count = catchup

        self.rate_period = 10  # in seconds
        self.connected = False
        self.starttime = None
        self.count = 0
        self.rate = 0
        self.user_agent = USER_AGENT
        if url: self.url = url

    def __iter__(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *params):
        self.close()
        return False

    def _init_conn(self):
        """Open the connection to the twitter server"""
        headers = {'User-Agent': self.user_agent}

        postdata = self._get_post_data() or {}
        if self._catchup_count:
            postdata["count"] = self._catchup_count

        poststring = urllib.urlencode(postdata) if postdata else None
        req = urllib2.Request(self.url, poststring, headers)

        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, self.url, self._username, self._password)
        handler = urllib2.HTTPBasicAuthHandler(password_mgr)
        opener = urllib2.build_opener(handler)

        try:
            self._conn = opener.open(req)
        except urllib2.HTTPError, exception:
            if exception.code == 401:
                raise AuthenticationError("Access denied")
            elif exception.code == 404:
                raise ConnectionError("URL not found: %s" % self.url)
            else:  # re raise. No idea what would cause this, so want to know
                raise
        except urllib2.URLError, exception:
            raise ConnectionError(exception.reason)

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

    def next(self):
        """Return the next available tweet. This call is blocking!"""
        while True:
            try:
                if not self.connected:
                    self._init_conn()

                rate_time = time.time() - self._rate_ts
                if not self._rate_ts or rate_time > self.rate_period:
                    self.rate = self._rate_cnt / rate_time
                    self._rate_cnt = 0
                    self._rate_ts = time.time()

                data = self._conn.readline()
                if data == "":  # something is wrong
                    self.close()
                    raise ConnectionError("Got entry of length 0. Disconnected")
                elif data.isspace():
                    continue

                data = anyjson.deserialize(data)
                self.count += 1
                self._rate_cnt += 1
                return data

            except ValueError, e:
                self.close()
                raise ConnectionError("Got invalid data from twitter",
                                      details=data)

            except socket.error, e:
                self.close()
                raise ConnectionError("Server disconnected")

    def close(self):
        """
        Close the connection to the streaming server.
        """
        self.connected = False
        if self._conn:
            self._conn.close()


class SampleStream(BaseStream):
    url = "http://stream.twitter.com/1/statuses/sample.json"


class TweetStream(SampleStream):
    def __init__(self, *args, **kwargs):
        # warn about deprecation
        SampleStream.__init__(self, *args, **kwargs)


class FilterStream(BaseStream):
    url = "http://stream.twitter.com/1/statuses/filter.json"

    def __init__(self, username, password, follow=None, locations=None,
                 track=None, **kwargs):
        self._follow = follow
        self._locations = locations
        self._track = track
        BaseStream.__init__(self, username, password, **kwargs)

    def _get_post_data(self):
        postdata = {}
        if self._follow: postdata["follow"] = ",".join([str(e) for e in self._follow])
        if self._locations: postdata["locations"] = ",".join(self._locations)
        if self._track: postdata["track"] = ",".join(self._track)
        return postdata


class FollowStream(FilterStream):
    def __init__(self, username, password, follow, **kwargs):
        FilterStream.__init__(self, username, password, follow=follow, **kwargs)


class TrackStream(FilterStream):
    def __init__(self, username, password, track, **kwargs):
        FilterStream.__init__(self, username, password, track=track, **kwargs)


class LocationStream(FilterStream):
    def __init__(self, username, password, location, **kwargs):
        FilterStream.__init__(self, username, password, location=location, **kwargs)


class ReconnectingTweetStream(TweetStream):
    """TweetStream class that automatically tries to reconnect if the
    connecting goes down. Reconnecting, and waiting for reconnecting, is
    blocking.

    :param username: See :TweetStream:

    :param password: See :TweetStream:

    :keyword url: See :TweetStream:

    :keyword reconnects: Number of reconnects before a ConnectionError is
        raised. Default is 3

    :error_cb: Optional callable that will be called just before trying to
        reconnect. The callback will be called with a single argument, the
        exception that caused the reconnect attempt. Default is None

    :retry_wait: Time to wait before reconnecting in seconds. Default is 5

    """

    def __init__(self, username, password, url="sample",
                 reconnects=3, error_cb=None, retry_wait=5):
        self.max_reconnects = reconnects
        self.retry_wait = retry_wait
        self._reconnects = 0
        self._error_cb = error_cb
        TweetStream.__init__(self, username, password, url=url)

    def next(self):
        while True:
            try:
                return TweetStream.next(self)
            except ConnectionError, e:
                self._reconnects += 1
                if self._reconnects > self.max_reconnects:
                    raise ConnectionError("Too many retries")

                # Note: error_cb is not called on the last error since we
                # raise a ConnectionError instead
                if  callable(self._error_cb):
                    self._error_cb(e)

                time.sleep(self.retry_wait)
        # Don't listen to auth error, since we can't reasonably reconnect
        # when we get one.
