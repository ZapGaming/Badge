import base64
import requests
import os
import html
import time
import google.generativeai as genai
from flask import Flask, Response, request

app = Flask(__name__)

# --- CONFIG ---
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

CACHE = {} 
HEADERS = {'User-Agent': 'HyperBadge/EasterEgg-v1'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

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
    base = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Rajdhani:wght@500;700&amp;family=Fredoka:wght@400;600&amp;family=Fira+Code:wght@500&amp;family=Outfit:wght@400;700&amp;display=swap');"
    
    if str(anim_enabled).lower() == 'false':
        return base + " * { animation: none !important; transition: none !important; }"
    
    return base + """
    /* Existing Hyper/Cute Anims */
    .drift { animation: d 40s linear infinite; transform-origin: center; } 
    @keyframes d { from{transform:rotate(0deg) scale(1.1)} to{transform:rotate(360deg) scale(1.1)} }
    .float { animation: f 6s ease-in-out infinite; } 
    @keyframes f { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-4px)} }
    .pulse { animation: p 2s infinite; } 
    @keyframes p { 50%{opacity:0.5} }
    .scroll-bg { animation: s 20s linear infinite; }
    @keyframes s { from {transform:translateY(0)} to {transform:translateY(-40px)} }
    .scanline { animation: sl 4s linear infinite; }
    @keyframes sl { 0% {transform:translateY(-100%)} 100% {transform:translateY(100%)} }
    .cursor { animation: b 1s step-end infinite; }
    @keyframes b { 50% { opacity: 0 } }
    .bob { animation: bb 3s ease-in-out infinite; } 
    @keyframes bb { 50% { transform: translateY(-5px); } }

    /* EASTER EGG ANIMS (Complex Fluid) */
    .flow-border { animation: borderFlow 4s linear infinite; stroke-dasharray: 200; }
    @keyframes borderFlow { to { stroke-dashoffset: -400; } }
    
    .hover-panel { animation: hov 8s ease-in-out infinite; }
    .hover-panel-2 { animation: hov 8s ease-in-out infinite reverse; }
    @keyframes hov { 0%,100%{transform:translateY(0) rotate(0deg)} 50%{transform:translateY(-5px) rotate(0.5deg)} }
    
    .gradient-spin { animation: gs 15s linear infinite; transform-origin: 50% 50%; }
    @keyframes gs { from{transform:rotate(0deg) scale(1.5)} to{transform:rotate(360deg) scale(1.5)} }
    """

# --- AI CORE ---
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
            prompt = f"Data context: '{status_text}' for user '{user_name}'. Output: Cool futuristic status text. Max 6 words. Uppercase."

        response = model.generate_content(prompt)
        text = html.escape(response.text.strip().replace('"','').replace("'", "")).upper()[:50]
        CACHE[key] = text
        return text
    except:
        return "DATA SECURED"

# --- DATA FETCH ---
def fetch_data(key, type_mode, args):
    try:
        # LANYARD (USER)
        if type_mode == 'user' or (type_mode == 'auto' and len(str(key)) > 15):
            r = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            d = r.json().get('data', {})
            if not d: return None
            
            u = d['discord_user']
            status = d['discord_status']
            
            show_display = args.get('showDisplayName','true').lower() == 'true'
            dname = u['global_name'] if show_display and u.get('global_name') else u['username']
            custom_idle = args.get('idleMessage', 'IDLE')
            
            l1, l2, col = "", "", "#555"
            is_music, art = False, None
            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#FF4444", "offline": "#555", "spotify": "#1DB954"}
            
            if d.get('spotify'):
                l1 = f"🎵 {d['spotify']['song']}"
                l2 = f"By {d['spotify']['artist']}"
                col = cols['spotify']
                art = get_base64(d['spotify'].get('album_art_url'))
                is_music = True
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
                "album_art": None, "id": str(d['id'])
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
                "album_art": None, "id": g['id']
            }
    except:
        return None

# ===========================
#      STYLES
# ===========================

