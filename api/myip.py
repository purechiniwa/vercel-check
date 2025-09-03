from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mangum import Mangum   # adapter for serverless

import httpx

app = FastAPI()

IP_API_URL = "http://ip-api.com/json/"

@app.get("/myip")
async def get_ip_and_location(request: Request):
    client_host = request.client.host
    forwarded = request.headers.get("x-forwarded-for")
    ip_address = forwarded.split(",")[0] if forwarded else client_host

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{IP_API_URL}{ip_address}")
        data = response.json()

    return JSONResponse({
        "ip": ip_address,
        "location": data
    })

# Vercel needs handler
handler = Mangum(app)
