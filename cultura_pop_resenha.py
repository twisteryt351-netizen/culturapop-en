import os
import urllib.parse
import re
import time
import base64
import random
import requests
from groq import Groq
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# --- CONFIGURACOES ---
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
QTD_MIN_IMAGENS = 5
QTD_MAX_IMAGENS = 10

# --- LISTA BASE DE CULTURA POP (Triplicada: 300 Temas Diferentes) ---
TEMAS = [
    # --- ANIMES & MANGÁS (60 Temas) ---
    "o anime e mangá 'Akira' (1988)",
    "o anime 'Yu Yu Hakusho' e sua passagem pelo Brasil",
    "a saga de 'Dragon Ball Z' e o legado de Akira Toriyama",
    "o anime 'Neon Genesis Evangelion'",
    "o mangá e anime 'Berserk' de Kentaro Miura",
    "o anime clássico 'Speed Racer'",
    "o anime 'Cowboy Bebop'",
    "o mangá e anime 'Monster' de Naoki Urasawa",
    "a franquia 'Sailor Moon'",
    "o anime 'Death Note'",
    "o anime 'Os Cavaleiros do Zodíaco'",
    "o filme 'A Viagem de Chihiro' e o Studio Ghibli",
    "o anime e filme 'Ghost in the Shell' (1995)",
    "o anime 'Fullmetal Alchemist: Brotherhood'",
    "o mangá e anime 'One Piece'",
    "o anime 'Hunter x Hunter'",
    "o anime 'Serial Experiments Lain'",
    "o mangá 'Vagabond' de Takehiko Inoue",
    "o anime 'InuYasha'",
    "o mangá e anime de basquete 'Slam Dunk'",
    "o anime 'Naruto Classic' e a febre dos anos 2000",
    "o anime e mangá 'Bleach'",
    "o anime 'Rurouni Kenshin' (Samurai X)",
    "o anime 'Digimon Adventure' (1999)",
    "o anime 'Cardcaptor Sakura'",
    "o anime 'Shingeki no Kyojin' (Attack on Titan)",
    "o anime e mangá 'Demon Slayer' (Kimetsu no Yaiba)",
    "o anime 'Jujutsu Kaisen'",
    "o anime e mangá 'Chainsaw Man'",
    "o anime 'JoJo's Bizarre Adventure'",
    "o anime 'Steins;Gate'",
    "o anime 'Code Geass: Lelouch of the Rebellion'",
    "o anime 'Trigun' (1998)",
    "o anime 'Outlaw Star'",
    "o anime 'Hellsing' e 'Hellsing Ultimate'",
    "o anime 'FLCL' (Fooly Cooly)",
    "o anime 'Gundam' e o gênero Mecha",
    "o anime 'Haikyu!!'",
    "o anime 'My Hero Academia' (Boku no Hero)",
    "o anime 'One Punch Man'",
    "o anime 'Mob Psycho 100'",
    "o filme 'Your Name' (Kimi no Na wa) de Makoto Shinkai",
    "o filme 'Princesa Mononoke' do Studio Ghibli",
    "o filme 'O Túmulo dos Vagalumes'",
    "o anime 'Parasyte' (Kiseijuu)",
    "o anime 'Made in Abyss'",
    "o anime 'Vinland Saga'",
    "o anime 'Frieren: Beyond Journey's End'",
    "o anime 'Tokyo Ghoul'",
    "o anime 'Shaman King'",
    "o anime 'Ranma ½'",
    "o anime 'Captain Tsubasa' (Super Campeões)",
    "o anime 'Zatch Bell!'",
    "o anime 'Medabots'",
    "o anime 'BeyBlade' clássico",
    "o anime 'Yu-Gi-Oh! Duel Monsters'",
    "o anime 'Tenchi Muyo!'",
    "o anime 'Fly: O Pequeno Guerreiro' (Dragon Quest)",
    "o anime 'Hamtaro'",
    "o mangá '20th Century Boys' de Naoki Urasawa",

    # --- GAMES & CONSOLES (60 Temas) ---
    "o jogo RPG 'Chrono Trigger'",
    "o jogo 'Castlevania: Symphony of the Night'",
    "a guerra de consoles dos anos 90 (Super Nintendo vs Mega Drive)",
    "o jogo 'Resident Evil 1' (1996) e o Survival Horror",
    "o jogo 'Final Fantasy VII' (PS1)",
    "o jogo 'The Legend of Zelda: Ocarina of Time'",
    "o console 'PlayStation 1' e a revolução da Sony",
    "o jogo de terror 'Silent Hill 2'",
    "o jogo 'GTA San Andreas'",
    "a franquia 'Pokémon' na era do Game Boy (Red/Blue)",
    "o jogo indie 'Hollow Knight'",
    "a criação e o impacto do mascote 'Sonic the Hedgehog'",
    "o jogo 'Super Mario 64'",
    "o jogo de corrida 'Top Gear' (SNES)",
    "o fenômeno 'Minecraft'",
    "o jogo 'Shadow of the Colossus'",
    "a franquia de luta 'Street Fighter II'",
    "a franquia 'Metal Gear Solid' de Hideo Kojima",
    "o jogo 'Half-Life 2'",
    "o console 'Dreamcast' e o fim da era SEGA em hardware",
    "o jogo 'The Witcher 3: Wild Hunt'",
    "o jogo 'Red Dead Redemption 2'",
    "o jogo 'God of War' (2005 / PS2)",
    "o jogo 'God of War' (2018 / PS4)",
    "o jogo 'The Last of Us' (Part I)",
    "o jogo 'Dark Souls' e a criação do gênero Soulsborne",
    "o jogo 'Elden Ring'",
    "o jogo 'Bloodborne'",
    "o jogo 'Skyrim' (The Elder Scrolls V)",
    "o jogo 'Fallout: New Vegas'",
    "o jogo 'Mass Effect 2'",
    "o jogo 'BioShock' (2007)",
    "o jogo 'Portal 1 e 2'",
    "o jogo 'Halo: Combat Evolved' (Xbox)",
    "o jogo 'Doom' (1993) e o nascimento dos FPS",
    "o jogo 'Quake' e as LAN Houses no Brasil",
    "o jogo 'Counter-Strike 1.6'",
    "o jogo 'Diablo II'",
    "o jogo 'Warcraft III: Reign of Chaos'",
    "o MMORPG 'World of Warcraft'",
    "o MMORPG 'Ragnarök Online'",
    "o jogo 'Mortal Kombat 1, 2 e 3' nos arcades",
    "o jogo 'The King of Fighters '98'",
    "o jogo 'Tekken 3' (PS1)",
    "o jogo 'Donkey Kong Country' (SNES)",
    "o jogo 'Banjo-Kazooie' (N64)",
    "o jogo 'GoldenEye 007' (N64)",
    "o jogo 'Metroid Prime'",
    "o jogo 'Star Fox 64'",
    "o jogo 'Super Mario World' (SNES)",
    "o jogo 'Crash Bandicoot' (PS1)",
    "o jogo 'Spyro the Dragon' (PS1)",
    "o jogo 'Tony Hawk's Pro Skater 2'",
    "o jogo 'Need for Speed: Underground 2'",
    "o jogo 'Bully' (PS2)",
    "o jogo 'Guitar Hero II'",
    "o jogo indie 'Undertale'",
    "o jogo indie 'Stardew Valley'",
    "o jogo indie 'Celeste'",
    "o jogo 'Persona 5'",

    # --- CINEMA & SÉRIES (60 Temas) ---
    "o filme 'Jurassic Park' (1993)",
    "a trilogia de filmes 'O Senhor dos Anéis'",
    "o filme 'De Volta para o Futuro'",
    "o filme 'Blade Runner' (1982)",
    "o filme 'Pulp Fiction' de Quentin Tarantino",
    "o filme '2001: Uma Odisséia no Espaço'",
    "o filme de terror 'O Exorcista' (1973)",
    "a trilogia clássica de 'Star Wars' (Episódios IV, V e VI)",
    "o filme 'Matrix' (1999)",
    "a série de TV 'Breaking Bad'",
    "a sitcom 'Seinfeld'",
    "o programa e série 'Chaves'",
    "o filme 'O Iluminado' de Stanley Kubrick",
    "a série 'Twin Peaks' de David Lynch",
    "o filme 'Alien: O Oitavo Passageiro' (1979)",
    "a trilogia de filmes 'O Poderoso Chefão'",
    "a franquia de terror 'A Hora do Pesadelo' (Freddy Krueger)",
    "o filme 'Clube da Luta'",
    "a série 'The Sopranos'",
    "o filme brasileiro 'Cidade de Deus'",
    "o filme 'Interstellar' de Christopher Nolan",
    "o filme 'A Origem' (Inception)",
    "o filme 'Batman: O Cavaleiro das Trevas' (2008)",
    "a franquia 'Indiana Jones'",
    "o filme 'A Lista de Schindler'",
    "o filme 'Forrest Gump'",
    "o filme 'O Resgate do Soldado Ryan'",
    "a série 'Game of Thrones'",
    "a série 'Stranger Things'",
    "a série 'Friends'",
    "a série 'The Office' (US)",
    "a série 'Lost'",
    "a série 'Arquivo X' (The X-Files)",
    "a série de terror 'Supernatural'",
    "o filme 'Panico' (Scream 1996) e o subgênero Slasher",
    "o filme 'Halloween' (1978) de John Carpenter",
    "o filme 'O Massacre da Serra Elétrica' (1974)",
    "o filme 'O Oitavo Passageiro' e a franquia Alien",
    "o filme 'O Exterminador do Futuro 2: O Julgamento Final'",
    "o filme 'RoboCop' (1987) de Paul Verhoeven",
    "o filme 'Os Goonies' (1985)",
    "o filme 'Conta Comigo' (Stand by Me)",
    "o filme 'O Clube dos Cinco' (The Breakfast Club)",
    "o filme 'Sociedade dos Poetas Mortos'",
    "o filme 'O Grande Hotel Budapeste' de Wes Anderson",
    "o filme 'Psicose' (1960) de Alfred Hitchcock",
    "o filme 'Taxista' (Taxi Driver - 1976)",
    "o filme 'Os Bons Companheiros' (Goodfellas)",
    "o filme 'Scarface' (1983)",
    "o filme 'Laranja Mecânica'",
    "o filme 'Donnie Darko'",
    "o filme 'O Enigma de Outro Mundo' (The Thing 1982)",
    "o filme 'Mad Max: Estrada da Fúria'",
    "a franquia 'Gladiador' de Ridley Scott",
    "o filme 'Whiplash: Em Busca da Perfeição'",
    "o filme 'Parasita' (2019) de Bong Joon-ho",
    "a trilogia de filmes do 'Homem-Aranha' de Sam Raimi",
    "o filme 'V de Vingança' no cinema",
    "a franquia 'O Senhor dos Anéis' no cinema vs livros",
    "o filme brasileiro 'Auto da Compadecida'",

    # --- MÚSICA & BANDAS (60 Temas) ---
    "o álbum 'Dark Side of the Moon' do Pink Floyd",
    "a trajetória da banda de metal 'Iron Maiden'",
    "o movimento Grunge e a banda 'Nirvana'",
    "o álbum 'Thriller' e a carreira de Michael Jackson",
    "o festival 'Woodstock 1969'",
    "a banda 'Black Sabbath' e o nascimento do Heavy Metal",
    "o álbum 'Abbey Road' e o fim dos 'Beatles'",
    "o fenômeno global do K-Pop e a banda 'BTS'",
    "o show e festival 'Live Aid 1985'",
    "a carreira e os alter egos de 'David Bowie'",
    "o álbum 'Master of Puppets' do Metallica",
    "a trajetória da banda 'AC/DC'",
    "o festival 'Rock in Rio 1985' no Brasil",
    "o álbum 'OK Computer' do Radiohead",
    "a dupla de música eletrônica 'Daft Punk'",
    "a estética musical do Synthwave e anos 80",
    "a banda 'Led Zeppelin'",
    "a cena musical japonesa 'Visual Kei' (X Japan)",
    "a ascensão do 'Guns N' Roses' nos anos 90",
    "o movimento Punk de 1977 (Sex Pistols e Ramones)",
    "a carreira da banda 'Queen' e Freddie Mercury",
    "o álbum 'Nevermind' do Nirvana",
    "a trajetória do 'Red Hot Chili Peppers'",
    "a banda 'Foo Fighters' e Dave Grohl",
    "o álbum 'The Wall' do Pink Floyd",
    "a trajetória da banda 'Pearl Jam'",
    "a história da banda 'System of a Down'",
    "a trajetória da banda 'Slipknot'",
    "a banda 'Linkin Park' e o Nu Metal",
    "a trajetória da banda 'Rammstein'",
    "a história da banda 'Megadeth'",
    "a trajetória do 'Judas Priest'",
    "a banda 'Motorhead' e Lemmy Kilmister",
    "a história da banda 'Ozzy Osbourne' em carreira solo",
    "a trajetória da banda de metal progressivo 'Dream Theater'",
    "a banda brasileira 'Sepultura' e a projeção internacional",
    "a banda brasileira 'Angra' e o Power Metal",
    "o movimento 'Manguetown' e Chico Science & Nação Zumbi",
    "a trajetória da banda 'Legião Urbana'",
    "a banda 'Os Paralamas do Sucesso'",
    "a carreira de 'Raul Seixas'",
    "a trajetória de 'Tim Maia'",
    "a carreira e vida de 'Cazuza'",
    "a banda 'Charlie Brown Jr.' e o legado de Chorão",
    "a história do 'Raimundos' nos anos 90",
    "a trajetória dos 'Mamonas Assassinas'",
    "o movimento Pop Punk dos anos 2000 (Blink-182, Green Day)",
    "a banda 'Gorillaz' e a música virtual",
    "a carreira de 'Amy Winehouse'",
    "a trajetória de 'Prince'",
    "a carreira de 'Madonna' nos anos 80 e 90",
    "a trajetória de 'Britney Spears' nos anos 2000",
    "a história da banda 'The Cure' e o Rock Gótico",
    "a banda 'Joy Division' e 'New Order'",
    "a trajetória da banda 'Depeche Mode'",
    "a banda 'Oasis' e o Britpop dos anos 90",
    "a trajetória da banda 'The Strokes' nos anos 2000",
    "a banda 'Arctic Monkeys'",
    "a carreira solo de 'Eric Clapton'",
    "a trajetória da banda 'The Who'",

    # --- CARTOONS & QUADRINHOS (60 Temas) ---
    "o desenho 'Coragem, o Cão Covarde'",
    "a animação 'Avatar: A Lenda de Aang'",
    "o desenho 'O Laboratório de Dexter'",
    "a animação 'Batman: A Série Animada' (1992)",
    "o desenho 'As Meninas Superpoderosas'",
    "o desenho clássico 'Caverna do Dragão'",
    "a animação 'Apenas um Show' (Regular Show)",
    "o desenho 'Hora de Aventura'",
    "o estúdio de animação 'Hanna-Barbera'",
    "a HQ e graphic novel 'Watchmen' de Alan Moore",
    "a HQ 'O Cavaleiro das Trevas' de Frank Miller",
    "as histórias em quadrinhos da 'Turma da Mônica'",
    "a HQ 'Sandman' de Neil Gaiman",
    "a saga de quadrinhos 'A Morte do Superman'",
    "a graphic novel 'Maus' sobre o Holocausto",
    "a saga 'Guerra Civil' da Marvel Comics",
    "a história em quadrinhos 'A Piada Mortal' (Coringa)",
    "o selo de quadrinhos adultos 'Vertigo' da DC",
    "a HQ 'V de Vingança'",
    "o desenho clássico do 'Pica-Pau' no Brasil",
    "o desenho 'Os Simpsons' e seu impacto na TV",
    "o desenho 'Futurama'",
    "a animação 'South Park'",
    "a série animada 'Rick and Morty'",
    "a animação 'BoJack Horseman'",
    "o desenho 'X-Men: A Série Animada' (1992)",
    "o desenho 'Homem-Aranha: A Série Animada' (1994)",
    "o desenho 'Liga da Justiça' e 'Liga da Justiça Sem Limites'",
    "o desenho 'Super Choque' (Static Shock)",
    "o desenho 'Os Jovens Titãs' (2003)",
    "o desenho 'Ben 10' clássico",
    "o desenho 'Danny Phantom'",
    "o desenho 'O Aposento do Dexter'",
    "o desenho 'Johnny Bravo'",
    "o desenho 'A Vaca e o Frango'",
    "o desenho 'Eu Sou o Abalone' (I Am Weasel)",
    "o desenho 'Ed, Edd n Eddy'",
    "o desenho 'KND: A Turma do Bairro'",
    "o desenho 'As Terríveis Aventuras de Billy e Mandy'",
    "o desenho 'Mansão Foster para Amigos Imaginários'",
    "o desenho 'Phineas e Ferb'",
    "o desenho 'Gravity Falls: Um Verão de Mistérios'",
    "a animação 'Star Wars: The Clone Wars'",
    "o desenho clássico 'He-Man e os Mestres do Universo'",
    "o desenho 'Thundercats' (1985)",
    "o desenho 'Transformers' G1 original",
    "o desenho 'Tartarugas Ninja' (1987)",
    "o desenho 'Nossa Turma' (Get Along Gang)",
    "o desenho 'Ursinhos Carinhosos'",
    "o desenho 'Os Smurfs'",
    "a HQ 'Kingdom Come' (O Reino do Amanhã) da DC",
    "a HQ 'Berserker' e quadrinhos independentes",
    "a HQ 'Hellboy' de Mike Mignola",
    "a HQ 'Spawn' de Todd McFarlane",
    "a HQ 'The Walking Dead' nos quadrinhos",
    "a HQ 'Preacher' de Garth Ennis",
    "a HQ 'Invencível' (Invincible) de Robert Kirkman",
    "a HQ 'Scott Pilgrim' de Bryan Lee O'Malley",
    "a HQ nacional 'Astronauta' de Danilo Beyruth",
    "a trajetória do quadrinista 'Mauricio de Sousa'"
]

