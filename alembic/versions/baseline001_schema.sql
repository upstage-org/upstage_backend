--
-- PostgreSQL database dump
--


-- Dumped from database version 18.2 (Debian 18.2-1.pgdg13+1)
-- Dumped by pg_dump version 18.2 (Debian 18.2-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
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
-- Name: admin_one_time_totp_qr_url; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_one_time_totp_qr_url (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    url text NOT NULL,
    code text NOT NULL,
    recorded_time timestamp without time zone NOT NULL,
    active boolean NOT NULL
);


--
-- Name: admin_one_time_totp_qr_url_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.admin_one_time_totp_qr_url_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: admin_one_time_totp_qr_url_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.admin_one_time_totp_qr_url_id_seq OWNED BY public.admin_one_time_totp_qr_url.id;


--
-- Name: apple_profile; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.apple_profile (
    id bigint NOT NULL,
    user_id integer,
    apple_id text DEFAULT ''::text NOT NULL,
    apple_phone text,
    apple_email text,
    apple_first_name text,
    apple_last_name text,
    apple_username text,
    other_profile_json text,
    received_datetime timestamp with time zone DEFAULT (now() AT TIME ZONE 'utc'::text)
);


--
-- Name: apple_profile_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.apple_profile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: apple_profile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.apple_profile_id_seq OWNED BY public.apple_profile.id;


--
-- Name: asset; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.asset (
    id bigint NOT NULL,
    name text NOT NULL,
    asset_type_id integer NOT NULL,
    owner_id integer NOT NULL,
    description text,
    file_location text NOT NULL,
    copyright_level integer NOT NULL,
    created_on timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text),
    updated_on timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text),
    size bigint NOT NULL,
    dormant boolean
);


--
-- Name: asset_attribute; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.asset_attribute (
    id bigint NOT NULL,
    asset_id integer NOT NULL,
    name text NOT NULL,
    description text,
    created_on timestamp with time zone DEFAULT (now() AT TIME ZONE 'utc'::text)
);


--
-- Name: asset_attribute_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.asset_attribute_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: asset_attribute_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.asset_attribute_id_seq OWNED BY public.asset_attribute.id;


--
-- Name: asset_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.asset_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: asset_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.asset_id_seq OWNED BY public.asset.id;


--
-- Name: asset_license; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.asset_license (
    id bigint NOT NULL,
    asset_id integer NOT NULL,
    created_on timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text),
    level integer NOT NULL,
    permissions text
);


--
-- Name: asset_license_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.asset_license_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: asset_license_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.asset_license_id_seq OWNED BY public.asset_license.id;


--
-- Name: asset_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.asset_type (
    id bigint NOT NULL,
    name text NOT NULL,
    description text,
    file_location text NOT NULL,
    created_on timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text)
);


--
-- Name: asset_type_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.asset_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: asset_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.asset_type_id_seq OWNED BY public.asset_type.id;


--
-- Name: asset_usage; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.asset_usage (
    id bigint NOT NULL,
    asset_id integer NOT NULL,
    user_id integer NOT NULL,
    approved boolean NOT NULL,
    note text,
    created_on timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text),
    owner_seen boolean DEFAULT false NOT NULL,
    requester_seen boolean DEFAULT false NOT NULL
);


--
-- Name: asset_usage_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.asset_usage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: asset_usage_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.asset_usage_id_seq OWNED BY public.asset_usage.id;


--
-- Name: config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.config (
    id bigint NOT NULL,
    name text NOT NULL,
    value text,
    created_on timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text)
);


--
-- Name: config_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.config_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.config_id_seq OWNED BY public.config.id;


--
-- Name: connection_stats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.connection_stats (
    id integer NOT NULL,
    connected_id character varying,
    mqtt_timestamp timestamp without time zone,
    topic character varying,
    payload json,
    created timestamp without time zone
);


--
-- Name: connection_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.connection_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: connection_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.connection_stats_id_seq OWNED BY public.connection_stats.id;


--
-- Name: events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 2147483647
    CACHE 1;


