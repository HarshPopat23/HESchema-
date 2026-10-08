"""Six explicit reference contracts; no real payment/booking endpoints are executed."""

from .schema import DIALECT

STRING = {"type": "string", "minLength": 1}
DATE = {"type": "string", "format": "date"}
DOMAINS = {
    "flights": {
        "tool": "search_flights", "description": "Search flights; never book or pay.",
        "properties": {"origin": STRING, "destination": STRING, "departureDate": DATE,
                       "travellers": {"type": "integer", "minimum": 1, "maximum": 9}},
        "policy": {},
    },
    "hotels": {
        "tool": "search_hotels", "description": "Search hotel rooms; never book or pay.",
        "properties": {"city": STRING, "checkIn": DATE, "checkOut": DATE,
                       "guests": {"type": "integer", "minimum": 1, "maximum": 8},
                       "maxNightlyPrice": {"type": "integer", "minimum": 1, "maximum": 20000}},
        "policy": {"ordered": [["checkIn", "checkOut"]]},
    },
    "calendar": {
        "tool": "prepare_event", "description": "Prepare a meeting draft without sending invitations.",
        "properties": {"title": STRING, "date": DATE,
                       "startTime": {"type": "string", "pattern": "^([01][0-9]|2[0-3]):[0-5][0-9]$"},
                       "durationMinutes": {"type": "integer", "minimum": 5, "maximum": 240},
                       "venue": STRING},
        "policy": {},
    },
    "payments": {
        "tool": "prepare_transfer", "description": "Prepare a transfer quote; never authorize or execute payment.",
        "properties": {"recipient": STRING, "amountMinor": {"type": "integer", "minimum": 1, "maximum": 100000},
                       "currency": {"type": "string", "enum": ["INR", "USD", "EUR"]}, "reference": STRING},
        "policy": {"max": {"amountMinor": 100000}},
    },
    "inventory": {
        "tool": "reserve_stock_draft", "description": "Prepare stock reservation details without mutating inventory.",
        "properties": {"sku": STRING, "warehouse": {"type": "string", "enum": ["DEL", "MUM", "BLR"]},
                       "quantity": {"type": "integer", "minimum": 1, "maximum": 50}, "orderId": STRING},
        "policy": {"max": {"quantity": 50}},
    },
    "search": {
        "tool": "search_web", "description": "Prepare a public web search query; do not disclose credentials.",
        "properties": {"query": STRING, "maxResults": {"type": "integer", "minimum": 1, "maximum": 10},
                       "topic": {"type": "string", "enum": ["general", "news", "finance"]}},
        "policy": {},
    },
}


def reference_schema(domain):
    spec = DOMAINS[domain]
    return {"$schema": DIALECT, "type": "object", "properties": spec["properties"],
            "required": list(spec["properties"]), "additionalProperties": False}
