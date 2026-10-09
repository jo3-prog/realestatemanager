# Learning Guide: how this Django project works (for total beginners)

You do not need to know Django to follow this. Read it top to bottom once, then keep it open while you look at the code.

---

## Part 1. The big ideas in plain English

**API.** A website returns pretty pages. An *API* returns **data** (usually JSON) that other programs (a mobile app, a React frontend) use. Our project has no pages at all, only URLs that accept and return JSON. Example: `GET /api/properties/` returns a list of properties as JSON.

**HTTP verbs.** Every request has a verb that says what you want to do:

| Verb | Meaning | Example |
|---|---|---|
| GET | read | `GET /api/properties/` |
| POST | create | `POST /api/properties/` |
| PUT | replace everything | `PUT /api/properties/5/` |
| PATCH | change part of it | `PATCH /api/properties/5/` |
| DELETE | remove | `DELETE /api/properties/5/` |

**Status codes** are the server's answer: `200` OK, `201` created, `204` deleted, `400` your data is invalid, `401` you are not logged in, `403` you are logged in but not allowed, `404` not found.

**Django** is a Python web framework. **Django REST Framework (DRF)** is an add-on that makes building APIs easy. We use both.

**Project vs app.** A *project* is the whole system (`config/`). An *app* is one feature area with its own models, views and URLs. We have 8 apps: `accounts`, `agents`, `properties`, `inquiries`, `inspections`, `reviews`, `notifications`, `analytics`. Splitting into apps is what the requirements call a "modular architecture".

**The five building blocks you will meet in every app** (learn these and you understand 90 % of Django REST):

1. **Model** (`models.py`): describes a database table in Python. One class = one table, one attribute = one column, one object = one row.
2. **Serializer** (`serializers.py`): converts model objects to JSON and back, and **validates** incoming data.
3. **View / ViewSet** (`views.py`): the code that runs when a request arrives (fetch data, check rules, return a response).
4. **URL** (`urls.py`): maps an address like `/api/properties/` to a view.
5. **Permission** (`permissions.py`): decides *who* may call a view.

The journey of a request:

```
Client --> urls.py (which view?) --> authentication (who are you? JWT)
       --> permissions (are you allowed?) --> view (do the work)
       --> serializer (validate input / format output) --> model (database) --> JSON response
```

**Migrations.** When you change a model, you run `makemigrations` (Django writes a "change plan" file) and then `migrate` (Django applies it to the database). You never write SQL by hand.

**JWT (JSON Web Token).** After you log in you receive two tokens: a short-lived **access token** (30 min) that you send with every request in the header `Authorization: Bearer <token>`, and a longer-lived **refresh token** (7 days) used only to get new access tokens. Logging out "blacklists" the refresh token so it cannot be used again.

---

## Part 2. Setting up from zero (what I did, and what you would type)

```bash
mkdir realestate && cd realestate
python -m venv venv                 # a private box for this project's packages
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install django djangorestframework djangorestframework-simplejwt django-filter Pillow drf-spectacular django-cors-headers
pip freeze > requirements.txt       # (I wrote a cleaner requirements.txt by hand)

django-admin startproject config .  # creates manage.py + the config/ folder
python manage.py startapp accounts  # repeat for: agents properties inquiries inspections reviews notifications analytics
```

Why a *virtual environment*? It keeps this project's package versions separate from every other Python project on your computer.

Why `startproject config .`? The dot means "put it in the current folder", and `config` is just the name of the settings folder.

---

## Part 3. `config/settings.py`: the control panel

Open `config/settings.py`. The parts that matter:

* **`INSTALLED_APPS`**: Django only knows about an app if it is listed here. Our own apps *and* the packages (`rest_framework`, `django_filters`, `drf_spectacular`, `corsheaders`, `token_blacklist`) go here.
* **`AUTH_USER_MODEL = "accounts.User"`**: tells Django to use *our* User model. This must be set **before your first `migrate`**, otherwise it is painful to change later.
* **`DATABASES`**: SQLite by default (a single file, zero setup). Set `DB_ENGINE=postgres` to use PostgreSQL.
* **`REST_FRAMEWORK`**: global API rules: JWT authentication, "must be logged in" by default, filter backends, pagination (10 per page), rate limiting.
* **`SIMPLE_JWT`**: token lifetimes and blacklisting.
* **`MEDIA_ROOT` / `MEDIA_URL`**: where uploaded images are saved and served.
* **`EMAIL_BACKEND`**: by default emails are **printed in your terminal** instead of being sent, so you can see them without configuring an email server.
* **Environment variables**: `SECRET_KEY`, `DEBUG`, database passwords, and so on come from the environment (`env()` helper at the top) so secrets never sit in your code. Copy `.env.example` to see the names. This satisfies "environment variables" in the requirements.

**Rate limiting.** In `REST_FRAMEWORK` you'll see `DEFAULT_THROTTLE_RATES`. Anonymous visitors get 100 requests/hour, logged-in users 1000/hour, and the "auth" endpoints (register, login, refresh, reset password) only **20/hour** to slow down password guessing. While you test manually you may hit this, and if you do you'll get a `429 Too Many Requests`. Raise the `auth` number temporarily, or wait an hour.

---

## Part 4. The `accounts` app: users and login

### 4.1 `models.py`: the custom User

```python
class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(choices=Role.choices, default=Role.USER)
    ...
    USERNAME_FIELD = "email"
```

* `AbstractUser` already gives us username, password (hashed!), first/last name, `is_active`, `date_joined`... We only **add** what we need.
* `unique=True` on email implements the validation rule "Email must be unique".
* `role` is how we do **role-based access control**: `admin`, `agent` or `user`.
* `USERNAME_FIELD = "email"` means people log in with email, not username.
* In `save()`, anyone created via `createsuperuser` automatically gets role `admin`, and emails are stored lowercase.

Helper properties `is_admin_role` and `is_approved_agent` keep permission code short and readable.

### 4.2 `permissions.py`: who may do what

Each class answers one question:

* `IsAdminRole`: is this an admin?
* `IsApprovedAgent`: is this an agent **whose application was approved**? (this is the rule "Only approved agents can create listings")
* `IsApprovedAgentOrAdmin`
* `IsOwnerOrAdmin`: for a single object, is it *my* listing (or am I an admin)? This stops Agent A from editing Agent B's property.

DRF calls `has_permission()` before the view runs and `has_object_permission()` when a specific object is fetched with `get_object()`.

### 4.3 `serializers.py`

