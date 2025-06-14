from . import create_app

app = create_app()

if __name__ == '__main__':
    # Explicitly disable debug mode for production runs
    app.run(debug=False)
