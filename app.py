import base64
import requests
import os
import datetime
import random
import google.generativeai as genai
from flask import Flask, Response, request, redirect

app = Flask(__name__)

# --- CONFIGURATION ---
# Get key from: https://aistudio.google.com/app/apikey
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

CACHE = {}
AI_CACHE = {} 
CACHE_TTL = 300 # 5 min for logic
AI_TTL = 900    # 15 min for AI responses (save quota)

# Fake Browser Header
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def get_base64(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=3)
        return f"data:image/png;base64,{base64.b64encode(r.content).decode('utf-8')}"
    except:
        return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# --- AI LOGIC ---
def consult_gemini(context_text, user_name):
    """
    Asks Gemini to generate a short 'System Status' or 'Roast'.
    """
    # Check AI Cache first
    cache_key = f"{user_name}_ai"
    if cache_key in AI_CACHE:
        return AI_CACHE[cache_key]

    if not GOOGLE_API_KEY:
        return "AI MODULE OFFLINE // API KEY MISSING"

    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"""
        Act as a Sci-Fi Ship Computer (like JARVIS or Cortana).
        The user '{user_name}' current status is: "{context_text}".
        Write a ONE LINE, COOL, UPPERCASE status update about this. 
        Max 7 words. Be cryptic but cool. 
        Examples: "SYNCHRONIZING NEURAL NET", "COMPILING QUANTUM SHARDS", "IDLE DETECTED: POWER SAVE MODE".
        """
        response = model.generate_content(prompt)
        text = response.text.strip().upper().replace('"', '')
        
        AI_CACHE[cache_key] = text
        return text
    except Exception as e:
        return "SYSTEM STANDBY // AI REBOOTING"

# --- DATA FETCHING ---
def get_lanyard_user(user_id):
    """Fetches User Status & Activity."""
    try:
        r = requests.get(f"https://api.lanyard.rest/v1/users/{user_id}", headers=HEADERS, timeout=4)
        if r.status_code != 200: return None
        
        d = r.json()['data']
        u = d['discord_user']
        status = d['discord_status']
        
        activity = "NET_RUNNING"
        for act in d.get('activities', []):
            if act['type'] == 0: activity = f"PLAYING {act['name']}".upper()
            if act['type'] == 2: activity = "PROCESSING AUDIO STREAM"
            if act['type'] == 4: activity = "DATA UPLINK ESTABLISHED"

        return {
            "name": u['username'],
            "status_color": {"online": "#00FF99", "idle": "#FFAA00", "dnd": "#FF4B4B"}.get(status, "#777"),
            "raw_status": activity,
            "avatar": get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png"),
            "id": user_id
        }
    except:
        return None

