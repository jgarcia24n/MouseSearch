import asyncio
import base64
import copy
import hashlib
import json
import logging
import re
import time
from datetime import date
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class HardcoverAPIError(Exception):
    pass


class AsyncTokenBucket:
    def __init__(self, limit: int, period_seconds: float):
        self.limit = max(1, int(limit))
        self.period_seconds = float(period_seconds)
        self.tokens = float(self.limit)
        self.updated_at = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self) -> float:
        waited_total = 0.0
        while True:
            async with self.lock:
                now = time.monotonic()
                elapsed = now - self.updated_at
                self.updated_at = now
                refill_rate = self.limit / self.period_seconds
                self.tokens = min(float(self.limit), self.tokens + elapsed * refill_rate)
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return waited_total
                wait_for = (1.0 - self.tokens) / refill_rate
            waited_total += wait_for
            await asyncio.sleep(wait_for)


class HardcoverRateController:
    def __init__(self, limit: int, period_seconds: float):
        self.limit = max(1, int(limit))
        self.period_seconds = float(period_seconds)
        self.bucket = AsyncTokenBucket(self.limit, self.period_seconds)
        self.cooldown_until = 0.0
        self.cooldown_lock = asyncio.Lock()

    async def acquire(self) -> float:
        waited_total = 0.0
        while True:
            async with self.cooldown_lock:
                wait_for = self.cooldown_until - time.monotonic()
            if wait_for > 0:
                waited_total += wait_for
                await asyncio.sleep(wait_for)
                continue

            waited_total += await self.bucket.acquire()

            async with self.cooldown_lock:
                wait_for = self.cooldown_until - time.monotonic()
            if wait_for <= 0:
                return waited_total

    async def note_rate_limited(self, attempt: int, retry_after: str | None = None) -> float:
        delay_seconds = self._retry_delay_seconds(attempt, retry_after)
        async with self.cooldown_lock:
            self.cooldown_until = max(self.cooldown_until, time.monotonic() + delay_seconds)
        return delay_seconds

    def _retry_delay_seconds(self, attempt: int, retry_after: str | None) -> float:
        if retry_after is not None:
            try:
                parsed = float(str(retry_after).strip())
            except (TypeError, ValueError):
                parsed = None
            if parsed is not None and parsed > 0:
                return parsed
        return min(15.0, 1.0 * (2 ** max(0, int(attempt))))


_HARDCOVER_RATE_CONTROLLERS: dict[str, HardcoverRateController] = {}


def get_hardcover_rate_controller(endpoint: str, authorization_header: str, limit: int) -> HardcoverRateController:
    scope = f"{str(endpoint or '').strip().lower()}:{hashlib.sha256(str(authorization_header or '').encode('utf-8')).hexdigest()}"
    controller = _HARDCOVER_RATE_CONTROLLERS.get(scope)
    if controller is None or controller.limit != max(1, int(limit)):
        controller = HardcoverRateController(limit, 60.0)
        _HARDCOVER_RATE_CONTROLLERS[scope] = controller
    return controller


def normalize_search_results(results: Any) -> list[dict[str, Any]]:
    if isinstance(results, dict):
        for key in ("hits", "results", "documents"):
            nested = results.get(key)
            if isinstance(nested, list):
                results = nested
                break
        else:
            results = [results]

    if not isinstance(results, list):
        return []

    normalized = []
    for item in results:
        candidate = item
        if isinstance(item, dict):
            if isinstance(item.get("document"), dict):
                candidate = item["document"]
            elif isinstance(item.get("book"), dict):
                candidate = item["book"]
            elif isinstance(item.get("series"), dict):
                candidate = item["series"]
            elif isinstance(item.get("author"), dict):
                candidate = item["author"]

        if isinstance(candidate, dict):
            normalized.append(candidate)
    return normalized


def graphql_operation_name(query: str) -> str:
    match = re.search(r"\b(query|mutation)\s+([A-Za-z0-9_]+)", str(query or ""))
    if match:
        return match.group(2)
    return "anonymous"


