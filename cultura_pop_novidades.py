import os
import urllib.parse
import re
import time
import base64
import random
import feedparser
import requests
from groq import Groq
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# --- CONFIGURAÇÕES ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
BLOGGER_ID = os.environ.get("BLOGGER_ID_POP")
CLIENT_ID = os.environ.get("BLOGGER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("BLOGGER_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("BLOGGER_REFRESH_TOKEN")

for nome, valor in [
    ("GROQ_API_KEY", GROQ_API_KEY),
    ("BLOGGER_ID_POP", BLOGGER_ID),
    ("BLOGGER_CLIENT_ID", CLIENT_ID),
    ("BLOGGER_CLIENT_SECRET", CLIENT_SECRET),
    ("BLOGGER_REFRESH_TOKEN", REFRESH_TOKEN),
]:
    if not valor:
        raise ValueError(f"Faltou configurar a variavel/segredo: {nome}")

groq_client = Groq(api_key=GROQ_API_KEY)
MODELO_IA = "llama-3.3-70b-versatile"

# --- GERACAO DE IMAGENS COM IA (Pollinations.ai) ---
# Opcional: se nao configurado, ou se qualquer etapa falhar, o script cai
# automaticamente no metodo antigo (busca de imagem no Openverse).
POLLINATIONS_TOKEN = os.environ.get("POLLINATIONS_TOKEN")  # opcional: remove marca dagua e aumenta limite
# Sem token: 1 requisicao a cada 15s. Com token gratuito (auth.pollinations.ai): a cada 5s.
INTERVALO_POLLINATIONS = 6 if POLLINATIONS_TOKEN else 16
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")
QTD_MIN_IMAGENS = 3
QTD_MAX_IMAGENS = 5

# --- FONTES: nacionais e internacionais de cultura pop (incluindo games) ---
FONTES = {
    # Nacionais
    "Jbox": "https://jbox.com.br/feed/",
    "Omelete": "https://www.omelete.com.br/sitemap-news.xml",
    "Jovem Nerd": "https://jovemnerd.com.br/feed-completo",
    "Critical Hits": "https://criticalhits.com.br/feed/",
    "IGN Brasil": "https://br.ign.com/feed/",
    "Legiao dos Herois": "https://legiaodosherois.com.br/feed/",
    "AnimeNew": "https://www.animenew.com.br/feed/",
    "Adrenaline (Games)": "https://www.adrenaline.com.br/feed/",
    "TecMundo Games": "https://www.tecmundo.com.br/feed/games",

    # Internacionais - anime/manga/geek
    "Anime News Network": "https://www.animenewsnetwork.com/all/rss.xml",
    "Otaku USA": "https://otakuusamagazine.com/feed/",
    "CBR": "https://www.cbr.com/feed/",
    "Screen Rant": "https://screenrant.com/feed/",
    "Crunchyroll News": "https://www.crunchyroll.com/newsrss",

    # Internacionais - filmes/series
    "Variety": "https://variety.com/feed/",
    "Deadline": "https://deadline.com/feed/",

    # Internacionais - games
    "IGN Global": "https://www.ign.com/feed",
    "Kotaku": "https://kotaku.com/rss",
    "GameSpot": "https://www.gamespot.com/feeds/mashup/",

    # Musica (rock, pop, k-pop, j-pop)
    "NME": "https://www.nme.com/feed",
    "Soompi (K-pop)": "https://www.soompi.com/feed",
    "Rolling Stone": "https://www.rollingstone.com/feed/",
    "Pitchfork": "https://pitchfork.com/rss/news/",
}

# --- Blogger tags/labels per category (the AI picks the right category) ---
CATEGORIAS_TAGS = {
    "anime": ["anime", "pop culture", "japan"],
    "manga": ["manga", "pop culture", "japan"],
    "cartoon": ["cartoon", "animation", "pop culture"],
    "quadrinho": ["comics", "graphic novels", "pop culture"],
    "filme": ["movies", "cinema", "pop culture"],
    "serie": ["tv series", "streaming", "pop culture"],
    "game": ["games", "video games", "pop culture"],
    "musica": ["music", "k-pop", "j-pop", "rock", "pop culture"],
    "retro": ["throwback", "retro", "pop culture", "nostalgia"],
}

ARQUIVO_HISTORICO = "historico_pop_novidades.txt"


def ja_foi_postada(link):
    if not os.path.exists(ARQUIVO_HISTORICO):
        return False
    with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
        return link in f.read()


def marcar_como_postada(link):
    with open(ARQUIVO_HISTORICO, "a", encoding="utf-8") as f:
        f.write(link + "\n")


def pegar_novidade():
    fontes_lista = list(FONTES.items())
    random.shuffle(fontes_lista)

    for nome_fonte, url_rss in fontes_lista:
        try:
            feed = feedparser.parse(url_rss, agent="Mozilla/5.0")
            if feed.bozo and not feed.entries:
                print(f"Fonte com problema: {nome_fonte} -> {url_rss}")
                continue
        except Exception as e:
            print(f"Fonte falhou: {nome_fonte} -> {url_rss} | Erro: {e}")
            continue

        for entrada in feed.entries[:5]:
            link = entrada.get("link")
            titulo = entrada.get("title")
            resumo = entrada.get("summary") or entrada.get("description") or ""

            if not link or not titulo:
                continue

            if not ja_foi_postada(link):
                print(f"Novidade encontrada em {nome_fonte}: {titulo[:60]}...")
                return titulo, resumo, link, nome_fonte

    return None, None, None, None


# --- RETRO/THROWBACK FALLBACK ---
# When no fresh news is found in any feed, instead of doing nothing we publish a
# nostalgic "on this day in pop culture" post. The year is randomized and the
# specific fact is picked by the AI, so the pool of possible posts is effectively
# infinite and never needs to repeat.
import datetime

GANCHOS_RETRO = [
    "Were you even alive in {ano}? Because that's the year {evento} happened.",
    "It's been {anos} years since {evento} - yes, really, do the math.",
    "Rewind to {ano}: while a lot of us were still in school (or not born yet), {evento}.",
    "Quick pop quiz: what came out in {ano}? Here's a hint - {evento}.",
    "If {ano} means anything to you, you'll remember this: {evento}.",
    "{anos} years ago today (give or take), {evento}. Time flies, huh?",
    "Some of you reading this weren't even a thought in {ano}, the year {evento}.",
    "Throwback to {ano}, a year that gave us {evento}.",
    "Let's talk about {ano} for a second, the year {evento} changed pop culture forever.",
    "Ever wonder what pop culture looked like in {ano}? Well, {evento}.",
]


def escolher_ano_retro(inicio=1970, margem_anos=3):
    ano_atual = datetime.datetime.utcnow().year
    fim = ano_atual - margem_anos
    return random.randint(inicio, fim)


def buscar_fato_retro(ano):
    """Pede a IA um acontecimento real e verificavel de cultura pop (games, animes,
    filmes, series, musica, quadrinhos) daquele ano, de qualquer parte do mundo."""
    prompt = f"""
Give me ONE real, well-known and verifiable pop culture release or event from the year {ano}
(worldwide - it can be from Japan, the US, Europe, or anywhere else): a movie, video game, anime,
manga, TV series, comic book, or music album/concert. Pick something genuinely iconic or
memorable, not obscure or uncertain.

Reply in EXACTLY this format, nothing else:
NAME: <name of the movie/game/anime/album/etc>
FACT: <one sentence, in English, stating what happened and why it mattered, no invented specific numbers or quotes>
"""
    resposta = pedir_ia_groq(prompt, temperatura=0.9)
    nome, fato = None, None
    for linha in resposta.splitlines():
        if linha.strip().upper().startswith("NAME:"):
            nome = linha.split(":", 1)[1].strip()
        elif linha.strip().upper().startswith("FACT:"):
            fato = linha.split(":", 1)[1].strip()
    if not nome or not fato:
        # fallback simples caso a IA fuja do formato
        nome = resposta.strip().splitlines()[0][:80]
        fato = resposta.strip()
    return nome, fato


def gerar_titulo_retro(ano, nome_evento):
    prompt = (
        f"Create a catchy, nostalgic, SEO-friendly blog title in English, no quotation marks, "
        f"about {nome_evento}, which is connected to the year {ano}. "
        f"Reply with only the title, plain text."
    )
    return pedir_ia_groq(prompt, temperatura=0.7).replace('"', '').strip()


def gerar_artigo_retro(ano, nome_evento, fato):
    anos_passados = datetime.datetime.utcnow().year - ano
    gancho = random.choice(GANCHOS_RETRO).format(ano=ano, anos=anos_passados, evento=fato.rstrip('.'))
    prompt = f"""
You are a writer for a highly engaged pop culture fan blog (anime, manga, comics, cartoons, movies,
TV series, video games and music). You write in a warm, conversational, nostalgic, slightly funny
tone that builds community - like chatting with a friend who really knows their pop culture history.

Today there's no fresh breaking news, so you're writing a "throwback" / "on this day in pop culture
history" post about: {nome_evento} ({ano}).
Known fact to build from: {fato}

Use this exact line as inspiration for your opening hook (rephrase it naturally into the opening
paragraph, don't just paste it): "{gancho}"

IMPORTANT RULES:
- Base everything on real, general knowledge about {nome_evento} and the year {ano}. Do NOT invent
  specific dates, numbers, or quotes you're not sure about - lean on real, well-known context:
  history, legacy, reception at the time, how it compares to today, why it still matters.
- Make it feel nostalgic AND relevant to today's fans - connect the past to the present when it
  makes sense (legacy, remakes, influence on newer works, anniversaries).
- NEVER be repetitive: every paragraph must add something new.
- Write entirely in English, for a worldwide audience.
- Length: between 600 and 1100 words.

FORMAT RULES (pure HTML, no Markdown):
1. An engaging, conversational opening paragraph using the hook above.
2. AT LEAST 3 <h2> subheadings (e.g. the context back then, why it mattered, its legacy today).
3. Insert 3 light, funny author's notes inside <blockquote> tags, written like a fan chatting
   with the reader (never mean-spirited or offensive), spread throughout the post.
4. Close with a short paragraph inviting readers to share their own memories in the comments.
"""
    return pedir_ia_groq(prompt, temperatura=0.8)


IMAGEM_PADRAO = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/News_icon.svg/640px-News_icon.svg.png"


def buscar_imagem_openverse(palavra_chave):
    try:
        resposta = requests.get(
            "https://api.openverse.org/v1/images/",
            params={
                "q": palavra_chave,
                "license_type": "commercial",
                "page_size": 3,
                "mature": "false",
            },
            headers={"User-Agent": "RoboCulturaPop/1.0"},
            timeout=10,
        )
        resultados = resposta.json().get("results", [])
        return resultados[0]["url"] if resultados else IMAGEM_PADRAO
    except Exception as e:
        print(f"Erro ao buscar imagem: {e}")
        return IMAGEM_PADRAO


DIMENSOES_RATIO = {
    "16:9": (1280, 720),
    "1:1": (1024, 1024),
    "9:16": (720, 1280),
}


def gerar_imagem_pollinations(prompt, ratio="16:9"):
    """Gera uma imagem via Pollinations.ai (gratuito, sem chave, sem cota diaria).
    Retorna bytes da imagem ou None se falhar."""
    largura, altura = DIMENSOES_RATIO.get(ratio, (1280, 720))
    try:
        prompt_codificado = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{prompt_codificado}"
        params = {
            "width": largura,
            "height": altura,
            "model": "flux",
            "seed": random.randint(1, 999999),
            "nologo": "true",
        }
        headers = {}
        if POLLINATIONS_TOKEN:
            headers["Authorization"] = f"Bearer {POLLINATIONS_TOKEN}"
        resposta = requests.get(url, params=params, headers=headers, timeout=120)
        resposta.raise_for_status()
        content_type = resposta.headers.get("Content-Type", "")
        if "image" not in content_type:
            raise ValueError(f"Resposta nao parece ser uma imagem (Content-Type: {content_type})")
        return resposta.content
    except Exception as e:
        print(f"⚠️ Pollinations.ai falhou para o prompt '{prompt[:40]}...': {e}")
        return None


def hospedar_imagem(imagem_bytes, nome_arquivo="imagem.png"):
    """Sobe a imagem gerada para o imgbb.com (host gratuito via API) e retorna a URL publica.
    Catbox.moe bloqueia uploads vindos de IPs de datacenter (ex: GitHub Actions), por isso
    usamos o imgbb, que aceita chamadas de API normalmente."""
    if not IMGBB_API_KEY:
        print("Falha ao hospedar imagem: IMGBB_API_KEY nao configurada")
        return None
    try:
        b64 = base64.b64encode(imagem_bytes).decode("utf-8")
        resposta = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IMGBB_API_KEY, "image": b64, "name": nome_arquivo},
            timeout=30,
        )
        resposta.raise_for_status()
        dados = resposta.json()
        if dados.get("success"):
            return dados["data"]["url"]
        raise ValueError(f"Resposta inesperada do imgbb: {dados}")
    except Exception as e:
        print(f"Falha ao hospedar imagem gerada: {e}")
        return None


