import hashlib
import json
import os
import threading
import time
from urllib.parse import urlparse, quote, unquote
from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
import requests

PORTAL_BASE = "http://91.215.188.161"
PORTAL_URL = f"{PORTAL_BASE}/stalker_portal/server/load.php"

MAC_BASE = "00:1A:79:39:80:9C"
SN_BASE = "420428156A9E4"
UID_BASE = "30DAC1D60ADB0CA2303756C2B420BA2C1D3614520B7CA5D2AA00241598AE9055"
DEVICE_ID = "C6E50B24774620673221A09FDF75789A8B76E581A06073166E126D0AE3F804E6"
SIGNATURE = "8093B01764649C3D8B2024B9B8F72CB47BA2D7B1CCAE5988013AEE59020B5689"
HW_VERSION_2 = "61c3ee11415738e10b26e47bd195df7e23f8b1a0"

SECRET_KEY = "000"  
TELEGRAM_GROUP_URL = "https://t.me/+2lWVU6CKQsVkMWRi"  
STUB_VIDEO_URL = "https://raw.githubusercontent.com/Waswas777/video2/refs/heads/main/playlist.m3u8"
PORTAL_DOMAIN = urlparse(PORTAL_BASE).netloc

BANNED_IPS = {        
        "2a00:1e98:f022:9877:c1ba:4b65:5e85:1c4f", "2a0d:6fc2:5db2:6600:b0b1:70c1:6721:ca58", "2a00:1e98:f2d5:e661:5a0f:182a:60ea:e4cd", 
        "2a02:6ea0:3100:2000:490a:2928:d5eb:e685"    
}
BANNED_PREFIXES = (
    "176.3.", "176.123.", "78.56.", "185.146.", "95.85.", "212.57.", "78.54.", "178.254.", "188.163.", "205.210.31."
)

def is_ip_banned(request: Request) -> bool:
    client_ip = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for")
    if not client_ip and request.client:
        client_ip = request.client.host    
    if not client_ip:
        return False        
    client_ip = client_ip.split(",")[0].strip()
    if client_ip in BANNED_IPS or client_ip.startswith(BANNED_PREFIXES):
        return True        
    return False

def is_browser_request(request: Request) -> bool:
    ua = request.headers.get("user-agent", "").lower()
    if not ua:
        return False
    browser_keywords = ["mozilla", "chrome", "safari", "edge", "opera", "firefox", "androidwebkit"]
    player_keywords = ["televizo", "iptv", "vlc", "kodi", "gst", "ffmpeg", "mag", "stb", "android"]    
    for pk in player_keywords:
        if pk in ua:
            if "android" in ua and ("mobile" in ua or "wv" in ua or "chrome" in ua or "safari" in ua):
                pass
            else:
                return False
    return any(bk in ua for bk in browser_keywords)

app = FastAPI()

global_session = None
session_created_time = 0
memory_playlist_cache = []
cache_time = 0

def get_session(force_new=False):
    global global_session, session_created_time    
    if not force_new and global_session and (time.time() - session_created_time) < 300:
        return global_session        
        
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "X-User-Agent": "Model: MAG250; Link: WiFi",
        "Referer": f"{PORTAL_BASE}/stalker_portal/c/index.html",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
        "Pragma": "no-cache",
    }
    session.headers.update(headers)
    session.cookies.set("mac", MAC_BASE, domain=PORTAL_DOMAIN)
    session.cookies.set("stb_lang", "en", domain=PORTAL_DOMAIN)
    session.cookies.set("timezone", "Europe/London", domain=PORTAL_DOMAIN)
    
    try:
        session.get(f"{PORTAL_BASE}/stalker_portal/c/", timeout=5)
    except Exception:
        pass

    token = ""
    random_val = "22ef3d9929d4689666c71115027b6559cb966b78"
    try:
        hs_url = f"{PORTAL_URL}?type=stb&action=handshake&token=&JsHttpRequest=1-xml"
        r = session.get(hs_url, timeout=10).json()
        js_data = r.get("js", {})
        token = js_data.get("token", "")
        random_val = js_data.get("random", random_val)        
        if token:
            session.cookies.set("token", token, domain=PORTAL_DOMAIN)
            session.headers.update({"Authorization": f"Bearer {token}"})
    except Exception:
        pass

    metrics_data = json.dumps({
        "type": "stb",
        "model": "MAG254",
        "mac": MAC_BASE,
        "sn": SN_BASE,
        "uid": UID_BASE,
        "random": random_val,
    })    
    
    token_param = f"&token={token}" if token else ""
    timestamp = int(time.time())
    
    prof_url = (
        f"{PORTAL_URL}?type=stb&action=get_profile&JsHttpRequest=1-xml&hd=1"
        f"{token_param}"
        "&ver=ImageDescription: 0.2.18-r23-250; ImageDate: Thu Sep 13 11:31:16 EEST 2018; PORTAL version: 5.3.0; API Version: JS API version: 343; STB API version: 146; Player Engine version: 0x58c"
        f"&num_banks=2&sn={SN_BASE}&stb_type=MAG250&client_type=STB&image_version=218&video_out=hdmi"
        f"&device_id={DEVICE_ID}"
        f"&device_id2={DEVICE_ID}"
        f"&signature={SIGNATURE}"
        "&auth_second_step=1&hw_version=1.7-BD-00&not_valid_token=0"
        f"&metrics={metrics_data}"
        f"&hw_version_2={HW_VERSION_2}&timestamp={timestamp}&api_signature=262&prehash=015bbe819626803ef0fe6df45ad6fb000f759aa9"
    )
    
    try:
        session.get(prof_url, timeout=10)
        # Также дергаем account_info для полного соответствия цепочке на скриншоте
        acc_url = f"{PORTAL_URL}?type=account_info&action=get_main_info&JsHttpRequest=1-xml{token_param}"
        session.get(acc_url, timeout=10)
    except Exception:
        pass

    global_session = session
    session_created_time = time.time()
    return session

