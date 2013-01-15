"""Simple access to Twitter's streaming API"""

VERSION = (1, 2)
__version__ = ".".join(map(str, VERSION[0:3])) + "".join(VERSION[3:])
__author__ = "Rune Halvorsen"
__contact__ = "runefh@gmail.com"
__homepage__ = "http://bitbucket.org/runeh/tweetstream/"
__docformat__ = "restructuredtext"

# -eof meta-

"""
 .. data:: USER_AGENT

     The default user agent string for stream objects
"""

USER_AGENT = "TweetStream %s" % __version__


from .streamclasses import SampleStream, FilterStream
from .exceptions import (
    TweetStreamError, ConnectionError, ReconnectError,
    ReconnectImmediatelyError, ReconnectLinearlyError,
    ReconnectExponentiallyError, AuthenticationError
)
from .deprecated import (
    FollowStream, TrackStream, LocationStream, TweetStream,
    ReconnectingTweetStream
)
