import os
import re
import time
import json
import requests
import anthropic
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
MATTERMOST_URL    = "http://localhost:56412"
MATTERMOST_TOKEN  = "mb6ckof5e3yoid87kh1y9hatea"
CHANNEL_ID        = "y66b5dg88igpjye6k9jy73u11y"
MEMORY_FILE       = "memory.json"

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Memory ────────────────────────────────────────────────────────────────────
def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_to_memory(url: str, summary: str):
    memory = load_memory()
    memory.append({
        "url": url,
        "summary": summary,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def search_memory(query: str) -> str:
    memory = load_memory()
    if not memory:
        return "Your Second Brain is empty. Drop some URLs to get started!"
    context = ""
    for i, item in enumerate(memory):
        context += f"\n---\nArticle {i+1} (saved {item['saved_at']}):\n{item['summary']}\nURL: {item['url']}\n"
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": (
                f"You are a Second Brain assistant. "
                f"The user asks: '{query}'\n\n"
                f"Here are their saved articles:\n{context}\n\n"
                f"Answer their question using only what's in their saved articles. "
                f"Be concise. Mention which article(s) the info came from."
            )
        }]
    )
    return message.content[0].text

# ── Daily Digest ──────────────────────────────────────────────────────────────
def send_daily_digest():
    memory = load_memory()
    if not memory:
        return
    now = datetime.now()
    recent = []
    for item in memory:
        saved = datetime.strptime(item["saved_at"], "%Y-%m-%d %H:%M")
        hours_ago = (now - saved).total_seconds() / 3600
        if hours_ago <= 24:
            recent.append(item)
    if not recent:
        return
    context = ""
    for i, item in enumerate(recent):
        context += f"\nArticle {i+1}:\n{item['summary']}\n"
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": (
                "You are a Second Brain assistant giving a morning digest. "
                "Here are the articles saved in the last 24 hours:\n"
                + context +
                "\nWrite a short digest (3-5 bullets) highlighting: "
                "1) Key themes across articles "
                "2) One surprising connection between them "
                "3) One question worth exploring further. "
                "Start with: '🌅 Good morning! Here's your Second Brain digest:'"
            )
        }]
    )
    post_message(message.content[0].text)

# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch_article(url: str) -> str:
    jina_url = f"https://r.jina.ai/{url}"
    try:
        resp = requests.get(jina_url, timeout=30)
        if resp.status_code == 200:
            return resp.text[:8000]
        return None
    except Exception:
        return None

def summarize(text: str) -> str:
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": (
                "You are a Second Brain assistant. "
                "Summarize this article in 3-5 bullet points. "
                "Be concise. End with: 'Save this to your Second Brain? (reply yes/no)'\n\n"
                + text
            )
        }]
    )
    return message.content[0].text

def post_message(text: str):
    headers = {
        "Authorization": f"Bearer {MATTERMOST_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {"channel_id": CHANNEL_ID, "message": text}
    requests.post(f"{MATTERMOST_URL}/api/v4/posts", json=payload, headers=headers)

def get_new_posts(since: int) -> list:
    headers = {"Authorization": f"Bearer {MATTERMOST_TOKEN}"}
    resp = requests.get(
        f"{MATTERMOST_URL}/api/v4/channels/{CHANNEL_ID}/posts",
        params={"since": since},
        headers=headers
    )
    posts = resp.json().get("posts", {})
    return sorted(posts.values(), key=lambda p: p["create_at"])

# ── Detection ─────────────────────────────────────────────────────────────────
URL_PATTERN   = re.compile(r'https?://\S+')
QUERY_PATTERN = re.compile(r'(what did i learn|what do i know|search|recall|find|tell me about)\s+(.+)', re.IGNORECASE)

def extract_url(text: str):
    match = URL_PATTERN.search(text)
    return match.group(0) if match else None

def extract_query(text: str):
    match = QUERY_PATTERN.search(text)
    return match.group(2).strip() if match else None

# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    print("Second Brain agent starting...")
    print(f"Memory file: {MEMORY_FILE}")
    print("Watching for URLs and queries... (Ctrl+C to stop)")

    last_check  = int(time.time() * 1000)
    pending     = {}
    last_digest = datetime.now().replace(hour=0, minute=0, second=0)

    while True:
        time.sleep(3)

        now = datetime.now()
        if now.hour == 9 and now.minute == 0 and (now - last_digest).total_seconds() > 3600:
            send_daily_digest()
            last_digest = now

        posts = get_new_posts(last_check)

        for post in posts:
            post_id   = post["id"]
            text      = post["message"]
            create_at = post["create_at"]

            if create_at > last_check:
                last_check = create_at

            if post.get("type") == "system_message":
                continue

            if any(x in text for x in ["📖 Reading", "✅ Saved", "🧠 You now", "👍 Skipped", "🔍 Searching", "⚠️", "🌅"]):
                continue

            if text.strip().lower() in ["yes", "no"] and pending:
                last_item = list(pending.values())[-1]
                if text.strip().lower() == "yes":
                    save_to_memory(last_item["url"], last_item["summary"])
                    post_message(f"✅ Saved! Added to your Second Brain.\n🧠 You now have {len(load_memory())} article(s) saved.")
                else:
                    post_message("👍 Skipped. Drop another link anytime!")
                pending.clear()
                continue

            query = extract_query(text)
            if query:
                post_message(f"🔍 Searching your Second Brain for: *{query}*...")
                answer = search_memory(query)
                post_message(answer)
                continue

            url = extract_url(text)
            if url and "localhost" not in url:
                post_message("📖 Reading that article for you...")
                article = fetch_article(url)
                if article:
                    summary = summarize(article)
                    pending[post_id] = {"url": url, "summary": summary}
                    post_message(summary)
                else:
                    post_message("⚠️ Couldn't fetch that article. Try a different URL.")

if __name__ == "__main__":
    main()