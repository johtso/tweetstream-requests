"""
Simple iterator class for accessing Twitters streaming API

An instance of TweetStream is iterable. Each iteration returns a dictionary.
The dictionary is the same as the json that is returned from the Twitter
streaming API.

>>> stream = tweetstream.TweetStream("username", "password")
>>> for tweet in stream:
        print tweet


The stream object can also be used as a context, as in

>>> with tweetstream.TweetStream("username", "password") as stream
...     for tweet in stream:
...         print "Got tweet from %-16s\t( tweet %d, rate %.1f tweets/sec)" % (
...                 tweet["user"]["screen_name"], stream.count, stream.rate )

The object exposes the integer count, the number of tweets returned, and
the float rate, the rate at which tweets have been returned. The period over
which the rate is calculated can be changed by setting the value of
rate_period. rate_period should be a number of seconds.
"""
__version__ = "0.1"
__author__ = "Rune Halvorsen <runefh@gmail.com>"
__homepage__ = "http://bitbucket.org/runeh/tweetstream/"
__docformat__ = "restructuredtext"

import urllib2
import time
import anyjson

SPRITZER_URL = "http://stream.twitter.com/spritzer.json"


class AuthenticationError(Exception):
    pass

class TweetStream(object):
    """A network connection to Twitters streamign API

    :param username: Twitter username for the account accessing the API.
    :param password: Twitter password for the account accessing the API.

    :keyword url: URL to connect to. By default, the public "spritzer" url.

    :keyword ssl: see :attr:`ssl`.


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
        until the next time the rate is calculated.

"""

    def __init__(self, username, password, url=SPRITZER_URL):
        self._conn = None
        self._rate_ts = None
        self._rate_cnt = 0
        self._username = username
        self._password = password
        self._authenticated = False

        self.rate_period = 10 # in seconds
        self.url = url
        self.connected = False
        self.starttime = None
        self.count = 0
        self.rate = 0

    def __iter__(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *params):
        if self._conn:
            self._conn.close()
        return False

    def _init_auth(self):
        """Set up authentication for the connection"""
        # stolen from the urllib2 tutorial on voidspace
        try:
            password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            top_level_url = "http://stream.twitter.com/"
            password_mgr.add_password(None, top_level_url, self._username, self._password)
            handler = urllib2.HTTPBasicAuthHandler(password_mgr)
            opener = urllib2.build_opener(handler)
            opener.open(self.url)
            urllib2.install_opener(opener)
        except urllib2.HTTPError, e:
            if e.code==401:
                raise AuthenticationError("Invalid credentials for Twitter")
            else:
                raise

    def _init_conn(self):
        """Open the connection to the twitter server"""
        if not self._authenticated:
            self._init_auth()
        self._conn = urllib2.urlopen(self.url)
        self.connected = True
        if not self.starttime:
            self.starttime = time.time()
        if not self._rate_ts:
            self._rate_ts = time.time()

    def next(self):
        """Return the next available tweet. This call is blocking!"""
        if not self.connected:
            self._init_conn()

        rate_time = time.time() - self._rate_ts
        if not self._rate_ts or rate_time > self.rate_period:
            self.rate = self._rate_cnt / rate_time
            self._rate_cnt = 0
            self._rate_ts = time.time()

        self.count += 1
        self._rate_cnt += 1
        return anyjson.deserialize(self._conn.readline())

    def close(self):
        """
        Close the connection to the streaming server.
        """
        self._conn.close()

