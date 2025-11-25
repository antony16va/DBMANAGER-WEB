--
-- PostgreSQL database dump
--

\restrict Uc2AbWW8PHLf8CIfgxmQkVTAiZEqOwI0LvMpgdwHu5CFQidJT6Ly0rYD8AQiOmW

-- Dumped from database version 17.6
-- Dumped by pg_dump version 17.6

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

--
-- Name: cae_admin; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA cae_admin;


--
-- Name: SCHEMA cae_admin; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA cae_admin IS 'Esquema del cae_admin Administrador';


--
-- Name: cae_eg2026; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA cae_eg2026;


--
-- Name: SCHEMA cae_eg2026; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA cae_eg2026 IS 'Esquema del cae_eg2026 Administrador';


--
-- Name: dblink; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS dblink WITH SCHEMA public;


--
-- Name: EXTENSION dblink; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION dblink IS 'connect to other PostgreSQL databases from within a database';


--
-- Name: postgres_fdw; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgres_fdw WITH SCHEMA public;


--
-- Name: EXTENSION postgres_fdw; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION postgres_fdw IS 'foreign-data wrapper for remote PostgreSQL servers';


--
-- Name: fn_carga_bdonpe_1_odpe(character varying, character varying, character varying, character varying); Type: FUNCTION; Schema: cae_admin; Owner: -
--

CREATE FUNCTION cae_admin.fn_carga_bdonpe_1_odpe(pi_dblink character varying, pi_esquema_origen character varying, pi_esquema_destino character varying, pi_aud_usuario_creacion character varying) RETURNS TABLE(po_resultado integer, po_mensaje character varying)
    LANGUAGE plpgsql
    AS $$
DECLARE
    vc_tabla_origen  varchar := 'mae_odpe'; --v_tabla_origen
    vc_tabla_destino varchar := 'tab_odpe'; --v_tabla_destino
    vc_sql_remoto    text; --v_sql_remoto
    vc_query         text; --v_query
BEGIN

	PERFORM set_config('search_path', 'public,' || current_schema(), false);

	RAISE NOTICE '🔹 Iniciando carga de %.% desde %.% ...',
    pi_esquema_destino, vc_tabla_destino, pi_esquema_origen, vc_tabla_origen;

    -- Limpiar tabla destino y reiniciar secuencia
    EXECUTE format('TRUNCATE TABLE %I.%I CASCADE;', pi_esquema_destino, vc_tabla_destino);
    EXECUTE format('ALTER SEQUENCE %I.sq_tab_odpe_pk RESTART WITH 0;', pi_esquema_destino);

    -- SQL remoto para traer datos desde el origen
    vc_sql_remoto := format(
        'SELECT 
            regexp_replace(substr(mp.c_odpe_pk, 4), ''[^0-9]'', '''', ''g'')::integer AS n_odpe_pk,
            mp.c_descripcion AS c_descripcion,
            regexp_replace(substr(mp.c_odpepadre, 4), ''[^0-9]'', '''', ''g'')::integer AS n_odpe_padre,
            %L::varchar AS c_aud_usuario_creacion
         FROM %I.%I mp
         ORDER BY 1',
        pi_aud_usuario_creacion,
        pi_esquema_origen,
        vc_tabla_origen
    );

    -- Query final en el esquema destino
    vc_query := format(
        'INSERT INTO %I.%I (
            n_odpe_pk,
            c_descripcion,
            n_odpe_padre,
            c_aud_usuario_creacion
        )
        SELECT *
        FROM public.dblink(%L, %L) AS x(
            n_odpe_pk integer,
            c_descripcion varchar,
            n_odpe_padre integer,
            c_aud_usuario_creacion varchar
        )',
        pi_esquema_destino,
        vc_tabla_destino,
        pi_dblink,
        vc_sql_remoto
    );

    -- Ejecutar la carga
	RAISE NOTICE 'Ejecutando inserción en %I.%I ...', pi_esquema_destino, vc_tabla_destino;
    EXECUTE vc_query;
	RAISE NOTICE 'Carga completada correctamente en %I.%I', pi_esquema_destino, vc_tabla_destino;


    po_resultado := 1;
    po_mensaje   := 'Se realizó la carga en la tabla  '||pi_esquema_destino||'.'||vc_tabla_destino;
    RETURN NEXT;

EXCEPTION WHEN OTHERS THEN
    po_resultado := -1;
    po_mensaje   := sqlerrm;
    RETURN NEXT;
END;
$$;


--
-- Name: fn_carga_bdonpe_2_ubigeo(character varying, character varying, character varying, character varying); Type: FUNCTION; Schema: cae_admin; Owner: -
--

CREATE FUNCTION cae_admin.fn_carga_bdonpe_2_ubigeo(pi_dblink character varying, pi_esquema_origen character varying, pi_esquema_destino character varying, pi_aud_usuario_creacion character varying) RETURNS TABLE(po_resultado integer, po_mensaje character varying)
    LANGUAGE plpgsql
    AS $_$
DECLARE
    vc_tabla_origen  varchar := 'mae_ubigeo'; --v_tabla_origen
    vc_tabla_destino varchar := 'tab_ubigeo'; --v_tabla_destino
    vc_sql_remoto    text; --v_sql_remoto
    vc_query         text; --v_query
BEGIN
	PERFORM set_config('search_path', 'public,' || current_schema(), false);

	RAISE NOTICE '🔹 Iniciando carga de %.% desde %.% ...',
    pi_esquema_destino, vc_tabla_destino, pi_esquema_origen, vc_tabla_origen;

    -- Limpiar tabla destino y reiniciar secuencia
    EXECUTE format('TRUNCATE TABLE %I.%I CASCADE;', pi_esquema_destino, vc_tabla_destino);
    EXECUTE format('ALTER SEQUENCE %I.sq_tab_ubigeo_pk RESTART WITH 1;', pi_esquema_destino);

    -- SQL remoto para traer datos desde el origen
    vc_sql_remoto := format(
        $$SELECT 
            regexp_replace(c_ubigeo_pk, '[^0-9]', '', 'g')::integer AS n_ubigeo_pk,
            c_descripcion,
            regexp_replace(c_ubipadre, '[^0-9]', '', 'g')::integer AS n_ubigeo_padre, 
            substring(regexp_replace(c_odpe_fk, '[^0-9]', '', 'g') from 3)::integer AS n_odpe,
            regexp_replace(c_ccomputo_fk, '[^0-9]', '', 'g')::integer AS n_centro_computo,
            regexp_replace(c_capital, '[^0-9]', '', 'g')::integer AS n_capital, 
            regexp_replace(c_region_fk, '[^0-9]', '', 'g')::integer AS n_region, 
            coalesce(substring(regexp_replace(c_distritoe_fk, '[^0-9]', '', 'g') from 3)::integer, 0) AS n_distrito_electoral,
            regexp_replace(c_sede_odpe, '[^0-9]', '', 'g')::integer AS n_sede_odpe, 
            regexp_replace(c_consulado, '[^0-9]', '', 'g')::integer AS n_consulado,    
            %L::varchar AS c_aud_usuario_creacion
         FROM %I.%I mu
         ORDER BY 1$$,
        pi_aud_usuario_creacion,
        pi_esquema_origen,
        vc_tabla_origen
    );

    -- Query final en el esquema destino
    vc_query := format(
        $$INSERT INTO %I.%I (
            n_ubigeo_pk,
            c_descripcion,
            n_ubigeo_padre,
            n_odpe,
            n_centro_computo,
            n_capital,
            n_region,
            n_distrito_electoral,
            n_sede_odpe,
            n_consulado,
            c_aud_usuario_creacion
        )
        SELECT *
        FROM public.dblink(%L, %L) AS x(
            n_ubigeo_pk integer,
            c_descripcion varchar,
            n_ubigeo_padre integer,
            n_odpe integer,
            n_centro_computo integer,
            n_capital integer,
            n_region integer,
            n_distrito_electoral integer,
            n_sede_odpe integer,
            n_consulado integer,
            c_aud_usuario_creacion varchar
        )$$,
        pi_esquema_destino,
        vc_tabla_destino,
        pi_dblink,
        vc_sql_remoto
    );

    -- Ejecutar la carga
	RAISE NOTICE 'Ejecutando inserción en %I.%I ...', pi_esquema_destino, vc_tabla_destino;
    EXECUTE vc_query;
	RAISE NOTICE 'Carga completada correctamente en %I.%I', pi_esquema_destino, vc_tabla_destino;

    po_resultado := 1;
    po_mensaje   := 'Se realizó la carga en la tabla  '||pi_esquema_destino||'.'||vc_tabla_destino;
    RETURN NEXT;

EXCEPTION WHEN OTHERS THEN
	RAISE NOTICE 'Error durante la carga: %', SQLERRM;
    po_resultado := -1;
    po_mensaje   := sqlerrm;
    RETURN NEXT;
END;
$_$;


--
-- Name: fn_carga_bdonpe_3_miembro_mesa(character varying, character varying, character varying, character varying); Type: FUNCTION; Schema: cae_admin; Owner: -
--

CREATE FUNCTION cae_admin.fn_carga_bdonpe_3_miembro_mesa(pi_dblink character varying, pi_esquema_origen character varying, pi_esquema_destino character varying, pi_aud_usuario_creacion character varying) RETURNS TABLE(po_resultado integer, po_mensaje character varying)
    LANGUAGE plpgsql
    AS $_$
DECLARE
    vc_tabla_origen  varchar := 'tab_mmesa'; --v_tabla_origen
    vc_tabla_destino varchar := 'tab_miembro_mesa'; --v_tabla_destino
    vc_sql_remoto    text; --v_sql_remoto
    vc_query         text; --v_query
    vi_min_pk        integer; --v_min_pk
    vi_max_pk        integer; --v_max_pk
    vi_batch_size    integer := 80000; --v_batch_size