* `RegisterSerializer`: fields for signing up. Points to notice:
  * `password` is `write_only` (accepted, never returned).
  * `validate()` checks the two passwords match and runs Django's password-strength rules.
  * `create()` calls `create_user()`, which **hashes** the password. It always sets `role=USER`, so nobody can register themselves as admin by adding `"role": "admin"` to the JSON (there's a test for this).
* `LoginSerializer`: SimpleJWT's built-in login serializer, extended to put the role inside the token, return basic user info, and (if `REQUIRE_EMAIL_VERIFICATION=True`) block unverified users.
* `LogoutSerializer`: takes the refresh token and blacklists it.
* `PasswordReset...Serializer`: request a reset, then confirm it with `uid` + `token` + new password.

### 4.3.1 How email verification and password reset work (`services.py`)

Django can create a one-time **token** tied to a user (`default_token_generator`). We email a link that contains the user's id (`uid`, base64-encoded) and the `token`. When it comes back we rebuild the user from `uid` and ask "is this token valid for this user?". Tokens expire after 3 days by default and stop working once the password changes. The reset endpoint answers the same way whether or not the email exists, so attackers can't discover who is registered.

### 4.4 `views.py` and `urls.py`

* `RegisterView` uses DRF's ready-made `CreateAPIView`. You write almost nothing!
* `LoginView` and `RefreshView` are SimpleJWT views with our serializer plugged in.
* `throttle_scope = "auth"` connects a view to the strict rate limit.
* `AdminUserViewSet`: lets admins list users, change a role, or suspend someone (`is_active=False`). It lives at `/api/admin/users/`.

Endpoints: `POST /api/auth/register/`, `login/`, `logout/`, `refresh/`, `reset-password/`, plus extras `reset-password/confirm/`, `verify-email/`, `resend-verification/`, `me/`.

---

## Part 5. The `agents` app: register, then wait for approval

**Model `AgentProfile`** has a one-to-one link to `User` (`OneToOneField`) and stores company, licence number, bio, photo and a `status`: `pending`, `approved` or `rejected`. The property `is_verified` is true only when approved. That is the **verification badge**.

**Flow:**

1. `POST /api/agents/register/` creates a `User` with role `agent` **and** an `AgentProfile` with status `pending` in one `transaction.atomic` block (either both are saved or neither). All admins get a notification.
2. The agent can log in but cannot create listings, because `IsApprovedAgent` checks the status.
3. An admin calls `GET /api/admin/agents/pending/` to see the queue, then `PATCH /api/admin/agents/{id}/approve/` (or `reject/`). The agent receives an email and an in-app notification (via `notify()`, see Part 10).

Note the `{id}` is the **AgentProfile id**, not the user id.

In `agents/urls.py` the explicit paths (`agents/register/`, `agents/me/`) are listed **before** the router. Otherwise Django would treat the word "register" as if it were an agent id.

---

## Part 6. The `properties` app: the heart of the system

### 6.1 Models
* **Category**: name + auto-generated **slug** (`"Office Space"` becomes `"office-space"`). The `save()` method builds the slug and adds `-2`, `-3` if it already exists.
* **Property**: every field from the requirements. Highlights:
  * `price` is a `DecimalField` (never use floats for money) with `MinValueValidator(0)`: price cannot be negative.
  * `bedrooms`, `bathrooms`, `square_feet` are `PositiveIntegerField`: cannot go below 0.
  * `property_type` is a `ForeignKey` to Category (`on_delete=PROTECT` stops you deleting a category that still has properties).
  * `status` is a choices field: `for_sale`, `for_rent`, `leased`, `sold`.
  * `amenities` is a `JSONField` (a list like `["pool","gym"]`).
  * `latitude`/`longitude` are validated floats (geolocation).
  * `publication_status`: `draft`, `published`, `suspended`. This is **draft & published mode**, and admins can suspend.
  * `featured`, `is_available`, `views_count` (for analytics), `created_by` (the agent).
* **PropertyImage**: many images per property (`ForeignKey` with `related_name="images"`). The `ImageField` needs **Pillow**, which checks the file is a real image, and we restrict extensions to jpg/jpeg/png/webp.
* **Favorite**: user + property, with `unique_together` so you can't save the same property twice.

### 6.2 `serializers.py`
`PropertySerializer` converts a Property to JSON, including nested `images`, the category name, and the average rating.
* `read_only_fields = ["featured", "views_count", "created_by", ...]`: clients cannot set these. Agents can't make themselves "featured", and `created_by` is filled by the server.
* `validate_<field>` methods hold custom rules: price not negative, amenities must be a list of text, only admins may set `suspended`, latitude and longitude must come together.

`ImageUploadSerializer` validates a **list** of files (`ListField(child=ImageField())`) and enforces a 5 MB limit.

### 6.3 `filters.py`: search and filtering
`PropertyFilter` (django-filter) creates the query parameters: `min_price`, `max_price`, `city`, `state`, `location`, `category`, `status`, `bedrooms`, `bathrooms`, `agent`, `featured`.

`status` is a *custom method filter* so both `?status=rent` (the form used in your requirements doc) and `?status=for_rent` work.

Text search and sorting are configured on the viewset:
```python
search_fields   = ["title", "description", "address", "city", "state", "country", "property_type__name"]
ordering_fields = ["price", "created_at", "bedrooms", ...]
```
`?search=duplex` matches the title *or* the category name, `?ordering=-price` sorts by price descending (minus = descending).

### 6.4 `views.py`: `PropertyViewSet`
A **ModelViewSet** gives you list, create, retrieve, update, partial update and delete from about 5 lines. We customise:

* `get_queryset()`: **who sees what**. Admin sees everything, an agent sees published listings + their own drafts, visitors see only published.
* `get_permissions()`: which permission class applies to which action (read = anyone, create = approved agent, edit/delete = owner or admin, suspend/feature = admin only).
* `perform_create()`: sets `created_by` to the logged-in agent.
* `retrieve()`: adds 1 to `views_count` (not for the owner's own views). This powers analytics.
* `@action` methods create the extra endpoints: `images` (upload many), `images/<id>` (delete one), `mine`, `featured`, `compare`, `suspend`, `reinstate`, `feature`, `unfeature`.

**Uploading images:** send `multipart/form-data` with the field name `images` repeated for each file. In Swagger use the file chooser; in Postman choose Body, then form-data, type File, key `images`, and add several rows with the same key.

`CategoryViewSet`: anyone can read; only admins write. `FavoriteViewSet`: built from small "mixins" (create, list, destroy only) and always filtered to `user=request.user`, so nobody can see or delete another person's favourites.

### 6.5 Pagination
Set globally: 10 results per page. Responses look like `{"count": 25, "next": "...?page=2", "previous": null, "results": [...]}`.

---

## Part 7. `inquiries`: visitor asks, agent answers
* `Inquiry` has name, email, phone, message, the property, an optional `user`, a `status` (`new`/`responded`) and the agent's `response`.
* `POST /api/inquiries/` is open to everyone (visitors don't need an account). The agent is notified by email + in-app.
* `GET /api/inquiries/` shows: admin = all; approved agent = inquiries on **their** properties; normal user = their own. This is done in `get_queryset()`.
* `PATCH /api/inquiries/{id}/respond/`: the agent writes a reply, the status becomes `responded`, and the inquirer is emailed. This is "inquiry tracking".

## Part 8. `inspections`: booking a viewing
* A logged-in user `POST`s a property and a `scheduled_at` date-time. It must be in the future (`validate_scheduled_at`).
* Status starts `pending`. `PATCH /api/inspections/{id}/status/` lets the property's agent/admin set `approved`, `rejected` or `completed`; the person who booked may only `cancel`. The booker is notified of every change.
* **Reminders:** `python manage.py send_inspection_reminders` finds approved inspections in the next 24 h and notifies both sides once. It is a *custom management command*; run it from cron or a scheduler (Celery is a bonus feature).

## Part 9. `reviews`
One model, one rule: a review is for **either** an agent **or** a property (validated in `validate()`), rating 1 to 5, one review per person per target, and you can't review yourself or your own listing. Average rating shows on agents and properties (computed with `Avg`).

## Part 10. `notifications`
* `Notification` model = in-app inbox. Endpoints: `GET /api/notifications/`, `PATCH /api/notifications/{id}/read/`, `PATCH /api/notifications/read-all/`.
* `services.py` has `notify(user, title, message, type)`. It saves a Notification **and** sends an email. Every other app calls this one function instead of repeating email code. That is the "reusable services" requirement.
* Emails print to your terminal in development.

## Part 11. `analytics`
Two read-only views (no models): agent stats (listings, views, inquiries, **conversion rate** = inquiries divided by views x 100) and admin stats (users, agents, listings, five most viewed properties).

---

## Part 12. API documentation
`drf-spectacular` reads your views and serializers and produces an OpenAPI schema automatically:

* Swagger UI: `/api/docs/`. Click **Authorize** and paste your **access token** (just the token, without the word "Bearer"), then try any endpoint.
* ReDoc: `/api/redoc/`.
* Postman: `docs/RealEstateAPI.postman_collection.json` (generated by `tools/make_postman.py` from the schema). Import it, run *auth to login*: a small script saves the token in the collection variable `access_token`, and all other requests use it automatically.
* `@extend_schema` decorators in the views add extra details for Swagger where DRF can't guess.

## Part 13. Testing
`tests/` holds 45 tests, split into: `test_auth.py` (register, login, refresh, logout, verification, reset), `test_agents.py` (approval flow), `test_properties.py` (CRUD, validation, permissions, images, search/filter), `test_engagement.py` (favourites, inquiries, inspections, reviews, notifications, analytics).

Each test uses `APIClient`, which fakes HTTP requests without starting a server, and a **temporary test database** that Django creates and deletes for you. `client_for(user)` logs in as a user without a password step. Run them: `python manage.py test`. To run one file: `python manage.py test tests.test_auth`.

## Part 14. Try it yourself (5-minute walkthrough)
1. `python manage.py migrate` then `python manage.py seed_demo` then `python manage.py runserver`.
2. Open `http://127.0.0.1:8000/api/docs/`.
3. `POST /api/auth/login/` with `agent@example.com` / `Agent#12345`. Copy the `access` value. Click **Authorize** and paste it (only the token, no "Bearer").
4. `GET /api/properties/` (no login needed). Try `?search=duplex`, `?status=rent`, `?ordering=-price`.
5. `POST /api/properties/` as the agent (get the category `id` from `GET /api/categories/`).
6. Log in as `user@example.com`; `POST /api/favorites/` with `{"property": 1}`, then `POST /api/inquiries/`.
7. Log in as admin and call `GET /api/analytics/admin/`.
8. Register a new agent (`POST /api/agents/register/`), then as admin approve them.

## Part 15. Requirement checklist (where each one lives)
| Requirement | Where |
|---|---|
| Register, login, logout, refresh, password reset, email verification, JWT | `accounts/` |
| Roles admin / agent / user, RBAC | `User.role`, `accounts/permissions.py` |
| Agent application + approve/reject + email + badge | `agents/` |
| Categories CRUD + slug | `properties/models.py` (`Category.save`), `CategoryViewSet` |
| Listings CRUD, statuses, draft/published, featured, geolocation, amenities JSON, multiple images | `properties/` |
| Search, filters, sorting, pagination | `properties/filters.py`, viewset attributes, `settings.py` |
| Favourites | `properties/` (`FavoriteViewSet`) |
| Inquiries + agent responses + email | `inquiries/` |
| Inspection booking + approval + reminders | `inspections/` |
| Reviews & average ratings | `reviews/` |
| Notifications | `notifications/` |
| Analytics (agent + admin) | `analytics/` |
| Validation rules (price >= 0, bedrooms >= 0, only approved agents list, valid images, unique email) | models + serializers + permissions |
| Security: JWT, password hashing, RBAC, input validation, rate limiting | `settings.py`, `accounts/` |
| Swagger / ReDoc / Postman | `/api/docs/`, `/api/redoc/`, `docs/` |
| Tests (API, auth, permission, CRUD) | `tests/` |
| ER diagram, DB schema, README | `docs/ERD.md`, `docs/database_schema.sql`, `README.md` |
| Bonus done: property comparison, admin user management, reminder command | see above |

## Part 16. Common problems
* **`ModuleNotFoundError`**: your virtual environment isn't active or you skipped `pip install -r requirements.txt`.
* **`no such table`**: run `python manage.py migrate`.
* **`401 Unauthorized`**: missing/expired token. Log in again (access tokens last 30 minutes).
* **`403 Forbidden`**: logged in but the wrong role, or the agent isn't approved yet.
* **`429 Too Many Requests`**: the rate limit (see Part 3).
* **Image upload 400**: field name must be `images`, and files must be real jpg/png/webp under 5 MB.
* **Changed a model?** `python manage.py makemigrations` then `python manage.py migrate`.
* **Want to start over?** Delete `db.sqlite3` and run `migrate` again.

## Part 17. Be ready to explain (viva questions)
1. What is the difference between authentication and authorization? (Who are you vs what may you do.)
2. Why a custom User model, and why before the first migration?
3. What does a serializer do that a model does not?
4. What is a ViewSet and what does a Router do?
5. Why do we blacklist refresh tokens on logout?
6. Why is `created_by` set in `perform_create` and not accepted from the client?
7. How do you stop agent A from editing agent B's listing? (`IsOwnerOrAdmin` + `get_queryset`.)
8. Why store money as `DecimalField`?

## Part 18. Honest notes / what to improve later
* Images are stored locally. To use Cloudinary see the README.
* Emails go to the console until you configure SMTP.
* Email verification is not enforced at login by default (easier for testing). Set `REQUIRE_EMAIL_VERIFICATION=True` to enforce it.
* Bonus items not implemented: AI recommendations, real-time chat, Redis, Celery, Docker, CI/CD. The structure is ready for them.
* Before deploying: set `DEBUG=False`, a real `SECRET_KEY`, `ALLOWED_HOSTS`, use PostgreSQL, and serve media from Cloudinary/S3.
