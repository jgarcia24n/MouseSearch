OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "MouseSearch API",
        "description": (
            "REST API for MouseSearch — a self-hosted MAM search and torrent management tool.\n\n"
            "## Authentication\n\n"
            "Two methods are supported:\n\n"
            "**HTTP Basic Auth** (recommended for API/curl clients) — use the admin credentials "
            "configured via `AUTH_USERNAME` / `AUTH_PASSWORD` environment variables.\n\n"
            "**Session Cookie** — POST to `/login` with form data; the response sets a `session` "
            "cookie that is sent automatically by browsers.\n\n"
            "## Permissions\n\n"
            "| Permission | Description |\n"
            "|---|---|\n"
            "| `can_search` | Search MAM and view results |\n"
            "| `can_download` | Add torrents to the client |\n"
            "| `can_settings` | View and modify application settings |\n"
            "| `is_admin` | Full access including user management |\n\n"
            "## Content Negotiation\n\n"
            "Routes that render HTML pages also return JSON when the request includes "
            "`Accept: application/json`. All dedicated `/api/*` routes always return JSON."
        ),
        "version": "1.0.0",
        "contact": {"name": "MouseSearch"},
    },
    "servers": [{"url": "/", "description": "Current server"}],
    "security": [{"basicAuth": []}, {"cookieAuth": []}],
    "tags": [
        {"name": "Authentication", "description": "Login, logout, and account self-service"},
        {"name": "Search", "description": "MAM search and autocomplete — requires `can_search`"},
        {"name": "MAM", "description": "MAM user data and marketplace operations"},
        {"name": "Torrent Client", "description": "Torrent management — write ops require `can_download`"},
        {"name": "File Organization", "description": "Move/copy completed torrents into destination folders"},
        {"name": "Hardcover", "description": "Book metadata enrichment via the Hardcover API"},
        {"name": "Settings", "description": "App configuration — writes require `can_settings`"},
        {"name": "Admin", "description": "User management — requires `is_admin`"},
        {"name": "System", "description": "Utilities: public IP, SSE stream, thumbnail proxy"},
    ],
    "components": {
        "securitySchemes": {
            "basicAuth": {
                "type": "http",
                "scheme": "basic",
                "description": "Admin credentials (AUTH_USERNAME / AUTH_PASSWORD env vars).",
            },
            "cookieAuth": {
                "type": "apiKey",
                "in": "cookie",
                "name": "session",
                "description": "Session cookie set by POST /login.",
            },
        },
        "schemas": {
            "Error": {
                "type": "object",
                "properties": {"error": {"type": "string"}},
                "required": ["error"],
            },
            "StatusResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["success", "error", "partial"]},
                    "message": {"type": "string"},
                },
                "required": ["status"],
            },
            "SearchResult": {
                "type": "object",
                "description": "A single MAM torrent search result.",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "author": {"type": "string"},
                    "torrent_url": {"type": "string"},
                    "download_link": {"type": "string"},
                    "size": {"type": "string", "example": "1.2 GiB"},
                    "seeders": {"type": "integer"},
                    "leechers": {"type": "integer"},
                    "free": {"type": "integer", "description": "1 = public freeleech"},
                    "personal_freeleech": {"type": "integer"},
                    "main_cat": {"type": "string"},
                    "category": {"type": "string"},
                    "categories": {
                        "type": "object",
                        "description": "Nested category data parsed from MAM",
                    },
                    "mediainfo": {
                        "type": "object",
                        "description": "Media-specific metadata (format, codec, etc.)",
                    },
                    "ownership": {
                        "type": "object",
                        "description": "Ownership/freeleech flags",
                    },
                    "series_info": {
                        "type": "object",
                        "description": "Series membership info",
                    },
                },
            },
            "AutosuggestItem": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["title", "author", "series", "narrator"],
                    },
                    "text": {"type": "string"},
                    "id": {"type": "string"},
                    "thumbnail": {"type": "string", "format": "uri"},
                },
            },
            "TorrentInfo": {
                "type": "object",
                "description": "Torrent status from the connected torrent client.",
                "properties": {
                    "hash": {"type": "string"},
                    "name": {"type": "string"},
                    "state": {"type": "string"},
                    "progress": {"type": "number", "format": "float", "minimum": 0, "maximum": 1},
                    "size": {"type": "integer", "description": "Total size in bytes"},
                    "save_path": {"type": "string"},
                },
            },
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "username": {"type": "string"},
                    "is_admin": {"type": "boolean"},
                    "can_search": {"type": "boolean"},
                    "can_download": {"type": "boolean"},
                    "can_settings": {"type": "boolean"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"},
                },
            },
        },
        "responses": {
            "Unauthorized": {
                "description": "Authentication required.",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Error"},
                        "example": {"error": "Unauthorized"},
                    }
                },
            },
            "Forbidden": {
                "description": "Authenticated but lacking required permission.",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Error"},
                        "example": {"error": "Permission denied"},
                    }
                },
            },
        },
    },
    "paths": {
        # ── Authentication ────────────────────────────────────────────────────
        "/login": {
            "post": {
                "tags": ["Authentication"],
                "summary": "Log in and obtain a session cookie",
                "description": (
                    "Authenticates using form data. On success, sets a `session` cookie and "
                    "redirects to `/` (or the `?next=` URL). Supports both env-admin and "
                    "database users."
                ),
                "security": [],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/x-www-form-urlencoded": {
                            "schema": {
                                "type": "object",
                                "required": ["username", "password"],
                                "properties": {
                                    "username": {"type": "string"},
                                    "password": {"type": "string", "format": "password"},
                                },
                            }
                        }
                    },
                },
                "parameters": [
                    {
                        "name": "next",
                        "in": "query",
                        "schema": {"type": "string"},
                        "description": "URL to redirect to after successful login.",
                    }
                ],
                "responses": {
                    "302": {"description": "Login successful — redirects to `/` or `?next=`."},
                    "401": {"description": "Invalid username or password (renders login page with error)."},
                },
            },
        },
        "/logout": {
            "get": {
                "tags": ["Authentication"],
                "summary": "Log out and clear session",
                "responses": {
                    "302": {"description": "Session cleared — redirects to `/login`."},
                },
            },
        },
        "/account": {
            "post": {
                "tags": ["Authentication"],
                "summary": "Change your own password",
                "description": "Available to database-managed users only (not the env-admin account).",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/x-www-form-urlencoded": {
                            "schema": {
                                "type": "object",
                                "required": ["current_password", "new_password"],
                                "properties": {
                                    "current_password": {"type": "string", "format": "password"},
                                    "new_password": {"type": "string", "format": "password"},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {"description": "Password changed successfully."},
                    "400": {"description": "Validation error (wrong current password, etc.)."},
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        # ── Search ────────────────────────────────────────────────────────────
        "/mam/search": {
            "get": {
                "tags": ["Search"],
                "summary": "Search MAM",
                "description": (
                    "Searches MyAnonamouse. Send `Accept: application/json` to receive a JSON "
                    "payload; omit it (or send `Accept: text/html`) for an HTML partial suitable "
                    "for HTMX. Requires `can_search` permission."
                ),
                "parameters": [
                    {"name": "query", "in": "query", "schema": {"type": "string"}, "description": "Free-text search query."},
                    {
                        "name": "searchType",
                        "in": "query",
                        "schema": {"type": "string", "default": "all"},
                        "description": "MAM search type (all, fl, vip, …).",
                    },
                    {"name": "search_in_title", "in": "query", "schema": {"type": "boolean", "default": True}},
                    {"name": "search_in_author", "in": "query", "schema": {"type": "boolean", "default": True}},
                    {"name": "search_in_series", "in": "query", "schema": {"type": "boolean", "default": True}},
                    {"name": "search_in_narrator", "in": "query", "schema": {"type": "boolean", "default": False}},
                    {
                        "name": "language",
                        "in": "query",
                        "schema": {"type": "string", "default": "English"},
                        "description": "Language name (e.g. `English`) or numeric MAM language ID.",
                    },
                    {
                        "name": "main_cat",
                        "in": "query",
                        "schema": {"type": "array", "items": {"type": "string"}},
                        "style": "form",
                        "explode": True,
                        "description": "Category filter(s). Omit or pass `all` for no filter.",
                    },
                    {"name": "search_scope", "in": "query", "schema": {"type": "string"}, "description": "MAM browse-scope flag."},
                    {"name": "flags_mode", "in": "query", "schema": {"type": "string", "default": "0"}, "description": "Browse-flags hide/show mode."},
                    {"name": "start_date", "in": "query", "schema": {"type": "string", "format": "date"}, "description": "Filter by upload date ≥ this date."},
                    {"name": "end_date", "in": "query", "schema": {"type": "string", "format": "date"}, "description": "Filter by upload date ≤ this date."},
                    {"name": "min_size", "in": "query", "schema": {"type": "number"}, "description": "Minimum torrent size (use with `size_unit`)."},
                    {"name": "max_size", "in": "query", "schema": {"type": "number"}, "description": "Maximum torrent size (use with `size_unit`)."},
                    {
                        "name": "size_unit",
                        "in": "query",
                        "schema": {"type": "string", "enum": ["KiB", "MiB", "GiB"]},
                        "description": "Unit for `min_size` / `max_size`.",
                    },
                ],
                "responses": {
                    "200": {
                        "description": "Search results (JSON when `Accept: application/json`).",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "results": {
                                            "type": "array",
                                            "items": {"$ref": "#/components/schemas/SearchResult"},
                                        },
                                        "search_id": {"type": "string"},
                                        "total": {"type": "integer"},
                                    },
                                }
                            }
                        },
                    },
                    "400": {
                        "description": "Bad request (invalid params or MAM error).",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                    "403": {"$ref": "#/components/responses/Forbidden"},
                },
            },
        },
        "/mam/autosuggest": {
            "get": {
                "tags": ["Search"],
                "summary": "Autocomplete / autosuggest",
                "description": "Returns title, author, series, and narrator suggestions. The query must be at least 3 characters.",
                "parameters": [
                    {
                        "name": "q",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string", "minLength": 3},
                        "description": "Search prefix (minimum 3 characters).",
                    },
                    {"name": "language", "in": "query", "schema": {"type": "string", "default": "English"}},
                    {"name": "search_in_title", "in": "query", "schema": {"type": "boolean", "default": True}},
                    {"name": "search_in_author", "in": "query", "schema": {"type": "boolean", "default": True}},
                    {"name": "search_in_series", "in": "query", "schema": {"type": "boolean", "default": True}},
                    {"name": "search_in_narrator", "in": "query", "schema": {"type": "boolean", "default": False}},
                    {
                        "name": "main_cat",
                        "in": "query",
                        "schema": {"type": "array", "items": {"type": "string"}},
                        "style": "form",
                        "explode": True,
                    },
                    {
                        "name": "cache_only",
                        "in": "query",
                        "schema": {"type": "boolean", "default": False},
                        "description": "Return cached results only; skip upstream MAM call.",
                    },
                ],
                "responses": {
                    "200": {
                        "description": "Suggestion list.",
                        "headers": {
                            "X-Autosuggest-Cache": {
                                "schema": {"type": "string", "enum": ["hit", "miss"]},
                                "description": "Whether the response came from the local cache.",
                            }
                        },
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/AutosuggestItem"},
                                }
                            }
                        },
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        # ── MAM ───────────────────────────────────────────────────────────────
        "/mam/status": {
            "get": {
                "tags": ["MAM"],
                "summary": "Get MAM user status",
                "description": "Returns the current user's MAM status: ratio, upload/download totals, buffer, VIP status, bonus points, etc.",
                "responses": {
                    "200": {
                        "description": "MAM user status object.",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                    "502": {"description": "MAM API unreachable.", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                },
            },
        },
        "/mam/user_data": {
            "get": {
                "tags": ["MAM"],
                "summary": "Get MAM user data",
                "responses": {
                    "200": {"description": "User data from MAM.", "content": {"application/json": {"schema": {"type": "object"}}}},
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        "/mam/buy_vip": {
            "post": {
                "tags": ["MAM"],
                "summary": "Purchase a VIP credit",
                "responses": {
                    "200": {"description": "Purchase result.", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/StatusResponse"}}}},
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        "/mam/buy_upload": {
            "post": {
                "tags": ["MAM"],
                "summary": "Purchase upload credit",
                "responses": {
                    "200": {"description": "Purchase result.", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/StatusResponse"}}}},
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        "/mam/buy_wedge": {
            "post": {
                "tags": ["MAM"],
                "summary": "Purchase bonus points (wedge)",
                "responses": {
                    "200": {"description": "Purchase result.", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/StatusResponse"}}}},
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        # ── Torrent Client ────────────────────────────────────────────────────
        "/client/status": {
            "get": {
                "tags": ["Torrent Client"],
                "summary": "Get torrent client connection status",
                "responses": {
                    "200": {
                        "description": "Client connectivity status.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {
                                            "type": "string",
                                            "enum": ["CONNECTED", "NOT CONNECTED", "ERROR"],
                                        },
                                        "message": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        "/client/categories": {
            "get": {
                "tags": ["Torrent Client"],
                "summary": "List torrent client categories",
                "responses": {
                    "200": {
                        "description": "Category list.",
                        "content": {
                            "application/json": {
                                "schema": {"type": "array", "items": {"type": "string"}},
                            }
                        },
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        "/client/add": {
            "post": {
                "tags": ["Torrent Client"],
                "summary": "Add a torrent to the client",
                "description": (
                    "Requires `can_download` permission. Performs a buffer check before adding. "
                    "Supports personal freeleech, custom save paths, and triggers auto-organization "
                    "when enabled."
                ),
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["torrent_url"],
                                "properties": {
                                    "torrent_url": {"type": "string", "description": "MAM torrent download URL."},
                                    "author": {"type": "string"},
                                    "title": {"type": "string"},
                                    "id": {"type": "string", "description": "MAM torrent/metadata ID."},
                                    "category": {"type": "string", "description": "Torrent client category. Defaults to configured default."},
                                    "size": {"type": "string", "example": "1.5 GiB", "description": "Human-readable torrent size."},
                                    "free": {"type": "integer", "enum": [0, 1], "description": "1 = public freeleech."},
                                    "personal_freeleech": {"type": "integer", "enum": [0, 1]},
                                    "use_personal_freeleech": {"type": "boolean", "description": "Request personal freeleech via download URL."},
                                    "series_info": {"type": "object"},
                                    "main_cat": {"type": "string"},
                                    "download_link": {"type": "string"},
                                    "custom_relative_path": {
                                        "type": "string",
                                        "description": "Override the relative path template for the save location.",
                                    },
                                    "custom_destination_path": {
                                        "type": "string",
                                        "description": "Override the base destination path.",
                                    },
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Torrent added successfully.",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/StatusResponse"}}},
                    },
                    "402": {
                        "description": "Insufficient buffer.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "error": {"type": "string"},
                                        "recommended_upload_credit": {"type": "number"},
                                    },
                                }
                            }
                        },
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                    "403": {"$ref": "#/components/responses/Forbidden"},
                    "500": {
                        "description": "Client not initialized.",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
                    },
                },
            },
        },
        "/client/info/{hash_val}": {
            "get": {
                "tags": ["Torrent Client"],
                "summary": "Get torrent info by hash",
                "parameters": [
                    {
                        "name": "hash_val",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": "Torrent info-hash.",
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Torrent info.",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/TorrentInfo"}}},
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                    "404": {"description": "Torrent not found in client."},
                },
            },
        },
        "/client/info/batch": {
            "post": {
                "tags": ["Torrent Client"],
                "summary": "Get info for multiple torrents",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["hashes"],
                                "properties": {
                                    "hashes": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "List of torrent info-hashes.",
                                    }
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Map of hash → torrent info.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "additionalProperties": {"$ref": "#/components/schemas/TorrentInfo"},
                                }
                            }
                        },
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        "/client/resolve_mid": {
            "post": {
                "tags": ["Torrent Client"],
                "summary": "Resolve a MAM metadata ID to a torrent hash",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["mid"],
                                "properties": {
                                    "mid": {"type": "string", "description": "MAM metadata ID."}
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Resolved hash.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "hash": {"type": "string"},
                                        "mid": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                    "404": {"description": "MID not found in local database."},
                },
            },
        },
        "/calculate_hash": {
            "post": {
                "tags": ["Torrent Client"],
                "summary": "Calculate torrent hash from a URL",
                "description": "Downloads the .torrent file and computes its info-hash.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["url"],
                                "properties": {
                                    "url": {"type": "string", "format": "uri", "description": "Torrent file URL."}
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Computed hash.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"hash": {"type": "string"}},
                                }
                            }
                        },
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        # ── File Organization ─────────────────────────────────────────────────
        "/organize": {
            "post": {
                "tags": ["File Organization"],
                "summary": "Organize all pending torrents",
                "description": "Moves or copies every torrent with `status=pending` in the local database into its configured destination folder.",
                "responses": {
                    "200": {
                        "description": "All organized successfully.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "results": {
                                            "type": "object",
                                            "properties": {
                                                "succeeded": {"type": "integer"},
                                                "failed": {"type": "integer"},
                                                "errors": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {
                                                            "hash": {"type": "string"},
                                                            "message": {"type": "string"},
                                                        },
                                                    },
                                                },
                                            },
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "207": {"description": "Partial success — some torrents organized, some failed."},
                    "500": {"description": "All torrents failed to organize."},
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        "/organize/{hash_val}": {
            "post": {
                "tags": ["File Organization"],
                "summary": "Organize a specific torrent",
                "parameters": [
                    {
                        "name": "hash_val",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": "Torrent info-hash.",
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Organized successfully.",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/StatusResponse"}}},
                    },
                    "500": {
                        "description": "Organization failed.",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/StatusResponse"}}},
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        # ── Hardcover ─────────────────────────────────────────────────────────
        "/hardcover/enrichment/{search_id}": {
            "get": {
                "tags": ["Hardcover"],
                "summary": "Get enrichment batch status",
                "description": "Returns the current state of a Hardcover enrichment batch for a search session.",
                "parameters": [
                    {"name": "search_id", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "responses": {
                    "200": {
                        "description": "Batch state object.",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        "/hardcover/enrichment/{search_id}/queue": {
            "post": {
                "tags": ["Hardcover"],
                "summary": "Queue an enrichment task for a search batch",
                "parameters": [
                    {"name": "search_id", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "responses": {
                    "202": {
                        "description": "Task queued.",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/StatusResponse"}}},
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        "/hardcover/series/{series_id}": {
            "get": {
                "tags": ["Hardcover"],
                "summary": "Fetch series details",
                "parameters": [
                    {"name": "series_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                ],
                "responses": {
                    "200": {
                        "description": "Series metadata from Hardcover.",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                    "404": {"description": "Series not found."},
                },
            },
        },
        "/hardcover/user-book/{book_id}": {
            "get": {
                "tags": ["Hardcover"],
                "summary": "Get the user's reading status for a book",
                "parameters": [
                    {"name": "book_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                ],
                "responses": {
                    "200": {
                        "description": "User-book status from Hardcover.",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        "/hardcover/user-book/status": {
            "post": {
                "tags": ["Hardcover"],
                "summary": "Update reading status for a book",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["book_id", "status"],
                                "properties": {
                                    "book_id": {"type": "integer"},
                                    "status": {
                                        "type": "string",
                                        "example": "read",
                                        "description": "Hardcover reading status slug.",
                                    },
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Status updated.",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/StatusResponse"}}},
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        # ── Settings ──────────────────────────────────────────────────────────
        "/api/settings": {
            "get": {
                "tags": ["Settings"],
                "summary": "Get path template settings",
                "responses": {
                    "200": {
                        "description": "Current path template settings.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "DEFAULT_RELATIVE_PATH_TEMPLATE": {"type": "string"},
                                        "REL_PATH_TEMPLATE": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
            "post": {
                "tags": ["Settings"],
                "summary": "Update default path template",
                "description": "Requires `can_settings` permission. Updates `DEFAULT_RELATIVE_PATH_TEMPLATE` in both the env file and `config.json`.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["DEFAULT_RELATIVE_PATH_TEMPLATE"],
                                "properties": {
                                    "DEFAULT_RELATIVE_PATH_TEMPLATE": {
                                        "type": "string",
                                        "example": "{author}/{title}",
                                    }
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Template updated.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "DEFAULT_RELATIVE_PATH_TEMPLATE": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "400": {
                        "description": "Missing required field.",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                    "403": {"$ref": "#/components/responses/Forbidden"},
                },
            },
        },
        "/api/settings/test-torrent-client": {
            "post": {
                "tags": ["Settings"],
                "summary": "Test torrent client connectivity",
                "description": "Tests a connection using the provided (or currently saved) torrent client settings.",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "TORRENT_CLIENT_TYPE": {
                                        "type": "string",
                                        "enum": ["qbittorrent", "transmission", "rtorrent", "deluge"],
                                    },
                                    "TORRENT_CLIENT_HOST": {"type": "string"},
                                    "TORRENT_CLIENT_PORT": {"type": "integer"},
                                    "TORRENT_CLIENT_USERNAME": {"type": "string"},
                                    "TORRENT_CLIENT_PASSWORD": {"type": "string", "format": "password"},
                                },
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Connection test result.",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/StatusResponse"}}},
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        "/api/settings/test-hardcover": {
            "post": {
                "tags": ["Settings"],
                "summary": "Test Hardcover API token",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "HARDCOVER_API_TOKEN": {"type": "string"}
                                },
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Token validation result.",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/StatusResponse"}}},
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        # ── Admin ─────────────────────────────────────────────────────────────
        "/admin/users": {
            "get": {
                "tags": ["Admin"],
                "summary": "List all users",
                "description": "Requires `is_admin`. Returns JSON when `Accept: application/json` is sent.",
                "responses": {
                    "200": {
                        "description": "User list.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/User"},
                                }
                            }
                        },
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                    "403": {"$ref": "#/components/responses/Forbidden"},
                },
            },
        },
        "/admin/users/new": {
            "post": {
                "tags": ["Admin"],
                "summary": "Create a new user",
                "description": "Requires `is_admin`. Usernames must be unique.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/x-www-form-urlencoded": {
                            "schema": {
                                "type": "object",
                                "required": ["username", "password"],
                                "properties": {
                                    "username": {"type": "string"},
                                    "password": {"type": "string", "format": "password"},
                                    "can_search": {"type": "string", "enum": ["on"], "description": "Include to grant permission."},
                                    "can_download": {"type": "string", "enum": ["on"]},
                                    "can_settings": {"type": "string", "enum": ["on"]},
                                    "is_admin": {"type": "string", "enum": ["on"]},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "302": {"description": "User created — redirects to `/admin/users`."},
                    "400": {"description": "Username already exists or validation error."},
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                    "403": {"$ref": "#/components/responses/Forbidden"},
                },
            },
        },
        "/admin/users/{user_id}": {
            "post": {
                "tags": ["Admin"],
                "summary": "Edit a user's permissions or password",
                "description": "Requires `is_admin`. Leave `new_password` blank to keep the existing password.",
                "parameters": [
                    {"name": "user_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/x-www-form-urlencoded": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "new_password": {"type": "string", "format": "password"},
                                    "can_search": {"type": "string", "enum": ["on"]},
                                    "can_download": {"type": "string", "enum": ["on"]},
                                    "can_settings": {"type": "string", "enum": ["on"]},
                                    "is_admin": {"type": "string", "enum": ["on"]},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "302": {"description": "User updated — redirects to `/admin/users`."},
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                    "403": {"$ref": "#/components/responses/Forbidden"},
                    "404": {"description": "User not found."},
                },
            },
        },
        "/admin/users/{user_id}/delete": {
            "post": {
                "tags": ["Admin"],
                "summary": "Delete a user",
                "description": "Requires `is_admin`. Cannot delete the env-admin account.",
                "parameters": [
                    {"name": "user_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                ],
                "responses": {
                    "302": {"description": "User deleted — redirects to `/admin/users`."},
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                    "403": {"$ref": "#/components/responses/Forbidden"},
                    "404": {"description": "User not found."},
                },
            },
        },
        # ── System ────────────────────────────────────────────────────────────
        "/system/public_ip": {
            "get": {
                "tags": ["System"],
                "summary": "Get the server's public IP address",
                "responses": {
                    "200": {
                        "description": "Public IP info.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "ip": {"type": "string"},
                                        "source": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        "/events": {
            "get": {
                "tags": ["System"],
                "summary": "Server-Sent Events stream",
                "description": (
                    "Real-time event stream (`text/event-stream`) for download monitoring, "
                    "status updates, and background task notifications."
                ),
                "responses": {
                    "200": {
                        "description": "SSE stream (keep-alive connection).",
                        "content": {"text/event-stream": {"schema": {"type": "string"}}},
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                },
            },
        },
        "/proxy_thumbnail": {
            "get": {
                "tags": ["System"],
                "summary": "Proxy and cache a torrent cover thumbnail",
                "parameters": [
                    {
                        "name": "url",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string", "format": "uri"},
                        "description": "Original thumbnail URL to proxy.",
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Image data.",
                        "content": {"image/*": {"schema": {"type": "string", "format": "binary"}}},
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                    "404": {"description": "Thumbnail not found or fetch failed."},
                },
            },
        },
        # ── OpenAPI self-reference ────────────────────────────────────────────
        "/api/openapi.json": {
            "get": {
                "tags": ["System"],
                "summary": "OpenAPI spec (this document)",
                "description": "Returns the OpenAPI 3.0 spec for all MouseSearch API endpoints.",
                "security": [],
                "responses": {
                    "200": {
                        "description": "OpenAPI 3.0 JSON document.",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    }
                },
            },
        },
        "/api/docs": {
            "get": {
                "tags": ["System"],
                "summary": "Swagger UI",
                "description": "Interactive API explorer powered by Swagger UI.",
                "security": [],
                "responses": {
                    "200": {"description": "Swagger UI HTML page.", "content": {"text/html": {"schema": {"type": "string"}}}},
                },
            },
        },
    },
}
