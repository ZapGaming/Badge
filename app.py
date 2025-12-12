import base64
import requests
import os
import datetime
import random
import html  # Added for XML sanitization
import google.generativeai as genai
from flask import Flask, Response, request, redirect

app = Flask(__name__)

# --- CONFIGURATION ---
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

CACHE = {}
AI_CACHE = {} 
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def get_base64(url):
    try:
        if not url: return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        r = requests.get(url, headers=HEADERS, timeout=3)
        return f"data:image/png;base64,{base64.b64encode(r.content).decode('utf-8')}"
    except:
        return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# --- AI LOGIC ---
def consult_gemini(context_text, user_name):
    """Generates sci-fi status using Gemini."""
    cache_key = f"{user_name}_ai"
    if cache_key in AI_CACHE: return AI_CACHE[cache_key]

    if not GOOGLE_API_KEY: return "AI MODULE OFFLINE // API KEY MISSING"

    try:
        model = genai.GenerativeModel('gemini-pro')
        # We tell the AI to be brief and "Tech" styled
        prompt = f"""
        Status: User '{user_name}' is currently: "{context_text}".
        Task: Write a highly futuristic, 5-word maximum, upper-case System Log entry describing this state.
        Style: Cyberpunk interface.
        Examples: "BIOMETRICS STABLE", "UPLINK ESTABLISHED", "PROCESSING DATA STREAM".
        """
        response = model.generate_content(prompt)
        text = response.text.strip().upper().replace('"', '').replace("'", "")
        # Fallback if AI hallucinates long text
        if len(text) > 30: text = text[:30] + "..."
        
        AI_CACHE[cache_key] = html.escape(text) # SANITIZE AI OUTPUT
        return AI_CACHE[cache_key]
    except:
        return "SYSTEM STANDBY"

# --- DATA FETCHING ---
def get_lanyard_user(user_id):
    try:
        r = requests.get(f"https://api.lanyard.rest/v1/users/{user_id}", headers=HEADERS, timeout=4)
        if r.status_code != 200: return None
        
        d = r.json().get('data')
        if not d: return None

        u = d['discord_user']
        status = d['discord_status']
        
        # Priority Logic: Game > Spotify > Custom > Online Status
        activity = "NO SIGNAL DETECTED"
        if d.get('activities'):
            for act in d['activities']:
                if act['type'] == 0: activity = f"RUNNING: {act['name']}"; break
                if act['type'] == 2: activity = "AUDIO: SPOTIFY"; break
                if act['type'] == 4: activity = f"MSG: {act['state']}"; break
        
        if activity == "NO SIGNAL DETECTED":
            activity = f"STATUS: {status.upper()}"

        return {
            "name": html.escape(u['username']), # Prevent & symbols from crashing SVG
            "status_color": {"online": "#00FF99", "idle": "#FFAA00", "dnd": "#FF4B4B"}.get(status, "#777777"),
            "raw_status": html.escape(activity.upper()),
            "avatar": get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png"),
            "id": str(user_id)
        }
    except Exception as e:
        print(f"Fetch Error: {e}")
        return None

