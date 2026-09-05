from promptrecipe.custody import FragmentContent
from promptrecipe.custody.cache import ContentCache
from promptrecipe.identity import FragmentId


def test_caches_and_returns_content_by_identity():
    cache = ContentCache()
    content = FragmentContent.of(b"Be concise.")
    cache.put(content)
    assert cache.get(content.id).data == content.data
    assert cache.stats == (1, 0)


def test_an_edited_fragment_never_hits_the_cache():
    """THE load-bearing test of this module.

    If someone re-keys this cache by path, this test fails — the point.
    """
    cache = ContentCache()
    before = FragmentContent.of(b"Be concise.")
    cache.put(before)

    after = FragmentContent.of(b"Be concise and cite sources.")
    assert before.id != after.id, "edited content must have a new identity"

    assert cache.get(after.id) is None, (
        "edited content must MISS the cache — a hit means the cache is keyed "
        "by something other than content, and stale text would be served "
        "after an edit, breaking FR-007 silently"
    )


def test_identical_content_at_two_paths_shares_one_entry():
    cache = ContentCache()
    cache.put(FragmentContent.of(b"shared safety rule"))
    cache.put(FragmentContent.of(b"shared safety rule"))
    assert len(cache) == 1


def test_a_miss_is_counted_and_returns_none():
    cache = ContentCache()
    assert cache.get(FragmentId.of(b"never inserted")) is None
    assert cache.stats == (0, 1)


def test_the_cache_is_keyed_by_fragment_id_not_by_path():
    cache = ContentCache()
    cache.put(FragmentContent.of(b"x"))
    assert all(isinstance(k, FragmentId) for k in cache.keys())