--
-- Name: events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.events (
    id integer DEFAULT nextval('public.events_id_seq'::regclass) NOT NULL,
    performance_id integer,
    topic text NOT NULL,
    mqtt_timestamp double precision NOT NULL,
    created timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    payload json NOT NULL
);


--
-- Name: facebook_profile; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.facebook_profile (
    id bigint NOT NULL,
    user_id integer,
    facebook_id text DEFAULT ''::text NOT NULL,
    facebook_phone text,
    facebook_email text,
    facebook_first_name text,
    facebook_last_name text,
    facebook_username text,
    other_profile_json text,
    received_datetime timestamp with time zone DEFAULT (now() AT TIME ZONE 'utc'::text)
);


--
-- Name: facebook_profile_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.facebook_profile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: facebook_profile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.facebook_profile_id_seq OWNED BY public.facebook_profile.id;


--
-- Name: google_profile; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.google_profile (
    id bigint NOT NULL,
    user_id integer,
    google_id text DEFAULT ''::text NOT NULL,
    google_phone text,
    google_email text,
    google_first_name text,
    google_last_name text,
    google_username text,
    other_profile_json text,
    received_datetime timestamp with time zone DEFAULT (now() AT TIME ZONE 'utc'::text)
);


--
-- Name: google_profile_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.google_profile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: google_profile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.google_profile_id_seq OWNED BY public.google_profile.id;


--
-- Name: jwt_no_list; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.jwt_no_list (
    id bigint NOT NULL,
    token text NOT NULL,
    token_type text NOT NULL,
    remove_after timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text)
);


--
-- Name: jwt_no_list_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.jwt_no_list_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: jwt_no_list_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.jwt_no_list_id_seq OWNED BY public.jwt_no_list.id;


--
-- Name: live_performance_mqtt_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.live_performance_mqtt_config (
    id bigint NOT NULL,
    name text NOT NULL,
    owner_id integer DEFAULT 0 NOT NULL,
    ip_address text NOT NULL,
    websocket_port integer DEFAULT 0 NOT NULL,
    webclient_port integer DEFAULT 0 NOT NULL,
    topic_name text NOT NULL,
    username text NOT NULL,
    password text NOT NULL,
    created_on timestamp with time zone DEFAULT (now() AT TIME ZONE 'utc'::text),
    expires_on timestamp with time zone,
    performance_id integer NOT NULL
);


--
-- Name: live_performance_mqtt_config_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.live_performance_mqtt_config_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: live_performance_mqtt_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.live_performance_mqtt_config_id_seq OWNED BY public.live_performance_mqtt_config.id;


--
-- Name: media_tag; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.media_tag (
    id bigint NOT NULL,
    asset_id integer NOT NULL,
    tag_id integer NOT NULL,
    created_on timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text)
);


--
-- Name: media_tag_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.media_tag_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: media_tag_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.media_tag_id_seq OWNED BY public.media_tag.id;


--
-- Name: parent_stage; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parent_stage (
    id bigint NOT NULL,
    stage_id integer NOT NULL,
    child_asset_id integer NOT NULL,
    exit_animation character varying,
    exit_speed integer
);


--
-- Name: parent_stage_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.parent_stage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: parent_stage_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.parent_stage_id_seq OWNED BY public.parent_stage.id;


--
-- Name: performance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.performance (
    id bigint NOT NULL,
    name text,
    description text,
    stage_id integer NOT NULL,
    created_on timestamp with time zone DEFAULT (now() AT TIME ZONE 'utc'::text),
    saved_on timestamp with time zone,
    recording boolean DEFAULT false NOT NULL
);


--
-- Name: performance_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.performance_config (
    id bigint NOT NULL,
    name character varying NOT NULL,
    owner_id integer NOT NULL,
    description text NOT NULL,
    splash_screen_text text,
    splash_screen_animation_urls text,
    created_on timestamp without time zone NOT NULL,
    expires_on timestamp without time zone NOT NULL
);


--
-- Name: performance_config_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.performance_config_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: performance_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.performance_config_id_seq OWNED BY public.performance_config.id;


--
-- Name: performance_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.performance_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: performance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.performance_id_seq OWNED BY public.performance.id;


