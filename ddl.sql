-- =============================================
-- DDL Generated from Excel Template
-- =============================================

CREATE SCHEMA IF NOT EXISTS cursos_online;

-- Table: cursos_online.categorias
CREATE TABLE cursos_online.categorias (
    id_categoria SERIAL NOT NULL,
    nombre_categoria VARCHAR(100) NOT NULL,
    descripcion TEXT,
    id_categoria_padre INTEGER,
    activo VARCHAR(2) NOT NULL DEFAULT ''SI'',
    CONSTRAINT pk_categorias PRIMARY KEY (id_categoria)
);

COMMENT ON TABLE cursos_online.categorias IS 'Tabla de categorías de cursos';
COMMENT ON COLUMN cursos_online.categorias.id_categoria IS 'Identificador único de la categoría';
COMMENT ON COLUMN cursos_online.categorias.nombre_categoria IS 'Nombre de la categoría';
COMMENT ON COLUMN cursos_online.categorias.descripcion IS 'Descripción de la categoría';
COMMENT ON COLUMN cursos_online.categorias.id_categoria_padre IS 'Referencia a categoría padre para jerarquía';
COMMENT ON COLUMN cursos_online.categorias.activo IS 'Indicador si la categoría está activa';

-- Table: cursos_online.certificados
CREATE TABLE cursos_online.certificados (
    id_certificado SERIAL NOT NULL,
    id_inscripcion INTEGER NOT NULL,
    codigo_certificado VARCHAR(50) NOT NULL,
    fecha_emision TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    url_certificado VARCHAR(500),
    calificacion_final NUMERIC(5,2),
    CONSTRAINT pk_certificados PRIMARY KEY (id_certificado)
);

COMMENT ON TABLE cursos_online.certificados IS 'Tabla de certificados emitidos';
COMMENT ON COLUMN cursos_online.certificados.id_certificado IS 'Identificador único del certificado';
COMMENT ON COLUMN cursos_online.certificados.id_inscripcion IS 'Inscripción que genera el certificado';
COMMENT ON COLUMN cursos_online.certificados.codigo_certificado IS 'Código único del certificado';
COMMENT ON COLUMN cursos_online.certificados.fecha_emision IS 'Fecha de emisión del certificado';
COMMENT ON COLUMN cursos_online.certificados.url_certificado IS 'URL del archivo PDF del certificado';
COMMENT ON COLUMN cursos_online.certificados.calificacion_final IS 'Calificación final del curso';

-- Table: cursos_online.cursos
CREATE TABLE cursos_online.cursos (
    id_curso SERIAL NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    descripcion TEXT NOT NULL,
    id_categoria INTEGER NOT NULL,
    id_instructor INTEGER NOT NULL,
    duracion_horas NUMERIC(5,2) NOT NULL,
    nivel VARCHAR(20) NOT NULL,
    precio NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_publicacion DATE,
    activo VARCHAR(2) NOT NULL DEFAULT ''SI'',
    CONSTRAINT pk_cursos PRIMARY KEY (id_curso)
);

COMMENT ON TABLE cursos_online.cursos IS 'Tabla de cursos disponibles';
COMMENT ON COLUMN cursos_online.cursos.id_curso IS 'Identificador único del curso';
COMMENT ON COLUMN cursos_online.cursos.titulo IS 'Título del curso';
COMMENT ON COLUMN cursos_online.cursos.descripcion IS 'Descripción completa del curso';
COMMENT ON COLUMN cursos_online.cursos.id_categoria IS 'Categoría a la que pertenece el curso';
COMMENT ON COLUMN cursos_online.cursos.id_instructor IS 'Instructor responsable del curso';
COMMENT ON COLUMN cursos_online.cursos.duracion_horas IS 'Duración estimada del curso en horas';
COMMENT ON COLUMN cursos_online.cursos.nivel IS 'Nivel del curso (Básico, Intermedio, Avanzado)';
COMMENT ON COLUMN cursos_online.cursos.precio IS 'Precio del curso';
COMMENT ON COLUMN cursos_online.cursos.fecha_creacion IS 'Fecha de creación del curso';
COMMENT ON COLUMN cursos_online.cursos.fecha_publicacion IS 'Fecha de publicación del curso';
COMMENT ON COLUMN cursos_online.cursos.activo IS 'Indicador si el curso está activo';