# --- HYPER-SVG GENERATOR ---
def generate_super_svg(data, ai_message):
    
    # We use GLSL-like SVG Filters to simulate shaders
    svg = f"""<svg version="1.1" width="480" height="160" viewBox="0 0 480 160"
     xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     xmlns:xhtml="http://www.w3.org/1999/xhtml"
     xmlns:ai="http://google.deepmind/schema#"
     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:chillax="http://chillax.dev/superbadge#">

  <metadata>
    <rdf:RDF>
      <dc:title>Interactive Neural Badge</dc:title>
      <dc:creator>Gemini Integration System</dc:creator>
      <ai:model>Gemini-Pro</ai:model>
      <ai:response>{ai_message}</ai:response>
      <chillax:interaction>True</chillax:interaction>
    </rdf:RDF>
  </metadata>

  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;800&display=swap');
      
      :root {{ --main: {data['status_color']}; --bg: #030303; }}
      
      .terminal {{ font-family: 'JetBrains Mono', monospace; fill: white; }}
      .h1 {{ font-weight: 800; font-size: 20px; letter-spacing: 2px; }}
      .h2 {{ font-weight: 400; font-size: 10px; fill: var(--main); letter-spacing: 1px; }}
      .console {{ font-size: 10px; fill: #aaa; }}
      .ai-text {{ fill: #00ffff; font-weight: 800; animation: blinkCursor 4s infinite; }}

      @keyframes blinkCursor {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.7; }} }}
      
      /* HYPER SHADER ANIMATION */
      .shader-anim {{ animation: shiftColor 20s infinite alternate; }}
      @keyframes shiftColor {{ 0% {{ fill: #5865F2; }} 100% {{ fill: #FF0055; }} }}
      
      /* CLICKABLE BUTTONS STYLING */
      .btn {{ cursor: pointer; transition: 0.2s; }}
      .btn:hover rect {{ stroke: #fff; fill: rgba(255,255,255,0.1); }}
    </style>

    <!-- FAKE GLSL SHADER: DISPLACEMENT TURBULENCE -->
    <filter id="quantumFlux" x="-20%" y="-20%" width="140%" height="140%">
      <feTurbulence type="fractalNoise" baseFrequency="0.005" numOctaves="5" seed="50">
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

  <!-- === LAYER 1: CHASSIS === -->
  <rect width="480" height="160" rx="15" fill="#08080a" stroke="#222" stroke-width="2"/>
  
  <!-- === LAYER 2: THE QUANTUM BACKGROUND (GLSL MIMIC) === -->
  <g clip-path="url(#screenMask)">
     <rect width="100%" height="100%" fill="#000" />
     <!-- Dynamic Plasma -->
     <g style="mix-blend-mode: screen; opacity: 0.6">
        <circle cx="100" cy="50" r="100" class="shader-anim" filter="url(#quantumFlux)" />
        <circle cx="380" cy="120" r="120" fill="{data['status_color']}" filter="url(#quantumFlux)" />
     </g>
     <!-- Grid Overlay -->
     <path d="M0 0 L480 0 L480 160 L0 160" fill="url(#gridPat)" />
  </g>

  <!-- === LAYER 3: INTERFACE === -->
  <pattern id="gridPat" width="20" height="20" patternUnits="userSpaceOnUse">
    <path d="M20 0 L0 0 L0 20" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
  </pattern>
  <rect x="10" y="10" width="460" height="140" rx="10" fill="url(#gridPat)" />
  
  <!-- Scanner Line -->
  <rect x="10" y="10" width="460" height="2" fill="white" opacity="0.1">
    <animate attributeName="y" values="10;150;10" dur="5s" repeatCount="indefinite" />
  </rect>

  <!-- === DATA DISPLAY === -->
  
  <!-- AVATAR (HEXAGON MASK) -->
  <g>
    <!-- Rotating ring behind avatar -->
    <path d="M42 0 L84 25 L84 75 L42 100 L0 75 L0 25 Z" fill="none" stroke="{data['status_color']}" stroke-width="2" transform="translate(20, 30) scale(0.9)">
        <animateTransform attributeName="transform" type="rotate" from="0 42 50" to="360 42 50" dur="20s" repeatCount="indefinite" />
    </path>
    <image href="{data['avatar']}" width="90" height="90" clip-path="url(#avatarHex)" x="-5" y="5"/>
  </g>

  <!-- TERMINAL READOUT -->
  <g transform="translate(120, 45)" class="terminal">
      <text x="0" y="0" class="h1">{data['name'].upper()}</text>
      <text x="0" y="15" class="h2"> // {data['raw_status']}</text>
      
      <!-- AI MESSAGE BOX -->
      <g transform="translate(0, 35)">
         <rect x="-5" y="-12" width="340" height="30" fill="rgba(0,0,0,0.5)" stroke="rgba(255,255,255,0.2)" rx="4"/>
         <text x="5" y="8" class="console">GEMINI_AI > <tspan class="ai-text">{ai_message}</tspan></text>
      </g>
      
      <!-- FOOTER STATS -->
      <text x="0" y="80" class="console" fill="#555">UID: {data['id']}  |  LINK_STATUS: STABLE</text>
  </g>

  <!-- === INTERACTIVE 'BUTTONS' (LINKS) === -->
  <!-- Because we can't do Javascript, we map rects to anchors -->
  
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
        user_data = {
            'name': 'UNKNOWN', 'status_color': '#FF0000', 
            'raw_status': 'DISCONNECTED', 'avatar': get_base64(""), 'id': '0000'
        }

    # 2. Consult AI (What witty thing to say based on status?)
    #    We pass the activity text (e.g. "PLAYING MINECRAFT")
    ai_msg = consult_gemini(user_data['raw_status'], user_data['name'])

    # 3. Build the Hyper-SVG
    svg = generate_super_svg(user_data, ai_msg)

    # 4. Return with NO-CACHE (So the AI message updates)
    return Response(svg, mimetype='image/svg+xml; charset=utf-8', headers={
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    })

@app.route('/')
def home():
    return "Chillax Neural AI System Online. Endpoints: /superbadge/<userid>"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
