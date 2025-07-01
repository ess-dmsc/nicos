description = "setup for the cache server"
group = "special"

devices = dict(
    DB=device(
        "nicos.services.cache.server.FlatfileCacheDatabase",
        "nicos.services.cache.server.MemoryCacheDatabase",
        storepath="/opt/nicos-data/cache",
        loglevel="info",
    ),
    Server=device(
        "nicos.services.cache.server.CacheServer", db="DB", server="", loglevel="debug"
    ),
)
