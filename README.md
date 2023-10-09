```cp .env-sample .env
virtualenv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env-sample .env
./manage.py runserver