from core.cache import make_list_cache_key, make_tree_cache_key


class TestMakeListCacheKey:

    def test_key_contains_ordering(self):
        key = make_list_cache_key(ordering = "-created_at", page = "1")
        assert "-created_at" in key

    def test_key_contains_page(self):
        key = make_list_cache_key(ordering = "-created_at", page = "3")
        assert "page=3" in key

    def test_key_format(self):
        key = make_list_cache_key(ordering = "username", page = "2")
        assert key == "comments:list:ordering=username:page=2"

    def test_different_params_produce_different_keys(self):
        key1 = make_list_cache_key(ordering = "-created_at", page = "1")
        key2 = make_list_cache_key(ordering = "-created_at", page = "2")
        assert key1 != key2


class TestMakeTreeCacheKey:

    def test_key_contains_root_id(self):
        root_id = "abc-123"
        assert root_id in make_tree_cache_key(root_id)

    def test_key_format(self):
        assert make_tree_cache_key("uuid-xyz") == "comments:tree:uuid-xyz"

    def test_different_ids_produce_different_keys(self):
        assert make_tree_cache_key("id-a") != make_tree_cache_key("id-b")
