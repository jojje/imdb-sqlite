test:
	flake8 --max-line-length=120

dist:
	python setup.py sdist bdist_wheel

rc-deploy:
	twine upload -r pypitest dist/*

rc-install:
	python -m pip install --index-url https://test.pypi.org/simple/ imdb-sqlite

clean:
	rm -rf build dist *egg-info
