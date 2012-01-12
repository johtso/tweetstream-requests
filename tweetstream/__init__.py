"""
Simple Twitter streaming API access
"""
__version__ = "1.1.1"
__author__ = "Rune Halvorsen <runefh@gmail.com>"
__homepage__ = "http://bitbucket.org/runeh/tweetstream/"
__docformat__ = "restructuredtext"


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
        return '<%s %s>' % (self.__class__.__name__, self.reason)


# The following exceptions track the various types of reconnection guidance
# given in the Twitter API documentation
# (https://dev.twitter.com/docs/streaming-api/concepts#connecting). In the
# code, if it's unclear which kind of reconnection is appropriate, the more
# conservative exception is raised.

class ReconnectError(ConnectionError):
    """Base class of the reconnectable connection errors."""
    pass

class ReconnectImmediatelyError(ReconnectError):
    '''From Twitter docs: "Once a valid connection connection drops, reconnect
    immediately."'''
    pass

class ReconnectLinearlyError(ReconnectError):
    '''From Twitter docs: "When a network error (TCP/IP level) is encountered,
    back off linearly. Perhaps start at 250 milliseconds and cap at 16
    seconds. Network layer problems are generally transitory and tend to clear
    quickly."'''
    pass

class ReconnectExponentiallyError(ReconnectError):
    '''From Twitter docs: "When a HTTP error (> 200) is returned, back off
    exponentially. Perhaps start with a 10 second wait, double on each
    subsequent failure, and finally cap the wait at 240 seconds. Consider
    sending an alert to a human operator after multiple HTTP errors, as there
    is probably a client configuration issue that is unlikely to be resolved
    without human intervention."'''
    pass
    
from .streamclasses import SampleStream, FilterStream
from .deprecated import FollowStream, TrackStream, LocationStream, TweetStream, ReconnectingTweetStream
