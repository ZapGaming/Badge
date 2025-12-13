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
    cache_key = f"AI_{user_name}_{status_text}_{mode}"import base64
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
HEADERS = {'User-Agent': 'HyperBadge/Universal-v10'}
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

def get_css(anim_enabled):
    """Returns CSS blocks, optionally stripping animations for performance"""
    # Base Fonts
    css = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&family=Rajdhani:wght@500;700&family=Fredoka:wght@400;600&family=Fira+Code:wght@500&display=swap');"
    
    if str(anim_enabled).lower() == 'false':
        return css + " * { animation: none !important; transition: none !important; }"
    
    # Keyframes
    css += """
    .drift { animation: d 40s linear infinite; transform-origin: center; } 
    @keyframes d { from{transform:rotate(0deg) scale(1.1)} to{transform:rotate(360deg) scale(1.1)} }
    
    .float { animation: f 6s ease-in-out infinite; } 
    @keyframes f { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-4px)} }
    
    .pulse { animation: p 2s infinite; } 
    @keyframes p { 50%{opacity:0.5} }
    
    .bob { animation: b 3s ease-in-out infinite; } 
    @keyframes b { 50%{transform:translateY(-5px)} }
    
    .spin { animation: r 4s linear infinite; transform-origin: 50% 50%; } 
    @keyframes r { to{transform:rotate(360deg)} }
    
    .blink { animation: k 1s step-end infinite; } 
    @keyframes k { 50% { opacity: 0 } }
    """
    return css

# ===========================
#        AI NEURAL CORE
# ===========================

def consult_gemini(status_text, name, mode, enabled, data_type):
    if str(enabled).lower() == 'false': return "AI MODULE DISABLED"
    if not GOOGLE_API_KEY: return "AI OFFLINE (NO KEY)"
    
    # Memoize response
    key = f"AI_{name}_{status_text}_{mode}"
    if key in CACHE: return CACHE[key]

    try:
        model = genai.GenerativeModel('gemini-pro')
        
        # Dynamic Prompting based on Mode & Type
        if mode == "roast":
            context = f"User '{name}' status: '{status_text}'."
            task = "Write a BRUTAL, SAVAGE roast. Mock their music taste, game skill, or github commit history. Uppercase."
        else:
            if data_type == 'github':
                task = f"GitHub User '{name}'. Stats: '{status_text}'. Write a short technical summary line. Tech/Sci-fi style."
            elif data_type == 'discord':
                task = f"Discord Server '{name}'. Stats: '{status_text}'. Write a HUD status line."
            else:
                task = f"User '{name}' activity: '{status_text}'. Write a futuristic OS status report. Uppercase. Technobabble."

        response = model.generate_content(f"{task}\nMAX 7 WORDS. NO QUOTES. OUTPUT TEXT ONLY.")
        clean_text = html.escape(response.text.strip().replace('"','').replace("'", "")).upper()[:55]
        
        CACHE[key] = clean_text
        return clean_text
    except Exception as e:
        print(e)
        return "DATA STREAM ENCRYPTED"

# ===========================
#       DATA HARVESTERS
# ===========================

