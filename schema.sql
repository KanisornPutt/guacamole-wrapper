--
-- PostgreSQL database dump
--

\restrict QOclwkK9IzJo61L8Iutc1b30hOkKgMtQ8y1PP2b9OKjYY633kLSH1ZSmFDeNOye

-- Dumped from database version 15.17 (Debian 15.17-1.pgdg13+1)
-- Dumped by pg_dump version 15.17 (Debian 15.17-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: guacadmin
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO guacadmin;

--
-- Name: users; Type: TABLE; Schema: public; Owner: guacadmin
--

CREATE TABLE public.users (
    external_user_id character varying(36) NOT NULL,
    username character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.users OWNER TO guacadmin;

--
-- Name: workspaces; Type: TABLE; Schema: public; Owner: guacadmin
--

CREATE TABLE public.workspaces (
    external_instance_id character varying(36) NOT NULL,
    user_id character varying(36),
    guacamole_connection_id integer,
    workspace_name character varying(255),
    floating_ip character varying(45),
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    os_username character varying(255),
    os_password character varying(255),
    guacamole_group_id integer
);


ALTER TABLE public.workspaces OWNER TO guacadmin;

--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: guacadmin
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: guacadmin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (external_user_id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: guacadmin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: workspaces workspaces_guacamole_connection_id_key; Type: CONSTRAINT; Schema: public; Owner: guacadmin
--

ALTER TABLE ONLY public.workspaces
    ADD CONSTRAINT workspaces_guacamole_connection_id_key UNIQUE (guacamole_connection_id);


--
-- Name: workspaces workspaces_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: guacadmin
--

ALTER TABLE ONLY public.workspaces
    ADD CONSTRAINT workspaces_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(external_user_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict QOclwkK9IzJo61L8Iutc1b30hOkKgMtQ8y1PP2b9OKjYY633kLSH1ZSmFDeNOye

