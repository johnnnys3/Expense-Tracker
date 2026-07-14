from flask import jsonify


def require_fields(data, *fields):
    # Callers use `if error := require_fields(data, ...): return error` —
    # None means "valid", anything else is a ready-to-return Flask response.
    if not data:
        return jsonify({"error": "request body must be JSON"}), 400
    missing = [f for f in fields if f not in data]
    if missing:
        return jsonify({"error": f"missing fields: {', '.join(missing)}"}), 400
    return None
