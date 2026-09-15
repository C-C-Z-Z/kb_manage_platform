"""使用部署密钥对模型 API Key 进行加密和完整性校验。"""

import base64
import hashlib
import hmac
import os


class LocalSecretCipher:
    """无外部依赖的本地流式加密实现。"""

    def __init__(self, secret: str) -> None:
        self._key = hashlib.sha256(secret.encode("utf-8")).digest()

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        nonce = os.urandom(16)
        payload = plaintext.encode("utf-8")
        stream = self._stream(nonce, len(payload))
        encrypted = bytes(left ^ right for left, right in zip(payload, stream, strict=True))
        tag = hmac.new(self._key, nonce + encrypted, hashlib.sha256).digest()[:16]
        return base64.urlsafe_b64encode(nonce + tag + encrypted).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        raw = base64.urlsafe_b64decode(ciphertext.encode("ascii"))
        if len(raw) < 32:
            raise ValueError("invalid encrypted secret")
        nonce, tag, encrypted = raw[:16], raw[16:32], raw[32:]
        expected = hmac.new(self._key, nonce + encrypted, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(tag, expected):
            raise ValueError("encrypted secret integrity check failed")
        stream = self._stream(nonce, len(encrypted))
        return bytes(left ^ right for left, right in zip(encrypted, stream, strict=True)).decode("utf-8")

    def _stream(self, nonce: bytes, length: int) -> bytes:
        blocks: list[bytes] = []
        counter = 0
        while sum(len(block) for block in blocks) < length:
            blocks.append(
                hmac.new(self._key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
            )
            counter += 1
        return b"".join(blocks)[:length]

    @staticmethod
    def mask(plaintext: str) -> str:
        if not plaintext:
            return ""
        if len(plaintext) <= 8:
            return "*" * len(plaintext)
        return f"{plaintext[:4]}{'*' * (len(plaintext) - 8)}{plaintext[-4:]}"
