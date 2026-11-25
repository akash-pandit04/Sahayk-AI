import pytest
import os
import ipaddress
import socket
from bs4 import BeautifulSoup
from unittest.mock import patch, MagicMock

from app.services.ingestion.fetcher import is_safe_url
from app.services.ingestion.extractor import extract_html, generate_hash

def test_is_safe_url():
    # Valid external urls
    assert is_safe_url("https://www.google.com/") == True
    assert is_safe_url("https://pmkisan.gov.in/") == True
    
    # Internal/SSRF attempting urls
    assert is_safe_url("http://localhost:8000") == False
    assert is_safe_url("http://127.0.0.1") == False
    assert is_safe_url("http://10.0.0.1/admin") == False
    assert is_safe_url("http://192.168.1.100") == False
    
    # Invalid schemes
    assert is_safe_url("ftp://example.com") == False
    assert is_safe_url("file:///etc/passwd") == False

def test_html_extraction():
    html_content = b"""
    <html>
        <head><title>Test</title><style>.hidden { display: none; }</style></head>
        <body>
            <nav>Menu Items</nav>
            <header>Header Content</header>
            <main>
                <h1>Scheme Name</h1>
                <p>This is the important scheme text.</p>
                <script>console.log('Ignore this');</script>
            </main>
            <footer>Footer Links</footer>
        </body>
    </html>
    """
    
    extracted = extract_html(html_content)
    assert "Scheme Name" in extracted
    assert "This is the important scheme text." in extracted
    assert "Menu Items" not in extracted
    assert "Footer Links" not in extracted
    assert "Ignore this" not in extracted
    assert ".hidden" not in extracted

def test_generate_hash():
    text1 = "This is some test content."
    text2 = "This is some test content."
    text3 = "Different content."
    
    hash1 = generate_hash(text1)
    hash2 = generate_hash(text2)
    hash3 = generate_hash(text3)
    
    assert hash1 == hash2
    assert hash1 != hash3

