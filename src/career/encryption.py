import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from core.settings import Settings, get_settings


class LocalEncryptor:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.fernet = Fernet(self._resolve_key())

    def encrypt(self, value: str) -> str:
        return self.fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str) -> str:
        try:
            return self.fernet.decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            raise ValueError("本地敏感数据解密失败，请检查 APP_ENCRYPTION_KEY。") from exc

    def _resolve_key(self) -> bytes:
        configured = self.settings.app_encryption_key.strip()
        if configured:
            return configured.encode("ascii")
        key_path = Path(self.settings.encryption_key_path)
        key_path.parent.mkdir(parents=True, exist_ok=True)
        if not key_path.exists():
            key_path.write_bytes(Fernet.generate_key())
            os.chmod(key_path, 0o600)
        return key_path.read_bytes().strip()
