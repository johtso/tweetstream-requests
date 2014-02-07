# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import time

import pytest
from pytest import raises
slow = pytest.mark.slow

from tweetstream import (
    SampleStream, FilterStream, ConnectionError, AuthenticationError, 
    EnhanceYourCalmError, ReconnectExponentiallyError, FatalError,
)

from servercontext import test_server

single_tweet = (r"""{"in_reply_to_status_id":null,"in_reply_to_user_id":null,"favorited":false,"created_at":"Tue Jun 16 10:40:14 +0000 2009","in_reply_to_screen_name":null,"text":"ʀεϲɸʀδ ιƞδυστʀψ just keeps on amazing me: http:\/\/is.gd\/13lFo - $150k per song you've SHARED, not that somebody has actually DOWNLOADED.","user":{"notifications":null,"profile_background_tile":false,"followers_count":206,"time_zone":"Copenhagen","utc_offset":3600,"friends_count":191,"profile_background_color":"ffffff","profile_image_url":"http:\/\/s3.amazonaws.com\/twitter_production\/profile_images\/250715794\/profile_normal.png","description":"Digital product developer, currently at Opera Software. My tweets are my opinions, not those of my employer.","verified_profile":false,"protected":false,"favourites_count":0,"profile_text_color":"3C3940","screen_name":"eiriksnilsen","name":"Eirik Stridsklev N.","following":null,"created_at":"Tue May 06 12:24:12 +0000 2008","profile_background_image_url":"http:\/\/s3.amazonaws.com\/twitter_production\/profile_background_images\/10531192\/160x600opera15.gif","profile_link_color":"0099B9","profile_sidebar_fill_color":"95E8EC","url":"http:\/\/www.stridsklev-nilsen.no\/eirik","id":14672543,"statuses_count":506,"profile_sidebar_border_color":"5ED4DC","location":"Oslo, Norway"},"id":2190767504,"truncated":false,"source":"<a href=\"http:\/\/widgets.opera.com\/widget\/7206\">Twitter Opera widget<\/a>"}"""
                + '\r\n')

BASIC_AUTH = ('username', 'password')

streamtypes = [
    dict(cls=SampleStream, args=[], kwargs=dict(auth=BASIC_AUTH)),
    dict(cls=FilterStream, args=[], kwargs=dict(auth=BASIC_AUTH,
                                                track=['υƞιϲɸδε', 'foo'],
                                                follow=['υƞιϲɸδε', 'foo'],
                                                locations=['υƞιϲɸδε', 'foo'])),
]


def parameterized(funcarglist):
    def wrapper(function):
        function.funcarglist = funcarglist
        return function
    return wrapper


def pytest_generate_tests(metafunc):
    for funcargs in getattr(metafunc.function, 'funcarglist', ()):
        metafunc.addcall(funcargs=funcargs)


def test_initialize_filterstream_without_params():
    with pytest.raises(ValueError):
        FilterStream(auth=BASIC_AUTH)


@parameterized(streamtypes)
@pytest.mark.parametrize(('status_code', 'exception'), [
    # Unauthorized
    (401, AuthenticationError),
    # Not Found
    (404, FatalError),
    # Not Acceptable
    (406, FatalError),
    # Too Long
    (413, FatalError),
    # Range Unacceptable
    (416, FatalError),
    # Unhandled failure codes
    (418, ReconnectExponentiallyError),
    # Enhance Your Calm
    (420, EnhanceYourCalmError),
])
def test_reponse_code_exceptions(cls, args, kwargs, status_code, exception):
    """Test that the proper exception is raised when the given status code is
    recieved"""

    with raises(exception):
        with test_server(status=status_code) as server:
            cls.url = server.baseurl
            stream = cls(*args, **kwargs)
            for e in stream: pass


@parameterized(streamtypes)
def test_bad_content(cls, args, kwargs):
    """Test error handling if we are given invalid data"""

    def bad_content():
        for n in xrange(10):
            # what json we pass doesn't matter. It's not verifying the
            # strcuture, only checking that it's parsable
            yield "[1,2,3]\r\n"
        yield "[1,2, I need no stinking close brace\r\n"
        yield "[1,2,3]\r\n"

    with raises(ConnectionError):
        with test_server(response=bad_content) as server:
            cls.url = server.baseurl
            stream = cls(*args, **kwargs)
            for tweet in stream:
                pass


@parameterized(streamtypes)
def test_closed_connection(cls, args, kwargs):
    """Test error handling if server unexpectedly closes connection"""
    cnt = 1000

    def bad_content():
        for n in xrange(cnt):
            # what json we pass doesn't matter. It's not verifying the
            # strcuture, only checking that it's parsable
            yield "[1,2,3]\r\n"

    with raises(ConnectionError):
        with test_server(response=bad_content) as server:
            cls.url = server.baseurl
            stream = cls(*args, **kwargs)
            for tweet in stream:
                pass


@parameterized(streamtypes)
def test_bad_host(cls, args, kwargs):
    """Test behaviour if we can't connect to the host"""
    with raises(ConnectionError):
        cls.url = "http://wedfwecfghhreewerewads.foo"
        stream = cls(*args, **kwargs)
        next(stream)


@parameterized(streamtypes)
def smoke_test_receive_tweets(cls, args, kwargs):
    """Receive 100k tweets and disconnect (slow)"""
    total = 100000

    def tweetsource():
        while True:
            yield single_tweet

    with test_server(response=tweetsource) as server:
        cls.url = server.baseurl
        stream = cls(*args, **kwargs)
        for tweet in stream:
            if stream.count == total:
                break


@parameterized(streamtypes)
def test_keepalive(cls, args, kwargs):
    """Make sure we behave sanely when there are keepalive newlines in the
    data recevived from twitter"""

    def tweetsource():
        yield single_tweet
        yield "\r\n"
        yield "\r\n"
        yield single_tweet
        yield "\r\n"
        yield "\r\n"
        yield "\r\n"
        yield "\r\n"
        yield "\r\n"
        yield "\r\n"
        yield "\r\n"
        yield single_tweet
        yield "\r\n"

    with test_server(response=tweetsource) as server:
        cls.url = server.baseurl
        stream = cls(*args, **kwargs)
        try:
            for tweet in stream:
                pass
        except ConnectionError:
            assert stream.count == 3, "Got %s, wanted 3" % stream.count
        else:
            assert False, "Didn't handle keepalive"


@slow
@parameterized(streamtypes)
def test_buffering(cls, args, kwargs):
    """Test if buffering stops data from being returned immediately.
    If there is some buffering in play that might mean data is only returned
    from the generator when the buffer is full. If buffer is bigger than a
    tweet, this will happen. Default buffer size in the part of socket lib
    that enables readline is 8k. Max tweet length is around 3k."""

    def tweetsource():
        yield single_tweet
        time.sleep(2)
        # need to yield a bunch here so we're sure we'll return from the
        # blocking call in case the buffering bug is present.
        for n in xrange(100):
            yield single_tweet

    with test_server(response=tweetsource) as server:
        cls.url = server.baseurl
        stream = cls(*args, **kwargs)
        start = time.time()
        next(stream)
        first = time.time()
        diff = first - start
        assert diff < 1, "Getting first tweet took too long! %i > 1" % (diff)