BEGIN

	PERFORM set_config('search_path', 'public,' || current_schema(), false);

	RAISE NOTICE 'Iniciando carga de %.% desde %.% ...',
    pi_esquema_destino, vc_tabla_destino, pi_esquema_origen, vc_tabla_origen;
    -- Eliminar índices y constraints antes de la carga
    -------------------------------------------------------------------------
    BEGIN
        EXECUTE format('DROP INDEX IF EXISTS %I.inx_tab_miembro_mesa_c_numero_documento_1;', pi_esquema_destino);
        EXECUTE format('DROP INDEX IF EXISTS %I.inx_tab_miembro_mesa_n_mesa;', pi_esquema_destino);
        EXECUTE format('DROP INDEX IF EXISTS %I.inx_tab_miembro_mesa_c_apellidos_nombres;', pi_esquema_destino);
        EXECUTE format('DROP INDEX IF EXISTS %I.inx_tab_miembro_mesa_n_mesa_activo;', pi_esquema_destino);
        EXECUTE format('DROP INDEX IF EXISTS %I.inx_tab_miembro_mesa_c_numero_documento_2;', pi_esquema_destino);
        EXECUTE format('DROP INDEX IF EXISTS %I.inx_tab_miembro_mesa_n_ubigeo;', pi_esquema_destino);

        EXECUTE format('ALTER TABLE %I.%I DROP CONSTRAINT IF EXISTS cst_tab_miembro_mesa_fk_02;', pi_esquema_destino, vc_tabla_destino);
        EXECUTE format('ALTER TABLE %I.%I DROP CONSTRAINT IF EXISTS cst_tab_miembro_mesa_fk_03;', pi_esquema_destino, vc_tabla_destino);

	EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Advertencia al intentar borrar constraints/índices: %', sqlerrm;
    END;

    -- Limpiar tabla destino y reiniciar secuencia
    EXECUTE format('TRUNCATE TABLE %I.%I CASCADE;', pi_esquema_destino, vc_tabla_destino);
    EXECUTE format('ALTER SEQUENCE %I.sq_tab_miembro_mesa_pk RESTART WITH 1;', pi_esquema_destino);

    -- Obtener rango de PK de la tabla origen
    SELECT MIN(n_mmesa_pk), MAX(n_mmesa_pk)
    		INTO vi_min_pk, vi_max_pk
    FROM dblink(
        pi_dblink,
        format('SELECT n_mmesa_pk FROM %I.%I', pi_esquema_origen, vc_tabla_origen)
    ) AS t(n_mmesa_pk integer);

    IF vi_min_pk IS NULL THEN
        po_resultado := -1;
        po_mensaje := 'No hay registros en la tabla origen';
        RETURN NEXT;
        RETURN;
    END IF;

    -- Carga por bloques de 80,000
    WHILE vi_min_pk <= vi_max_pk LOOP

        -- Construir SQL remoto para el bloque
        vc_sql_remoto := format(
            $sql$
            SELECT
                regexp_replace(tm.c_numele, '[^0-9]', '', 'g') AS c_numero_documento,
                CAST(regexp_replace(tm.c_cargo, '[^0-9]', '', 'g') AS integer) AS n_cargo,
                tm.c_nummesa_fk AS c_mesa,
                CAST(regexp_replace(tm.c_bolo, '[^0-9]', '', 'g') AS integer) AS n_bolo,
                CASE
                    WHEN tm.n_estado = 1 THEN 1
                    WHEN position('TACHA' in upper(tc.c_nombre)) > 0 THEN 2
                    WHEN position('EXCL'  in upper(tc.c_nombre)) > 0 THEN 3
                    WHEN position('EXC'   in upper(tc.c_nombre)) > 0
                      OR position('JUST'  in upper(tc.c_nombre)) > 0 THEN 4
                    ELSE NULL
                END AS n_estado,
                tm.c_direccion AS c_direccion,
                CAST(regexp_replace(tm.c_ubigeo_fk, '[^0-9]', '', 'g') AS integer) AS n_ubigeo,
                %L::varchar AS c_aud_usuario_creacion,
                mp.n_tipodoc AS n_tipo_documento,
                mp.c_nombres AS c_nombres,
                mp.c_appat AS c_apellido_paterno,
                mp.c_apmat AS c_apellido_materno,
                DATE(mp.c_fecnac) AS d_fecha_nacimiento,
                CAST(mp.n_edad AS integer) AS n_edad,
                CAST(mp.c_sexo AS integer) AS n_sexo,
                CAST(regexp_replace(substring(mu.c_odpe_fk FROM 4), '[^0-9]', '', 'g') AS integer) AS n_odpe
            FROM %I.%I tm
            INNER JOIN %I.mae_padron mp 
                ON mp.c_numele_pk = tm.c_numele
            INNER JOIN %I.tab_catalogo tc 
                ON tc.n_codigo = tm.n_estado 
               AND tc.n_flag = 1 
               AND tc.n_eliminado = 0 
               AND tc.c_tabla = 'TAB_MMESA' 
               AND tc.c_columna = 'N_ESTADO'
            INNER JOIN %I.mae_ubigeo mu   
                ON mu.c_ubigeo_pk = tm.c_ubigeo_fk
            WHERE tm.n_mmesa_pk BETWEEN %s AND %s
            $sql$,
            pi_aud_usuario_creacion,
            pi_esquema_origen,
            vc_tabla_origen,
            pi_esquema_origen,
            pi_esquema_origen,
            pi_esquema_origen,
            vi_min_pk,
            LEAST(vi_min_pk + vi_batch_size - 1, vi_max_pk)
        );

        -- Construir query de inserción final
        vc_query := format(
            $final$
            INSERT INTO %I.%I (
                c_numero_documento,
                n_cargo,
                c_mesa,
                n_bolo,
                n_estado,
                c_direccion,
                n_ubigeo,
                c_aud_usuario_creacion,
                n_tipo_documento,
                c_nombres,
                c_apellido_paterno,
                c_apellido_materno,
                d_fecha_nacimiento,
                n_edad,
                n_sexo,
                n_odpe
            )
            SELECT *
            FROM public.dblink(%L, %L) AS x(
                c_numero_documento varchar,
                n_cargo integer,
                c_mesa varchar,
                n_bolo integer,
                n_estado integer,
                c_direccion varchar,
                n_ubigeo integer,
                c_aud_usuario_creacion varchar,
                n_tipo_documento integer,
                c_nombres varchar,
                c_apellido_paterno varchar,
                c_apellido_materno varchar,
                d_fecha_nacimiento date,
                n_edad integer,
                n_sexo integer,
                n_odpe integer
            )
            $final$,
            pi_esquema_destino,
            vc_tabla_destino,
            pi_dblink,
            vc_sql_remoto
        );

		RAISE NOTICE 'Ejecutando inserción en %I.%I ...', pi_esquema_destino, vc_tabla_destino;
        EXECUTE vc_query;

 		-- Devolver mensaje parcial al backend
		        po_resultado := 1;
		        po_mensaje := format(
		            'Bloque cargado: n_padron entre %s y %s',
		            vi_min_pk,
		            LEAST(vi_min_pk + vi_batch_size - 1, vi_max_pk)
		        );
		        RETURN NEXT;

        vi_min_pk := vi_min_pk + vi_batch_size;

    END LOOP;

    -------------------------------------------------------------------------
    -- Recrear índices y constraints al final
    -------------------------------------------------------------------------

     -- 🔹 Índices
    EXECUTE format('CREATE INDEX inx_tab_miembro_mesa_c_numero_documento_1 ON %I.%I (c_numero_documento) TABLESPACE tbs_cae_inx;', pi_esquema_destino, vc_tabla_destino );
    po_resultado := 1;
    po_mensaje := 'Creado índice: inx_tab_miembro_mesa_c_numero_documento_1';
    RETURN NEXT;

    EXECUTE format('CREATE INDEX inx_tab_miembro_mesa_n_mesa ON %I.%I (c_mesa) TABLESPACE tbs_cae_inx;', pi_esquema_destino, vc_tabla_destino);
    po_resultado := 1;
    po_mensaje := 'Creado índice: inx_tab_miembro_mesa_n_mesa';
    RETURN NEXT;

    EXECUTE format('CREATE INDEX inx_tab_miembro_mesa_c_apellidos_nombres ON %I.%I (c_apellido_paterno, c_apellido_materno, c_nombres) TABLESPACE tbs_cae_inx;',pi_esquema_destino, vc_tabla_destino );
    po_resultado := 1;
    po_mensaje := 'Creado índice: inx_tab_miembro_mesa_c_apellidos_nombres';
    RETURN NEXT;

    EXECUTE format('CREATE INDEX inx_tab_miembro_mesa_n_mesa_activo ON %I.%I (c_mesa) TABLESPACE tbs_cae_inx WHERE n_activo = 1;', pi_esquema_destino, vc_tabla_destino );
    po_resultado := 1;
    po_mensaje := 'Creado índice: inx_tab_miembro_mesa_n_mesa_activo';
    RETURN NEXT;

    EXECUTE format('CREATE INDEX inx_tab_miembro_mesa_c_numero_documento_2 ON %I.%I (c_numero_documento) TABLESPACE tbs_cae_inx WHERE n_activo = 1;', pi_esquema_destino, vc_tabla_destino );
    po_resultado := 1;
    po_mensaje := 'Creado índice: inx_tab_miembro_mesa_c_numero_documento_2';
    RETURN NEXT;

    EXECUTE format('CREATE INDEX inx_tab_miembro_mesa_n_ubigeo ON %I.%I (n_ubigeo) TABLESPACE tbs_cae_inx WHERE n_activo = 1;', pi_esquema_destino, vc_tabla_destino );
    po_resultado := 1;
    po_mensaje := 'Creado índice: inx_tab_miembro_mesa_n_ubigeo';
    RETURN NEXT;

    -- 🔹 Constraints
    EXECUTE format('ALTER TABLE %I.%I ADD CONSTRAINT cst_tab_miembro_mesa_fk_02 FOREIGN KEY (n_ubigeo) REFERENCES %I.tab_ubigeo (n_ubigeo_pk) ON UPDATE NO ACTION ON DELETE NO ACTION;',  pi_esquema_destino, vc_tabla_destino, pi_esquema_destino );
    po_resultado := 1;
    po_mensaje := 'Agregado constraint: cst_tab_miembro_mesa_fk_02';
    RETURN NEXT;

    EXECUTE format('ALTER TABLE %I.%I ADD CONSTRAINT cst_tab_miembro_mesa_fk_03 FOREIGN KEY (n_odpe) REFERENCES %I.tab_odpe (n_odpe_pk) ON UPDATE NO ACTION ON DELETE NO ACTION;', pi_esquema_destino, vc_tabla_destino, pi_esquema_destino );
    po_resultado := 1;
    po_mensaje := 'Agregado constraint: cst_tab_miembro_mesa_fk_03';
    RETURN NEXT;
 

    -- 🔹 Mensaje final
    po_resultado := 1;
    po_mensaje   := 'Carga finalizada para '||pi_esquema_destino||'.'||vc_tabla_destino;
    RETURN NEXT;
 
EXCEPTION WHEN OTHERS THEN
    po_resultado := -1;
    po_mensaje   := sqlerrm;
    RETURN NEXT;
END;
$_$;


--
-- Name: fn_carga_bdonpe_4_padron(character varying, character varying, character varying, character varying); Type: FUNCTION; Schema: cae_admin; Owner: -
--

CREATE FUNCTION cae_admin.fn_carga_bdonpe_4_padron(pi_dblink character varying, pi_esquema_origen character varying, pi_esquema_destino character varying, pi_aud_usuario_creacion character varying) RETURNS TABLE(po_resultado integer, po_mensaje character varying)
    LANGUAGE plpgsql
    AS $_$
DECLARE
    vc_tabla_origen  varchar := 'mae_padron'; --v_tabla_origen
    vc_tabla_destino varchar := 'tab_padron'; --v_tabla_destino
    vc_sql_remoto    text; --v_sql_remoto
    vc_query         text; --v_query
    vi_min_pk        integer; --v_min_pk
    vi_max_pk        integer; --v_max_pk
    vi_batch_size    integer := 80000; --v_batch_size
