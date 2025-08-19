.PHONY: build up down install-db init-roles run

# Build the Docker image
build:
	docker build -t majestic-sapp .

# Start the services defined in docker-compose.yml
up:
	docker-compose up -d

# Stop the services
down:
	docker-compose down

# Install PostgreSQL and set up the database
install-db:
	docker-compose run web bash -c "python scripts/init_db.sh"

# Initialize user roles
init-roles:
	docker-compose run web bash -c "python scripts/init_roles.py"

# Run the application
run:
	docker-compose run web python src/main.py