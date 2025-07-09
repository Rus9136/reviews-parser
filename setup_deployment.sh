#!/bin/bash
# Setup script for deploying Reviews API on aqniet.site

echo "=== Setting up Reviews API deployment ==="

# 1. Create PostgreSQL database container
echo "1. Creating PostgreSQL database..."
docker run -d --name reviews-db \
  -e POSTGRES_DB=reviews_db \
  -e POSTGRES_USER=reviews_user \
  -e POSTGRES_PASSWORD=reviews_password \
  -p 5436:5432 \
  postgres:15

# Wait for database to be ready
echo "Waiting for database to be ready..."
sleep 10

# 2. Install Python dependencies
echo "2. Installing Python dependencies..."
cd /root/projects/reviews-parser
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Initialize database
echo "3. Initializing database..."
python database.py

# 4. Migrate existing data
echo "4. Migrating existing data to database..."
python migrate_to_db.py

# 5. Setup systemd service
echo "5. Setting up systemd service..."
cp reviews-api.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable reviews-api.service
systemctl start reviews-api.service

# 6. Get SSL certificate for subdomain
echo "6. Obtaining SSL certificate for reviews.aqniet.site..."
docker run --rm --name certbot \
  -v "/root/projects/infra/infra/certbot/conf:/etc/letsencrypt" \
  -v "/root/projects/infra/infra/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  --email admin@aqniet.site --agree-tos --no-eff-email \
  -d reviews.aqniet.site

# 7. Add nginx configuration
echo "7. Note: Add the nginx configuration from nginx-reviews.conf to the main nginx.conf"
echo "   Then reload nginx: docker exec hr-nginx nginx -s reload"

# 8. Check service status
echo "8. Checking service status..."
systemctl status reviews-api.service

echo ""
echo "=== Deployment setup complete ==="
echo "API will be available at: https://reviews.aqniet.site"
echo "Documentation: https://reviews.aqniet.site/docs"
echo ""
echo "Next steps:"
echo "1. Add nginx configuration from nginx-reviews.conf to /root/projects/hr-miniapp/nginx.conf"
echo "2. Reload nginx: docker exec hr-nginx nginx -s reload"
echo "3. Test the API: curl https://reviews.aqniet.site/health"