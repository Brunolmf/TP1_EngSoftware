# TP1_EngSoftware

**Membros:** Bruno Lopes Melo Fonseca (Full stack), Gabriel Alkmim Barros (Full stack), Felipe Araujo Melo (Full stack)

## Sobre o projeto

O **Saideira** e uma aplicação web em Flask voltada para descoberta e avaliação de bares em Belo Horizonte. A proposta do sistema e funcionar como um diario social da vida noturna: usuários podem criar conta, explorar estabelecimentos, publicar reviews com notas por categoria e acompanhar a reputacao de cada lugar.

Pelo codigo atual, o sistema possui tres eixos principais:

- exploracao publica de bares e avaliacoes
- autenticacao e gerenciamento de perfil
- administracao de estabelecimentos e usuários

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
- editar perfil do usuário
- publicar avaliação com notas separadas para bebida, comida, ambiente e servico
- cadastrar novos estabelecimentos como administrador
- listar e remover usuários como administrador

## Documentacao UML preliminar


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

    subgraph UsuarioAutenticado["Usuário autenticado"]
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
    D -->|requer login| A
    P --> S
    P -->|se for admin| NB
    P -->|se for admin| AU
    AU --> DU
```

### 2. Visao de componentes e responsabilidades

Este diagrama mostra como a aplicação web se organiza entre interface, camada Flask, modelos, banco e scripts auxiliares.

```mermaid
flowchart TD
    Browser["Browser (cliente)<br/>HTML renderizado, formularios e requisicoes HTTP"]
    Flask["Flask - src/app.py<br/>rotas, sessao, validacoes e renderizacao"]
    Models["SQLAlchemy - src/models.py<br/>Usuario, Estabelecimento e avaliação"]
    DB[("Banco de dados relacional<br/>SQLite/PostgreSQL")]?
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

Este e o diagrama UML mais importante para entender o núcleo do sistema e a relação entre usuários, bares e reviews.

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

### 4. Diagrama de sequencia do fluxo de avaliação

Este diagrama detalha a operação central do sistema: publicar uma avaliação de um bar.

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
            F->>DB: insere nova avaliação
            DB-->>F: commit confirmado
            F-->>B: redireciona para /bar/{id}
            B-->>U: exibe review publicada
        end
    end
```

## Regras de negocio 

- o cadastro exige idade minima de 18 anos
- o sistema também rejeita idades maiores ou iguais a 125 anos
- o email do usuario deve ser único
- uma avaliação só é aceita quando as quatro categorias são informadas
- a `nota` final da avaliação é a media aritmetica de bebida, comida, ambiente e serviço
- apenas administradores podem cadastrar bares
- apenas administradores podem acessar o painel de usuarios
- administradores não podem ser removidos pelo fluxo de exclusão
- ao deletar um usuário comum, os estabelecimentos cadastrados por ele não são apagados; o campo `adicionado_por` passa para `NULL`
- a sessão Flask armazena `usuario_id` e `usuario_nome` para controle de autenticação

## Estrutura resumida do repositório

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

## Histórias de usuário atendidas

- como visitante, quero buscar bares disponíveis para conhecer a plataforma
- como usuário, quero criar conta usando email e senha
- como usuário registrado, quero fazer login com email e senha
- como usuário autenticado, quero editar meus dados pessoais
- como usuário autenticado, quero avaliar bares em categorias separadas
- como usuário, quero visualizar avaliações publicadas sobre um estabelecimento
- como administrador, quero adicionar novos bares
- como administrador, quero consultar e remover usuários comuns

## Ferramentas de apoio utilizadas no desenvolvimento

- GPT
- Gemini
- Claude
- Copilot
