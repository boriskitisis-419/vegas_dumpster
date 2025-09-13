from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# Load prompt from external file
with open("prompts/inbound_prompt.txt", "r", encoding="utf-8") as f:
    PROMPT = f.read()

pst_time = datetime.now(ZoneInfo("America/Los_Angeles"))
current_hour = pst_time.hour

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
        "keyterms": ["hello", "goodbye"],    
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
              "prior_ordered": { "type": "boolean", "description": "I’d be happy to set it! May I ask if you’ve ordered from us before?" },
              "customer_name": { "type": "string", "description": "Thank you for placing an order with us! Could I start by getting your name, please?" },
              "size_yards": { "type": "string", "description": "Thanks (Customer name)! What size dumpster would you like? We have 10, 15, 20, 30, and 40-yard options available." },
              "delivery_date": { "type": "string", "description": "When would you like the dumpster to be delivered?" },
              "time_slot": { "type": "string", "description": "Which time slot would you like for the dumpster delivery?"},
              "address": { "type": "string", "description": "Delivery address including ZIP code" },
              "parking_instructions": { "type": "string", "description": "Where would you like the dumpster parked?" },
              "surface_protection": { "type": "boolean", "description": "Would you like to add surface protection for $35 extra?" },
              "contact_info": { "type": "string", "description": "Customer phone number/email" },
              "payment_method": { "type": "string", "description": "Payment method (Card Number, CVC, Expiration Date, Billing Address)" },
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
              "customer_name": { "type": "string", "description": "Thank you for placing an order! Could I start by getting your name, please?" },
              "address": { "type": "string", "description": "Swap address including ZIP code" },
              "swap_time": { "type": "string", "description": "Would you like that swapped out today?" },
              "time_slot": { "type": "string", "description": "Which time slot would you like for the dumpster delivery?"},
              "surface_protection": { "type": "boolean", "description": "Would you like to add surface protection for $35 extra?" },
              "contact_info": { "type": "string", "description": "Customer phone number/email" },
              "payment_method": { "type": "string", "description": "Payment method (Card Number, CVC, Expiration Date, Billing Address)" },
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
              "customer_name": { "type": "string", "description": "Thank you very much for placing an order with our services. I need some information to process your order. First, can I have your name please?" },
              "address": { "type": "string", "description": "Final pick up address including ZIP code" },
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
              "customer_name": { "type": "string", "description": "Thank you very much for placing an order with our services. I need some information to process your order. First, can I have your name please?" },
              "address": { "type": "string", "description": "Final pick up address including ZIP code" },
              "extended_period": { "type": "string", "description": "Number of additional rental days" },
              "contact_info": { "type": "string", "description": "Customer phone number/email" },
              "payment_method": { "type": "string", "description": "Payment method (Card Number, CVC, Expiration Date, Billing Address)" },
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
    "speak": {
      "provider": {
        "type": "deepgram",
        "model": "aura-2-luna-en"
      }
    },
    "greeting": "Thank you for calling Vegas Dumpsters, I'm Chris. What can I do for you today?"
  }
}
