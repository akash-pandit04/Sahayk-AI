import socket
import ipaddress
import httpx
from urllib.parse import urlparse
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

def is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            return False
            
        hostname = parsed.hostname
        if not hostname:
            return False
            
        # Resolve IP
        ip = socket.gethostbyname(hostname)
        ip_obj = ipaddress.ip_address(ip)
        
        # Block private, loopback, and reserved IPs
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved:
            return False
            
        return True
    except Exception as e:
        logger.warning(f"URL validation failed for {url}: {e}")
        return False

async def fetch_url(url: str) -> tuple[bytes, str]:
    """
    Fetches a URL safely. 
    Returns a tuple of (content_bytes, content_type)
    """
    if not is_safe_url(url):
        raise HTTPException(status_code=400, detail="Invalid or unsafe URL. Internal/Private IPs are not allowed.")
        
    try:
        async with httpx.AsyncClient(follow_redirects=True, max_redirects=3) as client:
            response = await client.get(url, timeout=15.0)
            
            # Check the final URL after redirects for SSRF safety as well
            if not is_safe_url(str(response.url)):
                raise HTTPException(status_code=400, detail="Redirected to unsafe URL.")
                
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            return response.content, content_type
    except httpx.RequestError as e:
        logger.error(f"Error fetching {url}: {e}")
        raise HTTPException(status_code=400, detail=f"Error fetching URL: {str(e)}")
