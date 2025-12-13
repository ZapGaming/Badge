import base64
import requests
import os
import html
import re
import time
import google.generativeai as genai
from flask import Flask, Response, request

app = Flask(__name__)

# ===========================
#        CONFIGURATION
# ===========================
# AI is optional. If no key, it simply returns "SECURE LINK" for HUD text.
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

CACHE = {} 
HEADERS = {'User-Agent': 'HyperBadge/Compact-v25'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# ===========================
#      HELPER FUNCTIONS
# ===========================

def sanitize_xml(text):
    """Prevents XML crashes from weird unicode chars"""
    if not text: return ""
    text = str(text)
    # Remove control chars (0-31)
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

def get_css(bg_anim, fg_anim):
    # COMPACT FONTS: Clean, modern stack
    css = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Rajdhani:wght@600;800&amp;family=Outfit:wght@500;900&amp;display=swap');"
    
    # Define Animations (Keyframes)
    css += """
    @keyframes m1 { 0%{cx:10px; cy:10px} 50%{cx:300px; cy:80px} 100%{cx:10px; cy:10px} }
    @keyframes m2 { 0%{cx:400px; cy:100px} 50%{cx:100px; cy:20px} 100%{cx:400px; cy:100px} }
    @keyframes d { from{transform:rotate(0deg) scale(1.1)} to{transform:rotate(360deg) scale(1.1)} }
    @keyframes f { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-3px)} }
    @keyframes p { 50%{opacity:0.6} }
    """
    
    classes = ""
    # Foreground: Only add classes if explicitly enabled
    if str(fg_anim).lower() == 'true':
        classes += ".float {animation: f 6s ease-in-out infinite;} .pulse {animation: p 2s infinite;} "
    
    # Background: Only add classes if enabled
    if str(bg_anim).lower() == 'true':
        classes += ".mesh-1 {animation: m1 15s infinite ease-in-out;} .mesh-2 {animation: m2 20s infinite ease-in-out;} .drift {animation: d 40s linear infinite; transform-origin: center;}"

    return css + classes

# ===========================
#        AI LOGIC
# ===========================

def consult_gemini(status_text, user_name, mode, enabled):
    if str(enabled).lower() == 'false': return None
    if not GOOGLE_API_KEY: return None 
    
    key = f"AI_{user_name}_{status_text}_{mode}"
    if key in CACHE: return CACHE[key]

    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"System status for '{user_name}': '{status_text}'. Tech HUD style. Uppercase. Max 6 words."
        response = model.generate_content(prompt)
        text = sanitize_xml(response.text.strip().replace('"','')).upper()[:45]
        CACHE[key] = text
        return text
    except:
        return "SECURE LINK"

# ===========================
#       DATA FETCHERS
# ===========================

def fetch_data(key, type_mode, args):
    try:
        # --- 1. DISCORD SERVER (Compact Mode) ---
        if type_mode == 'discord':
            r = requests.get(f"https://discord.com/api/v10/invites/{key}?with_counts=true", headers=HEADERS, timeout=4)
            d = r.json()
            g = d.get('guild')
            if not g: return None
            
            # CONFIG FOR COMPACT MODE
            # We map: 
            # name -> Small Label ("TOTAL MEMBERS")
            # l1   -> BIG STAT (Member Count)
            # l2   -> Small Subtext (Online Count)
            
            forced_label = args.get('name', 'MEMBERS')
            
            return {
                "type": "discord",
                "name": sanitize_xml(forced_label), 
                "l1": f"{d['approximate_member_count']:,}", 
                "l2": f"{d.get('approximate_presence_count',0):,} ONLINE",
                "color": "#5865F2", 
                "avatar": get_base64(f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png") if g.get('icon') else EMPTY,
                "is_music": False, "bg_img": None, "id": g['id']
            }

        # --- 2. LANYARD USER ---
        else:
            r = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            d = r.json().get('data', {})
            if not d: return None
            u = d['discord_user']
            status = d['discord_status']
            
            dname = u['global_name'] if (args.get('showDisplayName','true').lower()=='true' and u.get('global_name')) else u['username']
            final_name = sanitize_xml(args.get('name', dname))
            custom_idle = args.get('idleMessage', 'IDLE')
            
            l1, l2, col = "", "", "#555"
            is_music, art, progress = False, None, 0.0
            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#FF4444", "offline": "#555", "spotify": "#1DB954"}
            
            if d.get('spotify'):
                s = d['spotify']
                l1 = f"🎵 {s['song']}"; l2 = f"By {s['artist']}"; col = cols['spotify']
                art = get_base64(s.get('album_art_url')); is_music = True
                try: 
                    now = time.time()*1000
                    p = min(max(((now - s['timestamps']['start']) / (s['timestamps']['end'] - s['timestamps']['start']))*100, 0), 100)
                    progress = p
                except: pass
            else:
                col = cols.get(status, "#555")
                found = False
                for act in d.get('activities', []):
                    if act['type'] == 0: l1="PLAYING:"; l2=act['name']; found=True; break
                    if act['type'] == 4: l1="NOTE:"; l2=act.get('state','Active'); found=True; break
                if not found:
                    l1="STATUS:"; l2="ONLINE" if status=="online" else custom_idle.upper()

            return {
                "type": "user",
                "name": final_name,
                "l1": sanitize_xml(l1)[:30], "l2": sanitize_xml(l2)[:35],
                "color": col, 
                "avatar": get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png"),
                "bg_img": art, "is_music": is_music, "progress": progress, "id": u['id']
            }
    except: return None

# ===========================
#      RENDER ENGINES
# ===========================

def render_compact(d, ai_msg, css, radius, bg_col):
    """
    SPECIAL RENDERER FOR SERVERS:
    - 400x110 dimensions (Smaller)
    - Big Number, Small Labels
    - Forced Static Foreground (No .float classes applied to text)
    - Animated Mesh Background
    """
    
    # 1. Background Mesh (Animated by default via css, can be turned off in css generator)
    bg = f"""
    <rect width="100%" height="100%" fill="#{bg_col}" />
    <circle r="80" fill="#5865F2" opacity="0.4" class="mesh-1" filter="url(#b)" />
    <circle r="60" fill="#00AAFF" opacity="0.3" class="mesh-2" filter="url(#b)" />
    """
    
    return f"""<svg width="400" height="110" viewBox="0 0 400 110" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css}
        .mono {{ font-family: 'JetBrains Mono', monospace; }}
        .big {{ font-family: 'Outfit', sans-serif; font-weight: 900; }}
      </style>
      <clipPath id="cp"><rect width="400" height="110" rx="{radius}"/></clipPath>
      <clipPath id="av"><rect width="70" height="70" rx="14"/></clipPath>
      <filter id="b"><feGaussianBlur stdDeviation="25"/></filter>
      </defs>
      
      <!-- BG -->
      <g clip-path="url(#cp)">{bg}
         <!-- Glass shine -->
         <path d="M0 0 L400 0 L0 110 Z" fill="white" opacity="0.05"/>
         <rect width="100%" height="100%" fill="rgba(255,255,255,0.02)" stroke="rgba(255,255,255,0.1)" stroke-width="2" rx="{radius}"/>
      </g>

      <!-- CONTENT (STATIC POSITION) -->
      <g transform="translate(20, 20)">
         <!-- Icon -->
         <g>
            <rect width="70" height="70" rx="14" fill="rgba(0,0,0,0.3)"/>
            <g clip-path="url(#av)"><image href="{d['avatar']}" width="70" height="70"/></g>
            <rect width="70" height="70" rx="14" fill="none" stroke="{d['color']}" stroke-width="2"/>
         </g>
         
         <!-- Stats Block -->
         <g transform="translate(90, 5)">
            <text x="0" y="10" font-family="Rajdhani" font-weight="700" font-size="12" fill="#AAA" letter-spacing="2">{d['name']}</text>
            <text x="0" y="45" class="big" font-size="38" fill="white" letter-spacing="-1">{d['l1']}</text>
            <text x="0" y="62" class="mono" font-size="10" fill="{d['color']}">● {d['l2']}</text>
         </g>
      </g>
    </svg>"""

def render_standard(d, ai_msg, css, radius, bg_col):
    """Standard Large Card for Users"""
    # ... (Reusing the robust hyper renderer from before) ...
    bg_lyr = f'<image href="{d["bg_img"]}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" opacity="0.4" filter="url(#bl)"/>' if d['bg_img'] else f'<g class="drift" opacity="0.4"><circle cx="20" cy="20" r="160" fill="{d["color"]}" filter="url(#liq)"/><circle cx="450" cy="160" r="140" fill="#5865F2" filter="url(#liq)"/></g>'
    ai_div = f'<g transform="translate(130, 95)" class="float"><rect width="320" height="30" rx="6" fill="rgba(0,0,0,0.5)" stroke="rgba(255,255,255,0.1)"/><text x="15" y="19" font-family="Rajdhani" font-size="12" fill="#E0E0FF"><tspan fill="{d["color"]}">AI //</tspan> {ai_msg}<tspan class="pulse">_</tspan></text></g>' if ai_msg else ""

    return f"""<svg width="480" height="150" viewBox="0 0 480 150" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css}.ui {{font-family:'Rajdhani',sans-serif;}}</style>
      <filter id="liq"><feTurbulence type="fractalNoise" baseFrequency="0.01"/><feDisplacementMap in="SourceGraphic" scale="30"/></filter>
      <filter id="bl"><feGaussianBlur stdDeviation="12"/></filter>
      <clipPath id="cc"><rect width="480" height="150" rx="{radius}"/></clipPath>
      <clipPath id="hc"><path d="M50 0 L93.3 25 V75 L50 100 L6.7 75 V25 Z"/></clipPath>
      </defs>
      <rect width="100%" height="100%" rx="{radius}" fill="#{bg_col}"/>
      <g clip-path="url(#cc)">{bg_lyr}<rect width="100%" height="100%" fill="black" opacity="0.2"/></g>
      <g transform="translate(25,25)"><path d="M50 0 L93.3 25 V75 L50 100 L6.7 75 V25 Z" fill="{d['color']}" opacity="0.2" transform="translate(0,3)"/><g clip-path="url(#hc)"><image href="{d['avatar']}" width="100" height="100"/></g><path d="M50 0 L93.3 25 V75 L50 100 L6.7 75 V25 Z" fill="none" stroke="{d['color']}" stroke-width="3"/></g>
      <g transform="translate(145,40)" class="float"><text y="0" class="ui" font-size="28" fill="white" font-weight="700">{d['name']}</text><text y="22" font-family="JetBrains Mono" font-size="11" fill="{d['color']}">>> {d['l1']}</text><text y="38" font-family="JetBrains Mono" font-size="10" fill="#CCC">{d['l2']}</text></g>
      {ai_div}
    </svg>"""

# ===========================
#        CONTROLLER
# ===========================

@app.route('/superbadge/<key>')
@app.route('/badge/<mode>/<key>')
def handler(key, mode="auto"):
    args = request.args
    target = mode
    if mode == "auto": target = 'user' if (key.isdigit() and len(str(key)) > 15) else 'discord'
    
    data = fetch_data(key, target, args)
    if not data: return Response('<svg xmlns="http://www.w3.org/2000/svg" width="300" height="50"><rect width="100%" height="100%" fill="black"/><text x="10" y="30" fill="red" font-family="sans-serif">INVALID ID</text></svg>', mimetype="image/svg+xml")

    # Settings
    ai_on = args.get('aifeatures', 'true')
    # Default for Servers = BG Anim ON, FG Anim OFF
    default_bg = 'true'
    default_fg = 'false' if data['type'] == 'discord' else 'true'
    
    bg_anim = args.get('bgAnimations', default_bg)
    fg_anim = args.get('fgAnimations', default_fg)
    
    # AI Generation
    msg = None
    if data['type'] != 'discord' and ai_on == 'true': # Skip AI for member count to keep it clean
        msg = consult_gemini(f"{data['l1']} {data['l2']}", data['name'], "normal", ai_on)

    css = get_css(bg_anim, fg_anim)
    bg_col = args.get('bg', '09090b').replace('#','')
    radius = args.get('borderRadius', '20').replace('px', '')

    # RENDERER SELECTION
    if data['type'] == 'discord':
        # Use specialized Compact renderer for Member Counts
        svg = render_compact(data, msg, css, radius, bg_col)
    else:
        # Use standard Hyper renderer for Users
        svg = render_standard(data, msg, css, radius, bg_col)

    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
