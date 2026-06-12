from src.models import Usuario


def test_usuario_gera_hash_e_valida_senha():
    usuario = Usuario(nome='Maria', email='maria@teste.com', idade=22)

    usuario.set_senha('Senha@123')

    assert usuario.senha_hash != 'Senha@123'
    assert usuario.verificar_senha('Senha@123') is True
    assert usuario.verificar_senha('SenhaErrada') is False


def test_cadastro_cria_usuario_com_senha_hash_e_sessao(client, app):
    resposta = client.post(
        '/cadastro',
        data={
            'nome': 'Maria Silva',
            'email': 'Maria@Teste.com',
            'idade': '24',
            'senha': 'Senha@123',
        },
    )

    assert resposta.status_code == 302
    assert resposta.headers['Location'].endswith('/')

    with app.app_context():
        usuario = Usuario.query.filter_by(email='maria@teste.com').first()
        assert usuario is not None
        assert usuario.nome == 'Maria Silva'
        assert usuario.idade == 24
        assert usuario.senha_hash != 'Senha@123'
        assert usuario.verificar_senha('Senha@123') is True
        usuario_id = usuario.id

    with client.session_transaction() as sessao:
        assert sessao['usuario_id'] == usuario_id
        assert sessao['usuario_nome'] == 'Maria Silva'


def test_cadastro_rejeita_email_duplicado(client, app, criar_usuario):
    criar_usuario(email='maria@teste.com')

    resposta = client.post(
        '/cadastro',
        data={
            'nome': 'Outra Maria',
            'email': 'MARIA@TESTE.COM',
            'idade': '20',
            'senha': 'Senha@123',
        },
    )

    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Este email já está cadastrado.' in corpo

    with app.app_context():
        assert Usuario.query.count() == 1


def test_cadastro_rejeita_menor_de_idade(client, app):
    resposta = client.post(
        '/cadastro',
        data={
            'nome': 'João',
            'email': 'joao@teste.com',
            'idade': '17',
            'senha': 'Senha@123',
        },
    )

    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Você precisa ter pelo menos 18 anos.' in corpo

    with app.app_context():
        assert Usuario.query.count() == 0


def test_cadastro_rejeita_idade_invalida(client, app):
    resposta = client.post(
        '/cadastro',
        data={
            'nome': 'João',
            'email': 'joao@teste.com',
            'idade': 'abc',
            'senha': 'Senha@123',
        },
    )

    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Idade inválida.' in corpo

    with app.app_context():
        assert Usuario.query.count() == 0


def test_cadastro_rejeita_idade_maior_ou_igual_a_125(client, app):
    resposta = client.post(
        '/cadastro',
        data={
            'nome': 'João',
            'email': 'joao@teste.com',
            'idade': '125',
            'senha': 'Senha@123',
        },
    )

    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Digite uma idade válida.' in corpo

    with app.app_context():
        assert Usuario.query.count() == 0


def test_login_autentica_usuario_com_email_normalizado(client, criar_usuario):
    usuario = criar_usuario(nome='Carla', email='carla@teste.com', senha='Senha@123')

    resposta = client.post(
        '/acesso',
        data={
            'email': '  CARLA@TESTE.COM  ',
            'senha': 'Senha@123',
        },
    )

    assert resposta.status_code == 302
    assert resposta.headers['Location'].endswith('/')

    with client.session_transaction() as sessao:
        assert sessao['usuario_id'] == usuario['id']
        assert sessao['usuario_nome'] == 'Carla'


def test_login_rejeita_senha_incorreta(client, criar_usuario):
    criar_usuario(email='carla@teste.com', senha='Senha@123')

    resposta = client.post(
        '/acesso',
        data={
            'email': 'carla@teste.com',
            'senha': 'SenhaErrada',
        },
    )

    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Email ou senha inválidos.' in corpo

    with client.session_transaction() as sessao:
        assert 'usuario_id' not in sessao


def test_login_rejeita_campos_vazios(client):
    resposta = client.post(
        '/acesso',
        data={
            'email': '',
            'senha': '',
        },
    )

    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Preencha email e senha.' in corpo


def test_logout_limpa_a_sessao(client, criar_usuario):
    usuario = criar_usuario(nome='Carla', email='carla@teste.com', senha='Senha@123')

    with client.session_transaction() as sessao:
        sessao['usuario_id'] = usuario['id']
        sessao['usuario_nome'] = usuario['nome']

    resposta = client.get('/sair')

    assert resposta.status_code == 302
    assert resposta.headers['Location'].endswith('/')

    with client.session_transaction() as sessao:
        assert 'usuario_id' not in sessao
        assert 'usuario_nome' not in sessao