def gerar_imagem_ia(prompt, ratio="16:9"):
    """Pipeline completo: gera a imagem no Pollinations.ai e hospeda no imgbb. Retorna URL ou None."""
    imagem_bytes = gerar_imagem_pollinations(prompt, ratio)
    if not imagem_bytes:
        return None
    return hospedar_imagem(imagem_bytes)


def _limpar_tag(texto):
    return re.sub(r"<[^>]+>", "", texto).strip()


def extrair_titulos_h2(html):
    return re.findall(r"<h2[^>]*>(.*?)</h2>", html, flags=re.IGNORECASE | re.DOTALL)


def contar_palavras_html(html):
    texto = re.sub(r"<[^>]+>", " ", html)
    return len(texto.split())


def calcular_qtd_imagens(wc, minimo, maximo, base_palavras, palavras_por_imagem_extra):
    if wc <= base_palavras:
        return minimo
    extras = (wc - base_palavras) // palavras_por_imagem_extra
    return min(maximo, minimo + extras)


def gerar_prompts_imagens_ia(titulo_post, secoes, quantidade, contexto_extra=""):
    """Asks the AI for image prompts in English: the first one in a 'store/thumbnail cover'
    style to attract clicks, and the rest tied to each moment/section of the post."""
    qtd_secoes = max(0, quantidade - 1)
    secoes_usadas = secoes[:qtd_secoes]
    lista_secoes = "\n".join(f"- {s}" for s in secoes_usadas) or "- (no subheadings defined, use the post's general theme)"

    prompt = f"""
You are an art director creating prompts for an AI image generator (Stable Diffusion/Flux style).
Post title: "{titulo_post}"
{contexto_extra}

I need exactly {quantidade} image prompts in ENGLISH, each on its own separate line, NO numbering,
NO quotation marks, NO explanations - just the prompts, one per line, in this order:

1) The FIRST line is the COVER/THUMBNAIL image: it needs to look like a professional digital
   storefront thumbnail (eye-catching streaming or games/movies store cover style), extremely high
   visual impact, vibrant colors, centered composition, dramatic lighting, focused on the main
   element of the topic, no text written on the image, designed to maximize clicks.
2) The following lines are one image for EACH of these post moments/sections (in this order):
{lista_secoes}
   Each prompt should visually relate to the content of that specific section, keeping aesthetic
   consistency with the overall theme.

Each prompt: descriptive, rich in visual detail (setting, lighting, art style, composition),
WITHOUT naming specific characters, works, or trademarks - describe visually without citing
proper names of copyrighted works. Reply with ONLY the {quantidade} prompt lines.
"""
    resposta = pedir_ia_groq(prompt, temperatura=0.8)
    linhas = [l.strip(" -\"") for l in resposta.strip().splitlines() if l.strip()]
    if len(linhas) < quantidade:
        while len(linhas) < quantidade:
            linhas.append(linhas[-1] if linhas else titulo_post)
    return linhas[:quantidade]


