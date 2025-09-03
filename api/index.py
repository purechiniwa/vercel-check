from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
import ipaddress

app = FastAPI(title="Whoami on Vercel", version="1.0.0")

# Preferred header order for real client IP on Vercel
IP_HEADER_CANDIDATES = [
    "x-forwarded-for",          # Vercel populates this with the public client IP
    "x-real-ip",
    "x-vercel-forwarded-for",
    "x-vercel-proxied-for",
    "forwarded",
]

def extract_ip_from_headers(headers: dict) -> str | None:
    # x-forwarded-for can contain a list: client, proxy1, proxy2, ...
    xff = headers.get("x-forwarded-for")
    if xff:
        # take the first non-empty token
        for token in xff.split(","):
            ip = token.strip()
            if ip:
                return ip

    # try other single-value headers
    for name in IP_HEADER_CANDIDATES[1:]:
        val = headers.get(name)
        if val:
            # Forwarded header can be like: for=203.0.113.5;proto=https;host=...
            if name == "forwarded" and "for=" in val:
                try:
                    part = val.split("for=")[1].split(";")[0]
                    ip = part.strip().strip('"').strip("[]")  # handle IPv6 [] or quotes
                    return ip
                except Exception:
                    pass
            return val

    return None

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/")
async def whoami(request: Request):
    # Headers are case-insensitive; FastAPI exposes a CIMultiDictProxy
    headers = {k.lower(): v for k, v in request.headers.items()}

    ip = extract_ip_from_headers(headers) or request.client.host

    # sanity check: ensure it's an IP (and not something odd)
    try:
        ipaddress.ip_address(ip)
        valid_ip = True
    except Exception:
        valid_ip = False

    geo = None
    if valid_ip:
        # Free, no-key lookup (light rate limits). Swap for ipinfo, MaxMind, etc. if needed.
        url = f"https://ipapi.co/{ip}/json/"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(url)
                if r.status_code == 200:
                    data = r.json()
                    # pick only useful fields
                    geo = {
                        "ip": data.get("ip"),
                        "city": data.get("city"),
                        "region": data.get("region"),
                        "country": data.get("country"),
                        "country_name": data.get("country_name"),
                        "latitude": data.get("latitude"),
                        "longitude": data.get("longitude"),
                        "org": data.get("org"),
                        "timezone": data.get("timezone"),
                    }
        except Exception:
            pass

    return JSONResponse(
        {
            "ip": ip,
            "ip_is_valid": valid_ip,
            "geo": geo,
            "user_agent": headers.get("user-agent"),
        }
    )
