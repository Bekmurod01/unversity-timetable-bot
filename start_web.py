import os
import traceback

import uvicorn


def main() -> None:
    port_raw = os.getenv("PORT", "10000")
    try:
        port = int(port_raw)
    except ValueError:
        print(f"Invalid PORT='{port_raw}', defaulting to 10000")
        port = 10000

    print(f"Starting web service on 0.0.0.0:{port}")
    uvicorn.run("app.api.main:app", host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("Fatal startup error in start_web.py")
        traceback.print_exc()
        raise
