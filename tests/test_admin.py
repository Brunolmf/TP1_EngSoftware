from src.models import Estabelecimento, Usuario, db


def login(client, usuario_id):
    with client.session_transaction() as sessao:
        sessao['usuario_id'] = usuario_id


def criar_bar(app, nome='Boteco do Zé', endereco='Rua A, 123', adicionado_por=None):
    with app.app_context():
        bar = Estabelecimento(
            nome=nome,
            endereco=endereco,
            adicionado_por=adicionado_por,
        )
        db.session.add(bar)
        db.session.commit()
        return bar.id


# ---------------------------------------------------------------------------
# /admin/usuarios
# ---------------------------------------------------------------------------

def test_admin_usuarios_redireciona_visitante_para_acesso(client):
    resposta = client.get('/admin/usuarios')

    assert resposta.status_code == 302
    assert resposta.headers['Location'].endswith('/acesso')


def test_admin_usuarios_nega_acesso_a_usuario_comum(client, criar_usuario):
    usuario = criar_usuario(email='comum@teste.com', is_admin=False)
    login(client, usuario['id'])

    resposta = client.get('/admin/usuarios', follow_redirects=True)
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Acesso negado.' in corpo


def test_admin_usuarios_lista_usuarios_para_admin(client, criar_usuario):
    admin = criar_usuario(nome='Chefe', email='admin@teste.com', is_admin=True)
    criar_usuario(nome='Fulano Listado', email='fulano@teste.com')
    login(client, admin['id'])

    resposta = client.get('/admin/usuarios')
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Fulano Listado' in corpo


# ---------------------------------------------------------------------------
# /bar/adicionar
# ---------------------------------------------------------------------------

def test_adicionar_bar_exige_login(client):
    resposta = client.get('/bar/adicionar')

    assert resposta.status_code == 302
    assert resposta.headers['Location'].endswith('/acesso')


def test_adicionar_bar_nega_usuario_comum(client, criar_usuario):
    usuario = criar_usuario(email='comum@teste.com', is_admin=False)
    login(client, usuario['id'])

    resposta = client.get('/bar/adicionar', follow_redirects=True)
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'apenas administradores podem adicionar bares' in corpo


def test_adicionar_bar_renderiza_formulario_para_admin(client, criar_usuario):
    admin = criar_usuario(email='admin@teste.com', is_admin=True)
    login(client, admin['id'])

    resposta = client.get('/bar/adicionar')

    assert resposta.status_code == 200


def test_adicionar_bar_cria_estabelecimento_com_dados_validos(client, app, criar_usuario):
    admin = criar_usuario(email='admin@teste.com', is_admin=True)
    login(client, admin['id'])

    resposta = client.post(
        '/bar/adicionar',
        data={
            'nome': 'Bar da Esquina',
            'endereco': 'Av. Brasil, 1000',
            'foto_url': 'http://exemplo.com/foto.jpg',
            'faixa_de_preco': '$$',
        },
    )

    assert resposta.status_code == 302
    assert resposta.headers['Location'].endswith('/')

    with app.app_context():
        bar = Estabelecimento.query.filter_by(nome='Bar da Esquina').first()
        assert bar is not None
        assert bar.endereco == 'Av. Brasil, 1000'
        assert bar.adicionado_por == admin['id']


def test_adicionar_bar_rejeita_campos_obrigatorios_vazios(client, app, criar_usuario):
    admin = criar_usuario(email='admin@teste.com', is_admin=True)
    login(client, admin['id'])

    resposta = client.post(
        '/bar/adicionar',
        data={'nome': '', 'endereco': ''},
        follow_redirects=True,
    )
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Nome e Endereço são campos obrigatórios.' in corpo

    with app.app_context():
        assert Estabelecimento.query.count() == 0


# ---------------------------------------------------------------------------
# /admin/usuarios/deletar/<id>
# ---------------------------------------------------------------------------

def test_deletar_usuario_exige_login(client):
    resposta = client.post('/admin/usuarios/deletar/1')

    assert resposta.status_code == 302
    assert resposta.headers['Location'].endswith('/acesso')


def test_deletar_usuario_nega_usuario_comum(client, criar_usuario):
    comum = criar_usuario(email='comum@teste.com', is_admin=False)
    alvo = criar_usuario(email='alvo@teste.com')
    login(client, comum['id'])

    resposta = client.post(
        f'/admin/usuarios/deletar/{alvo["id"]}',
        follow_redirects=True,
    )
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Operação não permitida.' in corpo


def test_deletar_usuario_inexistente_retorna_404(client, criar_usuario):
    admin = criar_usuario(email='admin@teste.com', is_admin=True)
    login(client, admin['id'])

    resposta = client.post('/admin/usuarios/deletar/9999')

    assert resposta.status_code == 404


def test_deletar_usuario_admin_nao_remove_outro_admin(client, app, criar_usuario):
    admin = criar_usuario(email='admin@teste.com', is_admin=True)
    outro_admin = criar_usuario(email='outro@teste.com', is_admin=True)
    login(client, admin['id'])

    resposta = client.post(
        f'/admin/usuarios/deletar/{outro_admin["id"]}',
        follow_redirects=True,
    )
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Não é possível remover um administrador.' in corpo

    with app.app_context():
        assert db.session.get(Usuario, outro_admin['id']) is not None


def test_deletar_usuario_comum_remove_do_banco(client, app, criar_usuario):
    admin = criar_usuario(email='admin@teste.com', is_admin=True)
    alvo = criar_usuario(email='alvo@teste.com')
    login(client, admin['id'])

    resposta = client.post(
        f'/admin/usuarios/deletar/{alvo["id"]}',
        follow_redirects=True,
    )
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'removido com sucesso' in corpo

    with app.app_context():
        assert db.session.get(Usuario, alvo['id']) is None


def test_deletar_usuario_preserva_bar_e_desassocia_autor(client, app, criar_usuario):
    admin = criar_usuario(email='admin@teste.com', is_admin=True)
    autor = criar_usuario(email='autor@teste.com')
    bar_id = criar_bar(app, nome='Bar do Autor', adicionado_por=autor['id'])
    login(client, admin['id'])

    resposta = client.post(
        f'/admin/usuarios/deletar/{autor["id"]}',
        follow_redirects=True,
    )

    assert resposta.status_code == 200

    with app.app_context():
        assert db.session.get(Usuario, autor['id']) is None
        bar = db.session.get(Estabelecimento, bar_id)
        assert bar is not None
        assert bar.adicionado_por is None
