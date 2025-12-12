import base64
import requests
import os
import datetime
import html
import google.generativeai as genai
from flask import Flask, Response

app = Flask(__name__)

# --- CONFIGURATION ---
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

HEADERS = {'User-Agent': 'HyperBadge/v4.0'}

# 1x1 Transparent Fallback
EMPTY_IMG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

def get_base64(url):
    if not url: return EMPTY_IMG
    try:
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(r.content).decode('utf-8')}"
    except:
        pass
    return EMPTY_IMG

# --- INTELLIGENT AI CORE ---
def consult_gemini(status_text, user_name, is_music):
    if not GOOGLE_API_KEY: 
        return "AI_MOD :: INITIALIZATION_FAILED"

    try:
        model = genai.GenerativeModel('gemini-pro')
        
        # Context-Aware Prompt
        context = "LISTENING TO MUSIC" if is_music else "GENERAL ACTIVITY"
        
        prompt = f"""
        Role: Sci-Fi System OS.
        Target: '{user_name}' is currently {context}: "{status_text}".
        
        Task: Write a 1-line uppercase status report. Max 6 words.
        - If Music: Mention frequency analysis, audio streams, or vibes.
        - If Coding: Mention compilation or syntax.
        - If Generic: Mention biometrics.
        
        Output: ONLY the status text.
        """
        
        response = model.generate_content(prompt)
        text = response.text.strip().replace('"', '').replace("'", "")
        return html.escape(text[:40]).upper()
    except:
        return "DATA STREAM ENCRYPTED"

# --- DATA LAYER (LANYARD + SPOTIFY) ---
def get_user_data(user_id):
    try:
        r = requests.get(f"https://api.lanyard.rest/v1/users/{user_id}", headers=HEADERS, timeout=4)
        data = r.json()
        
        if not r.status_code == 200 or not data['success']: 
            return None
        
        d = data['data']
        u = d['discord_user']
        status = d['discord_status']
        
        # --- LOGIC VARIABLES ---
        # Defaults
        display_color = "#7a7a7a"
        line_1 = f"STATUS: {status.upper()}"
        line_2 = "NO SIGNAL"
        is_music = False
        
        # Color Map
        colors = {
            "online": "#00ffb3", 
            "idle": "#ffbb00",   
            "dnd": "#ff2a6d",    
            "offline": "#555555",
            "spotify": "#1DB954" # Special Spotify Color
        }
        
        # 1. CHECK SPOTIFY PRIORITY
        if d.get('spotify'):
            spot = d['spotify']
            song = spot['song']
            artist = spot['artist']
            
            # Smart Truncate
            if len(song) > 20: song = song[:18] + ".."
            
            line_1 = f"🎵 {html.escape(song)}"
            line_2 = f"BY: {html.escape(artist)}"
            display_color = colors['spotify']
            is_music = True
            
        # 2. CHECK OTHER ACTIVITIES (If no Spotify)
        else:
            display_color = colors.get(status, "#555")
            
            # Find Game or Custom Status
            found_act = False
            for act in d.get('activities', []):
                if act['type'] == 0: # Game
                    line_1 = "RUNNING_EXE:"
                    line_2 = html.escape(act['name'])
                    found_act = True
                    break
                if act['type'] == 4: # Custom Status
                    state = act.get('state', '')
                    if state:
                        line_1 = "USER NOTE:"
                        line_2 = html.escape(state)
                        found_act = True
                        break
            
            if not found_act:
                # Basic Fallback
                line_1 = f"SYSTEM IS {status.upper()}"
                line_2 = "WAITING FOR INPUT..."

        return {
            "valid": True,
            "id": u['id'],
            "name": html.escape(u['username'].upper()),
            "status_color": display_color,
            "line_1": line_1,
            "line_2": line_2,
            "is_music": is_music,
            "avatar": get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png")
        }
    except Exception as e:
        print(e)
        pass
    
    return { 
        "valid": False, "status_color": "#ff0000", "name": "ERR_404", 
        "line_1": "CONNECTION LOST", "line_2": "RETRYING...", "id": "0000", "avatar": EMPTY_IMG, "is_music": False
    }