def montar_galeria_ia(titulo_post, corpo_html, minimo, maximo, contexto_extra=""):
    """Gera a galeria completa de imagens via Pollinations.ai. Lanca excecao se qualquer
    etapa falhar, para o chamador cair no fallback do Openverse."""
    if not IMGBB_API_KEY:
        raise RuntimeError("IMGBB_API_KEY nao configurada")

    secoes_brutas = extrair_titulos_h2(corpo_html)
    secoes = [_limpar_tag(s) for s in secoes_brutas]

    wc = contar_palavras_html(corpo_html)
    qtd = calcular_qtd_imagens(wc, minimo, maximo, base_palavras=500, palavras_por_imagem_extra=250)
    if secoes:
        qtd = min(qtd, len(secoes) + 1)
    qtd = max(1, qtd)

    prompts = gerar_prompts_imagens_ia(titulo_post, secoes, qtd, contexto_extra)

    galeria = []
    for i, prompt in enumerate(prompts):
        url = gerar_imagem_ia(prompt, ratio="16:9")
        if not url:
            raise RuntimeError(f"Falha ao gerar/hospedar imagem {i + 1}/{qtd} da galeria")
        alt = titulo_post if i == 0 else (secoes[i - 1] if i - 1 < len(secoes) else titulo_post)
        galeria.append((url, alt))
        if i < len(prompts) - 1:
            time.sleep(INTERVALO_POLLINATIONS)  # respeita o rate limit do Pollinations.ai

    return galeria, secoes_brutas


