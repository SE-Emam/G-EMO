"""Android Keystore-backed storage for provider credentials.

Secrets are encrypted with an AES-256-GCM key held by AndroidKeyStore.
Only the IV and ciphertext are stored in app-private SharedPreferences.
There is intentionally no plaintext-file fallback.
"""
from __future__ import annotations

import os
from typing import Protocol


class SecureStorageError(RuntimeError):
    """Secure storage is unavailable; callers must fail closed."""


class SecretStore(Protocol):
    def get(self, name: str) -> str: ...
    def set(self, name: str, value: str) -> None: ...
    def delete(self, name: str) -> None: ...


class AndroidKeystoreTokenStore:
    KEY_ALIAS = "com.emam.gemo.provider_tokens.aes256gcm.v1"
    PREFS_NAME = "g_emo_secure_tokens"
    _ALLOWED_NAMES = {"whatsapp_access_token", "whatsapp_webjs_token"}

    def __init__(self) -> None:
        try:
            from jnius import autoclass
            self._autoclass = autoclass
            self._activity = autoclass("org.kivy.android.PythonActivity").mActivity
            self._Context = autoclass("android.content.Context")
            self._KeyStore = autoclass("java.security.KeyStore")
            self._KeyGenerator = autoclass("javax.crypto.KeyGenerator")
            self._KeyGenParameterSpecBuilder = autoclass("android.security.keystore.KeyGenParameterSpec$Builder")
            self._KeyProperties = autoclass("android.security.keystore.KeyProperties")
            self._Cipher = autoclass("javax.crypto.Cipher")
            self._GCMParameterSpec = autoclass("javax.crypto.spec.GCMParameterSpec")
            self._JavaString = autoclass("java.lang.String")
            self._Base64 = autoclass("android.util.Base64")
            self._AndroidException = autoclass("java.lang.Exception")
            self._prefs = self._activity.getSharedPreferences(self.PREFS_NAME, self._Context.MODE_PRIVATE)
            self._ensure_key()
        except Exception as exc:
            raise SecureStorageError(
                "Android Keystore is unavailable; refusing to store credentials in plaintext"
            ) from exc

    def _ensure_key(self) -> None:
        store = self._KeyStore.getInstance("AndroidKeyStore")
        store.load(None)
        if store.containsAlias(self.KEY_ALIAS):
            return
        purposes = self._KeyProperties.PURPOSE_ENCRYPT | self._KeyProperties.PURPOSE_DECRYPT
        builder = self._KeyGenParameterSpecBuilder(self.KEY_ALIAS, purposes)
        builder.setBlockModes([self._KeyProperties.BLOCK_MODE_GCM])
        builder.setEncryptionPaddings([self._KeyProperties.ENCRYPTION_PADDING_NONE])
        builder.setKeySize(256)
        builder.setRandomizedEncryptionRequired(True)
        spec = builder.build()
        generator = self._KeyGenerator.getInstance("AES", "AndroidKeyStore")
        generator.init(spec)
        generator.generateKey()

    def _validate(self, name: str) -> None:
        if name not in self._ALLOWED_NAMES:
            raise SecureStorageError("Unsupported secret identifier")

    def _key(self):
        store = self._KeyStore.getInstance("AndroidKeyStore")
        store.load(None)
        key = store.getKey(self.KEY_ALIAS, None)
        if key is None:
            raise SecureStorageError("Android Keystore key is missing")
        return key

    def set(self, name: str, value: str) -> None:
        self._validate(name)
        if not isinstance(value, str):
            raise SecureStorageError("Credential must be text")
        if not value:
            self.delete(name)
            return
        try:
            cipher = self._Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(self._Cipher.ENCRYPT_MODE, self._key())
            plaintext = self._JavaString(value).getBytes("UTF-8")
            encrypted = cipher.doFinal(plaintext)
            iv_text = str(self._Base64.encodeToString(cipher.getIV(), self._Base64.NO_WRAP))
            cipher_text = str(self._Base64.encodeToString(encrypted, self._Base64.NO_WRAP))
            encoded = iv_text + "." + cipher_text
            editor = self._prefs.edit()
            editor.putString(name, encoded)
            if not editor.commit():
                raise SecureStorageError("Encrypted credential could not be committed")
        except SecureStorageError:
            raise
        except Exception as exc:
            raise SecureStorageError("Credential encryption failed; no plaintext fallback is allowed") from exc

    def get(self, name: str) -> str:
        self._validate(name)
        encoded = self._prefs.getString(name, None)
        if encoded is None:
            return ""
        try:
            iv_text, cipher_text = encoded.split(".", 1)
            iv = self._Base64.decode(iv_text, self._Base64.NO_WRAP)
            encrypted = self._Base64.decode(cipher_text, self._Base64.NO_WRAP)
            cipher = self._Cipher.getInstance("AES/GCM/NoPadding")
            key = self._key()
            spec = self._GCMParameterSpec(128, iv)
            cipher.init(self._Cipher.DECRYPT_MODE, key, spec)
            plaintext = cipher.doFinal(encrypted)
            return str(self._JavaString(plaintext, "UTF-8"))
        except Exception as exc:
            # Do not silently discard data or fall back to plaintext if key/data is invalid.
            raise SecureStorageError("Credential decryption failed; re-authentication is required") from exc


    def delete(self, name: str) -> None:
        self._validate(name)
        try:
            editor = self._prefs.edit()
            editor.remove(name)
            if not editor.commit():
                raise SecureStorageError("Credential could not be removed from encrypted storage")
        except SecureStorageError:
            raise
        except Exception as exc:
            raise SecureStorageError("Credential deletion failed") from exc


class EnvironmentSecretStore:
    """Read-only environment-backed secrets for controlled development/test use."""
    _ENV = {
        "whatsapp_access_token": "G_EMO_WHATSAPP_ACCESS_TOKEN",
        "whatsapp_webjs_token": "G_EMO_WHATSAPP_WEBJS_TOKEN",
    }

    def get(self, name: str) -> str:
        if name not in self._ENV:
            raise SecureStorageError("Unsupported secret identifier")
        return os.environ.get(self._ENV[name], "")

    def set(self, name: str, value: str) -> None:
        raise SecureStorageError("Environment secret store is read-only")

    def delete(self, name: str) -> None:
        raise SecureStorageError("Environment secret store is read-only")
