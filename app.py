import base64
import requests
import time
import os
from flask import Flask, render_template, Response, request

app = Flask(__name__)

# --- CONFIG & CACHE ---
# Caching to prevent hitting Discord rate limits (429 Too Many Requests)
CACHE = {}
CACHE_TIMEOUT = 120 # 2 minutes

# Fake a browser so Discord API returns data instead of 403 Forbidden
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_base64_image(url):
    """Downloads an image URL and converts it to base64 for embedding."""
    if not url: return ""
    try:
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            encoded = base64.b64encode(r.content).decode('utf-8')
            return f"data:image/png;base64,{encoded}"
    except:
        pass
    # 1x1 Transparent Pixel Fallback
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# --- DATA FETCHERS ---

def get_discord_invite_data(invite_code):
    """
    Replaces: GuildMemberCountStore.getMemberCount(guildId)
    Replaces: OnlineMemberCountStore.getCount(guildId)
    Uses: Public Invite API
    """
    cache_key = f"invite:{invite_code}"
    if cache_key in CACHE and (time.time() - CACHE[cache_key]['time'] < CACHE_TIMEOUT):
        return CACHE[cache_key]['data']

    try:
        url = f"https://discord.com/api/v10/invites/{invite_code}?with_counts=true"
        r = requests.get(url, headers=HEADERS, timeout=5)
        
        if r.status_code != 200: return None
        
        data = r.json()
        
        # Get Icon
        guild = data.get('guild', {})
        icon_url = f"https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}.png" if guild.get('icon') else None
        
        result = {
            "title": guild.get('name', 'Server'),
            "subtitle": "Support Server",
            "count": f"{data['approximate_member_count']:,}", # Format with commas
            "sub_status": f"{data['approximate_presence_count']:,} Online",
            "color_accent": "#00FF99", # Green dot for online
            "icon": get_base64_image(icon_url)
        }
        
        CACHE[cache_key] = {'time': time.time(), 'data': result}
        return result
    except Exception as e:
        print(f"Discord API Error: {e}")
        return None

