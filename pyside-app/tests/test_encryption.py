"""Tests for AES-256-GCM encryption module."""
import json

import pytest

from app.encryption import (
    clear_session_password,
    decrypt_data,
    decrypt_file,
    encrypt_data,
    encrypt_file,
    get_session_password,
    hash_password,
    is_encrypted,
    read_json_file,
    set_session_password,
    verify_password_hash,
    write_json_file,
)


def test_encrypt_decrypt_roundtrip():
    text = '{"key": "value", "nested": {"x": 1}}'
    blob = encrypt_data(text, 'mypassword')
    assert isinstance(blob, bytes)
    assert blob[0:1] == b'\x01'
    result = decrypt_data(blob, 'mypassword')
    assert result == text


def test_wrong_password_raises():
    blob = encrypt_data('hello', 'correct')
    with pytest.raises(ValueError):
        decrypt_data(blob, 'wrong')


def test_unknown_version_raises():
    with pytest.raises(ValueError, match='Unknown encryption version'):
        decrypt_data(b'\x02' + b'\x00' * 40, 'pwd')


def test_encrypt_decrypt_file(tmp_path):
    p = tmp_path / 'test.json'
    p.write_text('{"a": 1}', encoding='utf-8')
    assert not is_encrypted(str(p))
    encrypt_file(str(p), 'pass123')
    assert is_encrypted(str(p))
    text = decrypt_file(str(p), 'pass123')
    assert json.loads(text) == {'a': 1}


def test_is_encrypted_missing_file():
    assert not is_encrypted('/nonexistent/path/file.json')


def test_read_write_json_encrypted(tmp_path):
    p = tmp_path / 'data.json'
    data = {'hello': 'world', 'num': 42}
    write_json_file(str(p), data, password='secret')
    assert is_encrypted(str(p))
    loaded = read_json_file(str(p), password='secret')
    assert loaded == data


def test_read_write_json_plain(tmp_path):
    p = tmp_path / 'data.json'
    data = {'plain': True}
    write_json_file(str(p), data)
    assert not is_encrypted(str(p))
    loaded = read_json_file(str(p))
    assert loaded == data


def test_read_json_file_missing_returns_empty(tmp_path):
    p = tmp_path / 'missing.json'
    assert read_json_file(str(p)) == {}


def test_read_encrypted_without_password_raises(tmp_path):
    p = tmp_path / 'enc.json'
    write_json_file(str(p), {'x': 1}, password='pwd')
    with pytest.raises(ValueError, match='encrypted but no password'):
        read_json_file(str(p), password=None)


def test_password_hash():
    h = hash_password('mypassword')
    assert verify_password_hash('mypassword', h)
    assert not verify_password_hash('wrong', h)


def test_session_password():
    set_session_password('test123')
    assert get_session_password() == 'test123'
    clear_session_password()
    assert get_session_password() is None


def test_encrypt_produces_different_blobs():
    """Each encryption call uses fresh random salt+nonce → unique output."""
    b1 = encrypt_data('same', 'pwd')
    b2 = encrypt_data('same', 'pwd')
    assert b1 != b2
    # But both decrypt to the same text
    assert decrypt_data(b1, 'pwd') == decrypt_data(b2, 'pwd') == 'same'