def inserir_imagens_no_corpo(corpo_html, secoes_brutas, galeria):
    """Insere as imagens de secao (a partir do indice 1 da galeria) logo apos os respectivos <h2>."""
    novo_html = corpo_html
    imagens_secao = galeria[1:]
    for i, (url, alt) in enumerate(imagens_secao):
        if i >= len(secoes_brutas):
            break
        h2_bruto = secoes_brutas[i]
        padrao = re.compile(r"(<h2[^>]*>" + re.escape(h2_bruto) + r"</h2>)", re.IGNORECASE)
        img_html = gerar_tabela_imagem_blogger(url, alt)
        novo_html, _ = padrao.subn(lambda m: m.group(1) + img_html, novo_html, count=1)
    return novo_html


def gerar_tabela_imagem_blogger(url_img, alt_title):
    return (
        '<table align="center" cellpadding="0" cellspacing="0" '
        'class="tr-caption-container" style="margin-left: auto; margin-right: auto;">'
        '<tbody><tr><td style="text-align: center;">'
        f'<img alt="{alt_title}" border="0" height="360" src="{url_img}" '
        f'title="{alt_title}" width="640" /></td></tr></tbody></table><br />'
    )


def pedir_ia_groq(prompt, temperatura=0.7):
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=MODELO_IA,
        temperature=temperatura,
    )
    return response.choices[0].message.content.strip()


