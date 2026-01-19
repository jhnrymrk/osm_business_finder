from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

BUSINESS_TAGS = {
    "manufacturing": '["industrial"]',
    "technology": '["office"="it"]',
    "warehouse": '["industrial"="warehouse"]',
    "factory": '["man_made"="works"]',
    "restaurant": '["amenity"="restaurant"]',
    "cafe": '["amenity"="cafe"]',
    "hotel": '["tourism"="hotel"]',
    "shop": '["shop"]'
}

def build_query(city, tag):
    return f"""
    [out:json][timeout:25];
    area["name"="{city}"]->.a;
    (
      node{tag}(area.a);
      way{tag}(area.a);
    );
    out center tags;
    """

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search", methods=["POST"])
def search():
    city = request.form.get("location", "").strip()
    selected_types = request.form.get("business_types", "").split(",")

    if not city:
        return jsonify({"error": "City is required"}), 400

    headers = {
        "User-Agent": "OSM-Business-Finder/1.0 (contact@example.com)",
        "Accept": "application/json"
    }

    result = {}

    for btype in selected_types:
        tag = BUSINESS_TAGS.get(btype)
        if not tag:
            continue

        query = build_query(city, tag)

        try:
            response = requests.post(
                OVERPASS_URL,
                data=query,
                headers=headers,
                timeout=30
            )

            if response.status_code != 200 or not response.text.strip():
                result[btype] = []
                continue

            data = response.json()

        except (requests.exceptions.RequestException, ValueError):
            result[btype] = []
            continue

        businesses = []

        for el in data.get("elements", []):
            tags = el.get("tags", {})
            lat = el.get("lat") or el.get("center", {}).get("lat")
            lon = el.get("lon") or el.get("center", {}).get("lon")
            if not lat or not lon:
                continue

            name = tags.get("name")
            if not name:
                continue

            website = tags.get("website", "")

            phone = (
                tags.get("phone")
                or tags.get("contact:phone")
                or tags.get("mobile")
                or tags.get("contact:mobile")
                or ""
            )

            logo = tags.get("logo", "")

            if not logo and website:
                logo = f"https://www.google.com/s2/favicons?domain={website}"

            if not logo:
                logo = "https://via.placeholder.com/50?text=Logo"

            address = tags.get("addr:full") or (
                tags.get("addr:street", "") + ", " + tags.get("addr:city", "")
            )

            business = {
                "name": name,
                "lat": lat,
                "lon": lon,
                "address": address.strip(", "),
                "website": website,
                "phone": phone,
                "logo": logo
            }

            businesses.append(business)

        result[btype] = businesses

    return jsonify(result)

if __name__ == "__main__":
    app.run(host='10.10.111.95', port=5000, debug=True)
