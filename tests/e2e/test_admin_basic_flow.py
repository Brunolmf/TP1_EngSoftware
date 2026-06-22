import os

import pytest

pytest.importorskip('playwright.sync_api')

from playwright.sync_api import Error, expect, sync_playwright


@pytest.mark.e2e
def test_admin_loga_adiciona_bar_e_ve_na_home(live_server, criar_usuario):
    criar_usuario(
        nome='Admin Saideira',
        email='admin@teste.com',
        senha='Senha@123',
        is_admin=True,
    )

    with sync_playwright() as playwright:
        headless = os.getenv('E2E_HEADLESS', '1') != '0'
        slow_mo = int(os.getenv('E2E_SLOWMO', '0'))
        try:
            browser = playwright.chromium.launch(headless=headless, slow_mo=slow_mo)
        except Error as exc:
            pytest.skip(f'Chromium do Playwright não está instalado: {exc}')

        try:
            page = browser.new_page()

            # 1. Admin faz login
            page.goto(f'{live_server}/acesso')
            page.get_by_label('Email').fill('admin@teste.com')
            page.get_by_label('Senha').fill('Senha@123')
            page.get_by_role('button', name='Entrar').click()
            expect(page).to_have_url(f'{live_server}/')

            # 2. Admin cadastra um novo bar
            page.goto(f'{live_server}/bar/adicionar')
            page.get_by_label('Nome do Boteco').fill('Bar do Playwright')
            page.get_by_label('Endereço Completo').fill('Av. dos Testes, 42')
            page.get_by_role('button', name='Cadastrar Bar').click()

            # 3. É redirecionado para a home e vê o bar recém-criado
            expect(page).to_have_url(f'{live_server}/')
            expect(page.get_by_role('heading', name='Bar do Playwright')).to_be_visible()
        finally:
            browser.close()
