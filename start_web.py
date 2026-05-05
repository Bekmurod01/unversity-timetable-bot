import os
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

import uvicorn


def run_fallback_server(port: int, error_text: str) -> None:
    class FallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            body = (
                "Service is running in fallback mode.\n\n"
                "Startup error:\n"
                f"{error_text}\n"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    print(f"Starting fallback HTTP server on 0.0.0.0:{port}")
    HTTPServer(("0.0.0.0", port), FallbackHandler).serve_forever()


def main() -> None:
    port = int(os.environ.get("PORT", 10000))

    print(f"Starting web service on 0.0.0.0:{port}")
    try:
        uvicorn.run("app.api.main:app", host="0.0.0.0", port=port, log_level="critical")
    except Exception:
        error_text = traceback.format_exc()
        print("Uvicorn startup failed; switching to fallback server")
        print(error_text)
        run_fallback_server(port, error_text)


if __name__ == "__main__":
    main()