ARQUIVO_HISTORICO = "historico_pop_resenha.txt"


def tema_ja_usado(tema):
    if not os.path.exists(ARQUIVO_HISTORICO):
        return False
    with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
        linhas = f.read().splitlines()
    # Evita repetir o mesmo tema exato nos últimos 15 ciclos
    return tema in linhas[-15:]


def marcar_tema_usado(tema):
    with open(ARQUIVO_HISTORICO, "a", encoding="utf-8") as f:
        f.write(tema + "\n")


def escolher_tema():
    disponiveis = [t for t in TEMAS if not tema_ja_usado(t)]
    if not disponiveis:
        disponiveis = TEMAS
    return random.choice(disponiveis)


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
            headers={"User-Agent": "RoboResenhaPop/1.0"},
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
   consistency with the overall theme (nostalgic/documentary tone).

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
    qtd = calcular_qtd_imagens(wc, minimo, maximo, base_palavras=1400, palavras_por_imagem_extra=250)
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


def pedir_ia_groq(prompt, temperatura=0.7, max_tokens=None):
    kwargs = {
        "messages": [{"role": "user", "content": prompt}],
        "model": MODELO_IA,
        "temperature": temperatura,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    response = groq_client.chat.completions.create(**kwargs)
    return response.choices[0].message.content.strip()


def gerar_esqueleto(instrucao_tema):
    """STEP 1: Rolls a random angle and asks for a detailed skeleton.
    Injecting the angle guarantees fresh, non-repetitive posts over time."""

    angulos = [
        "Focus on Behind-the-Scenes and Development (how it was made, production struggles, the team, creation secrets).",
        "Critical and Thematic Analysis (hidden messages, philosophy, symbolism, analysis of the script or aesthetics).",
        "Cultural Impact and Legacy (how it changed the industry, revolutionized its genre, works it went on to influence).",
        "Little-Known Trivia and Easter Eggs (strange facts, easy-to-miss details, myths and truths).",
        "Nostalgic Perspective and Worldwide Reception (how it was broadcast/rented/streamed, dubbing, the fan craze at the time)."
    ]
    angulo_sorteado = random.choice(angulos)

    prompt = f"""
You are a documentary writer covering pop culture (anime, manga, cartoons, TV series, comics, music and video games).

Today's central topic (the source theme below may be written in Portuguese - that's just an internal
note; your entire output must be in English): {instrucao_tema}

MANDATORY ANGLE FOR TODAY'S PIECE:
"{angulo_sorteado}"

First, BEFORE writing the article, build a detailed SKELETON guided by this angle:
- Confirm the main topic and the chosen angle.
- List 5 to 7 topics/sections the article will cover.
- For each topic, write 1-2 sentences summarizing what will be covered, with NO repeated information.

Reply with only this skeleton, in plain text (no HTML), entirely in English.
"""
    return pedir_ia_groq(prompt, temperatura=0.6)


def gerar_artigo_completo(esqueleto):
    """STEP 2: Asks for the full article using the skeleton as a mandatory guide."""
    prompt = f"""
You are an award-winning pop culture writer, a true chronicler! You write documentary/retrospective-style
articles for a highly engaged fan blog. Write with GREAT care, take your time - this is a
featured, flagship article for the blog.
Reinforcing: you're a writer (who researches multiple sources) specialized in pop culture (anime, manga,
comics, cartoons, movies, TV series, video games and music) for an engaged fan blog. You know all the
latest happenings, you connect the dots from memory, and you write in a pleasant, funny,
behind-the-scenes-digging way. You know a bit of gossip here and there, and you build community.

Use this skeleton as a MANDATORY guide, developing each of its topics in depth,
without skipping any and without repeating information between sections:

{esqueleto}

CONTENT RULES:
- Base everything on real historical and cultural facts about the topic. Do NOT invent dates or numbers
  you're not sure about.
- Write in a pleasant, engaging way.
- FORBIDDEN to repeat the same sentence or idea. Every paragraph must move the narrative forward.
- MANDATORY length: AT LEAST 1400 words. Develop each section well.
- Write entirely in English (for a worldwide audience), regardless of what language the skeleton above
  was written in.

FORMAT RULES (pure HTML, no Markdown):
1. Start directly with an intriguing opening paragraph (no h1).
2. Each topic from the skeleton becomes its own <h2> subheading.
3. Include AT LEAST 2 light, funny author's notes, each inside a <blockquote>, with fan-like comments.
4. Do not include links in the body text.
5. End with a reflective closing paragraph about the topic's legacy.
"""
    return pedir_ia_groq(prompt, temperatura=0.75)


def gerar_titulo(esqueleto):
    prompt = (
        f"Based on this article skeleton:\n{esqueleto}\n\n"
        f"Create an engaging, nostalgic, SEO-optimized blog title in English, with no quotation marks. "
        f"Reply with only the title, plain text."
    )
    return pedir_ia_groq(prompt, temperatura=0.7).replace('"', '').strip()


def extrair_palavra_chave(esqueleto):
    prompt = (
        f"Based on this article skeleton:\n{esqueleto}\n\n"
        f"Give just ONE keyword in English that visually describes the main topic "
        f"(e.g. 'anime', 'rock concert', 'retro cartoon', 'vintage video game'). "
        f"Reply with only the word."
    )
    return pedir_ia_groq(prompt, temperatura=0.3).strip().lower().split()[0]


def gerar_cta():
    return """
<div style="background-color: #f4f6f8; border-radius: 12px; margin: 30px 0; padding: 25px; text-align: center; font-family: sans-serif;">
    <p style="font-size: 17px; font-weight: bold; color: #333; margin: 0 0 10px 0;">Enjoyed this trip down memory lane?</p>
    <p style="font-size: 14px; color: #555; margin: 0 0 15px 0;">Like it, drop a comment sharing your own memories of the topic, and share it with someone who'll get nostalgic too!</p>
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


if __name__ == "__main__":
    print("Generating a pop culture throwback/retrospective...")
    instrucao_tema = escolher_tema()
    print(f"Topic picked: {instrucao_tema}")

    esqueleto = gerar_esqueleto(instrucao_tema)
    print("Skeleton and angle generated. Writing the full article...")

    corpo = gerar_artigo_completo(esqueleto)
    titulo = gerar_titulo(esqueleto)

    try:
        galeria, secoes_brutas = montar_galeria_ia(
            titulo,
            corpo,
            minimo=QTD_MIN_IMAGENS,
            maximo=QTD_MAX_IMAGENS,
            contexto_extra=f"Article skeleton/topic: {esqueleto[:600]}",
        )
        img_html = gerar_tabela_imagem_blogger(galeria[0][0], titulo)
        corpo = inserir_imagens_no_corpo(corpo, secoes_brutas, galeria)
        print(f"Gallery with {len(galeria)} image(s) generated via Pollinations.ai.")
    except Exception as e:
        print(f"AI image generation failed, using fallback method (Openverse): {e}")
        palavra_chave = extrair_palavra_chave(esqueleto)
        img_url = buscar_imagem_openverse(palavra_chave)
        img_html = gerar_tabela_imagem_blogger(img_url, titulo)

    cta = gerar_cta()

    aviso = (
        '<p style="font-size: 12px; color: #888; font-style: italic;">This article is cultural, '
        'historical and opinion-based content, for entertainment and nostalgia purposes.</p>'
    )

    html_final = f"{img_html}{corpo}{cta}{aviso}"
    publicar_no_blogger(titulo, html_final, ["throwback", "retrospective", "pop culture"])
    marcar_tema_usado(instrucao_tema)
    print("Done!")
