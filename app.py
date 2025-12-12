import base64
import requests
import os
import html
import random
import google.generativeai as genai
from flask import Flask, Response, request

app = Flask(__name__)

# --- CONFIG ---
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# Use Firefox User-Agent to avoid blocking
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
EMPTY_IMG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# --- UTILS ---
def get_base64(url):
    if not url: return EMPTY_IMG
    try:
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(r.content).decode('utf-8')}"
    except:
        pass
    return EMPTY_IMG

# --- AI CORE (DUAL MODE) ---
def consult_gemini(status_text, user_name, mode="normal", is_music=False):
    if not GOOGLE_API_KEY: return "AI OFFLINE"

    try:
        model = genai.GenerativeModel('gemini-pro')
        
        # 1. ROAST MODE
        if mode == "roast":
            context = "playing music" if is_music else "doing this"
            prompt = f"""
            TASK: Roast the Discord user '{user_name}' who is currently {context}: "{status_text}".
            - Be savage but funny. No swearing.
            - If playing League/Valorant: Insult their skill.
            - If Spotify: Insult their music taste.
            - If Coding: Mock their spaghetti code.
            - If Idle: Call them boring.
            FORMAT: One UPPERCASE line. Max 8 words.
            """
        
        # 2. SYSTEM/HUD MODE
        else:
            prompt = f"""
            TASK: Act as a Sci-Fi Operating System (JARVIS style).
            Target: '{user_name}'
            Activity: "{status_text}".
            OUTPUT: A cool, technical status update. Max 5 words. UPPERCASE only.
            Examples: "AUDIO STREAM SYNCED", "NEURAL UPLINK ACTIVE", "COMPILING DATA".
            """
        
        response = model.generate_content(prompt)
        text = response.text.strip().replace('"', '').replace("'", "")
        return html.escape(text[:45]).upper()
    except:
        return "DATA ENCRYPTED"

# --- DATA LAYER (FULL FEATURED) ---
def get_user_data(user_id):
    try:
        r = requests.get(f"https://api.lanyard.rest/v1/users/{user_id}", headers=HEADERS, timeout=4)
        data = r.json()
        
        if not r.status_code == 200 or not data['success']: 
            return None
        
        d = data['data']
        u = d['discord_user']
        status = d['discord_status']
        
        # LOGIC
        display_color = "#555"
        line_1 = ""
        line_2 = ""
        is_music = False
        
        colors = {
            "online": "#00ffb3", "idle": "#ffbb00", "dnd": "#ff2a6d", "offline": "#555555",
            "spotify": "#1DB954"
        }
        
        # Priority 1: Spotify
        if d.get('spotify'):
            spot = d['spotify']
            line_1 = f"🎵 {html.escape(spot['song'])}"
            line_2 = f"By {html.escape(spot['artist'])}"
            display_color = colors['spotify']
            is_music = True
            
        # Priority 2: Activities
        else:
            found = False
            for act in d.get('activities', []):
                if act['type'] == 0: # Game
                    line_1 = "PLAYING:"
                    line_2 = html.escape(act['name'])
                    found = True; break
                if act['type'] == 4: # Status
                    st = act.get('state', '')
                    if st:
                        line_1 = "STATUS:"
                        line_2 = html.escape(st)
                        found = True; break
                if act['type'] == 2:
                    line_1 = "LISTENING:"
                    line_2 = "Audio Stream"
                    found = True; break
            
            if not found:
                line_1 = "CURRENTLY:"
                line_2 = status.upper()
                
            display_color = colors.get(status, "#555")

        # Smart Truncate for long songs/status
        if len(line_1) > 20: line_1 = line_1[:18] + ".."
        if len(line_2) > 25: line_2 = line_2[:23] + ".."

        return {
            "valid": True,
            "id": u['id'],
            "name": html.escape(u['global_name'] or u['username']),
            "color": display_color,
            "line_1": line_1,
            "line_2": line_2,
            "is_music": is_music,
            "full_status_text": f"{line_1} {line_2}",
            "avatar": get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png")
        }
    except Exception as e:
        print(e)
        return {"valid": False, "color": "#F00", "name": "ERROR", "line_1": "API ERROR", "line_2": "RETRY", "avatar": EMPTY_IMG}

