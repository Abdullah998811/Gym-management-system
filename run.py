import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5000))
    app_env = os.environ.get('APP_ENV', 'production').lower()
    flask_debug = os.environ.get('FLASK_DEBUG', '0').strip() in ('1', 'true', 'True')
    debug = flask_debug and (app_env != 'production')
    app.run(host=host, port=port, debug=debug)
