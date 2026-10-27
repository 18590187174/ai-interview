"""密码哈希：加盐慢哈希，相同明文产生不同哈希。"""

from __future__ import annotations

from app.services.password import dummy_verify, hash_password, verify_password


def test_same_password_produces_different_hashes():
    first = hash_password("Passw0rd1")
    second = hash_password("Passw0rd1")
    assert first != second
    assert first.startswith("$argon2")


def test_verify_correct_and_incorrect_password():
    hashed = hash_password("Passw0rd1")
    assert verify_password("Passw0rd1", hashed) is True
    assert verify_password("WrongPass1", hashed) is False


def test_verify_invalid_hash_returns_false():
    assert verify_password("Passw0rd1", "not-a-hash") is False


def test_dummy_verify_matches_real_verify_cost():
    """用户不存在时的校验耗效应与真实校验处于同一量级。"""
    import time

    hashed = hash_password("Passw0rd1")

    start = time.perf_counter()
    verify_password("Passw0rd1", hashed)
    real_duration = time.perf_counter() - start

    start = time.perf_counter()
    dummy_verify("Passw0rd1")
    dummy_duration = time.perf_counter() - start

    ratio = dummy_duration / real_duration if real_duration else 1
    assert 0.2 <= ratio <= 5, f"耗时差异过大：real={real_duration:.4f}s dummy={dummy_duration:.4f}s"
