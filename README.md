# TP1_EngSoftware

**Membros:** Bruno Lopes Melo Fonseca (Full stack), Gabriel Alkmim Barros (Full stack), Felipe Araujo Melo (Full stack)

## Sobre o projeto

O **Saideira** e uma aplicacao web em Flask voltada para descoberta e avaliacao de bares em Belo Horizonte. A proposta do sistema e funcionar como um diario social da vida noturna: usuarios podem criar conta, explorar estabelecimentos, publicar reviews com notas por categoria e acompanhar a reputacao de cada lugar.

Pelo codigo atual, o sistema possui tres eixos principais:

- exploracao publica de bares e avaliacoes
- autenticacao e gerenciamento de perfil
- administracao de estabelecimentos e usuarios

## Tecnologias

- Python
- Flask
- Flask-SQLAlchemy
- SQLAlchemy ORM
- SQLite ou PostgreSQL via `DATABASE_URL`
- HTML/CSS com templates Jinja2
- Playwright para scraping de bares

## Funcionalidades principais

- listar bares na pagina inicial com busca por nome
- visualizar detalhes e avaliacoes de um bar
- criar conta com validacao de idade minima
- fazer login e logout com sessao Flask
- editar perfil do usuario
- publicar avaliacao com notas separadas para bebida, comida, ambiente e servico
- cadastrar novos estabelecimentos como administrador
- listar e remover usuarios como administrador

## Documentacao UML preliminar

Os diagramas abaixo foram revisados a partir do codigo atual em `src/app.py`, `src/models.py`, `src/templates/`, `seed_avaliacoes.py` e `scraper/scraper_bares.py`.

Os dois tipos UML exigidos pelo trabalho estao cobertos por:

- **diagrama de classes**
- **diagrama de sequencia**

Os fluxogramas complementam a documentacao com uma visao mais direta de navegacao e arquitetura.

### 1. Fluxo funcional por perfil

Este fluxograma resume o que cada perfil consegue fazer e quais rotas aparecem no fluxo principal de uso.

```mermaid
flowchart TD
    H["/<br/>listar e buscar bares"]
    D["/bar/{id}<br/>ver detalhes e avaliacoes"]
    C["/cadastro<br/>criar conta"]
    L["/acesso<br/>entrar com email e senha"]
    P["/perfil<br/>editar nome, email, idade e senha"]
    A["POST /bar/{id}/avaliar<br/>enviar review com 4 categorias"]
    S["/sair<br/>encerrar sessao"]
    NB["/bar/adicionar<br/>cadastrar estabelecimento"]
    AU["/admin/usuarios<br/>listar usuarios"]
    DU["POST /admin/usuarios/deletar/{id}<br/>remover usuario comum"]

    subgraph Visitante
        H
        D
        C
        L
    end

    subgraph UsuarioAutenticado["Usuario autenticado"]
        P
        A
        S
    end

    subgraph Administrador
        NB
        AU
        DU
    end

    H --> D
    H --> C
    H --> L
    C --> P
    L --> P
    D -. requer login .-> A
    P --> S
    P -. se usuario.is_admin .-> NB
    P -. se usuario.is_admin .-> AU
    AU --> DU
```

### 2. Visao de componentes e responsabilidades

Este diagrama mostra como a aplicacao web se organiza entre interface, camada Flask, modelos, banco e scripts auxiliares.

```mermaid
flowchart TD
    Browser["Browser (cliente)<br/>HTML renderizado, formularios e requisicoes HTTP"]
    Flask["Flask - src/app.py<br/>rotas, sessao, validacoes e renderizacao"]
    Models["SQLAlchemy - src/models.py<br/>Usuario, Estabelecimento e Avaliacao"]
    DB[("Banco de dados relacional<br/>SQLite/PostgreSQL")]
    Seed["seed_avaliacoes.py<br/>gera avaliacoes de teste"]
    Scraper["scraper/scraper_bares.py<br/>coleta bares em JSON"]
    JSON["arquivo JSON local<br/>base coletada externamente"]

    Browser --> Flask
    Flask --> Models
    Models --> DB
    Seed --> Flask
    Seed --> DB
    Scraper --> JSON
```