-- Table: cursos_online.evaluaciones
CREATE TABLE cursos_online.evaluaciones (
    id_evaluacion SERIAL NOT NULL,
    id_curso INTEGER,
    id_modulo INTEGER,
    titulo VARCHAR(200) NOT NULL,
    descripcion TEXT,
    tipo VARCHAR(20) NOT NULL,
    duracion_minutos SMALLINT,
    puntaje_minimo NUMERIC(5,2) NOT NULL DEFAULT 60.00,
    intentos_permitidos SMALLINT NOT NULL DEFAULT 3,
    CONSTRAINT pk_evaluaciones PRIMARY KEY (id_evaluacion)
);

COMMENT ON TABLE cursos_online.evaluaciones IS 'Tabla de evaluaciones de cursos o módulos';
COMMENT ON COLUMN cursos_online.evaluaciones.id_evaluacion IS 'Identificador único de la evaluación';
COMMENT ON COLUMN cursos_online.evaluaciones.id_curso IS 'Curso asociado a la evaluación';
COMMENT ON COLUMN cursos_online.evaluaciones.id_modulo IS 'Módulo asociado a la evaluación';
COMMENT ON COLUMN cursos_online.evaluaciones.titulo IS 'Título de la evaluación';
COMMENT ON COLUMN cursos_online.evaluaciones.descripcion IS 'Descripción de la evaluación';
COMMENT ON COLUMN cursos_online.evaluaciones.tipo IS 'Tipo de evaluación (quiz, examen, proyecto)';
COMMENT ON COLUMN cursos_online.evaluaciones.duracion_minutos IS 'Duración de la evaluación en minutos';
COMMENT ON COLUMN cursos_online.evaluaciones.puntaje_minimo IS 'Puntaje mínimo para aprobar';
COMMENT ON COLUMN cursos_online.evaluaciones.intentos_permitidos IS 'Número de intentos permitidos';

-- Table: cursos_online.inscripciones
CREATE TABLE cursos_online.inscripciones (
    id_inscripcion SERIAL NOT NULL,
    id_usuario INTEGER NOT NULL,
    id_curso INTEGER NOT NULL,
    fecha_inscripcion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(20) NOT NULL DEFAULT ''activo'',
    progreso_porcentaje NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    fecha_inicio DATE,
    fecha_finalizacion DATE,
    CONSTRAINT pk_inscripciones PRIMARY KEY (id_inscripcion)
);

COMMENT ON TABLE cursos_online.inscripciones IS 'Tabla de inscripciones de usuarios a cursos';
COMMENT ON COLUMN cursos_online.inscripciones.id_inscripcion IS 'Identificador único de la inscripción';
COMMENT ON COLUMN cursos_online.inscripciones.id_usuario IS 'Usuario que se inscribe';
COMMENT ON COLUMN cursos_online.inscripciones.id_curso IS 'Curso al que se inscribe';
COMMENT ON COLUMN cursos_online.inscripciones.fecha_inscripcion IS 'Fecha de inscripción';
COMMENT ON COLUMN cursos_online.inscripciones.estado IS 'Estado de la inscripción (activo, completado, abandonado)';
COMMENT ON COLUMN cursos_online.inscripciones.progreso_porcentaje IS 'Porcentaje de progreso del curso';
COMMENT ON COLUMN cursos_online.inscripciones.fecha_inicio IS 'Fecha de inicio del curso';
COMMENT ON COLUMN cursos_online.inscripciones.fecha_finalizacion IS 'Fecha de finalización del curso';

-- Table: cursos_online.lecciones
CREATE TABLE cursos_online.lecciones (
    id_leccion SERIAL NOT NULL,
    id_modulo INTEGER NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    contenido TEXT NOT NULL,
    tipo_contenido VARCHAR(30) NOT NULL,
    url_recurso VARCHAR(500),
    orden SMALLINT NOT NULL,
    duracion_minutos SMALLINT,
    CONSTRAINT pk_lecciones PRIMARY KEY (id_leccion)
);

COMMENT ON TABLE cursos_online.lecciones IS 'Tabla de lecciones de los módulos';
COMMENT ON COLUMN cursos_online.lecciones.id_leccion IS 'Identificador único de la lección';
COMMENT ON COLUMN cursos_online.lecciones.id_modulo IS 'Módulo al que pertenece la lección';
COMMENT ON COLUMN cursos_online.lecciones.titulo IS 'Título de la lección';
COMMENT ON COLUMN cursos_online.lecciones.contenido IS 'Contenido textual de la lección';
COMMENT ON COLUMN cursos_online.lecciones.tipo_contenido IS 'Tipo de contenido (video, texto, audio, pdf)';
COMMENT ON COLUMN cursos_online.lecciones.url_recurso IS 'URL del recurso multimedia';
COMMENT ON COLUMN cursos_online.lecciones.orden IS 'Orden de la lección dentro del módulo';
COMMENT ON COLUMN cursos_online.lecciones.duracion_minutos IS 'Duración de la lección en minutos';