def get_lanyard_data(user_id):
    """
    Fetches User Presence (Playing, Spotify, etc.)
    """
    cache_key = f"user:{user_id}"
    if cache_key in CACHE and (time.time() - CACHE[cache_key]['time'] < 30): # Short cache for status
        return CACHE[cache_key]['data']
        
    try:
        url = f"https://api.lanyard.rest/v1/users/{user_id}"
        r = requests.get(url, headers=HEADERS, timeout=5)
        if r.status_code != 200: return None
        
        payload = r.json()
        if not payload.get('success'): return None
        
        data = payload['data']
        user = data['discord_user']
        
        # Determine status color
        status = data.get('discord_status', 'offline')
        color_map = { "online": "#00FF99", "idle": "#FFAA00", "dnd": "#FF4B4B", "offline": "#747F8D" }
        
        # Find primary activity (Game or Spotify)
        activity_text = "Chilling"
        for act in data.get('activities', []):
            if act['type'] == 0: # Game
                activity_text = f"Playing {act['name']}"
                break
            if act['type'] == 2: # Spotify
                activity_text = "Listening to Spotify"
                break
            if act['type'] == 4: # Status Message
                activity_text = act['state']
                break
                
        result = {
            "title": user['username'],
            "subtitle": "User Status",
            "count": status.upper(),
            "sub_status": activity_text[:20], # Truncate long status
            "color_accent": color_map.get(status, "#747F8D"),
            "icon": get_base64_image(f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png")
        }
        CACHE[cache_key] = {'time': time.time(), 'data': result}
        return result
    except:
        return None

def get_github_data(username):
    """
    Fetches Repos and Followers
    """
    cache_key = f"gh:{username}"
    if cache_key in CACHE and (time.time() - CACHE[cache_key]['time'] < CACHE_TIMEOUT):
        return CACHE[cache_key]['data']

    try:
        url = f"https://api.github.com/users/{username}"
        r = requests.get(url, headers=HEADERS, timeout=5)
        if r.status_code != 200: return None
        data = r.json()
        
        result = {
            "title": data['login'],
            "subtitle": "GitHub Profile",
            "count": f"{data['public_repos']}",
            "sub_status": f"{data['followers']} Followers",
            "color_accent": "#FFFFFF",
            "icon": get_base64_image(data['avatar_url'])
        }
        CACHE[cache_key] = {'time': time.time(), 'data': result}
        return result
    except:
        return None

# --- SVG GENERATOR (The Complex One) ---

def generate_complex_svg(data, mode="default"):
    """
    Generates the SVG using namespaces, complex filters, and data injection.
    """
    if not data:
        # Error Fallback
        return '<svg width="450" height="120"><rect width="100%" height="100%" fill="#111"/><text x="20" y="65" fill="red" font-family="sans-serif">Error Fetching Data</text></svg>'

    # Default Color Scheme: Blurple to Red
    # You can customize these gradients per badge if you want
    accent_color = data['color_accent'] # For the status dot

    svg = f"""<svg width="450" height="120" viewBox="0 0 450 120" 
     xmlns="http://www.w3.org/2000/svg" 
     xmlns:xlink="http://www.w3.org/1999/xlink">
  
  <metadata>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:dc="http://purl.org/dc/elements/1.1/">
      <rdf:Description>
        <dc:title>{data['title']} Badge</dc:title>
        <dc:description>Generated by Chillax Badge System</dc:description>
      </rdf:Description>
    </rdf:RDF>
  </metadata>

  <defs>
    <!-- FONTS -->
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@600&family=Varela+Round&display=swap');
      
      .title {{ font-family: 'Fredoka', sans-serif; font-size: 32px; fill: white; font-weight: 600; text-shadow: 0 4px 12px rgba(0,0,0,0.6); }}
      .subtitle {{ font-family: 'Varela Round', sans-serif; font-size: 14px; fill: #A0A0FF; letter-spacing: 2px; text-transform: uppercase; }}
      .count {{ font-family: 'Fredoka', sans-serif; font-size: 38px; fill: #FF4B4B; font-weight: 700; }}
      .status {{ font-family: 'Varela Round', sans-serif; font-size: 10px; fill: {accent_color}; }}

      /* ANIMATIONS */
      .bg-drift {{ animation: nebulaMove 40s linear infinite; }}
      @keyframes nebulaMove {{ 
          0% {{ transform: translate(0,0) rotate(0deg); }} 
          50% {{ transform: translate(-20px, -15px) rotate(2deg); }} 
          100% {{ transform: translate(0,0) rotate(0deg); }} 
      }}
      
      .pulse {{ animation: heartBeat 3s ease-in-out infinite; }}
      @keyframes heartBeat {{ 0% {{ opacity: 0.8; }} 50% {{ opacity: 1; transform: scale(1.05); }} 100% {{ opacity: 0.8; }} }}

      /* MOUSE INTERACTION */
      svg:hover .glitch {{ animation: skewAnim 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94) both infinite; }}
      @keyframes skewAnim {{ 0% {{ transform: translate(0); }} 20% {{ transform: translate(-2px, 2px); }} 40% {{ transform: translate(-2px, -2px); }} 60% {{ transform: translate(2px, 2px); }} 100% {{ transform: translate(0); }} }}
    </style>

    <!-- FRACTAL LIQUID FILTER -->
    <filter id="liquidGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feTurbulence type="fractalNoise" baseFrequency="0.015" numOctaves="3" result="noise" seed="42">
         <animate attributeName="baseFrequency" values="0.015;0.025;0.015" dur="30s" repeatCount="indefinite" />
      </feTurbulence>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="40" />
      <feGaussianBlur stdDeviation="1.5" />
    </filter>

    <clipPath id="cardBounds"><rect width="446" height="116" rx="20" /></clipPath>
    <clipPath id="iconCircle"><rect width="70" height="70" rx="18" /></clipPath>
  </defs>

  <!-- 1. BASE BACKGROUND (DEEP SPACE) -->
  <rect x="2" y="2" width="446" height="116" rx="20" fill="#080812" stroke="#333" stroke-width="2" />

  <!-- 2. ANIMATED NEBULA BLOBS -->
  <g clip-path="url(#cardBounds)" opacity="0.45">
    <g class="bg-drift">
        <circle cx="50" cy="120" r="130" fill="#5865F2" filter="url(#liquidGlow)" />
        <circle cx="420" cy="10" r="150" fill="#FF4B4B" filter="url(#liquidGlow)" style="mix-blend-mode: lighten"/>
        <!-- Extra vivid element for complexity -->
        <circle cx="200" cy="60" r="60" fill="#8800ff" filter="url(#liquidGlow)" opacity="0.6" style="mix-blend-mode: screen"/>
    </g>
  </g>
  
  <!-- 3. GRID & GLASS OVERLAY -->
  <pattern id="tinyGrid" width="20" height="20" patternUnits="userSpaceOnUse">
     <circle cx="1" cy="1" r="1" fill="white" opacity="0.1"/>
  </pattern>
  <rect x="2" y="2" width="446" height="116" rx="20" fill="url(#tinyGrid)" />
  <rect x="2" y="2" width="446" height="116" rx="20" fill="white" fill-opacity="0.03" />

  <!-- === LAYOUT CONTENT === -->
  <line x1="120" y1="20" x2="120" y2="100" stroke="white" stroke-opacity="0.15" stroke-width="2" stroke-linecap="round" />

  <!-- LOGO SECTION -->
  <g transform="translate(25, 25)">
      <!-- Soft Pulsing Glow behind Logo -->
      <circle cx="35" cy="35" r="45" fill="white" opacity="0.05" class="pulse"/>
      
      <image href="{data['icon']}" width="70" height="70" clip-path="url(#iconCircle)" />
      <!-- Glass Rim -->
      <rect width="70" height="70" rx="18" fill="none" stroke="white" stroke-opacity="0.25" stroke-width="1.5" />
  </g>

  <!-- TITLE SECTION -->
  <g transform="translate(140, 55)">
      <text x="0" y="0" class="title">{data['title'][:16]}</text> <!-- Truncate to fit -->
      <text x="3" y="25" class="subtitle">{data['subtitle']}</text>
  </g>

  <!-- DATA SECTION -->
  <g transform="translate(420, 30)" text-anchor="end" class="glitch" style="cursor: crosshair">
      <text x="0" y="45" class="count" filter="url(#liquidGlow)">{data['count']}</text>
      <g transform="translate(0, 65)">
         <circle cx="-60" cy="-3" r="3" fill="{accent_color}" />
         <text x="-52" y="0" class="status">{data['sub_status']}</text>
      </g>
  </g>
  
  <!-- INTERACTIVE HOTSPOT -->
  <rect width="450" height="120" fill="transparent" />

</svg>"""
    return svg


# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/badge/discord/<code_or_id>')
def badge_discord(code_or_id):
    """
    If param is a user ID (numbers), go Lanyard. 
    If param is text (invite), go Discord Invite.
    """
    if code_or_id.isdigit() and len(code_or_id) > 15:
        # It's a User ID -> Use Lanyard
        data = get_lanyard_data(code_or_id)
        if not data: data = {'title': 'Unknown', 'subtitle': 'User', 'count': 'ERR', 'sub_status': 'Not Found', 'color_accent': 'red', 'icon': get_base64_image("")}
    else:
        # It's an Invite -> Use Discord API
        data = get_discord_invite_data(code_or_id)
        if not data: data = {'title': 'Error', 'subtitle': 'Server', 'count': '---', 'sub_status': 'Invalid Invite', 'color_accent': 'red', 'icon': get_base64_image("")}

    svg = generate_complex_svg(data)
    resp = Response(svg, mimetype='image/svg+xml; charset=utf-8')
    resp.headers['Cache-Control'] = 'public, max-age=60'
    return resp

@app.route('/badge/github/<username>')
def badge_github(username):
    data = get_github_data(username)
    if not data: data = {'title': 'Error', 'subtitle': 'Profile', 'count': '?', 'sub_status': 'User Not Found', 'color_accent': 'red', 'icon': get_base64_image("")}
    
    svg = generate_complex_svg(data)
    resp = Response(svg, mimetype='image/svg+xml; charset=utf-8')
    resp.headers['Cache-Control'] = 'public, max-age=120'
    return resp

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