def extrair_palavra_chave(titulo):
    prompt = (
        f"Based on this title: '{titulo}', give just ONE keyword in English that "
        f"visually describes the topic (e.g. 'anime', 'kpop concert', 'superhero movie', "
        f"'video game', 'rock band'). Reply with only the word."
    )
    return pedir_ia_groq(prompt, temperatura=0.3).strip().lower().split()[0]


def identificar_categoria(titulo):
    categorias_validas = [c for c in CATEGORIAS_TAGS.keys() if c != "retro"]
    prompt = (
        f"Based on this news headline: '{titulo}', choose the most fitting category "
        f"among: {', '.join(categorias_validas)}. Reply with ONLY the category word."
    )
    resposta = pedir_ia_groq(prompt, temperatura=0.2).strip().lower()
    for cat in categorias_validas:
        if cat in resposta:
            return cat
    return "anime"


def gerar_titulo(titulo_original):
    prompt = (
        f"Create a brand-new, catchy, SEO-optimized title in English, "
        f"with no quotation marks, based on this pop culture news item: '{titulo_original}'. "
        f"Reply with only the title, plain text."
    )
    return pedir_ia_groq(prompt, temperatura=0.7).replace('"', '').strip()


def gerar_artigo(titulo_original, resumo, nome_fonte):
    prompt = f"""
You are a writer (who researches multiple sources) specialized in pop culture (anime, manga, comics, cartoons,
movies, TV series, video games and music - rock, pop, k-pop, j-pop, metal) for a highly engaged fan blog.
You know all the latest happenings, you can connect the dots from memory, and you write in a pleasant, funny,
behind-the-scenes-digging way. You know a bit of gossip here and there, and you know how to build community.
Write with high quality, take your time - really put care into it.

Rewrite this news item completely in your own words (never copy sentences verbatim), in English, for a
worldwide audience (source: {nome_fonte}):
Original title: {titulo_original}
Original summary: {resumo}

IMPORTANT RULES:
- If the original information is short, EXPAND it with real, relevant context: the franchise's/artist's/studio's
  history, widely known behind-the-scenes trivia, fan/audience reception, comparisons with previous works.
  DO NOT invent specific facts (dates, numbers, quotes) you are not sure of - add real general context,
  never specific fabrications.
- NEVER be repetitive: every paragraph must bring new information, without restating what was already
  said in different words.
- Length: between 600 and 1200 words (it's fine to go over 1200 if the topic calls for it).

FORMAT RULES (pure HTML, no Markdown):
1. An engaging opening paragraph.
2. AT LEAST 3 <h2> subheadings (e.g. context, details, fan reaction/expectations).
3. Insert 3 light, funny author's notes inside <blockquote> tags, commenting with fan-like humor
   (never mean-spirited or offensive), spread throughout the post.
4. Always mention sources to build credibility.
"""
    return pedir_ia_groq(prompt, temperatura=0.75)


