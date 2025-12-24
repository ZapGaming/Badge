import base64
import requests
import os
import html
import re
import time
from flask import Flask, Response, request, render_template_string, jsonify

app = Flask(__name__)

# ===========================
#        CONFIGURATION
# ===========================
HEADERS = {'User-Agent': 'HyperBadge/Titan-v50'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# Platform Icons (SVG Paths)
PLAT_PATHS = {
    "desktop": "M4 4h16c1.1 0 2 .9 2 2v9c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2zm0 2v9h16V6H4zm8 14c-.55 0-1-.45-1-1v-1h2v1c0 .55-.45 1-1 1z",
    "mobile": "M17 1.01L7 1c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14z",
    "web": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"
}

# Connections Map
CONN_ICONS = {
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
    text = str(text).replace('\n', ' ')
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    text = re.sub(r'<a?:.+?:\d+>', '', text) # Remove discord emojis
    return html.escape(text, quote=True)

def get_base64(url, is_svg=False):
    if not url: return EMPTY
    try:
        if url.startswith("mp:"): url = f"https://media.discordapp.net/{url[3:]}"
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            mime = "image/svg+xml" if (is_svg or url.endswith(".svg")) else "image/png"
            return f"data:{mime};base64,{base64.b64encode(r.content).decode('utf-8')}"
    except: pass
    return EMPTY

def get_css(bg_anim, fg_anim):
    # CSS: Import Fonts
    css = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Outfit:wght@400;500;800;900&amp;family=Pacifico&amp;family=Poppins:wght@400;500;600&amp;display=swap');"
    
    keyframes = """
    @keyframes d { from{transform:scale(1.02) rotate(0deg)} to{transform:scale(1.05) rotate(0.5deg)} }
    @keyframes slide { 0%{transform:translateX(-15px);opacity:0} 100%{transform:translateX(0);opacity:1} }
    @keyframes pop { 0%{transform:scale(0); opacity:0} 100%{transform:scale(1); opacity:1} }
    @keyframes pulse { 0%{opacity:0.6} 50%{opacity:1} 100%{opacity:0.6} }
    @keyframes glint { 0% {transform:translateX(-200%)} 100% {transform:translateX(200%)} }
    @keyframes breathe { 0%{r:12px} 50%{r:16px} 100%{r:12px} }
    @keyframes floatY { 0%{transform:translateY(0)} 50%{transform:translateY(-4px)} }
    """
    
    classes = ""
    if str(bg_anim).lower() != 'false': 
        classes += ".bg-drift{animation:d 40s linear infinite alternate} .pulsing{animation:pulse 3s infinite} .shiny{animation:glint 6s infinite cubic-bezier(0.4, 0, 0.2, 1)}"
    if str(fg_anim).lower() != 'false': 
        classes += ".slide-in{animation:slide 0.8s ease-out} .badge-pop{animation:pop 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) backwards} .status-breathe{animation:breathe 3s infinite} .floater{animation:floatY 4s ease-in-out infinite}"
    return css + keyframes + classes

# ===========================
#      DATA LOGIC
# ===========================

def fetch_data(key, type_mode, args, for_html=False):
    try:
        force_name = args.get('name')

        # 1. SERVER MODE
        if type_mode == 'discord':
            r = requests.get(f"https://discord.com/api/v10/invites/{key}?with_counts=true", headers=HEADERS, timeout=4)
            d = r.json(); g = d.get('guild')
            if not g: return None
            # Server Mode returns simplified structure
            return {
                "type": "discord",
                "name": sanitize_xml(force_name or g['name']), 
                "title": f"{d.get('approximate_member_count', 0):,} Members",
                "color": "#5865F2", 
                "avatar": get_base64(f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png") if g.get('icon') else EMPTY
            }

        # 2. USER MODE
        else:
            dcdn_user = {}
            badges_list = []
            conn_list = [] # List of dicts for HTML, or list of B64 strings for SVG
            banner_url = None
            
            # A. Fetch DCDN
            try:
                r_p = requests.get(f"https://dcdn.dstn.to/profile/{key}", headers=HEADERS, timeout=3)
                if r_p.status_code == 200:
                    prof = r_p.json()
                    dcdn_user = prof.get('user', {})
                    banner_url = dcdn_user.get('banner')
                    # Badges
                    for b in prof.get('badges', []):
                         u_b = f"https://cdn.discordapp.com/badge-icons/{b['icon']}.png"
                         badges_list.append(u_b if for_html else get_base64(u_b))
                    # Connections
                    for c in prof.get('connected_accounts', []):
                         if c['type'] in CONN_ICONS:
                             u_c = f"{SIMPLE_ICONS_BASE}{CONN_ICONS[c['type']]}.svg"
                             # For HTML we keep raw url and metadata
                             if for_html: 
                                 conn_list.append({'type': c['type'], 'name': c['name'], 'src': u_c})
                             else: 
                                 # For SVG we limit to first 6 and get Base64
                                 if len(conn_list) < 6: 
                                     conn_list.append(get_base64(u_c, is_svg=True))
            except: pass

            # B. Fetch Lanyard
            r_l = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            if r_l.status_code != 200: return None
            lan_j = r_l.json()
            if not lan_j.get('success'): return None
            
            d = lan_j['data']
            u = d['discord_user']
            status = d['discord_status']
            
            # --- Platform Logic ---
            platforms = []
            if d.get('active_on_discord_desktop'): platforms.append("desktop")
            if d.get('active_on_discord_mobile'): platforms.append("mobile")
            if d.get('active_on_discord_web'): platforms.append("web")

            # --- Activity Logic ---
            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#ed4245", "offline": "#80848e", "spotify": "#1DB954"}
            
            main_act = None
            is_music = False
            
            # Spotify
            if d.get('spotify'):
                s = d['spotify']
                main_act = {"header": "LISTENING TO SPOTIFY", "title": s['song'], "detail": s['artist'], 
                            "image": s.get('album_art_url'), "color": cols['spotify'], "start": s['timestamps']['start'], "end": s['timestamps']['end']}
                is_music = True
            # RPC
            elif d.get('activities'):
                for act in d['activities']:
                    if act['type'] == 4: continue
                    img = None
                    if 'assets' in act and 'large_image' in act['assets']:
                         raw = act['assets']['large_image']
                         aid = act['application_id']
                         img = f"https://media.discordapp.net/{raw[3:]}" if raw.startswith("mp:") else f"https://cdn.discordapp.com/app-assets/{aid}/{raw}.png"
                    
                    head = "PLAYING" if act['type'] == 0 else "WATCHING"
                    main_act = {"header": f"{head} {act['name'].upper()}", "title": act.get('details', act['name']), "detail": act.get('state', ''), 
                                "image": img, "color": cols.get(status, "#5865F2"), "start": act.get('timestamps',{}).get('start',0), "end":0}
                    break
            
            if not main_act:
                main_act = {"header": "CURRENTLY", "title": args.get('idleMessage','Chilling'), "detail": status.title(), 
                            "image": None, "color": cols.get(status, "#555"), "start":0, "end":0}

            # Normalize Text & URLs
            display_name = force_name if force_name else (dcdn_user.get('global_name') or u['global_name'] or u['username'])
            u_avatar = f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png"
            final_bg = banner_url if banner_url else u_avatar

            if for_html:
                return {
                    "name": display_name, "uid": u['id'], "avatar": u_avatar, "banner": final_bg, "status_color": cols.get(status,"#555"),
                    "bio": dcdn_user.get('bio','No bio available.'),
                    "badges": badges_list, "connections": conn_list, "platforms": platforms,
                    "activity": {**main_act, "is_music": is_music}
                }
            else:
                return {
                    "type": "user",
                    "name": sanitize_xml(display_name),
                    "title": sanitize_xml(main_act['title']),
                    "detail": sanitize_xml(main_act['detail']),
                    "app_name": sanitize_xml(main_act['header']),
                    "color": main_act['color'],
                    "status_color": cols.get(status, "#555"),
                    "avatar": get_base64(u_avatar),
                    "banner_image": get_base64(final_bg),
                    "act_image": get_base64(main_act['image']) if main_act['image'] else None,
                    "bio": sanitize_xml(dcdn_user.get('bio','')),
                    "badges": badges_list,
                    "connections": conn_list,
                    "platforms": platforms, # List of strings ['mobile', 'desktop']
                    "sub_id": u['id'],
                    "is_music": is_music
                }
    except Exception as e:
        print(f"ERR: {e}")
        return None

# ===========================
#      SVG RENDERER
# ===========================

def render_svg(d, css, radius, bg_col):
    """Titan v50 SVG Engine: Safe from Collisions"""
    
    # 1. Background (Liquid Blur)
    bg_svg = f"""<rect width="100%" height="100%" fill="#{bg_col}" /><image href="{d['banner_image']}" width="100%" height="150%" y="-15%" preserveAspectRatio="xMidYMid slice" opacity="0.4" filter="url(#heavyBlur)" class="bg-drift"/><rect width="100%" height="100%" fill="url(#vig)"/>"""
    
    # 2. Activity Dock (Auto Layout)
    if d['act_image']:
        act_viz = f"""<image href="{d['act_image']}" x="25" y="195" width="80" height="80" rx="14" /><rect x="25" y="195" width="80" height="80" rx="14" fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="1"/>"""
        txt_pos = 130 # Shift text if image exists
    else:
        # Fallback Bolt Icon
        act_viz = f"""<rect x="25" y="195" width="80" height="80" rx="14" fill="rgba(255,255,255,0.05)"/><text x="65" y="245" text-anchor="middle" font-family="Outfit" font-size="28" fill="{d['color']}">⚡</text>"""
        txt_pos = 130

    # 3. Lists (Badges & Platforms)
    # Badges (Above name)
    b_svg = "".join([f'<image href="{b}" x="{i*28}" y="0" width="22" height="22" class="badge-pop" style="animation-delay:{i*0.05}s"/>' for i,b in enumerate(d.get('badges', []))])
    
    # Connections (Right Bottom of Dock)
    c_svg = "".join([f'<image href="{c}" x="{i*32}" y="0" width="22" height="22" filter="url(#invert)" opacity="0.7"/>' for i,c in enumerate(d.get('connections', []))])

    # Platforms (Top Right Icons)
    p_svg = ""
    px = 840
    for p in d.get('platforms', []):
        path = PLAT_PATHS.get(p, "")
        if path: p_svg += f'<path transform="translate({px},0)" d="{path}" fill="{d["status_color"]}" opacity="0.8"/><circle cx="{px+20}" cy="22" r="3" fill="{d["status_color"]}" />'; px -= 30

    return f"""<svg width="880" height="320" viewBox="0 0 880 320" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css}
          .t{{font-family:'Pacifico',cursive;text-shadow:0 4px 8px rgba(0,0,0,0.6)}} .h{{font-family:'Outfit',sans-serif;font-weight:800}}
          .s{{font-family:'Poppins',sans-serif;font-weight:500}} .m{{font-family:'JetBrains Mono',monospace}}</style>
        <clipPath id="cp"><rect width="880" height="320" rx="{radius}"/></clipPath><clipPath id="avc"><circle cx="75" cy="75" r="75"/></clipPath>
        <filter id="heavyBlur"><feGaussianBlur stdDeviation="60"/></filter><filter id="ds"><feDropShadow dx="0" dy="4" flood-opacity="0.6"/></filter>
        <filter id="invert"><feColorMatrix type="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 1 0"/></filter>
        <linearGradient id="vig" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="rgba(0,0,0,0.3)"/><stop offset="1" stop-color="#000" stop-opacity="0.95"/></linearGradient>
        <linearGradient id="glint" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stop-color="white" stop-opacity="0.04"/><stop offset="1" stop-color="white" stop-opacity="0"/></linearGradient>
      </defs>

      <g clip-path="url(#cp)">{bg_svg}
        <rect x="-400" width="200" height="320" fill="white" opacity="0.03" transform="skewX(-20)" class="shiny"/>
        <rect width="876" height="316" x="2" y="2" rx="{radius}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="2"/>
      </g>
      
      <!-- TOP LEFT PROFILE -->
      <g transform="translate(40,40)">
         <circle cx="75" cy="75" r="79" fill="#18181c"/><circle cx="75" cy="75" r="76" fill="none" stroke="{d['color']}" stroke-width="4" stroke-dasharray="20 12" class="pulsing"/>
         <g clip-path="url(#avc)"><image href="{d['avatar']}" width="150" height="150"/></g>
         <circle cx="125" cy="125" r="18" fill="#121212"/><circle cx="125" cy="125" r="13" fill="{d['status_color']}" class="status-breathe"/>
         
         <g transform="translate(180, 20)">
            <g transform="translate(0, -15)">{b_svg}</g>
            <text x="0" y="55" class="t" font-size="60" fill="white">{d['name']}</text>
            <text x="10" y="80" class="m" font-size="12" fill="#aaa" opacity="0.6">UID :: {d['sub_id']}</text>
            <!-- Truncated Bio -->
            <foreignObject x="5" y="90" width="600" height="50">
               <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:'Poppins';font-size:16px;color:#ddd;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{d['bio']}</div>
            </foreignObject>
         </g>
      </g>
      
      <!-- Top Right Platforms -->
      <g transform="translate(0, 30)">{p_svg}</g>
      
      <!-- BOTTOM DOCK -->
      <g transform="translate(20, 195)" class="slide-in">
          <rect width="840" height="110" rx="20" fill="rgba(20,20,25,0.7)" stroke="{d['color']}" stroke-opacity="0.3" stroke-width="2"/>
          <rect width="840" height="110" rx="20" fill="url(#glint)"/>
          {act_viz}
          
          <g transform="translate({txt_pos}, 28)">
              <text x="0" y="0" class="m" font-size="11" fill="{d['color']}" letter-spacing="1.5" font-weight="bold">{d['app_name']}</text>
              <text x="0" y="32" class="h" font-size="26" fill="white" filter="url(#ds)">{d['title'][:32]}</text>
              <text x="0" y="56" class="s" font-size="15" fill="#BBB">{d['detail'][:45]}</text>
              
              <!-- Connection Icons Right Aligned in Dock -->
              <g transform="translate(500, 20)">{c_svg}</g>
          </g>
      </g>
    </svg>"""

# ===========================
#      LIVE HTML (Islands)
# ===========================

def render_live_html(key, args):
    """
    HTML Mode: Floating Islands Layout
    3 Separate Divs: Profile, Activity, Status
    """
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@500;700&family=Pacifico&family=JetBrains+Mono&display=swap" rel="stylesheet">
        <style>
            :root {{ --acc: #5865F2; --stat: #555; }}
            * {{ margin:0; box-sizing:border-box; }}
            body {{ background:#050508; color:white; font-family:'Outfit'; height:100vh; display:flex; justify-content:center; align-items:center; overflow:hidden; }}
            .ambient {{ position:fixed; inset:0; background-size:cover; filter:blur(100px) opacity(0.3); z-index:-1; transition:0.5s; }}
            
            /* The Layout Container */
            .layout {{ position:relative; width:900px; height:350px; display:grid; grid-template-columns: 260px 1fr; grid-template-rows: auto 1fr; gap:20px; }}

            /* Base Glass Style */
            .glass {{ background:rgba(20,20,25,0.4); border:1px solid rgba(255,255,255,0.08); backdrop-filter:blur(30px); border-radius:30px; box-shadow:0 15px 50px rgba(0,0,0,0.3); overflow:hidden; transition:transform 0.2s; position:relative; }}
            .glass:hover {{ transform:translateY(-2px); border-color:var(--acc); }}
            
            /* 1. Identity Island (Left Tall) */
            .island-id {{ grid-row: 1 / 3; display:flex; flex-direction:column; align-items:center; padding:30px; text-align:center; }}
            .av-ring {{ width:140px; height:140px; border-radius:50%; border:3px dashed var(--acc); display:flex; justify-content:center; align-items:center; animation:spin 20s linear infinite; margin-bottom:15px; opacity:0.7; }}
            .av-img {{ width:120px; height:120px; border-radius:50%; position:absolute; top:40px; border:4px solid #18181c; }}
            .id-name {{ font-family:'Pacifico'; font-size:38px; line-height:1.2; text-shadow:0 2px 10px rgba(0,0,0,0.5); }}
            .id-bio {{ color:#999; font-size:14px; margin-top:10px; line-height:1.4; }}
            .badges {{ margin-top:15px; display:flex; gap:8px; justify-content:center; flex-wrap:wrap; }}
            .badge-icon {{ width:24px; }}
            
            /* 2. Status Island (Top Right) */
            .island-stat {{ height:100px; display:flex; align-items:center; padding:0 30px; justify-content:space-between; }}
            .status-text {{ font-size:30px; font-weight:700; color:white; }}
            .status-sub {{ font-family:'JetBrains Mono'; font-size:12px; color:var(--acc); letter-spacing:2px; text-transform:uppercase; }}
            .plat-row {{ display:flex; gap:10px; }}
            .plat-icon {{ width:24px; height:24px; filter:grayscale(1); opacity:0.5; }}
            .plat-icon.active {{ filter:none; opacity:1; fill:var(--stat); }}

            /* 3. Activity Island (Bottom Right) */
            .island-act {{ display:flex; align-items:center; padding:25px; gap:25px; }}
            .act-art {{ width:100px; height:100px; border-radius:15px; object-fit:cover; box-shadow:0 5px 20px rgba(0,0,0,0.5); flex-shrink:0; transition:0.3s; }}
            .spinning {{ border-radius:50%; animation: spin 4s linear infinite; }}
            .act-info {{ flex:1; min-width:0; display:flex; flex-direction:column; justify-content:center; }}
            .prog-wrap {{ margin-top:15px; height:4px; background:rgba(255,255,255,0.1); border-radius:2px; position:relative; overflow:hidden; }}
            .prog-fill {{ height:100%; width:0%; background:var(--acc); }}
            .act-head {{ font-size:10px; font-weight:bold; color:var(--acc); letter-spacing:1px; margin-bottom:4px; }}
            .act-tit {{ font-size:26px; font-weight:bold; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
            .conns {{ position:absolute; bottom:25px; right:25px; display:flex; gap:10px; }}
            .c-icon {{ width:22px; filter:invert(1); opacity:0.5; transition:0.2s; }}
            .c-icon:hover {{ opacity:1; transform:scale(1.2); }}

            @keyframes spin {{ to{{transform:rotate(360deg)}} }}
        </style>
    </head>
    <body>
        <div class="ambient" id="bg"></div>
        <div class="layout">
            <!-- ID PANEL -->
            <div class="glass island-id">
                <div class="av-ring"></div>
                <img id="avatar" class="av-img">
                <div style="height:140px"></div>
                <div class="id-name" id="name">...</div>
                <div class="badges" id="badgeRow"></div>
                <div class="id-bio" id="bio"></div>
            </div>
            
            <!-- STATUS PANEL -->
            <div class="glass island-stat">
                <div>
                    <div class="status-sub" id="statSub">CURRENTLY</div>
                    <div class="status-text" id="statTxt">Offline</div>
                </div>
                <div class="plat-row" id="plats"></div>
            </div>

            <!-- ACTIVITY PANEL -->
            <div class="glass island-act">
                <img id="art" class="act-art">
                <div class="act-info">
                    <div class="act-head" id="actHead">ACTIVITY</div>
                    <div class="act-tit" id="track">No Signal</div>
                    <div style="color:#aaa" id="detail">...</div>
                    <div class="prog-wrap"><div class="prog-fill" id="bar"></div></div>
                </div>
                <div class="conns" id="connRow"></div>
            </div>
        </div>

        <script>
            const UID = "{key}";
            async function loop() {{
                try {{
                    const r = await fetch(`/api/data/${{UID}}`);
                    const d = await r.json();
                    if(!d) return;

                    // Props
                    document.documentElement.style.setProperty('--acc', d.color);
                    document.documentElement.style.setProperty('--stat', d.status_color);
                    document.getElementById('bg').style.backgroundImage = `url(${{d.banner || d.avatar}})`;
                    
                    // Identity
                    document.getElementById('avatar').src = d.avatar;
                    document.getElementById('name').innerText = d.name;
                    document.getElementById('bio').innerText = d.bio;
                    document.getElementById('badgeRow').innerHTML = d.badges.map(s => `<img src="${{s}}" class="badge-icon">`).join('');
                    
                    // Status
                    document.getElementById('statTxt').innerText = d.status_color === '#80848e' ? 'Offline' : 'Online';
                    document.getElementById('plats').innerHTML = 
                       (d.platforms.includes('desktop') ? '<svg class="plat-icon active" viewBox="0 0 24 24"><path d="M4 4h16c1.1 0 2 .9 2 2v9c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2zm0 2v9h16V6H4zm8 14c-.55 0-1-.45-1-1v-1h2v1c0 .55-.45 1-1 1z"/></svg>' : '') + 
                       (d.platforms.includes('mobile') ? '<svg class="plat-icon active" viewBox="0 0 24 24"><path d="M17 1.01L7 1c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14z"/></svg>' : '');

                    // Activity
                    const a = d.activity;
                    document.getElementById('actHead').innerText = a.header;
                    document.getElementById('track').innerText = a.title;
                    document.getElementById('detail').innerText = a.detail;
                    
                    const art = document.getElementById('art');
                    if(a.image) {{ art.src = a.image; art.style.display='block'; }} else {{ art.style.display='none'; }}
                    art.className = a.is_music ? "act-art spinning" : "act-art";

                    // Bar
                    if(a.is_music && a.end) {{
                         const pct = Math.min(((Date.now() - a.start) / (a.end - a.start))*100, 100);
                         document.getElementById('bar').style.width = pct + "%";
                    }} else {{ document.getElementById('bar').style.width = "0%"; }}

                    // Connections
                    document.getElementById('connRow').innerHTML = d.connections.map(c => `<a href="#"><img src="${{c.src}}" class="c-icon"></a>`).join('');

                }} catch(e) {{}}
            }}
            setInterval(loop, 1000);
            loop();
        </script>
    </body>
    </html>
    """

# ===========================
#      CONTROLLERS
# ===========================

@app.route('/api/data/<key>')
def api(key):
    # Endpoint for HTML polling
    data = fetch_data(key, 'user', request.args, for_html=True)
    return jsonify(data)

@app.route('/superbadge/<key>')
def handler(key):
    args = request.args
    # Detect HTML Mode request
    if args.get('mode') == 'html':
        return render_live_html(key, args)
    
    # SVG Mode (GitHub)
    type_mode = 'user' if (key.isdigit() and len(str(key)) > 15) else 'discord'
    data = fetch_data(key, type_mode, args, for_html=False)
    
    if not data: return Response('<svg><text>Error</text></svg>', mimetype='image/svg+xml')

    bg_an = args.get('bgAnimations', 'true')
    fg_an = args.get('fgAnimations', 'true')
    bg_col = args.get('bg', '0f0f12').replace('#','')
    radius = args.get('borderRadius', '30').replace('px', '') 

    css = get_css(bg_an, fg_an)
    
    if data.get('type') == 'discord': # Simple Server Card
        svg = f"""<svg width="400" height="100" xmlns="http://www.w3.org/2000/svg"><defs><style>{css}</style></defs><rect width="100%" height="100%" rx="{radius}" fill="#{bg_col}"/><image href="{data['avatar']}" width="70" height="70" x="15" y="15" rx="10"/><text x="100" y="40" font-family="Outfit" fill="white" font-size="20">{data['name']}</text><text x="100" y="70" font-family="JetBrains Mono" fill="#5865F2">{data['title']}</text></svg>"""
    else: # Mega User Card
        svg = render_mega_profile(data, css, radius, bg_col)
    
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