# --- HYPER-SVG GENERATOR ---
def generate_super_svg(data, ai_message):
    
    # NOTE: The Font URL below uses &amp; instead of & to fix the XML Error
    svg = f"""<svg version="1.1" width="480" height="160" viewBox="0 0 480 160"
     xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     xmlns:ai="http://google.deepmind/schema#"
     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:chillax="http://chillax.dev/superbadge#">

  <metadata>
    <rdf:RDF>
      <dc:title>Neural Badge</dc:title>
      <ai:model>Gemini-Pro</ai:model>
      <chillax:serverID>{data['id']}</chillax:serverID>
    </rdf:RDF>
  </metadata>

  <defs>
    <style>
      /* FIX: URL escaped correctly below */
      @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;800&amp;display=swap');
      
      :root {{ --main: {data['status_color']}; --bg: #030303; }}
      
      .terminal {{ font-family: 'JetBrains Mono', monospace; fill: white; }}
      .h1 {{ font-weight: 800; font-size: 20px; letter-spacing: 2px; text-shadow: 0 0 10px rgba(0,0,0,0.5); }}
      .h2 {{ font-weight: 400; font-size: 10px; fill: var(--main); letter-spacing: 1px; }}
      .console {{ font-size: 10px; fill: #aaa; }}
      .ai-text {{ fill: #00ffff; font-weight: 800; animation: blinkCursor 4s infinite; }}

      @keyframes blinkCursor {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.7; }} }}
      
      /* CLICKABLE */
      .btn {{ cursor: pointer; transition: 0.2s; }}
      .btn:hover rect {{ stroke: #fff; fill: rgba(255,255,255,0.1); }}
    </style>

    <!-- QUANTUM SHADER (Fake GLSL in SVG) -->
    <filter id="quantumFlux" x="-20%" y="-20%" width="140%" height="140%">
      <feTurbulence type="fractalNoise" baseFrequency="0.005" numOctaves="4" seed="50">
        <animate attributeName="baseFrequency" values="0.005;0.02;0.005" dur="15s" repeatCount="indefinite"/>
      </feTurbulence>
      <feColorMatrix type="hueRotate" values="0">
        <animate attributeName="values" from="0" to="360" dur="20s" repeatCount="indefinite"/>
      </feColorMatrix>
      <feDisplacementMap in="SourceGraphic" scale="60" />
      <feGaussianBlur stdDeviation="3" />
      <feComposite in="SourceGraphic" operator="in" />
    </filter>

    <clipPath id="screenMask"><rect x="10" y="10" width="460" height="140" rx="10" /></clipPath>
    <clipPath id="avatarHex"><path d="M42 0 L84 25 L84 75 L42 100 L0 75 L0 25 Z" transform="translate(20, 30) scale(0.8)"/></clipPath>
  </defs>

  <!-- CHASSIS -->
  <rect width="480" height="160" rx="15" fill="#08080a" stroke="#222" stroke-width="2"/>
  
  <!-- LIQUID CORE -->
  <g clip-path="url(#screenMask)">
     <rect width="100%" height="100%" fill="#000" />
     <g style="mix-blend-mode: screen; opacity: 0.6">
        <circle cx="100" cy="50" r="100" fill="#5865F2" filter="url(#quantumFlux)" />
        <circle cx="380" cy="120" r="120" fill="{data['status_color']}" filter="url(#quantumFlux)" />
     </g>
     <!-- GRID -->
     <pattern id="gridPat" width="20" height="20" patternUnits="userSpaceOnUse">
        <path d="M20 0 L0 0 L0 20" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
     </pattern>
     <rect x="10" y="10" width="460" height="140" rx="10" fill="url(#gridPat)" />
  </g>

  <!-- DATA INTERFACE -->
  <rect x="10" y="10" width="460" height="2" fill="white" opacity="0.1">
    <animate attributeName="y" values="10;150;10" dur="5s" repeatCount="indefinite" />
  </rect>

  <!-- AVATAR -->
  <g>
    <path d="M42 0 L84 25 L84 75 L42 100 L0 75 L0 25 Z" fill="none" stroke="{data['status_color']}" stroke-width="2" transform="translate(20, 30) scale(0.9)">
        <animateTransform attributeName="transform" type="rotate" from="0 42 50" to="360 42 50" dur="20s" repeatCount="indefinite" />
    </path>
    <image href="{data['avatar']}" width="90" height="90" clip-path="url(#avatarHex)" x="-5" y="5"/>
  </g>

  <!-- TEXT CONSOLE -->
  <g transform="translate(120, 45)" class="terminal">
      <text x="0" y="0" class="h1">{data['name']}</text>
      <text x="0" y="15" class="h2">// {data['raw_status']}</text>
      
      <!-- AI RESPONSE BOX -->
      <g transform="translate(0, 35)">
         <rect x="-5" y="-12" width="340" height="30" fill="rgba(0,0,0,0.5)" stroke="rgba(255,255,255,0.2)" rx="4"/>
         <text x="5" y="8" class="console">GEMINI_AI :: <tspan class="ai-text">{ai_message}</tspan></text>
      </g>
      
      <text x="0" y="80" class="console" fill="#555">UID: {data['id']}  |  NET: SECURE</text>
  </g>

  <!-- CLICK TARGETS -->
  <a xlink:href="https://discord.com/users/{data['id']}" target="_blank" class="btn">
     <rect x="370" y="120" width="90" height="25" rx="5" fill="#5865F2" />
     <text x="415" y="136" text-anchor="middle" font-family="JetBrains Mono" font-size="10" font-weight="bold" fill="white">CONTACT</text>
  </a>

</svg>"""
    return svg

@app.route('/superbadge/<user_id>')
def superbadge(user_id):
    # 1. Fetch User Data
    user_data = get_lanyard_user(user_id)
    if not user_data:
        # Fallback Data
        user_data = {
            'name': 'UNKNOWN_ENTITY', 'status_color': '#FF0000', 
            'raw_status': 'DISCONNECTED', 'avatar': get_base64(""), 'id': '0000'
        }

    # 2. Consult Gemini (Cached for 15 mins)
    ai_msg = consult_gemini(user_data['raw_status'], user_data['name'])

    # 3. Generate XML
    svg = generate_super_svg(user_data, ai_msg)

    # 4. Headers
    return Response(svg, mimetype='image/svg+xml; charset=utf-8', headers={
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    })

@app.route('/')
def home():
    return """<h1 style='color:white; background:black; font-family:monospace; padding:20px'>
              NEURAL CORE ONLINE. <br><br> Use endpoint: /superbadge/[DISCORD_USER_ID]</h1>"""

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