BEGIN
	PERFORM set_config('search_path', 'public,' || current_schema(), false);

	RAISE NOTICE 'Iniciando carga de %.% desde %.% ...',
    pi_esquema_destino, vc_tabla_destino, pi_esquema_origen, vc_tabla_origen;

    -- 1. Borrar constraints e índices relacionados
    BEGIN
        EXECUTE format('ALTER TABLE %I.%I DROP CONSTRAINT IF EXISTS cst_tab_padron_fk_01;', pi_esquema_destino, vc_tabla_destino);

        EXECUTE format('DROP INDEX IF EXISTS %I.inx_tab_padron_c_numero_documento;', pi_esquema_destino);
        EXECUTE format('DROP INDEX IF EXISTS %I.inx_tab_padron_c_apellidos_nombres;', pi_esquema_destino);
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Advertencia al intentar borrar constraints/índices: %', sqlerrm;
    END;

    -- Limpiar tabla destino y reiniciar secuencia
    EXECUTE format('TRUNCATE TABLE %I.%I CASCADE;', pi_esquema_destino, vc_tabla_destino);
    EXECUTE format('ALTER SEQUENCE %I.sq_tab_padron_pk RESTART WITH 1;', pi_esquema_destino);

    -- Obtener el rango de PK de la tabla origen
    SELECT MIN(n_padron), MAX(n_padron)
    INTO vi_min_pk, vi_max_pk
    FROM dblink(
        pi_dblink,
        format('SELECT n_padron FROM %I.%I', pi_esquema_origen, vc_tabla_origen)
    ) AS t(n_padron integer);

    IF vi_min_pk IS NULL THEN
        po_resultado := -1;
        po_mensaje := 'No hay registros en la tabla origen';
        RETURN NEXT;
        RETURN;
    END IF;
	

	/*
	-- LÍMITE MOMENTÁNEO A 500,000 REGISTROS
    IF vi_max_pk > vi_min_pk + 5000 - 1 THEN
        vi_max_pk := vi_min_pk + 5000 - 1;
    END IF;
	*/
	------------------------------------------

    -- Carga por bloques
    WHILE vi_min_pk <= vi_max_pk LOOP

        -- Construir SQL remoto con rango de PK
        vc_sql_remoto := format(
            $sql$
            SELECT
                mp.c_nummesa_fk::integer                AS n_numero_mesa,
                mp.c_ubigeo_fk::integer                 AS n_ubigeo,
                mp.c_digver::integer                    AS n_digito_verificacion,
                mp.n_tipodoc                            AS n_tipo_documento,
                mp.c_numele_pk                          AS c_numero_documento,
                mp.c_appat                              AS c_apellido_paterno,
                mp.c_apmat                              AS c_apellido_materno,
                mp.c_nombres							AS c_nombres,
                mp.c_sexo::integer                      AS n_sexo,
                NULLIF(mp.c_fecnac, '''')::date         AS d_fecha_nacimiento,
                mp.n_gradins                            AS n_grado_instruccion,
                mp.c_restric::integer                   AS n_restriccion,
                mp.n_discap                             AS n_discapacidad,
                mp.c_nummesa_ant::integer               AS n_numero_mesa_anterior,
                mp.c_ubigeo_reniec::integer             AS n_ubigeo_reniec,
                mp.n_orden::integer                     AS n_orden,
                mp.n_edad::integer                      AS n_edad,
                mp.n_procedencia_discap::integer        AS n_procedencia_discapacidad,
                mp.n_cambio_ubigeo::integer             AS n_cambio_ubigeo,
                1                                       AS n_origen_fuente,
                %L::varchar 							AS c_aud_usuario_creacion
            FROM %I.%I mp
            WHERE mp.n_padron BETWEEN %s AND %s
            $sql$,
            pi_aud_usuario_creacion,
            pi_esquema_origen,
            vc_tabla_origen,
            vi_min_pk,
            LEAST(vi_min_pk + vi_batch_size - 1, vi_max_pk)
        );

        -- Ejecutar insert por dblink
        vc_query := format(
            $final$
            INSERT INTO %I.%I (
                n_numero_mesa,
                n_ubigeo,
                n_digito_verificacion,
                n_tipo_documento,
                c_numero_documento,
                c_apellido_paterno,
                c_apellido_materno,
                c_nombres,
                n_sexo,
                d_fecha_nacimiento,
                n_grado_instruccion,
                n_restriccion,
                n_discapacidad,
                n_numero_mesa_anterior,
                n_ubigeo_reniec,
                n_orden,
                n_edad,
                n_procedencia_discapacidad,
                n_cambio_ubigeo,
                n_origen_fuente,
                c_aud_usuario_creacion
            )
            SELECT *
            FROM public.dblink(%L, %L) AS x(
                n_numero_mesa integer,
                n_ubigeo integer,
                n_digito_verificacion integer,
                n_tipo_documento integer,
                c_numero_documento varchar,
                c_apellido_paterno varchar,
                c_apellido_materno varchar,
                c_nombres varchar,
                n_sexo integer,
                d_fecha_nacimiento date,
                n_grado_instruccion integer,
                n_restriccion integer,
                n_discapacidad integer,
                n_numero_mesa_anterior integer,
                n_ubigeo_reniec integer,
                n_orden integer,
                n_edad integer,
                n_procedencia_discapacidad integer,
                n_cambio_ubigeo integer,
                n_origen_fuente integer,
                c_aud_usuario_creacion varchar
            )
            $final$,
            pi_esquema_destino,
            vc_tabla_destino,
            pi_dblink,
            vc_sql_remoto
        );

		RAISE NOTICE 'Ejecutando inserción en %I.%I ...', pi_esquema_destino, vc_tabla_destino;
        EXECUTE vc_query;

		 -- Devolver mensaje parcial al backend
		        po_resultado := 1;
		        po_mensaje := format(
		            'Bloque cargado: n_padron entre %s y %s',
		            vi_min_pk,
		            LEAST(vi_min_pk + vi_batch_size - 1, vi_max_pk)
		        );
		        RETURN NEXT;

        vi_min_pk := vi_min_pk + vi_batch_size;

    END LOOP;



 	-- 5. Recrear índices y constraints
    RAISE NOTICE 'Recreando índices y constraints...';

	 EXECUTE format('CREATE INDEX inx_tab_padron_c_numero_documento ON %I.%I (c_numero_documento) TABLESPACE tbs_cae_inx;', pi_esquema_destino, vc_tabla_destino );
	    po_resultado := 1;
	    po_mensaje := 'Creado índice: inx_tab_padron_c_numero_documento';
	    RETURN NEXT;
	
	    EXECUTE format('CREATE INDEX inx_tab_padron_c_apellidos_nombres ON %I.%I (c_apellido_paterno, c_apellido_materno, c_nombres) TABLESPACE tbs_cae_inx;', pi_esquema_destino, vc_tabla_destino );
	    po_resultado := 1;
	    po_mensaje := 'Creado índice: inx_tab_padron_c_apellidos_nombres';
	    RETURN NEXT;
	
	    EXECUTE format('ALTER TABLE %I.%I ADD CONSTRAINT cst_tab_padron_fk_01 FOREIGN KEY (n_ubigeo) REFERENCES %I.tab_ubigeo (n_ubigeo_pk);', pi_esquema_destino, vc_tabla_destino, pi_esquema_destino );
	    po_resultado := 1;
	    po_mensaje := 'Agregado constraint: cst_tab_padron_fk_01';
	    RETURN NEXT;
	
	    -- Mensaje final
	    po_resultado := 1;
	    po_mensaje   := 'Carga finalizada para '||pi_esquema_destino||'.'||vc_tabla_destino;
	    RETURN NEXT;


EXCEPTION WHEN OTHERS THEN
    po_resultado := -1;
    po_mensaje   := sqlerrm;
    RETURN NEXT;
END;
$_$;


--
-- Name: fn_carga_bdonpe_general(character varying, character varying, character varying, character varying); Type: FUNCTION; Schema: cae_admin; Owner: -
--

CREATE FUNCTION cae_admin.fn_carga_bdonpe_general(pi_dblink character varying, pi_esquema_origen character varying, pi_esquema_destino character varying, pi_aud_usuario_creacion character varying) RETURNS TABLE(po_paso text, po_resultado integer, po_mensaje character varying)
    LANGUAGE plpgsql
    AS $$
DECLARE
    vi_resultado integer; --v_resultado
    vc_mensaje   varchar; --v_mensaje
BEGIN

	PERFORM set_config('search_path', 'public,' || current_schema(), false);
		

    -- 1. Cargar ODPE
    FOR vi_resultado, vc_mensaje IN
        SELECT * FROM cae_admin.fn_carga_bdonpe_1_odpe(pi_dblink, pi_esquema_origen, pi_esquema_destino, pi_aud_usuario_creacion)
    LOOP
        po_paso := 'Carga ODPE';
        po_resultado := vi_resultado;
        po_mensaje   := vc_mensaje;
        RETURN NEXT;

        -- Si hubo error, detener ejecución
        IF vi_resultado = -1 THEN
            RETURN;
        END IF;
    END LOOP;

    -- 🔹 2. Cargar Ubigeo
    FOR vi_resultado, vc_mensaje IN
        SELECT * FROM cae_admin.fn_carga_bdonpe_2_ubigeo(pi_dblink, pi_esquema_origen, pi_esquema_destino, pi_aud_usuario_creacion)
    LOOP
        po_paso := 'Carga Ubigeo';
        po_resultado := vi_resultado;
        po_mensaje   := vc_mensaje;
        RETURN NEXT;

        IF vi_resultado = -1 THEN
            RETURN;
        END IF;
    END LOOP;

    -- 🔹 3. Cargar Miembro de Mesa
    FOR vi_resultado, vc_mensaje IN
        SELECT * FROM cae_admin.fn_carga_bdonpe_3_miembro_mesa(pi_dblink, pi_esquema_origen, pi_esquema_destino, pi_aud_usuario_creacion)
    LOOP
        po_paso := 'Carga Miembro Mesa';
        po_resultado := vi_resultado;
        po_mensaje   := vc_mensaje;
        RETURN NEXT;

        IF vi_resultado = -1 THEN
            RETURN;
        END IF;
    END LOOP;

    -- 🔹 4. Cargar Padrón
    FOR vi_resultado, vc_mensaje IN
        SELECT * FROM cae_admin.fn_carga_bdonpe_4_padron(pi_dblink, pi_esquema_origen, pi_esquema_destino, pi_aud_usuario_creacion)
    LOOP
        po_paso := 'Carga Padrón';
        po_resultado := vi_resultado;
        po_mensaje   := vc_mensaje;
        RETURN NEXT;

        IF vi_resultado = -1 THEN
            RETURN;
        END IF;
    END LOOP;

END;
$$;


--
-- Name: fn_listado_configuracion_proceso_electoral(character varying); Type: FUNCTION; Schema: cae_admin; Owner: -
--

CREATE FUNCTION cae_admin.fn_listado_configuracion_proceso_electoral(pi_esquema character varying) RETURNS TABLE(n_configuracion_proceso_electoral_pk integer, c_nombre character varying, c_acronimo character varying, b_logo bytea, c_nombre_logo character varying, d_fecha_convocatoria timestamp without time zone, n_vigente integer, c_vigente character varying, n_activo integer, c_activo character varying)
    LANGUAGE plpgsql
    AS $$
	BEGIN
	    -- Cambiar esquema dinámicamente
	    EXECUTE 'SET search_path = ' || pi_esquema;
	
	    RETURN QUERY
	    SELECT 
	        tcpe.n_configuracion_proceso_electoral_pk,
	        tcpe.c_nombre,
	        tcpe.c_acronimo,
	        tcpe.b_logo,
	        tcpe.c_nombre_logo,
	        tcpe.d_fecha_convocatoria,
	        tcpe.n_vigente::integer,
	        dce1.c_nombre AS c_vigente,
	        tcpe.n_activo::integer,
	        dce2.c_nombre AS c_activo
	    FROM tab_configuracion_proceso_electoral tcpe
	    INNER JOIN det_catalogo_estructura dce1 ON dce1.n_codigo = tcpe.n_vigente AND dce1.c_columna = 'n_vigente' AND dce1.n_activo = 1
	    INNER JOIN det_catalogo_estructura dce2 ON dce2.n_codigo = tcpe.n_activo  AND dce2.c_columna = 'n_activo'  AND dce2.n_activo = 1
	    WHERE tcpe.n_activo = 1
		order by  tcpe.n_configuracion_proceso_electoral_pk desc;
	END;
	$$;


--
-- Name: fn_filacolumna(character varying, character varying, character varying, character varying, character varying, character varying, integer); Type: FUNCTION; Schema: cae_eg2026; Owner: -
--

CREATE FUNCTION cae_eg2026.fn_filacolumna(pi_esquema character varying, pi_tabla character varying, pi_rowc character varying, pi_colc character varying, pi_cellc character varying, pi_celldatatype character varying, pi_tipoarchivo integer) RETURNS character varying
    LANGUAGE plpgsql
    AS $$
declare
    vc_dynsql1 varchar; --dynsql1
    vc_dynsql2 varchar; --dynsql2
    vc_columnlist varchar; --columnlist
begin
    -- 1. lista de columnas.
    vc_dynsql1 = 'select string_agg(distinct ''_''||'||pi_colc||'||'' '||pi_celldatatype||''','','' order by ''_''||'||pi_colc||'||'' '||pi_celldatatype||''') from '||pi_esquema||'.'||pi_tabla||' where n_carga_archivo='||pi_tipoarchivo||' and n_activo = 1;';
    execute vc_dynsql1 into vc_columnlist;

    -- 2. configura consulta 
    vc_dynsql2 = 'select * from public.crosstab (
 ''select '||pi_rowc||','||pi_colc||','||pi_cellc||' from '||pi_esquema||'.'||pi_tabla||' where n_carga_archivo='||pi_tipoarchivo||' and n_activo = 1 group by n_fila, c_clave, c_valor order by 1'',
 ''select distinct '||pi_colc||' from '||pi_esquema||'.'||pi_tabla||' where n_carga_archivo='||pi_tipoarchivo||' and n_activo = 1 order by 1''
 )
 as newtable (
 '||pi_rowc||' varchar,'||vc_columnlist||'
 );';
    return vc_dynsql2;
