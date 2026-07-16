from app import create_app

# WSGI entrypoint — e.g. `flask run` / gunicorn target this module's `app`.
app = create_app()

if __name__ == "__main__":
    # debug=True only for local dev: enables the reloader and interactive debugger.
    # Port 5000 conflicts with macOS AirPlay Receiver (which squats on it over IPv6).
    app.run(debug=True, port=5001)
