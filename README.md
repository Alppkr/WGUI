# WGUI

Simple Flask login page with default admin credentials.
Admin users can manage application users from the **Users** page.
Logged in users can create custom lists of type **Ip**, **Ip Range** or **String**
and store items with data, description and date.

## Setup

```bash
pip install -r requirements.txt
# The application will automatically apply migrations on startup, but you can
# also run them manually:
flask --app wgui db upgrade
```

## Run

```bash
python -m wgui
celery -A wgui.tasks worker -B
```

## Tests

```bash
pytest
```
