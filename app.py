import base64
import requests
import os
import datetime
import html
import random
import google.generativeai as genai
from flask import Flask, Response

app = Flask(__name__)

# --- CONFIGURATION ---
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# 1x1 Transparent Fallback
EMPTY_IMG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

def get_base64(url):
    if not url: return EMPTY_IMG
    try:
        r = requests.get(url, headers=HEADERS, timeout=3)
        if r.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(r.content).decode('utf-8')}"
    except:
        pass
    return EMPTY_IMG

# --- AI CORE ---
def consult_gemini(user_status, user_name):
    """
    Asks Gemini for a sci-fi status string.
    """
    if not GOOGLE_API_KEY: 
        return "AI OFFLINE :: SYSTEM STANDBY"

    try:
        model = genai.GenerativeModel('gemini-pro')
        # Instruct AI to be an OS
        prompt = f"""
        User '{user_name}' status is: '{user_status}'.
        Generate a Cyberpunk/Military HUD status line (Max 6 words). 
        Make it sound like a system initializing or monitoring. 
        Examples: "BIOMETRIC SYNC COMPLETE", "TARGET ACQUIRED", "NEURAL UPLINK ACTIVE".
        Return ONLY the uppercase text.
        """
        response = model.generate_content(prompt)
        text = response.text.strip().replace('"', '').replace("'", "")
        return html.escape(text[:35]) # Safety Cutoff
    except:
        return "DATA STREAM ENCRYPTED"

# --- LANYARD DATA FETCHER (Fixed Logic) ---
def get_user_data(user_id):
    try:
        url = f"https://api.lanyard.rest/v1/users/{user_id}"
        r = requests.get(url, headers=HEADERS, timeout=4)
        
        if r.status_code == 200:
            json_data = r.json()
            if json_data['success']:
                d = json_data['data']
                u = d['discord_user']
                status = d['discord_status']
                
                # --- ACTIVITY LOGIC (THE FIX) ---
                activity = "NO SIGNAL"
                
                # Check for Activities
                for act in d.get('activities', []):
                    # Type 0: Playing Game
                    if act['type'] == 0: 
                        activity = f"EXE: {act['name']}"
                        break
                    # Type 2: Spotify
                    if act['type'] == 2: 
                        activity = "AUDIO: SPOTIFY"
                        break
                    # Type 4: Custom Status (FIXED)
                    if act['type'] == 4: 
                        # Safe Get: prevent crash if 'state' is missing
                        state_txt = act.get('state', '')
                        emoji = act.get('emoji', {}).get('name', '')
                        
                        if state_txt:
                            activity = f"NOTE: {state_txt}"
                        elif emoji:
                            activity = f"MOOD: {emoji}"
                        else:
                            activity = "STATUS: ACTIVE"
                        break
                
                # Fallback if no activity found but online
                if activity == "NO SIGNAL" and status != "offline":
                    activity = f"SYSTEM: {status.upper()}"

                # Visual Colors
                colors = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#FF4444", "offline": "#555555"}
                
                return {
                    "valid": True,
                    "id": u['id'],
                    "name": html.escape(u['username'].upper()),
                    "status_color": colors.get(status, "#555"),
                    "raw_status": html.escape(activity.upper()),
                    "avatar": get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png")
                }
    except Exception as e:
        print(f"Error for {user_id}: {e}")
        pass
        
    # FAILURE MODE
    return {
        "valid": False,
        "id": str(user_id),
        "name": "UNKNOWN_ENTITY", 
        "status_color": "#FF0000", 
        "raw_status": "DISCONNECTED // ERROR", 
        "avatar": EMPTY_IMG
    }