--
-- Name: receive_stats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.receive_stats (
    id integer NOT NULL,
    received_id character varying,
    mqtt_timestamp timestamp without time zone,
    topic character varying,
    payload json,
    created timestamp without time zone
);


--
-- Name: receive_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.receive_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: receive_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.receive_stats_id_seq OWNED BY public.receive_stats.id;


--
-- Name: scene; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scene (
    id bigint NOT NULL,
    name text NOT NULL,
    scene_order integer DEFAULT 0 NOT NULL,
    scene_preview text,
    payload text NOT NULL,
    created_on timestamp with time zone DEFAULT (now() AT TIME ZONE 'utc'::text),
    active boolean DEFAULT true NOT NULL,
    owner_id integer DEFAULT 0 NOT NULL,
    stage_id integer NOT NULL
);


--
-- Name: scene_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.scene_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: scene_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.scene_id_seq OWNED BY public.scene.id;


--
-- Name: stage; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stage (
    id bigint NOT NULL,
    name text NOT NULL,
    description text,
    owner_id integer NOT NULL,
    file_location character varying NOT NULL,
    created_on timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text),
    last_access timestamp without time zone
);


--
-- Name: stage_attribute; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stage_attribute (
    id bigint NOT NULL,
    stage_id integer NOT NULL,
    name text NOT NULL,
    description text,
    created_on timestamp with time zone DEFAULT (now() AT TIME ZONE 'utc'::text),
    CONSTRAINT stage_attribute_visibility_binary CHECK (((name <> 'visibility'::text) OR (description = ANY (ARRAY['true'::text, 'false'::text]))))
);


--
-- Name: stage_attribute_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.stage_attribute_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stage_attribute_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.stage_attribute_id_seq OWNED BY public.stage_attribute.id;


--
-- Name: stage_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.stage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stage_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.stage_id_seq OWNED BY public.stage.id;


--
-- Name: stage_statistics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stage_statistics (
    stage_url character varying NOT NULL,
    players integer DEFAULT 0 NOT NULL,
    audiences integer DEFAULT 0 NOT NULL,
    updated_on timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: tag; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tag (
    id bigint NOT NULL,
    name text NOT NULL,
    color text,
    created_on timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text)
);


--
-- Name: tag_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tag_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tag_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tag_id_seq OWNED BY public.tag.id;


--
-- Name: upstage_user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.upstage_user (
    id bigint NOT NULL,
    username text NOT NULL,
    password text NOT NULL,
    email text,
    bin_name text NOT NULL,
    role integer NOT NULL,
    first_name text,
    last_name text,
    display_name text,
    active boolean NOT NULL,
    firebase_pushnot_id text,
    created_on timestamp with time zone DEFAULT (now() AT TIME ZONE 'utc'::text),
    deactivated_on timestamp with time zone,
    upload_limit integer,
    intro text,
    can_send_email boolean NOT NULL,
    last_login timestamp with time zone
);


--
-- Name: upstage_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.upstage_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: upstage_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.upstage_user_id_seq OWNED BY public.upstage_user.id;


--
-- Name: user_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_session (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    access_token text NOT NULL,
    refresh_token text NOT NULL,
    recorded_time timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL,
    app_version text,
    app_os_type text,
    app_os_version text,
    app_device text
);


--
-- Name: user_session_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_session_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_session_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_session_id_seq OWNED BY public.user_session.id;


--
-- Name: admin_one_time_totp_qr_url id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_one_time_totp_qr_url ALTER COLUMN id SET DEFAULT nextval('public.admin_one_time_totp_qr_url_id_seq'::regclass);


--
-- Name: apple_profile id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.apple_profile ALTER COLUMN id SET DEFAULT nextval('public.apple_profile_id_seq'::regclass);


--
-- Name: asset id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset ALTER COLUMN id SET DEFAULT nextval('public.asset_id_seq'::regclass);


--
-- Name: asset_attribute id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_attribute ALTER COLUMN id SET DEFAULT nextval('public.asset_attribute_id_seq'::regclass);


--
-- Name: asset_license id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_license ALTER COLUMN id SET DEFAULT nextval('public.asset_license_id_seq'::regclass);


