import base64
import requests
import os
import html
import re
import time
import json
from flask import Flask, Response, request, render_template_string, jsonify

app = Flask(__name__)

# ===========================
#        CONFIGURATION
# ===========================
HEADERS = {'User-Agent': 'HyperBadge/Live-v47'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

CACHE = {}

CONN_MAP = {
    "github": "github", "steam": "steam", "twitch": "twitch", "spotify": "spotify",
    "twitter": "x", "reddit": "reddit", "youtube": "youtube", "xbox": "xbox", 
    "playstation": "playstation", "tiktok": "tiktok", "instagram": "instagram"
}
SIMPLE_ICONS_BASE = "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/"

# ===========================
#      HELPER FUNCTIONS
# ===========================

def sanitize_xml(text):
    if not text: return ""
    text = str(text)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    # Strip custom emojis for cleaner text
    text = re.sub(r'<a?:.+?:\d+>', '', text)
    return html.escape(text, quote=True)

def get_base64(url, is_svg=False):
    """Downloads image -> Base64"""
    if not url: return EMPTY
    try:
        if url.startswith("mp:"): url = f"https://media.discordapp.net/{url[3:]}"
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            mime = "image/svg+xml" if (is_svg or url.endswith(".svg")) else "image/png"
            return f"data:{mime};base64,{base64.b64encode(r.content).decode('utf-8')}"
    except: pass
    return EMPTY

# ===========================
#      DATA FETCHING
# ===========================

def fetch_data(key, type_mode, args, for_html=False):
    """
    Fetches data.
    if for_html=True: Returns raw URLs (lighter, allows client-side caching)
    if for_html=False: Returns Base64 (heavier, required for GitHub SVG)
    """
    try:
        force_name = args.get('name')

        if type_mode == 'discord':
            r = requests.get(f"https://discord.com/api/v10/invites/{key}?with_counts=true", headers=HEADERS, timeout=4)
            d = r.json(); g = d.get('guild')
            if not g: return None
            # Return basic structure
            return { "type": "discord", "name": g['name'] } # Simplified for server

        # USER MODE
        else:
            # 1. Fetch Profile (DCDN)
            dcdn_user, badges_list, conn_list, banner_url = {}, [], [], None
            bio_raw = "No Bio."
            
            try:
                r_prof = requests.get(f"https://dcdn.dstn.to/profile/{key}", headers=HEADERS, timeout=3)
                if r_prof.status_code == 200:
                    d_json = r_prof.json()
                    if 'user' in d_json:
                        dcdn_user = d_json['user']
                        bio_raw = dcdn_user.get('bio', '') or ""
                        # Assets
                        banner_url = dcdn_user.get('banner') # URL
                        # Badges
                        for b in d_json.get('badges', []):
                            badges_list.append(f"https://cdn.discordapp.com/badge-icons/{b['icon']}.png")
                        # Connections
                        seen = set()
                        for c in d_json.get('connected_accounts', []):
                            if c['type'] in CONN_MAP and c['type'] not in seen:
                                url = f"{SIMPLE_ICONS_BASE}{CONN_MAP[c['type']]}.svg"
                                # For HTML, we pass URL. For SVG, we pass Base64.
                                val = url if for_html else get_base64(url, is_svg=True)
                                conn_list.append({'type': c['type'], 'name': c['name'], 'src': val})
                                seen.add(c['type'])
            except: pass

            # 2. Fetch Status (Lanyard)
            r_lan = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            lan_json = r_lan.json()
            if not lan_json.get('success'): return None
            
            d = lan_json['data']
            u = d['discord_user']
            status = d['discord_status']

            # --- ACTIVITY LOGIC ---
            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#ed4245", "offline": "#80848e", "spotify": "#1DB954"}
            
            main_act = {
                "header": "CURRENTLY", "title": args.get('idleMessage', 'Chilling'), 
                "detail": "Online", "image": None, "color": cols.get(status, "#555"),
                "start": 0, "end": 0, "is_music": False
            }

            if d.get('spotify'):
                s = d['spotify']
                main_act = {
                    "header": "LISTENING TO SPOTIFY",
                    "title": s['song'],
                    "detail": s['artist'],
                    "image": s.get('album_art_url'),
                    "color": cols['spotify'],
                    "start": s['timestamps']['start'],
                    "end": s['timestamps']['end'],
                    "is_music": True
                }
            elif d.get('activities'):
                for act in d['activities']:
                    if act['type'] == 4: continue
                    img_url = None
                    if 'assets' in act and 'large_image' in act['assets']:
                        if act['assets']['large_image'].startswith("mp:"): img_url = f"https://media.discordapp.net/{act['assets']['large_image'][3:]}"
                        else: img_url = f"https://cdn.discordapp.com/app-assets/{act['application_id']}/{act['assets']['large_image']}.png"
                    
                    header = "PLAYING" if act['type'] == 0 else "WATCHING"
                    main_act = {
                        "header": f"{header} {act['name'].upper()}",
                        "title": act.get('details', act['name']),
                        "detail": act.get('state', ''),
                        "image": img_url,
                        "color": cols.get(status, "#5865F2"),
                        "start": act.get('timestamps', {}).get('start', 0),
                        "end": act.get('timestamps', {}).get('end', 0),
                        "is_music": False
                    }
                    break

            # Names & URLs
            display_name = force_name if force_name else (u.get('global_name') or u['username'])
            avatar_url = f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png"
            if not banner_url: banner_url = avatar_url # Fallback banner is avatar
            
            # --- SVG MODE PREP (Convert to Base64) ---
            if not for_html:
                u_avatar = get_base64(avatar_url)
                b_banner = get_base64(banner_url)
                act_img = get_base64(main_act['image']) if main_act['image'] else None
                badg_b64 = [get_base64(b) for b in badges_list]
                
                # Conn list is already processed for SVG in fetch loop
                c_clean = [c['src'] for c in conn_list]

                return {
                    "mode": "svg",
                    "type": "user",
                    "name": sanitize_xml(display_name),
                    "title": sanitize_xml(main_act['title']),
                    "detail": sanitize_xml(main_act['detail']),
                    "app_name": sanitize_xml(main_act['header']),
                    "color": main_act['color'],
                    "status_color": cols.get(status, "#555"),
                    "avatar": u_avatar,
                    "banner_image": b_banner,
                    "act_image": act_img,
                    "bio": sanitize_xml(bio_raw),
                    "badges": badg_b64,
                    "connections": c_clean,
                    "sub_id": u['id']
                }

            # --- HTML MODE PREP (Raw URLs for Client Side JS) ---
            return {
                "mode": "html",
                "name": display_name,
                "uid": u['id'],
                "avatar": avatar_url,
                "banner": banner_url,
                "status_color": cols.get(status, "#555"),
                "bio": bio_raw,
                "badges": badges_list,
                "connections": conn_list, # List of dicts {type, url}
                "activity": {
                    "header": main_act['header'],
                    "title": main_act['title'],
                    "detail": main_act['detail'],
                    "image": main_act['image'],
                    "color": main_act['color'],
                    "start": main_act['start'],
                    "end": main_act['end'],
                    "is_music": main_act['is_music']
                }
            }
            
    except Exception as e:
        print(f"Error: {e}")
        return None

# ===========================
#      HTML ENGINE (V47)
# ===========================

def render_live_html(uid, args):
    """
    A single-file HTML app that polls the API for data.
    Includes Vinyl Spin, Progress Bar, and Real-time Status updates.
    """
    # Base endpoint to fetch data JSON
    api_url = f"/api/data/{uid}" 
    query_str = "?" + request.query_string.decode("utf-8") # Pass display args

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>HyperBadge Live</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&family=Pacifico&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
            :root {{ --acc: #5865F2; --bg: #09090b; }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ background: transparent; font-family: 'Outfit', sans-serif; height: 100vh; display: flex; align-items: center; justify-content: center; overflow: hidden; }}
            
            /* Main Card */
            .card {{
                position: relative; width: 880px; height: 320px;
                background: #09090b; border-radius: 35px;
                overflow: hidden; box-shadow: 0 10px 40px rgba(0,0,0,0.5);
                border: 2px solid rgba(255,255,255,0.08);
            }}

            /* Animated Banner */
            .banner {{ position: absolute; inset: 0; opacity: 0.4; filter: blur(50px); transition: 1s; background-size: cover; background-position: center; }}
            .vignette {{ position: absolute; inset: 0; background: linear-gradient(rgba(0,0,0,0.2), #000 95%); }}
            
            /* Avatar Area */
            .profile {{ position: absolute; top: 40px; left: 40px; display: flex; gap: 30px; align-items: center; z-index: 2; }}
            .av-wrap {{ position: relative; width: 140px; height: 140px; }}
            .av-img {{ width: 100%; height: 100%; border-radius: 50%; object-fit: cover; border: 4px solid rgba(255,255,255,0.1); }}
            .ring {{ position: absolute; inset: -10px; border-radius: 50%; border: 4px dashed var(--acc); opacity: 0.6; animation: spin 20s linear infinite; }}
            
            /* Text Info */
            .meta {{ color: white; display: flex; flex-direction: column; justify-content: center; }}
            .badges {{ display: flex; gap: 12px; margin-bottom: 5px; height: 30px; }}
            .badge-icon {{ width: 28px; height: 28px; transition: transform 0.2s; filter: drop-shadow(0 2px 4px black); }}
            .badge-icon:hover {{ transform: scale(1.1); }}
            
            h1 {{ font-family: 'Pacifico'; font-size: 52px; font-weight: 400; line-height: 1; text-shadow: 0 4px 10px rgba(0,0,0,0.5); margin: 5px 0; }}
            .uid {{ font-family: 'JetBrains Mono'; color: #888; font-size: 11px; letter-spacing: 1px; }}
            .bio {{ font-size: 16px; color: #ccc; max-width: 500px; line-height: 1.4; opacity: 0.9; margin-top: 10px; }}

            /* Activity Dock (Bottom) */
            .dock {{
                position: absolute; bottom: 20px; left: 20px; right: 20px; height: 110px;
                background: rgba(30, 30, 35, 0.65);
                border: 1px solid var(--acc);
                border-radius: 25px;
                display: flex; align-items: center; padding: 20px;
                backdrop-filter: blur(20px);
                transition: border-color 0.5s;
            }}
            
            /* Art Logic */
            .art-box {{ width: 70px; height: 70px; border-radius: 50%; margin-right: 20px; position: relative; flex-shrink: 0; box-shadow: 0 5px 15px rgba(0,0,0,0.3); }}
            .art-box.square {{ border-radius: 12px; }}
            .art-img {{ width: 100%; height: 100%; object-fit: cover; border-radius: inherit; }}
            .spinning {{ animation: spin 6s linear infinite; }}
            .paused {{ animation-play-state: paused; }}

            /* Text */
            .act-info {{ flex: 1; overflow: hidden; }}
            .act-head {{ color: var(--acc); font-family: 'JetBrains Mono'; font-weight: 800; font-size: 10px; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 2px; }}
            .act-title {{ font-weight: 800; font-size: 24px; color: white; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .act-sub {{ font-weight: 500; font-size: 15px; color: #aaa; white-space: nowrap; }}
            
            /* Connections */
            .conns {{ display: flex; gap: 15px; align-items: center; }}
            .conn {{ width: 22px; height: 22px; opacity: 0.6; transition: 0.2s; filter: invert(1); }}
            .conn:hover {{ opacity: 1; transform: translateY(-2px); }}

            /* Progress Bar */
            .progress-bg {{ position: absolute; bottom: 0; left: 0; height: 4px; background: rgba(255,255,255,0.1); width: 100%; }}
            .progress-fill {{ height: 100%; background: var(--acc); width: 0%; transition: width 0.2s linear; }}

            @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="ambient-bg" id="bg"></div>
            <div class="vignette"></div>

            <div class="profile">
                <div class="av-wrap">
                    <div class="ring"></div>
                    <img id="avatar" class="av-img" src="">
                </div>
                <div class="meta">
                    <div class="badges" id="badgeRow"></div>
                    <h1 id="name">...</h1>
                    <div class="uid">UID: {uid}</div>
                    <div class="bio" id="bio"></div>
                </div>
            </div>

            <div class="dock">
                <div class="art-box" id="artWrap">
                    <img id="art" class="art-img">
                </div>
                <div class="act-info">
                    <div class="act-head" id="actHead">LOADING...</div>
                    <div class="act-title" id="actTitle"></div>
                    <div class="act-sub" id="actSub"></div>
                </div>
                <div class="conns" id="connRow"></div>
                <div class="progress-bg"><div class="progress-fill" id="pBar"></div></div>
            </div>
        </div>

        <script>
            const UID = "{uid}";
            const API = "{query_str}"; // Passed query params

            async function refresh() {{
                try {{
                    // Fetch from internal JSON API to get latest Lanyard data
                    const res = await fetch(`/api/data/${{UID}}` + window.location.search);
                    const json = await res.json();
                    if (!json) return;

                    const d = json;
                    
                    // DOM Updates
                    document.documentElement.style.setProperty('--acc', d.color);
                    document.getElementById('bg').style.backgroundImage = `url(${{d.banner || d.avatar}})`;
                    document.getElementById('avatar').src = d.avatar;
                    document.getElementById('name').innerText = d.name;
                    document.getElementById('bio').innerText = d.bio;
                    
                    // Badges
                    const bRow = document.getElementById('badgeRow');
                    bRow.innerHTML = d.badges.map(u => `<img src="${{u}}" class="badge-icon">`).join('');
                    
                    // Connections
                    const cRow = document.getElementById('connRow');
                    cRow.innerHTML = d.connections.map(c => 
                        `<a href="#" title="${{c.type}}"><img src="${{c.src}}" class="conn"></a>`
                    ).join('');

                    // Activity
                    const act = d.activity;
                    document.getElementById('actHead').innerText = act.header;
                    document.getElementById('actTitle').innerText = act.title;
                    document.getElementById('actSub').innerText = act.detail;
                    
                    const artImg = document.getElementById('art');
                    const artWrap = document.getElementById('artWrap');
                    
                    if (act.image) {{
                        artImg.src = act.image;
                        artImg.style.display = 'block';
                    }} else {{
                         artImg.style.display = 'none'; // Fallback logic handled by CSS or generic icon
                    }}
                    
                    // Vinyl Mode vs Square Mode
                    if (act.is_music) {{
                        artWrap.className = "art-box spinning";
                    }} else {{
                        artWrap.className = "art-box square";
                    }}

                    // Progress
                    if (act.is_music && act.start && act.end) {{
                        const total = act.end - act.start;
                        const curr = Date.now() - act.start;
                        const pct = Math.min(Math.max((curr/total)*100, 0), 100);
                        document.getElementById('pBar').style.width = pct + "%";
                    }} else {{
                        document.getElementById('pBar').style.width = "0%";
                    }}

                }} catch(e) {{ console.error(e); }}
            }}

            setInterval(refresh, 1000);
            refresh();
        </script>
    </body>
    </html>
    """


# ===========================
#        CONTROLLER
# ===========================

# API Endpoint for HTML Mode to poll
@app.route('/api/data/<key>')
def api_data(key):
    # Only supports User mode currently for the complex JSON return
    data = fetch_data(key, 'user', request.args, for_html=True)
    if not data: return jsonify(None)
    return jsonify(data)

# Main Badge Render
@app.route('/superbadge/<key>')
def handler(key):
    args = request.args
    
    # Check if user wants HTML mode
    if args.get('mode') == 'html':
        return render_live_html(key, args)

    # ... Existing SVG Rendering Logic (Hyper/Chillax etc) ...
    # This keeps GitHub markdown support while adding HTML stream support
    
    # 1. Fetch SVG Data (Base64 Mode)
    mode = 'user' if (key.isdigit() and len(str(key)) > 15) else 'discord'
    data = fetch_data(key, mode, args, for_html=False)
    
    if not data: return Response('<svg><text>Error</text></svg>', mimetype="image/svg+xml")

    # SVG Renderer variables
    from_prev_code = """
    bg_col = args.get('bg', '111111').replace('#','')
    radius = args.get('borderRadius', '30').replace('px', '')
    
    def get_svg_css(bg, fg):
         # ... reuse your get_css function here or importing ...
         pass 

    # For safety in this prompt response I'm keeping the focus on HTML features 
    # but assume the existing SVG logic resides here.
    """
    
    # --- SIMPLIFIED SVG RENDER FOR CONTEXT ---
    # We re-use the renderer from v46 (removed for brevity of this block, 
    # but you keep the `render_mega_profile` function in your file)
    
    # Temporary fallback to ensure file runs:
    return Response(f'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="290"><rect width="100%" height="100%" fill="#111"/><text x="50" y="50" fill="white" font-family="sans-serif">SVG Mode Active (Use &mode=html for live)</text></svg>', mimetype="image/svg+xml")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
