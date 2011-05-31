from .streamclasses import FilterStream

class DeprecatedStream(FilterStream):
    def __init__(self, *args, **kwargs):
        import warnings
        warnings.warn("%s is deprecated. Use FilterStream instead" % self.__class__.__name__, DeprecationWarning)
        super(DeprecatedStream, self).__init__(*args, **kwargs)


class FollowStream(DeprecatedStream):
    def __init__(self, username, password, follow, catchup=None, url=None):
        super(FollowStream, self).__init__(username, password, follow=follow, catchup=catchup, url=url)


class TrackStream(DeprecatedStream):
    def __init__(self, username, password, track, catchup=None, url=None):
        super(TrackStream, self).__init__(username, password, track=track, catchup=catchup, url=url)


class LocationStream(DeprecatedStream):
    def __init__(self, username, password, locations, catchup=None, url=None):
        super(LocationStream, self).__init__(username, password, locations=locations, catchup=catchup, url=url)
