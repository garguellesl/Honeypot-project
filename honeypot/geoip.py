"""
geoip.py
Geolocalización ligera de direcciones IP atacantes usando la API pública
gratuita ip-api.com (sin necesidad de API key, límite ~45 peticiones/min).

Si no hay conexión a internet o se supera el límite, devuelve "Unknown" en
vez de fallar: el honeypot nunca debe caerse por un problema de geolocalización.
"""

import requests

_cache: dict[str, dict] = {}

PRIVATE_PREFIXES = ("10.", "192.168.", "127.", "172.16.", "172.17.", "172.18.")


def lookup(ip: str) -> dict:
    if ip in _cache:
        return _cache[ip]

    if ip.startswith(PRIVATE_PREFIXES):
        result = {"country": "Local/LAN", "city": "-"}
        _cache[ip] = result
        return result

    try:
        resp = requests.get(
            f"http://ip-api.com/json/{ip}?fields=status,country,city",
            timeout=2,
        )
        data = resp.json()
        if data.get("status") == "success":
            result = {"country": data.get("country", "Unknown"), "city": data.get("city", "")}
        else:
            result = {"country": "Unknown", "city": ""}
    except Exception:
        result = {"country": "Unknown", "city": ""}

    _cache[ip] = result
    return result