--
-- Name: asset_type id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_type ALTER COLUMN id SET DEFAULT nextval('public.asset_type_id_seq'::regclass);


--
-- Name: asset_usage id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_usage ALTER COLUMN id SET DEFAULT nextval('public.asset_usage_id_seq'::regclass);


--
-- Name: config id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.config ALTER COLUMN id SET DEFAULT nextval('public.config_id_seq'::regclass);


--
-- Name: connection_stats id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connection_stats ALTER COLUMN id SET DEFAULT nextval('public.connection_stats_id_seq'::regclass);


--
-- Name: facebook_profile id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facebook_profile ALTER COLUMN id SET DEFAULT nextval('public.facebook_profile_id_seq'::regclass);


--
-- Name: google_profile id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.google_profile ALTER COLUMN id SET DEFAULT nextval('public.google_profile_id_seq'::regclass);


--
-- Name: jwt_no_list id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jwt_no_list ALTER COLUMN id SET DEFAULT nextval('public.jwt_no_list_id_seq'::regclass);


--
-- Name: live_performance_mqtt_config id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.live_performance_mqtt_config ALTER COLUMN id SET DEFAULT nextval('public.live_performance_mqtt_config_id_seq'::regclass);


--
-- Name: media_tag id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_tag ALTER COLUMN id SET DEFAULT nextval('public.media_tag_id_seq'::regclass);


--
-- Name: parent_stage id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_stage ALTER COLUMN id SET DEFAULT nextval('public.parent_stage_id_seq'::regclass);


--
-- Name: performance id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.performance ALTER COLUMN id SET DEFAULT nextval('public.performance_id_seq'::regclass);


--
-- Name: performance_config id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.performance_config ALTER COLUMN id SET DEFAULT nextval('public.performance_config_id_seq'::regclass);


--
-- Name: receive_stats id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.receive_stats ALTER COLUMN id SET DEFAULT nextval('public.receive_stats_id_seq'::regclass);


--
-- Name: scene id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scene ALTER COLUMN id SET DEFAULT nextval('public.scene_id_seq'::regclass);


--
-- Name: stage id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stage ALTER COLUMN id SET DEFAULT nextval('public.stage_id_seq'::regclass);


--
-- Name: stage_attribute id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stage_attribute ALTER COLUMN id SET DEFAULT nextval('public.stage_attribute_id_seq'::regclass);


--
-- Name: tag id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tag ALTER COLUMN id SET DEFAULT nextval('public.tag_id_seq'::regclass);


--
-- Name: upstage_user id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upstage_user ALTER COLUMN id SET DEFAULT nextval('public.upstage_user_id_seq'::regclass);


--
-- Name: user_session id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_session ALTER COLUMN id SET DEFAULT nextval('public.user_session_id_seq'::regclass);


--
-- Name: admin_one_time_totp_qr_url admin_one_time_totp_qr_url_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_one_time_totp_qr_url
    ADD CONSTRAINT admin_one_time_totp_qr_url_pkey PRIMARY KEY (id);


--
-- Name: admin_one_time_totp_qr_url admin_one_time_totp_qr_url_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_one_time_totp_qr_url
    ADD CONSTRAINT admin_one_time_totp_qr_url_user_id_key UNIQUE (user_id);


--
-- Name: apple_profile apple_profile_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.apple_profile
    ADD CONSTRAINT apple_profile_pkey PRIMARY KEY (id);


--
-- Name: asset_attribute asset_attribute_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_attribute
    ADD CONSTRAINT asset_attribute_pkey PRIMARY KEY (id);


--
-- Name: asset_license asset_license_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_license
    ADD CONSTRAINT asset_license_pkey PRIMARY KEY (id);


--
-- Name: asset asset_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset
    ADD CONSTRAINT asset_pkey PRIMARY KEY (id);


--
-- Name: asset_type asset_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_type
    ADD CONSTRAINT asset_type_pkey PRIMARY KEY (id);


--
-- Name: asset_usage asset_usage_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_usage
    ADD CONSTRAINT asset_usage_pkey PRIMARY KEY (id);


--
-- Name: config config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.config
    ADD CONSTRAINT config_pkey PRIMARY KEY (id);


