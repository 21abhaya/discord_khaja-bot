from urllib.parse import quote


def send_message(message):
    
    """encode the ordersummary and redirect with text to whatsapp 
    initiator's device"""
    
    encoded = quote(message)
    url = f"https://wa.me/9779813946169?text={encoded}"
    return url