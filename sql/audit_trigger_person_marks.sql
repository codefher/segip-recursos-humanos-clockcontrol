-- ============================================================
-- TRIGGER DE AUDITORIA PARA rrhh.person_marks
-- ============================================================
-- Objetivo: Registrar QUIEN inserta en person_marks
--           (IP del cliente, usuario, timestamp)
--
-- Ejecutar con un usuario con permisos de CREATE en schema rrhh
-- ============================================================

-- 1. Crear tabla de auditoria
CREATE TABLE IF NOT EXISTS rrhh.person_marks_audit (
    id serial PRIMARY KEY,
    operation varchar(10),
    mark_id integer,
    mark_carnet varchar,
    mark_date varchar,
    mark_time varchar,
    mark_ip_clock varchar,
    mark_id_reloj integer,
    db_user varchar,
    client_addr inet,
    client_port integer,
    app_name varchar,
    backend_pid integer,
    created_at timestamp DEFAULT now()
);

-- 2. Crear funcion del trigger
CREATE OR REPLACE FUNCTION rrhh.fn_audit_person_marks()
RETURNS trigger AS $$
BEGIN
    INSERT INTO rrhh.person_marks_audit (
        operation,
        mark_id,
        mark_carnet,
        mark_date,
        mark_time,
        mark_ip_clock,
        mark_id_reloj,
        db_user,
        client_addr,
        client_port,
        app_name,
        backend_pid
    ) VALUES (
        TG_OP,
        NEW.id,
        NEW.carnet,
        NEW.date_mark,
        NEW.time_mark,
        NEW.ip_clock,
        NEW.id_reloj_bio,
        current_user,
        inet_client_addr(),
        inet_client_port(),
        current_setting('application_name'),
        pg_backend_pid()
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Crear trigger (eliminar si ya existe)
DROP TRIGGER IF EXISTS trg_audit_person_marks ON rrhh.person_marks;

CREATE TRIGGER trg_audit_person_marks
AFTER INSERT ON rrhh.person_marks
FOR EACH ROW
EXECUTE FUNCTION rrhh.fn_audit_person_marks();

-- ============================================================
-- CONSULTAS UTILES (ejecutar despues de que se registren marcajes)
-- ============================================================

-- Ver todos los registros de auditoria
-- SELECT * FROM rrhh.person_marks_audit ORDER BY created_at DESC;

-- Ver agrupado por IP de origen (para saber QUIEN inserta)
-- SELECT client_addr, db_user, app_name, count(*),
--        min(created_at) AS primera, max(created_at) AS ultima
-- FROM rrhh.person_marks_audit
-- GROUP BY client_addr, db_user, app_name
-- ORDER BY count DESC;

-- ============================================================
-- PARA ELIMINAR (cuando ya no se necesite)
-- ============================================================
-- DROP TRIGGER IF EXISTS trg_audit_person_marks ON rrhh.person_marks;
-- DROP FUNCTION IF EXISTS rrhh.fn_audit_person_marks();
-- DROP TABLE IF EXISTS rrhh.person_marks_audit;
