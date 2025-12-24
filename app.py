import base64
import requests
import os
import html
import re
import time
import math
from flask import Flask, Response, request

app = Flask(__name__)

# ===========================
#        CONFIGURATION
# ===========================
# AI and GitHub Removed for Beta Stats Version
CACHE = {} 
HEADERS = {'User-Agent': 'HyperBadge/Beta-Stats-v1'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# ===========================
#      HELPER FUNCTIONS
# ===========================

def sanitize_xml(text):
    if not text: return ""
    text = str(text)
    # Remove control chars (ASCII 0-31) except tab/newline
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return html.escape(text, quote=True)

def get_base64(url):
    """Safely converts remote images to Base64"""
    if not url: return EMPTY
    try:
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(r.content).decode('utf-8')}"
    except:
        pass
    return EMPTY

def get_css(master_anim, bg_anim, fg_anim):
    # Base Fonts
    css = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Rajdhani:wght@500;700&amp;family=Outfit:wght@500;900&amp;family=Pacifico&amp;family=Fredoka:wght@500;700&amp;family=Fira+Code:wght@500&amp;display=swap');"
    
    keyframes = """
    @keyframes m1 { 0%{cx:10px; cy:10px} 50%{cx:300px; cy:80px} 100%{cx:10px; cy:10px} }
    @keyframes m2 { 0%{cx:400px; cy:100px} 50%{cx:100px; cy:20px} 100%{cx:400px; cy:100px} }
    @keyframes d { from{transform:rotate(0deg) scale(1.1)} to{transform:rotate(360deg) scale(1.1)} }
    @keyframes f { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-3px)} }
    @keyframes p { 50%{opacity:0.6} }
    @keyframes b { 50%{transform:translateY(-5px)} }
    @keyframes s { from {transform:translateY(0)} to {transform:translateY(-40px)} }
    @keyframes sl { 0% {transform:translateY(-100%)} 100% {transform:translateY(100%)} }
    @keyframes hov { 0%,100%{transform:translateY(0) rotate(0deg)} 50%{transform:translateY(-5px) rotate(0.5deg)} }
    @keyframes bf { to { stroke-dashoffset: -400; } }
    @keyframes curs { 50% { opacity: 0 } }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    """
    
    m_on = str(master_anim).lower() == 'true'
    if not m_on: return css + keyframes + " * { animation: none !important; transition: none !important; }"

    classes = ""
    # FG Classes
    if str(fg_anim).lower() == 'true':
        classes += ".float{animation:f 6s ease-in-out infinite} .pulse{animation:p 2s infinite} .bob{animation:b 3s ease-in-out infinite} .hover-panel{animation:hov 8s ease-in-out infinite} .hover-panel-2{animation:hov 8s ease-in-out infinite reverse} .cursor{animation:curs 1s step-end infinite} .disc-spin{animation:spin 10s linear infinite}"
    
    # BG Classes
    if str(bg_anim).lower() == 'true':
        classes += ".mesh-1{animation:m1 30s infinite ease-in-out} .mesh-2{animation:m2 40s infinite ease-in-out} .drift{animation:d 40s linear infinite;transform-origin:center} .scroll-bg{animation:s 20s linear infinite} .scanline{animation:sl 4s linear infinite} .flow-border{animation:bf 4s linear infinite;stroke-dasharray:200}"

    return css + keyframes + classes

# ===========================
#     DATA HARVESTER (STATS++)
# ===========================

