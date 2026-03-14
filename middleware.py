# app/middleware.py
from flask import render_template, request
def maintenance_mode(app):
    @app.before_request
    def check_maintenance():
        if app.config.get("MAINTENANCE", False):
            # Admin veya özel IP kontrolü eklenebilir
            return render_template("maintenance.html"), 503