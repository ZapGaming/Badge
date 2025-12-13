# ⚡ Chillax HyperBadge

<div align="center">

<!-- REPLACE 'your-app-name' WITH YOUR ACTUAL RENDER APP NAME BELOW -->
<a href="https://github.com/warrayquipsome">
  <img src="https://badge-oq5l.onrender.com/superbadge/1173155162093785099?style=chillax&roastMode=false&idleMessage=Coding&fgAnimations=false&aifeatures=false" alt="HyperBadge" height="150"/>
</a>

<p align="center">
  <b>The Next-Gen Status Generator for GitHub Profiles</b><br>
  <i>Powered by Flask, Lanyard, Discord, and Google Gemini AI.</i>
</p>

</div>

---

## 🎨 Overview

HyperBadge is a high-performance Python application that generates **real-time, animated SVG badges** for your GitHub `README.md`.

It tracks your **Discord Activity** (Games, Spotify, Coding) or **GitHub Stats** and uses **Neural AI** to generate sci-fi HUD updates, music analysis, or savage roasts based on your current status.

---

## 🚀 Quick Usage

### 1. The Magic Link (Auto-Detect)
Replace `YOUR_ID` with your **Discord User ID**, **Server Invite**, or **GitHub Username**.

```markdown
![Status](https://badge-oq5l.onrender.com/superbadge/YOUR_ID)
```

### 2. Specific Modes

| Mode | Input | Example Link |
| :--- | :--- | :--- |
| **Discord User** | `User ID` | `.../badge/user/1173155...` |
| **Discord Server** | `Invite Code` | `.../badge/discord/DrfX6286kF` |
| **GitHub Profile** | `Username` | `.../badge/github/warrayquipsome` |

---

## 🎨 Style Gallery

Customize the look by adding `?style=NAME` to the URL.

| Style Name | Description | Visual Vibe |
| :--- | :--- | :--- |
| **`chillax`** | **(New)** Replicates the custom Vencord/BetterDiscord translucent client aesthetic. | Glass, Aurora, Script Fonts |
| **`hyper`** | **(Default)** Advanced GLSL liquid shader background. Supports Spotify Album Art blur. | Neon, Liquid, Deep Space |
| **`spotify`** | Dedicated music player card with album art and a real-time progress bar. | Clean, Music-Focused |
| **`easteregg`** | "macOS 26" futuristic aesthetic. Floating islands and RGB flow borders. | Fluid OS, Apple, 3D |
| **`terminal`** | Retro CRT Monitor with scanlines, Vim status bar, and syntax highlighting. | Hacker, Dev, Matrix |
| **`cute`** | Pastel colors, scrolling heart patterns, bouncing animations, and kawaii UI. | Soft, Anime, Pink/White |
| **`pro`** | Static, high-contrast, clean business card. Perfect for emails. | Professional, Minimal |

**Example:**
```markdown
![](https://badge-oq5l.onrender.com/superbadge/YOUR_ID?style=chillax&bg=18191c)
```

---

## 🎛️ Customization & Parameters

Tailor the badge to your needs by adding query parameters:

### 🎭 Visuals
| Param | Values | Default | Description |
| :--- | :--- | :--- | :--- |
| `bg` | Hex Code | `09090b` | Custom background color (exclude the `#`). |
| `borderRadius` | Pixels | `20` | Corner roundness (e.g. `20` or `0` for sharp). |
| `showDisplayName` | `true/false` | `true` | Use your Global Display Name instead of Username. |

### 🤖 AI & Logic
| Param | Values | Description |
| :--- | :--- | :--- |
| `roastMode` | `true` | Changes AI personality from "System OS" to "Savage Troll". |
| `idleMessage` | Text | Custom text to show when offline (e.g. "SLEEPING"). |
| `aifeatures` | `false` | **Hide AI:** Removes the AI text/box entirely from the badge. |

### ⚡ Performance & Animation
| Param | Values | Description |
| :--- | :--- | :--- |
| `animations` | `false` | **Master Switch:** Turns off ALL movement. |
| `bgAnimations` | `false` | Disables background fluids/meshes, keeps UI floating. |
| `fgAnimations` | `false` | Disables UI floating/bobbing, keeps background alive. |

---

## 🛠️ Deployment (Self-Hosting)

You can host this for free on **Render.com**.

1.  **Clone** this repository.
2.  Go to **Render Dashboard** -> New **Web Service**.
3.  Connect your repo.
4.  **Settings:**
    *   **Runtime:** Python 3
    *   **Build Command:** `pip install -r requirements.txt`
    *   **Start Command:** `gunicorn app:app`
5.  **Environment Variables:**
    *   Key: `GEMINI_API_KEY`
    *   Value: *(Your Google AI Studio Key)*

---

### ⚠️ Important: Lanyard Setup
To display **User Activity** (Games, Music, VS Code), you must be a member of the Lanyard Discord Server. This is required for the API to see you.

1.  Join here: [discord.gg/lanyard](https://discord.gg/lanyard)
2.  Wait ~5 minutes for caching.
3.  The badge will switch from "UNKNOWN" to your status automatically.

---

<div align="center">
  <sub><b>Chillax Development</b> // Built by WQ</sub>
</div>
