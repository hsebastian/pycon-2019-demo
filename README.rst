watchmedo shell-command --patterns="*.py" --recursive --command='black --verbose --check .' .
watchmedo shell-command --patterns="*.py" --recursive --command='flake8 --count --statistics' .

# running flask
env FLASK_APP=mini_wallet/views.py FLASK_DEBUG=1 flask run

# entering DB from psql
psql -h localhost -p 5432 -U mydbuser -d mydb
