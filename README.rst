watchmedo shell-command --patterns="*.py" --recursive --command='black --verbose --check .' .

flake8 --count --statistics
