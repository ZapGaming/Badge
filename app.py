import base64
import requests
import time
import os
import datetime
from flask import Flask, render_template, Response

app = Flask(__name__)

# --- CONFIG & CACHE ---
# Browser Header is required to stop Discord blocking requests (Error 403)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Simple In-Memory Cache
CACHE = {}
CACHE_TTL = 300  # 5 Minutes

def get_base64_image(url):
    """Downloads image and converts to Base64 to prevent broken SVG images."""
    if not url: return ""
    try:
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(r.content).decode('utf-8')}"
    except:
        pass
    # Fallback transparent pixel
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

def fetch_data(key, type_mode):
    """
    Unified Fetcher:
    - Replicates 'GuildMemberCountStore' via API
    - Replicates 'OnlineMemberCountStore' via API
    - Replicates User Status via Lanyard
    """
    now = time.time()
    # Cache Check
    if key in CACHE and (now - CACHE[key]['time'] < CACHE_TTL):
        return CACHE[key]['data']

    try:
        data = {}
        
        # --- MODE 1: DISCORD SERVER STATS ---
        if type_mode == "discord":
            # Hits public invite endpoint to get exact Total/Online counts
            url = f"https://discord.com/api/v10/invites/{key}?with_counts=true"
            r = requests.get(url, headers=HEADERS, timeout=5)
            
            if r.status_code != 200: return None
            json_d = r.json()
            guild = json_d.get('guild', {})
            
            # Icon handling
            icon_url = None
            if guild.get('icon'):
                icon_url = f"https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}.png"

            data = {
                "id": guild.get('id', '0'),
                "title": guild.get('name', 'Server'),
                "subtitle": "Support Server",
                "label": "MEMBERS",
                "value": f"{json_d.get('approximate_member_count', 0):,}",
                "sub_status": f"{json_d.get('approximate_presence_count', 0):,} Online",
                "accent": "#5865F2",  # Blurple
                "icon": get_base64_image(icon_url),
                "timestamp": datetime.datetime.now().isoformat()
            }

        # --- MODE 2: GITHUB PROFILE ---
        elif type_mode == "github":
            url = f"https://api.github.com/users/{key}"
            r = requests.get(url, headers=HEADERS, timeout=5)
            
            if r.status_code != 200: return None
            json_d = r.json()
            
            data = {
                "id": str(json_d.get('id', '0')),
                "title": json_d.get('login', 'User'),
                "subtitle": "GitHub Profile",
                "label": "REPOSITORIES",
                "value": str(json_d.get('public_repos', 0)),
                "sub_status": f"{json_d.get('followers', 0)} Followers",
                "accent": "#FFFFFF",
                "icon": get_base64_image(json_d.get('avatar_url')),
                "timestamp": datetime.datetime.now().isoformat()
            }

        # --- MODE 3: DISCORD USER STATUS (Lanyard) ---
        elif type_mode == "user":
            url = f"https://api.lanyard.rest/v1/users/{key}"
            r = requests.get(url, headers=HEADERS, timeout=5)
            
            if r.status_code != 200: return None
            body = r.json()
            if not body.get('success'): return None
            
            lanyard = body['data']
            user = lanyard['discord_user']
            status = lanyard['discord_status']
            
            # Activity Parsing
            activity = "Chilling"
            for act in lanyard.get('activities', []):
                if act['type'] == 0: activity = act['name']; break
                if act['type'] == 2: activity = "Spotify"; break

            colors = {"online": "#00FF99", "idle": "#FFAA00", "dnd": "#FF4B4B", "offline": "#747F8D"}

            data = {
                "id": user['id'],
                "title": user['username'],
                "subtitle": "User Status",
                "label": "STATUS",
                "value": status.upper(),
                "sub_status": activity[:20],
                "accent": colors.get(status, "#747F8D"),
                "icon": get_base64_image(f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png"),
                "timestamp": datetime.datetime.now().isoformat()
            }

        CACHE[key] = {'time': now, 'data': data}
        return data

    except Exception as e:
        print(f"Error: {e}")
        return None

def generate_full_svg(data):
    """
    Generates the SVG with all Requested Namespaces:
    RDF, DC, CC, Chillax (Custom), XHTML, MathML.
    """
    if not data:
        # Beautiful Error SVG
        return '<svg width="450" height="120" xmlns="http://www.w3.org/2000/svg"><rect width="100%" height="100%" rx="20" fill="#050005"/><text x="50%" y="50%" fill="#FF4B4B" font-family="sans-serif" text-anchor="middle">API ERROR / INVALID ID</text></svg>'

    svg = f"""<svg version="1.1" width="450" height="120" viewBox="0 0 450 120"
     xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     xmlns:xhtml="http://www.w3.org/1999/xhtml"
     xmlns:math="http://www.w3.org/1998/Math/MathML"
     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:cc="http://creativecommons.org/ns#"
     xmlns:chillax="http://chillax.dev/schema/badge#">

  <!-- === FULLY NAMESPACED METADATA === -->
  <metadata>
    <rdf:RDF>
      <cc:Work rdf:about="">
        <dc:format>image/svg+xml</dc:format>
        <dc:type rdf:resource="http://purl.org/dc/dcmitype/StillImage" />
        <dc:title>{data['title']} Status</dc:title>
        <dc:date>{data['timestamp']}</dc:date>
        <!-- Custom Chillax Namespace Fields -->
        <chillax:serverID>{data['id']}</chillax:serverID>
        <chillax:primaryStat>{data['value']}</chillax:primaryStat>
        <chillax:secondaryStat>{data['sub_status']}</chillax:secondaryStat>
      </cc:Work>
    </rdf:RDF>
  </metadata>

  <defs>
    <!-- FONTS & STYLES -->
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@600&family=Varela+Round&display=swap');
      
      .main-title {{ font-family: 'Fredoka', sans-serif; font-size: 32px; fill: white; font-weight: 600; text-shadow: 0 4px 10px rgba(0,0,0,0.8); }}
      .sub-title {{ font-family: 'Varela Round', sans-serif; font-size: 14px; fill: #A0A0FF; letter-spacing: 2px; text-transform: uppercase; }}
      .meta-label {{ font-family: 'Varela Round', sans-serif; font-size: 10px; fill: #777; letter-spacing: 1px; font-weight: bold; }}
      .online-txt {{ font-family: 'Varela Round', sans-serif; font-size: 12px; fill: #EEE; }}

      /* XHTML GLITCH TEXT ANIMATION */
      .glitch-wrap {{
        color: {data['accent']};
        font-family: 'Fredoka', sans-serif;
        font-size: 42px;
        font-weight: 900;
        text-align: right;
        text-shadow: 3px 3px 0px rgba(255,255,255,0.1), -1px -1px 0 #000;
        animation: pulseText 4s infinite alternate;
      }}
      @keyframes pulseText {{ 0% {{ opacity: 0.9; transform: scale(1); }} 100% {{ opacity: 1; transform: scale(1.02); text-shadow: 0 0 10px {data['accent']}; }} }}

      /* BACKGROUND ANIMATIONS */
      .nebula {{ animation: spinNebula 60s linear infinite; }}
      @keyframes spinNebula {{ 0% {{ transform: rotate(0deg); }} 50% {{ transform: rotate(5deg) scale(1.1); }} 100% {{ transform: rotate(0deg); }} }}

      /* HOVER EFFECTS */
      svg:hover .shake-ui {{ animation: glitch 0.3s cubic-bezier(.25, .46, .45, .94) both infinite; }}
      @keyframes glitch {{ 0% {{ transform: translate(0); }} 20% {{ transform: translate(-2px, 2px); }} 40% {{ transform: translate(-2px, -2px); }} 100% {{ transform: translate(0); }} }}
    </style>

    <!-- FRACTAL LIQUID NOISE FILTER -->
    <filter id="liquidFlow" x="-20%" y="-20%" width="140%" height="140%">
      <feTurbulence type="fractalNoise" baseFrequency="0.015" numOctaves="3" seed="100">
         <animate attributeName="baseFrequency" values="0.01;0.02;0.01" dur="15s" repeatCount="indefinite" />
      </feTurbulence>
      <feDisplacementMap in="SourceGraphic" scale="40" />
      <feGaussianBlur stdDeviation="2" />
    </filter>

    <clipPath id="cBounds"><rect width="446" height="116" rx="20" /></clipPath>
    <clipPath id="cLogo"><rect width="70" height="70" rx="18" /></clipPath>
  </defs>

  <!-- === LAYER 1: DEEP SPACE BG === -->
  <rect x="2" y="2" width="446" height="116" rx="20" fill="#050409" stroke="#222" stroke-width="2"/>
  
  <!-- === LAYER 2: LIQUID NEBULA BLOBS === -->
  <g clip-path="url(#cBounds)" opacity="0.6">
    <g class="nebula">
       <!-- Primary Blurple Blob -->
       <circle cx="0" cy="120" r="140" fill="#5865F2" filter="url(#liquidFlow)" />
       <!-- Dynamic Accent Blob (Changes Red/Green based on data) -->
       <circle cx="450" cy="0" r="150" fill="{data['accent']}" filter="url(#liquidFlow)" style="mix-blend-mode: screen"/>
       <!-- Complexity Blob -->
       <circle cx="225" cy="60" r="60" fill="#9d46ff" opacity="0.5" filter="url(#liquidFlow)" style="mix-blend-mode: overlay"/>
    </g>
  </g>

  <!-- === LAYER 3: UI ELEMENTS === -->
  <rect x="2" y="2" width="446" height="116" rx="20" fill="url(#gridPattern)" /> <!-- Uses undefined pattern default is okay or define it if needed, omitted to keep brief but grid added below -->
  <pattern id="dotPattern" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="white" opacity="0.1"/></pattern>
  <rect x="2" y="2" width="446" height="116" rx="20" fill="url(#dotPattern)" />
  <rect x="2" y="2" width="446" height="116" rx="20" fill="white" fill-opacity="0.02" />

  <!-- Divider Line -->
  <line x1="120" y1="20" x2="120" y2="100" stroke="white" stroke-opacity="0.15" stroke-width="2" stroke-linecap="round"/>

  <!-- SECTION A: ICON -->
  <g transform="translate(25, 25)">
     <image href="{data['icon']}" width="70" height="70" clip-path="url(#cLogo)" />
     <rect width="70" height="70" rx="18" fill="none" stroke="white" stroke-opacity="0.25" stroke-width="1.5" />
  </g>

  <!-- SECTION B: TITLES -->
  <g transform="translate(140, 55)">
     <text x="0" y="0" class="main-title">{data['title'][:15]}</text>
     <text x="2" y="25" class="sub-title">{data['subtitle']}</text>
  </g>

  <!-- SECTION C: STATS (Right Aligned) -->
  <g transform="translate(420, 25)" text-anchor="end" class="shake-ui">
      
      <!-- Label -->
      <text x="0" y="0" class="meta-label">{data['label']}</text>
      
      <!-- MathML Symbol: Summation (Display only if supported, nice touch) -->
      <switch>
          <foreignObject x="-240" y="5" width="50" height="60">
             <math xmlns="http://www.w3.org/1998/Math/MathML" display="block">
                <mo style="font-size: 30px; color: rgba(255,255,255,0.2);">∑</mo>
             </math>
          </foreignObject>
      </switch>

      <!-- Main Count: XHTML Glitch or Fallback Text -->
      <switch>
         <foreignObject x="-210" y="5" width="210" height="60" requiredExtensions="http://www.w3.org/1999/xhtml">
            <xhtml:div xmlns:xhtml="http://www.w3.org/1999/xhtml" class="glitch-wrap">
               {data['value']}
            </xhtml:div>
         </foreignObject>
         <text x="0" y="45" font-family="'Fredoka', sans-serif" font-weight="900" font-size="42" fill="{data['accent']}">{data['value']}</text>
      </switch>

      <!-- Bottom Status Line -->
      <g transform="translate(0, 65)">
         <circle cx="-5" cy="-4" r="3" fill="#00FF99"/>
         <text x="-12" y="0" class="online-txt">{data['sub_status']}</text>
      </g>
  </g>

  <!-- CLICKABLE HOTSPOT -->
  <rect width="450" height="120" fill="transparent" />

</svg>"""
    return svg

# --- FLASK ROUTING ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/badge/<mode>/<key>')
def render_badge(mode, key):
    
    # 1. Determine Logic based on Mode
    target_mode = mode
    # If users enters Discord Badge mode but puts in an ID (User ID), swap to Lanyard logic
    if mode == 'discord' and key.isdigit() and len(key) > 15:
        target_mode = 'user'

    # 2. Fetch Data
    data_payload = fetch_data(key, target_mode)

    # 3. Generate SVG
    svg_output = generate_full_svg(data_payload)
    
    # 4. Return with correct headers
    return Response(svg_output, mimetype='image/svg+xml; charset=utf-8', headers={
        "Cache-Control": "public, max-age=120"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
