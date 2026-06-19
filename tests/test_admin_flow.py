import pytest

pytest.importorskip('playwright.sync_api')

from playwright.sync_api import Error, expect, sync_playwright


def _fazer_login(page, live_server, email, senha):
    page.goto(f'{live_server}/acesso')
    page.get_by_label('Email').fill(email)
    page.get_by_label('Senha').fill(senha)
    page.get_by_role('button', name='Entrar').click()


@pytest.mark.e2e
def test_admin_adiciona_bar_e_visualiza_na_home(live_server, criar_usuario):
    admin = criar_usuario(
        nome='Admin E2E',
        email='admin-e2e@teste.com',
        senha='Senha@123',
        is_admin=True,
    )

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except Error as exc:
            pytest.skip(f'Chromium do Playwright não está instalado: {exc}')

        try:
            page = browser.new_page()
            _fazer_login(page, live_server, admin['email'], admin['senha'])

            expect(page.locator('header').get_by_role('link', name='Controle de usuários')).to_be_visible()
            page.get_by_role('link', name='Adicionar bar').click()

            expect(page).to_have_url(f'{live_server}/bar/adicionar')
            page.get_by_label('Nome do Boteco').fill('Bar E2E do Codex')
            page.get_by_label('Endereço Completo').fill('Rua dos Testes E2E, 123 - Belo Horizonte')
            page.get_by_label('URL da Foto').fill('https://example.com/e2e-bar.jpg')
            page.locator('label[for="p2"]').click()
            page.get_by_role('button', name='Cadastrar Bar').click()

            expect(page).to_have_url(f'{live_server}/')
            expect(page.get_by_text('Boteco "Bar E2E do Codex" cadastrado com sucesso!')).to_be_visible()
            expect(page.get_by_role('heading', name='Bar E2E do Codex')).to_be_visible()
        finally:
            browser.close()


@pytest.mark.e2e
def test_admin_remove_usuario_comum_no_painel(live_server, criar_usuario):
    admin = criar_usuario(
        nome='Admin E2E',
        email='admin-e2e@teste.com',
        senha='Senha@123',
        is_admin=True,
    )
    criar_usuario(
        nome='Cliente E2E',
        email='cliente-e2e@teste.com',
        senha='Senha@123',
    )

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except Error as exc:
            pytest.skip(f'Chromium do Playwright não está instalado: {exc}')

        try:
            page = browser.new_page()
            _fazer_login(page, live_server, admin['email'], admin['senha'])

            page.locator('header').get_by_role('link', name='Controle de usuários').click()
            expect(page).to_have_url(f'{live_server}/admin/usuarios')

            linha_usuario = page.locator('tbody tr', has_text='cliente-e2e@teste.com')
            expect(linha_usuario).to_have_count(1)

            page.once('dialog', lambda dialog: dialog.accept())
            linha_usuario.get_by_role('button', name='Excluir').click()

            expect(page.get_by_text('Usuário Cliente E2E removido com sucesso!')).to_be_visible()
            expect(page.locator('tbody tr', has_text='cliente-e2e@teste.com')).to_have_count(0)
        finally:
            browser.close()