def fetch_channels_data(session):
    genres_map = {}
    try:
        genres_url = f"{PORTAL_URL}?type=itv&action=get_genres&JsHttpRequest=1-xml"
        g_resp = session.get(genres_url, timeout=10).json()
        g_data = g_resp.get("js", [])
        if isinstance(g_data, list):
            for g in g_data:
                gid = g.get("id")
                gtitle = g.get("title", "Umumiy")
                if gid is not None:
                    genres_map[str(gid)] = gtitle
    except Exception:
        pass

    channels = []
    seen_cmds = set()

    try:
        channels_url = f"{PORTAL_URL}?type=itv&action=get_all_channels&JsHttpRequest=1-xml"
        channels_res = session.get(channels_url, timeout=10).json()
        js_content = channels_res.get("js", {})
        data = js_content.get("data", []) if isinstance(js_content, dict) else (js_content if isinstance(js_content, list) else [])
        if isinstance(data, list):
            for ch in data:
                cmd = ch.get("cmd", "")
                if cmd and cmd not in seen_cmds:
                    seen_cmds.add(cmd)
                    channels.append(ch)
    except Exception:
        pass

    if genres_map:
        for gid in list(genres_map.keys())[:15]:
            page = 1
            while page <= 2:
                sub_url = (
                    f"{PORTAL_URL}?type=itv&action=get_ordered_list"
                    f"&genre={gid}&sortby=number&order=asc&hd=0&fav=0&not_my_genres=0"
                    f"&p={page}&JsHttpRequest=1-xml"
                )
                try:
                    sub_resp = session.get(sub_url, timeout=4).json()
                    js_content = sub_resp.get("js", {})
                    sub_data = js_content.get("data", []) if isinstance(js_content, dict) else (js_content if isinstance(js_content, list) else [])
                    if not sub_data:
                        break
                    added = 0
                    for ch in sub_data:
                        cmd = ch.get("cmd", "")
                        if cmd and cmd not in seen_cmds:
                            seen_cmds.add(cmd)
                            channels.append(ch)
                            added += 1
                    if len(sub_data) < 10 or added == 0:
                        break
                    page += 1
                except Exception:
                    break

    return channels, genres_map

def get_or_create_playlist():
    global memory_playlist_cache, cache_time
    if memory_playlist_cache and (time.time() - cache_time < 3600):
        return memory_playlist_cache

    session = get_session(force_new=False)
    channels, genres_map = fetch_channels_data(session)
    
    if not channels:
        session = get_session(force_new=True)
        channels, genres_map = fetch_channels_data(session)

    channels_list = []
    for ch in channels:
        ch_name = ch.get("name", "Kanal")
        cmd = ch.get("cmd", "")        
        logo = ch.get("logo", "")
        if logo and not logo.startswith("http"):
            logo = f"{PORTAL_BASE}/stalker_portal/misc/logos/{logo}"
        genre_id = str(ch.get("tv_genre_id", ch.get("genre_id", "")))
        group_title = genres_map.get(genre_id, "Umumiy")
        if cmd:
            channels_list.append({
                "name": ch_name,
                "cmd": cmd,
                "group": group_title,
                "logo": logo
            })

    if channels_list:
        memory_playlist_cache = channels_list
        cache_time = time.time()

    return memory_playlist_cache

@app.get("/", response_class=RedirectResponse)
def root_redirect(request: Request):
    if is_ip_banned(request):
        return RedirectResponse(url=STUB_VIDEO_URL, status_code=302)
    return RedirectResponse(url=TELEGRAM_GROUP_URL, status_code=302)

@app.get("/playlist.json")
def download_json(request: Request, key: str = ""):
    if is_ip_banned(request):
        return [{"name": "Reklama", "group": "Stub", "logo": "", "url": STUB_VIDEO_URL}]
        
    if is_browser_request(request):
        return RedirectResponse(url=TELEGRAM_GROUP_URL, status_code=302)

    if key != SECRET_KEY:
        return [{"name": "Reklama", "group": "Stub", "logo": "", "url": STUB_VIDEO_URL}]

    base_url = str(request.base_url).rstrip('/')
    channels = get_or_create_playlist()
    
    result = []
    for ch in channels:
        cmd_encoded = quote(ch["cmd"], safe="")
        result.append({
            "name": ch["name"],
            "group": ch.get("group", "Umumiy"),
            "logo": ch.get("logo", ""),
            "url": f"{base_url}/play?cmd={cmd_encoded}&key={SECRET_KEY}"
        })
    return result