-- Table: cursos_online.modulos
CREATE TABLE cursos_online.modulos (
    id_modulo SERIAL NOT NULL,
    id_curso INTEGER NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    descripcion TEXT,
    orden SMALLINT NOT NULL,
    duracion_estimada NUMERIC(5,2),
    CONSTRAINT pk_modulos PRIMARY KEY (id_modulo)
);

COMMENT ON TABLE cursos_online.modulos IS 'Tabla de módulos de los cursos';
COMMENT ON COLUMN cursos_online.modulos.id_modulo IS 'Identificador único del módulo';
COMMENT ON COLUMN cursos_online.modulos.id_curso IS 'Curso al que pertenece el módulo';
COMMENT ON COLUMN cursos_online.modulos.titulo IS 'Título del módulo';
COMMENT ON COLUMN cursos_online.modulos.descripcion IS 'Descripción del módulo';
COMMENT ON COLUMN cursos_online.modulos.orden IS 'Orden del módulo dentro del curso';
COMMENT ON COLUMN cursos_online.modulos.duracion_estimada IS 'Duración estimada del módulo en horas';

-- Table: cursos_online.preguntas
CREATE TABLE cursos_online.preguntas (
    id_pregunta SERIAL NOT NULL,
    id_evaluacion INTEGER NOT NULL,
    texto_pregunta TEXT NOT NULL,
    tipo_pregunta VARCHAR(30) NOT NULL,
    opciones TEXT,
    respuesta_correcta TEXT,
    puntaje NUMERIC(5,2) NOT NULL DEFAULT 1.00,
    orden SMALLINT NOT NULL,
    CONSTRAINT pk_preguntas PRIMARY KEY (id_pregunta)
);

COMMENT ON TABLE cursos_online.preguntas IS 'Tabla de preguntas de evaluaciones';
COMMENT ON COLUMN cursos_online.preguntas.id_pregunta IS 'Identificador único de la pregunta';
COMMENT ON COLUMN cursos_online.preguntas.id_evaluacion IS 'Evaluación a la que pertenece';
COMMENT ON COLUMN cursos_online.preguntas.texto_pregunta IS 'Texto de la pregunta';
COMMENT ON COLUMN cursos_online.preguntas.tipo_pregunta IS 'Tipo (multiple, verdadero_falso, abierta)';
COMMENT ON COLUMN cursos_online.preguntas.opciones IS 'Opciones de respuesta en formato JSON';
COMMENT ON COLUMN cursos_online.preguntas.respuesta_correcta IS 'Respuesta correcta';
COMMENT ON COLUMN cursos_online.preguntas.puntaje IS 'Puntaje de la pregunta';
COMMENT ON COLUMN cursos_online.preguntas.orden IS 'Orden de la pregunta en la evaluación';

-- Table: cursos_online.progreso_lecciones
CREATE TABLE cursos_online.progreso_lecciones (
    id_progreso SERIAL NOT NULL,
    id_inscripcion INTEGER NOT NULL,
    id_leccion INTEGER NOT NULL,
    completado VARCHAR(2) NOT NULL DEFAULT ''NO'',
    fecha_inicio TIMESTAMP,
    fecha_completado TIMESTAMP,
    tiempo_dedicado INTEGER,
    CONSTRAINT pk_progreso_lecciones PRIMARY KEY (id_progreso)
);

COMMENT ON TABLE cursos_online.progreso_lecciones IS 'Tabla de progreso de lecciones por usuario';
COMMENT ON COLUMN cursos_online.progreso_lecciones.id_progreso IS 'Identificador único del progreso';
COMMENT ON COLUMN cursos_online.progreso_lecciones.id_inscripcion IS 'Inscripción asociada';
COMMENT ON COLUMN cursos_online.progreso_lecciones.id_leccion IS 'Lección en progreso';
COMMENT ON COLUMN cursos_online.progreso_lecciones.completado IS 'Indicador si la lección fue completada';
COMMENT ON COLUMN cursos_online.progreso_lecciones.fecha_inicio IS 'Fecha de inicio de la lección';
COMMENT ON COLUMN cursos_online.progreso_lecciones.fecha_completado IS 'Fecha de completado de la lección';
COMMENT ON COLUMN cursos_online.progreso_lecciones.tiempo_dedicado IS 'Tiempo dedicado en segundos';

