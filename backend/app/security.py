"""Local-only HTTP controls, applied before multipart parsing."""
import asyncio
import ipaddress
from urllib.parse import urlsplit

from starlette.responses import JSONResponse


class RequestLimits:
    def __init__(self, app):
        self.app = app

    @staticmethod
    def _allowed_origin(origin: str) -> bool:
        try:
            parsed = urlsplit(origin)
            if parsed.scheme not in {'http', 'https'} or parsed.username or parsed.password:
                return False
            host = (parsed.hostname or '').lower().rstrip('.')
            if host in {'localhost', 'localhost.localdomain'}:
                return True
            address = ipaddress.ip_address(host)
            return address.is_loopback or address.is_private or address.is_link_local
        except (ValueError, TypeError):
            return False

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = dict(scope['headers'])
        origin = headers.get(b'origin', b'').decode('latin1')
        if origin and not self._allowed_origin(origin):
            return await JSONResponse({'detail': 'Cross-origin requests are not allowed.'}, 403)(scope, receive, send)
        if scope['method'] not in {'POST', 'PUT', 'PATCH'}:
            return await self.app(scope, receive, send)
        path = scope['path']
        limit = {'/api/verify/video': 51*1024*1024, '/api/verify/audio':26*1024*1024, '/api/verify/image':11*1024*1024}.get(path, 128*1024)
        try:
            if int(headers.get(b'content-length', b'0')) > limit:
                return await JSONResponse({'detail':'Request exceeds the size limit.'}, 413)(scope, receive, send)
        except ValueError:
            return await JSONResponse({'detail':'Invalid Content-Length.'}, 400)(scope, receive, send)
        chunks, size = [], 0
        try:
            async with asyncio.timeout(30):
                while True:
                    message = await receive()
                    if message['type'] == 'http.disconnect':
                        return
                    body = message.get('body', b'')
                    size += len(body)
                    if size > limit:
                        return await JSONResponse({'detail':'Request exceeds the size limit.'}, 413)(scope, receive, send)
                    chunks.append(body)
                    if not message.get('more_body'):
                        break
        except TimeoutError:
            return await JSONResponse({'detail':'Upload timed out.'}, 408)(scope, receive, send)
        delivered = False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type':'http.request', 'body':b''.join(chunks), 'more_body':False}
            return await receive()
        await self.app(scope, replay, send)
