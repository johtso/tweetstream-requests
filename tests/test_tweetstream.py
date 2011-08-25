import contextlib
import threading
import time

from tweetstream import TweetStream, FollowStream, TrackStream, LocationStream
from tweetstream import ConnectionError, AuthenticationError, SampleStream, FilterStream

import pytest
from pytest import raises
slow = pytest.mark.slow

from servercontext import test_server

single_tweet = r"""{"in_reply_to_status_id":null,"in_reply_to_user_id":null,"favorited":false,"created_at":"Tue Jun 16 10:40:14 +0000 2009","in_reply_to_screen_name":null,"text":"record industry just keeps on amazing me: http:\/\/is.gd\/13lFo - $150k per song you've SHARED, not that somebody has actually DOWNLOADED.","user":{"notifications":null,"profile_background_tile":false,"followers_count":206,"time_zone":"Copenhagen","utc_offset":3600,"friends_count":191,"profile_background_color":"ffffff","profile_image_url":"http:\/\/s3.amazonaws.com\/twitter_production\/profile_images\/250715794\/profile_normal.png","description":"Digital product developer, currently at Opera Software. My tweets are my opinions, not those of my employer.","verified_profile":false,"protected":false,"favourites_count":0,"profile_text_color":"3C3940","screen_name":"eiriksnilsen","name":"Eirik Stridsklev N.","following":null,"created_at":"Tue May 06 12:24:12 +0000 2008","profile_background_image_url":"http:\/\/s3.amazonaws.com\/twitter_production\/profile_background_images\/10531192\/160x600opera15.gif","profile_link_color":"0099B9","profile_sidebar_fill_color":"95E8EC","url":"http:\/\/www.stridsklev-nilsen.no\/eirik","id":14672543,"statuses_count":506,"profile_sidebar_border_color":"5ED4DC","location":"Oslo, Norway"},"id":2190767504,"truncated":false,"source":"<a href=\"http:\/\/widgets.opera.com\/widget\/7206\">Twitter Opera widget<\/a>"}""" + "\r"


def parameterized(funcarglist):
    def wrapper(function):
        function.funcarglist = funcarglist
        return function
    return wrapper

def pytest_generate_tests(metafunc):
    for funcargs in getattr(metafunc.function, 'funcarglist', ()):
        metafunc.addcall(funcargs=funcargs)


streamtypes = [
    dict(cls=TweetStream, args=[], kwargs=dict()),
    dict(cls=SampleStream, args=[], kwargs=dict()),
    dict(cls=FilterStream, args=[], kwargs=dict(track=("test",))),
    dict(cls=FollowStream, args=[[1, 2, 3]], kwargs=dict()),
    dict(cls=TrackStream, args=["opera"], kwargs=dict()),
    dict(cls=LocationStream, args=["123,4321"], kwargs=dict())
]


@parameterized(streamtypes)
def test_bad_auth(cls, args, kwargs):
    """Test that the proper exception is raised when the user could not be
    authenticated"""
    def auth_denied(request):
        request.send_error(401)

    with raises(AuthenticationError):
        with test_server(handler=auth_denied, methods=("post", "get"), port="random") as server:
            stream = cls("user", "passwd", *args, url=server.baseurl)
            for e in stream: pass


@parameterized(streamtypes)
def test_404_url(cls, args, kwargs):
    """Test that the proper exception is raised when the stream URL can't be
    found"""
    def not_found(request):
        request.send_error(404)

    with raises(ConnectionError):
        with test_server(handler=not_found, methods=("post", "get"), port="random") as server:
            stream = cls("user", "passwd", *args, url=server.baseurl)
            for e in stream: pass


@parameterized(streamtypes)
def test_bad_content(cls, args, kwargs):
    """Test error handling if we are given invalid data"""
    def bad_content(request):
        for n in xrange(10):
            # what json we pass doesn't matter. It's not verifying the
            # strcuture, only checking that it's parsable
            yield "[1,2,3]\r"
        yield "[1,2, I need no stinking close brace\r"
        yield "[1,2,3]\r"


    with raises(ConnectionError):
        with test_server(handler=bad_content, methods=("post", "get"), port="random") as server:
            stream = cls("user", "passwd", *args, url=server.baseurl)
            for tweet in stream:
                pass


@parameterized(streamtypes)
def test_closed_connection(cls, args, kwargs):
    """Test error handling if server unexpectedly closes connection"""
    cnt = 1000
    def bad_content(request):
        for n in xrange(cnt):
            # what json we pass doesn't matter. It's not verifying the
            # strcuture, only checking that it's parsable
            yield "[1,2,3]\r"

    with raises(ConnectionError):
        with test_server(handler=bad_content, methods=("post", "get"), port="random") as server:
            stream = cls("foo", "bar", *args, url=server.baseurl)
            for tweet in stream:
                pass


@parameterized(streamtypes)
def test_bad_host(cls, args, kwargs):
    """Test behaviour if we can't connect to the host"""
    with raises(ConnectionError):
        stream = cls("username", "passwd", *args, url="http://wedfwecfghhreewerewads.foo")
        stream.next()


@parameterized(streamtypes)
def smoke_test_receive_tweets(cls, args, kwargs):
    """Receive 100k tweets and disconnect (slow)"""
    total = 100000

    def tweetsource(request):
        while True:
            yield single_tweet + "\n"

    with test_server(handler=tweetsource, methods=("post", "get"), port="random") as server:
        stream = cls("foo", "bar", *args, url=server.baseurl)
        for tweet in stream:
            if stream.count == total:
                break


@parameterized(streamtypes)
def test_keepalive(cls, args, kwargs):
    """Make sure we behave sanely when there are keepalive newlines in the
    data recevived from twitter"""
    def tweetsource(request):
        yield single_tweet+"\n"
        yield "\n"
        yield "\n"
        yield single_tweet+"\n"
        yield "\n"
        yield "\n"
        yield "\n"
        yield "\n"
        yield "\n"
        yield "\n"
        yield "\n"
        yield single_tweet+"\n"
        yield "\n"


    with test_server(handler=tweetsource, methods=("post", "get"), port="random") as server:
        stream = cls("foo", "bar", *args, url=server.baseurl)
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

    def tweetsource(request):
        yield single_tweet+"\n"
        time.sleep(2)
        # need to yield a bunch here so we're sure we'll return from the
        # blocking call in case the buffering bug is present.
        for n in xrange(100):
            yield single_tweet+"\n"


    with test_server(handler=tweetsource, methods=("post", "get"), port="random") as server:
        stream = cls("foo", "bar", *args, url=server.baseurl)
        start = time.time()
        stream.next()
        first = time.time()
        diff = first - start
        assert diff < 1, "Getting first tweet took more than a second!"