-- Table: cursos_online.resultados_evaluaciones
CREATE TABLE cursos_online.resultados_evaluaciones (
    id_resultado SERIAL NOT NULL,
    id_evaluacion INTEGER NOT NULL,
    id_inscripcion INTEGER NOT NULL,
    fecha_realizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    puntaje_obtenido NUMERIC(5,2),
    puntaje_maximo NUMERIC(5,2),
    aprobado VARCHAR(2) NOT NULL,
    intento_numero SMALLINT NOT NULL DEFAULT 1,
    respuestas TEXT,
    CONSTRAINT pk_resultados_evaluaciones PRIMARY KEY (id_resultado)
);

COMMENT ON TABLE cursos_online.resultados_evaluaciones IS 'Tabla de resultados de evaluaciones';
COMMENT ON COLUMN cursos_online.resultados_evaluaciones.id_resultado IS 'Identificador único del resultado';
COMMENT ON COLUMN cursos_online.resultados_evaluaciones.id_evaluacion IS 'Evaluación realizada';
COMMENT ON COLUMN cursos_online.resultados_evaluaciones.id_inscripcion IS 'Inscripción del usuario';
COMMENT ON COLUMN cursos_online.resultados_evaluaciones.fecha_realizacion IS 'Fecha de realización de la evaluación';
COMMENT ON COLUMN cursos_online.resultados_evaluaciones.puntaje_obtenido IS 'Puntaje obtenido en la evaluación';
COMMENT ON COLUMN cursos_online.resultados_evaluaciones.puntaje_maximo IS 'Puntaje máximo posible';
COMMENT ON COLUMN cursos_online.resultados_evaluaciones.aprobado IS 'Indicador si aprobó la evaluación';
COMMENT ON COLUMN cursos_online.resultados_evaluaciones.intento_numero IS 'Número de intento';
COMMENT ON COLUMN cursos_online.resultados_evaluaciones.respuestas IS 'Respuestas del usuario en formato JSON';

-- Table: cursos_online.roles
CREATE TABLE cursos_online.roles (
    id_rol SERIAL NOT NULL,
    nombre_rol VARCHAR(50) NOT NULL,
    descripcion TEXT,
    fecha_creacion DATE NOT NULL DEFAULT CURRENT_DATE,
    CONSTRAINT pk_roles PRIMARY KEY (id_rol)
);

COMMENT ON TABLE cursos_online.roles IS 'Tabla de roles de usuario';
COMMENT ON COLUMN cursos_online.roles.id_rol IS 'Identificador único del rol';
COMMENT ON COLUMN cursos_online.roles.nombre_rol IS 'Nombre del rol (Estudiante, Instructor, Administrador)';
COMMENT ON COLUMN cursos_online.roles.descripcion IS 'Descripción detallada del rol';
COMMENT ON COLUMN cursos_online.roles.fecha_creacion IS 'Fecha de creación del rol';

-- Table: cursos_online.usuarios
CREATE TABLE cursos_online.usuarios (
    id_usuario SERIAL NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    telefono VARCHAR(20),
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso TIMESTAMP,
    activo VARCHAR(2) NOT NULL DEFAULT ''SI'',
    CONSTRAINT pk_usuarios PRIMARY KEY (id_usuario)
);

COMMENT ON TABLE cursos_online.usuarios IS 'Tabla de usuarios del sistema';
COMMENT ON COLUMN cursos_online.usuarios.id_usuario IS 'Identificador único del usuario';
COMMENT ON COLUMN cursos_online.usuarios.nombre IS 'Nombre completo del usuario';
COMMENT ON COLUMN cursos_online.usuarios.email IS 'Correo electrónico único del usuario';
COMMENT ON COLUMN cursos_online.usuarios.password_hash IS 'Hash de la contraseña del usuario';
COMMENT ON COLUMN cursos_online.usuarios.telefono IS 'Número de teléfono del usuario';
COMMENT ON COLUMN cursos_online.usuarios.fecha_registro IS 'Fecha y hora de registro del usuario';
COMMENT ON COLUMN cursos_online.usuarios.ultimo_acceso IS 'Fecha y hora del último acceso al sistema';
COMMENT ON COLUMN cursos_online.usuarios.activo IS 'Indicador si el usuario está activo (SI/NO)';

