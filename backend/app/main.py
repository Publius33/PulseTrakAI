import os
import sqlite3
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, Header, HTTPException, Response, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import time
import logging
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import stripe
import jwt
from datetime import datetime, timedelta
import json

logger = logging.getLogger("pulsetrak")
logging.basicConfig(level=logging.INFO)

# Prometheus metric: count page_view events
PAGE_VIEW_COUNTER = Counter("pulsetrak_page_views_total", "Total page views (opt-in)")


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

API_KEY = os.environ.get("API_KEY", "devkey")
DB_PATH = os.environ.get("DB_PATH", str(BASE_DIR / "data.db"))

app = FastAPI(title="PulseTrakAI Backend")

# Allow the frontend dev server during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    # Basic security headers to improve production posture
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=()")
    response.headers.setdefault("Content-Security-Policy", "default-src 'self'")
    response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
    return response


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS metrics (
            event TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0,
            last_ts INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            email TEXT,
            stripe_id TEXT,
            account_id TEXT
        )
        """
    )
    # ensure account_id column exists for older DBs
    try:
        cur.execute("ALTER TABLE customers ADD COLUMN account_id TEXT")
    except Exception:
        pass
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id TEXT PRIMARY KEY,
            customer_id TEXT,
            stripe_id TEXT,
            status TEXT,
            price_cents INTEGER,
            created_ts INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            name TEXT,
            plan_id TEXT,
            seats INTEGER DEFAULT 0,
            created_ts INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            account_id TEXT,
            amount_cents INTEGER,
            period_start INTEGER,
            period_end INTEGER,
            created_ts INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS prices (
            id TEXT PRIMARY KEY,
            price_cents INTEGER,
            currency TEXT,
            stripe_price_id TEXT,
            created_ts INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS dispute_reports (
            id TEXT PRIMARY KEY,
            customer_id TEXT,
            title TEXT,
            evidence_json TEXT,
            timeline_json TEXT,
            recommended_steps TEXT,
            created_ts INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS insights_results (
            id TEXT PRIMARY KEY,
            account_id TEXT,
            payload_json TEXT,
            summary_json TEXT,
            created_ts INTEGER
        )
        """
    )
    conn.commit()
    conn.close()


def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True


def verify_admin_token(x_admin_token: str = Header(None)):
    """Simple admin token check via header `X-Admin-Token`.

    Set `ADMIN_TOKEN` in env for production; default is `admintoken` for dev.
    """
    # Legacy simple token check
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", None)
    if ADMIN_TOKEN and x_admin_token == ADMIN_TOKEN:
        return True

    # Accept Authorization: Bearer <jwt>
    auth = x_admin_token
    if not auth:
        # try Authorization header
        return False
    # If header contains 'Bearer ', reject here because header passed was X-Admin-Token.
    # This function will be used alongside `require_jwt_admin` for JWT flows.
    return False


def require_jwt_admin(authorization: str = Header(None)):
    """Verify JWT in `Authorization: Bearer <token>` header or X-Admin-Token legacy header.

    Returns decoded payload if valid, else raises 401.
    """
    # Check legacy X-Admin-Token header first
    legacy = os.environ.get("ADMIN_TOKEN")
    if authorization and authorization == legacy:
        return {"role": "admin", "legacy": True}

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    # Accept form 'Bearer <token>'
    token = authorization
    if token.startswith("Bearer "):
        token = token.split(" ", 1)[1]

    secret = os.environ.get("ADMIN_JWT_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="Admin JWT secret not configured")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Not an admin token")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid admin token")


# OAuth2 scheme for docs and dependency
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login")


def get_secret(name: str):
    """Get secret from env or (optionally) from AWS Secrets Manager if available.

    Fallback order: ENV -> AWS Secrets Manager -> None
    """
    v = os.environ.get(name)
    if v:
        return v
    try:
        import boto3
        client = boto3.client('secretsmanager')
        resp = client.get_secret_value(SecretId=name)
        return resp.get('SecretString')
    except Exception:
        return None


class PingResponse(BaseModel):
    message: str


class UserIn(BaseModel):
    username: str


class UserOut(BaseModel):
    id: str
    username: str


