#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${1:-tunnel}"
changed_files=()

auto_set_file() {
  local file="$1"
  local content="$2"

  if [[ ! -f "$file" ]] || [[ "$(cat "$file")" != "$content" ]]; then
    printf '%s' "$content" > "$file"
    changed_files+=("$file")
  fi
}

append_missing_line() {
  local file="$1"
  local line="$2"
  if ! grep -Eiq "^${line//./\\.}([<>=!~].*)?$" "$file"; then
    printf '\n%s\n' "$line" >> "$file"
    changed_files+=("$file")
  fi
}

# 1) Procfile
procfile_content='web: gunicorn app:app'
auto_set_file "Procfile" "$procfile_content"

# 2) app.py root route validation + auto-fix
if [[ ! -f app.py ]]; then
  cat > app.py <<'PYEOF'
from flask import Flask, request, jsonify
from telegram import Bot
from werkzeug.utils import secure_filename
from datetime import datetime
from config import Config

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_FILE_SIZE

bot = Bot(token=Config.BOT_TOKEN)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@app.route("/")
def home():
    return jsonify({"status": "healthy", "service": "tunnel", "upload_endpoint": "/upload"}), 200

@app.route("/upload", methods=["POST"])
def upload():
    if request.headers.get("X-SECRET") != Config.UPLOAD_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    filename = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    try:
        bot.send_document(
            chat_id=Config.GROUP_CHAT_ID,
            document=file,
            filename=filename,
            caption=f"📂 New File Uploaded\\n🕒 {timestamp}\\n📎 {filename}",
        )
        return jsonify({"status": "File sent to group"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
PYEOF
  changed_files+=("app.py")
else
  if ! grep -Eq '@app\.route\(["\x27]/["\x27]\)' app.py; then
    if grep -q 'from flask import' app.py && ! grep -q 'jsonify' app.py; then
      python3 - <<'PY'
from pathlib import Path
import re
path = Path('app.py')
text = path.read_text()
text = re.sub(r'from flask import ([^\n]+)', lambda m: 'from flask import ' + m.group(1) + ', jsonify' if 'jsonify' not in m.group(1) else m.group(0), text, count=1)
path.write_text(text)
PY
    fi
    cat >> app.py <<'PYEOF'

@app.route("/")
def home():
    return jsonify({"status": "healthy", "service": "tunnel", "upload_endpoint": "/upload"}), 200
PYEOF
    changed_files+=("app.py")
  fi
fi

# 3) config.py generation if missing
if [[ ! -f config.py ]]; then
  cat > config.py <<'PYEOF'
import os


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
    UPLOAD_SECRET = os.getenv("UPLOAD_SECRET")

    MAX_FILE_SIZE = 20 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"txt", "pdf", "jpg", "png", "mp4", "zip"}
PYEOF
  changed_files+=("config.py")
fi

# 4) requirements validation
if [[ ! -f requirements.txt ]]; then
  cat > requirements.txt <<'REQEOF'
flask
gunicorn
python-telegram-bot
werkzeug
REQEOF
  changed_files+=("requirements.txt")
else
  append_missing_line requirements.txt flask
  append_missing_line requirements.txt gunicorn
  append_missing_line requirements.txt python-telegram-bot
  append_missing_line requirements.txt werkzeug
fi

# 5) runtime.txt generation
if [[ ! -f runtime.txt ]] || ! grep -Eq '^python-3\.11(\.[0-9]+)?$' runtime.txt; then
  echo 'python-3.11.9' > runtime.txt
  changed_files+=("runtime.txt")
fi

# 6) app.json validation/generation
repo_url="https://github.com/Oxeigns/Tunnel"
if git remote get-url origin >/dev/null 2>&1; then
  origin_url="$(git remote get-url origin)"
  if [[ "$origin_url" == https://github.com/* ]] || [[ "$origin_url" == git@github.com:* ]]; then
    clean="${origin_url%.git}"
    clean="${clean/git@github.com:/https://github.com/}"
    repo_url="$clean"
  fi
fi

cat > /tmp/appjson.new <<EOFJSON
{
  "name": "Telegram File Forwarder",
  "description": "Secure file upload server that forwards files to a Telegram group instantly.",
  "repository": "${repo_url}",
  "logo": "https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg",
  "keywords": ["flask", "telegram", "file-upload", "bot", "heroku"],
  "env": {
    "BOT_TOKEN": {"description": "Telegram Bot Token from @BotFather", "required": true},
    "GROUP_CHAT_ID": {"description": "Telegram Group Chat ID (e.g. -100xxxxxxxxxx)", "required": true},
    "UPLOAD_SECRET": {"description": "Secret key for protecting upload endpoint", "required": true}
  },
  "formation": {"web": {"quantity": 1, "size": "basic"}},
  "buildpacks": [{"url": "heroku/python"}]
}
EOFJSON
if [[ ! -f app.json ]] || ! cmp -s app.json /tmp/appjson.new; then
  mv /tmp/appjson.new app.json
  changed_files+=("app.json")
else
  rm -f /tmp/appjson.new
fi

# 9) Heroku git remote check
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if ! git remote get-url heroku >/dev/null 2>&1; then
    if command -v heroku >/dev/null 2>&1; then
      heroku git:remote -a "$APP_NAME" || true
    fi
    if ! git remote get-url heroku >/dev/null 2>&1; then
      git remote add heroku "https://git.heroku.com/${APP_NAME}.git" || true
    fi
  fi
fi

# 7) Output exactly what changed
if [[ ${#changed_files[@]} -eq 0 ]]; then
  echo "No file changes needed. Project already passes Heroku checks."
else
  mapfile -t uniq_files < <(printf '%s\n' "${changed_files[@]}" | awk '!seen[$0]++')
  echo "Updated files:"
  printf ' - %s\n' "${uniq_files[@]}"
fi

echo "Done. Next steps:"
echo "  git add Procfile app.py config.py requirements.txt runtime.txt app.json"
echo "  git commit -m 'Fix Heroku deployment scaffolding'"
echo "  git push heroku main"
