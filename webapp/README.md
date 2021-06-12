docker build -t flask-container ./flask
docker build -t nginx-container ./nginx
docker-compose up --build