@app.on_event("startup")
def on_startup():
    init_db()
    app.state.start_time = time.time()


@app.get("/health", response_model=PingResponse)
async def health():
    return {"message": "ok"}


@app.get("/", response_model=PingResponse)
async def root():
    """Root returns app name and short description."""
    return {"message": "PulseTrakAI - monitoring service (safe mode)"}


@app.get("/api/status")
def status():
    """Return app status including uptime (seconds) and API name."""
    start = getattr(app.state, "start_time", time.time())
    uptime = int(time.time() - start)
    return {"name": "PulseTrakAI", "uptime_seconds": uptime, "health": "ok"}


@app.get("/api/ping", response_model=PingResponse)
async def ping():
    return {"message": "pong"}


@app.post("/api/users", response_model=UserOut)
def create_user(item: UserIn, _=Depends(verify_api_key)):
    import uuid

    uid = str(uuid.uuid4())
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (id, username) VALUES (?, ?)", (uid, item.username))
    conn.commit()
    conn.close()
    return {"id": uid, "username": item.username}


@app.get("/api/users", response_model=List[UserOut])
def list_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM users ORDER BY username")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/api/users/{user_id}", response_model=UserOut)
def get_user(user_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)


@app.delete("/api/users/{user_id}")
def delete_user(user_id: str, _=Depends(verify_api_key)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    if affected == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"deleted": user_id}


@app.post("/api/analytics/track")
def track_event(payload: dict):
    """Track a simple event. Example payload: {"event": "page_view"}

    This endpoint is intended for opt-in, anonymous analytics.
    """
    event = payload.get("event") if isinstance(payload, dict) else None
    if not event:
        raise HTTPException(status_code=400, detail="Missing 'event' in payload")
    ts = int(time.time())
    conn = get_conn()
    cur = conn.cursor()
    # upsert: increment count and set last_ts
    cur.execute(
        """
        INSERT INTO metrics(event, count, last_ts)
        VALUES (?, 1, ?)
        ON CONFLICT(event) DO UPDATE SET
          count = metrics.count + 1,
          last_ts = ?
        """,
        (event, ts, ts),
    )
    conn.commit()
    # return current metric
    cur.execute("SELECT event, count, last_ts FROM metrics WHERE event=?", (event,))
    row = cur.fetchone()
    conn.close()
    # increment Prometheus counter for page_view
    if event == 'page_view':
        try:
            PAGE_VIEW_COUNTER.inc()
        except Exception:
            pass
    return dict(row) if row else {"event": event, "count": 0}


