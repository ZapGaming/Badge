# ⚡ Chillax HyperBadge

<div align="center">

<a href="https://github.com/zapgaming">
  <img src="https://badge-oq5l.onrender.com/superbadge/1173155162093785099?style=easteregg&showDisplayName=true&roastMode=false&animations=false&aifeatures=false" alt="HyperBadge" height="180"/>
</a>

<p align="center">
  <b>The Ultimate Dynamic SVG Generator for GitHub Profiles</b><br>
  Powered by Flask, Lanyard, and Google Gemini AI.
</p>

</div>

---

## 🎨 Overview

HyperBadge is a high-performance Python application that generates **real-time, animated SVG badges** for your GitHub `README.md`.

It fetches data from **Discord** (User Status, Spotify, Games) or **GitHub** (Repo stats) and uses **Google Gemini AI** to generate witty, sci-fi, or "roast" commentary based on what you are doing right now.

## ✨ Features

*   **🧠 Neural Core:** Embedded AI analyzes your status and comments on it (e.g., roasts your music taste or compliments your coding stack).
*   **🎵 Deep Spotify:** Detected automatically. Background morphs into blurred Album Art with color-matching borders.
*   **🎨 5 Visual Engines:** Choose between `Hyper` (Liquid GLSL), `EasterEgg` (macOS Fluid), `Cute` (Pastel), `Terminal` (Retro), or `Pro` (Clean).
*   **🕹️ Lanyard Powered:** Shows exactly what you are doing (VS Code, League of Legends, etc).
*   **⚡ High Performance:** Intelligent Caching, Animation Toggles, and CSS optimization.

---

## 🚀 Usage Guide

### 1. The Universal Endpoint
Copy the code below into your Markdown file. Replace `YOUR_ID` with your **Discord User ID**.

```markdown
[![My Status](https://your-app-url.onrender.com/superbadge/YOUR_DISCORD_ID_HERE)](https://discord.com/users/YOUR_DISCORD_ID_HERE)
```

### 2. GitHub Stats
Shows your repo counts and follower stats in a high-tech style.

```markdown
[![GitHub Stats](https://your-app-url.onrender.com/badge/github/YOUR_GITHUB_USERNAME)](https://github.com/YOUR_GITHUB_USERNAME)
```

### 3. Discord Server Widget
Shows live member counts and online presence. Use your Server Invite Code (e.g., `DrfX6286kF`).

```markdown
[![Server Stats](https://your-app-url.onrender.com/badge/discord/INVITE_CODE)](https://discord.gg/INVITE_CODE)
```

---

## 🎨 Style Gallery & Customization

You can fully customize the look by adding `?param=value` to the URL.

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `style` | `hyper` | Choose visual engine: `hyper`, `easteregg`, `cute`, `terminal`, `pro`. |
| `roastMode` | `false` | If `true`, the AI will insult you instead of writing a HUD status. |
| `bg` | `09090b` | Hex color code for the background (without `#`). |
| `borderRadius` | `20px` | Roundness of the card corners. |
| `idleMessage` | `IDLE` | Custom text to show when you are offline/afk. |
| `animations` | `true` | Set to `false` to disable movement (good for low-performance PCs). |
| `aifeatures` | `true` | Set to `false` to completely hide the AI box. |

### Examples

**🔥 The "Roast Me" Terminal**
> Gives you a hacker-style badge where the console insults your coding skills.
```markdown
![](https://.../superbadge/ID?style=terminal&roastMode=true)
```

**🍏 The "Fluid OS" (Mac Aesthetic)**
> The new Easter Egg style with Aurora backgrounds and glass floating panels.
```markdown
![](https://.../superbadge/ID?style=easteregg&showDisplayName=true)
```

**🎀 The "Kawaii" Card**
> Pastel colors, bouncing animations, and cute AI text.
```markdown
![](https://.../superbadge/ID?style=cute&idleMessage=Sleepy)
```

---

## 🛠️ Deployment (Self-Hosting)

You can host this for free on **Render.com**.

1.  **Fork/Clone** this repository.
2.  Create a **Google Gemini API Key** at [Google AI Studio](https://aistudio.google.com/).
3.  Go to **Render Dashboard** -> New **Web Service**.
4.  Connect your repo.
5.  **Settings:**
    *   **Runtime:** Python 3
    *   **Build Command:** `pip install -r requirements.txt`
    *   **Start Command:** `gunicorn app:app`
6.  **Environment Variables (Crucial):**
    *   Add Key: `GEMINI_API_KEY`
    *   Value: `Paste_Your_Google_Key_Here`
7.  Deploy! Use the URL provided by Render.

---

## ⚠️ Important Note for Lanyard
For the user status to work, you must be in the **Lanyard Discord Server**. This is a requirement of the free Lanyard API to track your presence.
1.  Join here: [discord.gg/lanyard](https://discord.gg/lanyard)
2.  Wait 1 minute.
3.  Your badge will start working.

---

<div align="center">
  <sub>Built by <b>WQ</b> & Chillax Development</sub>
</div>
