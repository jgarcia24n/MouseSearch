import asyncio
import logging
import os
import re
from urllib.parse import urlsplit, urlunsplit

import qbittorrentapi
from qbittorrentapi.exceptions import (
    APIConnectionError,
    APIError,
    LoginFailed,
    UnsupportedMediaType415Error,
)

from .base import TorrentClient
from hashing import calculate_torrent_hash_from_bytes


logger = logging.getLogger(__name__)
INFO_HASH_RE = re.compile(r"\b[a-fA-F0-9]{40}\b")


def _normalize_base_url(url: str | None) -> str:
    raw_url = str(url or "").strip()
    if not raw_url:
        return ""

    try:
        parsed = urlsplit(raw_url)
    except ValueError:
        return raw_url

    path = (parsed.path or "").rstrip("/")
    if path.endswith("/api/v2"):
        path = path[:-7]

    normalized = urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))
    return normalized.rstrip("/")


def _sanitize_base_url(url: str | None) -> str:
    raw_url = str(url or "").strip()
    if not raw_url:
        return "<missing>"

    try:
        parsed = urlsplit(raw_url)
    except ValueError:
        return "<invalid-url>"

    hostname = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    if parsed.username or parsed.password:
        netloc = f"<redacted>@{hostname}{port}" if hostname else "<redacted>"
    else:
        netloc = parsed.netloc or hostname

    sanitized = urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))
    return sanitized or raw_url


