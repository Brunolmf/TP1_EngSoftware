from html import unescape

from src.models import Estabelecimento, Usuario, db


def test_adicionar_bar_redireciona_visitante_para_acesso(client):
    resposta = client.get('/bar/adicionar')

    assert resposta.status_code == 302
    assert resposta.headers['Location'].endswith('/acesso')


def test_adicionar_bar_bloqueia_usuario_comum(client, criar_usuario, login_como):
    usuario = criar_usuario(nome='Cliente', email='cliente@teste.com')
    login_como(usuario)

    resposta = client.get('/bar/adicionar', follow_redirects=True)
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Acesso negado: apenas administradores podem adicionar bares.' in corpo


def test_adicionar_bar_admin_exibe_formulario(client, criar_usuario, login_como):
    admin = criar_usuario(nome='Admin', email='admin@teste.com', is_admin=True)
    login_como(admin)

    resposta = client.get('/bar/adicionar')
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Novo Estabelecimento' in corpo
    assert 'Cadastrar Bar' in corpo


def test_adicionar_bar_admin_persiste_estabelecimento(client, app, criar_usuario, login_como):
    admin = criar_usuario(nome='Admin', email='admin@teste.com', is_admin=True)
    login_como(admin)

    resposta = client.post(
        '/bar/adicionar',
        data={
            'nome': 'Bar do Codex',
            'endereco': 'Rua dos Testes, 42 - Belo Horizonte',
            'foto_url': 'https://example.com/codex.jpg',
            'faixa_de_preco': '$$$',
        },
        follow_redirects=True,
    )
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Boteco "Bar do Codex" cadastrado com sucesso!' in unescape(corpo)

    with app.app_context():
        bar = Estabelecimento.query.filter_by(nome='Bar do Codex').first()
        assert bar is not None
        assert bar.endereco == 'Rua dos Testes, 42 - Belo Horizonte'
        assert bar.foto_url == 'https://example.com/codex.jpg'
        assert bar.faixa_de_preco == '$$$'
        assert bar.adicionado_por == admin['id']


def test_adicionar_bar_valida_campos_obrigatorios(client, app, criar_usuario, login_como):
    admin = criar_usuario(nome='Admin', email='admin@teste.com', is_admin=True)
    login_como(admin)

    resposta = client.post(
        '/bar/adicionar',
        data={
            'nome': '',
            'endereco': 'Rua sem nome, 0',
            'foto_url': '',
            'faixa_de_preco': '$',
        },
        follow_redirects=True,
    )
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Nome e Endereço são campos obrigatórios.' in corpo

    with app.app_context():
        assert Estabelecimento.query.count() == 0


def test_admin_usuarios_exige_login(client):
    resposta = client.get('/admin/usuarios')

    assert resposta.status_code == 302
    assert resposta.headers['Location'].endswith('/acesso')


def test_admin_usuarios_bloqueia_usuario_comum(client, criar_usuario, login_como):
    usuario = criar_usuario(nome='Cliente', email='cliente@teste.com')
    login_como(usuario)

    resposta = client.get('/admin/usuarios', follow_redirects=True)
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Acesso negado.' in corpo


def test_admin_usuarios_admin_lista_usuarios(client, criar_usuario, login_como):
    admin = criar_usuario(nome='Admin', email='admin@teste.com', is_admin=True)
    criar_usuario(nome='Cliente', email='cliente@teste.com')
    login_como(admin)

    resposta = client.get('/admin/usuarios')
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Painel de Controle: Usuários' in corpo
    assert 'Admin' in corpo
    assert 'cliente@teste.com' in corpo


def test_deletar_usuario_exige_login(client):
    resposta = client.post('/admin/usuarios/deletar/1')

    assert resposta.status_code == 302
    assert resposta.headers['Location'].endswith('/acesso')


def test_deletar_usuario_bloqueia_usuario_comum(client, app, criar_usuario, login_como):
    usuario = criar_usuario(nome='Cliente', email='cliente@teste.com')
    alvo = criar_usuario(nome='Alvo', email='alvo@teste.com')
    login_como(usuario)

    resposta = client.post(
        f"/admin/usuarios/deletar/{alvo['id']}",
        follow_redirects=True,
    )
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Operação não permitida.' in corpo

    with app.app_context():
        assert Usuario.query.filter_by(email='alvo@teste.com').first() is not None


def test_deletar_usuario_admin_nao_remove_administrador(client, app, criar_usuario, login_como):
    admin_logado = criar_usuario(nome='Admin Principal', email='admin1@teste.com', is_admin=True)
    admin_protegido = criar_usuario(nome='Admin Protegido', email='admin2@teste.com', is_admin=True)
    login_como(admin_logado)

    resposta = client.post(
        f"/admin/usuarios/deletar/{admin_protegido['id']}",
        follow_redirects=True,
    )
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Não é possível remover um administrador.' in corpo

    with app.app_context():
        assert Usuario.query.filter_by(email='admin2@teste.com').first() is not None


def test_deletar_usuario_admin_remove_usuario_e_preserva_bares(
    client,
    app,
    criar_usuario,
    criar_estabelecimento,
    login_como,
):
    admin = criar_usuario(nome='Admin', email='admin@teste.com', is_admin=True)
    usuario = criar_usuario(nome='Cliente', email='cliente@teste.com')
    bar = criar_estabelecimento(
        nome='Bar Herdado',
        adicionado_por=usuario['id'],
    )
    login_como(admin)

    resposta = client.post(
        f"/admin/usuarios/deletar/{usuario['id']}",
        follow_redirects=True,
    )
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Usuário Cliente removido com sucesso!' in corpo

    with app.app_context():
        assert Usuario.query.filter_by(email='cliente@teste.com').first() is None
        bar_atualizado = db.session.get(Estabelecimento, bar['id'])
        assert bar_atualizado is not None
        assert bar_atualizado.adicionado_por is None
