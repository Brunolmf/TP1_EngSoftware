import sys
from pathlib import Path
from threading import Thread

import pytest
from werkzeug.serving import make_server

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app import create_app
from src.models import Estabelecimento, Usuario, db


@pytest.fixture()
def app(tmp_path):
    database_path = tmp_path / 'saideira_test.db'
    app = create_app(
        {
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{database_path}',
            'SECRET_KEY': 'test-secret-key',
        }
    )

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


@pytest.fixture()
def criar_usuario(app):
    def _criar_usuario(
        nome='Usuário Teste',
        email='teste@teste.com',
        senha='Senha@123',
        idade=25,
        is_admin=False,
    ):
        with app.app_context():
            usuario = Usuario(
                nome=nome,
                email=email.lower(),
                idade=idade,
                is_admin=is_admin,
            )
            usuario.set_senha(senha)
            db.session.add(usuario)
            db.session.commit()

            return {
                'id': usuario.id,
                'nome': usuario.nome,
                'email': usuario.email,
                'senha': senha,
            }

    return _criar_usuario


@pytest.fixture()
def criar_estabelecimento(app):
    def _criar_estabelecimento(
        nome='Bar Teste',
        endereco='Rua da Serra, 123 - Belo Horizonte',
        foto_url='https://example.com/bar.jpg',
        faixa_de_preco='$$',
        adicionado_por=None,
    ):
        with app.app_context():
            estabelecimento = Estabelecimento(
                nome=nome,
                endereco=endereco,
                foto_url=foto_url,
                faixa_de_preco=faixa_de_preco,
                adicionado_por=adicionado_por,
            )
            db.session.add(estabelecimento)
            db.session.commit()

            return {
                'id': estabelecimento.id,
                'nome': estabelecimento.nome,
                'endereco': estabelecimento.endereco,
                'foto_url': estabelecimento.foto_url,
                'faixa_de_preco': estabelecimento.faixa_de_preco,
                'adicionado_por': estabelecimento.adicionado_por,
            }

    return _criar_estabelecimento


@pytest.fixture()
def login_como(client):
    def _login_como(usuario):
        with client.session_transaction() as sessao:
            sessao['usuario_id'] = usuario['id']
            sessao['usuario_nome'] = usuario['nome']

    return _login_como


@pytest.fixture()
def live_server(app):
    server = make_server('127.0.0.1', 0, app)
    thread = Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        thread.join()
