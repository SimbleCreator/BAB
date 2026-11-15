"""Request size limit and security headers. Plain ASGI so streaming bodies are counted."""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_BODY_BYTES = 6 * 1024 * 1024  # GPX limit is 5 MB; a little room for form fields


class BodySizeLimit:
    """Reject bodies over the limit with 413, using Content-Length or by counting chunks."""

    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        length = dict(scope.get("headers", [])).get(b"content-length")
        if length is not None and length.isdigit() and int(length) > self.max_bytes:
            await self._reject(send)
            return

        seen = 0
        rejected = False
        started = False

        async def guarded_send(message: Message) -> None:
            nonlocal started
            if rejected:
                return  # the 413 has already been sent; drop the app's own response
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        async def counted() -> Message:
            nonlocal seen, rejected
            if rejected:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > self.max_bytes and not started:
                    rejected = True
                    await self._reject(send)
                    # Tell the app the client went away so it stops reading.
                    return {"type": "http.disconnect"}
            return message

        await self.app(scope, counted, guarded_send)

    @staticmethod
    async def _reject(send: Send) -> None:
        body = b'{"detail":"The upload is too large.","code":"too_large"}'
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


class SecurityHeaders:
    """Conservative headers for a JSON API. The interactive docs (development only) need
    scripts, so they are left without a CSP."""

    def __init__(self, app: ASGIApp, hsts: bool) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        is_docs = scope.get("path", "").startswith(("/docs", "/openapi.json"))

        async def with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers += [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"permissions-policy", b"geolocation=(), camera=(), microphone=()"),
                ]
                if not is_docs:
                    headers.append(
                        (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'")
                    )
                if self.hsts:
                    headers.append(
                        (b"strict-transport-security", b"max-age=31536000; includeSubDomains")
                    )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, with_headers)
