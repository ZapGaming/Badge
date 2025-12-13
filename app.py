import base64
import requests
import os
import html
import time
import random
import datetime
import google.generativeai as genai
from flask import Flask, Response, request

app = Flask(__name__)

# --- CONFIGURATION ---
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

HEADERS = {'User-Agent': 'HyperBadge/Universal-v11'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
CACHE = {} 

# --- HELPERS ---
def get_base64(url):
    if not url: return EMPTY
    try:
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(r.content).decode('utf-8')}"
    except:
        pass
    return EMPTY

def get_css(anim_enabled):
    """Global CSS definitions"""
    base = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&family=Rajdhani:wght@500;700&family=Fredoka:wght@400;600&family=Fira+Code:wght@500&display=swap');"
    
    if str(anim_enabled).lower() == 'false':
        return base + " * { animation: none !important; transition: none !important; }"
    
    return base + """
    /* Universal Animations */
    .drift { animation: d 30s linear infinite; transform-origin: center; } 
    @keyframes d { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
    
    .float { animation: f 6s ease-in-out infinite; } 
    @keyframes f { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-4px)} }
    
    .pulse { animation: p 2s infinite; } 
    @keyframes p { 50%{opacity:0.5} }
    
    .cloud-move { animation: cm 20s linear infinite; }
    @keyframes cm { from {transform:translateX(0)} to {transform:translateX(-50px)} }
    
    .scanline { animation: sl 4s linear infinite; }
    @keyframes sl { 0% {transform:translateY(-100%)} 100% {transform:translateY(100%)} }
    """

# --- AI ENGINE ---
def consult_gemini(status_text, user_name, mode, enabled):
    # Logic Change: Return None if disabled so Render knows to hide the UI
    if str(enabled).lower() == 'false': return None
    if not GOOGLE_API_KEY: return None # Don't show anything if key missing
    
    key = f"AI_{user_name}_{status_text}_{mode}"
    if key in CACHE: return CACHE[key]

    try:
        model = genai.GenerativeModel('gemini-pro')
        if mode == "roast":
            task = f"Roast '{user_name}' about '{status_text}'. Savage, uppercase, max 7 words."
        else:
            task = f"HUD status for '{user_name}': '{status_text}'. Technical, uppercase, max 6 words."

        response = model.generate_content(task)
        clean_text = html.escape(response.text.strip().replace('"','').replace("'", "")).upper()[:50]
        CACHE[key] = clean_text
        return clean_text
    except:
        return "DATA ENCRYPTED"

# --- DATA FETCHING ---
def fetch_data(key, type_mode, args):
    """Master Fetcher"""
    try:
        # LANYARD (USER)
        if type_mode == 'user' or (type_mode == 'auto' and len(str(key)) > 15):
            r = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            d = r.json().get('data', {})
            if not d: return None
            
            u = d['discord_user']
            status = d['discord_status']
            
            # Global Display Name support
            show_display = args.get('showDisplayName','true').lower() == 'true'
            name = u['global_name'] if show_display and u.get('global_name') else u['username']
            custom_idle = args.get('idleMessage', 'IDLE')
            
            # Activity Logic
            l1, l2 = "", ""
            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#FF4444", "offline": "#555", "spotify": "#1DB954"}
            
            if d.get('spotify'):
                l1 = f"🎵 {d['spotify']['song']}"
                l2 = f"By {d['spotify']['artist']}"
                color = cols['spotify']
                # Add art to 'extra' for backgrounds
                extra_img = get_base64(d['spotify'].get('album_art_url'))
            else:
                color = cols.get(status, "#555")
                extra_img = None
                
                # Check Games/Status
                found = False
                for act in d.get('activities', []):
                    if act['type'] == 0: l1="PLAYING:"; l2=act['name']; found=True; break
                    if act['type'] == 4: l1="NOTE:"; l2=act.get('state',''); found=True; break
                    if act['type'] == 2: l1="MEDIA:"; l2="Streaming"; found=True; break
                
                if not found:
                    l1="STATUS:"; l2="ONLINE" if status=="online" else custom_idle.upper()

            return {
                "name": html.escape(name),
                "l1": html.escape(l1)[:25], 
                "l2": html.escape(l2)[:30],
                "color": color, 
                "avatar": get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png"),
                "bg_image": extra_img, # Album art or None
                "id": u['id']
            }

        # DISCORD SERVER (Invite Code)
        else:
            r = requests.get(f"https://discord.com/api/v10/invites/{key}?with_counts=true", headers=HEADERS, timeout=4)
            d = r.json()
            if r.status_code != 200: return None
            return {
                "name": html.escape(d['guild']['name']),
                "l1": "MEMBERS", "l2": f"{d['approximate_member_count']:,}",
                "color": "#5865F2", 
                "avatar": get_base64(f"https://cdn.discordapp.com/icons/{d['guild']['id']}/{d['guild']['icon']}.png") if d['guild'].get('icon') else EMPTY,
                "bg_image": None,
                "id": d['guild']['id']
            }
    except:
        return None

