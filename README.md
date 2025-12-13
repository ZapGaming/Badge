# ⚡ Chillax HyperBadge

<div align="center">

<a href="https://github.com/zapgaming">
  <img src="https://badge-oq5l.onrender.com/superbadge/1173155162093785099?style=hyper&showDisplayName=true&roastMode=false&&fgAnimations=false&aifeatures=false" alt="HyperBadge" height="180"/>
</a>

<p align="center">
  <b>The Ultimate Dynamic Status Generator</b><br>
  Powered by Flask, Lanyard, and Google Gemini AI.
</p>

</div>

---

## 🚀 Overview

HyperBadge is a high-performance SVG generation API. It creates live, animated, and AI-enhanced badges for your GitHub Profile or Website. 

It tracks your **Discord Activity** (Games, VS Code, Spotify) or **GitHub Stats** and uses a Neural AI to generate sci-fi HUD updates (or roast you) in real-time.

### ✨ Key Features
*   **🎵 Deep Spotify:** Automatically pulls Album Art and sets it as a blurred, atmospheric background.
*   **🎨 5 Visual Engines:** Choose from Hyper, EasterEgg (Mac OS), Cute, Terminal, or Professional.
*   **🧠 Neural Core:** Gemini AI analyzes your specific song or game and comments on it.
*   **🕹️ Animation Control:** Fine-tune background drift vs. UI bobbing for performance or aesthetics.
*   **🔌 Universal:** Supports Discord User IDs, Discord Server Invites, and GitHub Usernames.

---

## 🛠️ Usage Guide

Base URL: `https://your-app-name.onrender.com`

### 1. The "Magic" Link (Auto-Detect)
Automatically detects if you provided a User ID (Lanyard) or an Invite Code.

```markdown
![My Status](https://your-app-name.onrender.com/superbadge/YOUR_DISCORD_USER_ID)
```

### 2. Specific Endpoints

| Type | Endpoint | Description |
| :--- | :--- | :--- |
| **User Status** | `/badge/user/<id>` | Shows detailed activity, music, and AI status. |
| **Discord Server** | `/badge/discord/<code>` | Shows Member count and Online count. |
| **GitHub Stats** | `/badge/github/<user>` | Shows Repositories and Follower counts. |

---

## 🎛️ Configuration Parameters

Customize your badge by adding these queries to the end of your URL:
Example: `.../superbadge/12345?style=cute&roastMode=true&bg=ffe4e1`

### 🎨 Visuals
| Param | Values | Description |
| :--- | :--- | :--- |
| `style` | `hyper`, `easteregg`, `cute`, `terminal`, `pro` | The rendering engine to use. (Default: `hyper`) |
| `bg` | Hex Code (e.g. `09090b`) | Custom background color (without the #). |
| `borderRadius` | Number (e.g. `20`) | Corner roundness in pixels. |
| `showDisplayName` | `true`, `false` | Use Global Discord Name instead of username. |

### ⚡ Animation & Performance
| Param | Values | Description |
| :--- | :--- | :--- |
| `animations` | `false` | **Master Switch:** Turns off ALL movement (CPU friendly). |
| `bgAnimations` | `false` | Disables background fluid/mesh, keeps UI floating. |
| `fgAnimations` | `false` | Disables UI floating/bobbing, keeps background fluid. |

### 🤖 AI Intelligence
| Param | Values | Description |
| :--- | :--- | :--- |
| `aifeatures` | `false` | **Privacy Mode:** Completely hides the AI text and chip from the badge. |
| `roastMode` | `true` | Changes AI personality from "Sci-Fi HUD" to "Savage Troll". |
| `idleMessage` | Text (e.g. `Sleepy`) | Custom text to show when you are Offline/Idle. |

---

## 🖼️ Style Gallery

### 1. Style: `hyper` (Default)
> Liquid GLSL shaders, Album Art backgrounds, glassmorphism.
```markdown
![](https://.../superbadge/ID?style=hyper)
```

### 2. Style: `easteregg` (Liquid OS)
> A futuristic "macOS 26" aesthetic with floating islands, RGB flow borders, and an aurora mesh background.
```markdown
![](https://.../superbadge/ID?style=easteregg)
```

### 3. Style: `terminal`
> Retro CRT hacker monitor. Scanlines, line numbers, and syntax highlighting.
```markdown
![](https://.../superbadge/ID?style=terminal&roastMode=true)
```

### 4. Style: `cute`
> Pastel colors, scrolling patterns, bouncing hearts, and a kawaii bunny helper.
```markdown
![](https://.../superbadge/ID?style=cute&bg=fff0f5)
```

### 5. Style: `professional`
> Static, clean, high-contrast. Uses system fonts. Perfect for email signatures.
```markdown
![](https://.../superbadge/ID?style=professional)
```

---

## 📦 Deployment (Self-Hosting)

Deploy for free on **Render**.

1.  Clone this repository.
2.  Go to [Render.com](https://render.com) and create a **Web Service**.
3.  Connect your repo.
4.  **Build Command:** `pip install -r requirements.txt`
5.  **Start Command:** `gunicorn app:app`
6.  **Environment Variables:**
    *   `GEMINI_API_KEY`: Get this from [Google AI Studio](https://aistudio.google.com/app/apikey).

### ⚠️ Requirements
To show Discord User status, you **must** be in the Lanyard Discord Server.
*   Join here: [discord.gg/lanyard](https://discord.gg/lanyard)

---

<div align="center">
  <sub>HyperBadge V13 // Chillax Development</sub>
</div>
