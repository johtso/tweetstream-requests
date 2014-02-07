"""Tweetstream exceptions"""


class TweetStreamError(Exception):
    """Base class for all tweetstream errors"""

    def __init__(self, reason='', details=None):
        self.reason = reason
        self.details = details

    def __str__(self):
        return '<%s %s>' % (self.__class__.__name__, self.reason)


class FatalError(TweetStreamError):
    """Raised when an unrecoverable issue occurs, such as the request sent
    to Twitter being malformed."""


class ConnectionError(TweetStreamError):
    """Raised when there are network problems. This means when there are
    dns errors, network errors, twitter issues"""


# The following exceptions track the various types of reconnection guidance
# given in the Twitter API documentation
# (https://dev.twitter.com/docs/streaming-api/concepts#connecting). In the
# code, if it's unclear which kind of reconnection is appropriate, the more
# conservative exception is raised.

class ReconnectError(ConnectionError):
    """Base class of the reconnectable connection errors."""


class ReconnectImmediatelyError(ReconnectError):
    '''From Twitter docs: "Once a valid connection connection drops, reconnect
    immediately."'''


class ReconnectLinearlyError(ReconnectError):
    '''From Twitter docs: "When a network error (TCP/IP level) is encountered,
    back off linearly. Perhaps start at 250 milliseconds and cap at 16
    seconds. Network layer problems are generally transitory and tend to clear
    quickly."'''


class ReconnectExponentiallyError(ReconnectError):
    '''From Twitter docs: "When a HTTP error (> 200) is returned, back off
    exponentially. Perhaps start with a 10 second wait, double on each
    subsequent failure, and finally cap the wait at 240 seconds. Consider
    sending an alert to a human operator after multiple HTTP errors, as there
    is probably a client configuration issue that is unlikely to be resolved
    without human intervention."'''


# Parent class per Twitter error handling guidance noted above.
class AuthenticationError(ReconnectExponentiallyError):
    """Exception raised if the username/password is not accepted"""

class EnhanceYourCalmError(ReconnectExponentiallyError):
    '''Exception raised when a 420 response is recieved signifying that you
    are being rate limited. From Twitter docs: "Back off exponentially for
    HTTP 420 errors. Start with a 1 minute wait and double each attempt.
    Note that every HTTP 420 received increases the time you must wait until
    rate limiting will no longer will be in effect for your account."'''
