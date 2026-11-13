"""Tests for local account handling and remember-me selection."""

from spotifyProject import auth


class TestPasswordHashing:
    def test_round_trip(self):
        stored = auth._hash_password("s3cret-pw")
        assert auth._verify_password("s3cret-pw", stored) is True

    def test_wrong_password_rejected(self):
        stored = auth._hash_password("s3cret-pw")
        assert auth._verify_password("wrong", stored) is False

    def test_hash_is_salted(self):
        assert auth._hash_password("same") != auth._hash_password("same")

    def test_hash_never_contains_plaintext(self):
        assert "hunter2" not in auth._hash_password("hunter2")

    def test_malformed_hash_is_rejected(self):
        for bad in ["", "not-a-hash", "pbkdf2_sha256$bad", "pbkdf2_sha256$1$zz$zz"]:
            assert auth._verify_password("x", bad) is False

    def test_unknown_algorithm_is_rejected(self):
        stored = auth._hash_password("pw").replace("pbkdf2_sha256", "pbkdf2_nope")
        assert auth._verify_password("pw", stored) is False


class TestAccounts:
    def test_register_and_login(self, user_data_dir):
        ok, _ = auth.register_user("alice", "pw")
        assert ok
        assert auth.login_user("alice", "pw") == (True, "Login successful.")
        assert auth.login_user("alice", "nope") == (False, "Incorrect password.")
        assert auth.login_user("bob", "pw")[0] is False

    def test_duplicate_username_rejected(self, user_data_dir):
        assert auth.register_user("alice", "pw")[0] is True
        ok, message = auth.register_user("alice", "other")
        assert ok is False
        assert "exists" in message

    def test_blank_username_rejected(self, user_data_dir):
        ok, _ = auth.register_user("   ", "pw")
        assert ok is False

    def test_playlist_round_trip(self, user_data_dir):
        auth.register_user("alice", "pw")
        uri = "spotify:playlist:0ZyG7KYBa5cT8oJua0V4jJ"
        assert auth.set_user_playlist("alice", uri) is True
        assert auth.get_user_playlist("alice") == uri

    def test_playlist_for_unknown_user(self, user_data_dir):
        assert auth.get_user_playlist("ghost") is None
        assert auth.set_user_playlist("ghost", "spotify:playlist:x") is False


class TestRememberMe:
    def test_no_remembered_user_by_default(self, user_data_dir):
        auth.register_user("alice", "pw")
        assert auth.get_remembered_user() is None

    def test_remembered_user_is_returned(self, user_data_dir):
        auth.register_user("alice", "pw")
        auth.set_remember_me("alice", True)
        assert auth.get_remembered_user() == "alice"

    def test_most_recent_login_wins(self, user_data_dir):
        """Regression: the first remembered account used to win regardless."""
        for name in ("alice", "bob"):
            auth.register_user(name, "pw")
        auth.set_remember_me("alice", True)
        auth.set_remember_me("bob", True)
        assert auth.get_remembered_user() == "bob"

        auth.set_remember_me("alice", True)  # alice logs in again, more recently
        assert auth.get_remembered_user() == "alice"

    def test_clearing_remember_me(self, user_data_dir):
        auth.register_user("alice", "pw")
        auth.set_remember_me("alice", True)
        auth.clear_remember_me("alice")
        assert auth.get_remembered_user() is None

    def test_legacy_last_logged_in_value_is_tolerated(self, user_data_dir):
        auth.register_user("alice", "pw")
        users = auth.load_users()
        users["alice"]["remember_me"] = True
        users["alice"]["last_logged_in"] = "alice"  # old format
        auth.save_users(users)
        assert auth.get_remembered_user() == "alice"
