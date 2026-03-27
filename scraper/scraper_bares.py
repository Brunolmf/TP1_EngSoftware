from playwright.sync_api import sync_playwright
import json
import time

def buscar_bares():
    bares = []
    base_url = "https://comidadibuteco.com.br/butecos/belo-horizonte/page/11/"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Deixe headless=False para ver o navegador em ação
        page = browser.new_page()
        
        print(f"Acessando a página inicial: {base_url}...")
        page.goto(base_url)
        
        print("Aguardando o carregamento... Resolva a verificação na tela se aparecer!")
        # Aguarda até 60 segundos na primeira página para você ter tempo de fazer o puzzle/captcha
        try:
            page.wait_for_selector('div.item', timeout=60000)
        except Exception:
            print("Tempo limite de espera! (Nenhum item apareceu).")
            return bares
        
        page_num = 1
        
        while True:
            # Busca todas as divs com a classe 'item'
            itens = page.query_selector_all('div.item')
            if not itens:
                print("Não há mais itens a raspar.")
                break
                
            print(f"Foram encontrados {len(itens)} bares na página {page_num}.")

            for item in itens:
                # Pega a foto
                img_tag = item.query_selector('img')
                foto_url = img_tag.get_attribute('src') if img_tag else None

                # Pega o nome e endereço da div caption
                caption = item.query_selector('div.caption')
                if caption:
                    nome_tag = caption.query_selector('h2')
                    nome = nome_tag.inner_text().strip() if nome_tag else None
                    
                    endereco_tag = caption.query_selector('p')
                    endereco = endereco_tag.inner_text().strip() if endereco_tag else None
                else:
                    nome = None
                    endereco = None

                bares.append({
                    "nome": nome,
                    "endereco": endereco,
                    "foto_url": foto_url
                })
                
            # Procura pelo botão "Próxima" e clica nele
            next_button = page.query_selector('a.next.page-link')
            
            if next_button:
                print(f"Avançando para a próxima página pelo botão...")
                next_button.click()
                page_num += 1
                
                # Aguarda a próxima página carregar de verdade antes de tentar extrair os itens
                # time.sleep ajuda a não dar falsos positivos por pegar os itens da página anterior antes da transição
                time.sleep(3)
                try:
                    print("Aguardando os itens da próxima página... Resolva a verificação se aparecer!")
                    page.wait_for_selector('div.item', timeout=60000)
                except Exception:
                    print("A próxima página não carregou os itens a tempo.")
                    break
            else:
                print("Botão 'Prox' não encontrado. Raspagem finalizada.")
                break
                
        browser.close()

    return bares

if __name__ == "__main__":
    dados_bares = buscar_bares()
    
    # Opcional: Salvar em um arquivo JSON para você carregar no Flask/Banco de dados
    if dados_bares:
        with open("bares_bh11.json", "w", encoding="utf-8") as f:
            json.dump(dados_bares, f, ensure_ascii=False, indent=4)
        print("Scraping finalizado! Dados salvos com sucesso no arquivo 'bares_bh.json'.")