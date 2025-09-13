import requests
import datetime
from zoneinfo import ZoneInfo

def place_order(customer_name, size_yards, delivery_date, time_slot, prior_ordered, address, parking_instructions,
                surface_protection, contact_info, payment_method):
    N8N_WEBHOOK_URL = "https://vegasdumpster.app.n8n.cloud/webhook/place-order"
    """
    Create a sample dumpster order and send it to n8n webhook.
    """
    order = {
        "id": int((datetime.datetime.now() - datetime.datetime(1970, 1, 1)).total_seconds() * 1000),
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "prior_ordered": prior_ordered,
        "customer_name": customer_name,
        "size_yards": size_yards,
        "delivery_date": delivery_date,
        "time_slot": time_slot,
        "address": address,
        "parking_instructions": parking_instructions,
        "surface_protection": surface_protection,
        "contact_info": contact_info,
        "payment_method": payment_method,
    }

    # Send order to n8n webhook
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=order)
        print("[n8n webhook] Status:", response.status_code)
        print("[n8n webhook] Response:", response.text)
    except Exception as e:
        print("[n8n webhook] Error:", e)

    return order

def swap_service(customer_name, swap_time, time_slot, address, surface_protection, contact_info, payment_method):
    N8N_WEBHOOK_URL = "https://vegasdumpster.app.n8n.cloud/webhook/swap-service"
    """
    Create a sample dumpster order and send it to n8n webhook.
    """
    order = {
        "id": int((datetime.datetime.now() - datetime.datetime(1970, 1, 1)).total_seconds() * 1000),
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "customer_name": customer_name,
        "swap_time": swap_time,        
        "time_slot": time_slot,
        "address": address,
        "surface_protection": surface_protection,
        "contact_info": contact_info,
        "payment_method": payment_method,
    }

    # Send order to n8n webhook
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=order)
        print("[n8n webhook] Status:", response.status_code)
        print("[n8n webhook] Response:", response.text)
    except Exception as e:
        print("[n8n webhook] Error:", e)

    return order

def final_pickup_service(customer_name, address):
    N8N_WEBHOOK_URL = "https://vegasdumpster.app.n8n.cloud/webhook/final-pickup-service"
    """
    Create a sample dumpster order and send it to n8n webhook.
    """
    order = {
        "id": int((datetime.datetime.now() - datetime.datetime(1970, 1, 1)).total_seconds() * 1000),
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "customer_name": customer_name,
        "address": address,
    }

    # Send order to n8n webhook
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=order)
        print("[n8n webhook] Status:", response.status_code)
        print("[n8n webhook] Response:", response.text)
    except Exception as e:
        print("[n8n webhook] Error:", e)

    return order

def extend_rental_service(customer_name, extended_period, address, contact_info, payment_method):
    N8N_WEBHOOK_URL = "https://vegasdumpster.app.n8n.cloud/webhook/extend-rental-service"
    """
    Create a sample dumpster order and send it to n8n webhook.
    """
    order = {
        "id": int((datetime.datetime.now() - datetime.datetime(1970, 1, 1)).total_seconds() * 1000),
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "customer_name": customer_name,
        "extended_period": extended_period,
        "address": address,
        "contact_info": contact_info,
        "payment_method": payment_method,
    }

    # Send order to n8n webhook
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=order)
        print("[n8n webhook] Status:", response.status_code)
        print("[n8n webhook] Response:", response.text)
    except Exception as e:
        print("[n8n webhook] Error:", e)

    return order

def delayed_pickup_service(address):
    N8N_WEBHOOK_URL = "https://vegasdumpster.app.n8n.cloud/webhook/delayed-pickup-service"
    """
    Create a sample dumpster order and send it to n8n webhook.
    """
    order = {
        "id": int((datetime.datetime.now() - datetime.datetime(1970, 1, 1)).total_seconds() * 1000),
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "address": address,
    }

    # Send order to n8n webhook
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=order)
        print("[n8n webhook] Status:", response.status_code)
        print("[n8n webhook] Response:", response.text)
    except Exception as e:
        print("[n8n webhook] Error:", e)

    return order

def get_info(info_type: str):
    info_map = {
        "sizes": "Available sizes: 10, 15, 20, 30, 40 yards. Lowboy available for concrete/rock/dirt.",
        "pricing": "Daily rental: $250–$550 depending on size. Surface protection: $35.",
        "rental_period": "Standard rental period: 7 days. Extensions available.",
        "weight_limits": "Weight limits apply per dumpster size. Extra fees may apply for overweight.",
        "surface_protection": "$35 optional surface protection to protect driveway/yard.",
        "time_slot": "For same-day delivery, orders can only be placed before twelve noon. For other delivery days, available time slots are seven to eleven A.M, nine to one, eleven to three, or one to five P.M."
    }
    return {"info_type": info_type, "info": info_map.get(info_type, "Info not available.")}

def finish_call(client_wants_to_finish: bool):
    """Indicate client wants to finish call. TTS message will be generated by agent."""
    return {
        "call_status": "finished" if client_wants_to_finish else "ongoing",
        "client_wants_to_finish": client_wants_to_finish
    }

FUNCTION_MAP = {
    "place_order": place_order,
    "swap_service": swap_service,
    "final_pickup_service": final_pickup_service,
    "extend_rental_service": extend_rental_service,
    "delayed_pickup_service": delayed_pickup_service,
    "get_info": get_info,
    "finish_call": finish_call,
}
