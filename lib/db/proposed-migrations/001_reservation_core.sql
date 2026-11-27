-- Proposed migration only. Review against existing PMS schema before applying.
BEGIN;
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE SCHEMA hotel_crm;
CREATE TABLE hotel_crm.guests (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 full_name text NOT NULL CHECK (length(trim(full_name)) > 0),
 email text NOT NULL, phone text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE hotel_crm.rooms (
 id text PRIMARY KEY, category text NOT NULL,
 capacity integer NOT NULL CHECK (capacity > 0),
 active boolean NOT NULL DEFAULT true
);
CREATE TABLE hotel_crm.reservations (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 booking_code uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
 guest_id uuid NOT NULL REFERENCES hotel_crm.guests(id),
 room_id text NOT NULL REFERENCES hotel_crm.rooms(id),
 check_in date NOT NULL, check_out date NOT NULL,
 adults integer NOT NULL CHECK (adults > 0),
 children integer NOT NULL DEFAULT 0 CHECK (children >= 0),
 status text NOT NULL CHECK (status IN ('confirmed','cancelled')),
 version integer NOT NULL DEFAULT 1,
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now(),
 CHECK (check_out > check_in),
 EXCLUDE USING gist (room_id WITH =, daterange(check_in,check_out,'[)') WITH &&)
 WHERE (status = 'confirmed')
);
CREATE TABLE hotel_crm.rates (
 room_id text NOT NULL REFERENCES hotel_crm.rooms(id),
 stay_date date NOT NULL, amount numeric(12,2) NOT NULL CHECK (amount >= 0),
 currency char(3) NOT NULL, PRIMARY KEY(room_id,stay_date)
);
CREATE TABLE hotel_crm.operation_keys (
 operation_key uuid PRIMARY KEY,
 request_hash text NOT NULL,
 reservation_id uuid REFERENCES hotel_crm.reservations(id),
 result jsonb, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE hotel_crm.reservation_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 reservation_id uuid NOT NULL REFERENCES hotel_crm.reservations(id),
 operation_key uuid NOT NULL UNIQUE REFERENCES hotel_crm.operation_keys(operation_key),
 action text NOT NULL CHECK(action IN ('create','change','cancel')),
 previous_state jsonb, next_state jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
-- No guest-facing access: server authorization and transaction handlers required.
REVOKE ALL ON SCHEMA hotel_crm FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA hotel_crm FROM PUBLIC;
COMMIT;
