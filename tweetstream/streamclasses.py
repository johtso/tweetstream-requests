import time
import urllib
import urllib2
import socket
import anyjson

from . import AuthenticationError, ConnectionError, USER_AGENT

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
                if 'text' in data:
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


class FilterStream(BaseStream):
    url = "http://stream.twitter.com/1/statuses/filter.json"

    def __init__(self, username, password, follow=None, locations=None,
                 track=None, catchup=None, url=None):
        self._follow = follow
        self._locations = locations
        self._track = track
        # remove follow, locations, track
        BaseStream.__init__(self, username, password, url=url)

    def _get_post_data(self):
        postdata = {}
        if self._follow: postdata["follow"] = ",".join([str(e) for e in self._follow])
        if self._locations: postdata["locations"] = ",".join(self._locations)
        if self._track: postdata["track"] = ",".join(self._track)
        return postdata
