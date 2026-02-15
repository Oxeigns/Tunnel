<a href="https://heroku.com/deploy?template=https://github.com/Oxeigns/Tunnel">
  <img src="https://www.herokucdn.com/deploy/button.svg" alt="Deploy to Heroku">
</a>

## Automated Heroku fixer

Run this command from the repo root to validate and repair Heroku deployment files:

```bash
./fix_heroku.sh
```

The script checks/fixes:
- `Procfile`
- root `/` route health response in `app.py`
- `config.py`
- required dependencies in `requirements.txt`
- `runtime.txt` (Python 3.11.x)
- `app.json`
- Heroku Git remote (`heroku git:remote -a tunnel` fallback to direct remote URL)
