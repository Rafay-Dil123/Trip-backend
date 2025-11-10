# 🚚 Trip Log App Backend

Welcome to the backend of the Trip Log App! This Django-powered API manages trip logging, duty scheduling, and route amenities for drivers.

---

## Features

- Trip creation and management
- Duty block scheduling
- Route amenities search (fuel, restaurants, etc.)
- Integration with OpenRouteService and OpenStreetMap
- RESTful API endpoints

---

## Quickstart

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/trip-log-backend.git
   cd trip-log-backend/backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   - Copy `.env.example` to `.env` and fill in your keys (e.g., `ORS_API_KEY`).

4. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Start the server**
   ```bash
   python manage.py runserver
   ```

---

## API Endpoints

- `POST /calculate/` — Calculate trip details and stops
- More endpoints coming soon!

---

## Tech Stack

- Python 3.11
- Django & Django REST Framework
- Docker (optional)
- OpenRouteService API
- OpenStreetMap Nominatim

---

## Environment Variables

ORS_API_KEY=""
Database_URL=""
GEOCODE_URL="https://api.openrouteservice.org/geocode/search"
ROUTE_URL="https://api.openrouteservice.org/v2/directions/driving-car"
NOMINATIM_URL="https://nominatim.openstreetmap.org/search"

---

## Contributing

Pull requests and issues are welcome! Please follow the code style and add tests for new features.

---

## License

MIT License © 2025 Your Name

---

## Contact

Questions or feedback? Open an issue or email [dilrafay@gmail.com](mailto:dilrafay@gmail.com).