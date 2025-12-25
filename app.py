import os
import time
import requests
import html
import re
from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# =======================
#    CONFIGURATION
# =======================
HEADERS = {'User-Agent': 'Titan-v64/Unified'}
CACHE = {}
# Default ID if none provided
DEFAULT_ID = "1173155162093785099" 

# Social Link Map
LINK_MAP = {
    "github": "https://github.com/{}",
    "steam": "https://steamcommunity.com/profiles/{}",
    "twitch": "https://twitch.tv/{}",
    "spotify": "https://open.spotify.com/user/{}",
    "twitter": "https://x.com/{}",
    "reddit": "https://reddit.com/user/{}",
    "youtube": "https://youtube.com/{}",
    "tiktok": "https://tiktok.com/@{}"
}

# =======================
#    BACKEND (DATA ENGINE)
# =======================

def get_profile_data(uid):
    """
    The Single Truth Source.
    Fetches from Lanyard & DCDN, merges them into a clean JSON structure.
    """
    
    # 1. Fetch DCDN (Profile Assets)
    dcdn = {}
    try:
        r = requests.get(f"https://dcdn.dstn.to/profile/{uid}", headers=HEADERS, timeout=3)
        if r.status_code == 200: dcdn = r.json()
    except: pass
    
    # 2. Fetch Lanyard (Live Status)
    lanyard = {}
    try:
        r = requests.get(f"https://api.lanyard.rest/v1/users/{uid}", headers=HEADERS, timeout=3)
        if r.status_code == 200: 
            body = r.json()
            if body.get('success'): lanyard = body['data']
    except: pass
    
    if not lanyard and not dcdn:
        return None # User doesn't exist
    
    # --- PROCESSING ---
    
    # 1. User Identity
    u_dcdn = dcdn.get('user', {})
    u_lan = lanyard.get('discord_user', {})
    
    # IDs
    username = u_dcdn.get('username') or u_lan.get('username') or "Unknown"
    display = u_dcdn.get('global_name') or u_lan.get('global_name') or username
    
    # Images (Prefer DCDN for HD quality)
    av_hash = u_dcdn.get('avatar') or u_lan.get('avatar')
    avatar_url = f"https://cdn.discordapp.com/avatars/{uid}/{av_hash}.png?size=256" if av_hash else "https://cdn.discordapp.com/embed/avatars/0.png"
    
    bn_hash = u_dcdn.get('banner') # Lanyard doesn't reliably give banner hashes
    banner_url = f"https://cdn.discordapp.com/banners/{uid}/{bn_hash}.png?size=1024" if bn_hash else avatar_url
    
    # Decor
    deco_hash = u_dcdn.get('avatar_decoration')
    deco_url = f"https://cdn.discordapp.com/avatar-decoration-presets/{deco_hash}.png" if deco_hash else None

    # Colors & Text
    # DCDN gives INT color, convert to HEX
    accent_int = u_dcdn.get('accent_color')
    if accent_int:
        accent_hex = f"#{accent_int:06x}"
    else:
        # Fallback to status colors
        status = lanyard.get('discord_status', 'offline')
        status_colors = {
            "online": "#23a559", "idle": "#f0b232", "dnd": "#f23f42", 
            "offline": "#80848e", "streaming": "#593695"
        }
        accent_hex = status_colors.get(status, "#5865F2")

    bio = u_dcdn.get('bio') or lanyard.get('kv', {}).get('bio') or "No biography found."
    bio = html.escape(bio)

    # 2. Activity / Music
    activity = {
        "type": "idle",
        "header": "CURRENTLY",
        "title": "Idling",
        "sub": "No active tasks",
        "image": None,
        "is_music": False,
        "start": 0, "end": 0
    }
    
    # Spotify Priority
    if lanyard.get('spotify'):
        s = lanyard['spotify']
        activity = {
            "type": "spotify",
            "header": "LISTENING TO SPOTIFY",
            "title": s['song'],
            "sub": s['artist'],
            "image": s['album_art_url'],
            "is_music": True,
            "start": s['timestamps']['start'],
            "end": s['timestamps']['end']
        }
    # Game Priority
    elif lanyard.get('activities'):
        for act in lanyard['activities']:
            if act['type'] == 4: continue # Custom status skip
            
            # Asset Resolver
            img = None
            if act.get('assets') and act['assets'].get('large_image'):
                raw = act['assets']['large_image']
                if raw.startswith("mp:"): img = f"https://media.discordapp.net/{raw.replace('mp:','')}"
                else: img = f"https://cdn.discordapp.com/app-assets/{act['application_id']}/{raw}.png"
            
            head_txt = "PLAYING" if act['type'] == 0 else "WATCHING"
            
            activity = {
                "type": "game",
                "header": f"{head_txt} {act['name'].upper()}",
                "title": act.get('details') or act['name'],
                "sub": act.get('state') or "In Menu",
                "image": img,
                "is_music": False
            }
            break
            
    # 3. Connections & Badges (Formatted)
    badges = []
    for b in dcdn.get('badges', []):
        badges.append({
            "name": b['id'],
            "icon": f"https://cdn.discordapp.com/badge-icons/{b['icon']}.png"
        })
        
    connections = []
    for c in dcdn.get('connected_accounts', []):
        c_type = c['type']
        # Build Real URL
        url = "#"
        if c_type in LINK_MAP:
            slug = c['id'] if c_type == 'steam' else c['name']
            url = LINK_MAP[c_type].format(slug)
        
        connections.append({
            "type": c_type,
            "url": url,
            "icon": f"https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/{c_type.replace('.','dot')}.svg"
        })
    
    platforms = []
    for p in ['desktop','mobile','web']:
        if lanyard.get(f'active_on_discord_{p}'): platforms.append(p)

    # FINAL JSON STRUCTURE
    return {
        "success": True,
        "identity": {
            "name": display_name,
            "username": username,
            "id": uid,
            "avatar": avatar_url,
            "banner": banner_url,
            "decoration": deco_url,
            "accent_color": accent_hex,
            "status_color": accent_hex, # synced
            "bio": bio
        },
        "assets": {
            "badges": badges,
            "connections": connections,
            "platforms": platforms
        },
        "activity": activity
    }

