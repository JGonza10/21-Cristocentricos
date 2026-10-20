from app.extensiones import db
from app.modelos import Evento, Integrante, Usuario


def test_crear_usuario(app):
    r = app.test_cli_runner().invoke(args=["crear-usuario"],
                                     input="aprobador\nAprobador\nclave-larga-2026\nclave-larga-2026\n")
    assert r.exit_code == 0, r.output
    with app.app_context():
        assert Usuario.query.filter_by(usuario="aprobador").first() is not None


def test_rechaza_password_debil_y_vuelve_a_pedir(app):
    r = app.test_cli_runner().invoke(args=["crear-usuario"],
                                     input="ana\nAna\ncorta\ncorta\nclave-larga-2026\nclave-larga-2026\n")
    assert r.exit_code == 0
    assert "al menos 10" in r.output


def test_maximo_dos_usuarios(app):
    runner = app.test_cli_runner()
    runner.invoke(args=["crear-usuario"], input="ana\nAna\nclave-larga-2026\nclave-larga-2026\n")
    r = runner.invoke(args=["crear-usuario"], input="beto\nBeto\nclave-larga-2026\nclave-larga-2026\n")
    assert r.exit_code != 0
    assert "máximo" in r.output


def test_cambiar_password(app):
    r = app.test_cli_runner().invoke(args=["cambiar-password", "gonza"],
                                     input="nueva-clave-2026\nnueva-clave-2026\n")
    assert r.exit_code == 0


def test_limpiar_datos_deja_la_base_en_blanco(app, tmp_path):
    app.config["PAQUETES_DIR"] = tmp_path / "paquetes"
    (tmp_path / "paquetes" / "2026-10-22").mkdir(parents=True)
    with app.app_context():
        i = Integrante(nombre="Esbeidy")
        ev = Evento(fecha=__import__("datetime").date(2026, 10, 22), tema="No tengas miedo")
        ev.integrantes = [i]
        db.session.add(ev)
        db.session.commit()
    runner = app.test_cli_runner()
    assert runner.invoke(args=["limpiar-datos"], input="n\n").exit_code != 0  # pide confirmar
    r = runner.invoke(args=["limpiar-datos", "--yes"])
    assert r.exit_code == 0, r.output
    with app.app_context():
        assert Evento.query.count() == 0 and Integrante.query.count() == 0
        assert Usuario.query.count() == 1  # las cuentas se quedan
    assert not (tmp_path / "paquetes").exists()
    assert runner.invoke(args=["limpiar-datos", "--yes", "--con-usuarios"]).exit_code == 0
    with app.app_context():
        assert Usuario.query.count() == 0
