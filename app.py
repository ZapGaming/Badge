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

# --- CONFIG & CACHE ---
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# High-Grade Cache to prevent API Bans
CACHE = {} 
CACHE_TTL = 120 # 2 minutes

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
EMPTY_IMG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# --- UTILITY ---
def get_base64(url):
    """Converts image URL to Base64 safely."""
    if not url: return EMPTY_IMG
    try:
        r = requests.get(url, headers=HEADERS, timeout=3)
        if r.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(r.content).decode('utf-8')}"
    except:
        pass
    return EMPTY_IMG

# --- AI CORE ---
def consult_gemini(status_text, user_name, mode, is_music):
    if not GOOGLE_API_KEY: return "AI OFFLINE (NO KEY)"
    
    # Memoize AI responses to save API quota/speed
    cache_key = f"AI_{user_name}_{status_text}_{mode}"
    if cache_key in CACHE: return CACHE[cache_key]

    try:
        model = genai.GenerativeModel('gemini-pro')
        
        if mode == "roast":
            ctx = "playing" if is_music else "doing"
            prompt = f"ROAST '{user_name}' who is {ctx} '{status_text}'. Savage, uppercase, max 7 words."
        else:
            prompt = f"Status report for '{user_name}': '{status_text}'. Sci-Fi HUD style. Uppercase. Max 6 words."
        
        response = model.generate_content(prompt)
        text = response.text.strip().replace('"', '').replace("'", "")
        
        # Clean & Cache
        final_text = html.escape(text[:45]).upper()
        CACHE[cache_key] = final_text
        return final_text
    except:
        return "DATA ENCRYPTED"

# --- UNIVERSAL DATA FETCHERS ---

def fetch_discord_invite(code):
    try:
        r = requests.get(f"https://discord.com/api/v10/invites/{code}?with_counts=true", headers=HEADERS, timeout=4)
        if r.status_code != 200: return None
        d = r.json()
        g = d['guild']
        icon = f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png" if g.get('icon') else None
        
        return {
            "type": "server",
            "name": html.escape(g['name']),
            "line_1": "MEMBERS:",
            "line_2": f"{d['approximate_member_count']:,}",
            "status": f"{d['approximate_presence_count']:,} ONLINE",
            "color": "#5865F2", # Blurple
            "is_music": False,
            "image": get_base64(icon)
        }
    except:
        return None

def fetch_github_user(username):
    try:
        r = requests.get(f"https://api.github.com/users/{username}", headers=HEADERS, timeout=4)
        if r.status_code != 200: return None
        d = r.json()
        
        return {
            "type": "github",
            "name": html.escape(d['login']),
            "line_1": "REPOSITORIES:",
            "line_2": str(d['public_repos']),
            "status": f"{d['followers']} FOLLOWERS",
            "color": "#FFFFFF",
            "is_music": False,
            "image": get_base64(d['avatar_url'])
        }
    except:
        return None

def fetch_lanyard_user(user_id, args):
    try:
        r = requests.get(f"https://api.lanyard.rest/v1/users/{user_id}", headers=HEADERS, timeout=4)
        data = r.json()
        if not data['success']: return None
        
        d = data['data']
        u = d['discord_user']
        status = d['discord_status']
        
        # Args Handling
        show_global = args.get('showDisplayName', 'true').lower() == 'true'
        custom_idle = args.get('idleMessage', 'IDLE')
        
        # Name Logic
        name = u['username']
        if show_global and u.get('global_name'): name = u['global_name']
        
        # Color Map
        colors = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#FF4444", "offline": "#555", "spotify": "#1DB954"}
        
        # Activity Logic
        line_1, line_2, active_color = "", "", colors.get(status, "#555")
        is_music, album_art = False, None
        
        if d.get('spotify'):
            s = d['spotify']
            line_1 = f"🎵 {s['song']}"
            line_2 = f"By {s['artist']}"
            active_color = colors['spotify']
            is_music = True
            if s.get('album_art_url'): album_art = get_base64(s['album_art_url'])
        else:
            found = False
            for act in d.get('activities', []):
                if act['type'] == 0: 
                    line_1 = "PLAYING:"; line_2 = act['name']; found = True; break
                if act['type'] == 4:
                    line_1 = "NOTE:"; line_2 = act.get('state', ''); found = True; break
            
            if not found:
                if status == "online": line_1 = "STATUS:"; line_2 = "ONLINE"; 
                else: line_1 = "STATUS:"; line_2 = custom_idle.upper()

        return {
            "type": "user",
            "id": u['id'],
            "name": html.escape(name),
            "line_1": html.escape(line_1),
            "line_2": html.escape(line_2),
            "status": status.upper(),
            "color": active_color,
            "is_music": is_music,
            "album_art": album_art, # Special bg for Hyper mode
            "image": get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png")
        }
    except:
        return None

