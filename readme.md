run the steering motor commad
sudo python3 -m Motor.smallmotor

run the server command
sudo python3 -m server.bike_client

**Run the GPS**

sudo python3 -m GPS.GPS

**Service for manual control**

sudo systemctl restart bike_service

sudo systemctl status bike_service

sudo tail -f /var/log/bike_service.log