class QBittorrentClient(TorrentClient):
    def __init__(self, config):
        super().__init__(config)
        self.base_url = _normalize_base_url(config.get("TORRENT_CLIENT_URL"))
        self.username = config.get("TORRENT_CLIENT_USERNAME")
        self.password = config.get("TORRENT_CLIENT_PASSWORD")
        self._last_error_message = ""
        self.force_start_on_add = str(os.getenv("QB_FORCE_START", "false")).strip().lower() in {
            "1", "true", "t", "yes", "y", "on"
        }
        self._client = self._build_client()
        self._client_lock = asyncio.Lock()

    @property
    def display_name(self) -> str:
        return "qBittorrent"

    def _build_client(self) -> qbittorrentapi.Client:
        extra_headers = {"Referer": self.base_url} if self.base_url else None
        return qbittorrentapi.Client(
            host=self.base_url,
            username=self.username,
            password=self.password,
            EXTRA_HEADERS=extra_headers,
            REQUESTS_ARGS={"timeout": (5, 30)},
            DISABLE_LOGGING_DEBUG_OUTPUT=True,
        )

    def _set_last_error(self, message: str | None):
        self._last_error_message = str(message or "").strip()

    def _clear_last_error(self):
        self._last_error_message = ""

    def _sync_session_cookies(self):
        session = getattr(self._client, "_http_session", None)
        if session is None:
            self.session_cookies = {}
            return
        self.session_cookies = dict(session.cookies)

    @staticmethod
    def _coerce_mapping(value) -> dict:
        if value is None:
            return {}
        return dict(value)

    @classmethod
    def _coerce_mapping_list(cls, value) -> list[dict]:
        if not value:
            return []
        return [cls._coerce_mapping(item) for item in value]

    def _extract_added_hash(self, response) -> str | None:
        def looks_like_hash(value) -> str | None:
            if not isinstance(value, str):
                return None
            match = INFO_HASH_RE.search(value.strip())
            return match.group(0).lower() if match else None

        if isinstance(response, dict):
            for key in ("hash", "infohash", "torrent_hash", "torrentHash"):
                extracted = looks_like_hash(response.get(key))
                if extracted:
                    return extracted
            for value in response.values():
                extracted = self._extract_added_hash(value)
                if extracted:
                    return extracted
            return None

        if isinstance(response, (list, tuple)):
            for item in response:
                extracted = self._extract_added_hash(item)
                if extracted:
                    return extracted
            return None

        return looks_like_hash(response)

    async def _call(self, method, *args, **kwargs):
        async with self._client_lock:
            result = await asyncio.to_thread(method, *args, **kwargs)
            self._sync_session_cookies()
            return result

    async def login(self) -> bool:
        if not all([self.base_url, self.username, self.password]):
            self._set_last_error("qBittorrent client URL, username, or password is missing")
            logger.warning(
                "qBittorrent login skipped due to missing configuration: url=%s username_present=%s password_present=%s",
                _sanitize_base_url(self.base_url),
                bool(self.username),
                bool(self.password),
            )
            return False

        sanitized_url = _sanitize_base_url(self.base_url)
        try:
            await self._call(self._client.auth_log_in, username=self.username, password=self.password)
            self._clear_last_error()
            return True
        except LoginFailed:
            self._set_last_error("Authentication failed")
            logger.warning("qBittorrent login rejected: url=%s", sanitized_url)
        except APIConnectionError as exc:
            self._set_last_error(f"Request error communicating with qBittorrent: {exc}")
            logger.error(
                "qBittorrent login request error: url=%s status=%s error=%s",
                sanitized_url,
                "n/a",
                str(exc),
            )
        except Exception as exc:
            self._set_last_error(f"Unexpected qBittorrent login error: {exc}")
            logger.error(
                "qBittorrent login unexpected error: url=%s status=%s error=%s",
                sanitized_url,
                "n/a",
                str(exc),
            )
        return False

    async def get_files(self, hash_val: str) -> list:
        try:
            files = await self._call(self._client.torrents_files, torrent_hash=hash_val)
            return self._coerce_mapping_list(files)
        except APIError:
            return []

    async def get_status(self) -> dict:
        sanitized_url = _sanitize_base_url(self.base_url)
        try:
            version = await self._call(self._client.app_version)
            self._clear_last_error()
            return {
                "status": "success",
                "message": f"{self.display_name} is connected.",
                "version": version,
                "display_name": self.display_name,
            }
        except LoginFailed:
            self._set_last_error("Authentication failed")
            logger.warning("qBittorrent status check unauthorized: url=%s", sanitized_url)
            return {
                "status": "error",
                "message": self._last_error_message or "Authentication failed",
                "display_name": self.display_name,
            }
        except (APIConnectionError, APIError, Exception) as exc:
            self._set_last_error(f"Failed to connect: {exc}")
            logger.error(
                "qBittorrent status check failed: url=%s status=%s error=%s",
                sanitized_url,
                "n/a",
                str(exc),
            )
            return {
                "status": "error",
                "message": f"Failed to connect: {exc}",
                "display_name": self.display_name,
            }

    async def get_categories(self) -> dict:
        try:
            categories = await self._call(self._client.torrents_categories)
            return self._coerce_mapping(categories)
        except APIError:
            return {}

    async def add_torrent(self, torrent_url: str, category: str, is_auto_organize: bool = False, **kwargs) -> dict:
        torrent_data = kwargs.get("torrent_data")
        torrent_filename = kwargs.get("torrent_filename") or "download.torrent"
        added_hash = calculate_torrent_hash_from_bytes(torrent_data) if torrent_data is not None else None

        add_kwargs = {}
        if category:
            add_kwargs["category"] = category

        if torrent_data is not None:
            add_kwargs["torrent_files"] = {torrent_filename: torrent_data}
        else:
            add_kwargs["urls"] = torrent_url

        try:
            response = await self._call(self._client.torrents_add, **add_kwargs)
            response_hash = self._extract_added_hash(response)

            if isinstance(response, str):
                if response not in {"", "Ok."}:
                    return {"status": "error", "message": response or "Unknown error"}
            elif response is not None and not isinstance(response, dict):
                return {"status": "error", "message": str(response) or "Unknown error"}

            message = "Torrent added successfully"
            effective_hash = added_hash or response_hash
            if self.force_start_on_add and effective_hash:
                await self._call(
                    self._client.torrents_set_force_start,
                    enable=True,
                    torrent_hashes=effective_hash,
                )
            elif self.force_start_on_add and not effective_hash:
                message = "Torrent added successfully (force start skipped: hash unavailable)"

            result = {"status": "success", "message": message}
            if effective_hash:
                result["hash"] = effective_hash
            return result
        except UnsupportedMediaType415Error:
            return {"status": "error", "message": "Invalid torrent file (HTTP 415 from qBittorrent)"}
        except (APIConnectionError, APIError) as exc:
            return {"status": "error", "message": f"Failed to communicate with qBittorrent: {exc}"}

    async def get_torrent_info(self, hash_val: str) -> dict:
        try:
            data = await self._call(self._client.torrents_info, torrent_hashes=hash_val)
            if data:
                return self.normalize_torrent_info(self._coerce_mapping(data[0]))
            return None
        except APIError:
            return None

    async def get_torrent_info_batch(self, hash_list: list) -> dict:
        try:
            torrent_list = await self._call(self._client.torrents_info, torrent_hashes=hash_list)
            torrents_by_hash = {
                str(torrent.get("hash") or "").strip().lower(): torrent
                for torrent in self._coerce_mapping_list(torrent_list)
                if torrent.get("hash")
            }
            return {"torrents": self.normalize_torrent_info_map(torrents_by_hash)}
        except APIError as exc:
            return {"error": f"Failed to fetch batch torrent info: {exc}"}

    async def get_api_version(self) -> str:
        try:
            return await self._call(self._client.app_web_api_version)
        except APIError:
            return "v2"

    async def get_torrents_with_metadata(self) -> list:
        try:
            torrents = await self._call(self._client.torrents_info)
            return self.normalize_torrent_metadata_list(self._coerce_mapping_list(torrents))
        except APIError:
            return []
