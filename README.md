# WGUI

Simple Flask login page with default admin credentials.
Admin users can manage application users from the **Users** page.
Logged in users can create custom lists of type **Ip**, **Ip Range** or **String**
and store items with data, description and date.

## Setup

```bash
pip install -r requirements.txt
flask --app wgui db upgrade
```

## Run

```bash
python -m wgui
```

## Tests

```bash
pytest
```
