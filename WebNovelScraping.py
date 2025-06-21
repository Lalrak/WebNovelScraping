import time
import random
import logging
from pathlib import Path

import requests
from lxml import html
from ebooklib import epub


logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


class SupremeMagusScraper:
    def __init__(self, base_url="https://centralnovel.com"):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (SupremeMagusScraper/1.0)"
        })
        self.base_url = base_url.rstrip("/")

        self.xpath_numero = "/html/body/div[1]/div[2]/div/div[2]/article/div[3]/div/div[1]/h1"
        self.xpath_titulo = "/html/body/div[1]/div[2]/div/div[2]/article/div[3]/div/div[1]/div[1]"
        self.xpath_conteudo = "/html/body/div[1]/div[2]/div/div[2]/article/div[3]/div/div[4]"

    def fetch_chapter_html(self, chapter_number):
        url = f"{self.base_url}/supreme-magus-capitulo-{chapter_number}/"
        resp = self.session.get(url, timeout=10)
        resp.raise_for_status()
        return resp.content

    def parse_chapter(self, html_content):
        tree = html.fromstring(html_content)

        numero_elem = tree.xpath(self.xpath_numero)
        titulo_elem = tree.xpath(self.xpath_titulo)
        conteudo_elem = tree.xpath(self.xpath_conteudo)

        if not numero_elem or not titulo_elem or not conteudo_elem:
            raise ValueError("Layout inesperado: não encontrou número, título ou conteúdo.")

        numero = numero_elem[0].text_content().strip()
        titulo = titulo_elem[0].text_content().strip()

        paragrafos = conteudo_elem[0].xpath(".//p")
        if not paragrafos:
            raise ValueError("Layout inesperado: não encontrou nenhum parágrafo dentro do conteúdo.")

        conteudo_lista = [p.text_content().strip() for p in paragrafos if p.text_content().strip()]

        return {
            "numero": numero,
            "titulo": titulo,
            "conteudo": conteudo_lista
        }

    def fetch_and_parse(self, chapter_number):
        html_bytes = self.fetch_chapter_html(chapter_number)
        data = self.parse_chapter(html_bytes)
        return data


def salvar_txt(chapters, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for chap in chapters:
            f.write(f"{chap['numero']}\n")
            f.write(f"{chap['titulo']}\n\n")
            for p in chap["conteudo"]:
                f.write(p + "\n\n")
            f.write("=" * 80 + "\n\n")


def criar_epub(chapters, output_path, book_title="Supreme Magus"):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    book = epub.EpubBook()
    book.set_identifier("supreme-magus")
    book.set_title(book_title)
    book.set_language("pt-br")
    book.add_author("Central Novel")

    spine: list = ["nav"]
    toc: list = []

    book.add_metadata("DC", "description", "Webnovel Supreme Magus – coletado automaticamente.")

    for idx, chap in enumerate(chapters, start=1):
        c = epub.EpubHtml(
            title=chap["titulo"],
            file_name=f"capitulo_{idx}.xhtml",
            lang="pt-br"
        )

        html_body = f"<h1>{chap['numero']}</h1>\n<h2>{chap['titulo']}</h2>\n"
        for p in chap["conteudo"]:
            html_body += f"<p>{p}</p>\n"
        c.content = html_body

        book.add_item(c)
        toc.append(c)
        spine.append(c)

    book.toc = toc
    book.spine = spine

    css = """
    @namespace epub "http://www.idpf.org/2007/ops";
    body { font-family: Cambria, Liberation Serif, serif; margin: 1em; }
    h1 { text-align: center; margin-top: 2em; }
    h2 { text-align: center; margin-bottom: 1em; }
    p { text-indent: 1.2em; margin-bottom: 0.8em; line-height: 1.4; }
    """
    nav_css = epub.EpubItem(
        uid="style_nav",
        file_name="styles/nav.css",
        media_type="text/css",
        content=css.encode("utf-8")
    )
    book.add_item(nav_css)

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub.write_epub(str(output_path), book, {})


def main(start_chapter, end_chapter, output_txt, output_epub, delay_range=(1, 2)):
    scraper = SupremeMagusScraper()
    chapters = []

    for num in range(start_chapter, end_chapter + 1):
        try:
            logging.info(f"Buscando capítulo {num}...")
            chap_data = scraper.fetch_and_parse(num)
            chapters.append(chap_data)

            time.sleep(random.uniform(*delay_range))

        except requests.exceptions.RequestException as e:
            logging.warning(f"Falha de rede no capítulo {num}: {e}")
        except ValueError as ve:
            logging.warning(f"Capítulo {num} ignorado: {ve}")
        except Exception as ex:
            logging.error(f"Erro inesperado no capítulo {num}: {ex}")

    if not chapters:
        logging.error("Nenhum capítulo foi recuperado com sucesso.")
        return

    logging.info(f"Salvando {len(chapters)} capítulos em TXT: {output_txt}")
    salvar_txt(chapters, output_txt)

    logging.info(f"Criando EPUB: {output_epub}")
    criar_epub(chapters, output_epub)
    logging.info("Processo concluído.")


if __name__ == "__main__":
    # Ajuste o intervalo de capítulos aqui
    START_CHAPTER = 487
    END_CHAPTER = 1262

    #vol 6 a 10 - 1 486
    #vol 6 a 10 - 487 1262
    #vol 11 a 14 - 1263 1712

    OUTPUT_TXT = "supreme_magus_Vol_6_a_10.txt"
    OUTPUT_EPUB = "supreme_magus_Vol_6_a_10.epub"

    main(START_CHAPTER, END_CHAPTER, OUTPUT_TXT, OUTPUT_EPUB)