# --- SVG GENERATOR (Fixed Hexagon) ---
def generate_badge_svg(data, ai_msg):
    # Hexagon Path Geometry
    # This path is centered in a 100x100 box approximately
    hex_d = "M25 5 L75 5 L95 50 L75 95 L25 95 L5 50 Z" 
    
    svg = f"""<svg version="1.1" width="480" height="160" viewBox="0 0 480 160"
     xmlns="http://www.w3.org/2000/svg" 
     xmlns:xlink="http://www.w3.org/1999/xlink">
  
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;800&amp;display=swap');
      
      :root {{ --main-col: {data['status_color']}; }}
      
      .font-main {{ font-family: 'JetBrains Mono', monospace; }}
      .txt-name {{ font-weight: 800; font-size: 22px; fill: white; text-shadow: 2px 2px 0px rgba(0,0,0,0.8); }}
      .txt-status {{ font-size: 11px; fill: var(--main-col); letter-spacing: 1px; font-weight: bold; }}
      
      /* AI CURSOR ANIMATION */
      .blink {{ animation: cursor 1s infinite; }}
      @keyframes cursor {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0; }} }}

      /* LIQUID ANIMATION */
      .fluid-bg {{ animation: hueShift 10s infinite linear; }}
      @keyframes hueShift {{ 0% {{ filter: hue-rotate(0deg); }} 100% {{ filter: hue-rotate(360deg); }} }}
    </style>

    <!-- COMPLEX LIQUID SHADER FILTER -->
    <filter id="liquidShader" x="-20%" y="-20%" width="140%" height="140%">
      <feTurbulence type="fractalNoise" baseFrequency="0.015" numOctaves="4" seed="85">
        <animate attributeName="baseFrequency" values="0.015;0.025;0.015" dur="15s" repeatCount="indefinite"/>
      </feTurbulence>
      <feColorMatrix type="saturate" values="3" />
      <feDisplacementMap in="SourceGraphic" scale="40" />
      <feGaussianBlur stdDeviation="3" />
      <feComposite in="SourceGraphic" operator="in" />
    </filter>

    <!-- CLIP MASKS -->
    <clipPath id="screenBounds"><rect x="12" y="12" width="456" height="136" rx="10"/></clipPath>
    
    <!-- Exact Hexagon Mask for Image -->
    <clipPath id="hexClip">
        <path d="{hex_d}" transform="translate(15, 30) scale(1.0)" />
    </clipPath>
  </defs>

  <!-- === LAYER 1: FRAME === -->
  <rect width="480" height="160" rx="16" fill="#08080A" stroke="#333" stroke-width="2"/>

  <!-- === LAYER 2: SHADER SCREEN === -->
  <g clip-path="url(#screenBounds)">
    <rect width="100%" height="100%" fill="#000"/>
    
    <!-- Animated Orbs -->
    <g class="fluid-bg" style="opacity: 0.6; mix-blend-mode: screen;">
       <circle cx="50" cy="50" r="120" fill="#5865F2" filter="url(#liquidShader)"/>
       <circle cx="430" cy="110" r="140" fill="{data['status_color']}" filter="url(#liquidShader)"/>
    </g>
    
    <!-- Scanline Grid -->
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
       <path d="M 40 0 L 0 0 0 40" fill="none" stroke="white" stroke-opacity="0.05" stroke-width="1"/>
    </pattern>
    <rect x="10" y="10" width="460" height="140" fill="url(#grid)"/>
  </g>

  <!-- === CONTENT LAYOUT === -->
  
  <!-- 1. AVATAR (Hexagon) -->
  <!-- We draw the image clipped to the hexagon, then the stroke ON TOP -->
  <g transform="translate(15, 30)">
     <image href="{data['avatar']}" width="100" height="100" clip-path="url(#hexClip)" />
     <!-- Hexagon Border (Aligned) -->
     <path d="{hex_d}" fill="none" stroke="{data['status_color']}" stroke-width="3" />
  </g>

  <!-- 2. TEXT DATA -->
  <g transform="translate(125, 55)" class="font-main">
     <text x="0" y="0" class="txt-name">{data['name']}</text>
     <text x="0" y="20" class="txt-status">>> {data['raw_status']}</text>
     
     <!-- AI CONSOLE -->
     <g transform="translate(0, 38)">
       <rect x="-5" y="-12" width="330" height="28" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.15)" rx="4"/>
       <text x="5" y="6" font-size="10" fill="#00ffff">
         AI_LINK > <tspan fill="white">{ai_msg}</tspan><tspan class="blink">_</tspan>
       </text>
     </g>
     
     <text x="0" y="78" font-size="9" fill="#555">UID: {data['id']}  ::  LINK ENCRYPTED</text>
  </g>

  <!-- INTERACTIVE OVERLAY (Full Size Click) -->
  <a xlink:href="https://discord.com/users/{data['id']}" target="_blank">
    <rect width="480" height="160" fill="transparent" style="cursor: pointer;" />
  </a>

</svg>"""
    return svg

@app.route('/superbadge/<user_id>')
def serve_badge(user_id):
    # Fetch
    data = get_user_data(user_id)
    
    # Process AI
    if data['valid']:
        msg = consult_gemini(data['raw_status'], data['name'])
    else:
        msg = "TARGET UNKNOWN - JOIN LANYARD"

    # Render
    svg = generate_badge_svg(data, msg)
    
    return Response(svg, mimetype="image/svg+xml", headers={
        "Cache-Control": "no-cache, max-age=0" # Force GitHub to re-fetch to update AI msg
    })

@app.route('/')
def home():
    return "<h1 style='color: #0f0; background:#000; font-family:monospace'>[ CHILLAX NEURAL NODE ONLINE ]</h1>"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