# ==========================================
#       MASTER RENDER ENGINE
# ==========================================

def render_svg(data, ai_msg, args):
    style = args.get('style', 'hyper').lower()
    
    # Common Styling Logic
    bg_override = args.get('bg')
    radius = args.get('borderRadius', '20').replace('px','')
    
    if bg_override: 
        bg_fill = f"#{bg_override}" if not bg_override.startswith('#') else bg_override
    else: 
        bg_fill = "#09090b"

    # Hexagon Logic (Used in Hyper/Terminal)
    hex_path = "M50 0 L93.3 25 V75 L50 100 L6.7 75 V25 Z"

    # --- STYLE 1: HYPER (Advanced GLSL & Album Art) ---
    if style == 'hyper':
        bg_content = ""
        if data.get('album_art'):
            bg_content = f"""
            <image href="{data['album_art']}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" filter="url(#blurStrong)" opacity="0.5"/>
            <rect width="100%" height="100%" fill="black" opacity="0.3"/>
            """
        else:
            bg_content = f"""
            <g class="drift" opacity="0.35">
                <circle cx="20" cy="20" r="150" fill="{data['color']}" filter="url(#liq)"/>
                <circle cx="450" cy="150" r="130" fill="#5865F2" filter="url(#liq)"/>
            </g>"""

        return f"""<svg version="1.1" width="480" height="180" viewBox="0 0 480 180" 
            xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
            xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            xmlns:xhtml="http://www.w3.org/1999/xhtml"
            xmlns:math="http://www.w3.org/1998/Math/MathML"
            xmlns:chillax="http://chillax.dev/badge">
        <metadata>
            <rdf:RDF><chillax:data server="{data['name']}" stat="{data['line_2']}"/></rdf:RDF>
        </metadata>
        <defs>
            <style>@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Rajdhani:wght@500;700&amp;display=swap');
            .ui {{ font-family: 'Rajdhani', sans-serif; }} .mono {{ font-family: 'JetBrains Mono', monospace; }}
            .drift {{ animation: d 20s linear infinite; transform-origin: center; }} @keyframes d {{ from{{transform:rotate(0deg)}} to{{transform:rotate(360deg)}} }}
            .fly {{ animation: f 6s ease-in-out infinite; }} @keyframes f {{ 50%{{transform:translateY(-3px)}} }}
            .pulse {{ animation: p 2s infinite; }} @keyframes p {{ 50%{{opacity:0.5}} }}
            </style>
            <filter id="liq" x="-20%" y="-20%" width="140%" height="140%"><feTurbulence type="fractalNoise" baseFrequency="0.01" /><feDisplacementMap in="SourceGraphic" scale="30"/></filter>
            <filter id="blurStrong"><feGaussianBlur stdDeviation="8"/></filter>
            <clipPath id="cardClip"><rect width="480" height="180" rx="{radius}"/></clipPath>
            <clipPath id="hex"><path d="{hex_path}"/></clipPath>
        </defs>
        
        <rect width="480" height="180" rx="{radius}" fill="{bg_fill}"/>
        <g clip-path="url(#cardClip)">{bg_content}<rect width="480" height="180" fill="white" opacity="0.02"/></g>
        
        <!-- UI -->
        <g transform="translate(25,40)">
            <path d="{hex_path}" fill="{data['color']}" opacity="0.2" transform="translate(0,3)"/>
            <g clip-path="url(#hex)"><image href="{data['image']}" width="100" height="100"/></g>
            <path d="{hex_path}" fill="none" stroke="{data['color']}" stroke-width="3"/>
        </g>
        
        <g transform="translate(145,50)" class="fly">
            <text y="0" class="ui" font-weight="700" font-size="30" fill="white" text-shadow="0 4px 10px rgba(0,0,0,0.5)">{data['name'].upper()}</text>
            <text y="25" class="mono" font-size="12" fill="{data['color']}" font-weight="bold">>> {data['line_1'][:25]}</text>
            <text y="42" class="mono" font-size="11" fill="#CCC">{data['line_2'][:35]}</text>
        </g>
        
        <!-- AI Box -->
        <g transform="translate(145,120)" class="fly" style="animation-delay:1s">
            <rect width="310" height="35" rx="6" fill="rgba(0,0,0,0.5)" stroke="rgba(255,255,255,0.1)"/>
            <text x="15" y="23" class="ui" font-size="13" fill="#E0E0FF"><tspan fill="#5865F2" font-weight="bold">AI</tspan> // {ai_msg}<tspan class="pulse">_</tspan></text>
        </g>
        </svg>"""

    # --- STYLE 2: CUTE (Kawaii) ---
    elif style == 'cute':
        return f"""<svg width="480" height="160" viewBox="0 0 480 160" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
        <defs><style>@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600&amp;display=swap');
        .bob {{ animation: b 3s ease-in-out infinite; }} @keyframes b {{ 50%{{transform:translateY(-5px)}} }}</style>
        <clipPath id="c"><circle cx="60" cy="60" r="50"/></clipPath></defs>
        <rect width="480" height="160" rx="30" fill="#FFFAFA"/>
        <rect x="5" y="5" width="470" height="150" rx="25" fill="none" stroke="{data['color']}" stroke-width="3" stroke-dasharray="10 6" opacity="0.3"/>
        <g transform="translate(20,20)">
            <circle cx="60" cy="60" r="54" fill="{data['color']}"/><image href="{data['image']}" width="120" height="120" clip-path="url(#c)"/>
        </g>
        <g transform="translate(150,45)">
            <text y="0" font-family="Fredoka" font-size="26" font-weight="600" fill="#555">{data['name']}</text>
            <text y="25" font-family="Fredoka" font-size="12" fill="{data['color']}">♥ {data['line_1']} {data['line_2']}</text>
            <g transform="translate(0,45)" class="bob">
                <rect width="280" height="35" rx="10" fill="#F0F8FF"/><text x="15" y="22" font-family="Fredoka" font-size="11" fill="#777">💬 {ai_msg.lower().capitalize()}</text>
            </g>
        </g>
        </svg>"""

    # --- STYLE 3: TERMINAL (Retro) ---
    else:
        return f"""<svg width="480" height="150" xmlns="http://www.w3.org/2000/svg">
        <style>@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@500&amp;display=swap');</style>
        <rect width="100%" height="100%" rx="6" fill="#0d1117" stroke="#30363d"/>
        <circle cx="20" cy="20" r="5" fill="#ff5f56"/><circle cx="40" cy="20" r="5" fill="#ffbd2e"/><circle cx="60" cy="20" r="5" fill="#27c93f"/>
        <g transform="translate(25,60)" font-family="Fira Code" font-size="12" fill="#c9d1d9">
            <text>> usr = new Entity("{data['name']}")</text>
            <text y="20">> usr.status = "{data['line_1']} {data['line_2']}"</text>
            <text y="40">> sys.analysis()</text>
            <text y="65" fill="#8b949e"># {ai_msg}_</text>
        </g>
        </svg>"""

