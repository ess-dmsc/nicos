description = "setup for the cache server (smoke integration)"
group = "special"

devices = dict(
    DB=device(
        "nicos.services.cache.server.MemoryCacheDatabase",
        loglevel="info",
    ),
    Server=device(
        "nicos.services.cache.server.CacheServer",
        db="DB",
        server=configdata("config.CACHE_HOST"),
        loglevel="debug",
    ),
)
