# ⚡ Zandy HyperBadge

<div align="center">

<!-- REPLACE 'your-app-name' WITH YOUR ACTUAL RENDER APP NAME BELOW -->
<a href="https://github.com/zapgaming">
  <img src="https://badge-oq5l.onrender.com/superbadge/1173155162093785099?style=chillax&roastMode=false&idleMessage=VIBING&fgAnimations=false&aifeatures=false" alt="HyperBadge" height="150"/>
</a>

<p align="center">
  <b>The All-In-One Dynamic Status Generator</b><br>
  <i>Universal Badge System for Discord Users, Servers, and GitHub Profiles.</i><br>
  Powered by Flask, Lanyard, and Google Gemini AI.
</p>

</div>

---

## 🚀 Overview

HyperBadge is a high-performance Python application that generates **real-time, animated SVG badges** for your GitHub `README.md`.

It serves as a single endpoint for all your status needs:
1.  **Discord User:** Live Activity (Games, Spotify, Coding) with AI status commentary.
2.  **Discord Server:** Live Member counts and Online counts (sanitized and crash-proof).
3.  **GitHub:** Repo Statistics (Star/Fork ranking) or User Profile stats. (not working atm)

### ✨ Features
*   **🎨 7 Visual Engines:** `Chillax`, `Hyper`, `Spotify`, `EasterEgg`, `Cute`, `Terminal`, `Professional`.
*   **🎵 Deep Spotify:** Card backgrounds morph into blurred Album Art when music plays.
*   **🧠 Neural Core:** Gemini AI generates sci-fi HUD text or "roasts" your activity in real-time.
*   **🛡️ Robust Parsing:** Auto-sanitizes Emojis and special characters to prevent XML breaking.
*   **⚡ Performance Controls:** Granular toggles for background vs. foreground animations.

---

## 🛠️ Usage Guide

**Base URL:** `https://badge-oq5l.onrender.com` (main)

### 1. The Magic Link (Auto-Detect)
The system automatically detects if you are asking for a User, a Server, or a Repo.

```markdown
![Status](https://badge-oq5l.onrender.com/superbadge/INPUT_HERE)
```

| Input Type | Format | Example |
| :--- | :--- | :--- |
| **Discord User** | `User ID` | `.../superbadge/1173155...` |
| **Discord Server** | `Invite Code` | `.../superbadge/DrfX6286kF` |
| **GitHub User** (not working atm) | `Username` | `.../superbadge/torvalds` |
| **GitHub Repo** (not working atm) | `User/Repo` | `.../superbadge/torvalds/linux` |

---

## 🎨 Style Gallery

Change the look by adding `?style=NAME` to the URL.

| Style | Description | Vibe |
| :--- | :--- | :--- |
| **`chillax`** | **(New)** Translucent Glass overlay, aurora wallpaper, script font header. Matches Vencord/BetterDiscord. | Aesthetic, Soft, Glass |
| **`hyper`** | **(Default)** Liquid GLSL shaders. Displays full Album Art as background when listening to Spotify. | Neon, Liquid, Deep |
| **`spotify`** | Dedicated music player card with a real-time moving progress bar. | Music-Focused, Clean |
| **`easteregg`** | Futuristic "macOS" design. Floating 3D islands and RGB flow borders. | Fluid OS, Apple |
| **`terminal`** | Retro CRT Monitor with scanlines, Vim status bar, and syntax highlighting. | Hacker, Dev, Matrix |
| **`cute`** | Pastel colors, scrolling patterns, bouncing animations, and kawaii UI. | Anime, Pink/White |
| **`pro`** | Static, clean business card style. Perfect for email signatures (Outlook friendly). | Corporate, Minimal |

**Example:**
```markdown
![](https://badge-oq5l.onrender.com/superbadge/YOUR_ID?style=chillax&bg=18191c)
```

---

## 🎛️ Configuration Parameters

You can combine any of these parameters to customize the badge.

### 🎭 Visuals & text
| Param | Values | Default | Description |
| :--- | :--- | :--- | :--- |
| `name` | Text | *Auto* | **Force Rename:** Overrides Server Name or Username with your own text. |
| `bg` | Hex Code | `09090b` | Custom background color (without #). |
| `borderRadius` | Pixels | `20` | Corner roundness (e.g., `0` for square, `30` for pill). |
| `showDisplayName` | `true/false` | `true` | Uses Global Name instead of username (User Mode only). |

### 🤖 AI Intelligence
| Param | Values | Default | Description |
| :--- | :--- | :--- | :--- |
| `aifeatures` | `true/false` | `true` | If false, completely hides the AI Chip/Text area. |
| `roastMode` | `true/false` | `false` | If true, AI insults your code/music/game choice instead of reporting status. |
| `idleMessage` | Text | `IDLE` | Custom status text when Offline/Away. |

### ⚡ Animation Control
| Param | Values | Default | Description |
| :--- | :--- | :--- | :--- |
| `animations` | `false` | `true` | **Master Switch:** Turns off ALL movement. |
| `bgAnimations` | `false` | `true` | Turns off background fluids/mesh (saves CPU), keeps text floating. |
| `fgAnimations` | `false` | `true` | Turns off UI floating/bobbing, keeps background alive. |

---

## 📦 Deployment

Deploy for free on **Render**.

1.  **Clone/Fork** this repository.
2.  Go to **Render Dashboard** -> New **Web Service**.
3.  Connect your repo.
4.  **Settings:**
    *   **Runtime:** Python 3
    *   **Build Command:** `pip install -r requirements.txt`
    *   **Start Command:** `gunicorn app:app`
5.  **Environment Variables:**
    *   `GEMINI_API_KEY`: *(Optional, for AI text)* Get from Google AI Studio.

### ⚠️ Discord User Status Requirement
To display **Live User Activity** (Games, Music, VS Code), the user **must** be in the **Lanyard Discord Server**.
1.  Join here: [discord.gg/lanyard](https://discord.gg/lanyard)
2.  Wait 1 minute.
3.  Your badge will activate.

---

<div align="center">
  <sub><b>Zandy HyperBadge</b> // Built by Zandy</sub>
</div>