def gerar_cta():
    return """
<div style="background-color: #f4f6f8; border-radius: 12px; margin: 30px 0; padding: 25px; text-align: center; font-family: sans-serif;">
    <p style="font-size: 17px; font-weight: bold; color: #333; margin: 0 0 10px 0;">Liked this news?</p>
    <p style="font-size: 14px; color: #555; margin: 0 0 15px 0;">Drop a comment, like it, and share it with your friends who follow this too!</p>
    <div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;">
        <a href="#" onclick="window.open('https://api.whatsapp.com/send?text=' + encodeURIComponent(document.title + ' - ' + window.location.href), '_blank'); return false;" style="background-color: #25d366; color: white; padding: 10px 16px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: bold;">WhatsApp</a>
        <a href="#" onclick="window.open('https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(window.location.href), '_blank'); return false;" style="background-color: #1877f2; color: white; padding: 10px 16px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: bold;">Facebook</a>
        <a href="#" onclick="window.open('https://twitter.com/intent/tweet?url=' + encodeURIComponent(window.location.href), '_blank'); return false;" style="background-color: #000; color: white; padding: 10px 16px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: bold;">X</a>
    </div>
</div>
"""


def obter_credenciais():
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(Request())
    return creds


def publicar_no_blogger(titulo, conteudo, tags):
    creds = obter_credenciais()
    blogger = build('blogger', 'v3', credentials=creds)
    corpo_postagem = {
        'kind': 'blogger#post',
        'title': titulo,
        'content': conteudo,
        'labels': tags,
    }
    resultado = blogger.posts().insert(blogId=BLOGGER_ID, body=corpo_postagem).execute()
    print(f"Postado: '{titulo}' -> {resultado.get('url')}")


