"""提供 scrypt 密码哈希和 HS256 JWT 令牌实现。"""

import base64
import hashlib
import hmac
import json
import secrets
import time

from kb_manage_platform.common.errors import AuthenticationError


class ScryptPasswordHasher:
    """使用标准库 scrypt 计算密码哈希。"""

    # 作用：计算带随机盐的密码哈希。
    def hash(self, password: str) -> str:
        """返回 scrypt 哈希字符串。"""
        if len(password) < 8:
            raise ValueError("password must contain at least 8 characters")
        salt = secrets.token_bytes(16)
        derived = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64
        )
        return "scrypt$16384$8$1$%s$%s" % (
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(derived).decode("ascii"),
        )

    # 作用：校验明文密码和密码哈希。
    def verify(self, password: str, password_hash: str) -> bool:
        """返回密码是否匹配。"""
        try:
            algorithm, n, r, p, salt_text, digest_text = password_hash.split("$")
            if algorithm != "scrypt":
                return False
            salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
            expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
            actual = hashlib.scrypt(
                password.encode("utf-8"),
                salt=salt,
                n=int(n),
                r=int(r),
                p=int(p),
                dklen=len(expected),
            )
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            return False


class JwtTokenService:
    """使用标准库实现 HS256 JWT。"""

    # 作用：保存签名密钥和令牌有效期。
    def __init__(self, secret_key: str, expires_seconds: int, issuer: str = "kb-manage-platform") -> None:
        self._secret_key = secret_key.encode("utf-8")
        self._expires_seconds = expires_seconds
        self._issuer = issuer

    # 作用：签发访问令牌并返回过期秒数。
    def issue(self, user_id: str, permission_version: int) -> tuple[str, int]:
        """返回访问令牌和有效期。"""
        now = int(time.time())
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": user_id,
            "ver": permission_version,
            "iss": self._issuer,
            "iat": now,
            "exp": now + self._expires_seconds,
        }
        encoded_header = self._encode(header)
        encoded_payload = self._encode(payload)
        signature = self._sign(f"{encoded_header}.{encoded_payload}")
        return f"{encoded_header}.{encoded_payload}.{signature}", self._expires_seconds

    # 作用：解析并校验访问令牌。
    def parse(self, token: str) -> tuple[str, int]:
        """返回用户 ID 和令牌中的权限版本。"""
        try:
            header_text, payload_text, signature = token.split(".")
            expected = self._sign(f"{header_text}.{payload_text}")
            if not hmac.compare_digest(signature, expected):
                raise AuthenticationError("invalid token signature")
            header = self._decode(header_text)
            payload = self._decode(payload_text)
            if header.get("alg") != "HS256" or payload.get("iss") != self._issuer:
                raise AuthenticationError("invalid token")
            if int(payload.get("exp", 0)) < int(time.time()):
                raise AuthenticationError("token expired")
            return str(payload["sub"]), int(payload["ver"])
        except AuthenticationError:
            raise
        except Exception as exc:
            raise AuthenticationError("invalid token") from exc

    # 作用：编码 JWT 片段。
    @staticmethod
    def _encode(value: dict[str, object]) -> str:
        """返回 Base64URL 字符串。"""
        raw = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    # 作用：解码 JWT 片段。
    @staticmethod
    def _decode(value: str) -> dict[str, object]:
        """返回 JSON 对象。"""
        padding = "=" * (-len(value) % 4)
        raw = base64.urlsafe_b64decode((value + padding).encode("ascii"))
        return json.loads(raw.decode("utf-8"))

    # 作用：计算 HMAC-SHA256 签名。
    def _sign(self, value: str) -> str:
        """返回 Base64URL 签名。"""
        digest = hmac.new(self._secret_key, value.encode("ascii"), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