--
-- Name: connection_stats connection_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connection_stats
    ADD CONSTRAINT connection_stats_pkey PRIMARY KEY (id);


--
-- Name: events events_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_id PRIMARY KEY (id);


--
-- Name: facebook_profile facebook_profile_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facebook_profile
    ADD CONSTRAINT facebook_profile_pkey PRIMARY KEY (id);


--
-- Name: google_profile google_profile_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.google_profile
    ADD CONSTRAINT google_profile_pkey PRIMARY KEY (id);


--
-- Name: jwt_no_list jwt_no_list_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jwt_no_list
    ADD CONSTRAINT jwt_no_list_pkey PRIMARY KEY (id);


--
-- Name: jwt_no_list jwt_no_list_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jwt_no_list
    ADD CONSTRAINT jwt_no_list_token_key UNIQUE (token);


--
-- Name: live_performance_mqtt_config live_performance_mqtt_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.live_performance_mqtt_config
    ADD CONSTRAINT live_performance_mqtt_config_pkey PRIMARY KEY (id);


--
-- Name: live_performance_mqtt_config live_performance_mqtt_config_topic_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.live_performance_mqtt_config
    ADD CONSTRAINT live_performance_mqtt_config_topic_name_key UNIQUE (topic_name);


--
-- Name: media_tag media_tag_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_tag
    ADD CONSTRAINT media_tag_pkey PRIMARY KEY (id);


--
-- Name: parent_stage parent_stage_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_stage
    ADD CONSTRAINT parent_stage_pkey PRIMARY KEY (id);


--
-- Name: performance_config performance_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.performance_config
    ADD CONSTRAINT performance_config_pkey PRIMARY KEY (id);


--
-- Name: performance performance_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.performance
    ADD CONSTRAINT performance_pkey PRIMARY KEY (id);


--
-- Name: receive_stats receive_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.receive_stats
    ADD CONSTRAINT receive_stats_pkey PRIMARY KEY (id);


--
-- Name: scene scene_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scene
    ADD CONSTRAINT scene_pkey PRIMARY KEY (id);


--
-- Name: stage_attribute stage_attribute_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stage_attribute
    ADD CONSTRAINT stage_attribute_pkey PRIMARY KEY (id);


--
-- Name: stage stage_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stage
    ADD CONSTRAINT stage_pkey PRIMARY KEY (id);


--
-- Name: stage_statistics stage_statistics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stage_statistics
    ADD CONSTRAINT stage_statistics_pkey PRIMARY KEY (stage_url);


--
-- Name: tag tag_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tag
    ADD CONSTRAINT tag_pkey PRIMARY KEY (id);


--
-- Name: upstage_user upstage_user_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upstage_user
    ADD CONSTRAINT upstage_user_email_key UNIQUE (email);


--
-- Name: upstage_user upstage_user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upstage_user
    ADD CONSTRAINT upstage_user_pkey PRIMARY KEY (id);


--
-- Name: upstage_user upstage_user_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upstage_user
    ADD CONSTRAINT upstage_user_username_key UNIQUE (username);


--
-- Name: user_session user_session_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_session
    ADD CONSTRAINT user_session_pkey PRIMARY KEY (id);


--
-- Name: events_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX events_created ON public.events USING btree (created);


--
-- Name: events_performance_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX events_performance_id ON public.events USING btree (performance_id);


--
-- Name: ix_admin_one_time_totp_qr_url_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_admin_one_time_totp_qr_url_active ON public.admin_one_time_totp_qr_url USING btree (active);


--
-- Name: ix_admin_one_time_totp_qr_url_recorded_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_admin_one_time_totp_qr_url_recorded_time ON public.admin_one_time_totp_qr_url USING btree (recorded_time);


--
-- Name: ix_connection_stats_connected_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_connection_stats_connected_id ON public.connection_stats USING btree (connected_id);


--
-- Name: ix_connection_stats_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_connection_stats_created ON public.connection_stats USING btree (created);


--
-- Name: ix_connection_stats_mqtt_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_connection_stats_mqtt_timestamp ON public.connection_stats USING btree (mqtt_timestamp);