# ==========================================
#       THE RENDER ENGINES (SVGS)
# ==========================================

# --- STYLE 1: HYPER (The Complex GLSL One) ---
def render_hyper(d, msg):
    hex_path = "M50 0 L93.3 25 V75 L50 100 L6.7 75 V25 Z"
    return f"""<svg width="480" height="160" viewBox="0 0 480 160" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs>
        <style>@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Rajdhani:wght@500;700&amp;display=swap');
        .h-font {{ font-family: 'Rajdhani', sans-serif; }} .h-mono {{ font-family: 'JetBrains Mono', monospace; }}
        .anim-float {{ animation: fly 6s ease-in-out infinite; }} @keyframes fly {{ 0%,100%{{transform:translateY(0)}} 50%{{transform:translateY(-4px)}} }}
        .bg-drift {{ animation: spin 25s linear infinite; transform-origin: 240px 80px; }} @keyframes spin {{ from{{transform:rotate(0deg)}} to{{transform:rotate(360deg)}} }}
        .pulse {{ animation: p 2s infinite; }} @keyframes p {{ 50%{{opacity:0.5}} }}
        </style>
        <clipPath id="hClip"><path d="{hex_path}"/></clipPath>
        <clipPath id="cClip"><rect width="480" height="160" rx="20"/></clipPath>
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="8" /><feComposite in="SourceGraphic" operator="over"/></filter>
      </defs>
      
      <!-- BG -->
      <rect width="100%" height="100%" rx="20" fill="#09090b"/>
      <g clip-path="url(#cClip)">
        <g class="bg-drift" opacity="0.4">
            <circle cx="50" cy="50" r="180" fill="{d['color']}" filter="url(#glow)"/>
            <circle cx="450" cy="160" r="150" fill="#5865F2" filter="url(#glow)"/>
        </g>
        <rect width="100%" height="100%" fill="rgba(255,255,255,0.03)"/>
        <path d="M0 0 L480 0 L0 160 Z" fill="white" opacity="0.03"/>
      </g>

      <!-- CONTENT -->
      <g transform="translate(25, 30)">
          <path d="{hex_path}" fill="{d['color']}" opacity="0.25" filter="url(#glow)" transform="translate(0,2)"/>
          <g clip-path="url(#hClip)"><image href="{d['avatar']}" width="100" height="100"/></g>
          <path d="{hex_path}" fill="none" stroke="{d['color']}" stroke-width="3"/>
      </g>

      <g transform="translate(145, 42)" class="anim-float">
          <text y="0" class="h-font" weight="700" font-size="28" fill="white" filter="url(#glow)">{d['name'].upper()}</text>
          <text y="24" class="h-mono" font-size="11" fill="{d['color']}">>> {d['line_1']}</text>
          <text y="38" class="h-mono" font-size="10" fill="#DDD">{d['line_2']}</text>
      </g>

      <g transform="translate(145, 95)" class="anim-float" style="animation-delay: 1s">
          <rect width="310" height="36" rx="8" fill="rgba(0,0,0,0.3)" stroke="rgba(255,255,255,0.15)"/>
          <rect x="10" y="12" width="4" height="12" fill="{d['color']}"/>
          <text x="26" y="22" class="h-font" font-size="13" fill="#E0E0FF">
            <tspan fill="#5865F2" font-weight="bold">AI //</tspan> {msg} <tspan class="pulse">_</tspan>
          </text>
      </g>
      <text x="460" y="150" text-anchor="end" class="h-mono" font-size="8" fill="#444">UID: {d['id']}</text>
    </svg>"""