@app.get("/pl.m3u8", response_class=PlainTextResponse)
@app.get("/playlist.m3u8", response_class=PlainTextResponse)
def download_m3u8(request: Request, key: str = ""):
    headers = {"Content-Disposition": "attachment; filename=playlist.m3u8"}    
    
    if is_ip_banned(request):
        content = f"#EXTM3U\n#EXTINF:-1 tvg-name=\"Reklama\" group-title=\"Stub\",Reklama\n{STUB_VIDEO_URL}"
        return PlainTextResponse(content, headers=headers)

    if is_browser_request(request):
        return RedirectResponse(url=TELEGRAM_GROUP_URL, status_code=302)

    if key != SECRET_KEY:
        content = f"#EXTM3U\n#EXTINF:-1 tvg-name=\"Reklama\" group-title=\"Stub\",Reklama\n{STUB_VIDEO_URL}"
        return PlainTextResponse(content, headers=headers)

    base_url = str(request.base_url).rstrip('/')
    channels = get_or_create_playlist()

    m3u_lines = ["#EXTM3U"]
    for ch in channels:
        name = ch.get("name", "Kanal")
        group = ch.get("group", "Umumiy")
        logo = ch.get("logo", "")
        cmd_encoded = quote(ch.get("cmd", ""), safe="")
        stream_link = f"{base_url}/play?cmd={cmd_encoded}&key={SECRET_KEY}"        
        m3u_lines.append(f"#EXTINF:-1 tvg-name=\"{name}\" tvg-logo=\"{logo}\" group-title=\"{group}\",{name}")
        m3u_lines.append(stream_link)

    return PlainTextResponse("\n".join(m3u_lines), headers=headers)

@app.get("/play")
def play_stream(cmd: str, request: Request, key: str = ""):
    if is_ip_banned(request):
        return RedirectResponse(url=STUB_VIDEO_URL, status_code=302)

    if is_browser_request(request):
        return RedirectResponse(url=TELEGRAM_GROUP_URL, status_code=302)

    if key != SECRET_KEY:
        return RedirectResponse(url=STUB_VIDEO_URL, status_code=302)

    session = get_session(force_new=True)
    stream_url = ""    

    clean_cmd = cmd
    for prefix in ["ffmpeg ", "ch:ffrt ", "ffrt ", "ch:"]:
        if clean_cmd.startswith(prefix):
            clean_cmd = clean_cmd[len(prefix):].strip()

    channel_id = ""
    if "/ch/" in clean_cmd:
        parts = clean_cmd.split("/ch/")
        if len(parts) > 1:
            channel_id = parts[-1].strip()

    cmds_to_try = [clean_cmd]
    if channel_id:
        cmds_to_try.insert(0, channel_id)  
        cmds_to_try.append(f"ch:{channel_id}")
        cmds_to_try.append(f"http:///ch/{channel_id}")

    for test_cmd in cmds_to_try:
        for attempt in range(2):
            try:
                link_url = f"{PORTAL_URL}?type=itv&action=create_link&cmd={requests.utils.quote(test_cmd)}&JsHttpRequest=1-xml"
                resp = session.get(link_url, timeout=10)
                link_res = resp.json()
                stream_cmd = link_res.get("js", {}).get("cmd")
                
                if stream_cmd:
                    stream_url = stream_cmd
                    for prefix in ["ffmpeg ", "ch:ffrt ", "ffrt ", "ch:"]:
                        if stream_url.startswith(prefix):
                            stream_url = stream_url[len(prefix):].strip()
                    break
            except Exception:
                if attempt == 0:
                    session = get_session(force_new=True)
                    time.sleep(0.5)
        
        if stream_url and not stream_url.startswith("http:///ch/") and "://" in stream_url:
            break

    if stream_url.startswith("http:///"):
        stream_url = stream_url.replace("http:///", f"{PORTAL_BASE}/")
    elif stream_url.startswith("/"):
        stream_url = f"{PORTAL_BASE}{stream_url}"

    if not stream_url or "://" not in stream_url or stream_url.startswith("http:///ch/"):
        if "://" in clean_cmd and not clean_cmd.startswith("http:///ch/"):
            stream_url = clean_cmd

    if stream_url and "token=" not in stream_url:
        session_token = session.cookies.get("token")
        if session_token:
            separator = "&" if "?" in stream_url else "?"
            stream_url = f"{stream_url}{separator}token={session_token}"

    if not stream_url or stream_url.startswith("http:///ch/"):
        return Response("Kanalni ochib bo'lmadi: медиасервер не вернул ссылку", status_code=500)
    return RedirectResponse(url=stream_url, status_code=302)
