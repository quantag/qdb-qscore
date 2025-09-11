--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4
-- Dumped by pg_dump version 17.2

-- Started on 2025-07-11 13:01:24

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
-- TOC entry 218 (class 1259 OID 24584)
-- Name: jobs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.jobs (
    uid uuid NOT NULL,
    user_id uuid NOT NULL,
    provider_id uuid,
    "time" bigint,
    status bigint,
    status_str character varying,
    input character varying,
    results character varying,
    start_time time with time zone,
    end_time time with time zone,
    instance character varying,
    mode character varying,
    qpu character varying,
    usage bigint,
    region character varying,
    job_id character varying
);


ALTER TABLE public.jobs OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 24589)
-- Name: providers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.providers (
    uid uuid NOT NULL,
    name character varying NOT NULL
);


ALTER TABLE public.providers OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 24601)
-- Name: subscriptions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.subscriptions (
    uid uuid NOT NULL,
    name character varying NOT NULL
);


ALTER TABLE public.subscriptions OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 24610)
-- Name: trans_internal; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.trans_internal (
    uid uuid NOT NULL,
    job_id uuid NOT NULL,
    user_id uuid NOT NULL
);


ALTER TABLE public.trans_internal OWNER TO postgres;

--
-- TOC entry 4929 (class 0 OID 0)
-- Dependencies: 222
-- Name: TABLE trans_internal; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.trans_internal IS 'internal transactions';


--
-- TOC entry 220 (class 1259 OID 24596)
-- Name: transactions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.transactions (
    uid uuid NOT NULL,
    user_id uuid NOT NULL,
    date time with time zone NOT NULL,
    amount bigint NOT NULL
);


ALTER TABLE public.transactions OWNER TO postgres;

--
-- TOC entry 217 (class 1259 OID 24577)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    uid uuid NOT NULL,
    firstname character varying,
    lastname character varying,
    company character varying,
    balance bigint,
    subscription_id uuid
);


ALTER TABLE public.users OWNER TO postgres;

--
-- TOC entry 4919 (class 0 OID 24584)
-- Dependencies: 218
-- Data for Name: jobs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.jobs (uid, user_id, provider_id, "time", status, status_str, input, results, start_time, end_time, instance, mode, qpu, usage, region, job_id) FROM stdin;
\.


--
-- TOC entry 4920 (class 0 OID 24589)
-- Dependencies: 219
-- Data for Name: providers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.providers (uid, name) FROM stdin;
\.


--
-- TOC entry 4922 (class 0 OID 24601)
-- Dependencies: 221
-- Data for Name: subscriptions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.subscriptions (uid, name) FROM stdin;
\.


--
-- TOC entry 4923 (class 0 OID 24610)
-- Dependencies: 222
-- Data for Name: trans_internal; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.trans_internal (uid, job_id, user_id) FROM stdin;
\.


--
-- TOC entry 4921 (class 0 OID 24596)
-- Dependencies: 220
-- Data for Name: transactions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.transactions (uid, user_id, date, amount) FROM stdin;
\.


--
-- TOC entry 4918 (class 0 OID 24577)
-- Dependencies: 217
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (uid, firstname, lastname, company, balance, subscription_id) FROM stdin;
\.


--
-- TOC entry 4764 (class 2606 OID 24588)
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (uid);


--
-- TOC entry 4766 (class 2606 OID 24595)
-- Name: providers providers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.providers
    ADD CONSTRAINT providers_pkey PRIMARY KEY (uid);


--
-- TOC entry 4770 (class 2606 OID 24607)
-- Name: subscriptions subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_pkey PRIMARY KEY (uid);


--
-- TOC entry 4772 (class 2606 OID 24614)
-- Name: trans_internal trans_internal_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trans_internal
    ADD CONSTRAINT trans_internal_pkey PRIMARY KEY (uid);


--
-- TOC entry 4768 (class 2606 OID 24600)
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (uid);


--
-- TOC entry 4762 (class 2606 OID 24583)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (uid);


-- Completed on 2025-07-11 13:01:24

--
-- PostgreSQL database dump complete
--

