"""Fresh public GETs only. Authenticated API POSTs are deliberately unchanged."""
import urllib.parse
import urllib.request
import uuid


def fresh_request(url, user_agent):
    parts = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    query = [(key, value) for key, value in query if key != "_my4d_check"]
    query.append(("_my4d_check", uuid.uuid4().hex))
    fresh_url = urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))
    return urllib.request.Request(fresh_url, headers={
        "User-Agent": user_agent,
        "Cache-Control": "no-cache, no-store, max-age=0",
        "Pragma": "no-cache",
    })
