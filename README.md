## Setup (Windows PowerShell; on macOS/Linux use `source .venv/bin/activate`)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        
python server.py
```
