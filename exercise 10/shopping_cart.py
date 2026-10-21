from flask import Flask, jsonify, request


app = Flask(__name__)
cart = []


@app.get("/cart")
def get_cart():
    return jsonify(cart)


@app.post("/cart")
def add_to_cart():
    item = request.get_json(silent=True)
    if not isinstance(item, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    item_id = item.get("id")
    name = item.get("name")
    quantity = item.get("quantity")
    if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 1:
        return jsonify({"error": "id must be a positive integer."}), 400
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "name must be a non-empty string."}), 400
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        return jsonify({"error": "quantity must be a positive integer."}), 400

    cart.append({"id": item_id, "name": name.strip(), "quantity": quantity})
    return jsonify(cart), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)
