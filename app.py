import base64
import requests
import time
import os
from flask import Flask, render_template, Response

app = Flask(__name__)

# --- CONFIG ---
CACHE = {}
CACHE_TIMEOUT = 300  # 5 minutes cache

# Headers are CRITICAL. Without this, Discord blocks the scraper.
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_base64_image(url):
    """Downloads an image URL and converts it to a base64 string for SVG embedding."""
    if not url: return ""
    try:
        r = requests.get(url, headers=HEADERS, timeout=3) # Timeout to prevent hanging
        if r.status_code == 200:
            encoded = base64.b64encode(r.content).decode('utf-8')
            return f"data:image/png;base64,{encoded}"
    except:
        pass
    # Fallback transparent pixel
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

def get_discord_data(invite_code):
    """Fetches Discord Invite API."""
    current_time = time.time()
    
    # Check Cache
    if invite_code in CACHE:
        if current_time - CACHE[invite_code]['timestamp'] < CACHE_TIMEOUT:
            return CACHE[invite_code]['data']

    try:
        url = f"https://discord.com/api/v10/invites/{invite_code}?with_counts=true"
        r = requests.get(url, headers=HEADERS, timeout=5)
        
        # If Discord says "Unknown Invite" or bans IP
        if r.status_code != 200:
            return None

        data = r.json()
        guild_id = data['guild']['id']
        icon_hash = data['guild'].get('icon')
        icon_url = f"https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.png" if icon_hash else None
        
        base64_icon = get_base64_image(icon_url)

        result = {
            "name": data['guild']['name'],
            "total": f"{data['approximate_member_count']:,}",
            "online": f"{data['approximate_presence_count']:,}",
            "icon": base64_icon
        }

        CACHE[invite_code] = {'timestamp': current_time, 'data': result}
        return result

    except Exception as e:
        print(f"Error scraping Discord: {e}")
        return None

def get_github_data(username):
    try:
        url = f"https://api.github.com/users/{username}"
        r = requests.get(url, headers=HEADERS, timeout=5)
        if r.status_code != 200: return None
        data = r.json()
        
        base64_icon = get_base64_image(data['avatar_url'])

        return {
            "name": data['login'],
            "total": str(data['public_repos']),
            "online": str(data['followers']), 
            "icon": base64_icon,
            "subtitle": "GitHub Stats"
        }
    except:
        return None

def generate_svg(data, mode="discord"):
    # If data is missing (API error), fill with placeholders to prevent broken image
    if not data:
        data = {
            "name": "Server Error", 
            "total": "---", 
            "online": "---", 
            "icon": get_base64_image("") 
        }

    subtitle = "Support Server" if mode == "discord" else "GitHub Profile"
    online_label = "Online" if mode == "discord" else "Followers"
    count_label = "MEMBERS" if mode == "discord" else "REPOS"

    # SVG CODE (Liquid Nebula Design)
    svg = f"""<svg width="450" height="120" viewBox="0 0 450 120" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs>
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@600&family=Varela+Round&display=swap');
          .title {{ font-family: 'Fredoka', sans-serif; font-size: 28px; fill: white; font-weight: 600; text-shadow: 0 4px 10px rgba(0,0,0,0.5); }}
          .subtitle {{ font-family: 'Varela Round', sans-serif; font-size: 14px; fill: #A0A0FF; letter-spacing: 2px; text-transform: uppercase; }}
          .count-text {{ font-family: 'Fredoka', sans-serif; font-size: 40px; fill: #FF4B4B; font-weight: 700; }}
          .online-text {{ font-family: 'Varela Round', sans-serif; font-size: 10px; fill: #00FF99; }}
          .drift-slow {{ animation: drift 40s linear infinite; }}
          @keyframes drift {{ 0% {{ transform: translate(0,0) rotate(0deg); }} 50% {{ transform: translate(-20px, -10px) rotate(2deg); }} 100% {{ transform: translate(0,0) rotate(0deg); }} }}
        </style>

        <filter id="liquid" x="-20%" y="-20%" width="140%" height="140%">
          <feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="3" result="noise"><animate attributeName="baseFrequency" values="0.01;0.015;0.01" dur="15s" repeatCount="indefinite" /></feTurbulence>
          <feDisplacementMap in="SourceGraphic" in2="noise" scale="40" />
        </filter>
        <clipPath id="cardClip"><rect width="446" height="116" rx="20" /></clipPath>
        <clipPath id="iconClip"><rect width="70" height="70" rx="18" /></clipPath>
      </defs>

      <rect x="2" y="2" width="446" height="116" rx="20" fill="#080815" stroke="#333" stroke-width="2" />
      <g clip-path="url(#cardClip)" opacity="0.45">
        <g class="drift-slow">
            <circle cx="20" cy="100" r="140" fill="#5865F2" filter="url(#liquid)" />
            <circle cx="430" cy="0" r="150" fill="#FF4B4B" filter="url(#liquid)" style="mix-blend-mode: screen"/>
        </g>
      </g>
      <rect x="2" y="2" width="446" height="116" rx="20" fill="white" fill-opacity="0.03" />

      <line x1="120" y1="20" x2="120" y2="100" stroke="white" stroke-opacity="0.15" stroke-width="2" />

      <g transform="translate(25, 25)">
          <image href="{data['icon']}" width="70" height="70" clip-path="url(#iconClip)" />
          <rect width="70" height="70" rx="18" fill="none" stroke="white" stroke-opacity="0.2" stroke-width="1" />
      </g>

      <g transform="translate(140, 50)">
          <text x="0" y="5" class="title">{data['name'][:18]}</text>
          <text x="3" y="32" class="subtitle">{subtitle}</text>
      </g>

      <g transform="translate(420, 25)" text-anchor="end">
          <text x="0" y="0" font-family="sans-serif" font-size="9" fill="#aaa" letter-spacing="1">{count_label}</text>
          <text x="0" y="45" class="count-text">{data['total']}</text>
          <g transform="translate(0, 65)">
             <circle cx="-50" cy="-3" r="3" fill="#00FF99" />
             <text x="-42" y="0" class="online-text">{data['online']} {online_label}</text>
          </g>
      </g>
    </svg>"""
    return svg

# --- ROUTES ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/badge/discord/<invite_code>')
def discord_badge(invite_code):
    data = get_discord_data(invite_code)
    # If None, generate_svg will handle using placeholders
    svg = generate_svg(data, mode="discord")
    
    resp = Response(svg, mimetype='image/svg+xml; charset=utf-8')
    # Cache Control (5 mins public)
    resp.headers['Cache-Control'] = 'public, max-age=300'
    return resp

@app.route('/badge/github/<username>')
def github_badge(username):
    data = get_github_data(username)
    svg = generate_svg(data, mode="github")
    resp = Response(svg, mimetype='image/svg+xml; charset=utf-8')
    resp.headers['Cache-Control'] = 'public, max-age=300'
    return resp

if __name__ == '__main__':
    # Render provides PORT environment variable
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
