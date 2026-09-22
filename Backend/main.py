# DineIQ Backend API
# ---------------------------------------------------------
# Modular Architecture Entry Point
# ---------------------------------------------------------

# CRITICAL: Import startup FIRST to decode credentials before any other imports
import startup  # Decodes SERVICE_ACCOUNT_JSON_BASE64 into a real file if on Vercel/Render

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Import Routers
from routes.auth import auth_router
from routes.order import order_router
from agents.menu import menu_router
from agents.recommendation import recommendation_router
from agents.chatbot import chatbot_router
from services.campaigns import campaigns_router
from agents.monitoring import monitoring_router
from services.reviews import reviews_router
from routes.dashboard import dashboard_router
from routes.tickets import tickets_router
from routes.kitchen import kitchen_router




# Initialize App
app = FastAPI(title="DineIQ Backend API", version="2.0")

# CORS Configuration
# Allow both production (Vercel) and development (localhost) origins
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000,http://localhost:8080,http://localhost:8081").split(",")
print("🚀 ALLOWED_ORIGINS LOADED:", allowed_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Register Routers
# ---------------------------------------------------------
# Auth: Login, Signup, OTP
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# Menu: Fetch Menu, AI Combos (Future)
app.include_router(menu_router, prefix="/menu", tags=["Menu"])

# Orders: Checkout, Place Order, Pricing Strategy
app.include_router(order_router, tags=["Orders"]) 
# Note: order_router has /pricing-strategy at root level to match frontend

# Recommendations: Upsell, Add-ons, Preferences
# Frontend calls /item-addons at root, let's include it at root for compatibility
app.include_router(recommendation_router, tags=["Recommendations"]) 

# Chatbot: AI Chat
app.include_router(chatbot_router, prefix="/chatbot", tags=["Chatbot"])

# Campaigns: Marketing
app.include_router(campaigns_router, prefix="/campaigns", tags=["Campaigns"])

# Monitoring: Tracking logs & AI Insights
app.include_router(monitoring_router, prefix="/activity", tags=["Monitoring"])

# Reviews: Customer Feedback
app.include_router(reviews_router, prefix="/reviews", tags=["Reviews"])

# Dashboard: Management Endpoints
app.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])

# Ticketing: Menu Approval Workflow
app.include_router(tickets_router, prefix="/tickets", tags=["Tickets"])

# Kitchen Display System
app.include_router(kitchen_router, prefix="/kitchen", tags=["Kitchen"])





# ---------------------------------------------------------
# Application Startup
# ---------------------------------------------------------
def _seed_master_account():
    """
    Optional first-run bootstrap for a fresh (empty) deploy: if
    SEED_MASTER_PHONE/SEED_MASTER_NAME are set and no master account with
    that phone exists yet, create one. Safe to leave the env vars set —
    it no-ops once the account exists.
    """
    phone = os.getenv("SEED_MASTER_PHONE")
    name = os.getenv("SEED_MASTER_NAME")
    if not phone or not name:
        return

    from services.dependencies import sqlite_db
    if sqlite_db.fetch_one("SELECT 1 FROM master WHERE phone = ?", (phone,)):
        return

    from routes.auth import generate_next_master_id
    import time
    sqlite_db.insert("master", {
        "master_id": generate_next_master_id(),
        "name": name,
        "phone": phone,
        "is_active": 1,
        "created_at": time.strftime("%d/%m/%Y %H:%M:%S"),
    })
    print(f"✅ Seeded master account for phone {phone}")


@app.on_event("startup")
async def startup_event():
    import asyncio
    from services.DineIQ_Database_Sync import start_progressive_sync
    # Start the progressive sync worker to sync SQLite changes to Google Sheets
    asyncio.create_task(start_progressive_sync())

    _seed_master_account()

# ---------------------------------------------------------
# Health Check
# ---------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "DineIQ Backend", "version": "2.0"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting DineIQ Backend on port {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
