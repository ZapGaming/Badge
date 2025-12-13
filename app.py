import base64
import requests
import os
import html
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
HEADERS = {'User-Agent': 'HyperBadge/Universal-v16'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# ===========================
#      HELPER FUNCTIONS
# ===========================

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
    # CSS IMPORTS
    css = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Rajdhani:wght@500;700&amp;family=Fredoka:wght@400;600&amp;family=Fira+Code:wght@500&amp;family=Outfit:wght@400;700;900&amp;display=swap');"
    
    # KEYFRAMES (Definitions)
    css += """
    @keyframes d { from{transform:rotate(0deg) scale(1.1)} to{transform:rotate(360deg) scale(1.1)} }
    @keyframes f { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-4px)} }
    @keyframes p { 50%{opacity:0.5} }
    @keyframes b { 50%{transform:translateY(-5px)} }
    @keyframes s { from {transform:translateY(0)} to {transform:translateY(-40px)} }
    @keyframes sl { 0% {transform:translateY(-100%)} 100% {transform:translateY(100%)} }
    @keyframes hov { 0%,100%{transform:translateY(0) rotate(0deg)} 50%{transform:translateY(-5px) rotate(0.5deg)} }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    
    /* Mesh & Border */
    @keyframes m1 { 0%{cx:20px; cy:20px;} 100%{cx:300px; cy:100px;} }
    @keyframes m2 { 0%{cx:400px; cy:160px;} 100%{cx:100px; cy:50px;} }
    @keyframes m3 { 0%{cx:100px; cy:150px; r:50px;} 50%{r:100px;} 100%{cx:400px; cy:20px; r:50px;} }
    @keyframes bf { to { stroke-dashoffset: -400; } }
    """

    # LOGIC FLAGS
    master = str(master_anim).lower() == 'true'
    bg = str(bg_anim).lower() == 'true' and master
    fg = str(fg_anim).lower() == 'true' and master

    # No animations at all
    if not master: return css + " * { animation: none !important; transition: none !important; }"

    # Apply classes based on flags
    if fg:
        css += """
        .float { animation: f 6s ease-in-out infinite; } 
        .pulse { animation: p 2s infinite; } 
        .bob { animation: b 3s ease-in-out infinite; } 
        .hover-panel { animation: hov 8s ease-in-out infinite; }
        .hover-panel-2 { animation: hov 8s ease-in-out infinite reverse; }
        .disc-spin { animation: spin 10s linear infinite; }
        .cursor { animation: p 1s step-end infinite; }
        """
    
    if bg:
        css += """
        .drift { animation: d 40s linear infinite; transform-origin: center; } 
        .scroll-bg { animation: s 20s linear infinite; }
        .scanline { animation: sl 4s linear infinite; }
        .mesh-1 { animation: m1 15s infinite ease-in-out alternate; }
        .mesh-2 { animation: m2 20s infinite ease-in-out alternate-reverse; }
        .mesh-3 { animation: m3 12s infinite ease-in-out; }
        .flow-border { animation: bf 4s linear infinite; stroke-dasharray: 200; }
        """
        
    return css

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
            prompt = f"Roast '{user_name}' about '{status_text}'. Savage, uppercase, max 7 words."
        else:
            ctx = "Activity"
            if data_type == "github": ctx = "GitHub Stats"
            prompt = f"{ctx} for '{user_name}': '{status_text}'. Cool sci-fi HUD update. Uppercase. Max 6 words."

        response = model.generate_content(prompt)
        text = html.escape(response.text.strip().replace('"','').replace("'", "")).upper()[:50]
        
        CACHE[key] = text
        return text
    except:
        return "DATA ENCRYPTED"

# ===========================
#       DATA HARVESTERS
# ===========================

def fetch_data(key, type_mode, args):
    try:
        # LANYARD (USER)
        if type_mode == 'user' or (type_mode == 'auto' and len(str(key)) > 15):
            r = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            d = r.json().get('data', {})
            if not d: return None
            
            u = d['discord_user']
            status = d['discord_status']
            
            # Args processing
            dname = u['global_name'] if (args.get('showDisplayName','true').lower()=='true' and u.get('global_name')) else u['username']
            custom_idle = args.get('idleMessage', 'IDLE')
            
            l1, l2, col = "", "", "#555"
            is_music, art, progress = False, None, 0.0
            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#FF4444", "offline": "#555", "spotify": "#1DB954"}
            
            if d.get('spotify'):
                l1 = f"🎵 {d['spotify']['song']}"
                l2 = f"By {d['spotify']['artist']}"
                col = cols['spotify']
                art = get_base64(d['spotify'].get('album_art_url'))
                is_music = True
                
                # Progress Bar Calculation
                try:
                    s_data = d['spotify']
                    now = time.time() * 1000
                    start = s_data['timestamps']['start']
                    end = s_data['timestamps']['end']
                    progress = (now - start) / (end - start) * 100
                    if progress > 100: progress = 100
                    if progress < 0: progress = 0
                except: 
                    progress = 0
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
                "name": html.escape(dname),
                "l1": html.escape(l1)[:25], "l2": html.escape(l2)[:30],
                "color": col, 
                "avatar": get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png"),
                "album_art": art, 
                "is_music": is_music,
                "progress": progress,
                "id": u['id']
            }

        # GITHUB PROFILE
        elif type_mode == 'github':
            r = requests.get(f"https://api.github.com/users/{key}", headers=HEADERS, timeout=4)
            d = r.json()
            if 'login' not in d: return None
            return {
                "type": "github",
                "name": html.escape(d['login']),
                "l1": "REPOS", "l2": str(d['public_repos']),
                "color": "#fff", 
                "avatar": get_base64(d['avatar_url']),
                "album_art": None, "is_music": False, "progress":0, "id": str(d['id'])
            }

        # DISCORD INVITE
        else:
            r = requests.get(f"https://discord.com/api/v10/invites/{key}?with_counts=true", headers=HEADERS, timeout=4)
            d = r.json()
            g = d.get('guild')
            if not g: return None
            return {
                "type": "discord",
                "name": html.escape(g['name']),
                "l1": "MEMBERS", "l2": f"{d['approximate_member_count']:,}",
                "color": "#5865F2", 
                "avatar": get_base64(f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png") if g.get('icon') else EMPTY,
                "album_art": None, "is_music": False, "progress":0, "id": g['id']
            }
    except:
        return None

# ===========================
#      STYLES
# ===========================

# 1. SPOTIFY (New!)
def render_spotify(d, ai_msg, css, radius, bg):
    img = d['album_art'] if d['album_art'] else d['avatar']
    
    ai_html = f'<text x="135" y="100" class="m" font-size="9" fill="{d["color"]}" opacity="0.8">AI // {ai_msg}</text>' if ai_msg else ""
    
    # Progress Width logic: Total width is 440px
    p_width = (d['progress'] / 100.0) * 440

    return f"""<svg width="480" height="150" viewBox="0 0 480 150" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css}
        .u {{ font-family: 'Rajdhani', sans-serif; }} .m {{ font-family: 'JetBrains Mono', monospace; }}
      </style>
      <clipPath id="cp"><rect width="480" height="150" rx="{radius}"/></clipPath>
      <clipPath id="artc"><rect width="100" height="100" rx="10"/></clipPath>
      <filter id="bl"><feGaussianBlur stdDeviation="15"/></filter>
      </defs>
      
      <!-- BG with Blurred Art -->
      <rect width="100%" height="100%" rx="{radius}" fill="#{bg}"/>
      <g clip-path="url(#cp)">
         <image href="{img}" width="480" height="480" x="0" y="-165" opacity="0.3" filter="url(#bl)"/>
         <rect width="100%" height="100%" fill="black" opacity="0.2"/>
      </g>

      <!-- Player UI -->
      <g transform="translate(20, 20)">
         <!-- Album Art -->
         <g class="float">
            <image href="{img}" width="100" height="100" clip-path="url(#artc)"/>
            <rect width="100" height="100" rx="10" fill="none" stroke="rgba(255,255,255,0.2)"/>
            { f'<circle cx="50" cy="50" r="20" fill="none" stroke="white" stroke-dasharray="10 5" opacity="0.5" class="disc-spin"/>' if d['is_music'] else '' }
         </g>
         
         <!-- Meta -->
         <g transform="translate(115, 10)">
            <text class="u" font-size="10" font-weight="bold" fill="#bbb" letter-spacing="2">NOW PLAYING</text>
            <text y="28" class="u" font-size="24" font-weight="bold" fill="white">{d['l1']}</text>
            <text y="50" class="m" font-size="12" fill="{d['color']}">{d['l2']}</text>
            <text y="70" class="m" font-size="10" fill="#999">User: {d['name']}</text>
         </g>
         {ai_html}
      </g>
      
      <!-- Progress Bar -->
      <g transform="translate(20, 135)">
         <rect width="440" height="4" rx="2" fill="rgba(255,255,255,0.15)"/>
         <rect width="{p_width}" height="4" rx="2" fill="{d['color']}"/>
      </g>
    </svg>"""

# 2. EASTER EGG (macOS 26)
def render_easteregg(d, ai_msg, css, radius):
    bg_element = ""
    if d['album_art']:
        bg_element = f"""<image href="{d['album_art']}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" opacity="0.6" filter="url(#heavyBlur)"/><rect width="100%" height="100%" fill="black" opacity="0.6"/>"""
    else:
        bg_element = f"""<rect width="100%" height="100%" fill="#050505"/><circle r="120" fill="{d['color']}" class="mesh-1" opacity="0.6" filter="url(#flowBlur)"/><circle r="150" fill="#5865F2" class="mesh-2" opacity="0.5" filter="url(#flowBlur)"/><circle r="100" fill="#00FFFF" class="mesh-3" opacity="0.4" filter="url(#flowBlur)"/>"""

    ai_html = f"""<g transform="translate(130, 20)" class="hover-panel-2"><rect width="220" height="24" rx="12" fill="black" stroke="rgba(255,255,255,0.15)"/><text x="110" y="16" text-anchor="middle" font-family="JetBrains Mono" font-size="9" fill="#EEE"><tspan fill="{d['color']}">●</tspan> {ai_msg}</text></g>""" if ai_msg else ""

    return f"""<svg width="480" height="180" viewBox="0 0 480 180" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css}</style><filter id="heavyBlur"><feGaussianBlur stdDeviation="15"/></filter><filter id="flowBlur"><feGaussianBlur stdDeviation="30"/><feComposite in="SourceGraphic" operator="over"/></filter><clipPath id="main"><rect width="480" height="180" rx="{radius}"/></clipPath><clipPath id="sq"><path d="M 20,0 H 80 C 100,0 100,20 100,20 V 80 C 100,100 80,100 80,100 H 20 C 0,100 0,80 0,80 V 20 C 0,0 20,0 20,0 Z" /></clipPath><linearGradient id="rb"><stop offset="0%" stop-color="{d['color']}"/><stop offset="50%" stop-color="#00FFFF"/><stop offset="100%" stop-color="{d['color']}"/></linearGradient></defs>
      <g clip-path="url(#main)">{bg_element}<rect width="100%" height="100%" fill="url(#grain)"/></g>
      <rect x="2" y="2" width="476" height="176" rx="{radius}" fill="none" stroke="url(#rb)" stroke-width="4" class="flow-border" opacity="0.8"/>
      <g transform="translate(20, 20)"><circle cx="0" cy="0" r="5" fill="#FF5F56"/><circle cx="15" cy="0" r="5" fill="#FFBD2E"/><circle cx="30" cy="0" r="5" fill="#27C93F"/></g>
      {ai_html}
      <g transform="translate(25, 50)" class="hover-panel"><rect x="5" y="5" width="100" height="100" rx="20" fill="black" opacity="0.3"/><g clip-path="url(#sq)"><image href="{d['avatar']}" width="100" height="100"/></g></g>
      <g transform="translate(145, 60)" class="float" style="animation-delay:0.2s"><text x="0" y="0" font-family="Outfit" font-weight="900" font-size="34" fill="white">{d['name']}</text><text x="0" y="25" font-family="JetBrains Mono" font-weight="800" font-size="13" fill="{d['color']}">>> {d['l1'].upper()}</text><text x="0" y="45" font-family="Outfit" font-weight="700" font-size="14" fill="#EEE">{d['l2']}</text></g>
    </svg>"""

# 3. HYPER (Standard)
def render_hyper(d, ai_msg, css, radius, bg):
    hex_path = "M50 0 L93.3 25 V75 L50 100 L6.7 75 V25 Z"
    
    ai_svg = f"""<g transform="translate(145,120)" class="float" style="animation-delay:0.5s"><rect width="310" height="35" rx="6" fill="rgba(0,0,0,0.5)" stroke="rgba(255,255,255,0.1)"/><text x="15" y="23" font-family="Rajdhani" font-size="13" fill="#E0E0FF"><tspan fill="#5865F2" font-weight="bold">AI //</tspan> {ai_msg}<tspan class="pulse">_</tspan></text></g>""" if ai_msg else ""

    bg_layer = f'<image href="{d["album_art"]}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" opacity="0.4" filter="url(#bl)"/>' if d['album_art'] else f'<g class="drift" opacity="0.4"><circle cx="20" cy="20" r="160" fill="{d["color"]}" filter="url(#liq)"/><circle cx="450" cy="160" r="140" fill="#5865F2" filter="url(#liq)"/></g>'

    return f"""<svg width="480" height="180" viewBox="0 0 480 180" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css}.u {{ font-family: 'Rajdhani', sans-serif; }} .m {{ font-family: 'JetBrains Mono', monospace; }}</style><filter id="liq"><feTurbulence type="fractalNoise" baseFrequency="0.015"/><feDisplacementMap in="SourceGraphic" scale="30"/></filter><filter id="bl"><feGaussianBlur stdDeviation="10"/></filter><clipPath id="cc"><rect width="480" height="180" rx="{radius}"/></clipPath><clipPath id="hc"><path d="{hex_path}"/></clipPath></defs>
      <rect width="100%" height="100%" rx="{radius}" fill="#{bg}"/>
      <g clip-path="url(#cc)">{bg_layer}<rect width="100%" height="100%" fill="black" opacity="0.1"/></g>
      <g transform="translate(25,40)"><path d="{hex_path}" fill="{d['color']}" opacity="0.2" transform="translate(0,3)"/><g clip-path="url(#hc)"><image href="{d['avatar']}" width="100" height="100"/></g><path d="{hex_path}" fill="none" stroke="{d['color']}" stroke-width="3"/></g>
      <g transform="translate(145,55)" class="float"><text y="0" class="u" font-size="30" font-weight="700" fill="white" style="text-shadow:0 4px 10px rgba(0,0,0,0.5)">{d['name'].upper()}</text><text y="25" class="m" font-size="12" fill="{d['color']}">>> {d['l1']}</text><text y="42" class="m" font-size="11" fill="#ccc">{d['l2']}</text></g>
      {ai_svg}<text x="470" y="170" text-anchor="end" class="m" font-size="8" fill="#555">UID: {d['id']}</text>
    </svg>"""

# 4. CUTE
def render_cute(d, ai_msg, css, bg):
    c = d['color']
    ai_svg = f"""<g transform="translate(0,60)" class="bob"><rect width="280" height="30" rx="15" fill="white" opacity="0.8" stroke="{c}" stroke-width="1"/><text x="15" y="19" font-family="Fredoka" font-size="11" fill="#888">🐰 {ai_msg.capitalize()}</text></g>""" if ai_msg else ""
    return f"""<svg width="480" height="180" viewBox="0 0 480 180" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><defs><style>{css}</style><clipPath id="cr"><circle cx="65" cy="65" r="55"/></clipPath></defs><rect width="480" height="180" rx="30" fill="#FFFAFA"/><rect x="5" y="5" width="470" height="170" rx="25" fill="none" stroke="{c}" stroke-width="4" stroke-dasharray="15 10" opacity="0.4"/><g transform="translate(25,25)"><image href="{d['avatar']}" width="130" height="130" clip-path="url(#cr)"/></g><g transform="translate(170,55)"><text y="0" font-family="Fredoka" font-weight="600" font-size="30" fill="#555">{d['name']}</text><rect y="10" width="220" height="25" rx="12" fill="#F0F0F0"/><text x="10" y="26" font-family="Fredoka" font-size="12" fill="{c}">✨ {d['l1']} {d['l2']}</text>{ai_svg}</g></svg>"""

# 5. TERMINAL
def render_terminal(d, ai_msg, css, bg):
    ai_svg = f"""<text x="15" y="100" fill="#569CD6">ai.query</text><text x="70" y="100" fill="#CE9178">("{d['name']}")</text><text x="15" y="120" fill="#6A9955">// {ai_msg}<tspan class="cursor">_</tspan></text>""" if ai_msg else ""
    return f"""<svg width="480" height="180" viewBox="0 0 480 180" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><defs><style>{css}</style></defs><rect width="100%" height="100%" rx="6" fill="#1e1e1e"/><g transform="translate(15, 45)" font-family="Fira Code" font-size="12"><text y="0" fill="#C586C0">const</text> <text x="80" y="0" fill="#CE9178">"{d['name']}"</text><text y="20" fill="#9CDCFE">usr.status</text><text y="20" x="90" fill="#B5CEA8">"{d['l1']} {d['l2']}"</text>{ai_svg}</g><rect y="160" width="100%" height="20" fill="#5865F2"/><image href="{d['avatar']}" x="380" y="40" width="80" height="80" opacity="0.9" rx="4"/></svg>"""

# 6. PROFESSIONAL
def render_pro(d, msg, args):
    msg_html = f'<text y="90" font-size="10" fill="#999" font-style="italic">NOTE: {msg}</text>' if msg else ""
    return f"""<svg width="480" height="140" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><defs><clipPath id="s"><rect width="90" height="90" rx="4"/></clipPath></defs><rect width="478" height="138" x="1" y="1" rx="4" fill="#FFFFFF" stroke="#e1e4e8"/><rect width="6" height="138" x="1" y="1" rx="1" fill="{d['color']}"/><g transform="translate(30,25)"><image href="{d['avatar']}" width="90" height="90" clip-path="url(#s)"/></g><g transform="translate(140,35)" font-family="Arial, Helvetica, sans-serif"><text y="0" font-weight="bold" font-size="22" fill="#333">{d['name']}</text><text y="30" font-size="11" font-weight="bold" fill="#586069">{d['l1']}</text><text y="45" font-size="11" fill="#586069">{d['l2']}</text><line x1="0" y1="70" x2="300" y2="70" stroke="#eee"/>{msg_html}</g></svg>"""

# ===========================
#        ROUTE HANDLER
# ===========================

@app.route('/superbadge/<key>')
@app.route('/badge/<mode>/<key>')
def handler(key, mode="auto"):
    args = request.args
    target_mode = mode
    if mode == "auto": target_mode = 'user' if (key.isdigit() and len(str(key)) > 15) else 'discord'
    data = fetch_data(key, target_mode, args)
    if not data: return Response('<svg xmlns="http://www.w3.org/2000/svg" width="300" height="50"><rect width="100%" height="100%" fill="black"/><text x="10" y="30" fill="red" font-family="sans-serif">DATA API ERROR</text></svg>', mimetype="image/svg+xml")

    # Settings
    roast = args.get('roastMode', 'false').lower() == 'true'
    anim_on = args.get('animations', 'true')
    # Specific Toggles (Default true if main is true)
    bg_an = args.get('bgAnimations', 'true') if anim_on=='true' else 'false'
    fg_an = args.get('fgAnimations', 'true') if anim_on=='true' else 'false'
    
    ai_on = args.get('aifeatures', 'true')
    style = args.get('style', 'hyper').lower()
    
    bg = args.get('bg', '09090b').replace('#','')
    rad = args.get('borderRadius', '20').replace('px', '')

    ai_role = "roast" if roast else "hud"
    full_text = f"{data.get('l1','')} {data.get('l2','')}"
    
    # 5 Args passed: Correct signature
    msg = consult_gemini(full_text, data['name'], ai_role, ai_on, data.get('type'))

    css = get_css(anim_on, bg_an, fg_an)

    if style == 'spotify': svg = render_spotify(data, msg, css, rad, bg)
    elif style == 'easteregg': svg = render_easteregg(data, msg, css, rad)
    elif style == 'cute': svg = render_cute(data, msg, css, bg)
    elif style == 'terminal': svg = render_terminal(data, msg, css, bg)
    elif style == 'pro': svg = render_pro(data, msg, args)
    else: svg = render_hyper(data, msg, css, rad, bg)

    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
