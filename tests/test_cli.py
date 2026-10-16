from app.modelos import Usuario


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
