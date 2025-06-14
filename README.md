# WGUI

WGUI is a small Flask application that provides user management and custom list handling (IP addresses, IP ranges and free text). The project includes authentication, JWT based sessions and a scheduled cleanup job that removes expired list entries and sends notification emails.

## Requirements

- Python 3.10+
- A relational database supported by SQLAlchemy (SQLite is used by default)
- See `requirements.txt` for Python package dependencies

## Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Apply database migrations (uses Alembic under the hood)
flask --app wgui db upgrade
```

By default the application creates an admin user with username `admin` and password `admin`. You can override the credentials and other settings using the following environment variables:

- `SECRET_KEY` – Flask secret key
- `APP_USERNAME` – admin username
- `APP_PASSWORD_HASH` – hashed password for the admin user
- `DATABASE_URL` – database connection string
- `JWT_SECRET_KEY` – secret key used for JWT tokens

Use `werkzeug.security.generate_password_hash` to create the value for `APP_PASSWORD_HASH`.

## Running Locally

```bash
python -m wgui
```

The application automatically starts the background scheduler so no additional worker process is required.

## Tests

```bash
pytest
```

## Production Deployment

1. **Install dependencies** and apply migrations as shown above.
2. **Install Gunicorn and Nginx** (example for Debian/Ubuntu):

```bash
sudo apt update
sudo apt install gunicorn nginx
```

3. **Disable debug mode** (do not set `FLASK_DEBUG`) and ensure `SECRET_KEY`/`JWT_SECRET_KEY` are strong values.
4. Run the application with a production WSGI server such as Gunicorn:

```bash
gunicorn -w 4 -b unix:/tmp/wgui.sock 'wgui:create_app()'
```

5. Place a reverse proxy such as **Nginx** in front of Gunicorn to handle TLS termination and static file delivery.
6. For additional hardening consider installing **Flask‑Talisman** to set HTTP security headers and enforce HTTPS.

### Running as a Service

This repository provides an example systemd service file at `systemd/wgui.service`.
Copy it to `/etc/systemd/system/` to keep the server running after reboots:

```ini
[Unit]
Description=WGUI Gunicorn
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/WGUI
EnvironmentFile=/path/to/env
ExecStart=/usr/bin/gunicorn -w 4 -b unix:/tmp/wgui.sock 'wgui:create_app()'
Restart=always

[Install]
WantedBy=multi-user.target
```

Then start and enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl start wgui
sudo systemctl enable wgui
```

The APScheduler job runs inside the Flask process and will clean up expired items daily at midnight. Email recipients and SMTP credentials can be configured from the **Email Settings** page once logged in as an admin.

### Example Nginx Configuration

To expose the application on port 80 and proxy requests to Gunicorn you can create
`/etc/nginx/sites-available/wgui` with the following contents:

```nginx
server {
    listen 80;
    server_name example.com;  # change to your domain

    location / {
        include proxy_params;
        proxy_pass http://unix:/tmp/wgui.sock;
    }
}
```

Enable the configuration and reload Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/wgui /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```
If you serve the application over plain HTTP the login cookie will not be set because it uses the "Secure" flag. When placing Nginx in front of the app ensure HTTPS is enabled (or set `JWT_COOKIE_SECURE=False` for testing only). The simplest way is to configure TLS termination in Nginx.


### Example Nginx Configuration with SSL

Create `/etc/nginx/sites-available/wgui-ssl`:
```nginx
server {
    listen 443 ssl;
    server_name example.com;  # change to your domain

    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    location / {
        include proxy_params;
        proxy_pass http://unix:/tmp/wgui.sock;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# optionally redirect HTTP to HTTPS
server {
    listen 80;
    server_name example.com;
    return 301 https://$host$request_uri;
}
```

Enable the config and reload Nginx similar to the previous section.
