-- Habilitar extensión vector
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabla preguntas_frecuentes
CREATE TABLE IF NOT EXISTS preguntas_frecuentes (
    id SERIAL PRIMARY KEY,
    pregunta TEXT NOT NULL,
    respuesta TEXT NOT NULL,
    intencion VARCHAR(100),
    frecuencia INT DEFAULT 0,
    embedding vector(384)
);

-- Tabla productos
CREATE TABLE IF NOT EXISTS productos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    precio DECIMAL(10, 2) NOT NULL,
    disponible BOOLEAN DEFAULT TRUE,
    stock INT DEFAULT 0,
    categoria VARCHAR(50),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla logs_interacciones
CREATE TABLE IF NOT EXISTS logs_interacciones (
    id SERIAL PRIMARY KEY,
    pregunta_usuario TEXT NOT NULL,
    intencion_detectada VARCHAR(100),
    id_pregunta_frecuente INT,
    id_producto INT,
    respuesta_generada TEXT,
    fuente_respuesta VARCHAR(50),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    canal VARCHAR(50),
    CONSTRAINT fk_faq      FOREIGN KEY (id_pregunta_frecuente) REFERENCES preguntas_frecuentes(id),
    CONSTRAINT fk_producto FOREIGN KEY (id_producto)           REFERENCES productos(id)
);

-- Tabla logs_errores
CREATE TABLE IF NOT EXISTS logs_errores (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    descripcion TEXT NOT NULL
);

-- Datos de prueba FAQ
INSERT INTO preguntas_frecuentes (pregunta, respuesta, intencion) VALUES
('¿Cuáles son los métodos de pago disponibles?', 'Aceptamos pagos por Nequi, Daviplata, PSE, tarjeta débito/crédito y efectivo contraentrega.', 'Métodos de pago'),
('¿Cuánto tarda el domicilio?', 'El tiempo estimado es de 30 a 60 minutos en Cali.', 'Tiempos de entrega'),
('¿Qué sabores de cheesecake tienen hoy?', 'Hoy tenemos de maracuyá, frutos rojos, limón y Oreo.', 'Disponibilidad de sabores'),
('¿Hacen envíos a otras ciudades?', 'Actualmente solo operamos en Cali y sus alrededores.', 'Cobertura'),
('¿Cómo hago un pedido por WhatsApp?', 'Puedes escribirnos al +57 310 1234567 y uno de nuestros asesores tomará tu pedido.', 'Canal de venta'),
('¿Tienen opción sin azúcar o sin lactosa?', 'Sí, contamos con línea sin azúcar y sin lactosa. Consulta disponibilidad del día.', 'Requisitos dietéticos'),
('¿Puedo programar un pedido para una hora específica?', 'Sí, solo indícanos la hora y lo programamos con mínimo 2h de anticipación.', 'Pedidos programados'),
('¿Puedo hacer pedidos para eventos?', 'Claro, hacemos paquetes especiales para eventos. Contáctanos al WhatsApp.', 'Eventos y pedidos grandes'),
('¿Cuál es el horario de atención?', 'Lunes a sábado de 9:00 a.m. a 8:00 p.m. y domingos hasta las 6:00 p.m.', 'Horario'),
('¿Dónde están ubicados?', 'Nuestra sede principal está en el barrio Granada, Cali.', 'Ubicación');

-- Datos de prueba Productos
INSERT INTO productos (nombre, descripcion, precio, stock, categoria) VALUES
('Cheesecake de Maracuyá', 'Postre suave con cobertura de maracuyá natural', 12000, 15, 'Cheesecake'),
('Cheesecake de Frutos Rojos', 'Base crocante con frutos rojos frescos', 13000, 10, 'Cheesecake'),
('Cheesecake de Limón', 'Postre refrescante con sabor a limón', 12000, 8, 'Cheesecake'),
('Cheesecake de Oreo', 'Delicioso postre con base de galleta Oreo', 13500, 20, 'Cheesecake'),
('Brownie Clásico', 'Brownie de chocolate con nueces', 8000, 25, 'Brownie'),
('Torta de Zanahoria', 'Torta húmeda con glaseado de queso crema', 10000, 12, 'Torta'),
('Brownie Vegano', 'Brownie sin productos animales', 8500, 10, 'Brownie'),
('Torta Red Velvet', 'Bizcocho rojo con cobertura de queso crema', 12000, 5, 'Torta'),
('Postre Sin Azúcar', 'Postre endulzado con stevia, ideal para diabéticos', 9000, 7, 'Sin Azúcar'),
('Tarta de Mango', 'Tarta con base crocante y mango fresco', 11500, 9, 'Tarta');
