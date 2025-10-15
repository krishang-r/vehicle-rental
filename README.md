# vehicle-rental

This repository contains a small Flask-based vehicle rental application. The project is currently in development and includes multiple branches where features are being integrated.

Contents
 - `app.py` — main Flask application (routes, models and helpers)
 - `templates/` — Jinja2 HTML templates
 - `static/` — static assets (CSS)
 - `forms.py`, `models.py` — helper modules added by contributors
 - `requirements.txt` — Python dependencies

Quickstart (development)

1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app (development)

```bash
python run.py
```

4. Visit the app

Open http://127.0.0.1:5000/ in your browser.

Testing

Run the test suite with pytest:

```bash
pytest -q
```

Branching & workflow notes

- Feature work is developed on branches (e.g. `tanisha`, `krishang`) and merged into `main` when ready.
- Keep `main` deployable. Use `krishang` for ongoing work and open pull requests when you want a review.

Contributing

1. Fork and create a feature branch
2. Run tests and linters locally
3. Open a PR against `main` and request reviews

Security

- Do not commit secrets. Use environment variables for sensitive configuration such as `SECRET_KEY` and database URIs.

Need help?

Open an issue or ask for help in the repository.

--
Minimal README created/updated on branch `krishang`.
# vehicle-rental

Minimal Flask boilerplate for the vehicle-rental project.

Quickstart

1. Create a virtual environment and install deps:

	python -m venv .venv
	source .venv/bin/activate
	pip install -r requirements.txt

2. Run the app:

	python run.py

3. Test endpoint:

	curl http://127.0.0.1:5000/

Development notes

- App factory is in `app/__init__.py` and routes are in `app/routes.py`.
- To run tests: `pytest -q`
# vehicle-rental