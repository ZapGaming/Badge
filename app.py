import base64
import requests
import os
import datetime
import html
import google.generativeai as genai
from flask import Flask, Response, request

app = Flask(__name__)

# --- CONFIGURATION ---
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

HEADERS = {'User-Agent': 'HyperBadge/v5.0-Custom'}

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
def consult_gemini(status_text, user_name, custom_idle=None):
    if not GOOGLE_API_KEY: 
        return "AI_MOD :: INITIALIZATION_FAILED"

    try:
        model = genai.GenerativeModel('gemini-pro')
        
        # Adjust prompt context if using a custom idle message
        context = "User is ACTIVE"
        if custom_idle and status_text == custom_idle:
            context = "User is IDLE/CHILLING"

        prompt = f"""
        Role: Sci-Fi System OS (JARVIS/Cortana).
        Target: '{user_name}'
        Activity: "{status_text}" ({context}).
        
        Task: Write a 1-line uppercase status report. Max 6 words.
        - If playing music: Comment on audio freq or vibes.
        - If idle/sleeping (status is "{status_text}"): "HIBERNATION MODE ACTIVE" or similar.
        - If coding: "COMPILING NEURAL SHARDS".
        
        Output: ONLY the status text.
        """
        
        response = model.generate_content(prompt)
        text = response.text.strip().replace('"', '').replace("'", "")
        return html.escape(text[:40]).upper()
    except:
        return "DATA STREAM ENCRYPTED"

# --- DATA LAYER (LANYARD + SPOTIFY + CUSTOM ARGS) ---
def get_user_data(user_id, args):
    try:
        r = requests.get(f"https://api.lanyard.rest/v1/users/{user_id}", headers=HEADERS, timeout=4)
        data = r.json()
        
        if not r.status_code == 200 or not data['success']: 
            return None
        
        d = data['data']
        u = d['discord_user']
        status = d['discord_status']
        
        # --- CUSTOMIZATION PARAMS ---
        # 1. Display Name vs Username
        show_display = args.get('showDisplayName', 'true').lower() == 'true'
        if show_display and u.get('global_name'):
            display_name = u['global_name']
            # Optional: Add username as subtext if needed, but for design we stick to one main name
        else:
            display_name = u['username']

        # 2. Idle Message
        forced_idle_msg = args.get('idleMessage', 'SYSTEM STANDBY')

        # --- LOGIC ---
        line_1 = ""
        line_2 = ""
        is_music = False
        
        colors = {
            "online": "#00ffb3", 
            "idle": "#ffbb00",   
            "dnd": "#ff2a6d",    
            "offline": "#555555",
            "spotify": "#1DB954" 
        }
        
        # 1. SPOTIFY CHECK
        if d.get('spotify'):
            spot = d['spotify']
            song = spot['song']
            artist = spot['artist']
            
            if len(song) > 18: song = song[:16] + ".."
            
            line_1 = f"🎵 {html.escape(song)}"
            line_2 = f"BY: {html.escape(artist)}"
            display_color = colors['spotify']
            is_music = True
            
        # 2. OTHER ACTIVITIES
        else:
            found_act = False
            for act in d.get('activities', []):
                if act['type'] == 0: # Game
                    line_1 = "RUNNING_EXE:"
                    line_2 = html.escape(act['name'])
                    found_act = True; break
                if act['type'] == 4: # Status Msg
                    state = act.get('state', '')
                    emoji = act.get('emoji', {}).get('name', '')
                    content = f"{emoji} {state}".strip()
                    if content:
                        line_1 = "USER STATUS:"
                        line_2 = html.escape(content)
                        found_act = True; break
                if act['type'] == 2: # Listening
                    line_1 = "MEDIA:"
                    line_2 = "AUDIO STREAM"
                    found_act = True; break

            # 3. IDLE/OFFLINE FALLBACK (Uses custom message)
            if not found_act:
                # If online but doing nothing, OR offline/idle
                if status == "online":
                    line_1 = "SYSTEM ONLINE"
                    line_2 = "AWAITING INPUT"
                else:
                    line_1 = "CURRENT STATE:"
                    line_2 = html.escape(forced_idle_msg).upper()
            
            display_color = colors.get(status, "#555")

        # Sanitize length
        if len(line_2) > 25: line_2 = line_2[:23] + ".."

        return {
            "valid": True,
            "id": u['id'],
            "name": html.escape(display_name.upper()),
            "status_color": display_color,
            "line_1": line_1,
            "line_2": line_2,
            "is_music": is_music,
            "avatar": get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png"),
            "style_settings": {
                "bg": args.get('bg', '09090b'),
                "radius": args.get('borderRadius', '20')
            }
        }
    except Exception as e:
        print(e)
        pass
    
    return { 
        "valid": False, "status_color": "#ff0000", "name": "ERR_404", 
        "line_1": "ERROR", "line_2": "CHECK API/USERID", "id": "0000", "avatar": EMPTY_IMG,
        "style_settings": { "bg": "000000", "radius": "20" }
    }