# ===========================
#      RENDER ENGINES
# ===========================

def render_hyper(d, ai_msg, css, bg, rad):
    """Glassmorphism / Liquid / Modern"""
    
    # AI Visibility Logic
    ai_html = ""
    if ai_msg:
        ai_html = f"""
        <g transform="translate(145,115)" class="float" style="animation-delay:0.5s">
            <rect width="310" height="35" rx="6" fill="rgba(0,0,0,0.5)" stroke="rgba(255,255,255,0.1)"/>
            <text x="15" y="23" font-family="Rajdhani" font-size="13" fill="#E0E0FF">
               <tspan fill="#5865F2" font-weight="bold">AI //</tspan> {ai_msg}<tspan class="pulse">_</tspan>
            </text>
        </g>"""

    # Background Logic
    if d['bg_image']:
        bg_layer = f'<image href="{d["bg_image"]}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" opacity="0.4" filter="url(#bl)"/>'
    else:
        bg_layer = f'<g class="drift" opacity="0.4"><circle cx="20" cy="20" r="160" fill="{d["color"]}" filter="url(#liq)"/><circle cx="450" cy="160" r="140" fill="#5865F2" filter="url(#liq)"/></g>'

    return f"""<svg width="480" height="180" viewBox="0 0 480 180" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css}</style>
      <clipPath id="cp"><rect width="480" height="180" rx="{rad}"/></clipPath>
      <clipPath id="hc"><path d="M50 0 L93.3 25 V75 L50 100 L6.7 75 V25 Z"/></clipPath>
      <filter id="liq"><feTurbulence type="fractalNoise" baseFrequency="0.015"/><feDisplacementMap in="SourceGraphic" scale="30"/></filter>
      <filter id="bl"><feGaussianBlur stdDeviation="10"/></filter>
      </defs>
      <rect width="100%" height="100%" rx="{rad}" fill="#{bg}"/>
      <g clip-path="url(#cp)">{bg_layer}<rect width="100%" height="100%" fill="black" opacity="0.3"/></g>
      
      <g transform="translate(25,40)">
         <path d="M50 0 L93.3 25 V75 L50 100 L6.7 75 V25 Z" fill="none" stroke="{d['color']}" stroke-width="3"/>
         <g clip-path="url(#hc)"><image href="{d['avatar']}" width="100" height="100"/></g>
      </g>
      
      <g transform="translate(145,55)" class="float">
         <text y="0" font-family="Rajdhani" font-weight="700" font-size="30" fill="white" style="text-shadow:0 4px 10px rgba(0,0,0,0.5)">{d['name'].upper()}</text>
         <text y="25" font-family="JetBrains Mono" font-size="12" fill="{d['color']}">>> {d['l1']}</text>
         <text y="42" font-family="JetBrains Mono" font-size="11" fill="#ccc">{d['l2']}</text>
      </g>
      
      {ai_html}
      <text x="470" y="170" text-anchor="end" font-family="JetBrains Mono" font-size="8" fill="#555" opacity="0.8">UID: {d['id']}</text>
    </svg>"""