# --- ROUTES ---

@app.route('/badge/<mode>/<key>')
@app.route('/superbadge/<key>') # Backward compatibility
def handler(mode="user", key=None):
    # normalize args
    args = request.args
    
    # Determine Logic
    # If route is /superbadge/ID, infer logic. Else use /badge/discord|github/ID
    target_data = None
    
    if mode == "user" and not key: key = mode # Fix flash URL logic if any
    
    # 1. Fetch
    if mode == "discord" or (mode=="user" and len(str(key)) < 15):
        # Invite Code
        target_data = fetch_discord_invite(key)
    elif mode == "github":
        # Github User
        target_data = fetch_github_user(key)
    else:
        # Default to Lanyard User ID
        target_data = fetch_lanyard_user(key, args)

    if not target_data:
        return Response('<svg><text y="20">Error: Invalid ID or API Failure</text></svg>', mimetype="image/svg+xml")

    # 2. AI
    roast = args.get('roastMode', 'false').lower() == 'true'
    ai_mode = "roast" if roast else "hud"
    # Construct context string for AI
    context_str = f"{target_data.get('line_1','')} {target_data.get('line_2','')}"
    
    msg = consult_gemini(context_str, target_data['name'], ai_mode, target_data.get('is_music', False))

    # 3. Render
    svg = render_svg(target_data, msg, args)
    
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache"})

@app.route('/')
def index():
    return "CHILLAX ENGINE ONLINE"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