# --- STYLE 2: CUTE (Pastel & Bubbly) ---
def render_cute(d, msg):
    # Pastelify the accent color slightly if it's too neon
    acc = d['color']
    if acc == "#555": acc = "#aaa"
    
    return f"""<svg width="480" height="160" viewBox="0 0 480 160" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs>
        <style>@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600&amp;display=swap');
        .bob {{ animation: b 3s ease-in-out infinite; }} @keyframes b {{ 50%{{transform:translateY(-6px)}} }}
        .wiggle {{ animation: w 4s ease-in-out infinite; transform-origin: 430px 40px; }} @keyframes w {{ 0%,100%{{transform:rotate(-10deg)}} 50%{{transform:rotate(10deg)}} }}
        </style>
        <clipPath id="cir"><circle cx="60" cy="60" r="50"/></clipPath>
        <filter id="soft"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.2"/></filter>
      </defs>
      
      <!-- BG -->
      <rect width="480" height="160" rx="30" fill="#FFFAFA"/>
      <rect x="5" y="5" width="470" height="150" rx="25" fill="none" stroke="{acc}" stroke-width="4" stroke-dasharray="12 8" opacity="0.3"/>
      
      <!-- Decors -->
      <circle cx="430" cy="40" r="20" fill="{acc}" opacity="0.2" class="wiggle"/>
      <text x="420" y="47" font-size="20" class="wiggle" style="animation-delay:0.1s">✨</text>
      
      <!-- Content -->
      <g transform="translate(20, 20)">
         <circle cx="60" cy="60" r="54" fill="{acc}"/>
         <image href="{d['avatar']}" width="120" height="120" clip-path="url(#cir)"/>
      </g>
      
      <g transform="translate(150, 45)">
         <text y="0" font-family="Fredoka" font-weight="600" font-size="28" fill="#555" filter="url(#soft)">{d['name']}</text>
         
         <g transform="translate(0, 15)">
            <rect width="260" height="30" rx="15" fill="white" filter="url(#soft)"/>
            <text x="15" y="20" font-family="Fredoka" font-size="12" fill="{acc}">💖 {d['line_1']} {d['line_2']}</text>
         </g>
         
         <g transform="translate(0, 55)" class="bob">
            <path d="M0 10 Q0 0 10 0 H280 Q290 0 290 10 V30 Q290 40 280 40 H30 L20 50 L10 40 H0 Z" fill="{acc}" opacity="0.1"/>
            <text x="15" y="25" font-family="Fredoka" font-size="11" fill="#777">💭 {msg.lower().capitalize()}</text>
         </g>
      </g>
    </svg>"""

# --- STYLE 3: TERMINAL (Retro Hacker) ---
def render_terminal(d, msg):
    return f"""<svg width="480" height="150" viewBox="0 0 480 150" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs>
        <style>@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@500&amp;display=swap');
        .cursor {{ animation: k 1s step-end infinite; }} @keyframes k {{ 50% {{ opacity: 0 }} }}
        </style>
      </defs>
      
      <!-- Window -->
      <rect width="480" height="150" rx="8" fill="#0d1117" stroke="#30363d"/>
      
      <!-- Title Bar -->
      <rect width="480" height="25" rx="8" fill="#161b22"/>
      <rect y="20" width="480" height="130" fill="#0d1117"/> <!-- Cut corners bottom -->
      <circle cx="20" cy="12" r="6" fill="#ff5f56"/>
      <circle cx="40" cy="12" r="6" fill="#ffbd2e"/>
      <circle cx="60" cy="12" r="6" fill="#27c93f"/>
      <text x="240" y="17" text-anchor="middle" font-family="Fira Code" font-size="10" fill="#8b949e">user_status.py</text>
      
      <!-- Code -->
      <g transform="translate(20, 50)" font-family="Fira Code" font-size="12">
         <!-- Line 1 -->
         <text y="0" fill="#ff7b72">const</text> 
         <text x="45" y="0" fill="#d2a8ff">User</text> 
         <text x="80" y="0" fill="#c9d1d9">= {{</text>
         
         <!-- Line 2 -->
         <text x="20" y="20" fill="#79c0ff">name:</text>
         <text x="65" y="20" fill="#a5d6ff">"{d['name']}"</text>,
         
         <!-- Line 3 -->
         <text x="20" y="40" fill="#79c0ff">activity:</text>
         <text x="95" y="40" fill="#7ee787">"{d['line_1']} {d['line_2']}"</text>,
         
         <!-- Line 4 -->
         <text x="20" y="60" fill="#79c0ff">ai_log:</text>
         <text x="80" y="60" fill="#8b949e">"{msg}"</text><tspan class="cursor" fill="white">_</tspan>
         
         <!-- Close -->
         <text y="80" fill="#c9d1d9">}}</text>
      </g>
      
      <!-- Image right aligned -->
      <image href="{d['avatar']}" x="380" y="45" width="80" height="80" rx="8" opacity="0.8"/>
    </svg>"""