def get_time_elapsed(start_timestamp):
    """Calculates 00:00 elapsed string"""
    if not start_timestamp: return ""
    try:
        # Lanyard timestamps are milliseconds usually
        diff = time.time() - (start_timestamp / 1000)
        if diff < 0: return "" # Future timestamp?
        
        m = int(diff // 60)
        h = int(m // 60)
        m = m % 60
        
        if h > 0: return f"{h}H {m}M ELAPSED"
        return f"{m}M ELAPSED"
    except:
        return ""

def fetch_data(key, type_mode, args):
    try:
        force_name = args.get('name')

        # --- 1. DISCORD SERVER (Member Counts) ---
        if type_mode == 'discord':
            r = requests.get(f"https://discord.com/api/v10/invites/{key}?with_counts=true", headers=HEADERS, timeout=4)
            d = r.json()
            g = d.get('guild')
            if not g: return None
            
            display_title = force_name if force_name else "TOTAL MEMBERS"
            
            return {
                "type": "discord",
                "name": sanitize_xml(display_title), 
                "l1": f"{d.get('approximate_member_count',0):,}", 
                "l2": "",
                "color": "#5865F2", 
                "avatar": get_base64(f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png") if g.get('icon') else EMPTY,
                "is_music": False, "album_art": None, "id": g['id'],
                "stats_extra": f"{d.get('approximate_presence_count', 0):,} ONLINE NOW"
            }

        # --- 2. LANYARD USER (Beta Stats Mode) ---
        else:
            r = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            d = r.json().get('data', {})
            if not d: return None
            
            u = d['discord_user']
            status = d['discord_status']
            
            # --- 1. NAME ---
            dname = u['global_name'] if (args.get('showDisplayName','true').lower()=='true' and u.get('global_name')) else u['username']
            final_name = force_name if force_name else dname

            # --- 2. DEVICE STATS ---
            devices = []
            if d.get('active_on_discord_desktop'): devices.append("DSK")
            if d.get('active_on_discord_mobile'): devices.append("MOB")
            if d.get('active_on_discord_web'): devices.append("WEB")
            device_str = " | ".join(devices) if devices else "OFFLINE"

            # --- 3. COLORS & ACTIVITY ---
            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#FF4444", "offline": "#555", "spotify": "#1DB954"}
            col = cols.get(status, "#555")
            
            line_1 = "STATUS"
            line_2 = "ONLINE" if status == "online" else args.get('idleMessage', 'IDLE').upper()
            extra_info = device_str # Default bottom text
            
            is_music, art, progress = False, None, 0.0

            # A. Spotify Priority
            if d.get('spotify'):
                s = d['spotify']
                line_1 = f"🎵 {s['song']}"
                line_2 = f"{s['artist']}"
                col = cols['spotify']
                is_music = True
                art = get_base64(s.get('album_art_url'))
                # Calc Math
                try: 
                    now = time.time()*1000
                    total = s['timestamps']['end'] - s['timestamps']['start']
                    curr = now - s['timestamps']['start']
                    progress = min(max((curr/total)*100, 0), 100)
                    # Convert ms to M:S for extra stat
                    extra_info = f"ON: {s['album'][:20]}" 
                except: pass

            # B. Rich Presence (Games/VSCode)
            else:
                found = False
                for act in d.get('activities', []):
                    # Type 0 (Game), 2 (Listening)
                    if act['type'] in [0, 2]:
                        line_1 = act['name']
                        # State = "In Game", Details = "Competitive"
                        # Combine them intelligently
                        detail = act.get('details', '')
                        state = act.get('state', '')
                        line_2 = f"{detail} {state}".strip()
                        if not line_2: line_2 = "Active"
                        
                        # Timestamps?
                        if 'timestamps' in act and 'start' in act['timestamps']:
                            elapsed = get_time_elapsed(act['timestamps']['start'])
                            if elapsed: extra_info = f"{device_str} // {elapsed}"
                        else:
                            extra_info = f"{device_str} // ACTIVE"
                            
                        found = True
                        break
                    
                    # Type 4 (Custom Status)
                    if act['type'] == 4:
                        state = act.get('state', '')
                        if state: 
                            # We store custom status but keep looking for a game
                            # If no game found at end, we use this
                            pass 

                if not found:
                    # Check for Custom Status as fallback
                    for act in d.get('activities', []):
                        if act['type'] == 4 and act.get('state'):
                            line_1 = "NOTE"
                            line_2 = act['state']
                            found = True
                            break

            return {
                "type": "user",
                "name": sanitize_xml(final_name),
                "l1": sanitize_xml(line_1)[:35], 
                "l2": sanitize_xml(line_2)[:35],
                "stats_extra": sanitize_xml(extra_info)[:40],
                "color": col, 
                "avatar": get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png"),
                "album_art": art, "is_music": is_music, "progress": progress, "id": u['id']
            }
    except Exception as e:
        print(e)
        return None

# ===========================
#      STYLES
# ===========================

# 1. COMPACT SERVER
def render_compact(d, css, radius, bg_col):
    bg = f"""<rect width="100%" height="100%" fill="#{bg_col}" /><circle r="80" fill="#5865F2" opacity="0.4" class="mesh-1" filter="url(#b)" /><circle r="60" fill="#00AAFF" opacity="0.3" class="mesh-2" filter="url(#b)" />"""
    return f"""<svg width="400" height="110" viewBox="0 0 400 110" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css}.mono{{font-family:'JetBrains Mono'}}.big{{font-family:'Outfit',sans-serif;font-weight:900}}</style>
      <clipPath id="cp"><rect width="400" height="110" rx="{radius}"/></clipPath><clipPath id="av"><rect width="70" height="70" rx="14"/></clipPath><filter id="b"><feGaussianBlur stdDeviation="25"/></filter></defs>
      <g clip-path="url(#cp)">{bg}<rect width="100%" height="100%" fill="rgba(255,255,255,0.02)" stroke="rgba(255,255,255,0.1)" stroke-width="2" rx="{radius}"/></g>
      <g transform="translate(20, 20)"><g><rect width="70" height="70" rx="14" fill="rgba(0,0,0,0.3)"/><g clip-path="url(#av)"><image href="{d['avatar']}" width="70" height="70"/></g><rect width="70" height="70" rx="14" fill="none" stroke="{d['color']}" stroke-width="2"/></g><g transform="translate(90, 8)"><text x="0" y="10" font-family="Rajdhani" font-weight="700" font-size="11" fill="#888" letter-spacing="2">{d['name']}</text><text x="0" y="48" class="big" font-size="42" fill="white" letter-spacing="-1">{d['l1']}</text><text x="0" y="64" font-family="Rajdhani" font-weight="600" font-size="10" fill="#bbb" letter-spacing="1">{d['stats_extra']}</text></g></g></svg>"""

# 2. HYPER (REPURPOSED AI BAR FOR STATS)
def render_hyper(d, css, radius, bg):
    hex_path = "M50 0 L93.3 25 V75 L50 100 L6.7 75 V25 Z"
    # Used the bottom bar for extra stats (Time elapsed / Devices)
    stat_svg = f"""<g transform="translate(145,120)" class="float" style="animation-delay:0.5s"><rect width="310" height="35" rx="6" fill="rgba(0,0,0,0.5)" stroke="rgba(255,255,255,0.1)"/><text x="15" y="23" font-family="Rajdhani" font-size="13" fill="#E0E0FF"><tspan fill="#5865F2" font-weight="bold">DATA //</tspan> {d['stats_extra']}</text></g>"""
    bg_l = f'<image href="{d["album_art"]}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" opacity="0.4" filter="url(#bl)"/>' if d['album_art'] else f'<g class="drift" opacity="0.4"><circle cx="20" cy="20" r="160" fill="{d["color"]}" filter="url(#liq)"/><circle cx="450" cy="160" r="140" fill="#5865F2" filter="url(#liq)"/></g>'
    return f"""<svg width="480" height="180" viewBox="0 0 480 180" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><defs><style>{css}.u {{ font-family: 'Rajdhani', sans-serif; }} .m {{ font-family: 'JetBrains Mono', monospace; }}</style><filter id="liq"><feTurbulence type="fractalNoise" baseFrequency="0.015"/><feDisplacementMap in="SourceGraphic" scale="30"/></filter><filter id="bl"><feGaussianBlur stdDeviation="10"/></filter><clipPath id="cc"><rect width="480" height="180" rx="{radius}"/></clipPath><clipPath id="hc"><path d="{hex_path}"/></clipPath></defs><rect width="100%" height="100%" rx="{radius}" fill="#{bg}"/><g clip-path="url(#cc)">{bg_l}<rect width="100%" height="100%" fill="black" opacity="0.1"/></g><g transform="translate(25,40)"><path d="{hex_path}" fill="{d['color']}" opacity="0.2" transform="translate(0,3)"/><g clip-path="url(#hc)"><image href="{d['avatar']}" width="100" height="100"/></g><path d="{hex_path}" fill="none" stroke="{d['color']}" stroke-width="3"/></g><g transform="translate(145,55)" class="float"><text y="0" class="u" font-size="30" font-weight="700" fill="white" style="text-shadow:0 4px 10px rgba(0,0,0,0.5)">{d['name'].upper()}</text><text y="25" class="m" font-size="12" fill="{d['color']}">>> {d['l1']}</text><text y="42" class="m" font-size="11" fill="#ccc">{d['l2']}</text></g>{stat_svg}<text x="470" y="170" text-anchor="end" class="m" font-size="8" fill="#555">ID: {d['id']}</text></svg>"""

# 3. CHILLAX
def render_chillax(d, css, radius, bg_arg):
    bg = bg_arg if bg_arg else "18191c"
    bg_art = f'<image href="{d["album_art"]}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" opacity="0.6" filter="url(#heavyBlur)"/><rect width="100%" height="100%" fill="black" opacity="0.5"/>' if d['album_art'] else f"""<rect width="100%" height="100%" fill="#{bg}"/><circle cx="50" cy="50" r="100" fill="#00CFFF" class="mesh-1" opacity="0.4" filter="url(#blur)"/><circle cx="430" cy="130" r="120" fill="#FF00FF" class="mesh-2" opacity="0.4" filter="url(#blur)"/>"""
    stat_e = f"""<g transform="translate(130, 95)" class="hover-panel"><rect width="320" height="30" rx="8" fill="rgba(0,0,0,0.6)" stroke="rgba(255,255,255,0.2)"/><text x="15" y="19" font-family="JetBrains Mono" font-size="10" fill="{d['color']}">{d['stats_extra']}<tspan class="cursor">_</tspan></text></g>"""
    return f"""<svg width="480" height="150" viewBox="0 0 480 150" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><defs><style>{css}.script-font{{font-family:'Pacifico'}}.ui-font{{font-family:'Fredoka'}}</style><clipPath id="c"><rect width="480" height="150" rx="{radius}"/></clipPath><clipPath id="av"><circle cx="50" cy="50" r="45"/></clipPath><filter id="blur"><feGaussianBlur stdDeviation="35"/></filter><filter id="heavyBlur"><feGaussianBlur stdDeviation="10"/></filter><filter id="sh"><feDropShadow dx="0" dy="2" flood-color="black" flood-opacity="0.8"/></filter></defs><g clip-path="url(#c)">{bg_art}<rect width="100%" height="100%" fill="rgba(255,255,255,0.02)"/></g><g transform="translate(30, 25)"><circle cx="50" cy="50" r="48" fill="none" stroke="{d['color']}" stroke-width="3" stroke-dasharray="10 8" opacity="0.8" class="disc-spin"/><g clip-path="url(#av)"><image href="{d['avatar']}" width="100" height="100"/></g><circle cx="85" cy="85" r="9" fill="{d['color']}" stroke="#{bg}" stroke-width="3"/></g><g transform="translate(145, 30)"><text x="0" y="15" class="script-font" font-size="34" fill="white" filter="url(#sh)">! {d['name']}</text><text x="220" y="12" font-size="18">🌸 🤍</text><g transform="translate(-5, 30)"><rect width="320" height="28" rx="6" fill="rgba(255,255,255,0.1)"/><text x="10" y="19" class="ui-font" font-weight="700" font-size="13" fill="white"><tspan fill="{d['color']}">></tspan> {d['l1']} {d['l2']}</text></g></g>{stat_e}<text x="470" y="145" text-anchor="end" class="ui-font" font-size="9" fill="#777">ID: {d['id']}</text></svg>"""

# 4. EASTER EGG (MacOS)
def render_easteregg(d, css, radius):
    bg_el = f'<image href="{d["album_art"]}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" opacity="0.6" filter="url(#heavyBlur)"/><rect width="100%" height="100%" fill="black" opacity="0.6"/>' if d['album_art'] else f"""<rect width="100%" height="100%" fill="#050505"/><circle r="120" fill="{d['color']}" class="mesh-1" opacity="0.6" filter="url(#fb)"/><circle r="150" fill="#5865F2" class="mesh-2" opacity="0.5" filter="url(#fb)"/><circle r="100" fill="#00FFFF" class="mesh-3" opacity="0.4" filter="url(#fb)"/>"""
    stat_html = f"""<g transform="translate(130, 20)" class="hover-panel-2"><rect width="220" height="24" rx="12" fill="black" stroke="rgba(255,255,255,0.15)"/><text x="110" y="16" text-anchor="middle" font-family="JetBrains Mono" font-size="9" fill="#EEE"><tspan fill="{d['color']}">●</tspan> {d['stats_extra']}</text></g>"""
    return f"""<svg width="480" height="180" viewBox="0 0 480 180" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><defs><style>{css}</style><filter id="heavyBlur"><feGaussianBlur stdDeviation="15"/></filter><filter id="fb"><feGaussianBlur stdDeviation="30"/><feComposite in="SourceGraphic" operator="over"/></filter><clipPath id="main"><rect width="480" height="180" rx="{radius}"/></clipPath><clipPath id="sq"><path d="M 20,0 H 80 C 100,0 100,20 100,20 V 80 C 100,100 80,100 80,100 H 20 C 0,100 0,80 0,80 V 20 C 0,0 20,0 20,0 Z" /></clipPath><linearGradient id="rb"><stop offset="0%" stop-color="{d['color']}"/><stop offset="50%" stop-color="#00FFFF"/><stop offset="100%" stop-color="{d['color']}"/></linearGradient></defs><g clip-path="url(#main)">{bg_el}<pattern id="gn" width="100" height="100" patternUnits="userSpaceOnUse"><rect width="1" height="1" fill="white" opacity="0.05"/></pattern><rect width="100%" height="100%" fill="url(#gn)"/></g><rect x="2" y="2" width="476" height="176" rx="{radius}" fill="none" stroke="url(#rb)" stroke-width="4" class="flow-border" opacity="0.8"/><g transform="translate(20, 20)"><circle cx="0" cy="0" r="5" fill="#FF5F56"/><circle cx="15" cy="0" r="5" fill="#FFBD2E"/><circle cx="30" cy="0" r="5" fill="#27C93F"/></g>{stat_html}<g transform="translate(25, 50)" class="hover-panel"><rect x="5" y="5" width="100" height="100" rx="20" fill="black" opacity="0.3"/><g clip-path="url(#sq)"><image href="{d['avatar']}" width="100" height="100"/><path d="M 0,0 L 100,0 L 0,100 Z" fill="white" opacity="0.1"/></g><path d="M 20,0 H 80 C 100,0 100,20 100,20 V 80 C 100,100 80,100 80,100 H 20 C 0,100 0,80 0,80 V 20 C 0,0 20,0 20,0 Z" fill="none" stroke="rgba(255,255,255,0.4)" stroke-width="2"/></g><g transform="translate(145, 60)" class="float"><text x="0" y="0" font-family="Outfit" font-weight="900" font-size="34" fill="white">{d['name']}</text><g transform="translate(0, 15)"><text x="0" y="20" font-family="JetBrains Mono" font-weight="800" font-size="13" fill="{d['color']}" letter-spacing="1">>> {d['l1'].upper()}</text><text x="0" y="40" font-family="Outfit" font-weight="700" font-size="14" fill="#EEE">{d['l2']}</text></g></g></svg>"""

# 5. SPOTIFY CARD (Updated for Stats)
def render_spotify(d, css, radius, bg):
    img = d['album_art'] if d['album_art'] else d['avatar']
    stat_html = f'<text x="120" y="70" class="m" font-size="10" fill="#E0E0FF" opacity="0.7">STATUS // {d["stats_extra"]}</text>'
    pw = (d['progress'] / 100.0) * 440
    return f"""<svg width="480" height="150" viewBox="0 0 480 150" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><defs><style>{css}.u{{font-family:'Rajdhani'}}.m{{font-family:'JetBrains Mono'}}</style><clipPath id="cp"><rect width="480" height="150" rx="{radius}"/></clipPath><clipPath id="ac"><rect width="100" height="100" rx="8"/></clipPath><filter id="bl"><feGaussianBlur stdDeviation="15"/></filter></defs><rect width="100%" height="100%" rx="{radius}" fill="#{bg}"/><g clip-path="url(#cp)"><image href="{img}" width="480" height="480" x="0" y="-165" opacity="0.3" filter="url(#bl)"/><rect width="100%" height="100%" fill="black" opacity="0.2"/></g><g transform="translate(20, 20)"><g class="float"><g clip-path="url(#ac)"><image href="{img}" width="100" height="100"/></g><rect width="100" height="100" rx="10" fill="none" stroke="rgba(255,255,255,0.1)"/>{'<circle cx="50" cy="50" r="20" fill="none" stroke="white" stroke-dasharray="10 5" opacity="0.5" class="disc-spin"/>' if d['is_music'] else ''}</g><g transform="translate(115, 10)"><text class="u" font-size="10" font-weight="bold" fill="#bbb" letter-spacing="2">NOW PLAYING</text><text y="28" class="u" font-size="24" font-weight="bold" fill="white">{d['l1']}</text><text y="50" class="m" font-size="12" fill="{d['color']}">{d['l2']}</text><text y="70" class="m" font-size="10" fill="#999">User: {d['name']}</text>{stat_html}</g></g><g transform="translate(20, 135)"><rect width="440" height="4" rx="2" fill="rgba(255,255,255,0.15)"/><rect width="{pw}" height="4" rx="2" fill="{d['color']}"/></g></svg>"""

# ===========================
#        CONTROLLER
# ===========================

@app.route('/superbadge/<key>')
@app.route('/badge/<mode>/<key>')
def handler(key, mode="auto"):
    args = request.args
    target = mode
    if mode == "auto":
        target = 'user' if (key.isdigit() and len(str(key)) > 15) else 'discord'
        
    data = fetch_data(key, target, args)
    if not data: return Response('<svg xmlns="http://www.w3.org/2000/svg" width="300" height="50"><rect width="100%" height="100%" fill="black"/><text x="10" y="30" fill="red" font-family="sans-serif">DATA API ERROR</text></svg>', mimetype="image/svg+xml")

    anim = args.get('animations', 'true')
    bg_an = args.get('bgAnimations', 'true')
    fg_an = args.get('fgAnimations', 'true')
    style = args.get('style', 'hyper').lower()
    
    bg = args.get('bg', '09090b').replace('#','')
    radius = args.get('borderRadius', '20').replace('px', '')
    
    # Force Compact + Static for Servers
    if data['type'] == 'discord':
        fg_an = 'false'
        style = 'compact'

    css = get_css(anim, bg_an, fg_an)

    if style == 'compact': svg = render_compact(data, css, radius, bg) # Note: AI Arg removed
    elif style == 'chillax': svg = render_chillax(data, css, radius, bg)
    elif style == 'spotify': svg = render_spotify(data, css, radius, bg)
    elif style == 'easteregg': svg = render_easteregg(data, css, radius)
    else: svg = render_hyper(data, css, radius, bg) # Standard

    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
