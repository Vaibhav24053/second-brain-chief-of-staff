# Second Brain Chief of Staff

An AI agent that lives in your chat and acts as a personal knowledge teammate.

## The Problem
I read 50 articles a week and retain almost none of them. Bookmarks don't work. Notion pages go unread. The problem isn't saving — it's resurfacing.

## The Solution
A teammate in your chat that:
- **Reads articles you drop** → summarizes in 5 bullets → asks if you want to save
- **Answers questions from your reading** → "what did I learn about AI?" → sourced answer
- **Sends a morning digest** → key themes, surprising connections, one question worth exploring

## Demo
[Insert YouTube link here]

## How it Works

You (Mattermost) → Switch Rooms → Agent (Python + Claude API)
↓
Jina Reader (fetch articles)
↓
Claude claude-sonnet-4-6 (summarize + reason)
↓
Local JSON memory (save + search)


## Stack
- **Switch Rooms** — connects agent to Mattermost as a chat teammate
- **OpenCode** — agent runtime (locally on laptop)
- **Claude API** (claude-sonnet-4-6) — reasoning, summarization, memory search
- **Jina Reader** — free article fetching (no API key needed)
- **Python** — agent logic, polling loop, memory management

## Setup

### Requirements
- Docker Desktop
- OpenCode with Anthropic API key
- Switch Console
- Python 3.9+

### Installation
```bash
git clone https://github.com/Vaibhav24053/second-brain-chief-of-staff
cd second-brain-chief-of-staff
pip install anthropic requests
```

### Configuration
Edit `agent.py` and fill in:
```python
MATTERMOST_TOKEN = "your-token"   # From Mattermost profile
CHANNEL_ID       = "your-channel" # From channel info panel
```

### Run
```bash
python3 agent.py
```

Then drop a URL in your Mattermost channel.

## Usage
| Action | What to type |
|---|---|
| Summarize article | Paste any URL |
| Save to memory | Reply `yes` |
| Skip | Reply `no` |
| Search memory | `what did I learn about X?` |
| Manual digest | `tell me about everything` |

## Built for
Flip the Switch Hackathon — WeMakeDevs x Switch AI (November 2026)
