# -*- coding: utf-8 -*-
"""
Caçador Particular de Passagens & Milhas

Busca em tempo real no Google Flights via SerpApi.

Estratégia A:
- Busca ida e volta como trechos separados.
- Combina as ofertas e encontra as menores combinações possíveis.

Estratégia B:
- Busca a passagem ida e volta como uma única tarifa round-trip.

Ainda não há integração de milhas. A área de recomendação
Cash vs. Milhas está preparada para a próxima etapa.
"""

import datetime
import itertools
from urllib.parse import quote_plus

import streamlit as st
from serpapi import GoogleSearch


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Caçador de Passagens - Multi-Estratégia",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ Caçador Particular de Passagens & Milhas")
st.caption(
    "Busca em tempo real no Google Flights (SerpApi) — "
    "Estratégia A: trechos separados | Estratégia B: ida e volta unificada"
)


# ============================================================
# SECRETS
# ============================================================
SERPAPI_KEY = st.secrets.get("SERPAPI_KEY", "")


# ============================================================
# AEROPORTOS
# ============================================================
AEROPORTOS = {
    "São Paulo - Todos os Aeroportos (SAO)": "SAO",
    "São Paulo - Guarulhos (GRU)": "GRU",
    "São Paulo - Congonhas (CGH)": "CGH",
    "São Paulo - Viracopos / Campinas (VCP)": "VCP",
    "Rio de Janeiro - Todos os Aeroportos (RIO)": "RIO",
    "Rio de Janeiro - Galeão (GIG)": "GIG",
    "Rio de Janeiro - Santos Dumont (SDU)": "SDU",
    "Belo Horizonte - Confins (CNF)": "CNF",
    "Belo Horizonte - Pampulha (PLU)": "PLU",
    "Brasília (BSB)": "BSB",
    "Salvador (SSA)": "SSA",
    "Recife (REC)": "REC",
    "Fortaleza (FOR)": "FOR",
    "Porto Alegre (POA)": "POA",
    "Curitiba (CWB)": "CWB",
    "Florianópolis (FLN)": "FLN",
    "Manaus (MAO)": "MAO",
    "Belém (BEL)": "BEL",
    "Goiânia (GYN)": "GYN",
    "Vitória (VIX)": "VIX",
    "Mendoza (MDZ)": "MDZ",
    "Buenos Aires - Todos (BUE)": "BUE",
    "Miami (MIA)": "MIA",
    "Orlando (MCO)": "MCO",
    "Nova York - Todos (NYC)": "NYC",
    "Lisboa (LIS)": "LIS",
    "Madri (MAD)": "MAD",
}

LISTA_AEROPORTOS = list(AEROPORTOS.keys())


# ============================================================
# FORMULÁRIO
# ============================================================
col_tipo, col_classe = st.columns(2)

with col_tipo:
    tipo_viagem = st.radio(
        "Tipo de viagem:",
        ["Somente Ida", "Ida e Volta"],
        horizontal=True,
    )

with col_classe:
    classe_cabine = st.radio(
        "Classe:",
        ["economy", "business", "first"],
        horizontal=True,
        format_func=lambda classe: {
            "economy": "Econômica",
            "business": "Executiva",
            "first": "Primeira Classe",
        }[classe],
    )

st.write("")

col1, col2, col3, col4, col5 = st.columns([3, 3, 2, 2, 2])

with col1:
    origem_selecionada = st.selectbox(
        "✈️ Origem",
        LISTA_AEROPORTOS,
        index=1,
    )
    origem_iata = AEROPORTOS[origem_selecionada]

with col2:
    destino_selecionado = st.selectbox(
        "✈️ Destino",
        LISTA_AEROPORTOS,
        index=5,
    )
    destino_iata = AEROPORTOS[destino_selecionado]

with col3:
    data_ida = st.date_input(
        "Data de ida",
        value=datetime.date.today() + datetime.timedelta(days=7),
    )

