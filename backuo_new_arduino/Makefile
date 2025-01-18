.PHONY: build run stop clean

build:
	sudo docker-compose build

run:
	sudo docker-compose up -d
	@echo "Aguardando serviços iniciarem..."
	@sleep 5
	@echo "Acesse http://localhost:5000 no navegador"

stop:
	sudo docker-compose down

clean:
	sudo docker-compose down -v
	sudo docker system prune -f

logs:
	sudo docker-compose logs -f

restart:
	sudo docker-compose restart

status:
	sudo docker-compose ps