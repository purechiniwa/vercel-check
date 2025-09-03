from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
import httpx
import ipaddress
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Whoami on Vercel", version="1.0.0")

# Preferred header order for real client IP on Vercel
IP_HEADER_CANDIDATES = [
    "x-forwarded-for",          # Vercel populates this with the public client IP
    "x-real-ip",
    "x-vercel-forwarded-for",
    "x-vercel-proxied-for",
    "forwarded",
]

# --- Database connection ---
def get_db():
    conn = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
    )
    return conn


def extract_ip_from_headers(headers: dict) -> str | None:
    # x-forwarded-for can contain a list: client, proxy1, proxy2, ...
    xff = headers.get("x-forwarded-for")
    if xff:
        for token in xff.split(","):
            ip = token.strip()
            if ip:
                return ip

    # try other single-value headers
    for name in IP_HEADER_CANDIDATES[1:]:
        val = headers.get(name)
        if val:
            if name == "forwarded" and "for=" in val:
                try:
                    part = val.split("for=")[1].split(";")[0]
                    ip = part.strip().strip('"').strip("[]")
                    return ip
                except Exception:
                    pass
            return val

    return None


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/json")
async def whoami(request: Request):
    headers = {k.lower(): v for k, v in request.headers.items()}
    ip = extract_ip_from_headers(headers) or request.client.host

    try:
        ipaddress.ip_address(ip)
        valid_ip = True
    except Exception:
        valid_ip = False

    geo = None
    if valid_ip:
        url = f"https://ipapi.co/{ip}/json/"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(url)
                if r.status_code == 200:
                    data = r.json()
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


@app.get("/verify/{member_id}")
async def verify(member_id: str, request: Request):
    headers = {k.lower(): v for k, v in request.headers.items()}
    ip = extract_ip_from_headers(headers) or request.client.host

    try:
        ipaddress.ip_address(ip)
        valid_ip = True
    except Exception:
        valid_ip = False

    is_valid = False
    country_name = None

    if valid_ip:
        url = f"https://ipapi.co/{ip}/json/"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(url)
                if r.status_code == 200:
                    data = r.json()
                    country_name = data.get("country_name")
                    if country_name and country_name.lower() == "indonesia":
                        is_valid = True
        except Exception:
            pass

    # --- Insert into existing MySQL table ---
    try:
        conn = get_db()
        cursor = conn.cursor()
        sql = """
            INSERT INTO verify (discord_id, ip, country_name, ip_is_valid, verified)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (member_id, ip, country_name, valid_ip, is_valid))
        conn.commit()
    except Exception as e:
        return HTMLResponse(f"<h1 style='color:red;'>DB Error: {e}</h1>", status_code=500)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    # --- Return simple HTML ---
    if is_valid:
        return HTMLResponse(
            f"<h1 style='color:green;'>✅ Verification Success</h1>"
        )
    else:
        return HTMLResponse(
            f"<h1 style='color:red;'>❌ Verification Failed</h1>"
        )









