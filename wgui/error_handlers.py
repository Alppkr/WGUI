from flask import render_template
from pydantic import ValidationError


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template('500.html'), 500

    @app.errorhandler(400)
    def bad_request(error):
        return render_template('400.html'), 400

    @app.errorhandler(ValidationError)
    def pydantic_error(error):
        return render_template('400.html', errors=error.errors()), 400