# =======================
#    HTML FRONTEND (UI)
# =======================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Titan View</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&family=Pacifico&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
    <style>
        :root { --acc: #5865F2; --text: #FFF; --bg: #09090b; }
        * { margin:0; padding:0; box-sizing:border-box; }
        body { background: var(--bg); color: var(--text); font-family: 'Outfit', sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; overflow: hidden; }

        /* Cinematic Background */
        .backdrop {
            position: fixed; top: -10%; left: -10%; width: 120%; height: 120%;
            background-size: cover; background-position: center;
            filter: blur(80px) brightness(0.4);
            z-index: -1;
            transition: background-image 1s ease;
            animation: drift 60s infinite alternate;
        }
        @keyframes drift { from{transform:scale(1)} to{transform:scale(1.1)} }

        /* Glass Card */
        .card {
            width: 800px; height: 320px;
            background: rgba(18, 18, 24, 0.65);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 32px;
            backdrop-filter: blur(40px);
            box-shadow: 0 40px 100px -20px rgba(0,0,0,0.8);
            position: relative;
            display: flex; flex-direction: column;
            overflow: hidden;
            transition: border-color 0.5s;
        }

        /* --- TOP SECTION --- */
        .profile { padding: 40px 40px 20px 40px; display: flex; gap: 35px; align-items: center; position: relative; }
        
        .avatar-group { position: relative; width: 140px; height: 140px; flex-shrink: 0; }
        .avatar { width: 100%; height: 100%; border-radius: 50%; object-fit: cover; }
        .decoration { position: absolute; top:-18px; left:-18px; width: 176px; height: 176px; pointer-events: none; z-index: 2; }
        
        /* Status Dot */
        .status { 
            position: absolute; bottom: 8px; right: 8px; 
            width: 32px; height: 32px; 
            background: #121215; border-radius: 50%; 
            display: grid; place-items: center; z-index: 3;
        }
        .status-in { 
            width: 18px; height: 18px; 
            background: var(--acc); border-radius: 50%; 
            box-shadow: 0 0 15px var(--acc); 
            animation: pulse 2s infinite; 
        }

        .meta { flex: 1; min-width: 0; z-index: 2; }
        
        .badges { display: flex; gap: 8px; margin-bottom: 5px; height: 28px; }
        .badge { height: 24px; filter: drop-shadow(0 2px 4px black); transition: transform 0.2s; }
        .badge:hover { transform: scale(1.2); }

        .name-row { display: flex; align-items: baseline; gap: 15px; }
        h1 { font-family: 'Pacifico', cursive; font-size: 54px; margin: 0; line-height: 1.1; text-shadow: 0 5px 15px rgba(0,0,0,0.5); }
        .username { font-family: 'JetBrains Mono'; color: #888; font-size: 14px; }
        
        .bio { 
            margin-top: 8px; font-size: 16px; color: #d1d5db; line-height: 1.4; opacity: 0.9;
            display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
        }

        /* --- BOTTOM SECTION (DOCK) --- */
        .dock {
            margin: 0 25px 25px 25px;
            flex: 1;
            background: rgba(0,0,0,0.3);
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.05);
            display: flex; align-items: center; padding: 20px;
            position: relative;
        }
        
        .art { width: 70px; height: 70px; border-radius: 12px; margin-right: 20px; object-fit: cover; box-shadow: 0 5px 20px rgba(0,0,0,0.4); flex-shrink:0; background: #222; }
        
        .activity { flex: 1; overflow: hidden; display: flex; flex-direction: column; justify-content: center; }
        .act-head { font-size: 10px; font-weight: 800; color: var(--acc); letter-spacing: 2px; margin-bottom: 2px; text-transform: uppercase; font-family: 'JetBrains Mono'; }
        .act-title { font-size: 20px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: white; }
        .act-sub { font-size: 14px; color: #a1a1aa; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

        .socials { display: flex; gap: 12px; margin-left: 20px; }
        .social-btn {
            width: 32px; height: 32px;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            display: grid; place-items: center;
            transition: 0.2s;
        }
        .social-btn img { width: 16px; height: 16px; filter: invert(1); opacity: 0.8; }
        .social-btn:hover { background: rgba(255,255,255,0.2); transform: translateY(-3px); }
        .social-btn:hover img { opacity: 1; }

        /* Platforms (Absolute Top Right) */
        .platforms { position: absolute; top: 40px; right: 40px; display: flex; gap: 10px; }
        .plat-icon { width: 20px; fill: var(--text-primary); opacity: 0.5; }
        .plat-icon.active { opacity: 1; fill: var(--acc); filter: drop-shadow(0 0 5px var(--acc)); }

        /* Progress Bar */
        .prog-track { position: absolute; bottom: 0; left: 0; width: 100%; height: 3px; background: rgba(255,255,255,0.1); }
        .prog-fill { height: 100%; background: var(--acc); width: 0%; transition: width 1s linear; }

        @keyframes pulse { 50% { opacity: 0.5; } }
        /* SVG paths for platform icons inline */
    </style>
</head>
<body>

    <div class="backdrop" id="bg"></div>

    <div class="card" id="cardContainer">
        <!-- TOP RIGHT: Platforms -->
        <div class="platforms" id="platContainer"></div>

        <div class="profile">
            <div class="avatar-group">
                <img id="avatar" class="avatar" src="">
                <img id="deco" class="decoration" src="" style="display:none;">
                <div class="status"><div class="status-in" id="statColor"></div></div>
            </div>
            
            <div class="meta">
                <div class="badges" id="badgeContainer"></div>
                <div class="name-row">
                    <h1 id="name">...</h1>
                    <span class="username" id="username">@...</span>
                </div>
                <div class="bio" id="bio">...</div>
            </div>
        </div>

        <div class="dock">
            <img id="art" class="art" src="">
            <div class="activity">
                <div class="act-head" id="actHead">Loading</div>
                <div class="act-title" id="actTitle">...</div>
                <div class="act-sub" id="actSub">...</div>
            </div>
            <div class="socials" id="connContainer"></div>
            
            <div class="prog-track"><div class="prog-fill" id="progBar"></div></div>
        </div>
    </div>

<script>
    const USER_ID = window.location.pathname.split("/").pop() || "1173155162093785099"; // Fallback to Zandy

    // SVGs
    const PLATS = {
        desktop: '<svg viewBox="0 0 24 24"><path d="M4 4h16c1.1 0 2 .9 2 2v9c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2zm0 2v9h16V6H4zm8 14c-.55 0-1-.45-1-1v-1h2v1c0 .55-.45 1-1 1z" fill="currentColor"/></svg>',
        mobile: '<svg viewBox="0 0 24 24"><path d="M17 1.01L7 1c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14z" fill="currentColor"/></svg>',
        web: '<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" fill="currentColor"/></svg>'
    };

    async function sync() {
        try {
            // Call our new simplified JSON API
            const r = await fetch(`/api/json/${USER_ID}`);
            const d = await r.json();
            if(!d.success) return;

            const u = d.data.identity;
            const p = d.data.profile;
            const s = d.data.status;
            const a = d.data.data.main_activity || { is_music:false }; 

            // 1. COLORS
            document.documentElement.style.setProperty('--acc', u.accent_color);
            document.getElementById('cardContainer').style.borderColor = u.accent_color;

            // 2. VISUALS
            document.getElementById('bg').style.backgroundImage = `url(${u.banner_url || u.avatar_url})`;
            document.getElementById('avatar').src = u.avatar_url;
            
            const deco = document.getElementById('deco');
            if(u.decoration) {
                deco.src = u.decoration;
                deco.style.display = 'block';
            }

            // 3. TEXT
            document.getElementById('name').textContent = u.display_name;
            document.getElementById('username').textContent = '@' + u.username;
            document.getElementById('bio').textContent = p.bio;

            // 4. BADGES
            const bHTML = p.badges.map(b => `<img src="${b.icon_url}" class="badge" title="${b.name}">`).join('');
            document.getElementById('badgeContainer').innerHTML = bHTML;

            // 5. PLATFORMS
            let platHTML = '';
            // Render active ones lit up
            ['desktop', 'mobile', 'web'].forEach(pk => {
                const isActive = s.active_on.includes(pk);
                if(isActive) {
                    platHTML += `<div class="plat-icon active">${PLATS[pk]}</div>`;
                }
            });
            document.getElementById('platContainer').innerHTML = platHTML;

            // 6. ACTIVITY
            if (a) {
                document.getElementById('actHead').textContent = a.header;
                document.getElementById('actTitle').textContent = a.title || "Idling";
                document.getElementById('actSub').textContent = a.description || "";
                
                const artUrl = (a.assets && a.assets.large_image) ? a.assets.large_image : 'https://cdn.discordapp.com/embed/avatars/0.png';
                document.getElementById('art').src = artUrl;
                
                // Progress
                const t = a.timestamps;
                if(t && t.is_seekable) {
                   document.getElementById('progBar').style.width = t.progress_percent + "%";
                } else {
                   document.getElementById('progBar').style.width = "0%";
                }
            }

            // 7. CONNECTIONS
            const cHTML = p.connections.map(c => `
                <a href="${c.url}" target="_blank" class="social-btn">
                    <img src="${c.icon}">
                </a>
            `).join('');
            document.getElementById('connContainer').innerHTML = cHTML;

        } catch(e) { console.error(e); }
    }

    setInterval(sync, 1500); // Polling every 1.5s
    sync();
</script>
</body>
</html>
"""

# =======================
#      ROUTING
# =======================

# 1. Raw JSON Data Endpoint
@app.route('/api/json/<uid>')
def get_json(uid):
    from app import build_titan_payload # Use the logic defined at top of file
    data = build_titan_payload(uid)
    return jsonify(data)

# 2. View Endpoint
@app.route('/view/<uid>')
@app.route('/<uid>') # Root fallback
def view_html(uid):
    # This route just returns the HTML template
    # The HTML then calls /api/json/<uid> to populate itself
    return render_template_string(HTML_TEMPLATE, key=uid)

@app.route('/')
def home():
    # Landing page demo
    return render_template_string(HTML_TEMPLATE, key="1173155162093785099")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
