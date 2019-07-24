all: check cover lint format

check:
	MYPYPATH=./src mypy -p iccli

test:
	pytest

cover:
	pytest --cov

cover-html:
	pytest -x --cov --cov-report html

lint:
	# PyCQA/pylint#214
	pylint --disable=similarities src/iccli

format:
	black --include '(\.pyi?|\.icp?)$$' .

install:
	pip install -e .[dev]

upgrade:
	pip install -e .[dev] --upgrade

dist:
	rm -rf .eggs build dist
	find . -name *.egg-info | xargs rm -rf
	python setup.py sdist bdist_wheel

.PHONY: dist

clean:
	rm -rf .coverage .eggs .pytest_cache build htmlcov dist
	find . -name *.egg-info | xargs rm -rf
	find . -name .mypy_cache | xargs rm -rf
	find . -name __pycache__ | xargs rm -rf