# 5. EASTER EGG (macOS 26 / Fluid OS)
def render_easteregg(d, ai_msg, css):
    """
    Super complex layout with 3 floating glass panels, liquid aura background, 
    and RGB flowing borders.
    """
    bg_element = ""
    # Liquid Background logic
    if d['album_art']:
        bg_element = f"""
        <image href="{d['album_art']}" width="120%" height="120%" x="-10%" y="-10%" preserveAspectRatio="xMidYMid slice" filter="url(#heavyBlur)"/>
        <rect width="100%" height="100%" fill="black" opacity="0.4"/>
        """
    else:
        # The Multi-Color Liquid Aurora
        bg_element = f"""
        <rect width="100%" height="100%" fill="#000"/>
        <g class="gradient-spin" filter="url(#fluidMat)">
            <circle cx="100" cy="50" r="150" fill="{d['color']}"/>
            <circle cx="380" cy="150" r="180" fill="#00CFFF"/>
            <circle cx="200" cy="100" r="100" fill="#FF00FF"/>
        </g>
        """

    ai_html = ""
    if ai_msg:
        ai_html = f"""
        <!-- AI Glass Chip -->
        <g transform="translate(135, 105)" class="hover-panel-2">
            <rect width="320" height="40" rx="12" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.2)" stroke-width="1" filter="url(#glassShadow)"/>
            <rect width="320" height="40" rx="12" fill="url(#gloss)" opacity="0.3"/>
            <!-- Chip Icon -->
            <rect x="15" y="12" width="16" height="16" rx="4" fill="{d['color']}"/>
            <text x="40" y="24" font-family="Outfit" font-weight="700" font-size="12" fill="#E0E0FF">AI <tspan fill="rgba(255,255,255,0.6)">//</tspan> {ai_msg}</text>
        </g>
        """

    return f"""<svg width="480" height="180" viewBox="0 0 480 180" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs>
        <style>{css}</style>
        
        <!-- Filters for that 'Mac' glass feel -->
        <filter id="glassShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="8" stdDeviation="6" flood-color="#000" flood-opacity="0.3"/>
        </filter>
        <filter id="fluidMat"><feGaussianBlur stdDeviation="30"/><feComposite operator="in" in2="SourceGraphic"/></filter>
        <filter id="heavyBlur"><feGaussianBlur stdDeviation="15"/></filter>
        
        <clipPath id="mainClip"><rect width="480" height="180" rx="28"/></clipPath>
        <clipPath id="sqClip"><rect width="100" height="100" rx="20"/></clipPath>
        
        <linearGradient id="gloss" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="white" stop-opacity="0.2"/>
            <stop offset="50%" stop-color="white" stop-opacity="0"/>
            <stop offset="100%" stop-color="white" stop-opacity="0.1"/>
        </linearGradient>
        
        <linearGradient id="rainbowBorder">
            <stop offset="0%" stop-color="{d['color']}"/>
            <stop offset="50%" stop-color="#00FFFF"/>
            <stop offset="100%" stop-color="{d['color']}"/>
        </linearGradient>
      </defs>

      <!-- 1. CHASSIS AND BACKGROUND -->
      <g clip-path="url(#mainClip)">
         {bg_element}
         <!-- Scanline Grid Overlay -->
         <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <rect width="20" height="1" fill="white" opacity="0.05"/>
            <rect width="1" height="20" fill="white" opacity="0.05"/>
         </pattern>
         <rect width="100%" height="100%" fill="url(#grid)"/>
      </g>
      
      <!-- Border: Animated RGB Flow -->
      <rect x="2" y="2" width="476" height="176" rx="28" fill="none" stroke="url(#rainbowBorder)" stroke-width="4" class="flow-border" opacity="0.8"/>

      <!-- 2. UI LAYER: FLOATING ISLANDS -->
      
      <!-- ISLAND A: AVATAR (Left) -->
      <g transform="translate(25, 30)" class="hover-panel">
         <!-- Shadow Backplate -->
         <rect x="0" y="0" width="100" height="100" rx="24" fill="black" opacity="0.4" filter="url(#glassShadow)"/>
         <!-- Image -->
         <g clip-path="url(#sqClip)">
            <image href="{d['avatar']}" width="100" height="100"/>
            <!-- Inner shine -->
            <rect width="100%" height="100%" fill="url(#gloss)"/>
         </g>
         <!-- Glass Rim -->
         <rect width="100" height="100" rx="24" fill="none" stroke="white" stroke-width="1.5" opacity="0.4"/>
         
         <!-- OS Buttons (Mac Traffic Lights) -->
         <circle cx="15" cy="115" r="4" fill="#FF5F56"/>
         <circle cx="28" cy="115" r="4" fill="#FFBD2E"/>
         <circle cx="41" cy="115" r="4" fill="#27C93F"/>
      </g>

      <!-- ISLAND B: INFO (Right Top) -->
      <g transform="translate(135, 35)" class="hover-panel">
         <!-- Translucent Glass Backing -->
         <rect width="320" height="60" rx="16" fill="rgba(255,255,255,0.03)" stroke="rgba(255,255,255,0.15)" stroke-width="1" filter="url(#glassShadow)"/>
         
         <g transform="translate(20, 20)">
             <!-- Name -->
             <text x="0" y="8" font-family="Outfit" font-weight="700" font-size="26" fill="white" style="text-shadow: 0 4px 12px rgba(0,0,0,0.5)">{d['name']}</text>
             
             <!-- Line 1: Badge -->
             <rect x="0" y="18" width="220" height="16" rx="4" fill="{d['color']}" fill-opacity="0.15"/>
             <text x="5" y="29" font-family="JetBrains Mono" font-weight="800" font-size="9" fill="{d['color']}" letter-spacing="1">ACTIVITY // {d['l1'].upper()}</text>
             
             <!-- Line 2: Details -->
             <text x="228" y="29" text-anchor="end" font-family="Outfit" font-weight="400" font-size="11" fill="rgba(255,255,255,0.7)">{d['l2']}</text>
         </g>
      </g>

      <!-- ISLAND C: AI CHIP (Included dynamically above in ai_html) -->
      {ai_html}

      <!-- UID Watermark -->
      <text x="460" y="168" text-anchor="end" font-family="JetBrains Mono" font-size="8" fill="white" opacity="0.2">ID::{d['id']}</text>
    </svg>"""

