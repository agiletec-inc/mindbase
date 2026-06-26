-- Plain-Postgres compatibility shim (runs first by filename sort order).
--
-- The initial schema migration declares RLS policies that call auth.role(),
-- a Supabase built-in. On a vanilla postgres / pgvector image the auth schema
-- and function do not exist, so CREATE POLICY aborts and the whole init stops
-- with: ERROR: schema "auth" does not exist.
--
-- Create a permissive stub ONLY when it is absent. On real Supabase the native
-- auth.role() already exists, so the DO block is a no-op and native auth is
-- left untouched. This is a single-user local store, so a constant
-- 'service_role' is the correct effective behavior.
CREATE SCHEMA IF NOT EXISTS auth;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'auth' AND p.proname = 'role'
  ) THEN
    CREATE FUNCTION auth.role()
      RETURNS text
      LANGUAGE sql
      STABLE
    AS $fn$ SELECT 'service_role'::text $fn$;
  END IF;
END $$;
