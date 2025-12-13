import base64
import requests
import os
import html
import re
import time
import datetime
import google.generativeai as genai
from flask import Flask, Response, request

app = Flask(__name__)

# ===========================
#        CONFIGURATION
# ===========================
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

CACHE = {} 
HEADERS = {'User-Agent': 'HyperBadge/v24-StaticServer'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# ===========================
#      HELPER FUNCTIONS
# ===========================

def sanitize_xml(text):
    if not text: return ""
    text = str(text)
    # Remove control chars (ASCII 0-31) except newline/tab
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return html.escape(text, quote=True)

def get_base64(url):
    if not url: return EMPTY
    try:
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(r.content).decode('utf-8')}"
    except:
        pass
    return EMPTY

def get_css(master_anim, bg_anim, fg_anim):
    css = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Rajdhani:wght@500;700&amp;family=Fredoka:wght@400;600;700&amp;family=Pacifico&amp;family=Outfit:wght@400;700;900&amp;family=Fira+Code:wght@500&amp;display=swap');"
    
    keyframes = """
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    @keyframes d { from{transform:rotate(0deg) scale(1.1)} to{transform:rotate(360deg) scale(1.1)} }
    @keyframes f { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-4px)} }
    @keyframes p { 50%{opacity:0.5} }
    @keyframes b { 50%{transform:translateY(-5px)} }
    @keyframes s { from {transform:translateY(0)} to {transform:translateY(-40px)} }
    @keyframes sl { 0% {transform:translateY(-100%)} 100% {transform:translateY(100%)} }
    @keyframes hov { 0%,100%{transform:translateY(0) rotate(0deg)} 50%{transform:translateY(-5px) rotate(0.5deg)} }
    @keyframes bf { to { stroke-dashoffset: -400; } }
    @keyframes m1 { 0%{cx:50px; cy:50px} 50%{cx:400px; cy:150px} 100%{cx:50px; cy:50px} }
    @keyframes m2 { 0%{cx:400px; cy:150px} 50%{cx:50px; cy:50px} 100%{cx:400px; cy:150px} }
    """

    m_on = str(master_anim).lower() == 'true'
    bg_on = str(bg_anim).lower() == 'true' and m_on
    fg_on = str(fg_anim).lower() == 'true' and m_on

    # Master switch OFF
    if not m_on: return css + keyframes + " * { animation: none !important; transition: none !important; }"

    classes = ""
    if fg_on:
        classes += ".float {animation: f 6s ease-in-out infinite;} .pulse {animation: p 2s infinite;} .bob {animation: b 3s ease-in-out infinite;} .hover-panel {animation: hov 8s ease-in-out infinite;} .hover-panel-2 {animation: hov 8s ease-in-out infinite reverse;} .disc-spin {animation: spin 10s linear infinite;} .cursor {animation: p 1s step-end infinite;}"
    if bg_on:
        classes += ".drift {animation: d 40s linear infinite; transform-origin: center;} .scroll-bg {animation: s 20s linear infinite;} .scanline {animation: sl 4s linear infinite;} .flow-border {animation: bf 4s linear infinite; stroke-dasharray: 200;} .mesh-ball-1 {animation: m1 20s infinite ease-in-out;} .mesh-ball-2 {animation: m2 25s infinite ease-in-out;}"
        
    return css + keyframes + classes

# ===========================
#        AI NEURAL CORE
# ===========================

def consult_gemini(status_text, user_name, mode, enabled, data_type):
    if str(enabled).lower() == 'false': return None
    if not GOOGLE_API_KEY: return None 
    
    key = f"AI_{user_name}_{status_text}_{mode}"
    if key in CACHE: return CACHE[key]

    try:
        model = genai.GenerativeModel('gemini-pro')
        
        if mode == "roast":
            prompt = f"Roast '{user_name}' about: '{status_text}'. Savage, uppercase, max 7 words."
        else:
            ctx = "Activity"
            if data_type == "github": ctx = "GitHub"
            if data_type == "discord": ctx = "Server"
            prompt = f"{ctx} for '{user_name}': '{status_text}'. Cool sci-fi HUD status. Uppercase. Max 6 words."

        response = model.generate_content(prompt)
        text = sanitize_xml(response.text.strip().replace('"','').replace("'", "")).upper()[:50]
        CACHE[key] = text
        return text
    except:
        return "DATA ENCRYPTED"