# --- STYLE 4: PRO (Business Card) ---
def render_pro(d, msg):
    # This style uses System fonts for reliability, no imports
    return f"""<svg width="420" height="130" viewBox="0 0 420 130" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs>
        <clipPath id="sq"><rect width="80" height="80" rx="6"/></clipPath>
      </defs>
      
      <!-- Clean Card -->
      <rect x="2" y="2" width="416" height="126" rx="8" fill="white" stroke="#e1e4e8" stroke-width="1"/>
      
      <!-- Side Accent -->
      <path d="M 10 10 L 10 120" stroke="{d['color']}" stroke-width="4" stroke-linecap="round"/>
      
      <!-- Avatar -->
      <g transform="translate(30, 25)">
         <image href="{d['avatar']}" width="80" height="80" clip-path="url(#sq)"/>
         <rect width="80" height="80" rx="6" fill="none" stroke="rgba(0,0,0,0.1)"/>
         <!-- Status Dot -->
         <circle cx="80" cy="80" r="8" fill="{d['color']}" stroke="white" stroke-width="2"/>
      </g>
      
      <!-- Text Info -->
      <g transform="translate(130, 35)" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif">
         <text y="0" font-weight="700" font-size="24" fill="#24292e">{d['name']}</text>
         
         <text y="28" font-size="12" fill="#586069" font-weight="600" style="text-transform:uppercase; letter-spacing:0.5px">
            {d['line_1']}
         </text>
         <text y="44" font-size="12" fill="#586069">{d['line_2']}</text>
         
         <g transform="translate(0, 70)">
            <rect width="250" height="1" fill="#eee"/>
            <text y="15" font-size="10" fill="#999" font-style="italic">{msg}</text>
         </g>
      </g>
    </svg>"""

# --- ROUTER ---
@app.route('/superbadge/<user_id>')
def serve(user_id):
    # 1. Capture Args
    roast_mode = request.args.get('roastMode', 'false').lower() == 'true'
    style = request.args.get('style', 'hyper').lower()
    
    # 2. Get Data
    data = get_user_data(user_id)
    if not data['valid']:
        return Response('<svg><text>Error Fetching Data</text></svg>', mimetype="image/svg+xml")

    # 3. AI
    mode = "roast" if roast_mode else "normal"
    msg = consult_gemini(data['full_status_text'], data['name'], mode, data['is_music'])
    
    # 4. Render
    if style == 'cute': svg = render_cute(data, msg)
    elif style == 'terminal': svg = render_terminal(data, msg)
    elif style == 'professional': svg = render_pro(data, msg)
    else: svg = render_hyper(data, msg) # Default
    
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache"})

@app.route('/')
def home():
    return "BADGE SYSTEM ACTIVE. Endpoints: /superbadge/[ID]?style=[hyper|cute|terminal|professional]&roastMode=[true|false]"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
