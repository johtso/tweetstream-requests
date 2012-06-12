.. -*- restructuredtext -*-

##########################################
tweetstream - Simple twitter streaming API
##########################################

Introduction
------------

tweetstream provides two classes, SampleStream and FollowStream, that can be
used to get tweets from Twitter's streaming API. An instance of one of the
classes can be used as an iterator. In addition to fetching tweets, the 
object keeps track of the number of tweets collected and the rate at which
tweets are received.

SampleStream delivers a sample of all tweets. FilterStream delivers
tweets that match one or more criteria. Note that it's not possible
to get all tweets without access to the "firehose" stream, which
is not currently avaliable to the public.

Twitter's documentation about the streaming API can be found here:
http://dev.twitter.com/pages/streaming_api_methods .

**Note** that the API is blocking. If for some reason data is not immediatly
available, calls will block until enough data is available to yield a tweet.

Examples
--------

Printing incoming tweets:

>>> stream = tweetstream.SampleStream("username", "password")
>>> for tweet in stream:
...     print tweet


The stream object can also be used as a context, as in this example that
prints the author for each tweet as well as the tweet count and rate:

>>> with tweetstream.SampleStream("username", "password") as stream
...     for tweet in stream:
...         print "Got tweet from %-16s\t( tweet %d, rate %.1f tweets/sec)" % (
...                 tweet["user"]["screen_name"], stream.count, stream.rate )


Stream objects can raise ConnectionError or AuthenticationError exceptions:

>>> try:
...     with tweetstream.TweetStream("username", "password") as stream
...         for tweet in stream:
...             print "Got tweet from %-16s\t( tweet %d, rate %.1f tweets/sec)" % (
...                     tweet["user"]["screen_name"], stream.count, stream.rate )
... except tweetstream.ConnectionError, e:
...     print "Disconnected from twitter. Reason:", e.reason

To get tweets that match specific criteria, use the FilterStream. FilterStreams
take three keyword arguments: "locations", "follow" and "track".

Locations are a list of bounding boxes in which geotagged tweets should originate.
The argument should be an iterable of longitude/latitude pairs.

Track specifies keywords to track. The argument should be an iterable of
strings.

Follow returns statuses that reference given users. Argument should be an iterable
of twitter user IDs. The IDs are userid ints, not the screen names. 

>>> words = ["opera", "firefox", "safari"]
>>> people = [123,124,125]
>>> locations = ["-122.75,36.8", "-121.75,37.8"]
>>> with tweetstream.FilterStream("username", "password", track=words,
...                               follow=people, locations=locations) as stream
...     for tweet in stream:
...         print "Got interesting tweet:", tweet


Deprecated classes
------------------

tweetstream used to contain the classes TweetStream, FollowStream, TrackStream
LocationStream and ReconnectingTweetStream. These were deprecated when twitter
changed its API end points. The same functionality is now available in
SampleStream and FilterStream. The deprecated methods will emit a warning when
used, but will remain functional for a while longer.


Changelog
---------

See the CHANGELOG file

Contact
-------

The author is Rune Halvorsen <runefh@gmail.com>. The project resides at
http://bitbucket.org/runeh/tweetstream . If you find bugs, or have feature
requests, please report them in the project site issue tracker. Patches are
also very welcome.

Contributors
------------

- Rune Halvorsen
- Christopher Schierkolk
- Reid Priedhorsky
- Johannes

License
-------

This software is licensed under the ``New BSD License``. See the ``LICENCE``
file in the top distribution directory for the full license text.