--
-- Name: ix_receive_stats_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_receive_stats_created ON public.receive_stats USING btree (created);


--
-- Name: ix_receive_stats_mqtt_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_receive_stats_mqtt_timestamp ON public.receive_stats USING btree (mqtt_timestamp);


--
-- Name: ix_receive_stats_received_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_receive_stats_received_id ON public.receive_stats USING btree (received_id);


--
-- Name: scene_scene_order_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX scene_scene_order_idx ON public.scene USING btree (scene_order);


--
-- Name: admin_one_time_totp_qr_url admin_one_time_totp_qr_url_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_one_time_totp_qr_url
    ADD CONSTRAINT admin_one_time_totp_qr_url_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.upstage_user(id);


--
-- Name: apple_profile apple_profile_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.apple_profile
    ADD CONSTRAINT apple_profile_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.upstage_user(id);


--
-- Name: asset asset_asset_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset
    ADD CONSTRAINT asset_asset_type_id_fkey FOREIGN KEY (asset_type_id) REFERENCES public.asset_type(id);


--
-- Name: asset_attribute asset_attribute_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_attribute
    ADD CONSTRAINT asset_attribute_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.asset(id);


--
-- Name: asset_license asset_license_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_license
    ADD CONSTRAINT asset_license_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.asset(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: asset asset_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset
    ADD CONSTRAINT asset_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.upstage_user(id);


--
-- Name: asset_usage asset_usage_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_usage
    ADD CONSTRAINT asset_usage_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.asset(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: asset_usage asset_usage_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_usage
    ADD CONSTRAINT asset_usage_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.upstage_user(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: facebook_profile facebook_profile_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facebook_profile
    ADD CONSTRAINT facebook_profile_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.upstage_user(id);


--
-- Name: google_profile google_profile_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.google_profile
    ADD CONSTRAINT google_profile_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.upstage_user(id);


--
-- Name: live_performance_mqtt_config live_performance_mqtt_config_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.live_performance_mqtt_config
    ADD CONSTRAINT live_performance_mqtt_config_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.upstage_user(id);


--
-- Name: live_performance_mqtt_config live_performance_mqtt_config_performance_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.live_performance_mqtt_config
    ADD CONSTRAINT live_performance_mqtt_config_performance_id_fkey FOREIGN KEY (performance_id) REFERENCES public.performance(id);


--
-- Name: media_tag media_tag_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_tag
    ADD CONSTRAINT media_tag_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.asset(id);


--
-- Name: media_tag media_tag_tag_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_tag
    ADD CONSTRAINT media_tag_tag_id_fkey FOREIGN KEY (tag_id) REFERENCES public.tag(id);


--
-- Name: parent_stage parent_stage_child_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_stage
    ADD CONSTRAINT parent_stage_child_asset_id_fkey FOREIGN KEY (child_asset_id) REFERENCES public.asset(id);


--
-- Name: parent_stage parent_stage_stage_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_stage
    ADD CONSTRAINT parent_stage_stage_id_fkey FOREIGN KEY (stage_id) REFERENCES public.stage(id);


--
-- Name: performance_config performance_config_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.performance_config
    ADD CONSTRAINT performance_config_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.upstage_user(id);


--
-- Name: performance performance_stage_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.performance
    ADD CONSTRAINT performance_stage_id_fkey FOREIGN KEY (stage_id) REFERENCES public.stage(id);


--
-- Name: scene scene_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scene
    ADD CONSTRAINT scene_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.upstage_user(id);


--
-- Name: scene scene_stage_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scene
    ADD CONSTRAINT scene_stage_id_fkey FOREIGN KEY (stage_id) REFERENCES public.stage(id);


--
-- Name: stage_attribute stage_attribute_stage_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stage_attribute
    ADD CONSTRAINT stage_attribute_stage_id_fkey FOREIGN KEY (stage_id) REFERENCES public.stage(id);


--
-- Name: stage stage_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stage
    ADD CONSTRAINT stage_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.upstage_user(id);


--
-- Name: user_session user_session_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_session
    ADD CONSTRAINT user_session_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.upstage_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- PostgreSQL database dump complete
--