with col4:
    if tipo_viagem == "Ida e Volta":
        data_volta = st.date_input(
            "Data de volta",
            value=data_ida + datetime.timedelta(days=7),
            min_value=data_ida,
        )
    else:
        data_volta = None
        st.text_input(
            "Data de volta",
            value="Apenas ida",
            disabled=True,
        )

with col5:
    numero_passageiros = st.number_input(
        "Passageiros",
        min_value=1,
        max_value=9,
        value=1,
        step=1,
    )


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================
CLASSES_SERPAPI = {
    "economy": 1,
    "premium_economy": 2,
    "business": 3,
    "first": 4,
}


def formatar_valor_brl(valor):
    """Formata valor no padrão brasileiro."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_duracao(minutos):
    """Transforma minutos em horas e minutos."""
    if not minutos:
        return "Não informado"

    horas = minutos // 60
    minutos_restantes = minutos % 60

    if horas <= 0:
        return f"{minutos_restantes}min"

    return f"{horas}h {minutos_restantes}min"


def extrair_horario(campo_horario):
    """
    O Google Flights/SerpApi pode devolver horário como:
    '2026-08-08 06:00' ou apenas '06:00'.
    """
    if not campo_horario:
        return "—"

    texto = str(campo_horario).strip()

    if " " in texto:
        return texto.split()[-1]

    return texto


def converter_preco_para_float(preco):
    """
    Converte preço da SerpApi em float.
    Aceita exemplos como:
    500
    500.0
    'R$ 500'
    '1.250'
    """
    if preco is None:
        return 0.0

    if isinstance(preco, (int, float)):
        return float(preco)

    texto = str(preco).strip()
    texto = texto.replace("R$", "").replace("BRL", "").strip()
    texto = texto.replace(".", "").replace(",", ".")

    try:
        return float(texto)
    except ValueError:
        return 0.0


def gerar_link_google_flights(
    origem,
    destino,
    data_ida_obj,
    data_volta_obj=None,
):
    """Gera link de conferência no Google Flights."""
    consulta = f"Flights to {destino} from {origem} on {data_ida_obj.strftime('%Y-%m-%d')}"

    if data_volta_obj:
        consulta += f" through {data_volta_obj.strftime('%Y-%m-%d')}"

    return f"https://www.google.com/travel/flights?q={quote_plus(consulta)}"


# ============================================================
# NORMALIZAÇÃO DAS OFERTAS DA SERPAPI
# ============================================================
def normalizar_oferta_serpapi(oferta_bruta, trecho, estrategia, indice):
    """
    Converte o retorno bruto da SerpApi em um formato padronizado.

    trecho:
        ida | volta | ida_volta

    estrategia:
        A_separado | B_unificado
    """
    voos = oferta_bruta.get("flights", [])

    if not voos:
        return None

    primeiro_voo = voos[0]
    ultimo_voo = voos[-1]

    companhia_inicio = primeiro_voo.get("airline", "")
    companhia_fim = ultimo_voo.get("airline", "")

    if companhia_inicio and companhia_fim and companhia_inicio != companhia_fim:
        companhia = f"{companhia_inicio} / {companhia_fim}"
    else:
        companhia = companhia_inicio or companhia_fim or "Companhia aérea"

    numeros_voo = []

    for voo in voos:
        numero = voo.get("flight_number", "")
        if numero and numero not in numeros_voo:
            numeros_voo.append(numero)

    numero_voo = " / ".join(numeros_voo)

    aeroporto_saida = primeiro_voo.get("departure_airport", {})
    aeroporto_chegada = ultimo_voo.get("arrival_airport", {})

    preco = converter_preco_para_float(oferta_bruta.get("price", 0))
    moeda = oferta_bruta.get("currency", "BRL")

    tipo_origem = oferta_bruta.get("tipo_origem", "other_flights")

    return {
        "fonte": "Google Flights",
        "estrategia": estrategia,
        "trecho": trecho,
        "indice": indice,
        "tipo_origem": tipo_origem,
        "cia": companhia,
        "num_voo": numero_voo,
        "escalas": max(0, len(voos) - 1),
        "duracao_min": oferta_bruta.get("total_duration", 0),
        "duracao_fmt": formatar_duracao(oferta_bruta.get("total_duration", 0)),
        "dep_iata": aeroporto_saida.get("id", ""),
        "dep_time": extrair_horario(aeroporto_saida.get("time", "")),
        "arr_iata": aeroporto_chegada.get("id", ""),
        "arr_time": extrair_horario(aeroporto_chegada.get("time", "")),
        "preco": preco,
        "moeda": moeda,
    }


# ============================================================
# CONSULTA À SERPAPI
# ============================================================
def executar_serpapi(parametros, descricao_busca):
    """
    Executa busca na SerpApi e separa mensagens de erro.
    """
    try:
        resultado = GoogleSearch(parametros).get_dict()

        if resultado.get("error"):
            return [], str(resultado["error"])

        todas_ofertas = []

        for oferta in resultado.get("best_flights", []) or []:
            oferta = dict(oferta)
            oferta["tipo_origem"] = "best_flights"
            todas_ofertas.append(oferta)

        for oferta in resultado.get("other_flights", []) or []:
            oferta = dict(oferta)
            oferta["tipo_origem"] = "other_flights"
            todas_ofertas.append(oferta)

        if not todas_ofertas:
            chaves = ", ".join(sorted(resultado.keys()))

            return [], (
                "A SerpApi respondeu sem opções de voo. "
                f"Campos recebidos: {chaves}. "
                "Tente outra data, rota, classe ou verifique os créditos da SerpApi."
            )

        return todas_ofertas, None

    except Exception as erro:
        return [], f"Erro técnico na busca {descricao_busca}: {erro}"


def criar_parametros_base(origem, destino, data, passageiros, classe):
    """Cria parâmetros compartilhados pelas buscas."""
    return {
        "engine": "google_flights",
        "departure_id": origem,
        "arrival_id": destino,
        "outbound_date": data.strftime("%Y-%m-%d"),
        "currency": "BRL",
        "hl": "pt-BR",
        "gl": "br",
        "adults": int(passageiros),
        "travel_class": CLASSES_SERPAPI.get(classe, 1),
        "api_key": SERPAPI_KEY,
    }


def buscar_ida(origem, destino, data, passageiros, classe):
    """Estratégia A: busca trecho avulso de ida."""
    if not SERPAPI_KEY:
        return [], "SERPAPI_KEY não configurada."

    parametros = criar_parametros_base(
        origem,
        destino,
        data,
        passageiros,
        classe,
    )

    parametros["type"] = 2

    return executar_serpapi(
        parametros,
        f"ida {origem}-{destino}",
    )


def buscar_ida_volta_unificada(
    origem,
    destino,
    data_ida_obj,
    data_volta_obj,
    passageiros,
    classe,
):
    """Estratégia B: busca ida e volta em uma única tarifa."""
    if not SERPAPI_KEY:
        return [], "SERPAPI_KEY não configurada."

    parametros = criar_parametros_base(
        origem,
        destino,
        data_ida_obj,
        passageiros,
        classe,
    )

    parametros["type"] = 1
    parametros["return_date"] = data_volta_obj.strftime("%Y-%m-%d")

    return executar_serpapi(
        parametros,
        f"ida e volta {origem}-{destino}",
    )


# ============================================================
# MOTOR DE RANKING CASH
# ============================================================
def gerar_combinacoes_ida_volta(
    ofertas_ida,
    ofertas_volta,
    top_n=5,
    max_ofertas_por_trecho=8,
):
    """
    Combina as opções de ida com as opções de volta.

    Em vez de combinar:
    - primeira ida com primeira volta;
    - segunda ida com segunda volta;

    O código testa todas as combinações possíveis entre as ofertas
    mais relevantes e ordena pelo preço total mais baixo.
    """
    idas_para_calculo = sorted(
        ofertas_ida,
        key=lambda oferta: oferta["preco"],
    )[:max_ofertas_por_trecho]

    voltas_para_calculo = sorted(
        ofertas_volta,
        key=lambda oferta: oferta["preco"],
    )[:max_ofertas_por_trecho]

    combinacoes = []

    for ida, volta in itertools.product(idas_para_calculo, voltas_para_calculo):
        combinacoes.append(
            {
                "ida": ida,
                "volta": volta,
                "preco_total": ida["preco"] + volta["preco"],
            }
        )

    combinacoes.sort(key=lambda combinacao: combinacao["preco_total"])

    return combinacoes[:top_n]


def rotulo_tipo_preco(numero_passageiros):
    """
    A SerpApi normalmente devolve o preço conforme os passageiros
    enviados na consulta. Como isso pode variar dependendo do retorno
    do Google Flights, o app deixa o número de passageiros explícito.
    """
    if numero_passageiros == 1:
        return "Consulta para 1 passageiro"

    return f"Consulta para {numero_passageiros} passageiros"


# ============================================================
# RECOMENDAÇÃO CASH VS. MILHAS (PREPARAÇÃO)
# ============================================================
ESTADOS_RECOMENDACAO = {
    "milhas": {
        "titulo": "✨ VALE EMITIR COM MILHAS",
        "tipo": "success",
        "texto": (
            "A emissão em milhas oferece melhor custo-benefício nesta rota. "
            "Verifique disponibilidade antes de transferir pontos."
        ),
    },
    "dinheiro": {
        "titulo": "💸 MELHOR PAGAR EM DINHEIRO",
        "tipo": "warning",
        "texto": (
            "O preço em dinheiro está competitivo para esta rota. "
            "Preserve suas milhas para uma oportunidade com valor melhor."
        ),
    },
    "aguardar": {
        "titulo": "⏳ AGUARDAR OPORTUNIDADE OU BÔNUS DE TRANSFERÊNCIA",
        "tipo": "info",
        "texto": (
            "A camada de milhas ainda não está conectada. "
            "Quando integrarmos programas e disponibilidade award, o sistema "
            "indicará automaticamente se vale pagar em dinheiro ou emitir."
        ),
    },
}


def exibir_recomendacao(estado="aguardar"):
    configuracao = ESTADOS_RECOMENDACAO[estado]

    st.markdown("## 💡 Recomendação Cash vs. Milhas")
    getattr(st, configuracao["tipo"])(
        f"**{configuracao['titulo']}**\n\n{configuracao['texto']}"
    )


# ============================================================
# COMPONENTES DE EXIBIÇÃO
# ============================================================
def exibir_card_ida(oferta, data_ida_texto, passageiros, link_google):
    """Exibe card de oferta somente ida."""
    tag = (
        "🏆 MENOR TARIFA GOOGLE"
        if oferta["indice"] == 0
        else "✅ OPORTUNIDADE ENCONTRADA"
    )

    st.markdown(
        f"""
        ### ✈️ {oferta["cia"]}
        <span style="
            background-color:#d4edda;
            color:#155724;
            padding:3px 8px;
            border-radius:5px;
            font-size:12px;
        ">
            {tag}
        </span>
        """,
        unsafe_allow_html=True,
    )

    coluna_voo, coluna_preco, coluna_botao = st.columns([4, 4, 3])

    with coluna_voo:
        numero = f" • Voo {oferta['num_voo']}" if oferta["num_voo"] else ""

        st.info(
            f"**✈️ IDA ({data_ida_texto})**{numero}\n\n"
            f"**{oferta['dep_iata']}** ({oferta['dep_time']}) → "
            f"**{oferta['arr_iata']}** ({oferta['arr_time']})\n\n"
            f"⏱️ Duração: {oferta['duracao_fmt']} | "
            f"Escalas: {oferta['escalas']}"
        )

    with coluna_preco:
        st.warning(
            f"**TARIFA DE REFERÊNCIA**\n\n"
            f"### {formatar_valor_brl(oferta['preco'])}\n"
            f"{rotulo_tipo_preco(passageiros)}\n\n"
            f"Fonte: Google Flights"
        )

    with coluna_botao:
        st.write("")
        st.write("")
        st.link_button(
            "Ver no Google Flights 🔗",
            link_google,
            use_container_width=True,
        )

    st.divider()


def exibir_card_combinacao(
    combinacao,
    indice,
    data_ida_texto,
    data_volta_texto,
    passageiros,
    link_google,
):
    """Exibe uma combinação de ida e volta da Estratégia A."""
    ida = combinacao["ida"]
    volta = combinacao["volta"]
    preco_total = combinacao["preco_total"]

    tag = (
        "🏆 MELHOR COMBINAÇÃO REAL"
        if indice == 0
        else "✅ OPORTUNIDADE ENCONTRADA"
    )

    st.markdown(
        f"""
        ### ✈️ {ida["cia"]} / {volta["cia"]}
        <span style="
            background-color:#d4edda;
            color:#155724;
            padding:3px 8px;
            border-radius:5px;
            font-size:12px;
        ">
            {tag}
        </span>
        """,
        unsafe_allow_html=True,
    )

    coluna_ida, coluna_volta, coluna_total, coluna_botao = st.columns([3, 3, 3, 2])

    with coluna_ida:
        numero_ida = f" • Voo {ida['num_voo']}" if ida["num_voo"] else ""

        st.info(
            f"**✈️ IDA ({data_ida_texto})**{numero_ida}\n\n"
            f"**{ida['dep_iata']}** ({ida['dep_time']}) → "
            f"**{ida['arr_iata']}** ({ida['arr_time']})\n\n"
            f"⏱️ {ida['duracao_fmt']} | {ida['escalas']} escala(s)\n\n"
            f"Preço da ida: **{formatar_valor_brl(ida['preco'])}**"
        )

    with coluna_volta:
        numero_volta = f" • Voo {volta['num_voo']}" if volta["num_voo"] else ""

        st.info(
            f"**✈️ VOLTA ({data_volta_texto})**{numero_volta}\n\n"
            f"**{volta['dep_iata']}** ({volta['dep_time']}) → "
            f"**{volta['arr_iata']}** ({volta['arr_time']})\n\n"
            f"⏱️ {volta['duracao_fmt']} | {volta['escalas']} escala(s)\n\n"
            f"Preço da volta: **{formatar_valor_brl(volta['preco'])}**"
        )

    with coluna_total:
        st.warning(
            f"**TARIFA TOTAL COMBINADA**\n\n"
            f"### {formatar_valor_brl(preco_total)}\n"
            f"{rotulo_tipo_preco(passageiros)}\n\n"
            f"Fonte: Google Flights\n"
            f"Soma de ida + volta separadas"
        )

    with coluna_botao:
        st.write("")
        st.write("")
        st.link_button(
            "Ver no Google Flights 🔗",
            link_google,
            use_container_width=True,
        )

    st.divider()


def exibir_card_round_trip(
    oferta,
    indice,
    passageiros,
    link_google,
):
    """Exibe oferta da Estratégia B: ida e volta unificada."""
    tag = (
        "🏆 MELHOR TARIFA ROUND-TRIP"
        if indice == 0
        else "✅ OPORTUNIDADE ENCONTRADA"
    )

    st.markdown(
        f"""
        ### ✈️ {oferta["cia"]}
        <span style="
            background-color:#cce5ff;
            color:#004085;
            padding:3px 8px;
            border-radius:5px;
            font-size:12px;
        ">
            {tag}
        </span>
        """,
        unsafe_allow_html=True,
    )

    coluna_voo, coluna_preco, coluna_botao = st.columns([4, 4, 3])

    with coluna_voo:
        numero = f" • Voo {oferta['num_voo']}" if oferta["num_voo"] else ""

        st.info(
            f"**✈️ IDA + VOLTA (tarifa única)**{numero}\n\n"
            f"Trecho de ida: **{oferta['dep_iata']}** ({oferta['dep_time']}) → "
            f"**{oferta['arr_iata']}** ({oferta['arr_time']})\n\n"
            f"⏱️ Duração da ida: {oferta['duracao_fmt']} | "
            f"Escalas: {oferta['escalas']}"
        )

    with coluna_preco:
        st.warning(
            f"**TARIFA ROUND-TRIP ÚNICA**\n\n"
            f"### {formatar_valor_brl(oferta['preco'])}\n"
            f"{rotulo_tipo_preco(passageiros)}\n\n"
            f"Tarifa ida + volta já combinada.\n"
            f"Fonte: Google Flights"
        )

    with coluna_botao:
        st.write("")
        st.write("")
        st.link_button(
            "Ver no Google Flights 🔗",
            link_google,
            use_container_width=True,
        )

    st.divider()


# ============================================================
# EXECUÇÃO DA BUSCA
# ============================================================
if st.button(
    "🔍 Buscar melhores ofertas no Google Flights",
    use_container_width=True,
):
    if not SERPAPI_KEY:
        st.error(
            "A chave `SERPAPI_KEY` não está configurada nos Secrets do Streamlit."
        )

    elif origem_iata == destino_iata:
        st.error("Origem e destino não podem ser iguais.")

    elif tipo_viagem == "Ida e Volta" and data_volta <= data_ida:
        st.error("A data de volta deve ser posterior à data de ida.")

    else:
        st.divider()

        data_ida_texto = data_ida.strftime("%d/%m/%Y")
        data_volta_texto = (
            data_volta.strftime("%d/%m/%Y")
            if data_volta
            else ""
        )

        titulo = (
            f"📍 Busca real de {origem_iata} para {destino_iata} "
            f"({data_ida_texto}) — classe {classe_cabine}"
        )

        if data_volta:
            titulo += f" | Volta: {data_volta_texto}"

        st.subheader(titulo)

        ofertas_ida = []
        ofertas_volta = []
        ofertas_round_trip = []

        erro_ida = None
        erro_volta = None
        erro_round_trip = None

        # ====================================================
        # ESTRATÉGIA A — TRECHOS SEPARADOS
        # ====================================================
        with st.spinner(
            "Consultando Google Flights — Estratégia A: trechos separados..."
        ):
            resultado_ida, erro_ida = buscar_ida(
                origem_iata,
                destino_iata,
                data_ida,
                numero_passageiros,
                classe_cabine,
            )

            for indice, oferta_bruta in enumerate(resultado_ida):
                oferta_normalizada = normalizar_oferta_serpapi(
                    oferta_bruta,
                    trecho="ida",
                    estrategia="A_separado",
                    indice=indice,
                )

                if oferta_normalizada:
                    ofertas_ida.append(oferta_normalizada)

            if tipo_viagem == "Ida e Volta" and data_volta:
                resultado_volta, erro_volta = buscar_ida(
                    destino_iata,
                    origem_iata,
                    data_volta,
                    numero_passageiros,
                    classe_cabine,
                )

                for indice, oferta_bruta in enumerate(resultado_volta):
                    oferta_normalizada = normalizar_oferta_serpapi(
                        oferta_bruta,
                        trecho="volta",
                        estrategia="A_separado",
                        indice=indice,
                    )

                    if oferta_normalizada:
                        ofertas_volta.append(oferta_normalizada)

        # ====================================================
        # ESTRATÉGIA B — IDA E VOLTA UNIFICADA
        # ====================================================
        if tipo_viagem == "Ida e Volta" and data_volta:
            with st.spinner(
                "Consultando Google Flights — Estratégia B: ida e volta unificada..."
            ):
                resultado_round_trip, erro_round_trip = buscar_ida_volta_unificada(
                    origem_iata,
                    destino_iata,
                    data_ida,
                    data_volta,
                    numero_passageiros,
                    classe_cabine,
                )

                for indice, oferta_bruta in enumerate(resultado_round_trip):
                    oferta_normalizada = normalizar_oferta_serpapi(
                        oferta_bruta,
                        trecho="ida_volta",
                        estrategia="B_unificado",
                        indice=indice,
                    )

                    if oferta_normalizada:
                        ofertas_round_trip.append(oferta_normalizada)

        # ====================================================
        # ERROS / DIAGNÓSTICO
        # ====================================================
        erros = [
            ("Busca de ida", erro_ida),
            ("Busca de volta", erro_volta),
            ("Busca ida e volta unificada", erro_round_trip),
        ]

        for descricao, erro in erros:
            if erro:
                st.warning(f"**{descricao}:** {erro}")

        # ====================================================
        # RESUMO
        # ====================================================
        col_resumo_1, col_resumo_2, col_resumo_3 = st.columns(3)

        with col_resumo_1:
            st.success(
                f"Estratégia A — Ida: {len(ofertas_ida)} opções"
            )

        with col_resumo_2:
            if tipo_viagem == "Ida e Volta":
                st.info(
                    f"Estratégia A — Volta: {len(ofertas_volta)} opções"
                )
            else:
                st.info("Estratégia A — Volta: n/a (somente ida)")

        with col_resumo_3:
            if tipo_viagem == "Ida e Volta":
                st.warning(
                    f"Estratégia B — Round-trip único: "
                    f"{len(ofertas_round_trip)} opções"
                )
            else:
                st.info("Estratégia B — n/a (somente ida)")

        st.write("")

        # ====================================================
        # NENHUM RESULTADO
        # ====================================================
        if not ofertas_ida and not ofertas_round_trip:
            st.warning(
                "Nenhum voo encontrado no Google Flights para os parâmetros informados."
            )

            st.info(
                """
                **Checklist rápido**

                1. Confirme que a `SERPAPI_KEY` está configurada;
                2. Confira se sua conta SerpApi possui créditos;
                3. Teste uma data entre 15 e 60 dias à frente;
                4. Teste aeroportos agregados, como SAO e RIO;
                5. Tente a mesma rota diretamente no Google Flights.
                """
            )

        # ====================================================
        # ESTRATÉGIA A — SOMENTE IDA
        # ====================================================
        if tipo_viagem == "Somente Ida" and ofertas_ida:
            st.markdown("## 🧭 Estratégia A — Trechos separados")

            ofertas_ida_ordenadas = sorted(
                ofertas_ida,
                key=lambda oferta: oferta["preco"],
            )

            link_google = gerar_link_google_flights(
                origem_iata,
                destino_iata,
                data_ida,
            )

            for indice, oferta in enumerate(ofertas_ida_ordenadas[:5]):
                oferta["indice"] = indice

                exibir_card_ida(
                    oferta,
                    data_ida_texto,
                    numero_passageiros,
                    link_google,
                )

        # ====================================================
        # ESTRATÉGIA A — IDA E VOLTA COMBINADAS
        # ====================================================
        melhores_combinacoes = []

        if (
            tipo_viagem == "Ida e Volta"
            and ofertas_ida
            and ofertas_volta
        ):
            st.markdown("## 🧭 Estratégia A — Trechos separados")

            st.caption(
                "As opções abaixo testam combinações entre voos de ida e de volta "
                "e são ordenadas pelo menor preço total. "
                "Não é apenas uma soma de ofertas com o mesmo índice."
            )

            melhores_combinacoes = gerar_combinacoes_ida_volta(
                ofertas_ida,
                ofertas_volta,
                top_n=5,
                max_ofertas_por_trecho=8,
            )

            link_google = gerar_link_google_flights(
                origem_iata,
                destino_iata,
                data_ida,
                data_volta,
            )

            for indice, combinacao in enumerate(melhores_combinacoes):
                exibir_card_combinacao(
                    combinacao,
                    indice,
                    data_ida_texto,
                    data_volta_texto,
                    numero_passageiros,
                    link_google,
                )

        # ====================================================
        # ESTRATÉGIA B — TARIFA ROUND-TRIP UNIFICADA
        # ====================================================
        if tipo_viagem == "Ida e Volta" and ofertas_round_trip:
            st.markdown("## 🎟️ Estratégia B — Ida e volta unificada")

            st.caption(
                "Nesta estratégia, o Google Flights consulta uma tarifa de ida e volta "
                "emitida conjuntamente. Esse valor já representa a viagem completa "
                "e não deve ser somado a outro trecho."
            )

            ofertas_round_trip_ordenadas = sorted(
                ofertas_round_trip,
                key=lambda oferta: oferta["preco"],
            )

            link_google = gerar_link_google_flights(
                origem_iata,
                destino_iata,
                data_ida,
                data_volta,
            )

            for indice, oferta in enumerate(ofertas_round_trip_ordenadas[:5]):
                exibir_card_round_trip(
                    oferta,
                    indice,
                    numero_passageiros,
                    link_google,
                )

        # ====================================================
        # COMPARATIVO A VS B
        # ====================================================
        if tipo_viagem == "Ida e Volta":
            melhor_preco_a = None
            melhor_preco_b = None

            if melhores_combinacoes:
                melhor_preco_a = melhores_combinacoes[0]["preco_total"]

            if ofertas_round_trip:
                melhor_preco_b = min(
                    oferta["preco"] for oferta in ofertas_round_trip
                )

            if melhor_preco_a is not None or melhor_preco_b is not None:
                st.markdown(
                    "## ⚖️ Comparativo: trechos separados vs. tarifa unificada"
                )

                coluna_a, coluna_b = st.columns(2)

                with coluna_a:
                    if melhor_preco_a is not None:
                        st.info(
                            "**Melhor combinação separada (A)**\n\n"
                            f"### {formatar_valor_brl(melhor_preco_a)}"
                        )
                    else:
                        st.info("Nenhuma combinação válida encontrada na Estratégia A.")

                with coluna_b:
                    if melhor_preco_b is not None:
                        st.info(
                            "**Melhor tarifa ida e volta unificada (B)**\n\n"
                            f"### {formatar_valor_brl(melhor_preco_b)}"
                        )
                    else:
                        st.info("Nenhuma tarifa válida encontrada na Estratégia B.")

                if melhor_preco_a is not None and melhor_preco_b is not None:
                    diferenca = abs(melhor_preco_a - melhor_preco_b)

                    if melhor_preco_a < melhor_preco_b:
                        st.success(
                            "✅ **Trechos separados são mais baratos nesta busca.**\n\n"
                            f"Economia estimada: {formatar_valor_brl(diferenca)}."
                        )

                    elif melhor_preco_b < melhor_preco_a:
                        st.success(
                            "✅ **A tarifa ida e volta unificada é mais barata nesta busca.**\n\n"
                            f"Economia estimada: {formatar_valor_brl(diferenca)}."
                        )

                    else:
                        st.info(
                            "As duas estratégias retornaram o mesmo preço total."
                        )

        # ====================================================
        # MELHOR TARIFA CASH
        # ====================================================
        precos_encontrados = []

        if tipo_viagem == "Somente Ida":
            precos_encontrados.extend(
                oferta["preco"] for oferta in ofertas_ida
            )

        if melhores_combinacoes:
            precos_encontrados.extend(
                combinacao["preco_total"]
                for combinacao in melhores_combinacoes
            )

        if ofertas_round_trip:
            precos_encontrados.extend(
                oferta["preco"]
                for oferta in ofertas_round_trip
            )

        if precos_encontrados:
            melhor_cash = min(precos_encontrados)

            st.info(
                f"💰 **Melhor tarifa em dinheiro encontrada:** "
                f"{formatar_valor_brl(melhor_cash)}"
            )

        # ====================================================
        # PRÓXIMA ETAPA: MILHAS
        # ====================================================
        exibir_recomendacao("aguardar")