# 1. HYPER (Liquid Shader)
def render_hyper(d, ai_msg, css, radius, bg):
    hex_path = "M50 0 L93.3 25 V75 L50 100 L6.7 75 V25 Z"
    
    ai_svg = ""
    if ai_msg:
        ai_svg = f"""<g transform="translate(145,120)" class="float" style="animation-delay:0.5s"><rect width="310" height="35" rx="6" fill="rgba(0,0,0,0.5)" stroke="rgba(255,255,255,0.1)"/><text x="15" y="23" font-family="Rajdhani" font-size="13" fill="#E0E0FF"><tspan fill="#5865F2" font-weight="bold">AI //</tspan> {ai_msg}<tspan class="pulse">_</tspan></text></g>"""

    bg_layer = f'<image href="{d["album_art"]}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" opacity="0.4" filter="url(#bl)"/>' if d['album_art'] else f'<g class="drift" opacity="0.4"><circle cx="20" cy="20" r="160" fill="{d["color"]}" filter="url(#liq)"/><circle cx="450" cy="160" r="140" fill="#5865F2" filter="url(#liq)"/></g>'

    return f"""<svg width="480" height="180" viewBox="0 0 480 180" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css}.u {{ font-family: 'Rajdhani', sans-serif; }} .m {{ font-family: 'JetBrains Mono', monospace; }}</style><filter id="liq"><feTurbulence type="fractalNoise" baseFrequency="0.015"/><feDisplacementMap in="SourceGraphic" scale="30"/></filter><filter id="bl"><feGaussianBlur stdDeviation="10"/></filter><clipPath id="cc"><rect width="480" height="180" rx="{radius}"/></clipPath><clipPath id="hc"><path d="{hex_path}"/></clipPath></defs>
      <rect width="100%" height="100%" rx="{radius}" fill="#{bg}"/>
      <g clip-path="url(#cc)">{bg_layer}<rect width="100%" height="100%" fill="black" opacity="0.1"/></g>
      <g transform="translate(25,40)"><path d="{hex_path}" fill="{d['color']}" opacity="0.2" transform="translate(0,3)"/><g clip-path="url(#hc)"><image href="{d['avatar']}" width="100" height="100"/></g><path d="{hex_path}" fill="none" stroke="{d['color']}" stroke-width="3"/></g>
      <g transform="translate(145,55)" class="float"><text y="0" class="u" font-size="30" font-weight="700" fill="white" style="text-shadow:0 4px 10px rgba(0,0,0,0.5)">{d['name'].upper()}</text><text y="25" class="m" font-size="12" fill="{d['color']}">>> {d['l1']}</text><text y="42" class="m" font-size="11" fill="#ccc">{d['l2']}</text></g>
      {ai_svg}<text x="470" y="170" text-anchor="end" class="m" font-size="8" fill="#555">UID: {d['id']}</text>
    </svg>"""

# 2. CUTE 
def render_cute(d, ai_msg, css, bg):
    c = d['color']
    ai_svg = f"""<g transform="translate(0,60)" class="bob"><rect width="280" height="30" rx="15" fill="white" opacity="0.8" stroke="{c}" stroke-width="1"/><text x="15" y="19" font-family="Fredoka" font-size="11" fill="#888">🐰 {ai_msg.capitalize()}</text></g>""" if ai_msg else ""
    return f"""<svg width="480" height="180" viewBox="0 0 480 180" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css}</style><pattern id="heart" width="40" height="40" patternUnits="userSpaceOnUse"><text x="0" y="20" font-size="10" opacity="0.1" fill="{c}">❤</text><text x="20" y="40" font-size="10" opacity="0.1" fill="{c}">❤</text></pattern><clipPath id="cr"><circle cx="65" cy="65" r="55"/></clipPath></defs>
      <rect width="480" height="180" rx="30" fill="#FFFAFA"/><rect width="100%" height="100%" fill="url(#heart)" class="scroll-bg"/><rect x="5" y="5" width="470" height="170" rx="25" fill="none" stroke="{c}" stroke-width="4" stroke-dasharray="15 10" opacity="0.4"/>
      <g transform="translate(25,25)"><circle cx="65" cy="65" r="60" fill="{c}"/><circle cx="65" cy="65" r="55" fill="white"/><image href="{d['avatar']}" width="130" height="130" clip-path="url(#cr)"/></g>
      <g transform="translate(170,55)"><text y="0" font-family="Fredoka" font-weight="600" font-size="30" fill="#555">{d['name']}</text><rect y="10" width="220" height="25" rx="12" fill="#F0F0F0"/><text x="10" y="26" font-family="Fredoka" font-size="12" fill="{c}">✨ {d['l1']} {d['l2']}</text>{ai_svg}</g><text x="430" y="50" font-size="24" class="bob">☁️</text>
    </svg>"""

