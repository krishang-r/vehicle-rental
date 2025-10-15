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