def rodar_fluxo_novidade(titulo_original, resumo, link, fonte):
    categoria = identificar_categoria(titulo_original)
    tags = CATEGORIAS_TAGS.get(categoria, ["pop culture"])

    novo_titulo = gerar_titulo(titulo_original)
    corpo = gerar_artigo(titulo_original, resumo, fonte)

    try:
        galeria, secoes_brutas = montar_galeria_ia(
            novo_titulo,
            corpo,
            minimo=QTD_MIN_IMAGENS,
            maximo=QTD_MAX_IMAGENS,
            contexto_extra=f"News summary (source: {fonte}): {resumo}",
        )
        img_html = gerar_tabela_imagem_blogger(galeria[0][0], novo_titulo)
        corpo = inserir_imagens_no_corpo(corpo, secoes_brutas, galeria)
        print(f"Gallery with {len(galeria)} image(s) generated via Pollinations.ai.")
    except Exception as e:
        print(f"AI image generation failed, using fallback method (Openverse): {e}")
        palavra_chave = extrair_palavra_chave(titulo_original)
        img_url = buscar_imagem_openverse(palavra_chave)
        img_html = gerar_tabela_imagem_blogger(img_url, novo_titulo)

    cta = gerar_cta()

    rodape = (
        '<hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;" />'
        '<p style="color: #555555; font-size: 13px; font-style: italic; margin-top: 15px;">'
        f'Original news source: <a href="{link}" rel="noopener noreferrer" target="_blank">{fonte}</a>'
        '</p>'
    )

    html_final = f"{img_html}{corpo}{cta}{rodape}"
    publicar_no_blogger(novo_titulo, html_final, tags)
    marcar_como_postada(link)


def rodar_fluxo_retro():
    ano = escolher_ano_retro()
    nome_evento, fato = buscar_fato_retro(ano)
    link_sintetico = f"retro::{ano}::{nome_evento}"

    tentativas = 0
    while ja_foi_postada(link_sintetico) and tentativas < 5:
        ano = escolher_ano_retro()
        nome_evento, fato = buscar_fato_retro(ano)
        link_sintetico = f"retro::{ano}::{nome_evento}"
        tentativas += 1

    print(f"Throwback topic picked: {nome_evento} ({ano})")

    titulo = gerar_titulo_retro(ano, nome_evento)
    corpo = gerar_artigo_retro(ano, nome_evento, fato)
    tags = CATEGORIAS_TAGS.get("retro", ["throwback", "retro", "pop culture"])

    try:
        galeria, secoes_brutas = montar_galeria_ia(
            titulo,
            corpo,
            minimo=QTD_MIN_IMAGENS,
            maximo=QTD_MAX_IMAGENS,
            contexto_extra=f"Throwback topic: {nome_evento} ({ano}) - {fato}",
        )
        img_html = gerar_tabela_imagem_blogger(galeria[0][0], titulo)
        corpo = inserir_imagens_no_corpo(corpo, secoes_brutas, galeria)
        print(f"Gallery with {len(galeria)} image(s) generated via Pollinations.ai.")
    except Exception as e:
        print(f"AI image generation failed, using fallback method (Openverse): {e}")
        palavra_chave = extrair_palavra_chave(nome_evento)
        img_url = buscar_imagem_openverse(palavra_chave)
        img_html = gerar_tabela_imagem_blogger(img_url, titulo)

    cta = gerar_cta()

    rodape = (
        '<hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;" />'
        '<p style="color: #888888; font-size: 12px; font-style: italic; margin-top: 15px;">'
        'Throwback post: a nostalgic look back at pop culture history, for entertainment purposes.'
        '</p>'
    )

    html_final = f"{img_html}{corpo}{cta}{rodape}"
    publicar_no_blogger(titulo, html_final, tags)
    marcar_como_postada(link_sintetico)


if __name__ == "__main__":
    print("Looking for pop culture news...")
    titulo_original, resumo, link, fonte = pegar_novidade()

    if titulo_original:
        print(f"Found on [{fonte}]: {titulo_original[:100]}...")
        try:
            rodar_fluxo_novidade(titulo_original, resumo, link, fonte)
            print("Done!")
        except Exception as e:
            print(f"Error during generation/publishing: {e}")
    else:
        print("No fresh news found in any source. Falling back to a throwback post...")
        try:
            rodar_fluxo_retro()
            print("Done!")
        except Exception as e:
            print(f"Error during throwback generation/publishing: {e}")