# ===========================
#       DATA HARVESTERS
# ===========================

def fetch_data(key, type_mode, args):
    try:
        force_name = args.get('name')
        custom_idle = args.get('idleMessage', 'IDLE')

        # --- 1. DISCORD INVITE (Static Mode Logic Trigger) ---
        if type_mode == 'discord':
            r = requests.get(f"https://discord.com/api/v10/invites/{key}?with_counts=true", headers=HEADERS, timeout=4)
            d = r.json()
            g = d.get('guild')
            if not g: return None
            
            # Using new sanitize
            name = sanitize_xml(g.get('name', 'Server'))
            
            try: 
                l1_txt = "MEMBERS"
                # Using comma separation
                l2_txt = f"{d['approximate_member_count']:,}"
                sub_status = f"{d.get('approximate_presence_count', 0):,} ONLINE"
            except:
                l1_txt = "STATUS"
                l2_txt = "ONLINE"
                sub_status = ""

            final_name = force_name if force_name else name

            return {
                "type": "discord",
                "name": final_name,
                "l1": l1_txt,
                "l2": l2_txt,
                "sub_status": sub_status, # Passed to logic
                "color": "#5865F2", 
                "avatar": get_base64(f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png") if g.get('icon') else EMPTY,
                "album_art": None, "is_music": False, "progress": 0, "id": g.get('id','0')
            }

        # --- 2. GITHUB ---
        elif type_mode == 'github':
            # REPO
            if '/' in key:
                r = requests.get(f"https://api.github.com/repos/{key}", headers=HEADERS, timeout=4)
                d = r.json()
                if 'id' not in d: return None
                
                stars = d.get('stargazers_count', 0)
                forks = d.get('forks_count', 0)
                rank = "SSS" if stars > 5000 else "A" if stars > 1000 else "B"
                title = force_name if force_name else d['name']
                
                return {
                    "type": "github", "name": sanitize_xml(title),
                    "l1": f"RANK: {rank}", "l2": f"★ {stars}  ⑂ {forks}",
                    "color": "#FFF", "avatar": get_base64(d['owner']['avatar_url']),
                    "album_art": None, "is_music": False, "progress": 0, "id": str(d['id'])
                }
            # USER
            else:
                r = requests.get(f"https://api.github.com/users/{key}", headers=HEADERS, timeout=4)
                d = r.json()
                if 'login' not in d: return None
                title = force_name if force_name else d['login']
                return {
                    "type": "github", "name": sanitize_xml(title),
                    "l1": "REPOS / GISTS", "l2": f"{d.get('public_repos',0)} / {d.get('public_gists',0)}",
                    "color": "#FFF", "avatar": get_base64(d.get('avatar_url')),
                    "album_art": None, "is_music": False, "progress": 0, "id": str(d.get('id',0))
                }

        # --- 3. LANYARD (USER) ---
        else:
            r = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            d = r.json().get('data', {})
            if not d: return None
            
            u = d['discord_user']
            status = d['discord_status']
            
            # Name Logic
            real_name = u['username']
            if args.get('showDisplayName', 'true').lower() == 'true' and u.get('global_name'):
                real_name = u['global_name']
            
            final_name = force_name if force_name else real_name
            
            # Colors
            l1, l2, col = "", "", "#555"
            is_music, art, progress = False, None, 0.0
            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#FF4444", "offline": "#555", "spotify": "#1DB954"}
            
            # Spotify Logic
            if d.get('spotify'):
                s = d['spotify']
                l1 = f"🎵 {s['song']}"
                l2 = f"By {s['artist']}"
                col = cols['spotify']
                is_music = True
                art = get_base64(s.get('album_art_url'))
                try:
                    now = time.time() * 1000
                    total = s['timestamps']['end'] - s['timestamps']['start']
                    curr = now - s['timestamps']['start']
                    progress = min(max((curr/total)*100, 0), 100)
                except: progress = 0
            else:
                col = cols.get(status, "#555")
                found = False
                for act in d.get('activities', []):
                    if act['type'] == 0: l1="PLAYING:"; l2=act['name']; found=True; break
                    if act['type'] == 4: l1="NOTE:"; l2=act.get('state',''); found=True; break
                    if act['type'] == 2: l1="MEDIA:"; l2="Stream"; found=True; break
                
                if not found:
                    l1="STATUS:"; l2="ONLINE" if status=="online" else custom_idle.upper()

            return {
                "type": "user",
                "name": sanitize_xml(final_name),
                "l1": sanitize_xml(l1)[:35], 
                "l2": sanitize_xml(l2)[:40],
                "color": col, 
                "avatar": get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png"),
                "album_art": art, 
                "is_music": is_music, 
                "progress": progress, 
                "id": u['id']
            }
    except:
        return None

# ===========================
#      STYLES
# ===========================

def render_chillax(d, ai_msg, css, radius, bg_arg):
    # Darkened for visibility
    bg = bg_arg if bg_arg else "18191c"
    
    if d['album_art']:
        bg_art = f'<image href="{d["album_art"]}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" opacity="0.6" filter="url(#heavyBlur)"/><rect width="100%" height="100%" fill="black" opacity="0.5"/>'
    else:
        bg_art = f"""<rect width="100%" height="100%" fill="#{bg}"/><circle cx="50" cy="50" r="100" fill="#00CFFF" class="mesh-ball-1" opacity="0.4" filter="url(#blur)"/><circle cx="430" cy="130" r="120" fill="#FF00FF" class="mesh-ball-2" opacity="0.4" filter="url(#blur)"/>"""

    # Extra Discord Info line if available (Online count)
    extra = ""
    if d['type'] == 'discord' and 'sub_status' in d:
        extra = f'<text x="315" y="19" text-anchor="end" class="ui-font" font-size="9" fill="{d["color"]}">{d["sub_status"]}</text>'

    ai_element = ""
    if ai_msg:
        ai_element = f"""<g transform="translate(130, 95)" class="hover-panel" style="animation-delay:0.3s"><rect width="320" height="30" rx="8" fill="rgba(0,0,0,0.5)" stroke="rgba(255,255,255,0.15)"/><text x="15" y="19" font-family="JetBrains Mono" font-size="10" fill="{d['color']}">{ai_msg}<tspan class="cursor">_</tspan></text></g>"""

    return f"""<svg width="480" height="150" viewBox="0 0 480 150" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css}.script-font {{ font-family: 'Pacifico', cursive; }}.ui-font {{ font-family: 'Fredoka', sans-serif; }}.mono {{ font-family: 'JetBrains Mono', monospace; }}</style><clipPath id="card"><rect width="480" height="150" rx="{radius}"/></clipPath><clipPath id="circleAv"><circle cx="50" cy="50" r="45"/></clipPath><filter id="blur"><feGaussianBlur stdDeviation="35"/></filter><filter id="heavyBlur"><feGaussianBlur stdDeviation="10"/></filter><filter id="tShadow"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#000" flood-opacity="0.8"/></filter></defs>
      <g clip-path="url(#card)">{bg_art}<pattern id="g" width="20" height="20" patternUnits="userSpaceOnUse"><rect width="1" height="1" fill="white" opacity="0.1"/></pattern><rect width="100%" height="100%" fill="url(#g)"/><linearGradient id="v" x1="0" x2="1"><stop offset="0%" stop-color="black" stop-opacity="0.4"/><stop offset="50%" stop-color="black" stop-opacity="0"/><stop offset="100%" stop-color="black" stop-opacity="0.4"/></linearGradient><rect width="100%" height="100%" fill="url(#v)"/></g>
      <g transform="translate(30, 25)"><circle cx="50" cy="50" r="48" fill="none" stroke="{d['color']}" stroke-width="3" stroke-dasharray="10 8" opacity="0.7" class="disc-spin"/><g clip-path="url(#circleAv)"><image href="{d['avatar']}" width="100" height="100"/></g><circle cx="85" cy="85" r="9" fill="{d['color']}" stroke="#{bg}" stroke-width="3"/></g>
      <g transform="translate(145, 30)"><text x="0" y="15" class="script-font" font-size="34" fill="white" filter="url(#tShadow)">! {d['name']}</text><text x="220" y="12" font-size="18">🌸 🍦 🤍</text><g transform="translate(-5, 30)"><rect width="320" height="28" rx="6" fill="rgba(255,255,255,0.15)"/><text x="10" y="19" class="ui-font" font-weight="700" font-size="13" fill="#FFF" filter="url(#tShadow)"><tspan fill="{d['color']}" font-weight="900">></tspan> {d['l1']} {d['l2']}</text>{extra}</g></g>{ai_element}<text x="470" y="145" text-anchor="end" class="mono" font-size="9" fill="rgba(255,255,255,0.4)">ID :: {d['id']}</text></svg>"""

# 2. SPOTIFY PLAYER
def render_spotify(d, ai_msg, css, radius, bg):
    img = d['album_art'] if d['album_art'] else d['avatar']
    ai_html = f'<text x="120" y="70" class="m" font-size="10" fill="#E0E0FF" opacity="0.7">AI // {ai_msg}</text>' if ai_msg else ""
    p_width = (d['progress'] / 100.0) * 440
    return f"""<svg width="480" height="150" viewBox="0 0 480 150" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><defs><style>{css}.u {{ font-family: 'Rajdhani', sans-serif; }} .m {{ font-family: 'JetBrains Mono', monospace; }}</style><clipPath id="cp"><rect width="480" height="150" rx="{radius}"/></clipPath><clipPath id="ac"><rect width="100" height="100" rx="8"/></clipPath><filter id="bl"><feGaussianBlur stdDeviation="15"/></filter></defs><rect width="100%" height="100%" rx="{radius}" fill="#{bg}"/><g clip-path="url(#cp)"><image href="{img}" width="480" height="480" x="0" y="-165" opacity="0.3" filter="url(#bl)"/><rect width="100%" height="100%" fill="black" opacity="0.2"/></g><g transform="translate(20, 20)"><g class="float"><g clip-path="url(#ac)"><image href="{img}" width="100" height="100"/></g><rect width="100" height="100" rx="10" fill="none" stroke="rgba(255,255,255,0.1)"/>{'<circle cx="50" cy="50" r="20" fill="none" stroke="white" stroke-dasharray="10 5" opacity="0.5" class="disc-spin"/>' if d['is_music'] else ''}</g><g transform="translate(115, 10)"><text class="u" font-size="10" font-weight="bold" fill="#bbb" letter-spacing="2">NOW PLAYING</text><text y="28" class="u" font-size="24" font-weight="bold" fill="white">{d['l1']}</text><text y="50" class="m" font-size="12" fill="{d['color']}">{d['l2']}</text><text y="70" class="m" font-size="10" fill="#999">User: {d['name']}</text>{ai_html}</g></g><g transform="translate(20, 135)"><rect width="440" height="4" rx="2" fill="rgba(255,255,255,0.15)"/><rect width="{p_width}" height="4" rx="2" fill="{d['color']}"/></g></svg>"""

# 3. EASTER EGG (macOS)
def render_easteregg(d, ai_msg, css, radius):
    bg_el = f'<image href="{d["album_art"]}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" opacity="0.6" filter="url(#heavyBlur)"/><rect width="100%" height="100%" fill="black" opacity="0.6"/>' if d['album_art'] else f"""<rect width="100%" height="100%" fill="#050505"/><circle r="120" fill="{d['color']}" class="mesh-1" opacity="0.6" filter="url(#flowBlur)"/><circle r="150" fill="#5865F2" class="mesh-2" opacity="0.5" filter="url(#flowBlur)"/><circle r="100" fill="#00FFFF" class="mesh-3" opacity="0.4" filter="url(#flowBlur)"/>"""
    ai_html = f"""<g transform="translate(130, 20)" class="hover-panel-2"><rect width="220" height="24" rx="12" fill="black" stroke="rgba(255,255,255,0.15)"/><text x="110" y="16" text-anchor="middle" font-family="JetBrains Mono" font-size="9" fill="#EEE"><tspan fill="{d['color']}">●</tspan> {ai_msg}</text></g>""" if ai_msg else ""
    return f"""<svg width="480" height="180" viewBox="0 0 480 180" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><defs><style>{css}</style><filter id="heavyBlur"><feGaussianBlur stdDeviation="15"/></filter><filter id="flowBlur"><feGaussianBlur stdDeviation="30"/><feComposite in="SourceGraphic" operator="over"/></filter><clipPath id="main"><rect width="480" height="180" rx="{radius}"/></clipPath><clipPath id="sq"><path d="M 20,0 H 80 C 100,0 100,20 100,20 V 80 C 100,100 80,100 80,100 H 20 C 0,100 0,80 0,80 V 20 C 0,0 20,0 20,0 Z" /></clipPath><linearGradient id="rb"><stop offset="0%" stop-color="{d['color']}"/><stop offset="50%" stop-color="#00FFFF"/><stop offset="100%" stop-color="{d['color']}"/></linearGradient></defs><g clip-path="url(#main)">{bg_el}<pattern id="gn" width="100" height="100" patternUnits="userSpaceOnUse"><rect width="1" height="1" fill="white" opacity="0.05"/></pattern><rect width="100%" height="100%" fill="url(#gn)"/></g><rect x="2" y="2" width="476" height="176" rx="{radius}" fill="none" stroke="url(#rb)" stroke-width="4" class="flow-border" opacity="0.8"/><g transform="translate(20, 20)"><circle cx="0" cy="0" r="5" fill="#FF5F56"/><circle cx="15" cy="0" r="5" fill="#FFBD2E"/><circle cx="30" cy="0" r="5" fill="#27C93F"/></g>{ai_html}<g transform="translate(25, 50)" class="hover-panel"><rect x="5" y="5" width="100" height="100" rx="20" fill="black" opacity="0.3"/><g clip-path="url(#sq)"><image href="{d['avatar']}" width="100" height="100"/><path d="M 0,0 L 100,0 L 0,100 Z" fill="white" opacity="0.1"/></g><path d="M 20,0 H 80 C 100,0 100,20 100,20 V 80 C 100,100 80,100 80,100 H 20 C 0,100 0,80 0,80 V 20 C 0,0 20,0 20,0 Z" fill="none" stroke="rgba(255,255,255,0.4)" stroke-width="2"/></g><g transform="translate(145, 60)" class="float" style="animation-delay:0.2s"><text x="0" y="0" font-family="Outfit" font-weight="900" font-size="34" fill="white">{d['name']}</text><g transform="translate(0, 15)"><text x="0" y="20" font-family="JetBrains Mono" font-weight="800" font-size="13" fill="{d['color']}" filter="url(#textGlow)" letter-spacing="1">>> {d['l1'].upper()}</text><text x="0" y="40" font-family="Outfit" font-weight="700" font-size="14" fill="#EEE">{d['l2']}</text></g></g></svg>"""

# 4. HYPER (Liquid)
def render_hyper(d, ai_msg, css, radius, bg):
    hex_path = "M50 0 L93.3 25 V75 L50 100 L6.7 75 V25 Z"
    ai_svg = f"""<g transform="translate(145,120)" class="float" style="animation-delay:0.5s"><rect width="310" height="35" rx="6" fill="rgba(0,0,0,0.5)" stroke="rgba(255,255,255,0.1)"/><text x="15" y="23" font-family="Rajdhani" font-size="13" fill="#E0E0FF"><tspan fill="#5865F2" font-weight="bold">AI //</tspan> {ai_msg}<tspan class="pulse">_</tspan></text></g>""" if ai_msg else ""
    bg_layer = f'<image href="{d["album_art"]}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" opacity="0.4" filter="url(#bl)"/>' if d['album_art'] else f'<g class="drift" opacity="0.4"><circle cx="20" cy="20" r="160" fill="{d["color"]}" filter="url(#liq)"/><circle cx="450" cy="160" r="140" fill="#5865F2" filter="url(#liq)"/></g>'
    return f"""<svg width="480" height="180" viewBox="0 0 480 180" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><defs><style>{css}.u {{ font-family: 'Rajdhani', sans-serif; }} .m {{ font-family: 'JetBrains Mono', monospace; }}</style><filter id="liq"><feTurbulence type="fractalNoise" baseFrequency="0.015"/><feDisplacementMap in="SourceGraphic" scale="30"/></filter><filter id="bl"><feGaussianBlur stdDeviation="10"/></filter><clipPath id="cc"><rect width="480" height="180" rx="{radius}"/></clipPath><clipPath id="hc"><path d="{hex_path}"/></clipPath></defs><rect width="100%" height="100%" rx="{radius}" fill="#{bg}"/><g clip-path="url(#cc)">{bg_layer}<rect width="100%" height="100%" fill="black" opacity="0.1"/></g><g transform="translate(25,40)"><path d="{hex_path}" fill="{d['color']}" opacity="0.2" transform="translate(0,3)"/><g clip-path="url(#hc)"><image href="{d['avatar']}" width="100" height="100"/></g><path d="{hex_path}" fill="none" stroke="{d['color']}" stroke-width="3"/></g><g transform="translate(145,55)" class="float"><text y="0" class="u" font-size="30" font-weight="700" fill="white" style="text-shadow:0 4px 10px rgba(0,0,0,0.5)">{d['name'].upper()}</text><text y="25" class="m" font-size="12" fill="{d['color']}">>> {d['l1']}</text><text y="42" class="m" font-size="11" fill="#ccc">{d['l2']}</text></g>{ai_svg}<text x="470" y="170" text-anchor="end" class="m" font-size="8" fill="#555">UID: {d['id']}</text></svg>"""

# 5. CUTE 
def render_cute(d, ai_msg, css, bg):
    c = d['color']
    ai_svg = f"""<g transform="translate(0,60)" class="bob"><rect width="280" height="30" rx="15" fill="white" opacity="0.8" stroke="{c}" stroke-width="1"/><text x="15" y="19" font-family="Fredoka" font-size="11" fill="#888">🐰 {ai_msg.capitalize()}</text></g>""" if ai_msg else ""
    return f"""<svg width="480" height="180" viewBox="0 0 480 180" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><defs><style>{css}</style><pattern id="heart" width="40" height="40" patternUnits="userSpaceOnUse"><text x="0" y="20" font-size="10" opacity="0.1" fill="{c}">❤</text><text x="20" y="40" font-size="10" opacity="0.1" fill="{c}">❤</text></pattern><clipPath id="cr"><circle cx="65" cy="65" r="55"/></clipPath></defs><rect width="480" height="180" rx="30" fill="#FFFAFA"/><rect width="100%" height="100%" fill="url(#heart)" class="scroll-bg"/><rect x="5" y="5" width="470" height="170" rx="25" fill="none" stroke="{c}" stroke-width="4" stroke-dasharray="15 10" opacity="0.4"/><g transform="translate(25,25)"><circle cx="65" cy="65" r="60" fill="{c}"/><circle cx="65" cy="65" r="55" fill="white"/><image href="{d['avatar']}" width="130" height="130" clip-path="url(#cr)"/></g><g transform="translate(170,55)"><text y="0" font-family="Fredoka" font-weight="600" font-size="30" fill="#555">{d['name']}</text><rect y="10" width="220" height="25" rx="12" fill="#F0F0F0"/><text x="10" y="26" font-family="Fredoka" font-size="12" fill="{c}">✨ {d['l1']} {d['l2']}</text>{ai_svg}</g></svg>"""

# 6. TERMINAL
def render_terminal(d, ai_msg, css, bg):
    ai_svg = f"""<text x="15" y="100" fill="#569CD6">ai.query</text><text x="70" y="100" fill="#CE9178">("{d['name']}")</text><text x="15" y="120" fill="#6A9955">// {ai_msg}<tspan class="cursor">_</tspan></text>""" if ai_msg else ""
    return f"""<svg width="480" height="180" viewBox="0 0 480 180" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><defs><style>{css}</style><pattern id="sl" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="black" opacity="0.3"/></pattern></defs><rect width="100%" height="100%" rx="6" fill="#1e1e1e"/><rect width="100%" height="100%" fill="url(#sl)" pointer-events="none"/><rect width="100%" height="25" fill="#252526"/><circle cx="20" cy="12" r="5" fill="#ff5f56"/><circle cx="40" cy="12" r="5" fill="#ffbd2e"/><circle cx="60" cy="12" r="5" fill="#27c93f"/><g transform="translate(15, 45)" font-family="Fira Code" font-size="12"><text y="0" fill="#C586C0">const</text> <text x="40" y="0" fill="#4FC1FF">usr</text> <text x="65" y="0" fill="#D4D4D4">=</text> <text x="80" y="0" fill="#CE9178">"{d['name']}"</text><text y="20" fill="#9CDCFE">usr.status</text> <text x="75" y="20" fill="#D4D4D4">=</text> <text x="90" y="20" fill="#B5CEA8">"{d['l1']} {d['l2']}"</text>{ai_svg}</g><rect y="160" width="100%" height="20" fill="#5865F2"/><text x="10" y="173" font-family="Fira Code" font-size="10" fill="white">NORMAL</text><image href="{d['avatar']}" x="380" y="40" width="80" height="80" opacity="0.9" rx="4"/></svg>"""

# 7. PROFESSIONAL
def render_pro(d, msg, args):
    msg_html = f'<text y="90" font-size="10" fill="#999" font-style="italic">NOTE: {msg}</text>' if msg else ""
    return f"""<svg width="480" height="140" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><defs><clipPath id="s"><rect width="90" height="90" rx="4"/></clipPath></defs><rect width="478" height="138" x="1" y="1" rx="4" fill="#FFFFFF" stroke="#e1e4e8"/><rect width="6" height="138" x="1" y="1" rx="1" fill="{d['color']}"/><g transform="translate(30,25)"><image href="{d['avatar']}" width="90" height="90" clip-path="url(#s)"/><rect width="90" height="90" rx="4" fill="none" stroke="rgba(0,0,0,0.1)"/></g><g transform="translate(140,35)" font-family="Arial, Helvetica, sans-serif"><text y="0" font-weight="bold" font-size="22" fill="#333">{d['name']}</text><text y="30" font-size="11" font-weight="bold" fill="#586069">{d['l1']}</text><text y="45" font-size="11" fill="#586069">{d['l2']}</text><line x1="0" y1="70" x2="300" y2="70" stroke="#eee"/>{msg_html}</g></svg>"""

# ===========================
#        ROUTE HANDLER
# ===========================

@app.route('/superbadge/<key>')
@app.route('/badge/<mode>/<key>')
def handler(key, mode="auto"):
    args = request.args
    target_mode = mode
    if mode == "auto":
        target_mode = 'user' if (key.isdigit() and len(str(key)) > 15) else 'discord'
        
    data = fetch_data(key, target_mode, args)
    if not data: return Response('<svg xmlns="http://www.w3.org/2000/svg" width="300" height="50"><rect width="100%" height="100%" fill="black"/><text x="10" y="30" fill="red" font-family="sans-serif">DATA API ERROR</text></svg>', mimetype="image/svg+xml")

    # Settings
    roast = args.get('roastMode', 'false').lower() == 'true'
    anim_on = args.get('animations', 'true')
    # Specific Controls (Forced Off for Server Type automatically)
    bg_an = args.get('bgAnimations', 'true')
    fg_an = args.get('fgAnimations', 'true')
    
    # HARD DISABLE for Discord Servers to prevent annoyance
    if data.get('type') == 'discord':
        anim_on = 'false'; bg_an = 'false'; fg_an = 'false'

    ai_on = args.get('aifeatures', 'true')
    style = args.get('style', 'hyper').lower()
    
    bg = args.get('bg', '09090b').replace('#','')
    rad = args.get('borderRadius', '20').replace('px', '')

    ai_role = "roast" if roast else "hud"
    ft = f"{data['l1']} {data['l2']}"
    msg = consult_gemini(ft, data['name'], ai_role, ai_on, data.get('type'))
    css = get_css(anim_on, bg_an, fg_an)

    if style == 'chillax': svg = render_chillax(data, msg, css, rad, bg)
    elif style == 'spotify': svg = render_spotify(data, msg, css, rad, bg)
    elif style == 'easteregg': svg = render_easteregg(data, msg, css, rad)
    elif style == 'cute': svg = render_cute(data, msg, css, bg)
    elif style == 'terminal': svg = render_terminal(data, msg, css, bg)
    elif style == 'pro': svg = render_pro(data, msg, args)
    else: svg = render_hyper(data, msg, css, rad, bg)

    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
