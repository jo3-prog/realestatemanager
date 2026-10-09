-- Generated from SQLite after `migrate` (real estate tables only)
CREATE TABLE "accounts_user" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "password" varchar(128) NOT NULL, "last_login" datetime NULL, "is_superuser" bool NOT NULL, "username" varchar(150) NOT NULL UNIQUE, "first_name" varchar(150) NOT NULL, "last_name" varchar(150) NOT NULL, "is_staff" bool NOT NULL, "is_active" bool NOT NULL, "date_joined" datetime NOT NULL, "email" varchar(254) NOT NULL UNIQUE, "role" varchar(10) NOT NULL, "phone_number" varchar(20) NOT NULL, "is_email_verified" bool NOT NULL);

CREATE TABLE "accounts_user_groups" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "user_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED, "group_id" integer NOT NULL REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "accounts_user_user_permissions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "user_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED, "permission_id" integer NOT NULL REFERENCES "auth_permission" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE UNIQUE INDEX "accounts_user_groups_user_id_group_id_59c0b32f_uniq" ON "accounts_user_groups" ("user_id", "group_id");

CREATE INDEX "accounts_user_groups_user_id_52b62117" ON "accounts_user_groups" ("user_id");

CREATE INDEX "accounts_user_groups_group_id_bd11a704" ON "accounts_user_groups" ("group_id");

CREATE UNIQUE INDEX "accounts_user_user_permissions_user_id_permission_id_2ab516c2_uniq" ON "accounts_user_user_permissions" ("user_id", "permission_id");

CREATE INDEX "accounts_user_user_permissions_user_id_e4f0a161" ON "accounts_user_user_permissions" ("user_id");

CREATE INDEX "accounts_user_user_permissions_permission_id_113bb443" ON "accounts_user_user_permissions" ("permission_id");

CREATE TABLE "agents_agentprofile" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "company_name" varchar(150) NOT NULL, "license_number" varchar(50) NOT NULL, "bio" text NOT NULL, "profile_photo" varchar(100) NULL, "status" varchar(10) NOT NULL, "rejection_reason" text NOT NULL, "created_at" datetime NOT NULL, "reviewed_at" datetime NULL, "user_id" bigint NOT NULL UNIQUE REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "properties_category" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL UNIQUE, "slug" varchar(120) NOT NULL UNIQUE, "description" text NOT NULL);

CREATE TABLE "properties_property" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "title" varchar(200) NOT NULL, "description" text NOT NULL, "price" decimal NOT NULL, "status" varchar(10) NOT NULL, "bedrooms" integer unsigned NOT NULL CHECK ("bedrooms" >= 0), "bathrooms" integer unsigned NOT NULL CHECK ("bathrooms" >= 0), "square_feet" integer unsigned NOT NULL CHECK ("square_feet" >= 0), "address" varchar(255) NOT NULL, "city" varchar(100) NOT NULL, "state" varchar(100) NOT NULL, "country" varchar(100) NOT NULL, "latitude" real NULL, "longitude" real NULL, "amenities" text NOT NULL CHECK ((JSON_VALID("amenities") OR "amenities" IS NULL)), "featured" bool NOT NULL, "is_available" bool NOT NULL, "publication_status" varchar(10) NOT NULL, "views_count" integer unsigned NOT NULL CHECK ("views_count" >= 0), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "created_by_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED, "property_type_id" bigint NOT NULL REFERENCES "properties_category" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "properties_propertyimage" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "image" varchar(100) NOT NULL, "caption" varchar(150) NOT NULL, "is_primary" bool NOT NULL, "uploaded_at" datetime NOT NULL, "property_id" bigint NOT NULL REFERENCES "properties_property" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "properties_favorite" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "created_at" datetime NOT NULL, "user_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED, "property_id" bigint NOT NULL REFERENCES "properties_property" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE INDEX "properties_property_created_by_id_7c8eb873" ON "properties_property" ("created_by_id");

CREATE INDEX "properties_property_property_type_id_21d12070" ON "properties_property" ("property_type_id");

CREATE INDEX "properties_propertyimage_property_id_883194e7" ON "properties_propertyimage" ("property_id");

CREATE UNIQUE INDEX "properties_favorite_user_id_property_id_22403a1e_uniq" ON "properties_favorite" ("user_id", "property_id");

CREATE INDEX "properties_favorite_user_id_7e4c50a0" ON "properties_favorite" ("user_id");

CREATE INDEX "properties_favorite_property_id_ba845687" ON "properties_favorite" ("property_id");

CREATE TABLE "inquiries_inquiry" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(120) NOT NULL, "email" varchar(254) NOT NULL, "phone_number" varchar(20) NOT NULL, "message" text NOT NULL, "status" varchar(10) NOT NULL, "response" text NOT NULL, "responded_at" datetime NULL, "created_at" datetime NOT NULL, "property_id" bigint NOT NULL REFERENCES "properties_property" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" bigint NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE INDEX "inquiries_inquiry_property_id_6f718227" ON "inquiries_inquiry" ("property_id");

CREATE INDEX "inquiries_inquiry_user_id_dda1021a" ON "inquiries_inquiry" ("user_id");

CREATE TABLE "inspections_inspectionbooking" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "scheduled_at" datetime NOT NULL, "note" text NOT NULL, "status" varchar(10) NOT NULL, "reminder_sent" bool NOT NULL, "created_at" datetime NOT NULL, "property_id" bigint NOT NULL REFERENCES "properties_property" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE INDEX "inspections_inspectionbooking_property_id_7ab6e45d" ON "inspections_inspectionbooking" ("property_id");

CREATE INDEX "inspections_inspectionbooking_user_id_f84f7186" ON "inspections_inspectionbooking" ("user_id");

CREATE TABLE "notifications_notification" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "title" varchar(200) NOT NULL, "message" text NOT NULL, "notification_type" varchar(20) NOT NULL, "is_read" bool NOT NULL, "created_at" datetime NOT NULL, "user_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE INDEX "notifications_notification_user_id_b5e8c0ff" ON "notifications_notification" ("user_id");

CREATE TABLE "reviews_review" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "rating" smallint unsigned NOT NULL CHECK ("rating" >= 0), "comment" text NOT NULL, "created_at" datetime NOT NULL, "agent_id" bigint NULL REFERENCES "agents_agentprofile" ("id") DEFERRABLE INITIALLY DEFERRED, "property_id" bigint NULL REFERENCES "properties_property" ("id") DEFERRABLE INITIALLY DEFERRED, "reviewer_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE INDEX "reviews_review_agent_id_35a50647" ON "reviews_review" ("agent_id");

CREATE INDEX "reviews_review_property_id_c73a0b24" ON "reviews_review" ("property_id");

CREATE INDEX "reviews_review_reviewer_id_29fc8a19" ON "reviews_review" ("reviewer_id");
