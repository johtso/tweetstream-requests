"""Simple access to Twitter's streaming API"""

__version__ = '2.2-dev'


"""
 .. data:: USER_AGENT

     The default user agent string for stream objects
"""

USER_AGENT = "TweetStream %s" % __version__


from .streamclasses import SampleStream, FilterStream
from .exceptions import (
    TweetStreamError, ConnectionError, ReconnectError,
    ReconnectImmediatelyError, ReconnectLinearlyError,
    ReconnectExponentiallyError, AuthenticationError,
    EnhanceYourCalmError, FatalError,
)