### 3. Diagrama de classes do dominio

Este e o diagrama UML mais importante para entender o nucleo do sistema e a relacao entre usuarios, bares e reviews.

```mermaid
classDiagram
    class Usuario {
        +int id
        +string nome
        +string email
        +string senha_hash
        +bool is_admin
        +int idade
        +datetime data_criacao
        +set_senha(senha)
        +verificar_senha(senha)
    }

    class Estabelecimento {
        +int id
        +string nome
        +string endereco
        +string foto_url
        +string faixa_de_preco
        +int adicionado_por
    }

    class Avaliacao {
        +int id
        +float nota
        +text texto_review
        +float avaliacao_bebida
        +float avaliacao_comida
        +float avaliacao_ambiente
        +float avaliacao_servico
        +datetime data_avaliacao
        +int usuario_id
        +int estabelecimento_id
    }

    Usuario "1" --> "0..*" Avaliacao : escreve
    Estabelecimento "1" --> "0..*" Avaliacao : recebe
    Usuario "0..1" --> "0..*" Estabelecimento : cadastra
```

### 4. Diagrama de sequencia do fluxo de avaliacao

Este diagrama detalha a operacao central do sistema: publicar uma avaliacao de um bar.

```mermaid
sequenceDiagram
    actor U as Usuario autenticado
    participant B as Browser
    participant F as Flask app
    participant S as Sessao Flask
    participant DB as Banco de dados

    U->>B: Preenche formulario na tela do bar
    B->>F: POST /bar/{id}/avaliar
    F->>S: Verifica usuario_id na sessao

    alt usuario nao autenticado
        F-->>B: redireciona para /acesso
    else usuario autenticado
        F->>DB: busca estabelecimento por id
        F->>F: le notas de bebida, comida, ambiente e servico

        alt alguma nota ausente
            F-->>B: redireciona para /bar/{id}
        else dados validos
            F->>F: calcula nota final = media das 4 categorias
            F->>DB: insere nova avaliacao
            DB-->>F: commit confirmado
            F-->>B: redireciona para /bar/{id}
            B-->>U: exibe review publicada
        end
    end
```

## Regras de negocio observadas no codigo

- o cadastro exige idade minima de 18 anos
- o sistema tambem rejeita idades maiores ou iguais a 125 anos
- o email do usuario deve ser unico
- uma avaliacao so e aceita quando as quatro categorias sao informadas
- a `nota` final da avaliacao e a media aritmetica de bebida, comida, ambiente e servico
- apenas administradores podem cadastrar bares
- apenas administradores podem acessar o painel de usuarios
- administradores nao podem ser removidos pelo fluxo de exclusao
- ao deletar um usuario comum, os estabelecimentos cadastrados por ele nao sao apagados; o campo `adicionado_por` passa para `NULL`
- a sessao Flask armazena `usuario_id` e `usuario_nome` para controle de autenticacao

## Estrutura resumida do repositorio

```text
.
|-- README.md
|-- requirements.txt
|-- seed_avaliacoes.py
|-- scraper/
|   |-- scraper_bares.py
|   `-- bares.json
`-- src/
    |-- app.py
    |-- models.py
    |-- static/
    `-- templates/
```

## Historias de usuario atendidas

- como visitante, quero buscar bares disponiveis para conhecer a plataforma
- como usuario, quero criar conta usando email e senha
- como usuario registrado, quero fazer login com email e senha
- como usuario autenticado, quero editar meus dados pessoais
- como usuario autenticado, quero avaliar bares em categorias separadas
- como usuario, quero visualizar avaliacoes publicadas sobre um estabelecimento
- como administrador, quero adicionar novos bares
- como administrador, quero consultar e remover usuarios comuns

## Ferramentas de apoio utilizadas no desenvolvimento

- GPT
- Gemini
- Claude
- Copilot
