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
def _seed_accounts():
    """
    Optional first-run bootstrap for a fresh (empty) deploy — local SQLite
    data is gitignored and Render's free tier has no persistent disk, so
    every fresh deploy/restart starts with zero accounts.

    SEED_MASTER_PHONE / SEED_MASTER_NAME: the single owner/master account.
    SEED_STAFF: "Name:phone:role,Name:phone:role,..." for staff accounts
    (role one of admin/manager/chef/staff). Safe to leave both set — each
    entry no-ops once an account with that phone already exists.
    """
    import time
    from services.dependencies import sqlite_db

    master_phone = os.getenv("SEED_MASTER_PHONE")
    master_name = os.getenv("SEED_MASTER_NAME")
    if master_phone and master_name:
        if not sqlite_db.fetch_one("SELECT 1 FROM master WHERE phone = ?", (master_phone,)):
            from routes.auth import generate_next_master_id
            sqlite_db.insert("master", {
                "master_id": generate_next_master_id(),
                "name": master_name,
                "phone": master_phone,
                "is_active": 1,
                "created_at": time.strftime("%d/%m/%Y %H:%M:%S"),
            })
            print(f"✅ Seeded master account for phone {master_phone}")

    staff_spec = os.getenv("SEED_STAFF")
    if staff_spec:
        from routes.auth import generate_next_staff_id
        for entry in staff_spec.split(","):
            parts = [p.strip() for p in entry.strip().split(":")]
            if len(parts) != 3:
                continue
            name, phone, role = parts
            if not name or not phone:
                continue
            if sqlite_db.fetch_one("SELECT 1 FROM staff WHERE phone = ?", (phone,)):
                continue
            sqlite_db.insert("staff", {
                "staff_id": generate_next_staff_id(),
                "name": name,
                "phone": phone,
                "role": role or "staff",
                "is_active": 1,
                "created_at": time.strftime("%d/%m/%Y %H:%M:%S"),
            })
            print(f"✅ Seeded staff account for phone {phone} ({role})")


def _seed_demo_data():
    """
    Optional demo data (menu, customers, orders, reviews) for a fresh
    deploy with SEED_DEMO_DATA set, so the admin dashboard isn't blank.
    No-ops if the menu table already has rows.
    """
    if not os.getenv("SEED_DEMO_DATA"):
        return

    import time
    from services.dependencies import sqlite_db

    if sqlite_db.fetch_one("SELECT 1 FROM menu LIMIT 1"):
        return

    now = time.strftime("%d/%m/%Y %H:%M:%S")

    menu_items = [
        ("Item_0001", "Paneer Tikka", "Starters", 350, "Grilled cottage cheese marinated in spiced yogurt"),
        ("Item_0002", "Chicken Biryani", "Mains", 450, "Fragrant basmati rice layered with spiced chicken"),
        ("Item_0003", "Butter Naan", "Sides", 60, "Soft leavened bread brushed with butter"),
        ("Item_0004", "Gulab Jamun", "Desserts", 120, "Fried milk dumplings soaked in sugar syrup"),
        ("Item_0005", "Mango Lassi", "Beverages", 150, "Chilled yogurt drink blended with mango"),
        ("Item_0006", "Dal Makhani", "Mains", 280, "Slow-cooked black lentils in a creamy tomato gravy"),
    ]
    for item_id, name, category, price, desc in menu_items:
        sqlite_db.insert("menu", {
            "item_id": item_id, "name": name, "category": category,
            "base_price": price, "low_cap_price": price, "high_cap_price": price,
            "current_price": price, "description": desc, "is_active": 1,
        })

    customers = [
        ("Cust_0001", "Priya Sharma", "priya.sharma@example.com", "9123456780", "Regular"),
        ("Cust_0002", "Rahul Verma", "rahul.verma@example.com", "9123456781", "New"),
        ("Cust_0003", "Sneha Iyer", "sneha.iyer@example.com", "9123456782", "VIP"),
    ]
    for cust_id, name, email, phone, category in customers:
        sqlite_db.insert("customers", {
            "customer_id": cust_id, "name": name, "email": email, "phone": phone,
            "customer_category": category, "created_at": now, "last_login": now,
        })

    orders = [
        ("Ord_0001", "Cust_0001", "COMPLETED", [("Item_0002", 1, 450), ("Item_0003", 2, 60)]),
        ("Ord_0002", "Cust_0002", "PENDING", [("Item_0001", 1, 350), ("Item_0005", 1, 150)]),
    ]
    for order_id, cust_id, status, items in orders:
        total = sum(qty * price for _, qty, price in items)
        sqlite_db.insert("orders", {
            "order_id": order_id, "customer_id": cust_id, "order_price": total,
            "created_at": now, "status": status, "table_number": 1, "instructions": "",
        })
        for idx, (item_id, qty, price) in enumerate(items, start=1):
            sqlite_db.insert("order_items", {
                "order_item_id": f"{order_id}_Item_{idx:04d}", "order_id": order_id,
                "item_id": item_id, "quantity": qty, "price": price,
                "status": "PENDING", "special_instructions": "",
            })

    reviews = [
        ("Rev_0001", "Cust_0001", 5, 5, 5, 5, 5, "Amazing food and quick service!"),
        ("Rev_0002", "Cust_0003", 4, 4, 5, 4, 4, "Great ambience, will visit again."),
    ]
    for review_id, cust_id, food, service, clean, value, overall, comment in reviews:
        sqlite_db.insert("reviews", {
            "review_id": review_id, "customer_id": cust_id, "review_datetime": now,
            "food_quality": food, "service": service, "cleanliness": clean,
            "value_for_money": value, "overall_experience": overall, "comments": comment,
            "review_type": "General", "urgency": "LOW", "status": "NEW",
        })

    print("✅ Seeded demo data: 6 menu items, 3 customers, 2 orders, 2 reviews")


@app.on_event("startup")
async def startup_event():
    import asyncio
    from services.DineIQ_Database_Sync import start_progressive_sync
    # Start the progressive sync worker to sync SQLite changes to Google Sheets
    asyncio.create_task(start_progressive_sync())

    _seed_accounts()
    _seed_demo_data()

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