def fetch_data(key, type_mode, args):
    """Master Fetcher that handles Lanyard, Discord Invites, and GitHub."""
    
    # --- 1. LANYARD (USER) ---
    if type_mode == 'user' or (type_mode == 'auto' and len(str(key)) > 15):
        try:
            r = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            d = r.json().get('data', {})
            if not d: raise ValueError("User not found")
            
            u = d['discord_user']
            status = d['discord_status']
            
            # Args processing
            dname = u['global_name'] if (args.get('showDisplayName')=='true' and u.get('global_name')) else u['username']
            idle_msg = args.get('idleMessage', 'SYSTEM IDLE')
            
            # Variables
            l1, l2, col = "", "", "#555"
            is_music, art, progress = False, None, 0
            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#FF4444", "offline": "#555", "spotify": "#1DB954"}
            
            if d.get('spotify'):
                s = d['spotify']
                l1 = s['song']; l2 = f"By {s['artist']}"; col = cols['spotify']
                is_music = True
                if s.get('album_art_url'): art = get_base64(s['album_art_url'])
                try: 
                    now_ms = time.time()*1000
                    progress = min(max(((now_ms - s['timestamps']['start']) / (s['timestamps']['end'] - s['timestamps']['start']))*100, 0), 100)
                except: progress = 0
            else:
                found = False
                for act in d.get('activities', []):
                    if act['type'] == 0: l1="PLAYING:"; l2=act['name']; found=True; break
                    if act['type'] == 4: l1="NOTE:"; l2=act.get('state','Active'); found=True; break
                    if act['type'] == 2: l1="MEDIA:"; l2="Audio Stream"; found=True; break
                
                if not found:
                    l1="CURRENTLY:"; l2="ONLINE" if status=="online" else idle_msg.upper()
                col = cols.get(status, "#555")

            return {
                "valid": True, "type": "user",
                "name": html.escape(dname),
                "l1": html.escape(l1)[:25], "l2": html.escape(l2)[:30],
                "color": col, "image": get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png"),
                "album_art": art, "is_music": is_music, "progress": progress, "id": u['id']
            }
        except: return None

    # --- 2. GITHUB USER ---
    elif type_mode == 'github':
        try:
            r = requests.get(f"https://api.github.com/users/{key}", headers=HEADERS, timeout=4)
            d = r.json()
            if 'login' not in d: raise ValueError("Github user not found")
            return {
                "valid": True, "type": "github",
                "name": html.escape(d['login']),
                "l1": "REPOS / GISTS", "l2": f"{d['public_repos']} / {d['public_gists']}",
                "color": "#ffffff", "image": get_base64(d['avatar_url']),
                "album_art": None, "is_music": False, "progress": 0, "id": str(d['id'])
            }
        except: return None

    # --- 3. DISCORD INVITE ---
    else: 
        try:
            r = requests.get(f"https://discord.com/api/v10/invites/{key}?with_counts=true", headers=HEADERS, timeout=4)
            d = r.json()
            g = d.get('guild', {})
            if not g: raise ValueError("Invalid Invite")
            return {
                "valid": True, "type": "discord",
                "name": html.escape(g['name']),
                "l1": "MEMBERS", "l2": f"{d['approximate_member_count']:,} ({d['approximate_presence_count']:,} On)",
                "color": "#5865F2", "image": get_base64(f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png") if g.get('icon') else EMPTY,
                "album_art": None, "is_music": False, "progress": 0, "id": g['id']
            }
        except: return None

# ===========================
#      STYLE ENGINES (SVG)
# ===========================

def render_spotify_card(d, msg, css, radius, bg):
    # Specialized layout mimicking Spotify
    prog_col = d['color'] if d['is_music'] else "rgba(255,255,255,0.3)"
    img = d['album_art'] if d['album_art'] else d['image']
    
    return f"""<svg width="480" height="150" viewBox="0 0 480 150" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css}
        .u {{ font-family: 'Rajdhani', sans-serif; }} .m {{ font-family: 'JetBrains Mono', monospace; }}
      </style>
      <clipPath id="cp"><rect width="480" height="150" rx="{radius}"/></clipPath>
      <clipPath id="imgc"><rect width="100" height="100" rx="8"/></clipPath>
      <filter id="bl"><feGaussianBlur stdDeviation="8"/></filter></defs>
      
      <rect width="100%" height="100%" rx="{radius}" fill="#{bg}"/>
      
      <!-- Blurred Background -->
      <g clip-path="url(#cp)">
        <image href="{img}" width="480" height="480" x="0" y="-150" opacity="0.3" filter="url(#bl)"/>
        <rect width="100%" height="100%" fill="#{bg}" opacity="0.6"/>
      </g>

      <!-- Layout -->
      <g transform="translate(20,25)">
         <!-- Album Art -->
         <g class="float">
            <image href="{img}" width="100" height="100" clip-path="url(#imgc)"/>
            <rect width="100" height="100" rx="8" fill="none" stroke="rgba(255,255,255,0.2)"/>
            {'<circle cx="50" cy="50" r="20" fill="none" stroke="white" stroke-width="2" stroke-dasharray="10 5" class="spin" opacity="0.6"/>' if d['is_music'] else ''}
         </g>
         
         <!-- Text -->
         <g transform="translate(120, 10)">
            <text class="u" font-size="10" font-weight="bold" fill="#bbb" letter-spacing="1">NOW PLAYING</text>
            <text y="28" class="u" font-size="24" font-weight="bold" fill="white">{d['l1']}</text>
            <text y="48" class="m" font-size="12" fill="{d['color']}">{d['l2']}</text>
            <!-- AI Line -->
            <text y="70" class="m" font-size="10" fill="#E0E0FF" opacity="0.7">AI: {msg}</text>
         </g>
      </g>
      
      <!-- Bar -->
      <g transform="translate(20, 135)">
         <rect width="440" height="4" rx="2" fill="rgba(255,255,255,0.2)"/>
         <rect width="{d['progress'] * 4.4}" height="4" rx="2" fill="{prog_col}"/>
      </g>
    </svg>"""

def render_hyper(d, msg, css, radius, bg):
    # Advanced GLSL/Liquid Shader style
    bg_element = f'<image href="{d["album_art"]}" width="100%" height="100%" opacity="0.4" filter="url(#bl)"/>' if d['album_art'] else \
                 f'<g class="drift" opacity="0.4"><circle cx="20" cy="20" r="160" fill="{d["color"]}" filter="url(#liq)"/><circle cx="450" cy="160" r="140" fill="#5865F2" filter="url(#liq)"/></g>'
    
    hex_path = "M50 0 L93.3 25 V75 L50 100 L6.7 75 V25 Z"

    return f"""<svg width="480" height="180" viewBox="0 0 480 180" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css} .u {{ font-family: 'Rajdhani', sans-serif; }} .m {{ font-family: 'JetBrains Mono', monospace; }}</style>
      <filter id="liq"><feTurbulence type="fractalNoise" baseFrequency="0.015"/><feDisplacementMap in="SourceGraphic" scale="30"/></filter>
      <filter id="bl"><feGaussianBlur stdDeviation="12"/></filter>
      <clipPath id="hex"><path d="{hex_path}"/></clipPath>
      <clipPath id="card"><rect width="480" height="180" rx="{radius}"/></clipPath>
      </defs>
      
      <rect width="100%" height="100%" rx="{radius}" fill="#{bg}"/>
      <g clip-path="url(#card)">{bg_element}<rect width="100%" height="100%" fill="black" opacity="0.2"/></g>
      
      <g transform="translate(25,40)">
         <path d="{hex_path}" fill="{d['color']}" opacity="0.2" transform="translate(0,4)"/>
         <g clip-path="url(#hex)"><image href="{d['image']}" width="100" height="100"/></g>
         <path d="{hex_path}" fill="none" stroke="{d['color']}" stroke-width="3"/>
      </g>
      
      <g transform="translate(145,50)" class="float">
         <text y="0" class="u" font-size="30" fill="white" font-weight="700" style="text-shadow:0 4px 10px rgba(0,0,0,0.5)">{d['name'].upper()}</text>
         <text y="25" class="m" font-size="12" fill="{d['color']}">>> {d['l1']}</text>
         <text y="42" class="m" font-size="11" fill="#ccc">{d['l2']}</text>
      </g>
      
      <g transform="translate(145,120)" class="float" style="animation-delay:0.5s">
         <rect width="310" height="35" rx="6" fill="rgba(0,0,0,0.5)" stroke="rgba(255,255,255,0.1)"/>
         <text x="15" y="23" class="u" font-size="13" fill="#E0E0FF"><tspan fill="#5865F2" font-weight="bold">AI //</tspan> {msg}<tspan class="pulse">_</tspan></text>
      </g>
    </svg>"""

def render_cute(d, msg, css):
    # Pastel kawaii style
    return f"""<svg width="480" height="160" viewBox="0 0 480 160" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css}</style><clipPath id="c"><circle cx="60" cy="60" r="50"/></clipPath></defs>
      <rect width="480" height="160" rx="30" fill="#FFFAFA"/>
      <rect x="5" y="5" width="470" height="150" rx="25" fill="none" stroke="{d['color']}" stroke-width="3" stroke-dasharray="10 6" opacity="0.3"/>
      
      <circle cx="430" cy="40" r="15" fill="{d['color']}" opacity="0.2" class="bob"/>
      <text x="420" y="47" font-size="20" class="bob">✨</text>
      
      <g transform="translate(20,20)">
         <circle cx="60" cy="60" r="54" fill="{d['color']}"/><image href="{d['image']}" width="120" height="120" clip-path="url(#c)"/>
      </g>
      
      <g transform="translate(150,45)">
         <text y="0" font-family="Fredoka" font-size="26" font-weight="600" fill="#555">{d['name']}</text>
         <g transform="translate(0,15)"><rect width="250" height="25" rx="12" fill="#F0F0F0"/>
         <text x="10" y="17" font-family="Fredoka" font-size="11" fill="{d['color']}">♥ {d['l1']} {d['l2']}</text></g>
         <g transform="translate(0,50)" class="bob">
            <text x="0" y="10" font-family="Fredoka" font-size="11" fill="#777">💭 {msg.lower().capitalize()}</text>
         </g>
      </g>
    </svg>"""

def render_terminal(d, msg, css):
    # Hacker / VS Code style
    return f"""<svg width="480" height="150" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css}</style></defs>
      <rect width="100%" height="100%" rx="6" fill="#0d1117" stroke="#30363d"/>
      <circle cx="20" cy="20" r="5" fill="#ff5f56"/><circle cx="40" cy="20" r="5" fill="#ffbd2e"/><circle cx="60" cy="20" r="5" fill="#27c93f"/>
      
      <g transform="translate(25,60)" font-family="Fira Code" font-size="12" fill="#c9d1d9">
         <text>> const user = "{d['name']}";</text>
         <text y="20">> user.activity = "{d['l1']} {d['l2']}";</text>
         <text y="45" fill="#d2a8ff">> ai.analyze(user);</text>
         <text y="65" fill="#8b949e"># RETURN: {msg}<tspan class="blink">_</tspan></text>
      </g>
      <image href="{d['image']}" x="390" y="40" width="70" height="70" opacity="0.8" rx="5"/>
    </svg>"""

def render_pro(d, msg):
    # Professional Email style (No Animation Code injection needed, purely static)
    return f"""<svg width="480" height="130" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><clipPath id="s"><rect width="80" height="80" rx="4"/></clipPath></defs>
      <rect width="478" height="128" x="1" y="1" rx="4" fill="#FFFFFF" stroke="#e1e4e8"/>
      <rect width="6" height="128" x="1" y="1" rx="1" fill="{d['color']}"/>
      <g transform="translate(30,25)">
         <image href="{d['image']}" width="80" height="80" clip-path="url(#s)"/>
         <rect width="80" height="80" rx="4" fill="none" stroke="rgba(0,0,0,0.1)"/>
      </g>
      <g transform="translate(130,35)" font-family="Arial, Helvetica, sans-serif">
         <text y="0" font-weight="bold" font-size="22" fill="#24292e">{d['name']}</text>
         <text y="25" font-size="11" font-weight="bold" fill="#586069">{d['l1']}</text>
         <text y="40" font-size="11" fill="#586069">{d['l2']}</text>
         <line x1="0" y1="60" x2="300" y2="60" stroke="#eee"/>
         <text y="80" font-size="10" fill="#888" font-style="italic">"{msg}"</text>
      </g>
    </svg>"""

# ===========================
#        MAIN CONTROLLER
# ===========================

@app.route('/superbadge/<key>')
@app.route('/badge/<mode>/<key>')
def handler(key, mode="auto"):
    args = request.args
    
    # 1. Logic Routing
    target_mode = mode
    if mode == "auto":
        # Guess the type
        if key.isdigit() and len(key) > 16: target_mode = 'user'
        else: target_mode = 'discord' # Fallback invite code logic
    
    # 2. Fetch Data
    data = fetch_data(key, target_mode, args)
    
    # Error Image
    if not data: return Response(f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="100"><rect width="100%" height="100%" fill="black"/><text x="10" y="50" fill="red" font-family="sans-serif">INVALID ID / API ERROR: {key}</text></svg>', mimetype='image/svg+xml')

    # 3. Process Settings
    roast = args.get('roastMode', 'false').lower() == 'true'
    anim_on = args.get('animations', 'true')
    ai_on = args.get('aifeatures', 'true')
    style = args.get('style', 'hyper').lower()
    bg_col = args.get('bg', '09090b').replace('#', '')
    rad = args.get('borderRadius', '20').replace('px', '')

    # 4. Generate AI Message
    ai_role = "roast" if roast else "hud"
    # Construct context based on lines
    context_str = f"{data['l1']} {data['l2']}"
    ai_msg = consult_gemini(context_str, data['name'], ai_role, ai_on, data['type'])

    # 5. Render Selected Style
    css = get_css(anim_on)
    
    if style == 'spotify':
        svg = render_spotify_card(data, ai_msg, css, rad, bg_col)
    elif style == 'cute':
        svg = render_cute(data, ai_msg, css)
    elif style == 'terminal':
        svg = render_terminal(data, ai_msg, css)
    elif style == 'professional' or style == 'pro':
        svg = render_pro(data, ai_msg)
    else:
        # Default Hyper
        svg = render_hyper(data, ai_msg, css, rad, bg_col)

    # 6. Response with Headers
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

@app.route('/')
def home():
    return """<body style="background:#111;color:#eee;font-family:sans-serif;text-align:center;padding:50px">
    <h1>HYPERBADGE V10 ONLINE</h1>
    <p>Endpoints:</p>
    <code>/badge/discord/[INVITE_CODE]</code><br>
    <code>/badge/github/[USERNAME]</code><br>
    <code>/superbadge/[USER_ID]</code>
    </body>"""

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