def render_cute(d, ai_msg, css, bg):
    # COMPLEX CUTE: Patterns + Floating Decor
    ai_html = ""
    if ai_msg:
        ai_html = f"""<g transform="translate(0,50)" class="bob">
            <rect width="280" height="30" rx="15" fill="white" opacity="0.8" stroke="{d['color']}" stroke-width="1"/>
            <text x="15" y="19" font-family="Fredoka" font-size="11" fill="#888">🐰 {ai_msg.capitalize()}</text>
        </g>"""

    return f"""<svg width="480" height="160" viewBox="0 0 480 160" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css}</style>
      <pattern id="dot" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="2" fill="{d['color']}" opacity="0.2"/></pattern>
      <clipPath id="cc"><circle cx="60" cy="60" r="50"/></clipPath></defs>
      
      <rect width="480" height="160" rx="30" fill="#FFFAFA"/>
      <!-- Animated Cloud BG -->
      <g class="cloud-move"><rect width="600" height="160" fill="url(#dot)"/></g>
      
      <rect x="5" y="5" width="470" height="150" rx="25" fill="none" stroke="{d['color']}" stroke-width="4" stroke-dasharray="15 10" opacity="0.3"/>
      
      <g transform="translate(20,20)">
         <circle cx="60" cy="60" r="55" fill="{d['color']}"/>
         <circle cx="60" cy="60" r="50" fill="white"/>
         <image href="{d['avatar']}" width="120" height="120" clip-path="url(#cc)"/>
      </g>
      
      <g transform="translate(150,45)">
         <text y="0" font-family="Fredoka" font-weight="600" font-size="28" fill="#555">{d['name']}</text>
         <text y="25" font-family="Fredoka" font-size="13" fill="{d['color']}">✨ {d['l1']} {d['l2']}</text>
         {ai_html}
      </g>
      
      <!-- Decor -->
      <text x="430" y="40" font-size="24" class="bob">☁️</text>
      <text x="400" y="130" font-size="18" class="bob" style="animation-delay:1s">💖</text>
    </svg>"""

def render_terminal(d, ai_msg, css, bg):
    # COMPLEX TERMINAL: Scanlines + Line Numbers + Syntax Highlight
    ai_line = ""
    if ai_msg:
        ai_line = f"""
        <text x="15" y="90" font-family="Fira Code" font-size="12" fill="#569CD6">ai.query</text>
        <text x="75" y="90" font-family="Fira Code" font-size="12" fill="#D4D4D4">(</text>
        <text x="82" y="90" font-family="Fira Code" font-size="12" fill="#CE9178">"USER_STATS"</text>
        <text x="175" y="90" font-family="Fira Code" font-size="12" fill="#D4D4D4">)</text>
        <text x="15" y="110" font-family="Fira Code" font-size="12" fill="#6A9955">// {ai_msg}<tspan class="blink">_</tspan></text>
        """

    return f"""<svg width="480" height="160" viewBox="0 0 480 160" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css}</style>
      <pattern id="lines" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" opacity="0.3"/></pattern>
      </defs>
      
      <rect width="100%" height="100%" rx="6" fill="#1e1e1e"/>
      <rect width="100%" height="25" rx="6" fill="#252526"/>
      <rect y="10" width="100%" height="15" fill="#252526"/> <!-- Hide top round corners for header -->
      
      <circle cx="20" cy="12" r="5" fill="#ff5f56"/>
      <circle cx="40" cy="12" r="5" fill="#ffbd2e"/>
      <circle cx="60" cy="12" r="5" fill="#27c93f"/>
      <text x="240" y="17" text-anchor="middle" font-family="Fira Code" font-size="10" fill="#888">status.json</text>
      
      <g transform="translate(10, 30)">
         <!-- Line Numbers -->
         <text x="0" y="20" font-family="Fira Code" font-size="10" fill="#555">1</text>
         <text x="0" y="45" font-family="Fira Code" font-size="10" fill="#555">2</text>
         
         <g transform="translate(20, 0)">
            <text y="20" font-family="Fira Code" font-size="12" fill="#9CDCFE">"user"</text>
            <text y="20" x="45" font-family="Fira Code" font-size="12" fill="#D4D4D4">: </text>
            <text y="20" x="60" font-family="Fira Code" font-size="12" fill="#CE9178">"{d['name']}"</text>
            
            <text y="45" font-family="Fira Code" font-size="12" fill="#9CDCFE">"status"</text>
            <text y="45" x="60" font-family="Fira Code" font-size="12" fill="#D4D4D4">: </text>
            <text y="45" x="75" font-family="Fira Code" font-size="12" fill="{d['color']}">"{d['l1']} {d['l2']}"</text>
         </g>
         
         {ai_line}
      </g>
      
      <!-- Scanline Overlay -->
      <rect width="100%" height="100%" fill="url(#lines)" opacity="0.2" pointer-events="none"/>
      <rect width="100%" height="2" fill="rgba(255,255,255,0.1)" class="scanline" pointer-events="none"/>
      
      <!-- Avatar Sticker -->
      <image href="{d['avatar']}" x="390" y="40" width="70" height="70" opacity="0.9" rx="5"/>
    </svg>"""

