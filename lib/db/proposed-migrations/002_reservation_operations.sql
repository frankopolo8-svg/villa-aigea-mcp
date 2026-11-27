-- Proposed migration. Apply only after reviewing 001 and existing PMS.
-- Trusted backend must authenticate the guest and derive p_guest from verified identity.
BEGIN;
CREATE FUNCTION hotel_crm.mutate_reservation(
 p_key uuid, p_guest uuid, p_action text, p_code uuid,
 p_room text, p_in date, p_out date, p_adults integer, p_children integer,
 p_version integer
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, hotel_crm AS $$
DECLARE
 v_hash text; v_key hotel_crm.operation_keys%ROWTYPE;
 v_old hotel_crm.reservations%ROWTYPE; v_new hotel_crm.reservations%ROWTYPE;
 v_capacity integer; v_result jsonb;
BEGIN
 IF p_key IS NULL OR p_guest IS NULL OR p_action IS NULL OR p_action NOT IN ('create','change','cancel') THEN
  RAISE EXCEPTION 'Invalid operation';
 END IF;
 v_hash := jsonb_build_array(p_guest,p_action,p_code,p_room,p_in,p_out,p_adults,p_children,p_version)::text;
 INSERT INTO hotel_crm.operation_keys(operation_key,request_hash) VALUES(p_key,v_hash)
 ON CONFLICT DO NOTHING;
 SELECT * INTO STRICT v_key FROM hotel_crm.operation_keys WHERE operation_key=p_key FOR UPDATE;
 IF v_key.request_hash <> v_hash THEN RAISE EXCEPTION 'Operation key conflict'; END IF;
 IF v_key.result IS NOT NULL THEN RETURN v_key.result; END IF;
 IF p_action <> 'create' THEN
  SELECT * INTO STRICT v_old FROM hotel_crm.reservations
   WHERE booking_code=p_code AND guest_id=p_guest FOR UPDATE;
  IF v_old.status <> 'confirmed' OR p_version IS DISTINCT FROM v_old.version THEN
   RAISE EXCEPTION 'Reservation state changed';
  END IF;
 END IF;
 IF p_action IN ('create','change') THEN
  IF p_in IS NULL OR p_out IS NULL OR p_out <= p_in OR p_in < CURRENT_DATE
   OR p_adults IS NULL OR p_adults < 1 OR p_children IS NULL OR p_children < 0 THEN
   RAISE EXCEPTION 'Invalid stay';
  END IF;
  SELECT capacity INTO STRICT v_capacity FROM hotel_crm.rooms WHERE id=p_room AND active FOR SHARE;
  IF p_adults + p_children > v_capacity THEN RAISE EXCEPTION 'Capacity exceeded'; END IF;
  IF (SELECT count(*) FROM hotel_crm.rates WHERE room_id=p_room AND stay_date>=p_in AND stay_date<p_out) <> p_out-p_in THEN
   RAISE EXCEPTION 'Incomplete rates';
  END IF;
 END IF;
 IF p_action='create' THEN
  INSERT INTO hotel_crm.reservations(guest_id,room_id,check_in,check_out,adults,children,status)
   VALUES(p_guest,p_room,p_in,p_out,p_adults,p_children,'confirmed') RETURNING * INTO v_new;
 ELSIF p_action='change' THEN
  UPDATE hotel_crm.reservations SET room_id=p_room,check_in=p_in,check_out=p_out,
   adults=p_adults,children=p_children,version=version+1,updated_at=now()
   WHERE id=v_old.id RETURNING * INTO v_new;
 ELSE
  UPDATE hotel_crm.reservations SET status='cancelled',version=version+1,updated_at=now()
   WHERE id=v_old.id RETURNING * INTO v_new;
 END IF;
 v_result := jsonb_build_object('booking_code',v_new.booking_code,'status',v_new.status,'version',v_new.version);
 UPDATE hotel_crm.operation_keys SET reservation_id=v_new.id,result=v_result WHERE operation_key=p_key;
 INSERT INTO hotel_crm.reservation_events(reservation_id,operation_key,action,previous_state,next_state)
 VALUES(v_new.id,p_key,p_action,CASE WHEN p_action='create' THEN NULL ELSE to_jsonb(v_old) END,to_jsonb(v_new));
 RETURN v_result;
END;
$$;
REVOKE ALL ON FUNCTION hotel_crm.mutate_reservation(uuid,uuid,text,uuid,text,date,date,integer,integer,integer) FROM PUBLIC;
COMMIT;
