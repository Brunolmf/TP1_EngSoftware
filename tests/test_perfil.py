from src.models import Avaliacao, Estabelecimento, Usuario, db


def login(client, usuario_id):
    with client.session_transaction() as sessao:
        sessao['usuario_id'] = usuario_id


def dados_perfil(**overrides):
    dados = {
        'nome': 'Nome Atualizado',
        'email': 'novo@teste.com',
        'idade': '30',
        'senha': '',
    }
    dados.update(overrides)
    return dados


# ---------------------------------------------------------------------------
# /perfil (editar_perfil)
# ---------------------------------------------------------------------------

def test_perfil_exige_login(client):
    resposta = client.get('/perfil')

    assert resposta.status_code == 302
    assert resposta.headers['Location'].endswith('/acesso')


def test_perfil_renderiza_para_usuario_logado(client, criar_usuario):
    usuario = criar_usuario(nome='Original', email='original@teste.com')
    login(client, usuario['id'])

    resposta = client.get('/perfil')
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Original' in corpo


def test_perfil_atualiza_dados_com_sucesso(client, app, criar_usuario):
    usuario = criar_usuario(email='original@teste.com')
    login(client, usuario['id'])

    resposta = client.post(
        '/perfil',
        data=dados_perfil(nome='Maria Nova', email='maria.nova@teste.com', idade='28'),
        follow_redirects=True,
    )
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Perfil atualizado com sucesso!' in corpo

    with app.app_context():
        atualizado = db.session.get(Usuario, usuario['id'])
        assert atualizado.nome == 'Maria Nova'
        assert atualizado.email == 'maria.nova@teste.com'
        assert atualizado.idade == 28


def test_perfil_atualiza_senha_quando_informada(client, app, criar_usuario):
    usuario = criar_usuario(email='original@teste.com', senha='Senha@123')
    login(client, usuario['id'])

    client.post('/perfil', data=dados_perfil(senha='NovaSenha@456'))

    with app.app_context():
        atualizado = db.session.get(Usuario, usuario['id'])
        assert atualizado.verificar_senha('NovaSenha@456') is True
        assert atualizado.verificar_senha('Senha@123') is False


def test_perfil_rejeita_campos_obrigatorios_vazios(client, criar_usuario):
    usuario = criar_usuario(email='original@teste.com')
    login(client, usuario['id'])

    resposta = client.post(
        '/perfil',
        data=dados_perfil(nome=''),
        follow_redirects=True,
    )
    corpo = resposta.get_data(as_text=True)

    assert 'Campos obrigatórios não preenchidos.' in corpo


def test_perfil_rejeita_email_de_outro_usuario(client, criar_usuario):
    criar_usuario(email='ocupado@teste.com')
    usuario = criar_usuario(email='original@teste.com')
    login(client, usuario['id'])

    resposta = client.post(
        '/perfil',
        data=dados_perfil(email='ocupado@teste.com'),
        follow_redirects=True,
    )
    corpo = resposta.get_data(as_text=True)

    assert 'Este email já está em uso.' in corpo


def test_perfil_rejeita_idade_nao_numerica(client, criar_usuario):
    usuario = criar_usuario(email='original@teste.com')
    login(client, usuario['id'])

    resposta = client.post(
        '/perfil',
        data=dados_perfil(idade='abc'),
        follow_redirects=True,
    )
    corpo = resposta.get_data(as_text=True)

    assert 'Idade inválida.' in corpo


def test_perfil_rejeita_menor_de_idade(client, criar_usuario):
    usuario = criar_usuario(email='original@teste.com')
    login(client, usuario['id'])

    resposta = client.post(
        '/perfil',
        data=dados_perfil(idade='16'),
        follow_redirects=True,
    )
    corpo = resposta.get_data(as_text=True)

    assert 'Você precisa ter pelo menos 18 anos.' in corpo


def test_perfil_rejeita_idade_maior_ou_igual_a_125(client, criar_usuario):
    usuario = criar_usuario(email='original@teste.com')
    login(client, usuario['id'])

    resposta = client.post(
        '/perfil',
        data=dados_perfil(idade='130'),
        follow_redirects=True,
    )
    corpo = resposta.get_data(as_text=True)

    assert 'Digite uma idade válida.' in corpo


def test_perfil_calcula_media_das_avaliacoes_do_usuario(client, app, criar_usuario):
    usuario = criar_usuario(email='original@teste.com')

    with app.app_context():
        bar = Estabelecimento(nome='Bar Teste', endereco='Rua B')
        db.session.add(bar)
        db.session.commit()
        db.session.add_all([
            Avaliacao(nota=4.0, usuario_id=usuario['id'], estabelecimento_id=bar.id),
            Avaliacao(nota=2.0, usuario_id=usuario['id'], estabelecimento_id=bar.id),
        ])
        db.session.commit()

    login(client, usuario['id'])
    resposta = client.get('/perfil')

    assert resposta.status_code == 200
    # média de 4.0 e 2.0 = 3.0
    assert '3.0' in resposta.get_data(as_text=True)
