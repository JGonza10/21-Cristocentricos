import sqlite3

from agentes import carrusel, worker
from agentes.estado import latido
from app import create_app
from app.extensiones import db
from app.modelos import EstadoAgente

from .conftest import login


def test_migracion_agrega_columnas_sin_borrar_datos(tmp_path):
    """Una base de la fase 2 (sin la columna 'datos') se actualiza sola al arrancar."""
    ruta = tmp_path / "vieja.db"
    con = sqlite3.connect(ruta)
    con.execute("""CREATE TABLE paquetes (id INTEGER PRIMARY KEY, tipo VARCHAR(20) NOT NULL,
        fecha_evento DATE NOT NULL, titulo VARCHAR(120) NOT NULL, texto TEXT NOT NULL,
        carpeta VARCHAR(200) NOT NULL, archivos JSON NOT NULL, estado VARCHAR(20) NOT NULL,
        motivo_rechazo VARCHAR(300), version INTEGER NOT NULL, creado DATETIME NOT NULL,
        actualizado DATETIME NOT NULL, revisado_por_id INTEGER, revisado_en DATETIME)""")
    con.execute("""INSERT INTO paquetes VALUES (1, 'carrusel', '2026-10-19', 'Viejo', 't', '', '[]',
        'pendiente', NULL, 1, '2026-10-16 10:00:00', '2026-10-16 10:00:00', NULL, NULL)""")
    con.commit()
    con.close()
    app = create_app({"TESTING": True, "SECRET_KEY": "x", "SQLALCHEMY_DATABASE_URI": f"sqlite:///{ruta}",
                      "LOG_DIR": tmp_path / "logs"})
    with app.app_context():
        from app.modelos import Paquete
        p = db.session.get(Paquete, 1)
        assert p.titulo == "Viejo" and p.datos is None
        assert db.session.execute(db.text("PRAGMA journal_mode")).scalar() == "wal"


def test_planificador_tiene_todos_los_agentes(app):
    sched = worker.crear_planificador(app)
    ids = {j.id for j in sched.get_jobs()}
    assert ids == {"latido", "carrusel", "reels", "recortes", "publicacion", "reparto", "invitaciones"}
    reparto = sched.get_job("reparto").trigger
    assert "day_of_week='sun'" in str(reparto) and "hour='18'" in str(reparto)


def test_agente_que_falla_no_tumba_al_worker(app, monkeypatch):
    def explota():
        raise RuntimeError("boom")
    monkeypatch.setattr(carrusel, "tarea", explota)
    sched = worker.crear_planificador(app)
    sched.get_job("carrusel").func()             # no lanza excepción
    with app.app_context():
        e = db.session.get(EstadoAgente, "carrusel")
        assert e.error and "boom" not in e.mensaje


def test_estado_general(app, cliente):
    login(cliente)
    d = cliente.get("/api/estado").get_json()
    assert d["worker_activo"] is False and d["google"] is False and d["meta"] is False
    assert d["bandeja"] == {"pendiente": 0, "aprobado": 0, "rechazado": 0}
    with app.app_context():
        latido("worker", "Activo", ok=True)
        latido("reels", "1 reel nuevo en la bandeja", ok=True)
    d = cliente.get("/api/estado").get_json()
    assert d["worker_activo"] is True
    reels = next(a for a in d["agentes"] if a["nombre"] == "reels")
    assert reels["mensaje"] == "1 reel nuevo en la bandeja" and reels["titulo"] == "Reels"


def test_estado_trae_conteos_para_el_diagrama(app, cliente):
    from datetime import date

    from app.bandeja import crear_paquete
    from app.modelos import Grabacion, Publicacion
    login(cliente)
    d = cliente.get("/api/estado").get_json()
    assert d["pendientes_por_tipo"] == {} and d["grabaciones_conteo"] == {} and d["publicaciones_conteo"] == {}
    with app.app_context():
        crear_paquete("carrusel", date(2026, 10, 19), "Invitación")
        reel = crear_paquete("reel", date(2026, 10, 19), "Reel 1")
        crear_paquete("reel", date(2026, 10, 19), "Reel 2")
        db.session.add(Grabacion(nombre="evento.mkv", estado="procesando"))
        db.session.add(Publicacion(paquete_id=reel.id, red="youtube", estado="error"))
        db.session.commit()
    d = cliente.get("/api/estado").get_json()
    assert d["pendientes_por_tipo"] == {"carrusel": 1, "reel": 2}
    assert d["grabaciones_conteo"] == {"procesando": 1}
    assert d["publicaciones_conteo"] == {"error": 1}
    assert d["publicaciones_por_red"] == {"youtube": {"error": 1}}