# 3. TERMINAL
def render_terminal(d, ai_msg, css, bg):
    ai_svg = f"""<text x="15" y="100" fill="#569CD6">ai.query</text><text x="70" y="100" fill="#CE9178">("{d['name']}")</text><text x="15" y="120" fill="#6A9955">// {ai_msg}<tspan class="cursor">_</tspan></text>""" if ai_msg else ""
    return f"""<svg width="480" height="180" viewBox="0 0 480 180" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css}</style><pattern id="sl" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="black" opacity="0.3"/></pattern></defs>
      <rect width="100%" height="100%" rx="6" fill="#1e1e1e"/><rect width="100%" height="100%" fill="url(#sl)" pointer-events="none"/><rect width="100%" height="25" fill="#252526"/><circle cx="20" cy="12" r="5" fill="#ff5f56"/><circle cx="40" cy="12" r="5" fill="#ffbd2e"/><circle cx="60" cy="12" r="5" fill="#27c93f"/>
      <g transform="translate(15, 45)" font-family="Fira Code" font-size="12"><text y="0" fill="#C586C0">const</text> <text x="40" y="0" fill="#4FC1FF">usr</text> <text x="65" y="0" fill="#D4D4D4">=</text> <text x="80" y="0" fill="#CE9178">"{d['name']}"</text><text y="20" fill="#9CDCFE">usr.status</text> <text x="75" y="20" fill="#D4D4D4">=</text> <text x="90" y="20" fill="#B5CEA8">"{d['l1']} {d['l2']}"</text>{ai_svg}</g>
      <rect y="160" width="100%" height="20" fill="#5865F2"/><text x="10" y="173" font-family="Fira Code" font-size="10" fill="white">NORMAL</text>
      <image href="{d['avatar']}" x="380" y="40" width="80" height="80" opacity="0.9" rx="4"/>
    </svg>"""

# 4. PROFESSIONAL
def render_pro(d, msg, args):
    return f"""<svg width="480" height="140" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><defs><clipPath id="s"><rect width="90" height="90" rx="4"/></clipPath></defs><rect width="478" height="138" x="1" y="1" rx="4" fill="#FFFFFF" stroke="#e1e4e8"/><rect width="6" height="138" x="1" y="1" rx="1" fill="{d['color']}"/><g transform="translate(30,25)"><image href="{d['avatar']}" width="90" height="90" clip-path="url(#s)"/></g><g transform="translate(140,35)" font-family="Arial"><text y="0" font-weight="bold" font-size="22" fill="#333">{d['name']}</text><text y="30" font-size="11" font-weight="bold" fill="#586069">{d['l1']}</text><text y="45" font-size="11" fill="#586069">{d['l2']}</text></g></svg>"""

# --- ROUTER ---
@app.route('/superbadge/<key>')
@app.route('/badge/<mode>/<key>')
def handler(key, mode="auto"):
    args = request.args
    target = mode
    if mode == "auto": target = 'user' if (key.isdigit() and len(str(key)) > 15) else 'discord'
    data = fetch_data(key, target, args)
    if not data: return Response('<svg><text>Error</text></svg>', mimetype="image/svg+xml")

    # Settings
    roast = args.get('roastMode', 'false').lower() == 'true'
    anim = args.get('animations', 'true')
    ai_on = args.get('aifeatures', 'true')
    style = args.get('style', 'hyper').lower()
    bg = args.get('bg', '09090b').replace('#','')
    rad = args.get('borderRadius', '20').replace('px','')

    msg = consult_gemini(f"{data['l1']} {data['l2']}", data['name'], "roast" if roast else "hud", ai_on, data.get('type'))
    css = get_css(anim)

    if style == 'easteregg': svg = render_easteregg(data, msg, css)
    elif style == 'cute': svg = render_cute(data, msg, css, bg)
    elif style == 'terminal': svg = render_terminal(data, msg, css, bg)
    elif style == 'pro' or style == 'professional': svg = render_pro(data, msg, args)
    else: svg = render_hyper(data, msg, css, rad, bg)

    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
