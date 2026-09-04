.PHONY: run test check

run:
	python3 -m backend.server

test:
	python3 -m unittest discover -s tests -v

check: test
	node --check frontend/app.js
