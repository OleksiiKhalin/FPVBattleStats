def test_backend_package_imports() -> None:
    from backend.app.main import app

    assert app.title == "FPVBattle Stats API"
