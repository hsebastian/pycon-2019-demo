watchmedo shell-command --patterns="*.py" --recursive --command='black --verbose --check .' .
watchmedo shell-command --patterns="*.py" --recursive --command='flake8 --count --statistics' .

# running flask
env FLASK_APP=mini_wallet/views.py flask run