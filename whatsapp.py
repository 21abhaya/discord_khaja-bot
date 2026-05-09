import os

from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

number = os.getenv('WHATSAPP_NUMBER')


def generate_whatsapp_link(message: str) -> str:
    
    """
    Generate a Whatsapp deep link with the message passed as argument
    """
    
    encoded = quote(message)
    url = f"https://wa.me/{number}?text={encoded}"
    
    return url