@app.post("/api/admin/login")
async def admin_login(request: Request):
    """Admin token endpoint compatible with OAuth2 password flow.

    Reads form data directly to avoid FastAPI introspection incompatibilities in some test environments.
    Form fields: `username` and `password` — we only check password here for demo.
    Returns: {"access_token": "...", "token_type": "bearer"}
    """
    pwd = None
    # Try JSON body first (tests and API clients may send JSON)
    try:
        j = await request.json()
        pwd = j.get('password') if isinstance(j, dict) else None
    except Exception:
        pwd = None
    if not pwd:
        try:
            form = await request.form()
            pwd = form.get('password')
        except AssertionError:
            # python-multipart not installed; attempt raw body parse
            try:
                b = await request.body()
                if b:
                    import json as _j
                    parsed = _j.loads(b.decode('utf-8'))
                    pwd = parsed.get('password')
            except Exception:
                pwd = None
    if not pwd:
        raise HTTPException(status_code=400, detail="Missing password")
    admin_pwd = os.environ.get("ADMIN_PASSWORD", "adminpass")
    if pwd != admin_pwd:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    secret = os.environ.get("ADMIN_JWT_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="Admin JWT secret not configured")
    exp = datetime.utcnow() + timedelta(hours=6)
    token = jwt.encode({"role": "admin", "exp": exp}, secret, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/metrics")
def get_metrics(admin=Depends(require_jwt_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT event, count, last_ts FROM metrics ORDER BY event")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/metrics")
def prometheus_metrics():
    # Expose Prometheus metrics at /metrics
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@app.get("/api/billing/report")
def billing_report(admin=Depends(verify_admin_token)):
    """Return a simple CSV billing report built from metrics counts.

    This is a minimal placeholder — replace with real usage metering for billing.
    """
    import csv
    from io import StringIO

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT event, count, last_ts FROM metrics ORDER BY event")
    rows = cur.fetchall()
    conn.close()

    sio = StringIO()
    writer = csv.writer(sio)
    writer.writerow(["event", "count", "last_ts"])
    for r in rows:
        writer.writerow([r[0], r[1], r[2]])
    return Response(content=sio.getvalue(), media_type="text/csv")


@app.post("/api/payment/create-intent")
def create_payment_intent(payload: dict):
    """Create a Stripe PaymentIntent when `STRIPE_SECRET` is set.

    Expected JSON body: {"amount_cents": 500, "currency": "usd"}
    Returns the PaymentIntent client_secret so the frontend can complete payment.
    """
    secret = os.environ.get("STRIPE_SECRET")
    if not secret:
        return {"ready": False, "message": "Payment provider not configured. Set STRIPE_SECRET in env."}
    stripe.api_key = secret
    amount = int(payload.get("amount_cents", 0))
    currency = payload.get("currency", "usd")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount_cents")
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            automatic_payment_methods={"enabled": True},
        )
        return {"ready": True, "client_secret": intent.client_secret}
    except Exception as e:
        logger.exception("Stripe create intent failed")
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/customers")
def create_customer(payload: dict, admin=Depends(require_jwt_admin)):
    """Create a customer in Stripe and persist mapping.

    JSON: {"email": "user@example.com"}
    """
    email = payload.get("email") if isinstance(payload, dict) else None
    if not email:
        raise HTTPException(status_code=400, detail="Missing email")
    secret = os.environ.get("STRIPE_SECRET")
    if secret:
        stripe.api_key = secret
    else:
        # Allow operation when STRIPE_SECRET is not set (tests may mock `stripe`).
        logger.info("STRIPE_SECRET not set; proceeding (tests may mock stripe)")
    try:
        cust = stripe.Customer.create(email=email)
        cid = cust.id
        account_id = payload.get('account_id') if isinstance(payload, dict) else None
        conn = get_conn()
        cur = conn.cursor()
        # guard: ensure account_id column exists
        try:
            cur.execute("ALTER TABLE customers ADD COLUMN account_id TEXT")
        except Exception:
            pass
        cur.execute("INSERT OR REPLACE INTO customers (id, email, stripe_id, account_id) VALUES (?, ?, ?, ?)", (cid, email, cid, account_id))
        conn.commit()
        conn.close()
        return {"id": cid, "email": email, "account_id": account_id}
    except Exception as e:
        logger.exception("Stripe create customer failed")
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/subscriptions")
def create_subscription(payload: dict, admin=Depends(require_jwt_admin)):
    """Create a subscription for a customer.

    JSON: {"customer_stripe_id": "cus_xxx", "price_cents": 500, "currency":"usd"}
    """
    stripe_id = payload.get("customer_stripe_id")
    price = int(payload.get("price_cents", 0))
    currency = payload.get("currency", "usd")
    if not stripe_id or price <= 0:
        raise HTTPException(status_code=400, detail="Missing customer_stripe_id or invalid price")
    secret = os.environ.get("STRIPE_SECRET")
    if secret:
        stripe.api_key = secret
    else:
        # Allow operation when STRIPE_SECRET is not set (tests may mock `stripe`).
        logger.info("STRIPE_SECRET not set; proceeding (tests may mock stripe)")
    try:
        # Use persisted prices when available to avoid creating duplicate Stripe prices.
        conn = get_conn()
        cur = conn.cursor()
        # ensure prices table exists (handle older DBs without migration)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS prices (
                id TEXT PRIMARY KEY,
                price_cents INTEGER,
                currency TEXT,
                stripe_price_id TEXT,
                created_ts INTEGER
            )
            """
        )
        cur.execute("SELECT stripe_price_id FROM prices WHERE price_cents=? AND currency=?", (price, currency))
        prow = cur.fetchone()
        if prow and prow[0]:
            price_id = prow[0]
        else:
            # create a new Stripe Price (tests may mock this)
            try:
                new_price = stripe.Price.create(
                    unit_amount=price,
                    currency=currency,
                    product_data={"name": "PulseTrakAI subscription"},
                )
                price_id = new_price.id
                # persist mapping
                import uuid
                pid = str(uuid.uuid4())
                ts = int(time.time())
                cur.execute("INSERT INTO prices (id, price_cents, currency, stripe_price_id, created_ts) VALUES (?, ?, ?, ?, ?)", (pid, price, currency, price_id, ts))
                conn.commit()
            except Exception:
                logger.exception("Stripe price creation failed")
                conn.close()
                raise HTTPException(status_code=502, detail="Failed to create price")

        # enforce plan seat limits if customer is linked to an account
        # guard: ensure account_id column exists for older DBs
        try:
            cur.execute("ALTER TABLE customers ADD COLUMN account_id TEXT")
        except Exception:
            pass
        cur.execute("SELECT account_id FROM customers WHERE stripe_id=?", (stripe_id,))
        crow = cur.fetchone()
        acct_id = crow[0] if crow else None
        if acct_id:
            cur.execute("SELECT seats, plan_id FROM accounts WHERE id=?", (acct_id,))
            arow = cur.fetchone()
            if arow:
                seats_allowed = arow[0] or 0
                # count active subscriptions for this account
                cur.execute("SELECT COUNT(*) FROM subscriptions s JOIN customers c ON s.stripe_id=c.stripe_id WHERE c.account_id=? AND s.status='active'", (acct_id,))
                used = cur.fetchone()[0]
                if used >= seats_allowed:
                    conn.close()
                    raise HTTPException(status_code=403, detail="Seat limit reached for account")

        # create subscription using price id
        try:
            subscription = stripe.Subscription.create(
                customer=stripe_id,
                items=[{"price": price_id, "quantity": 1}],
                expand=["latest_invoice.payment_intent"],
            )
        except Exception:
            logger.exception("Stripe create subscription failed")
            conn.close()
            raise HTTPException(status_code=502, detail="Failed to create subscription")
        sid = subscription.id
        status = subscription.status
        now = int(time.time())
        # attempt to link to internal customer id by stripe_id
        cur.execute("SELECT id FROM customers WHERE stripe_id=?", (stripe_id,))
        crow = cur.fetchone()
        cust_id = crow[0] if crow else None
        # store subscription id referencing customer (store stripe ids)
        cur.execute("INSERT OR REPLACE INTO subscriptions (id, customer_id, stripe_id, status, price_cents, created_ts) VALUES (?, ?, ?, ?, ?, ?)",
                (sid, cust_id, sid, status, price, now))
        conn.commit()
        conn.close()
        return {"id": sid, "status": status}
    except Exception as e:
        logger.exception("Stripe create subscription failed")
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/subscriptions/{sub_id}")
def get_subscription(sub_id: str, admin=Depends(require_jwt_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, customer_id, stripe_id, status, price_cents, created_ts FROM subscriptions WHERE id=?", (sub_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return dict(row)


@app.get("/api/subscriptions")
def list_subscriptions(admin=Depends(require_jwt_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, customer_id, stripe_id, status, price_cents, created_ts FROM subscriptions ORDER BY created_ts DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/plans")
def list_plans(admin=Depends(require_jwt_admin)):
    """Return available subscription plans and feature summaries.

    This endpoint is read-only and intended for admin/console use.
    """
    plans = [
        {
            "id": "basic",
            "name": "Basic",
            "price_per_user_month": 5,
            "features": [
                "core monitoring",
                "basic reports",
                "opt-in telemetry",
            ],
        },
        {
            "id": "advanced",
            "name": "Advanced",
            "price_per_user_month": 12,
            "features": [
                "integrations (email/chat/issue trackers)",
                "productivity intelligence",
                "dispute timelines",
            ],
        },
        {
            "id": "enterprise_ai",
            "name": "Enterprise AI",
            "price_per_user_month": 25,
            "features": [
                "AI coach for managers",
                "advanced forecasting",
                "priority support",
            ],
        },
    ]
    return {"plans": plans}


@app.post("/api/accounts")
def create_account(payload: dict, admin=Depends(require_jwt_admin)):
    name = payload.get('name') if isinstance(payload, dict) else None
    plan_id = payload.get('plan_id') if isinstance(payload, dict) else 'basic'
    seats = int(payload.get('seats', 0)) if isinstance(payload, dict) else 0
    if not name:
        raise HTTPException(status_code=400, detail='Missing name')
    import uuid
    aid = str(uuid.uuid4())
    ts = int(time.time())
    conn = get_conn()
    cur = conn.cursor()
    # guard: ensure accounts table exists for older DBs
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            name TEXT,
            plan_id TEXT,
            seats INTEGER DEFAULT 0,
            created_ts INTEGER
        )
        """
    )
    conn.commit()
    cur.execute("INSERT INTO accounts (id, name, plan_id, seats, created_ts) VALUES (?, ?, ?, ?, ?)", (aid, name, plan_id, seats, ts))
    conn.commit()
    conn.close()
    return {"id": aid, "name": name, "plan_id": plan_id, "seats": seats}


