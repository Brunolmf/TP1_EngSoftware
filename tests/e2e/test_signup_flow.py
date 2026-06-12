import pytest

pytest.importorskip('playwright.sync_api')

from playwright.sync_api import Error, expect, sync_playwright


@pytest.mark.e2e
def test_visitante_cria_conta_e_e_redirecionado_para_home(live_server):
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except Error as exc:
            pytest.skip(f'Chromium do Playwright não está instalado: {exc}')

        try:
            page = browser.new_page()
            page.goto(f'{live_server}/cadastro')

            page.get_by_label('Nome').fill('Marina Teste')
            page.get_by_label('Email').fill('marina@teste.com')
            page.get_by_label('Idade').fill('23')
            page.get_by_label('Senha').fill('Senha@123')
            page.get_by_role('button', name='Criar conta').click()

            expect(page).to_have_url(f'{live_server}/')
            expect(page.get_by_role('link', name='Marina Teste')).to_be_visible()
            expect(page.locator('header').get_by_role('link', name='Sair')).to_be_visible()
        finally:
            browser.close()
