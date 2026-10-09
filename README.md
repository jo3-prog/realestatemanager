# Real Estate Sales & Leasing Management System (API)

A backend-only REST API built with **Django** and **Django REST Framework**.
Agents register (and wait for admin approval), publish property listings with multiple images,
and users search, save favourites, send inquiries, book inspections and leave reviews.

> New to Django? Read **`docs/LEARNING_GUIDE.md`** first: it explains every file step by step.

## Quick start

```bash
# 1. create + activate a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. install packages
pip install -r requirements.txt

# 3. create the database tables
python manage.py migrate

# 4. (optional) demo data: admin, approved agent, user, categories, properties
python manage.py seed_demo

# 5. run the server
python manage.py runserver
```

| What | URL |
|---|---|
| Swagger UI (try endpoints in the browser) | http://127.0.0.1:8000/api/docs/ |
| ReDoc | http://127.0.0.1:8000/api/redoc/ |
| OpenAPI schema | http://127.0.0.1:8000/api/schema/ |
| Django admin panel | http://127.0.0.1:8000/admin/ |

Demo logins (after `seed_demo`): `admin@example.com / Admin#12345`, `agent@example.com / Agent#12345`, `user@example.com / User#12345`.

Run the tests: `python manage.py test`

## Endpoints

Send the token as `Authorization: Bearer <access_token>` on protected endpoints.

### Auth
| Method | Endpoint | Who | Description |
|---|---|---|---|
| POST | `/api/auth/register/` | anyone | Register a user |
| POST | `/api/auth/login/` | anyone | Login with email + password |
| POST | `/api/auth/logout/` | anyone with a refresh token | Blacklist refresh token |
| POST | `/api/auth/refresh/` | anyone with a refresh token | New access token |
| POST | `/api/auth/reset-password/` | anyone | Email a reset token |
| POST | `/api/auth/reset-password/confirm/` | anyone with token | Set a new password |
| GET/POST | `/api/auth/verify-email/` | anyone with token | Verify email |
| POST | `/api/auth/resend-verification/` | logged in | Resend verification email |
| GET/PATCH | `/api/auth/me/` | logged in | View/edit own profile |

### Agents
| Method | Endpoint | Who | Description |
|---|---|---|---|
| POST | `/api/agents/register/` | anyone | Apply as agent (status: pending) |
| GET | `/api/agents/`, `/api/agents/{id}/` | anyone | Approved agents |
| GET/PATCH | `/api/agents/me/` | agent | Manage own profile |
| GET | `/api/admin/agents/` (`?status=`) | admin | All applications |
| GET | `/api/admin/agents/pending/` | admin | Pending agents |
| PATCH | `/api/admin/agents/{id}/approve/` | admin | Approve (email sent) |
| PATCH | `/api/admin/agents/{id}/reject/` | admin | Reject, optional `{"reason": ""}` |
| GET/PATCH/DELETE | `/api/admin/users/`, `/api/admin/users/{id}/` | admin | Manage users |

### Categories & properties
| Method | Endpoint | Who | Description |
|---|---|---|---|
| GET | `/api/categories/` | anyone | List |
| POST/PUT/PATCH/DELETE | `/api/categories/`, `/api/categories/{id}/` | admin | Manage |
| GET | `/api/properties/` | anyone | List (search/filter/sort/paginate) |
| POST | `/api/properties/` | approved agent (or admin) | Create |
| GET | `/api/properties/{id}/` | anyone | Detail (counts a view) |
| PUT/PATCH/DELETE | `/api/properties/{id}/` | owner agent or admin | Update / delete |
| POST | `/api/properties/{id}/images/` | owner or admin | Upload many images (`images` field) |
| DELETE | `/api/properties/{id}/images/{image_id}/` | owner or admin | Delete an image |
| GET | `/api/properties/mine/` | agent | My listings incl. drafts |
| GET | `/api/properties/featured/` | anyone | Featured listings |
| GET | `/api/properties/compare/?ids=1,2,3` | anyone | Compare 2 to 4 properties |
| PATCH | `/api/properties/{id}/suspend/`, `reinstate/`, `feature/`, `unfeature/` | admin | Moderation |

**Search & filter examples**: `?search=duplex` `?city=Lagos` `?location=lekki` `?min_price=500000&max_price=3000000` `?bedrooms=3` `?bathrooms=2` `?status=rent` (or `for_rent`) `?category=land` `?ordering=-price` `?page=2`

### Favorites, inquiries, inspections, reviews, notifications, analytics
| Method | Endpoint | Who | Description |
|---|---|---|---|
| POST/GET | `/api/favorites/` | logged in | Save / list mine |
| DELETE | `/api/favorites/{id}/` | logged in | Remove |
| POST | `/api/inquiries/` | anyone | Send inquiry to the agent |
| GET | `/api/inquiries/`, `/api/inquiries/{id}/` | logged in | Own / own listings' / all (admin) |
| PATCH | `/api/inquiries/{id}/respond/` | agent/admin | Answer (email sent) |
| POST/GET | `/api/inspections/` | logged in | Book / list |
| PATCH | `/api/inspections/{id}/status/` | agent/admin approve, reject, complete; booker cancel | Update status |
| POST | `/api/reviews/` | logged in | Rate an agent OR a property |
| GET | `/api/reviews/?agent=1` / `?property=2` | anyone | List reviews |
| GET, PATCH | `/api/notifications/`, `/api/notifications/{id}/read/`, `/api/notifications/read-all/` | logged in | In-app notifications |
| GET | `/api/analytics/agent/` | approved agent | Listings, views, inquiries, conversion rate |
| GET | `/api/analytics/admin/` | admin | Users, agents, listings, most viewed |

Inspection reminders: `python manage.py send_inspection_reminders` (schedule it with cron).

## Project structure
```
config/         settings.py, root urls.py
accounts/       custom User, auth endpoints, permission classes
agents/         AgentProfile, registration, admin approval
properties/     Category, Property, PropertyImage, Favorite, filters
inquiries/      Inquiry + agent responses
inspections/    InspectionBooking + reminder command
reviews/        Review (agent or property)
notifications/  Notification + notify() email service
analytics/      agent + admin dashboards
tests/          45 API tests
docs/           ERD.md, database_schema.sql, openapi.yml/json, Postman collection, LEARNING_GUIDE.md
tools/          make_postman.py
```

## Deliverables checklist
Source code (this repo) - README.md - ER diagram `docs/ERD.md` - Swagger at `/api/docs/` - Postman collection `docs/RealEstateAPI.postman_collection.json` - DB schema `docs/database_schema.sql` - Tests `tests/`.

Regenerate docs after changing the API:
```bash
python manage.py spectacular --file docs/openapi.yml
python manage.py spectacular --format openapi-json --file docs/openapi.json
python tools/make_postman.py
```

## Using PostgreSQL / Cloudinary
* PostgreSQL: `pip install psycopg2-binary`, then set `DB_ENGINE=postgres` and the `DB_*` variables (see `.env.example`).
* Cloudinary: `pip install cloudinary django-cloudinary-storage` and then follow the package docs to set it as the default file storage (`STORAGES` in settings.py). Local storage is used by default.
