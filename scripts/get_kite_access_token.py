import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv
from kiteconnect import KiteConnect

# Load env vars
load_dotenv()

API_KEY = os.getenv("KITE_API_KEY")
API_SECRET = os.getenv("KITE_API_SECRET")
TOKEN_FILE = Path(os.getenv("KITE_ACCESS_TOKEN_PATH", "kite_access_token.txt"))


def main() -> None:
    if not API_KEY or not API_SECRET:
        raise RuntimeError("KITE_API_KEY or KITE_API_SECRET missing in .env")

    # Ensure parent folder exists (e.g. .secrets/)
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)

    kite = KiteConnect(api_key=API_KEY)

    # 1) Generate login URL
    login_url = kite.login_url()

    print("\n=== Kite access token helper ===\n")
    print("1) Open this URL in your browser, log in, and complete 2FA:\n")
    print(login_url)

    print(
        "\n2) After successful login, you will be redirected to your redirect URL "
        "(http://127.0.0.1/?request_token=...&status=success).\n"
        "   Copy the FULL URL from the browser address bar and paste it below.\n"
    )

    redirect_url = input("Paste redirect URL here:\n> ").strip()

    # 3) Extract request_token from the redirect URL
    parsed = urlparse(redirect_url)
    query = parse_qs(parsed.query)
    request_token = query.get("request_token", [None])[0]

    if not request_token:
        print("\nERROR: Could not find request_token in the provided URL.")
        print("Make sure you copied the ENTIRE URL after the browser redirects.")
        return

    print(f"\nRequest token: {request_token}")

    # 4) Exchange request_token for access_token
    session_data = kite.generate_session(request_token, api_secret=API_SECRET)
    access_token = session_data["access_token"]

    print(f"\nAccess token obtained: {access_token}")

    # 5) Save access token to file
    TOKEN_FILE.write_text(access_token, encoding="utf-8")
    print(f"\nSaved access token to: {TOKEN_FILE.resolve()}")
    print("\nYou can now run your main loader script.\n")


if __name__ == "__main__":
    main()