from fastapi import FastAPI, Request
import httpx

app = FastAPI()

# Use ip-api.com (free, no API key required)
IP_API_URL = "http://ip-api.com/json/"

@app.get("/myip")
async def get_ip_and_location(request: Request):
    # Get client IP (fallback to headers if behind proxy/load balancer)
    client_host = request.client.host
    forwarded = request.headers.get("x-forwarded-for")
    ip_address = forwarded.split(",")[0] if forwarded else client_host

    # Call external API to get location info
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{IP_API_URL}{ip_address}")
        data = response.json()

    return {
        "ip": ip_address,
        "location": data
    }
