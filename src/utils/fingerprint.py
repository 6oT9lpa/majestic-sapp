import hashlib

def generate_fingerprint(user_agent: str, ip_address: str) -> str:
    """Генерирует уникальный fingerprint пользователя"""
    
    data = f"{user_agent}-{ip_address}"
    return hashlib.sha256(data.encode()).hexdigest()