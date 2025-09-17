from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# Load prompt from external file
with open("prompts/inbound_prompt.txt", "r", encoding="utf-8") as f:
    PROMPT = f.read()

def load_description(file_path):
    path = Path(file_path)
    return path.read_text(encoding="utf-8") if path.exists() else ""

CONFIG = {
  "type": "Settings",
  "audio": {
    "input": {
      "encoding": "mulaw",
      "sample_rate": 8000
    },
    "output": {
      "encoding": "mulaw",
      "sample_rate": 8000,
      "container": "none"
    }
  },
  "agent": {
    "language": "en",
    "listen": {
      "provider": {
        "type": "deepgram",
        "model": "nova-3",
      }
    },
    "think": {
      "provider": {
        "type": "open_ai",
        "model": "gpt-4.1",
        "temperature": 0.7
      },
      "prompt": PROMPT,
      "functions": [
        {
          "name": "place_order",
          "description": load_description("descriptions/place_order.txt"),
          "parameters": {
            "type": "object",
            "properties": {
              "prior_ordered": { "type": "boolean", "description": "Whether the customer has ordered from us before"},
              "customer_name": { "type": "string", "description": "Customer's full name"},
              "size_yards": { "type": "string", "description": "We offer 10, 15, and 20-yard dumpsters for smaller jobs. For bigger projects, choose our 30 or 40-yard options" },
              "delivery_date": { "type": "string", "description": "Requested delivery date" },
              "time_slot": { "type": "string", "description": "Preferred delivery time slot"},
              "address": { "type": "string", "description": "Full delivery address, including ZIP code"},
              "parking_instructions": { "type": "string", "description": "Instructions on where to place the dumpster" },
              "surface_protection": { "type": "boolean", "description": "Whether to add surface protection for $35" },
              "contact_info": { "type": "string", "description": "Customer phone number and email" },
              "payment_method": { "type": "string", "description": "Payment details (card number, CVC, expiration, billing address)" },
            },
            "required": ["prior_ordered", "customer_name", "size_yards", "time_slot", "address", "parking_instructions", "surface_protection", "contact_info", "payment_method"]
          }
        },
        {
          "name": "swap_service",
          "description": load_description("descriptions/swap_service.txt"),
          "parameters": {
            "type": "object",
            "properties": {
              "customer_name": {
                "type": "string",
                "description": "Customer's full name"
              },
              "address": {
                "type": "string",
                "description": "Full swap address, including ZIP code"
              },
              "swap_time": {
                "type": "string",
                "description": "Requested date and time for the swap"
              },
              "time_slot": {
                "type": "string",
                "description": "Preferred time slot for the dumpster delivery"
              },
              "surface_protection": {
                "type": "boolean",
                "description": "Whether to add surface protection for $35"
              },
              "contact_info": {
                "type": "string",
                "description": "Customer phone number or email"
              },
              "payment_method": {
                "type": "string",
                "description": "Payment details (card number, CVC, expiration date, billing address)"
              }
            },
            "required": ["customer_name", "address", "swap_time", "surface_protection", "contact_info", "payment_method",]
          }
        },
        {
          "name": "final_pickup_service",
          "description": load_description("descriptions/final_pickup_service.txt"),
          "parameters": {
            "type": "object",
            "properties": {
              "customer_name": {
                "type": "string",
                "description": "Customer's full name"
              },
              "address": {
                "type": "string",
                "description": "Full address for final pickup, including ZIP code"
              }
            },
            "required": ["customer_name", "address" ]
          }
        },
        {
          "name": "extend_rental_service",
          "description": load_description("descriptions/extend_rental_service.txt"),
          "parameters": {
            "type": "object",
            "properties": {
              "customer_name": {
                "type": "string",
                "description": "Customer's full name"
              },
              "address": {
                "type": "string",
                "description": "Full address for pickup, including ZIP code"
              },
              "extended_period": {
                "type": "string",
                "description": "Number of additional rental days requested"
              },
              "contact_info": {
                "type": "string",
                "description": "Customer phone number or email"
              },
              "payment_method": {
                "type": "string",
                "description": "Payment details (card number, CVC, expiration date, billing address)"
              }
            },

            "required": ["address", "customer_name", "extended_period", "contact_info","payment_method"]
          }
        },
        {
          "name": "delayed_pickup_service",
          "description": load_description("descriptions/delayed_pickup_service.txt"),
          "parameters": {
            "type": "object",
            "properties": {
              "address": { "type": "string", "description": "Delayed pick up address including ZIP code" },
            },
            "required": ["address"]
          }
        },
        {
          "name": "get_info",
          "description": "Provide general info about dumpster rentals: sizes, pricing, rental periods, weight limits, or surface protection.",
          "parameters": {
            "type": "object",
            "properties": {
              "info_type": { "type": "string", "enum": ["sizes", "pricing", "rental_period", "weight_limits", "surface_protection"] }
            },
            "required": ["info_type"]
          }
        },
        {
          "name": "finish_call",
          "description": load_description("descriptions/finish_call.txt"),
          "parameters": {
            "type": "object",
            "properties": {
              "client_wants_to_finish": { "type": "boolean", "description":"Did the customer request to finish the call?" }
            },
            "required": ["client_wants_to_finish"]
          }
        },
      ]
    },
    "greeting": "Hello, this is Chris. What can I do for you?"
  }
}