# --- RENDER ENGINE ---
def generate_hyper_svg(data, ai_msg):
    settings = data.get('style_settings', {})
    
    # Process CSS Args
    bg_color = settings['bg']
    if not bg_color.startswith('#'): bg_color = f"#{bg_color}"
    
    radius = settings['radius']
    if "px" in radius: radius = radius.replace("px", "") # safety clean

    # Hexagon Math
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

      /* === ANIMATIONS === */
      .anim-float {{ animation: floatY 6s ease-in-out infinite; }}
      @keyframes floatY {{ 0%, 100% {{ transform: translateY(0px); }} 50% {{ transform: translateY(-4px); }} }}

      .pulse-text {{ animation: opacityPulse 2s infinite; }}
      @keyframes opacityPulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} 100% {{ opacity: 1; }} }}
      
      /* New Drift Animation for Frosted Glass Blob */
      .blob-drift {{ animation: rotateBlob 30s linear infinite; transform-origin: 240px 80px; }}
      @keyframes rotateBlob {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
    </style>

    <clipPath id="hexClip"><path d="{hex_path}" /></clipPath>
    
    <!-- User-Defined Border Radius Clip -->
    <clipPath id="cardClip"><rect width="480" height="160" rx="{radius}" /></clipPath>

    <!-- FROST EFFECTS -->
    <filter id="softGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
    
    <!-- Text Depth -->
    <filter id="textDrop">
        <feDropShadow dx="0" dy="2" stdDeviation="2" flood-opacity="0.5"/>
    </filter>
  </defs>

  <!-- === DYNAMIC BACKGROUND === -->
  <!-- User Defined BG Color -->
  <rect width="100%" height="100%" rx="{radius}" fill="{bg_color}" />

  <!-- Animated Nebula inside the card area -->
  <g clip-path="url(#cardClip)">
    <rect width="100%" height="100%" fill="transparent" />
    
    <g class="blob-drift" opacity="0.4">
        <!-- Accent Blob -->
        <circle cx="50" cy="50" r="180" fill="{data['status_color']}" filter="url(#softGlow)" />
        <!-- Secondary Chill Blob (Blurple) -->
        <circle cx="450" cy="160" r="150" fill="#5865F2" filter="url(#softGlow)" />
    </g>
    
    <!-- Noise & Shine Overlay -->
    <rect width="100%" height="100%" fill="rgba(255,255,255,0.02)" />
    <!-- Diagonal Glass Shine -->
    <path d="M0 0 L480 0 L0 160 Z" fill="url(#whiteGradient)" opacity="0.05" />
  </g>

  <!-- === FLOATING CONTENT === -->

  <!-- 1. HEX AVATAR -->
  <g transform="translate(25, 30)">
      <!-- Glow -->
      <path d="{hex_path}" fill="{data['status_color']}" opacity="0.25" filter="url(#softGlow)" transform="translate(0, 2)" />
      <!-- Img -->
      <g clip-path="url(#hexClip)">
         <image href="{data['avatar']}" width="100" height="100" />
      </g>
      <!-- Stroke -->
      <path d="{hex_path}" fill="none" stroke="{data['status_color']}" stroke-width="3" />
  </g>

  <!-- 2. DATA BLOCK (Floating) -->
  <g transform="translate(145, 42)" class="anim-float">
      <!-- Global Display Name -->
      <text x="0" y="0" class="font-ui" font-weight="700" font-size="28" fill="white" filter="url(#textDrop)">
        {data['name']}
      </text>
      
      <!-- LINE 1 (Song or Activity Type) -->
      <text x="0" y="24" class="font-tech" font-weight="800" font-size="12" fill="{data['status_color']}">
         >> {data['line_1']}
      </text>
      
      <!-- LINE 2 (Details) -->
      <text x="0" y="38" class="font-tech" font-weight="400" font-size="11" fill="#DDD" letter-spacing="0.5">
         {data['line_2']}
      </text>
  </g>

  <!-- 3. AI HUD (Bottom) -->
  <g transform="translate(145, 95)" class="anim-float">
      <!-- Glass Pill Background -->
      <rect x="0" y="0" width="315" height="36" rx="8" fill="rgba(0,0,0,0.3)" stroke="rgba(255,255,255,0.15)" stroke-width="1"/>
      
      <!-- Decorative Tech Bar -->
      <rect x="10" y="12" width="4" height="12" fill="{data['status_color']}"/>
      
      <text x="26" y="22" class="font-ui" font-weight="500" font-size="13" fill="#DDEEFF">
        <tspan fill="#5865F2" font-weight="800">AI //</tspan> {ai_msg}<tspan class="pulse-text">_</tspan>
      </text>
  </g>

  <text x="465" y="150" text-anchor="end" class="font-tech" font-size="9" fill="#FFFFFF" opacity="0.4">ID: {data['id']}</text>

</svg>"""
    return svg

@app.route('/superbadge/<user_id>')
def serve_badge(user_id):
    # Parse Query Args
    args = request.args
    
    # Fetch Data with Args support
    data = get_user_data(user_id, args)
    
    msg = "STANDBY"
    if data['valid']:
        # If the user is idle/offline and we are using a custom idle message, tell the AI
        forced_idle = args.get('idleMessage')
        msg = consult_gemini(data['line_2'], data['name'], custom_idle=forced_idle)
    else:
        msg = "CONNECTION REQUIRED"

    svg = generate_hyper_svg(data, msg)
    
    return Response(svg, mimetype="image/svg+xml", headers={
        "Cache-Control": "no-cache, max-age=0"
    })

@app.route('/')
def home():
    return """<h1 style='font-family:sans-serif; background:#111; color:#fff; padding:20px'>
    HYPERBADGE ONLINE.<br><br>
    Usage: /superbadge/ID?bg=000000&idleMessage=Sleeping&borderRadius=30&showDisplayName=true
    </h1>"""

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