-- Table: cursos_online.usuarios_roles
CREATE TABLE cursos_online.usuarios_roles (
    id_usuario_rol SERIAL NOT NULL,
    id_usuario INTEGER NOT NULL,
    id_rol INTEGER NOT NULL,
    fecha_asignacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_usuarios_roles PRIMARY KEY (id_usuario_rol)
);

COMMENT ON TABLE cursos_online.usuarios_roles IS 'Tabla de relación entre usuarios y roles';
COMMENT ON COLUMN cursos_online.usuarios_roles.id_usuario_rol IS 'Identificador único de la relación';
COMMENT ON COLUMN cursos_online.usuarios_roles.id_usuario IS 'Referencia al usuario';
COMMENT ON COLUMN cursos_online.usuarios_roles.id_rol IS 'Referencia al rol asignado';
COMMENT ON COLUMN cursos_online.usuarios_roles.fecha_asignacion IS 'Fecha de asignación del rol al usuario';

ALTER TABLE cursos_online.categorias
    ADD CONSTRAINT fk_categorias_1
    FOREIGN KEY (id_categoria_padre)
    REFERENCES categorias(id_categoria);

ALTER TABLE cursos_online.certificados
    ADD CONSTRAINT fk_certificados_1
    FOREIGN KEY (id_inscripcion)
    REFERENCES inscripciones(id_inscripcion);

ALTER TABLE cursos_online.cursos
    ADD CONSTRAINT fk_cursos_1
    FOREIGN KEY (id_categoria)
    REFERENCES categorias(id_categoria);

ALTER TABLE cursos_online.cursos
    ADD CONSTRAINT fk_cursos_2
    FOREIGN KEY (id_instructor)
    REFERENCES usuarios(id_usuario);

ALTER TABLE cursos_online.evaluaciones
    ADD CONSTRAINT fk_evaluaciones_1
    FOREIGN KEY (id_curso)
    REFERENCES cursos(id_curso);

ALTER TABLE cursos_online.evaluaciones
    ADD CONSTRAINT fk_evaluaciones_2
    FOREIGN KEY (id_modulo)
    REFERENCES modulos(id_modulo);

ALTER TABLE cursos_online.inscripciones
    ADD CONSTRAINT fk_inscripciones_1
    FOREIGN KEY (id_usuario)
    REFERENCES usuarios(id_usuario);

ALTER TABLE cursos_online.inscripciones
    ADD CONSTRAINT fk_inscripciones_2
    FOREIGN KEY (id_curso)
    REFERENCES cursos(id_curso);

ALTER TABLE cursos_online.lecciones
    ADD CONSTRAINT fk_lecciones_1
    FOREIGN KEY (id_modulo)
    REFERENCES modulos(id_modulo);

ALTER TABLE cursos_online.modulos
    ADD CONSTRAINT fk_modulos_1
    FOREIGN KEY (id_curso)
    REFERENCES cursos(id_curso);

ALTER TABLE cursos_online.preguntas
    ADD CONSTRAINT fk_preguntas_1
    FOREIGN KEY (id_evaluacion)
    REFERENCES evaluaciones(id_evaluacion);

ALTER TABLE cursos_online.progreso_lecciones
    ADD CONSTRAINT fk_progreso_lecciones_1
    FOREIGN KEY (id_inscripcion)
    REFERENCES inscripciones(id_inscripcion);

ALTER TABLE cursos_online.progreso_lecciones
    ADD CONSTRAINT fk_progreso_lecciones_2
    FOREIGN KEY (id_leccion)
    REFERENCES lecciones(id_leccion);

ALTER TABLE cursos_online.resultados_evaluaciones
    ADD CONSTRAINT fk_resultados_evaluaciones_1
    FOREIGN KEY (id_evaluacion)
    REFERENCES evaluaciones(id_evaluacion);

ALTER TABLE cursos_online.resultados_evaluaciones
    ADD CONSTRAINT fk_resultados_evaluaciones_2
    FOREIGN KEY (id_inscripcion)
    REFERENCES inscripciones(id_inscripcion);

ALTER TABLE cursos_online.usuarios_roles
    ADD CONSTRAINT fk_usuarios_roles_1
    FOREIGN KEY (id_usuario)
    REFERENCES usuarios(id_usuario);

ALTER TABLE cursos_online.usuarios_roles
    ADD CONSTRAINT fk_usuarios_roles_2
    FOREIGN KEY (id_rol)
    REFERENCES roles(id_rol);