class HardcoverClient:
    BOOK_FIELDS = """
      id
      title
      subtitle
      description
      slug
      contributions(limit: 5) {
        author {
          name
          slug
        }
      }
      rating
      ratings_count
      reviews_count
      users_read_count
      users_count
      release_date
      release_year
      pages
      compilation
      image {
        url
      }
      featured_book_series {
        position
        series {
          id
          name
          slug
        }
      }
    """

    USER_BOOK_FIELDS = """
      user_books(
        where: {user_id: {_eq: $user_id}}
        order_by: {updated_at: desc}
        limit: 1
      ) {
        id
        book_id
        edition_id
        user_id
        status_id
        rating
        privacy_setting_id
        updated_at
        user_book_status {
          id
          status
        }
      }
    """

    SEARCH_QUERY = """
    query HardcoverSearch($query: String!, $query_type: String!, $per_page: Int!, $page: Int!) {
      search(query: $query, query_type: $query_type, per_page: $per_page, page: $page) {
        ids
        results
        query
        query_type
        page
        per_page
      }
    }
    """

    EDITION_BY_ISBN_13_QUERY = """
    query EditionByISBN13($isbn: String!) {
      editions(where: {isbn_13: {_eq: $isbn}}, limit: 1) {
        id
        title
        isbn_10
        isbn_13
        release_date
        book {
""" + BOOK_FIELDS + """
        }
      }
    }
    """

    EDITION_BY_ISBN_13_QUERY_WITH_USER = """
    query EditionByISBN13($isbn: String!, $user_id: Int!) {
      editions(where: {isbn_13: {_eq: $isbn}}, limit: 1) {
        id
        title
        isbn_10
        isbn_13
        release_date
        book {
""" + BOOK_FIELDS + USER_BOOK_FIELDS + """
        }
      }
    }
    """

    EDITION_BY_ISBN_10_QUERY = """
    query EditionByISBN10($isbn: String!) {
      editions(where: {isbn_10: {_eq: $isbn}}, limit: 1) {
        id
        title
        isbn_10
        isbn_13
        release_date
        book {
""" + BOOK_FIELDS + """
        }
      }
    }
    """

    EDITION_BY_ISBN_10_QUERY_WITH_USER = """
    query EditionByISBN10($isbn: String!, $user_id: Int!) {
      editions(where: {isbn_10: {_eq: $isbn}}, limit: 1) {
        id
        title
        isbn_10
        isbn_13
        release_date
        book {
""" + BOOK_FIELDS + USER_BOOK_FIELDS + """
        }
      }
    }
    """

    BOOK_DETAILS_QUERY = """
    query BookDetails($id: Int!) {
      books(where: {id: {_eq: $id}}, limit: 1) {
""" + BOOK_FIELDS + """
      }
    }
    """

    BOOK_DETAILS_QUERY_WITH_USER = """
    query BookDetails($id: Int!, $user_id: Int!) {
      books(where: {id: {_eq: $id}}, limit: 1) {
""" + BOOK_FIELDS + USER_BOOK_FIELDS + """
      }
    }
    """

    USER_BOOK_FOR_BOOK_QUERY = """
    query UserBookForBook($book_id: Int!, $user_id: Int!) {
      user_books(
        where: {
          book_id: {_eq: $book_id}
          user_id: {_eq: $user_id}
        }
        order_by: {updated_at: desc}
        limit: 1
      ) {
        id
        book_id
        edition_id
        user_id
        status_id
        rating
        privacy_setting_id
        updated_at
        user_book_status {
          id
          status
        }
      }
    }
    """

    SERIES_DETAILS_QUERY = """
    query SeriesDetails($id: Int!) {
      series(where: {id: {_eq: $id}}, limit: 1) {
        id
        name
        slug
        books_count
        author {
          name
          slug
        }
        book_series(
          distinct_on: position
          order_by: [{position: asc}, {book: {users_count: desc}}]
          where: {
            book: {canonical_id: {_is_null: true}}
            compilation: {_eq: false}
          }
        ) {
          position
          book {
            id
            slug
            title
            release_date
            release_year
            rating
            ratings_count
            users_read_count
            users_count
            image {
              url
            }
          }
        }
      }
    }
    """

    UPDATE_USER_BOOK_MUTATION = """
    mutation UpdateUserBook($id: Int!, $object: UserBookUpdateInput!) {
      updateResponse: update_user_book(id: $id, object: $object) {
        error
        userBook: user_book {
          id
          book_id
          edition_id
          user_id
          status_id
          rating
          privacy_setting_id
          updated_at
          user_book_status {
            id
            status
          }
        }
      }
    }
    """

    DELETE_USER_BOOK_MUTATION = """
    mutation DestroyUserBook($id: Int!) {
      deleteResponse: delete_user_book(id: $id) {
        id
        bookId: book_id
        userId: user_id
      }
    }
    """

    CREATE_USER_BOOK_MUTATION = """
    mutation CreateUserBook($object: UserBookCreateInput!) {
      createResponse: insert_user_book(object: $object) {
        error
        id
        userBook: user_book {
          id
          book_id
          edition_id
          user_id
          status_id
          rating
          privacy_setting_id
          updated_at
          user_book_status {
            id
            status
          }
        }
      }
    }
    """

    def __init__(
        self,
        token: str,
        *,
        endpoint: str = "https://api.hardcover.app/v1/graphql",
        user_agent: str = "MouseSearch Hardcover Enrichment",
        timeout_seconds: float = 30.0,
        rate_limit: int = 60,
    ):
        self.token = token
        self.endpoint = endpoint
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.rate_limit_per_minute = max(1, int(rate_limit))
        self.user_id = self._extract_user_id(token)
        self.rate_controller = get_hardcover_rate_controller(
            self.endpoint,
            self.authorization_header(),
            self.rate_limit_per_minute,
        )
        self._client: httpx.AsyncClient | None = None
        self._cache: dict[str, Any] = {}

    def authorization_header(self) -> str:
        token = str(self.token or "").strip()
        if token.lower().startswith("bearer "):
            return token
        return f"Bearer {token}"

    @staticmethod
    def _extract_user_id(token: str) -> int | None:
        raw = str(token or "").strip()
        if raw.lower().startswith("bearer "):
            raw = raw[7:].strip()
        parts = raw.split(".")
        if len(parts) < 2:
            return None

        payload_part = parts[1]
        payload_part += "=" * (-len(payload_part) % 4)
        try:
            payload = json.loads(base64.urlsafe_b64decode(payload_part.encode("utf-8")).decode("utf-8"))
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None

        candidates = [
            ((payload.get("user") or {}) if isinstance(payload.get("user"), dict) else {}).get("id"),
            payload.get("id"),
            payload.get("sub"),
            ((payload.get("https://hasura.io/jwt/claims") or {}) if isinstance(payload.get("https://hasura.io/jwt/claims"), dict) else {}).get("x-hasura-user-id"),
        ]
        for candidate in candidates:
            try:
                normalized = int(str(candidate).strip())
            except (TypeError, ValueError):
                continue
            if normalized > 0:
                return normalized
        return None

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()

    async def open(self) -> None:
        if self._client is not None:
            return
        headers = {
            "Authorization": self.authorization_header(),
            "Content-Type": "application/json",
            "User-Agent": self.user_agent,
        }
        self._client = httpx.AsyncClient(headers=headers, timeout=self.timeout_seconds)

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def graphql(
        self,
        query: str,
        variables: dict[str, Any],
        *,
        cache_key: str | None = None,
        retry_5xx: int = 2,
    ) -> dict[str, Any]:
        if cache_key and cache_key in self._cache:
            return copy.deepcopy(self._cache[cache_key])

        await self.open()
        assert self._client is not None
        operation_name = graphql_operation_name(query)

        retry_429 = 3
        attempt = 0
        while True:
            waited_for = await self.rate_controller.acquire()
            if waited_for >= 1.0:
                logger.warning(
                    "[HARDCOVER-RATE] Delayed request op=%s wait_s=%.3f cache_key=%s endpoint=%s",
                    operation_name,
                    waited_for,
                    cache_key or "",
                    self.endpoint,
                )
            try:
                response = await self._client.post(
                    self.endpoint,
                    json={"query": query, "variables": variables},
                )
            except httpx.TimeoutException as exc:
                raise HardcoverAPIError(f"timeout: {exc}") from exc
            except httpx.RequestError as exc:
                raise HardcoverAPIError(f"request_error: {exc}") from exc

            if response.status_code == 429 and attempt < retry_429:
                retry_after = response.headers.get("Retry-After")
                cooldown_seconds = await self.rate_controller.note_rate_limited(attempt, retry_after)
                logger.warning(
                    "[HARDCOVER-RATE] Received 429 op=%s attempt=%s retry_after=%s cooldown_s=%.3f endpoint=%s",
                    operation_name,
                    attempt + 1,
                    retry_after or "",
                    cooldown_seconds,
                    self.endpoint,
                )
                attempt += 1
                continue

            if 500 <= response.status_code <= 599 and attempt < retry_5xx:
                await asyncio.sleep(min(4.0, 0.5 * (2 ** attempt)))
                attempt += 1
                continue

            if response.status_code >= 400:
                raise HardcoverAPIError(f"http_{response.status_code}")

            payload = response.json()
            if payload.get("errors"):
                first = payload["errors"][0]
                message = first.get("message") if isinstance(first, dict) else str(first)
                raise HardcoverAPIError(f"graphql_error: {message}")

            data = payload.get("data") or {}
            if cache_key:
                self._cache[cache_key] = copy.deepcopy(data)
            return data

    async def search(self, query: str, query_type: str = "Book", per_page: int = 5) -> list[dict[str, Any]]:
        normalized_type = str(query_type or "Book").strip().title()
        normalized_query = str(query or "").strip()
        if not normalized_query:
            return []

        data = await self.graphql(
            self.SEARCH_QUERY,
            {
                "query": normalized_query,
                "query_type": normalized_type,
                "per_page": int(per_page),
                "page": 1,
            },
            cache_key=f"search:{normalized_type.lower()}:{normalized_query.lower()}:{int(per_page)}",
        )
        search_data = data.get("search") or {}
        return normalize_search_results(search_data.get("results") or [])

    async def edition_by_isbn(self, isbn: str) -> dict[str, Any] | None:
        isbn = str(isbn or "").strip().upper()
        if not isbn:
            return None
        if len(isbn) == 13:
            query = self.EDITION_BY_ISBN_13_QUERY_WITH_USER if self.user_id else self.EDITION_BY_ISBN_13_QUERY
        else:
            query = self.EDITION_BY_ISBN_10_QUERY_WITH_USER if self.user_id else self.EDITION_BY_ISBN_10_QUERY
        variables = {"isbn": isbn}
        if self.user_id:
            variables["user_id"] = self.user_id
        data = await self.graphql(
            query,
            variables,
            cache_key=f"edition:isbn:{isbn}",
        )
        editions = data.get("editions") or []
        if isinstance(editions, list) and editions:
            return editions[0]
        return None

    async def book_details(self, book_id: int, *, use_cache: bool = True) -> dict[str, Any] | None:
        try:
            normalized_id = int(book_id)
        except (TypeError, ValueError):
            return None
        if normalized_id <= 0:
            return None

        query = self.BOOK_DETAILS_QUERY_WITH_USER if self.user_id else self.BOOK_DETAILS_QUERY
        variables: dict[str, Any] = {"id": normalized_id}
        if self.user_id:
            variables["user_id"] = self.user_id
        data = await self.graphql(
            query,
            variables,
            cache_key=f"book:{normalized_id}" if use_cache else None,
        )
        books = data.get("books") or []
        if isinstance(books, list) and books:
            return books[0]
        return None

    async def user_book_for_book(self, book_id: int) -> dict[str, Any] | None:
        if not self.user_id:
            return None
        try:
            normalized_id = int(book_id)
        except (TypeError, ValueError):
            return None
        if normalized_id <= 0:
            return None

        data = await self.graphql(
            self.USER_BOOK_FOR_BOOK_QUERY,
            {"book_id": normalized_id, "user_id": self.user_id},
            cache_key=None,
        )
        user_books = data.get("user_books") or []
        if isinstance(user_books, list) and user_books:
            return user_books[0]
        return None

    async def update_user_book_status(
        self,
        user_book_id: int,
        status_id: int,
        *,
        edition_id: int | None = None,
        privacy_setting_id: int | None = None,
        rating: float | int | None = None,
        user_date: str | None = None,
    ) -> dict[str, Any] | None:
        try:
            normalized_user_book_id = int(user_book_id)
            normalized_status_id = int(status_id)
        except (TypeError, ValueError):
            return None
        if normalized_user_book_id <= 0 or normalized_status_id <= 0:
            return None

        payload = {
            "edition_id": int(edition_id) if edition_id not in (None, "") else None,
            "status_id": normalized_status_id,
            "rating": float(rating) if rating not in (None, "") else None,
            "privacy_setting_id": int(privacy_setting_id) if privacy_setting_id not in (None, "") else 1,
            "user_date": str(user_date or date.today().isoformat()),
        }

        data = await self.graphql(
            self.UPDATE_USER_BOOK_MUTATION,
            {"id": normalized_user_book_id, "object": payload},
            cache_key=None,
        )
        response = data.get("updateResponse") or {}
        error_message = str(response.get("error") or "").strip()
        if error_message:
            raise HardcoverAPIError(error_message)

        self._cache.clear()
        user_book = response.get("userBook")
        return user_book if isinstance(user_book, dict) else None

    async def delete_user_book(self, user_book_id: int) -> dict[str, Any] | None:
        try:
            normalized_user_book_id = int(user_book_id)
        except (TypeError, ValueError):
            return None
        if normalized_user_book_id <= 0:
            return None

        data = await self.graphql(
            self.DELETE_USER_BOOK_MUTATION,
            {"id": normalized_user_book_id},
            cache_key=None,
        )
        self._cache.clear()
        deleted_user_book = data.get("deleteResponse")
        return deleted_user_book if isinstance(deleted_user_book, dict) else None

    async def create_user_book(
        self,
        book_id: int,
        *,
        status_id: int | None = None,
        edition_id: int | None = None,
        privacy_setting_id: int | None = None,
        rating: float | int | None = None,
        user_date: str | None = None,
    ) -> dict[str, Any] | None:
        try:
            normalized_book_id = int(book_id)
        except (TypeError, ValueError):
            return None
        if normalized_book_id <= 0:
            return None

        normalized_status_id = None
        if status_id not in (None, ""):
            try:
                normalized_status_id = int(status_id)
            except (TypeError, ValueError):
                return None
            if normalized_status_id <= 0:
                return None

        payload = {
            "book_id": normalized_book_id,
            "edition_id": int(edition_id) if edition_id not in (None, "") else None,
            "status_id": normalized_status_id,
            "rating": float(rating) if rating not in (None, "") else None,
            "privacy_setting_id": int(privacy_setting_id) if privacy_setting_id not in (None, "") else 1,
            "user_date": str(user_date or date.today().isoformat()),
        }

        data = await self.graphql(
            self.CREATE_USER_BOOK_MUTATION,
            {"object": payload},
            cache_key=None,
        )
        response = data.get("createResponse") or {}
        error_message = str(response.get("error") or "").strip()
        if error_message:
            raise HardcoverAPIError(error_message)

        self._cache.clear()
        user_book = response.get("userBook")
        if isinstance(user_book, dict):
            return user_book

        inserted_id = response.get("id")
        if inserted_id:
            return await self.user_book_for_book(normalized_book_id)
        return None

    async def series_details(self, series_id: int) -> dict[str, Any] | None:
        try:
            normalized_id = int(series_id)
        except (TypeError, ValueError):
            return None
        if normalized_id <= 0:
            return None

        data = await self.graphql(
            self.SERIES_DETAILS_QUERY,
            {"id": normalized_id},
            cache_key=f"series:{normalized_id}",
        )
        series = data.get("series") or []
        if isinstance(series, list) and series:
            return series[0]
        return None
