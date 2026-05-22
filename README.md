# SAM.gov MCP Connector

Connects Claude to the US Government's System for Award Management (SAM.gov).
Ask Claude to search federal contracts, get solicitation details, and look up registered vendors — all in plain English.

---

## What It Does

| Tool | What You Can Ask Claude |
|------|------------------------|
| `search_opportunities` | "Find active telecom contracts under $10M in Texas" |
| `get_opportunity` | "Get full details for notice ID SPE4A624R0022" |
| `search_entities` | "Look up vendor with CAGE code 5N6X3" |

---

## Setup (One Time)

### 1. Install Python
Download from https://python.org — install the latest version (3.11+).

### 2. Install dependencies
Open Terminal (Mac) or Command Prompt (Windows) and run:
```
pip install mcp[cli] httpx
```

### 3. Set your API key (optional — key is already baked in)
If you want to use your own key, set this environment variable:
```
export SAM_API_KEY=your_key_here       # Mac/Linux
set SAM_API_KEY=your_key_here          # Windows
```

---

## Run Locally (for testing)

```bash
python main.py
```

---

## Deploy on Railway (Production)

1. Go to https://railway.app and create a free account
2. Create a **New Project** → **Deploy from GitHub repo**
3. Push this folder to a GitHub repo first (see below)
4. In Railway, set the **Start Command** to:
   ```
   python main.py
   ```
5. Add Environment Variable in Railway dashboard:
   - Key: `SAM_API_KEY`
   - Value: `VHu23zpvOirNifNM2o9ewSeu6XvyjGlGvkSlM9y7`
6. Railway gives you a public URL like `https://your-app.up.railway.app`

---

## Push to GitHub (required for Railway)

1. Go to https://github.com and create a new repository called `sam-gov-connector`
2. Upload `main.py`, `requirements.txt`, and `README.md` to it
3. That's it — Railway will pull from there automatically

---

## Connect to Claude Desktop

Add this to your Claude Desktop config file:

**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "sam-gov": {
      "command": "python",
      "args": ["/full/path/to/main.py"]
    }
  }
}
```

Replace `/full/path/to/main.py` with the actual path where you saved the file.

---

## Example Prompts for Claude

- *"Search SAM.gov for active telecom opportunities in Saudi Arabia"*
- *"Find any sources sought notices from the Department of Defense related to fiber optics"*
- *"Get the full details of SAM.gov notice ID [paste notice ID]"*
- *"Look up the SAM registration for a company named Verizon Business"*
- *"Find 8(a) set-aside contracts in the network engineering space"*

---

## API Key

This connector uses the SAM.gov public API. The key included is a personal API key.
Get your own free key at: https://sam.gov/data-services → "API Keys"

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `403 Forbidden` | Your API key may be expired — get a new one at sam.gov/data-services |
| `No results found` | Try broader keywords or remove filters |
| `Connection error` | Check internet connection; SAM.gov may be down temporarily |