# --- RENDER ENGINE ---
def generate_hyper_svg(data, ai_msg):
    hex_path = "M50 0 L93.3 25 V75 L50 100 L6.7 75 V25 Z"

    svg = f"""<svg width="480" height="160" viewBox="0 0 480 160" 
     xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
  
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Rajdhani:wght@500;700&amp;display=swap');
      
      :root {{
        --acc: {data['status_color']};
      }}

      .font-tech {{ font-family: 'JetBrains Mono', monospace; }}
      .font-ui {{ font-family: 'Rajdhani', sans-serif; }}

      /* PARALLAX ANIMATION */
      .anim-float {{ animation: floatY 6s ease-in-out infinite; }}
      @keyframes floatY {{ 0%, 100% {{ transform: translateY(0px); }} 50% {{ transform: translateY(-3px); }} }}

      /* BACKGROUND DRIFT */
      .bg-drift {{ animation: rotate 20s infinite linear; transform-origin: center; }}
      @keyframes rotate {{ from {{ transform: rotate(0deg) scale(1.1); }} to {{ transform: rotate(360deg) scale(1.1); }} }}
      
      .pulse-text {{ animation: opacityPulse 2s infinite; }}
      @keyframes opacityPulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} 100% {{ opacity: 1; }} }}
    </style>

    <clipPath id="hexClip"><path d="{hex_path}" /></clipPath>
    <clipPath id="cardClip"><rect width="480" height="160" rx="20" /></clipPath>

    <!-- FROST SHADOW -->
    <filter id="softGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <!-- === BACKGROUND === -->
  <rect width="100%" height="100%" rx="20" fill="#09090b" />

  <g clip-path="url(#cardClip)">
    <g class="bg-drift" opacity="0.3">
        <!-- Main blob changes color based on Activity/Spotify -->
        <circle cx="50" cy="50" r="160" fill="{data['status_color']}" filter="url(#softGlow)" />
        <circle cx="450" cy="160" r="140" fill="#5865F2" filter="url(#softGlow)" />
    </g>
    <!-- Texture Overlay -->
    <rect width="100%" height="100%" fill="url(#noisePattern)" /> <!-- pattern ref omitted for brevity, renders transparently -->
    <rect width="100%" height="100%" fill="rgba(255,255,255,0.02)" />
  </g>

  <!-- === FLOATING UI === -->

  <!-- 1. HEXAGON AVATAR -->
  <g transform="translate(25, 30)">
      <!-- Glow Underlay -->
      <path d="{hex_path}" fill="{data['status_color']}" opacity="0.2" filter="url(#softGlow)" transform="scale(1.05) translate(-2.5,-2.5)" />
      
      <!-- Image & Border -->
      <g clip-path="url(#hexClip)">
         <image href="{data['avatar']}" width="100" height="100" />
      </g>
      <path d="{hex_path}" fill="none" stroke="{data['status_color']}" stroke-width="3" />
  </g>

  <!-- 2. DATA PANEL (Float) -->
  <g transform="translate(145, 42)" class="anim-float">
      <!-- Username -->
      <text x="0" y="0" class="font-ui" font-weight="700" font-size="28" fill="white" style="text-shadow: 2px 2px 0 rgba(0,0,0,0.5)">
        {data['name']}
      </text>
      
      <!-- Line 1: Song Name or Activity Title -->
      <text x="0" y="22" class="font-tech" font-weight="800" font-size="12" fill="{data['status_color']}" letter-spacing="0.5">
         >> {data['line_1']}
      </text>
      
      <!-- Line 2: Artist or Activity Details -->
      <text x="0" y="36" class="font-tech" font-weight="400" font-size="10" fill="#AAA">
         {data['line_2']}
      </text>
  </g>

  <!-- 3. AI CHIP (Bottom Panel) -->
  <g transform="translate(145, 95)" class="anim-float">
      <rect x="0" y="0" width="310" height="35" rx="6" fill="rgba(0,0,0,0.4)" stroke="rgba(255,255,255,0.1)"/>
      
      <!-- Little decorative blocks -->
      <rect x="5" y="10" width="3" height="15" fill="{data['status_color']}" />
      <rect x="10" y="10" width="3" height="15" fill="{data['status_color']}" opacity="0.5"/>
      
      <!-- The AI Message -->
      <text x="25" y="21" class="font-ui" font-weight="500" font-size="13" fill="#E0E0FF">
        <tspan fill="#5865F2" font-weight="700">AI //</tspan> {ai_msg}<tspan class="pulse-text">_</tspan>
      </text>
  </g>

  <!-- Footer -->
  <text x="460" y="150" text-anchor="end" class="font-tech" font-size="8" fill="#333">UID: {data['id']}</text>

</svg>"""
    return svg

@app.route('/superbadge/<user_id>')
def serve_badge(user_id):
    # Fetch User & Music
    data = get_user_data(user_id)
    
    msg = "STANDBY"
    if data['valid']:
        # Prompt based on Music vs Activity
        context_str = f"{data['line_1']} {data['line_2']}"
        msg = consult_gemini(context_str, data['name'], data['is_music'])
    else:
        msg = "CONNECTION REQUIRED"

    svg = generate_hyper_svg(data, msg)
    
    return Response(svg, mimetype="image/svg+xml", headers={
        "Cache-Control": "no-cache, max-age=0"
    })

@app.route('/')
def home():
    return "CHILLAX SERVER BADGE OS v4.0 (MUSIC_MODULE_ACTIVE)"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