@app.get("/api/accounts/{acct_id}")
def get_account(acct_id: str, admin=Depends(require_jwt_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, plan_id, seats, created_ts FROM accounts WHERE id=?", (acct_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail='Account not found')
    return dict(row)


@app.post("/api/accounts/{acct_id}/plan")
def change_account_plan(acct_id: str, payload: dict, admin=Depends(require_jwt_admin)):
    plan_id = payload.get('plan_id') if isinstance(payload, dict) else None
    if not plan_id:
        raise HTTPException(status_code=400, detail='Missing plan_id')
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE accounts SET plan_id=? WHERE id=?", (plan_id, acct_id))
    conn.commit()
    conn.close()
    return {"id": acct_id, "plan_id": plan_id}


@app.post("/api/billing/usage")
def report_usage(payload: dict, admin=Depends(require_jwt_admin)):
    account_id = payload.get('account_id') if isinstance(payload, dict) else None
    seats_used = int(payload.get('seats_used', 0)) if isinstance(payload, dict) else 0
    if not account_id:
        raise HTTPException(status_code=400, detail='Missing account_id')
    # determine plan price
    plan_prices = {'basic': 5, 'advanced': 12, 'enterprise_ai': 25}
    conn = get_conn()
    cur = conn.cursor()
    # guard: ensure invoices table exists for older DBs
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            account_id TEXT,
            amount_cents INTEGER,
            period_start INTEGER,
            period_end INTEGER,
            created_ts INTEGER
        )
        """
    )
    conn.commit()
    cur.execute("SELECT plan_id FROM accounts WHERE id=?", (account_id,))
    prow = cur.fetchone()
    if not prow:
        conn.close()
        raise HTTPException(status_code=404, detail='Account not found')
    plan_id = prow[0]
    price = plan_prices.get(plan_id, 5)
    amount_cents = seats_used * price * 100
    import uuid
    iid = str(uuid.uuid4())
    ts = int(time.time())
    # For simplicity, set period_start/end to now
    cur.execute("INSERT INTO invoices (id, account_id, amount_cents, period_start, period_end, created_ts) VALUES (?, ?, ?, ?, ?, ?)", (iid, account_id, amount_cents, ts, ts, ts))
    conn.commit()
    conn.close()
    return {"id": iid, "amount_cents": amount_cents}


@app.post("/api/subscriptions/{sub_id}/cancel")
def cancel_subscription(sub_id: str, admin=Depends(require_jwt_admin)):
    """Cancel a subscription both in Stripe and locally.

    This attempts to call Stripe to cancel the subscription and updates the
    local DB status to 'canceled'. Tests may mock `stripe`.
    """
    secret = os.environ.get("STRIPE_SECRET")
    if secret:
        stripe.api_key = secret
    else:
        logger.info("STRIPE_SECRET not set; proceeding (tests may mock stripe)")

    try:
        # Try to cancel via Stripe (may be mocked)
        try:
            resp = stripe.Subscription.delete(sub_id)
            new_status = getattr(resp, 'status', 'canceled')
        except Exception:
            logger.exception("Stripe cancel subscription call failed")
            new_status = 'canceled'

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE subscriptions SET status=? WHERE id=?", (new_status, sub_id))
        conn.commit()
        conn.close()
        return {"id": sub_id, "status": new_status}
    except Exception as e:
        logger.exception("Failed to cancel subscription")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Minimal Stripe webhook receiver. Accepts JSON payload and updates
    subscription records for relevant events.

    For robust production use, verify signatures using `STRIPE_WEBHOOK_SECRET`.
    """
    # If webhook secret configured, verify signature using Stripe helper
    raw_body = await request.body()
    sig_header = request.headers.get('Stripe-Signature')
    secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    if secret:
        try:
            evt = stripe.Webhook.construct_event(raw_body, sig_header, secret)
            payload = evt
        except Exception:
            logger.exception("Stripe webhook signature verification failed")
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
    else:
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")

    # Basic event handling
    etype = payload.get('type')
    data = payload.get('data', {}).get('object', {})
    if not etype:
        raise HTTPException(status_code=400, detail="Missing event type")

    try:
        conn = get_conn()
        cur = conn.cursor()
        if etype in ('customer.subscription.deleted', 'customer.subscription.updated'):
            sid = data.get('id')
            status = data.get('status')
            if sid and status:
                cur.execute("UPDATE subscriptions SET status=? WHERE stripe_id=?", (status, sid))
                conn.commit()
        elif etype == 'invoice.payment_failed':
            # optionally mark subscription in DB as past_due
            sid = data.get('subscription')
            if sid:
                cur.execute("UPDATE subscriptions SET status=? WHERE stripe_id=?", ('past_due', sid))
                conn.commit()
        conn.close()
        return {"received": True}
    except Exception:
        logger.exception("Failed to process stripe webhook")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@app.post("/api/disputes")
def create_dispute(payload: dict, admin=Depends(require_jwt_admin)):
    """Create a dispute protection report from provided evidence.

    Payload keys: `customer_id`, `title`, `evidence` (dict with screenshots/comments/timestamps/messages/meeting_logs)
    Returns created report id and generated timeline / recommended steps.
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")
    customer_id = payload.get('customer_id')
    title = payload.get('title', 'Dispute Report')
    evidence = payload.get('evidence', {})
    import uuid
    rid = str(uuid.uuid4())
    ts = int(time.time())

    # naive timeline generation: sort events by timestamp if available
    timeline = []
    try:
        events = evidence.get('events', []) if isinstance(evidence, dict) else []
        timeline = sorted(events, key=lambda e: e.get('timestamp', 0))
    except Exception:
        timeline = []

    # recommended HR steps (simple heuristic)
    recommended = []
    if any('harass' in (m.get('text','').lower()) for m in evidence.get('messages', []) if isinstance(evidence.get('messages', []), list)):
        recommended.append('Immediate HR review for harassment')
    else:
        recommended.append('Document and monitor; schedule manager conversation')

    conn = get_conn()
    cur = conn.cursor()
    # guard: ensure dispute_reports table exists
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS dispute_reports (
            id TEXT PRIMARY KEY,
            customer_id TEXT,
            title TEXT,
            evidence_json TEXT,
            timeline_json TEXT,
            recommended_steps TEXT,
            created_ts INTEGER
        )
        """
    )
    cur.execute("INSERT INTO dispute_reports (id, customer_id, title, evidence_json, timeline_json, recommended_steps, created_ts) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (rid, customer_id, title, json.dumps(evidence), json.dumps(timeline), json.dumps(recommended), ts))
    conn.commit()
    conn.close()
    return {"id": rid, "timeline": timeline, "recommended_steps": recommended}


@app.get("/api/disputes/{report_id}")
def get_dispute(report_id: str, admin=Depends(require_jwt_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, customer_id, title, evidence_json, timeline_json, recommended_steps, created_ts FROM dispute_reports WHERE id=?", (report_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail='Report not found')
    r = dict(row)
    r['evidence'] = json.loads(r.pop('evidence_json') or '{}')
    r['timeline'] = json.loads(r.pop('timeline_json') or '[]')
    r['recommended_steps'] = json.loads(r.pop('recommended_steps') or '[]')
    return r


@app.post("/api/insights")
def run_insights(payload: dict, admin=Depends(require_jwt_admin)):
    """Run lightweight productivity intelligence. Payload may include `account_id` and `data`.

    Returns mock `output_scores`, `time_allocation`, `bottlenecks`, `workload_forecast`.
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail='Invalid payload')
    account_id = payload.get('account_id')
    data = payload.get('data', {})
    import uuid
    iid = str(uuid.uuid4())
    ts = int(time.time())

    # Mock analysis logic
    output_scores = { 'efficiency': 0.8, 'focus': 0.7 }
    time_allocation = { 'meetings_pct': 0.35, 'deep_work_pct': 0.4, 'administrative_pct': 0.25 }
    bottlenecks = [ { 'area': 'PR review', 'impact': 'high' } ]
    workload_forecast = { 'next_30_days': 'increasing' }

    summary = {
        'output_scores': output_scores,
        'time_allocation': time_allocation,
        'bottlenecks': bottlenecks,
        'workload_forecast': workload_forecast,
    }

    conn = get_conn()
    cur = conn.cursor()
    # guard: ensure insights_results table exists
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS insights_results (
            id TEXT PRIMARY KEY,
            account_id TEXT,
            payload_json TEXT,
            summary_json TEXT,
            created_ts INTEGER
        )
        """
    )
    cur.execute("INSERT INTO insights_results (id, account_id, payload_json, summary_json, created_ts) VALUES (?, ?, ?, ?, ?)", (iid, account_id, json.dumps(data), json.dumps(summary), ts))
    conn.commit()
    conn.close()
    return { 'id': iid, 'summary': summary }


# Simple AI coach templates (no DB required)
COACH_TEMPLATES = [
    {
        'id': 'performance_concern',
        'title': 'Discussing performance concerns',
        'examples': {
            'neutral': 'I wanted to talk about some recent observations regarding your performance...',
            'ada_safe': 'I want to ensure we provide any accommodations you may need while discussing performance...',
            'deescalation': 'I value your contributions; can we discuss ways to better support you?'
        }
    },
]


@app.get('/api/coach/templates')
def list_coach_templates(admin=Depends(require_jwt_admin)):
    return {'templates': COACH_TEMPLATES}


@app.post("/api/payment/webhook")
async def stripe_webhook(request):
    """Stripe webhook endpoint. Protect with `STRIPE_WEBHOOK_SECRET` if configured.

    This will verify the signature if `STRIPE_WEBHOOK_SECRET` is set in env.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature") or request.headers.get("Stripe-Signature")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    stripe.api_key = os.environ.get("STRIPE_SECRET")

    event = None
    try:
        if webhook_secret and sig_header:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            # If no secret configured, parse payload directly (not recommended for prod)
            event = stripe.Event.construct_from(json.loads(payload.decode("utf-8")), stripe.api_key)
    except Exception as e:
        logger.exception("Webhook signature verification failed")
        raise HTTPException(status_code=400, detail=f"Webhook error: {str(e)}")

    # Handle event types you care about
    etype = getattr(event, 'type', None) or event.get('type')
    logger.info("Received Stripe event: %s", etype)
    # For example, update subscription status on subscription events
    try:
        if etype == 'payment_intent.succeeded':
            PAGE_VIEW_COUNTER.inc()
        if etype in ('customer.subscription.created', 'customer.subscription.updated'):
            data = event.get('data', {}).get('object', {})
            sid = data.get('id')
            status = data.get('status')
            price = None
            # attempt to extract price amount
            items = data.get('items', {}).get('data', []) if isinstance(data.get('items'), dict) else data.get('items', [])
            if items and isinstance(items, list):
                first = items[0]
                price = first.get('price', {}).get('unit_amount')
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("UPDATE subscriptions SET status=?, price_cents=? WHERE stripe_id=?", (status, price, sid))
            conn.commit()
            conn.close()
        if etype == 'customer.created':
            data = event.get('data', {}).get('object', {})
            cid = data.get('id')
            email = data.get('email')
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO customers (id, email, stripe_id) VALUES (?, ?, ?)", (cid, email, cid))
            conn.commit()
            conn.close()
    except Exception:
        pass

    return {"received": True}