def render_pro(d, msg):
    # Static Clean Business Style
    msg_html = f'<text y="85" font-family="Arial" font-size="10" fill="#888" font-style="italic">NOTE: {msg}</text>' if msg else ""
    return f"""<svg width="480" height="130" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><clipPath id="s"><rect width="90" height="90" rx="4"/></clipPath></defs>
      <rect width="478" height="128" x="1" y="1" rx="4" fill="#FFFFFF" stroke="#e1e4e8"/>
      <rect width="6" height="128" x="1" y="1" rx="1" fill="{d['color']}"/>
      <g transform="translate(30,25)">
         <image href="{d['avatar']}" width="90" height="90" clip-path="url(#s)"/>
         <rect width="90" height="90" rx="4" fill="none" stroke="rgba(0,0,0,0.1)"/>
      </g>
      <g transform="translate(140,35)" font-family="Arial, Helvetica, sans-serif">
         <text y="0" font-weight="bold" font-size="22" fill="#333">{d['name']}</text>
         <text y="28" font-size="11" font-weight="bold" fill="#586069">{d['l1']}</text>
         <text y="42" font-size="11" fill="#586069">{d['l2']}</text>
         <line x1="0" y1="60" x2="300" y2="60" stroke="#eee"/>
         {msg_html}
      </g>
    </svg>"""

# ===========================
#        CONTROLLER
# ===========================

@app.route('/superbadge/<key>')
@app.route('/badge/<mode>/<key>')
def handler(key, mode="auto"):
    # 1. SETUP
    args = request.args
    target_mode = mode
    if mode == "auto":
        target_mode = 'user' if (key.isdigit() and len(str(key)) > 15) else 'discord'
        
    # 2. DATA
    data = fetch_data(key, target_mode, args)
    if not data: return Response('<svg xmlns="http://www.w3.org/2000/svg" width="300" height="50"><text x="10" y="30" fill="red">DATA ERROR</text></svg>', mimetype='image/svg+xml')

    # 3. SETTINGS
    anim_on = args.get('animations', 'true')
    ai_on = args.get('aifeatures', 'true')
    roast = args.get('roastMode', 'false') == 'true'
    style = args.get('style', 'hyper').lower()
    
    bg = args.get('bg', '09090b').replace('#','')
    rad = args.get('borderRadius', '20').replace('px','')

    # 4. AI LOGIC
    ai_role = "roast" if roast else "hud"
    full_text = f"{data.get('l1','')} {data.get('l2','')}"
    
    msg = consult_gemini(full_text, data['name'], ai_role, ai_on, data.get('type'))

    # 5. RENDER
    css = get_css(anim_on)
    
    if style == 'cute':
        svg = render_cute(data, msg, css, bg)
    elif style == 'terminal':
        svg = render_terminal(data, msg, css, bg)
    elif style == 'pro' or style == 'professional':
        svg = render_pro(data, msg)
    else:
        svg = render_hyper(data, msg, css, bg, rad)

    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
