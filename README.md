# Dependencies
* pyenv
* docker
* docker-compose

# use local python
pyenv local

# install and activate virtualenv
pyenv virtualenv 380-11022020ve
pyenv activate 380-11022020ve

# uninstall virtualenv
pyenv virtualenv-delete 380-2311ve

# pycon-2019-demo
watchmedo shell-command --patterns="*.py" --recursive --command='black --verbose --check .' .
watchmedo shell-command --patterns="*.py" --recursive --command='flake8 --count --statistics' .

# have unit tests run once a code or test change is detected
ptw mini_wallet tests/unit -- tests/unit

# running flask
env FLASK_APP=mini_wallet/views.py FLASK_ENV=development flask run
env FLASK_APP=mini_wallet/views.py FLASK_DEBUG=1 flask run

# starting local DB
docker-compose up

# entering DB from psql
psql -h localhost -p 5432 -U mydbuser -d mydb

# docker image & container status
watch 'docker image list && docker container list'