end
$$;


--
-- Name: fn_carga_bdonpe_4_padron(character varying, character varying, character varying, character varying); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_carga_bdonpe_4_padron(pi_dblink character varying, pi_esquema_origen character varying, pi_esquema_destino character varying, pi_aud_usuario_creacion character varying) RETURNS TABLE(po_resultado integer, po_mensaje character varying)
    LANGUAGE plpgsql
    AS $_$
DECLARE
    v_tabla_origen  varchar := 'mae_padron';
    v_tabla_destino varchar := 'tab_padron';
    v_sql_remoto    text;
    v_query         text;
    v_min_pk        integer;
    v_max_pk        integer;
    v_batch_size    integer := 80000; --3000000
BEGIN
	PERFORM set_config('search_path', 'public,' || current_schema(), false);

	RAISE NOTICE '🔹 Iniciando carga de %.% desde %.% ...',
    pi_esquema_destino, v_tabla_destino, pi_esquema_origen, v_tabla_origen;

    -- 🔹 1. Borrar constraints e índices relacionados
    BEGIN
        EXECUTE format('ALTER TABLE %I.%I DROP CONSTRAINT IF EXISTS cst_tab_padron_fk_01;', pi_esquema_destino, v_tabla_destino);
        EXECUTE format('DROP INDEX IF EXISTS %I.inx_tab_padron_c_numero_documento;', pi_esquema_destino);
        EXECUTE format('DROP INDEX IF EXISTS %I.inx_tab_padron_c_apellidos_nombres;', pi_esquema_destino);
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Advertencia al intentar borrar constraints/índices: %', sqlerrm;
    END;

    -- 🔹 Limpiar tabla destino y reiniciar secuencia
    EXECUTE format('TRUNCATE TABLE %I.%I CASCADE;', pi_esquema_destino, v_tabla_destino);
    EXECUTE format('ALTER SEQUENCE %I.sq_tab_padron_pk RESTART WITH 1;', pi_esquema_destino);

    -- 🔹 Obtener el rango de PK de la tabla origen
    SELECT MIN(n_padron), MAX(n_padron)
    INTO v_min_pk, v_max_pk
    FROM dblink(
        pi_dblink,
        format('SELECT n_padron FROM %I.%I', pi_esquema_origen, v_tabla_origen)
    ) AS t(n_padron integer);

    IF v_min_pk IS NULL THEN
        po_resultado := -1;
        po_mensaje := 'No hay registros en la tabla origen';
        RETURN NEXT;
        RETURN;
    END IF;
	

	/*
	-- 🔹 LÍMITE MOMENTÁNEO A 500,000 REGISTROS
    IF v_max_pk > v_min_pk + 500000 - 1 THEN
        v_max_pk := v_min_pk + 500000 - 1;
    END IF;
	*/
	------------------------------------------

    -- 🔹 Carga por bloques
    WHILE v_min_pk <= v_max_pk LOOP

        -- Construir SQL remoto con rango de PK
        v_sql_remoto := format(
            $sql$
            SELECT
                mp.c_nummesa_fk::integer                AS n_numero_mesa,
                mp.c_ubigeo_fk::integer                 AS n_ubigeo,
                mp.c_digver::integer                    AS n_digito_verificacion,
                mp.n_tipodoc                             AS n_tipo_documento,
                mp.c_numele_pk                           AS c_numero_documento,
                mp.c_appat                               AS c_apellido_paterno,
                mp.c_apmat                               AS c_apellido_materno,
                mp.c_nombres,
                mp.c_sexo::integer                       AS n_sexo,
                NULLIF(mp.c_fecnac, '''')::date         AS d_fecha_nacimiento,
                mp.n_gradins                             AS n_grado_instruccion,
                mp.c_restric::integer                    AS n_restriccion,
                mp.n_discap                               AS n_discapacidad,
                mp.c_nummesa_ant::integer                AS n_numero_mesa_anterior,
                mp.c_ubigeo_reniec::integer              AS n_ubigeo_reniec,
                mp.n_orden::integer                       AS n_orden,
                mp.n_edad::integer                        AS n_edad,
                mp.n_procedencia_discap::integer         AS n_procedencia_discapacidad,
                mp.n_cambio_ubigeo::integer              AS n_cambio_ubigeo,
                1                                        AS n_origen_fuente,
                %L::varchar AS c_aud_usuario_creacion
            FROM %I.%I mp
            WHERE mp.n_padron BETWEEN %s AND %s
            $sql$,
            pi_aud_usuario_creacion,
            pi_esquema_origen,
            v_tabla_origen,
            v_min_pk,
            LEAST(v_min_pk + v_batch_size - 1, v_max_pk)
        );

        -- Ejecutar insert por dblink
        v_query := format(
            $final$
            INSERT INTO %I.%I (
                n_numero_mesa,
                n_ubigeo,
                n_digito_verificacion,
                n_tipo_documento,
                c_numero_documento,
                c_apellido_paterno,
                c_apellido_materno,
                c_nombres,
                n_sexo,
                d_fecha_nacimiento,
                n_grado_instruccion,
                n_restriccion,
                n_discapacidad,
                n_numero_mesa_anterior,
                n_ubigeo_reniec,
                n_orden,
                n_edad,
                n_procedencia_discapacidad,
                n_cambio_ubigeo,
                n_origen_fuente,
                c_aud_usuario_creacion
            )
            SELECT *
            FROM public.dblink(%L, %L) AS x(
                n_numero_mesa integer,
                n_ubigeo integer,
                n_digito_verificacion integer,
                n_tipo_documento integer,
                c_numero_documento varchar,
                c_apellido_paterno varchar,
                c_apellido_materno varchar,
                c_nombres varchar,
                n_sexo integer,
                d_fecha_nacimiento date,
                n_grado_instruccion integer,
                n_restriccion integer,
                n_discapacidad integer,
                n_numero_mesa_anterior integer,
                n_ubigeo_reniec integer,
                n_orden integer,
                n_edad integer,
                n_procedencia_discapacidad integer,
                n_cambio_ubigeo integer,
                n_origen_fuente integer,
                c_aud_usuario_creacion varchar
            )
            $final$,
            pi_esquema_destino,
            v_tabla_destino,
            pi_dblink,
            v_sql_remoto
        );

		RAISE NOTICE '⏳ Ejecutando inserción en %I.%I ...', pi_esquema_destino, v_tabla_destino;
        EXECUTE v_query;

		 -- 🔹 Devolver mensaje parcial al backend
		        po_resultado := 1;
		        po_mensaje := format(
		            'Bloque cargado: n_padron entre %s y %s',
		            v_min_pk,
		            LEAST(v_min_pk + v_batch_size - 1, v_max_pk)
		        );
		        RETURN NEXT;

        v_min_pk := v_min_pk + v_batch_size;

    END LOOP;


    -- 🔹 5. Recrear índices y constraints
 -- 🔹 5. Recrear índices y constraints
    RAISE NOTICE '🔧 Recreando índices y constraints...';

	 EXECUTE format(
	        'CREATE INDEX inx_tab_padron_c_numero_documento ON %I.%I (c_numero_documento) TABLESPACE tbs_cae_inx;',
	        pi_esquema_destino, v_tabla_destino
	    );
	    po_resultado := 1;
	    po_mensaje := 'Creado índice: inx_tab_padron_c_numero_documento';
	    RETURN NEXT;
	
	    EXECUTE format(
	        'CREATE INDEX inx_tab_padron_c_apellidos_nombres ON %I.%I (c_apellido_paterno, c_apellido_materno, c_nombres) TABLESPACE tbs_cae_inx;',
	        pi_esquema_destino, v_tabla_destino
	    );
	    po_resultado := 1;
	    po_mensaje := 'Creado índice: inx_tab_padron_c_apellidos_nombres';
	    RETURN NEXT;
	
	    EXECUTE format(
	        'ALTER TABLE %I.%I ADD CONSTRAINT cst_tab_padron_fk_01 FOREIGN KEY (n_ubigeo) REFERENCES %I.tab_ubigeo (n_ubigeo_pk);',
	        pi_esquema_destino, v_tabla_destino, pi_esquema_destino
	    );
	    po_resultado := 1;
	    po_mensaje := 'Agregado constraint: cst_tab_padron_fk_01';
	    RETURN NEXT;
	  	
	    -- 🔹 Mensaje final
	    po_resultado := 1;
	    po_mensaje   := '✅ Carga finalizada para '||pi_esquema_destino||'.'||v_tabla_destino;
	    RETURN NEXT;


EXCEPTION WHEN OTHERS THEN
    po_resultado := -1;
    po_mensaje   := sqlerrm;
    RETURN NEXT;
END;
$_$;


--
-- Name: srv_bdonpe; Type: SERVER; Schema: -; Owner: -
--

CREATE SERVER srv_bdonpe FOREIGN DATA WRAPPER postgres_fdw OPTIONS (
    dbname 'bdonpe',
    host '192.168.44.49',
    port '5433'
);


--
-- Name: USER MAPPING cae SERVER srv_bdonpe; Type: USER MAPPING; Schema: -; Owner: -
--

CREATE USER MAPPING FOR cae SERVER srv_bdonpe OPTIONS (
    password 'bdonpe_ab01$',
    "user" 'bdonpe'
);


--
-- Name: sq_cab_catalogo_pk; Type: SEQUENCE; Schema: cae_admin; Owner: -
--

CREATE SEQUENCE cae_admin.sq_cab_catalogo_pk
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 999999999999999
    CACHE 1;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: cab_catalogo; Type: TABLE; Schema: cae_admin; Owner: -
--

CREATE TABLE cae_admin.cab_catalogo (
    n_catalogo_pk integer DEFAULT nextval('cae_admin.sq_cab_catalogo_pk'::regclass) NOT NULL,
    n_catalogo_padre integer,
    c_maestro character varying(50),
    n_activo smallint DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_catalogo_estructura_pk; Type: SEQUENCE; Schema: cae_admin; Owner: -
--

CREATE SEQUENCE cae_admin.sq_det_catalogo_estructura_pk
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_catalogo_estructura; Type: TABLE; Schema: cae_admin; Owner: -
--

CREATE TABLE cae_admin.det_catalogo_estructura (
    n_det_catalogo_estructura_pk integer DEFAULT nextval('cae_admin.sq_det_catalogo_estructura_pk'::regclass) NOT NULL,
    n_catalogo integer,
    c_columna character varying(50),
    c_nombre character varying(1000),
    n_codigo integer,
    c_codigo character varying(20),
    n_orden integer,
    c_tipo character varying(250),
    c_informacion_adicional character varying(1000),
    n_obligatorio integer DEFAULT 0 NOT NULL,
    n_activo smallint DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_catalogo_referencia_pk; Type: SEQUENCE; Schema: cae_admin; Owner: -
--

CREATE SEQUENCE cae_admin.sq_det_catalogo_referencia_pk
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_catalogo_referencia; Type: TABLE; Schema: cae_admin; Owner: -
--

CREATE TABLE cae_admin.det_catalogo_referencia (
    n_det_catalogo_referencia_pk integer DEFAULT nextval('cae_admin.sq_det_catalogo_referencia_pk'::regclass) NOT NULL,
    n_catalogo integer,
    c_tabla_referencia character varying(250),
    n_activo smallint DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_tab_configuracion_proceso_electoral_pk; Type: SEQUENCE; Schema: cae_admin; Owner: -
--

CREATE SEQUENCE cae_admin.sq_tab_configuracion_proceso_electoral_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: tab_configuracion_proceso_electoral; Type: TABLE; Schema: cae_admin; Owner: -
--

CREATE TABLE cae_admin.tab_configuracion_proceso_electoral (
    n_configuracion_proceso_electoral_pk integer DEFAULT nextval('cae_admin.sq_tab_configuracion_proceso_electoral_pk'::regclass) NOT NULL,
    c_nombre character varying(500) NOT NULL,
    c_acronimo character varying(20) NOT NULL,
    b_logo bytea,
    c_nombre_logo character varying(100),
    c_nombre_esquema_principal character varying(100),
    c_nombre_esquema_bdonpe character varying(100),
    c_nombre_dblink_bdonpe character varying(100),
    d_fecha_convocatoria timestamp without time zone,
    d_fecha_cierre_convocatoria timestamp without time zone,
    n_estado_carga_bdonpe integer,
    n_cantidad_carga_bdonpe integer,
    n_vigente smallint DEFAULT 1 NOT NULL,
    n_activo smallint DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_cab_catalogo_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_cab_catalogo_pk
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: cab_catalogo; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.cab_catalogo (
    n_catalogo_pk integer DEFAULT nextval('cae_eg2026.sq_cab_catalogo_pk'::regclass) NOT NULL,
    n_catalogo_padre integer,
    c_maestro character varying(50),
    n_activo smallint DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_cab_curso_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_cab_curso_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: cab_curso; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.cab_curso (
    n_curso_pk integer DEFAULT nextval('cae_eg2026.sq_cab_curso_pk'::regclass) NOT NULL,
    c_nombre_curso character varying(300) NOT NULL,
    c_descripcion character varying(600),
    c_siglas character varying(50),
    n_orden integer,
    n_tipo_actor_electoral integer,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_catalogo_estructura_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_det_catalogo_estructura_pk
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_catalogo_estructura; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.det_catalogo_estructura (
    n_det_catalogo_estructura_pk integer DEFAULT nextval('cae_eg2026.sq_det_catalogo_estructura_pk'::regclass) NOT NULL,
    n_catalogo integer,
    c_columna character varying(50),
    c_nombre character varying(1000),
    n_codigo integer,
    c_codigo character varying(20),
    n_orden integer,
    c_tipo character varying(250),
    c_informacion_adicional character varying(1000),
    n_obligatorio integer DEFAULT 0 NOT NULL,
    n_activo smallint DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_catalogo_referencia_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_det_catalogo_referencia_pk
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_catalogo_referencia; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.det_catalogo_referencia (
    n_det_catalogo_referencia_pk integer DEFAULT nextval('cae_eg2026.sq_det_catalogo_referencia_pk'::regclass) NOT NULL,
    n_catalogo integer,
    c_tabla_referencia character varying(250),
    n_activo smallint DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_certificado_firma_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_det_certificado_firma_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_certificado_firma; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.det_certificado_firma (
    n_det_certificado_firma_pk integer DEFAULT nextval('cae_eg2026.sq_det_certificado_firma_pk'::regclass) NOT NULL,
    n_certificado_plantilla integer,
    c_nombre_firmante character varying(200) NOT NULL,
    c_cargo_firmante character varying(150),
    c_ruta_firma character varying(500),
    n_pos_x numeric(8,2),
    n_pos_y numeric(8,2),
    n_ancho numeric(8,2),
    n_alto numeric(8,2),
    n_mostrar_linea integer DEFAULT 1 NOT NULL,
    c_color_linea character varying(20) DEFAULT '#000000'::character varying,
    n_grosor_linea numeric(4,2) DEFAULT 1.0,
    c_estructura_json text,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_certificado_plantilla_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_det_certificado_plantilla_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_certificado_plantilla; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.det_certificado_plantilla (
    n_det_certificado_plantilla_pk integer DEFAULT nextval('cae_eg2026.sq_det_certificado_plantilla_pk'::regclass) NOT NULL,
    c_nombre_plantilla character varying(200) NOT NULL,
    c_titulo_certificado character varying(200),
    c_color_titulo character varying(20),
    c_subtitulo_presentacion character varying(300),
    c_texto_reconocimiento_1 text,
    c_texto_reconocimiento_2 text,
    c_texto_reconocimiento_3 text,
    c_texto_reconocimiento_4 text,
    c_texto_pie_pagina text,
    c_lugar character varying(150),
    c_marca_agua character varying(300),
    c_borde_estilo character varying(100),
    c_estructura_json text,
    n_curso integer,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_certificado_recurso_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_det_certificado_recurso_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_certificado_recurso; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.det_certificado_recurso (
    n_det_certificado_recurso_pk integer DEFAULT nextval('cae_eg2026.sq_det_certificado_recurso_pk'::regclass) NOT NULL,
    n_det_certificado_plantilla integer,
    c_nombre_elemento character varying(100),
    c_ruta_archivo character varying(500),
    n_pos_x numeric(8,2),
    n_pos_y numeric(8,2),
    n_ancho numeric(8,2),
    n_alto numeric(8,2),
    c_estructura_json text,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_curso_contenido_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_det_curso_contenido_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_curso_contenido; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.det_curso_contenido (
    n_det_curso_contenido_pk integer DEFAULT nextval('cae_eg2026.sq_det_curso_contenido_pk'::regclass) NOT NULL,
    n_tipo_curso_contenido integer NOT NULL,
    c_nombre_recurso character varying(300) NOT NULL,
    c_descripcion character varying(600),
    c_ruta_url character varying(1200),
    c_formato character varying(50),
    c_tamanio character varying(100),
    c_duracion character varying(50),
    n_tamano_kb integer,
    d_fecha_carga timestamp without time zone,
    n_orden integer,
    c_siglas character varying(50),
    n_curso integer,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_curso_contenido_ubigeo_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_det_curso_contenido_ubigeo_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_curso_contenido_ubigeo; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.det_curso_contenido_ubigeo (
    n_det_curso_contenido_ubigeo_pk integer DEFAULT nextval('cae_eg2026.sq_det_curso_contenido_ubigeo_pk'::regclass) NOT NULL,
    n_det_curso_contenido integer NOT NULL,
    n_ubigeo_departamento integer NOT NULL,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_encuesta_plantilla_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_det_encuesta_plantilla_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_encuesta_plantilla; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.det_encuesta_plantilla (
    n_det_encuesta_plantilla_pk integer DEFAULT nextval('cae_eg2026.sq_det_encuesta_plantilla_pk'::regclass) NOT NULL,
    c_nombre_encuesta character varying(300) NOT NULL,
    c_descripcion character varying(600),
    n_curso integer,
    n_orden integer,
    n_max_intentos integer DEFAULT 1 NOT NULL,
    d_fecha_hora_inicio timestamp without time zone,
    d_fecha_hora_fin timestamp without time zone,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_encuesta_pregunta_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_det_encuesta_pregunta_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_encuesta_pregunta; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.det_encuesta_pregunta (
    n_det_encuesta_pregunta_pk integer DEFAULT nextval('cae_eg2026.sq_det_encuesta_pregunta_pk'::regclass) NOT NULL,
    c_nombre_pregunta character varying(300) NOT NULL,
    n_orden integer,
    n_det_encuesta_plantilla integer,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_evaluacion_plantilla_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_det_evaluacion_plantilla_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_evaluacion_plantilla; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.det_evaluacion_plantilla (
    n_det_evaluacion_plantilla_pk integer DEFAULT nextval('cae_eg2026.sq_det_evaluacion_plantilla_pk'::regclass) NOT NULL,
    c_nombre_evaluacion character varying(300) NOT NULL,
    c_descripcion character varying(600),
    n_curso integer NOT NULL,
    n_orden integer,
    n_max_intentos integer DEFAULT 1 NOT NULL,
    d_fecha_hora_inicio timestamp without time zone,
    d_fecha_hora_fin timestamp without time zone,
    n_nota_minima_aprobatoria numeric(5,2) DEFAULT 12 NOT NULL,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_evaluacion_pregunta_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_det_evaluacion_pregunta_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_evaluacion_pregunta; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.det_evaluacion_pregunta (
    n_det_evaluacion_pregunta_pk integer DEFAULT nextval('cae_eg2026.sq_det_evaluacion_pregunta_pk'::regclass) NOT NULL,
    c_nombre_pregunta character varying(300) NOT NULL,
    n_orden integer,
    n_det_evaluacion_plantilla integer,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_participante_certificado_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_det_participante_certificado_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_participante_certificado; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.det_participante_certificado (
    n_det_participante_certificado_pk integer DEFAULT nextval('cae_eg2026.sq_det_participante_certificado_pk'::regclass) NOT NULL,
    n_descargado integer DEFAULT 0 NOT NULL,
    d_fecha_descarga timestamp without time zone,
    n_enviado_correo integer DEFAULT 0 NOT NULL,
    d_fecha_envio_correo timestamp without time zone,
    c_correo_destino character varying(200),
    c_ruta_pdf character varying(500),
    n_numero_descarga integer DEFAULT 0,
    n_numero_envio integer DEFAULT 0,
    d_fecha_emision timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    n_det_participante_curso integer,
    n_det_certificado_plantilla integer,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_participante_curso_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_det_participante_curso_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_participante_curso; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.det_participante_curso (
    n_det_participante_curso_pk integer DEFAULT nextval('cae_eg2026.sq_det_participante_curso_pk'::regclass) NOT NULL,
    c_numero_documento character varying(50) NOT NULL,
    c_nombres character varying(100),
    c_apellido_paterno character varying(100),
    c_apellido_materno character varying(100),
    n_curso integer NOT NULL,
    n_fase integer DEFAULT 0,
    n_estado_fase integer DEFAULT 0,
    d_fecha_inicio timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    d_fecha_fin timestamp without time zone,
    n_intentos_evaluacion integer DEFAULT 0,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_participante_encuesta_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_det_participante_encuesta_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_participante_encuesta; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.det_participante_encuesta (
    n_det_participante_encuesta_pk integer DEFAULT nextval('cae_eg2026.sq_det_participante_encuesta_pk'::regclass) NOT NULL,
    n_intento integer DEFAULT 1,
    c_respuesta_encuesta jsonb,
    c_comentario text,
    d_fecha_respuesta timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    n_es_completado integer DEFAULT 0 NOT NULL,
    n_det_participante_curso integer,
    n_det_encuesta_plantilla integer,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_participante_evaluacion_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_det_participante_evaluacion_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_participante_evaluacion; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.det_participante_evaluacion (
    n_det_participante_evaluacion_pk integer DEFAULT nextval('cae_eg2026.sq_det_participante_evaluacion_pk'::regclass) NOT NULL,
    n_intento integer NOT NULL,
    n_puntaje numeric(5,2) NOT NULL,
    n_es_aprobado integer,
    d_fecha_evaluacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_respuesta_evaluacion jsonb,
    n_es_completado integer DEFAULT 0 NOT NULL,
    n_det_participante_curso integer,
    n_det_evaluacion_plantilla integer,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_participante_visualizacion_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_det_participante_visualizacion_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_participante_visualizacion; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.det_participante_visualizacion (
    n_det_participante_visualizacion_pk integer DEFAULT nextval('cae_eg2026.sq_det_participante_visualizacion_pk'::regclass) NOT NULL,
    d_fecha_ultima_visualizacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    n_veces_visto integer DEFAULT 1 NOT NULL,
    n_segundos_vistos integer DEFAULT 0 NOT NULL,
    n_es_completado integer DEFAULT 0 NOT NULL,
    n_det_participante_curso integer,
    n_det_curso_contenido integer,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_pregunta_alternativa_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_det_pregunta_alternativa_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_pregunta_alternativa; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.det_pregunta_alternativa (
    n_det_pregunta_alternativa_pk integer DEFAULT nextval('cae_eg2026.sq_det_pregunta_alternativa_pk'::regclass) NOT NULL,
    c_nombre_alternativa character varying(300) NOT NULL,
    n_orden integer,
    n_es_correcto integer DEFAULT 0 NOT NULL,
    n_det_evaluacion_pregunta integer,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_det_pregunta_opcion_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_det_pregunta_opcion_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: det_pregunta_opcion; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.det_pregunta_opcion (
    n_det_pregunta_opcion_pk integer DEFAULT nextval('cae_eg2026.sq_det_pregunta_opcion_pk'::regclass) NOT NULL,
    c_nombre_opcion character varying(300) NOT NULL,
    n_orden integer,
    n_det_encuesta_pregunta integer,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_mae_tipo_actor_electoral_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_mae_tipo_actor_electoral_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: mae_tipo_actor_electoral; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.mae_tipo_actor_electoral (
    n_tipo_actor_electoral_pk integer DEFAULT nextval('cae_eg2026.sq_mae_tipo_actor_electoral_pk'::regclass) NOT NULL,
    c_nombre character varying(100),
    c_abreviatura character varying(100),
    n_orden integer,
    n_vigente smallint DEFAULT 1 NOT NULL,
    n_activo smallint DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_mae_tipo_estrategia_electoral_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_mae_tipo_estrategia_electoral_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: mae_tipo_estrategia_electoral; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.mae_tipo_estrategia_electoral (
    n_tipo_estrategia_electoral_pk integer DEFAULT nextval('cae_eg2026.sq_mae_tipo_estrategia_electoral_pk'::regclass) NOT NULL,
    c_nombre character varying(100),
    c_abreviatura character varying(100),
    n_orden integer,
    n_vigente smallint DEFAULT 1 NOT NULL,
    n_activo smallint DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: sq_tab_configuracion_actor_electoral_estrategia_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_tab_configuracion_actor_electoral_estrategia_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: sq_tab_miembro_mesa_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_tab_miembro_mesa_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: sq_tab_odpe_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_tab_odpe_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: sq_tab_padron_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_tab_padron_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: sq_tab_ubigeo_pk; Type: SEQUENCE; Schema: cae_eg2026; Owner: -
--

CREATE SEQUENCE cae_eg2026.sq_tab_ubigeo_pk
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    MAXVALUE 999999999999999
    CACHE 1;


--
-- Name: tab_configuracion_actor_electoral_estrategia; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.tab_configuracion_actor_electoral_estrategia (
    n_configuracion_actor_electoral_estrategia_pk integer DEFAULT nextval('cae_eg2026.sq_tab_configuracion_actor_electoral_estrategia_pk'::regclass) NOT NULL,
    n_tipo_estrategia_electoral integer,
    n_tipo_actor_electoral integer,
    n_vigente smallint DEFAULT 1 NOT NULL,
    n_activo smallint DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: tab_miembro_mesa; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.tab_miembro_mesa (
    n_miembro_mesa_pk integer DEFAULT nextval('cae_eg2026.sq_tab_miembro_mesa_pk'::regclass) NOT NULL,
    c_numero_documento character varying(50),
    n_cargo integer,
    c_mesa character varying(10),
    n_bolo integer,
    n_estado integer,
    c_direccion character varying(150),
    n_ubigeo integer,
    n_estado_capacitado integer DEFAULT 0 NOT NULL,
    n_tipo_documento integer,
    c_nombres character varying(100),
    c_apellido_paterno character varying(100),
    c_apellido_materno character varying(100),
    d_fecha_nacimiento timestamp without time zone,
    n_edad integer,
    n_sexo integer,
    n_odpe integer,
    n_vigente smallint DEFAULT 1 NOT NULL,
    n_activo smallint DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: tab_odpe; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.tab_odpe (
    n_odpe_pk integer DEFAULT nextval('cae_eg2026.sq_tab_odpe_pk'::regclass) NOT NULL,
    c_descripcion character varying(100),
    n_odpe_padre integer,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: tab_padron; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.tab_padron (
    n_padron_pk integer DEFAULT nextval('cae_eg2026.sq_tab_padron_pk'::regclass) NOT NULL,
    n_numero_mesa integer,
    n_ubigeo integer,
    n_digito_verificacion integer,
    n_tipo_documento integer,
    c_numero_documento character varying(50),
    c_apellido_paterno character varying(100),
    c_apellido_materno character varying(100),
    c_nombres character varying(100),
    n_sexo integer,
    d_fecha_nacimiento timestamp without time zone,
    n_grado_instruccion integer,
    n_restriccion integer,
    n_discapacidad integer,
    n_numero_mesa_anterior integer,
    n_ubigeo_reniec integer,
    n_orden integer,
    n_edad integer,
    n_procedencia_discapacidad integer,
    n_cambio_ubigeo integer,
    n_centro_computo integer,
    n_cargo integer,
    n_origen_fuente integer,
    n_estado_capacitado smallint DEFAULT 0 NOT NULL,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: tab_ubigeo; Type: TABLE; Schema: cae_eg2026; Owner: -
--

CREATE TABLE cae_eg2026.tab_ubigeo (
    n_ubigeo_pk integer DEFAULT nextval('cae_eg2026.sq_tab_ubigeo_pk'::regclass) NOT NULL,
    c_descripcion character varying(50),
    n_ubigeo_padre integer,
    n_odpe integer,
    n_centro_computo integer,
    n_capital integer,
    n_region integer,
    n_distrito_electoral integer,
    n_sede_odpe integer,
    n_consulado integer,
    n_vigente integer DEFAULT 1 NOT NULL,
    n_activo integer DEFAULT 1 NOT NULL,
    c_aud_usuario_creacion character varying(50) NOT NULL,
    d_aud_fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_aud_usuario_modificacion character varying(50),
    d_aud_fecha_modificacion timestamp without time zone
);


--
-- Name: vw_odpe; Type: VIEW; Schema: cae_eg2026; Owner: -
--

CREATE VIEW cae_eg2026.vw_odpe AS
 SELECT n_odpe_pk AS n_odpe,
    c_descripcion AS c_odpe
   FROM cae_eg2026.tab_odpe to2
  WHERE ((n_activo = 1) AND (n_vigente = 1))
  ORDER BY n_odpe_pk;


--
-- Name: vw_tipo_actor_estrategia; Type: VIEW; Schema: cae_eg2026; Owner: -
--

CREATE VIEW cae_eg2026.vw_tipo_actor_estrategia AS
 SELECT tae.n_tipo_actor_electoral_pk,
    tae.c_nombre AS actor_electoral,
    tee.n_tipo_estrategia_electoral_pk,
    tee.c_nombre AS tipo_estrategia,
    tee.c_abreviatura
   FROM ((cae_eg2026.mae_tipo_actor_electoral tae
     JOIN cae_eg2026.tab_configuracion_actor_electoral_estrategia a1 ON (((a1.n_tipo_actor_electoral = tae.n_tipo_actor_electoral_pk) AND (a1.n_activo = 1))))
     JOIN cae_eg2026.mae_tipo_estrategia_electoral tee ON (((tee.n_tipo_estrategia_electoral_pk = a1.n_tipo_estrategia_electoral) AND (tee.n_activo = 1))))
  WHERE (tae.n_activo = 1);


--
-- Name: vw_ubigeo_departamento; Type: VIEW; Schema: cae_eg2026; Owner: -
--

CREATE VIEW cae_eg2026.vw_ubigeo_departamento AS
 SELECT n_ubigeo_pk AS n_ubigeo_departamento,
    c_descripcion AS c_ubigeo_departamento
   FROM cae_eg2026.tab_ubigeo mu
  WHERE (("substring"(lpad((n_ubigeo_pk)::text, 6, '0'::text), 3, 4) = '0000'::text) AND (n_activo = 1) AND (n_vigente = 1))
  ORDER BY n_ubigeo_pk;


--
-- Name: vw_ubigeo_distrito; Type: VIEW; Schema: cae_eg2026; Owner: -
--

CREATE VIEW cae_eg2026.vw_ubigeo_distrito AS
 SELECT n_ubigeo_pk AS n_ubigeo_distrito,
    c_descripcion AS c_ubigeo_distrito
   FROM cae_eg2026.tab_ubigeo mu
  WHERE (("substring"(lpad((n_ubigeo_pk)::text, 6, '0'::text), 5, 2) <> '00'::text) AND (n_activo = 1) AND (n_vigente = 1))
  ORDER BY n_ubigeo_pk;


--
-- Name: vw_ubigeo_odpe; Type: VIEW; Schema: cae_eg2026; Owner: -
--

CREATE VIEW cae_eg2026.vw_ubigeo_odpe AS
 SELECT mu3.n_ubigeo_pk AS n_ubigeo_departamento,
    mu3.c_descripcion AS c_ubigeo_departamento,
    mu2.n_ubigeo_pk AS n_ubigeo_provincia,
    mu2.c_descripcion AS c_ubigeo_provincia,
    mu1.n_ubigeo_pk AS n_ubigeo_distrito,
    mu1.c_descripcion AS c_ubigeo_distrito,
    mu1.n_odpe,
    to2.c_descripcion AS c_odpe
   FROM (((cae_eg2026.tab_ubigeo mu1
     JOIN cae_eg2026.tab_ubigeo mu2 ON (((lpad((mu2.n_ubigeo_pk)::text, 6, '0'::text) = lpad((mu1.n_ubigeo_padre)::text, 6, '0'::text)) AND (mu2.n_activo = 1) AND (mu2.n_vigente = 1))))
     JOIN cae_eg2026.tab_ubigeo mu3 ON (((lpad((mu3.n_ubigeo_pk)::text, 6, '0'::text) = lpad((mu2.n_ubigeo_padre)::text, 6, '0'::text)) AND (mu3.n_activo = 1) AND (mu3.n_vigente = 1))))
     JOIN cae_eg2026.tab_odpe to2 ON (((to2.n_odpe_pk = mu1.n_odpe) AND (to2.n_activo = 1) AND (to2.n_vigente = 1))))
  WHERE (("substring"(lpad((mu1.n_ubigeo_pk)::text, 6, '0'::text), 5, 2) <> '00'::text) AND (mu1.n_activo = 1) AND (mu1.n_vigente = 1))
  ORDER BY mu3.n_ubigeo_pk, mu2.n_ubigeo_pk, mu1.n_ubigeo_pk;


--
-- Name: vw_ubigeo_provincia; Type: VIEW; Schema: cae_eg2026; Owner: -
--

CREATE VIEW cae_eg2026.vw_ubigeo_provincia AS
 SELECT n_ubigeo_pk AS n_ubigeo_provincia,
    c_descripcion AS c_ubigeo_provincia
   FROM cae_eg2026.tab_ubigeo mu
  WHERE (("substring"(lpad((n_ubigeo_pk)::text, 6, '0'::text), 5, 2) = '00'::text) AND ("substring"(lpad((n_ubigeo_pk)::text, 6, '0'::text), 3, 2) <> '00'::text) AND (n_activo = 1) AND (n_vigente = 1))
  ORDER BY n_ubigeo_pk;


--
-- Name: cab_catalogo cst_cab_catalogo_pk; Type: CONSTRAINT; Schema: cae_admin; Owner: -
--

ALTER TABLE ONLY cae_admin.cab_catalogo
    ADD CONSTRAINT cst_cab_catalogo_pk PRIMARY KEY (n_catalogo_pk);


--
-- Name: det_catalogo_estructura cst_det_catalogo_estructura_pk; Type: CONSTRAINT; Schema: cae_admin; Owner: -
--

ALTER TABLE ONLY cae_admin.det_catalogo_estructura
    ADD CONSTRAINT cst_det_catalogo_estructura_pk PRIMARY KEY (n_det_catalogo_estructura_pk);


--
-- Name: det_catalogo_referencia cst_det_catalogo_referencia_pk; Type: CONSTRAINT; Schema: cae_admin; Owner: -
--

ALTER TABLE ONLY cae_admin.det_catalogo_referencia
    ADD CONSTRAINT cst_det_catalogo_referencia_pk PRIMARY KEY (n_det_catalogo_referencia_pk);


--
-- Name: tab_configuracion_proceso_electoral cst_tab_configuracion_proceso_electoral_pk; Type: CONSTRAINT; Schema: cae_admin; Owner: -
--

ALTER TABLE ONLY cae_admin.tab_configuracion_proceso_electoral
    ADD CONSTRAINT cst_tab_configuracion_proceso_electoral_pk PRIMARY KEY (n_configuracion_proceso_electoral_pk);


--
-- Name: cab_catalogo cst_cab_catalogo_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.cab_catalogo
    ADD CONSTRAINT cst_cab_catalogo_pk PRIMARY KEY (n_catalogo_pk);


--
-- Name: det_catalogo_estructura cst_det_catalogo_estructura_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_catalogo_estructura
    ADD CONSTRAINT cst_det_catalogo_estructura_pk PRIMARY KEY (n_det_catalogo_estructura_pk);


--
-- Name: det_catalogo_referencia cst_det_catalogo_referencia_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_catalogo_referencia
    ADD CONSTRAINT cst_det_catalogo_referencia_pk PRIMARY KEY (n_det_catalogo_referencia_pk);


--
-- Name: det_certificado_firma cst_det_certificado_firma_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_certificado_firma
    ADD CONSTRAINT cst_det_certificado_firma_pk PRIMARY KEY (n_det_certificado_firma_pk);


--
-- Name: det_certificado_plantilla cst_det_certificado_plantilla_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_certificado_plantilla
    ADD CONSTRAINT cst_det_certificado_plantilla_pk PRIMARY KEY (n_det_certificado_plantilla_pk);


--
-- Name: det_certificado_recurso cst_det_certificado_recurso_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_certificado_recurso
    ADD CONSTRAINT cst_det_certificado_recurso_pk PRIMARY KEY (n_det_certificado_recurso_pk);


--
-- Name: det_curso_contenido cst_det_curso_contenido_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_curso_contenido
    ADD CONSTRAINT cst_det_curso_contenido_pk PRIMARY KEY (n_det_curso_contenido_pk);


--
-- Name: det_curso_contenido_ubigeo cst_det_curso_contenido_ubigeo_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_curso_contenido_ubigeo
    ADD CONSTRAINT cst_det_curso_contenido_ubigeo_pk PRIMARY KEY (n_det_curso_contenido_ubigeo_pk);


--
-- Name: det_encuesta_plantilla cst_det_encuesta_plantilla_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_encuesta_plantilla
    ADD CONSTRAINT cst_det_encuesta_plantilla_pk PRIMARY KEY (n_det_encuesta_plantilla_pk);


--
-- Name: det_encuesta_pregunta cst_det_encuesta_pregunta_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_encuesta_pregunta
    ADD CONSTRAINT cst_det_encuesta_pregunta_pk PRIMARY KEY (n_det_encuesta_pregunta_pk);


--
-- Name: det_evaluacion_plantilla cst_det_evaluacion_plantilla_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_evaluacion_plantilla
    ADD CONSTRAINT cst_det_evaluacion_plantilla_pk PRIMARY KEY (n_det_evaluacion_plantilla_pk);


--
-- Name: det_evaluacion_pregunta cst_det_evaluacion_pregunta_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_evaluacion_pregunta
    ADD CONSTRAINT cst_det_evaluacion_pregunta_pk PRIMARY KEY (n_det_evaluacion_pregunta_pk);


--
-- Name: det_participante_certificado cst_det_participante_certificado_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_participante_certificado
    ADD CONSTRAINT cst_det_participante_certificado_pk PRIMARY KEY (n_det_participante_certificado_pk);


--
-- Name: det_participante_curso cst_det_participante_curso_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_participante_curso
    ADD CONSTRAINT cst_det_participante_curso_pk PRIMARY KEY (n_det_participante_curso_pk);


--
-- Name: det_participante_encuesta cst_det_participante_encuesta_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_participante_encuesta
    ADD CONSTRAINT cst_det_participante_encuesta_pk PRIMARY KEY (n_det_participante_encuesta_pk);


--
-- Name: det_participante_evaluacion cst_det_participante_evaluacion_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_participante_evaluacion
    ADD CONSTRAINT cst_det_participante_evaluacion_pk PRIMARY KEY (n_det_participante_evaluacion_pk);


--
-- Name: det_participante_visualizacion cst_det_participante_visualizacion_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_participante_visualizacion
    ADD CONSTRAINT cst_det_participante_visualizacion_pk PRIMARY KEY (n_det_participante_visualizacion_pk);


--
-- Name: det_pregunta_alternativa cst_det_pregunta_alternativa_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_pregunta_alternativa
    ADD CONSTRAINT cst_det_pregunta_alternativa_pk PRIMARY KEY (n_det_pregunta_alternativa_pk);


--
-- Name: det_pregunta_opcion cst_det_pregunta_opcion_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_pregunta_opcion
    ADD CONSTRAINT cst_det_pregunta_opcion_pk PRIMARY KEY (n_det_pregunta_opcion_pk);


--
-- Name: cab_curso cst_mae_curso_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.cab_curso
    ADD CONSTRAINT cst_mae_curso_pk PRIMARY KEY (n_curso_pk);


--
-- Name: mae_tipo_actor_electoral cst_mae_tipo_actor_electoral_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.mae_tipo_actor_electoral
    ADD CONSTRAINT cst_mae_tipo_actor_electoral_pk PRIMARY KEY (n_tipo_actor_electoral_pk);


--
-- Name: mae_tipo_estrategia_electoral cst_mae_tipo_estrategia_electoral_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.mae_tipo_estrategia_electoral
    ADD CONSTRAINT cst_mae_tipo_estrategia_electoral_pk PRIMARY KEY (n_tipo_estrategia_electoral_pk);


--
-- Name: tab_configuracion_actor_electoral_estrategia cst_tab_configuracion_actor_electoral_estrategia_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.tab_configuracion_actor_electoral_estrategia
    ADD CONSTRAINT cst_tab_configuracion_actor_electoral_estrategia_pk PRIMARY KEY (n_configuracion_actor_electoral_estrategia_pk);


--
-- Name: tab_miembro_mesa cst_tab_miembro_mesa_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.tab_miembro_mesa
    ADD CONSTRAINT cst_tab_miembro_mesa_pk PRIMARY KEY (n_miembro_mesa_pk);


--
-- Name: tab_odpe cst_tab_odpe_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.tab_odpe
    ADD CONSTRAINT cst_tab_odpe_pk PRIMARY KEY (n_odpe_pk);


--
-- Name: tab_padron cst_tab_padron_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.tab_padron
    ADD CONSTRAINT cst_tab_padron_pk PRIMARY KEY (n_padron_pk);


--
-- Name: tab_ubigeo cst_tab_ubigeo_pk; Type: CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.tab_ubigeo
    ADD CONSTRAINT cst_tab_ubigeo_pk PRIMARY KEY (n_ubigeo_pk);


SET default_tablespace = tbs_cae_inx;

--
-- Name: inx_det_catalogo_estructura_columna_codigo; Type: INDEX; Schema: cae_eg2026; Owner: -; Tablespace: tbs_cae_inx
--

CREATE INDEX inx_det_catalogo_estructura_columna_codigo ON cae_eg2026.det_catalogo_estructura USING btree (c_columna, n_codigo) WHERE (n_activo = 1);


--
-- Name: inx_mae_tipo_estrategia_electoral_pk_activo; Type: INDEX; Schema: cae_eg2026; Owner: -; Tablespace: tbs_cae_inx
--

CREATE INDEX inx_mae_tipo_estrategia_electoral_pk_activo ON cae_eg2026.mae_tipo_estrategia_electoral USING btree (n_tipo_estrategia_electoral_pk) WHERE (n_activo = 1);


--
-- Name: inx_tab_miembro_mesa_c_apellidos_nombres; Type: INDEX; Schema: cae_eg2026; Owner: -; Tablespace: tbs_cae_inx
--

CREATE INDEX inx_tab_miembro_mesa_c_apellidos_nombres ON cae_eg2026.tab_miembro_mesa USING btree (c_apellido_paterno, c_apellido_materno, c_nombres);


--
-- Name: inx_tab_miembro_mesa_c_numero_documento_1; Type: INDEX; Schema: cae_eg2026; Owner: -; Tablespace: tbs_cae_inx
--

CREATE INDEX inx_tab_miembro_mesa_c_numero_documento_1 ON cae_eg2026.tab_miembro_mesa USING btree (c_numero_documento);


--
-- Name: inx_tab_miembro_mesa_c_numero_documento_2; Type: INDEX; Schema: cae_eg2026; Owner: -; Tablespace: tbs_cae_inx
--

CREATE INDEX inx_tab_miembro_mesa_c_numero_documento_2 ON cae_eg2026.tab_miembro_mesa USING btree (c_numero_documento) WHERE (n_activo = 1);


--
-- Name: inx_tab_miembro_mesa_n_mesa; Type: INDEX; Schema: cae_eg2026; Owner: -; Tablespace: tbs_cae_inx
--

CREATE INDEX inx_tab_miembro_mesa_n_mesa ON cae_eg2026.tab_miembro_mesa USING btree (c_mesa);


--
-- Name: inx_tab_miembro_mesa_n_mesa_activo; Type: INDEX; Schema: cae_eg2026; Owner: -; Tablespace: tbs_cae_inx
--

CREATE INDEX inx_tab_miembro_mesa_n_mesa_activo ON cae_eg2026.tab_miembro_mesa USING btree (c_mesa) WHERE (n_activo = 1);


--
-- Name: inx_tab_miembro_mesa_n_ubigeo; Type: INDEX; Schema: cae_eg2026; Owner: -; Tablespace: tbs_cae_inx
--

CREATE INDEX inx_tab_miembro_mesa_n_ubigeo ON cae_eg2026.tab_miembro_mesa USING btree (n_ubigeo) WHERE (n_activo = 1);


--
-- Name: inx_tab_odpe_pk_activo; Type: INDEX; Schema: cae_eg2026; Owner: -; Tablespace: tbs_cae_inx
--

CREATE INDEX inx_tab_odpe_pk_activo ON cae_eg2026.tab_odpe USING btree (n_odpe_pk) WHERE (n_activo = 1);


--
-- Name: inx_tab_padron_c_apellidos_nombres; Type: INDEX; Schema: cae_eg2026; Owner: -; Tablespace: tbs_cae_inx
--

CREATE INDEX inx_tab_padron_c_apellidos_nombres ON cae_eg2026.tab_padron USING btree (c_apellido_paterno, c_apellido_materno, c_nombres);


--
-- Name: inx_tab_padron_c_numero_documento; Type: INDEX; Schema: cae_eg2026; Owner: -; Tablespace: tbs_cae_inx
--

CREATE INDEX inx_tab_padron_c_numero_documento ON cae_eg2026.tab_padron USING btree (c_numero_documento);


--
-- Name: cab_catalogo cst_cab_catalogo_fk_01; Type: FK CONSTRAINT; Schema: cae_admin; Owner: -
--

ALTER TABLE ONLY cae_admin.cab_catalogo
    ADD CONSTRAINT cst_cab_catalogo_fk_01 FOREIGN KEY (n_catalogo_padre) REFERENCES cae_admin.cab_catalogo(n_catalogo_pk);


--
-- Name: det_catalogo_estructura cst_det_catalogo_estructura_fk_01; Type: FK CONSTRAINT; Schema: cae_admin; Owner: -
--

ALTER TABLE ONLY cae_admin.det_catalogo_estructura
    ADD CONSTRAINT cst_det_catalogo_estructura_fk_01 FOREIGN KEY (n_catalogo) REFERENCES cae_admin.cab_catalogo(n_catalogo_pk) ON DELETE CASCADE;


--
-- Name: det_catalogo_referencia cst_det_catalogo_referencia_fk_01; Type: FK CONSTRAINT; Schema: cae_admin; Owner: -
--

ALTER TABLE ONLY cae_admin.det_catalogo_referencia
    ADD CONSTRAINT cst_det_catalogo_referencia_fk_01 FOREIGN KEY (n_catalogo) REFERENCES cae_admin.cab_catalogo(n_catalogo_pk) ON DELETE CASCADE;


--
-- Name: cab_catalogo cst_cab_catalogo_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.cab_catalogo
    ADD CONSTRAINT cst_cab_catalogo_fk_01 FOREIGN KEY (n_catalogo_padre) REFERENCES cae_eg2026.cab_catalogo(n_catalogo_pk);


--
-- Name: cab_curso cst_cab_curso_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.cab_curso
    ADD CONSTRAINT cst_cab_curso_fk_01 FOREIGN KEY (n_tipo_actor_electoral) REFERENCES cae_eg2026.mae_tipo_actor_electoral(n_tipo_actor_electoral_pk);


--
-- Name: det_catalogo_estructura cst_det_catalogo_estructura_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_catalogo_estructura
    ADD CONSTRAINT cst_det_catalogo_estructura_fk_01 FOREIGN KEY (n_catalogo) REFERENCES cae_eg2026.cab_catalogo(n_catalogo_pk) ON DELETE CASCADE;


--
-- Name: det_catalogo_referencia cst_det_catalogo_referencia_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_catalogo_referencia
    ADD CONSTRAINT cst_det_catalogo_referencia_fk_01 FOREIGN KEY (n_catalogo) REFERENCES cae_eg2026.cab_catalogo(n_catalogo_pk) ON DELETE CASCADE;


--
-- Name: det_certificado_plantilla cst_det_certificado_plantilla_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_certificado_plantilla
    ADD CONSTRAINT cst_det_certificado_plantilla_fk_01 FOREIGN KEY (n_curso) REFERENCES cae_eg2026.cab_curso(n_curso_pk);


--
-- Name: det_certificado_recurso cst_det_certificado_recurso_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_certificado_recurso
    ADD CONSTRAINT cst_det_certificado_recurso_fk_01 FOREIGN KEY (n_det_certificado_plantilla) REFERENCES cae_eg2026.det_certificado_plantilla(n_det_certificado_plantilla_pk);


--
-- Name: det_curso_contenido cst_det_curso_contenido_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_curso_contenido
    ADD CONSTRAINT cst_det_curso_contenido_fk_01 FOREIGN KEY (n_curso) REFERENCES cae_eg2026.cab_curso(n_curso_pk);


--
-- Name: det_curso_contenido_ubigeo cst_det_curso_contenido_ubigeo_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_curso_contenido_ubigeo
    ADD CONSTRAINT cst_det_curso_contenido_ubigeo_fk_01 FOREIGN KEY (n_det_curso_contenido) REFERENCES cae_eg2026.det_curso_contenido(n_det_curso_contenido_pk);


--
-- Name: det_encuesta_plantilla cst_det_encuesta_plantilla_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_encuesta_plantilla
    ADD CONSTRAINT cst_det_encuesta_plantilla_fk_01 FOREIGN KEY (n_curso) REFERENCES cae_eg2026.cab_curso(n_curso_pk);


--
-- Name: det_encuesta_pregunta cst_det_encuesta_pregunta_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_encuesta_pregunta
    ADD CONSTRAINT cst_det_encuesta_pregunta_fk_01 FOREIGN KEY (n_det_encuesta_plantilla) REFERENCES cae_eg2026.det_encuesta_plantilla(n_det_encuesta_plantilla_pk);


--
-- Name: det_evaluacion_plantilla cst_det_evaluacion_plantilla_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_evaluacion_plantilla
    ADD CONSTRAINT cst_det_evaluacion_plantilla_fk_01 FOREIGN KEY (n_curso) REFERENCES cae_eg2026.cab_curso(n_curso_pk);


--
-- Name: det_evaluacion_pregunta cst_det_evaluacion_pregunta_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_evaluacion_pregunta
    ADD CONSTRAINT cst_det_evaluacion_pregunta_fk_01 FOREIGN KEY (n_det_evaluacion_plantilla) REFERENCES cae_eg2026.det_evaluacion_plantilla(n_det_evaluacion_plantilla_pk);


--
-- Name: det_participante_certificado cst_det_participante_certificado_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_participante_certificado
    ADD CONSTRAINT cst_det_participante_certificado_fk_01 FOREIGN KEY (n_det_participante_curso) REFERENCES cae_eg2026.det_participante_curso(n_det_participante_curso_pk);


--
-- Name: det_participante_certificado cst_det_participante_certificado_fk_02; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_participante_certificado
    ADD CONSTRAINT cst_det_participante_certificado_fk_02 FOREIGN KEY (n_det_certificado_plantilla) REFERENCES cae_eg2026.det_certificado_plantilla(n_det_certificado_plantilla_pk);


--
-- Name: det_participante_curso cst_det_participante_curso_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_participante_curso
    ADD CONSTRAINT cst_det_participante_curso_fk_01 FOREIGN KEY (n_curso) REFERENCES cae_eg2026.cab_curso(n_curso_pk);


--
-- Name: det_participante_encuesta cst_det_participante_encuesta_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_participante_encuesta
    ADD CONSTRAINT cst_det_participante_encuesta_fk_01 FOREIGN KEY (n_det_participante_curso) REFERENCES cae_eg2026.det_participante_curso(n_det_participante_curso_pk);


--
-- Name: det_participante_encuesta cst_det_participante_encuesta_fk_02; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_participante_encuesta
    ADD CONSTRAINT cst_det_participante_encuesta_fk_02 FOREIGN KEY (n_det_encuesta_plantilla) REFERENCES cae_eg2026.det_encuesta_plantilla(n_det_encuesta_plantilla_pk);


--
-- Name: det_participante_evaluacion cst_det_participante_evaluacion_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_participante_evaluacion
    ADD CONSTRAINT cst_det_participante_evaluacion_fk_01 FOREIGN KEY (n_det_participante_curso) REFERENCES cae_eg2026.det_participante_curso(n_det_participante_curso_pk);


--
-- Name: det_participante_evaluacion cst_det_participante_evaluacion_fk_02; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_participante_evaluacion
    ADD CONSTRAINT cst_det_participante_evaluacion_fk_02 FOREIGN KEY (n_det_evaluacion_plantilla) REFERENCES cae_eg2026.det_evaluacion_plantilla(n_det_evaluacion_plantilla_pk);


--
-- Name: det_participante_visualizacion cst_det_participante_visualizacion_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_participante_visualizacion
    ADD CONSTRAINT cst_det_participante_visualizacion_fk_01 FOREIGN KEY (n_det_participante_curso) REFERENCES cae_eg2026.det_participante_curso(n_det_participante_curso_pk);


--
-- Name: det_participante_visualizacion cst_det_participante_visualizacion_fk_02; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_participante_visualizacion
    ADD CONSTRAINT cst_det_participante_visualizacion_fk_02 FOREIGN KEY (n_det_curso_contenido) REFERENCES cae_eg2026.det_curso_contenido(n_det_curso_contenido_pk);


--
-- Name: det_pregunta_alternativa cst_det_pregunta_alternativa_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_pregunta_alternativa
    ADD CONSTRAINT cst_det_pregunta_alternativa_fk_01 FOREIGN KEY (n_det_evaluacion_pregunta) REFERENCES cae_eg2026.det_evaluacion_pregunta(n_det_evaluacion_pregunta_pk);


--
-- Name: det_pregunta_opcion cst_det_pregunta_opcion_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_pregunta_opcion
    ADD CONSTRAINT cst_det_pregunta_opcion_fk_01 FOREIGN KEY (n_det_encuesta_pregunta) REFERENCES cae_eg2026.det_encuesta_pregunta(n_det_encuesta_pregunta_pk);


--
-- Name: tab_configuracion_actor_electoral_estrategia cst_mae_configuracion_actor_electoral_estrategia_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.tab_configuracion_actor_electoral_estrategia
    ADD CONSTRAINT cst_mae_configuracion_actor_electoral_estrategia_fk_01 FOREIGN KEY (n_tipo_estrategia_electoral) REFERENCES cae_eg2026.mae_tipo_estrategia_electoral(n_tipo_estrategia_electoral_pk);


--
-- Name: tab_configuracion_actor_electoral_estrategia cst_mae_configuracion_actor_electoral_estrategia_fk_02; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.tab_configuracion_actor_electoral_estrategia
    ADD CONSTRAINT cst_mae_configuracion_actor_electoral_estrategia_fk_02 FOREIGN KEY (n_tipo_actor_electoral) REFERENCES cae_eg2026.mae_tipo_actor_electoral(n_tipo_actor_electoral_pk);


--
-- Name: det_certificado_firma cst_tab_encuesta_alternativa_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.det_certificado_firma
    ADD CONSTRAINT cst_tab_encuesta_alternativa_fk_01 FOREIGN KEY (n_certificado_plantilla) REFERENCES cae_eg2026.det_certificado_plantilla(n_det_certificado_plantilla_pk);


--
-- Name: tab_miembro_mesa cst_tab_miembro_mesa_fk_02; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.tab_miembro_mesa
    ADD CONSTRAINT cst_tab_miembro_mesa_fk_02 FOREIGN KEY (n_ubigeo) REFERENCES cae_eg2026.tab_ubigeo(n_ubigeo_pk);


--
-- Name: tab_miembro_mesa cst_tab_miembro_mesa_fk_03; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.tab_miembro_mesa
    ADD CONSTRAINT cst_tab_miembro_mesa_fk_03 FOREIGN KEY (n_odpe) REFERENCES cae_eg2026.tab_odpe(n_odpe_pk);


--
-- Name: tab_padron cst_tab_padron_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.tab_padron
    ADD CONSTRAINT cst_tab_padron_fk_01 FOREIGN KEY (n_ubigeo) REFERENCES cae_eg2026.tab_ubigeo(n_ubigeo_pk);


--
-- Name: tab_ubigeo cst_tab_ubigeo_fk_01; Type: FK CONSTRAINT; Schema: cae_eg2026; Owner: -
--

ALTER TABLE ONLY cae_eg2026.tab_ubigeo
    ADD CONSTRAINT cst_tab_ubigeo_fk_01 FOREIGN KEY (n_odpe) REFERENCES cae_eg2026.tab_odpe(n_odpe_pk);


--
-- PostgreSQL database dump complete
--

\unrestrict Uc2AbWW8PHLf8CIfgxmQkVTAiZEqOwI0LvMpgdwHu5CFQidJT6Ly0rYD8AQiOmW
