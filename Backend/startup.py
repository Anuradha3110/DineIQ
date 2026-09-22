# DineIQ\Backend\startup.py
# ---------------------------------------------------------
# Production credential bootstrap
# ---------------------------------------------------------
# The Google service-account key (dineIQ_service_account.json) is a secret
# and is gitignored, so it only exists on machines where someone has placed
# it manually (local dev). Serverless platforms like Vercel can't have files
# "placed" in the repo — the only way to hand them a secret is an
# environment variable.
#
# The fix: base64-encode the JSON key once, store it as the
# SERVICE_ACCOUNT_JSON_BASE64 env var in the Vercel dashboard, and this
# module decodes it back to a real file on every cold start, before any
# other module (services/sheets.py) tries to open SERVICE_ACCOUNT_FILE.
#
#   # one-time, locally:
#   python -c "import base64; print(base64.b64encode(open('dineIQ_service_account.json','rb').read()).decode())"
#   # paste the output into Vercel -> Settings -> Environment Variables
#   # as SERVICE_ACCOUNT_JSON_BASE64
#
# Local development is unaffected: if SERVICE_ACCOUNT_FILE already points
# at a real file on disk (the normal .env + downloaded-json setup), this
# module does nothing.
#
# main.py imports this module FIRST — before any routers/services — so the
# env var is in place before anything reads it.
# ---------------------------------------------------------

import os
import base64
import tempfile

from dotenv import load_dotenv
load_dotenv()


def _decode_service_account():
    b64 = os.getenv("SERVICE_ACCOUNT_JSON_BASE64")
    if not b64:
        return  # not configured — local dev path, nothing to do

    existing = os.getenv("SERVICE_ACCOUNT_FILE")
    if existing and os.path.isfile(existing):
        # A real key file is already on disk (local dev) — don't touch it.
        return

    try:
        decoded = base64.b64decode(b64)
    except Exception as e:
        print(f"❌ startup.py: could not base64-decode SERVICE_ACCOUNT_JSON_BASE64: {e}")
        return

    # Serverless filesystems (Vercel, Lambda, etc.) only guarantee /tmp is
    # writable, so write there rather than the project directory.
    fd, path = tempfile.mkstemp(prefix="dineIQ_service_account_", suffix=".json")
    with os.fdopen(fd, "wb") as f:
        f.write(decoded)

    os.environ["SERVICE_ACCOUNT_FILE"] = path
    print(f"✅ startup.py: decoded SERVICE_ACCOUNT_JSON_BASE64 -> {path}")


_decode_service_account()
