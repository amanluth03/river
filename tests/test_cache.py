from benchmark.cache import Cache


def test_store_then_verify_hash(tmp_path):
    cache = Cache(tmp_path)
    digest = cache.store("1", "0001-26-000001", "doc.htm", b"hello")
    assert len(digest) == 64
    assert cache.has("1", "0001-26-000001", "doc.htm")
    assert cache.verify_hash("1", "0001-26-000001", "doc.htm")


def test_tampered_file_fails_hash_check(tmp_path):
    cache = Cache(tmp_path)
    cache.store("1", "0001-26-000001", "doc.htm", b"hello")
    cache.path("1", "0001-26-000001", "doc.htm").write_bytes(b"hellO")
    assert not cache.verify_hash("1", "0001-26-000001", "doc.htm")


def test_manifest_survives_a_new_cache_object(tmp_path):
    Cache(tmp_path).store("1", "0001-26-000001", "doc.htm", b"hello")
    assert Cache(tmp_path).sha256("1", "0001-26-000001", "doc.htm") is not None
