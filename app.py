import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from serpapi import GoogleSearch
import streamlit as st

# Configuração da Página
st.set_page_config(
    page_title="Caçador de Passagens - Multi-Base",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ Caçador Particular de Passagens & Milhas")
st.caption(
    "Cruzamento de dados em tempo real: Google Flights (SerpApi) 🆚 Duffel API"
)

# Puxa as chaves dos Secrets do Streamlit Cloud
SERPAPI_KEY = st.secrets.get("SERPAPI_KEY", "")
DUFFEL_TOKEN = st.secrets.get("DUFFEL_TOKEN", "")

# --- DICIONÁRIO DE AEROPORTOS ---
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

lista_opcoes_aeroportos = list(AEROPORTOS.keys())

# --- OPÇÕES SUPERIORES DE FILTRO ---
col_opt1, col_opt2 = st.columns(2)

with col_opt1:
    tipo_viagem = st.radio(
        "Tipo de Viagem:",
        options=["Somente Ida", "Ida e Volta"],
        horizontal=True,
        index=0,
    )

with col_opt2:
    modalidade_busca = st.radio(
        "Buscar por:",
        options=["Dinheiro", "Milhas"],
        horizontal=True,
        index=0,
    )

st.write("")

# --- FORMULÁRIO DE BUSCA ---
col1, col2, col3, col4, col5 = st.columns([3, 3, 2, 2, 2])

with col1:
    origem_sel = st.selectbox(
        "🛫 Origem",
        options=lista_opcoes_aeroportos,
        index=1,
    )
    origem_iata = AEROPORTOS[origem_sel]

with col2:
    destino_sel = st.selectbox(
        "🛬 Destino",
        options=lista_opcoes_aeroportos,
        index=5,
    )
    destino_iata = AEROPORTOS[destino_sel]

with col3:
    data_ida = st.date_input(
        "📅 Data de Ida", datetime.date.today() + datetime.timedelta(days=7)
    )

with col4:
    if tipo_viagem == "Ida e Volta":
        data_volta = st.date_input(
            "📅 Data de Volta", data_ida + datetime.timedelta(days=7)
        )
    else:
        data_volta = None
        st.text_input("📅 Data de Volta", value="Apenas Ida", disabled=True)

with col5:
    num_pax = st.number_input(
        "👤 Passageiros", min_value=1, max_value=9, value=1
    )


# --- BUSCA 1: SERPAPI (GOOGLE FLIGHTS) ---
def buscar_serpapi(dep_iata, arr_iata, data_obj):
    if not SERPAPI_KEY:
        return []
    try:
        data_iso = data_obj.strftime("%Y-%m-%d")
        params = {
            "engine": "google_flights",
            "departure_id": dep_iata,
            "arrival_id": arr_iata,
            "outbound_date": data_iso,
            "currency": "BRL",
            "hl": "pt",
            "type": "2",
            "adults": int(num_pax),
            "api_key": SERPAPI_KEY,
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        all_flights = []
        if "best_flights" in results:
            all_flights.extend(results["best_flights"])
        if "other_flights" in results:
            all_flights.extend(results["other_flights"])
        return all_flights
    except Exception as e:
        st.warning(f"Aviso SerpApi: {e}")
        return []


# --- BUSCA 2: DUFFEL API (REQUISIÇÃO POR TRECHO ÚNICO) ---
def buscar_duffel_single_slice(dep_iata, arr_iata, data_obj):
    if not DUFFEL_TOKEN:
        return [], "Chave DUFFEL_TOKEN não configurada."
    try:
        url = "https://api.duffel.com/air/offer_requests?return_offers=true"
        headers = {
            "Authorization": f"Bearer {DUFFEL_TOKEN}",
            "Duffel-Version": "v2",
            "Content-Type": "application/json",
        }

        payload = {
            "data": {
                "slices": [{
                    "origin": dep_iata,
                    "destination": arr_iata,
                    "departure_date": data_obj.strftime("%Y-%m-%d"),
                }],
                "passengers": [{"type": "adult"} for _ in range(int(num_pax))],
                "cabin_class": "economy",
            }
        }

        session = requests.Session()
        retries = Retry(
            total=2, backoff_factor=1, status_forcelist=[500, 502, 503, 504]
        )
        session.mount("https://", HTTPAdapter(max_retries=retries))

        res = session.post(url, json=payload, headers=headers, timeout=30)
        data = res.json()

        if res.status_code in (200, 201):
            offers = data.get("data", {}).get("offers", [])
            msg = "OK" if offers else "Sem voos retornados para este trecho."
            return offers, msg
        else:
            err_msg = data.get("errors", [{}])[0].get("message", "Erro desconhecido")
            return [], f"Detalhe Duffel: {err_msg}"
    except requests.exceptions.Timeout:
        return [], "Detalhe Duffel: Tempo limite excedido."
    except Exception as e:
        return [], f"Detalhe Duffel: {e}"


# --- PROCESSAMENTO E CRUZAMENTO ---
if st.button("🔎 Cruzar Bases e Buscar Melhores Ofertas", use_container_width=True):
    if not SERPAPI_KEY and not DUFFEL_TOKEN:
        st.error("⚠️ Nenhuma chave de API configurada nos Secrets.")
    else:
        st.divider()
        data_br_ida = data_ida.strftime("%d/%m/%Y")
        data_iso_ida = data_ida.strftime("%Y-%m-%d")
        timestamp_ms_ida = int(
            datetime.datetime.combine(data_ida, datetime.time.min).timestamp()
            * 1000
        )

        titulo_busca = f"📍 Cruzamento Reais de {origem_iata} para {destino_iata} ({data_br_ida}) • {modalidade_busca}"
        if tipo_viagem == "Ida e Volta" and data_volta:
            data_br_volta = data_volta.strftime("%d/%m/%Y")
            titulo_busca += f" | Volta: {data_br_volta}"

        st.subheader(titulo_busca)

        with st.spinner("Consultando Google Flights e Duffel API com requisições independentes..."):
            # Buscas SerpApi (Google Flights)
            voos_ida_serp = buscar_serpapi(origem_iata, destino_iata, data_ida)
            voos_volta_serp = (
                buscar_serpapi(destino_iata, origem_iata, data_volta)
                if (tipo_viagem == "Ida e Volta" and data_volta)
                else []
            )

            # Buscas Duffel (Independentes por trecho)
            voos_ida_duffel, status_duffel_ida = buscar_duffel_single_slice(
                origem_iata, destino_iata, data_ida
            )
            voos_volta_duffel, status_duffel_volta = (
                buscar_duffel_single_slice(destino_iata, origem_iata, data_volta)
                if (tipo_viagem == "Ida e Volta" and data_volta)
                else ([], "N/A")
            )

            col_b1, col_b2 = st.columns(2)
            with col_b1:
                st.success(
                    f"✅ Base Google Flights: {len(voos_ida_serp)} opções encontradas"
                )
            with col_b2:
                total_duffel = len(voos_ida_duffel) + (
                    len(voos_volta_duffel) if tipo_viagem == "Ida e Volta" else 0
                )
                st.info(
                    f"ℹ️ Base Duffel (NDC Direct): {total_duffel} ofertas carregadas"
                    f" (Ida: {status_duffel_ida})"
                )

            st.write("")

            if not voos_ida_serp and not voos_ida_duffel:
                st.warning("Nenhum voo encontrado nas duas bases consultadas.")
            else:
                # --- BLOCO 1: GOOGLE FLIGHTS ---
                if voos_ida_serp:
                    st.markdown("## 🔍 Ofertas Encontradas no Google Flights")

                    if tipo_viagem == "Somente Ida":
                        for idx, flight_option in enumerate(voos_ida_serp[:5]):
                            flights_list = flight_option.get("flights", [])
                            if not flights_list:
                                continue

                            voo = flights_list[0]
                            cia = voo.get("airline", "Companhia Aérea")
                            num_voo = voo.get("flight_number", "")
                            hora_dep = (
                                voo.get("departure_airport", {}).get("time", "").split()[-1]
                            )
                            hora_arr = (
                                voo.get("arrival_airport", {}).get("time", "").split()[-1]
                            )
                            duracao_min = flight_option.get("total_duration", 0)
                            duracao_fmt = (
                                f"{duracao_min // 60}h {duracao_min % 60}m"
                                if duracao_min
                                else "N/A"
                            )
                            preco_reais = flight_option.get("price", 0)

                            tag_fonte = (
                                "🏆 MENOR TARIFA GOOGLE"
                                if idx == 0
                                else "✅ OPORTUNIDADE VALIDADA"
                            )

                            st.markdown(
                                f"### ✈️ {cia}"
                                f" <span style='background-color:#d4edda; color:#155724;"
                                f" padding:3px 8px; border-radius:5px;"
                                f" font-size:12px;'>{tag_fonte}</span>",
                                unsafe_allow_html=True,
                            )

                            c1, c2, c3 = st.columns([4, 4, 3])
                            with c1:
                                txt_voo_i = f" • Voo {num_voo}" if num_voo else ""
                                st.info(
                                    f"**🛫 IDA ({data_br_ida})**{txt_voo_i}\n\n"
                                    f"**{origem_iata}** ({hora_dep}) ➡️ **{destino_iata}**"
                                    f" ({hora_arr})\n\n"
                                    f"⏱️ Duração: {duracao_fmt}"
                                )

                            with c2:
                                st.warning(
                                    f"**TARIFA CONFIRMADA**\n\n"
                                    f"### R$ {preco_reais:,.2f}\n"
                                    f"Fonte: Google Flights"
                                )

                            with c3:
                                st.write("")
                                st.write("")
                                link_acao = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}%20on%20{data_iso_ida}"
                                st.link_button("Comprar Voo 🔗", link_acao, use_container_width=True)

                            st.divider()

                    else:
                        data_iso_volta = data_volta.strftime("%Y-%m-%d")
                        qtd_combinacoes = min(len(voos_ida_serp), len(voos_volta_serp), 5)

                        for i in range(qtd_combinacoes):
                            opt_ida = voos_ida_serp[i]
                            opt_volta = voos_volta_serp[i]

                            voo_ida = opt_ida["flights"][0]
                            voo_volta = opt_volta["flights"][0]

                            cia_ida = voo_ida.get("airline", "Companhia Aérea")
                            cia_volta = voo_volta.get("airline", "Companhia Aérea")

                            num_ida = voo_ida.get("flight_number", "")
                            num_volta = voo_volta.get("flight_number", "")

                            h_dep_ida = voo_ida.get("departure_airport", {}).get("time", "").split()[-1]
                            h_arr_ida = voo_ida.get("arrival_airport", {}).get("time", "").split()[-1]

                            h_dep_volta = voo_volta.get("departure_airport", {}).get("time", "").split()[-1]
                            h_arr_volta = voo_volta.get("arrival_airport", {}).get("time", "").split()[-1]

                            preco_total = opt_ida.get("price", 0) + opt_volta.get("price", 0)

                            st.markdown(
                                f"### ✈️ {cia_ida} / {cia_volta}",
                                unsafe_allow_html=True,
                            )

                            c1, c2, c3, c4 = st.columns([3, 3, 3, 2])
                            with c1:
                                txt_voo_i = f" • Voo {num_ida}" if num_ida else ""
                                st.info(
                                    f"**🛫 IDA ({data_br_ida})**{txt_voo_i}\n\n"
                                    f"**{origem_iata}** ({h_dep_ida}) ➡️ **{destino_iata}** ({h_arr_ida})"
                                )
                            with c2:
                                txt_voo_v = f" • Voo {num_volta}" if num_volta else ""
                                st.info(
                                    f"**🛬 VOLTA ({data_br_volta})**{txt_voo_v}\n\n"
                                    f"**{destino_iata}** ({h_dep_volta}) ➡️ **{origem_iata}** ({h_arr_volta})"
                                )
                            with c3:
                                st.warning(
                                    f"**TARIFA TOTAL COMBINADA**\n\n"
                                    f"### R$ {preco_total:,.2f}\n"
                                    f"Fonte: Google Flights"
                                )
                            with c4:
                                st.write("")
                                st.write("")
                                link_acao = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}%20on%20{data_iso_ida}%20through%20{data_iso_volta}"
                                st.link_button("Comprar Voo 🔗", link_acao, use_container_width=True)

                            st.divider()

                # --- BLOCO 2: DUFFEL (NDC DIRECT) - COMBINAÇÃO INDEPENDENTE ---
                if voos_ida_duffel:
                    st.write("")
                    st.markdown("## 🌐 Ofertas Exclusivas NDC Direct (Duffel)")
                    TAXA_EUR_BRL = 6.00

                    def extrair_dados_duffel(offer):
                        owner = offer.get("owner", {}).get("name", "Companhia Aérea")
                        raw_price = float(offer.get("total_amount", 0.0))
                        curr = offer.get("total_currency", "BRL")

                        if curr == "EUR":
                            p_brl = raw_price * TAXA_EUR_BRL
                        elif curr == "USD":
                            p_brl = raw_price * 5.50
                        else:
                            p_brl = raw_price

                        slice_data = offer.get("slices", [{}])[0]
                        seg = slice_data.get("segments", [{}])[0] if slice_data.get("segments") else {}

                        num = (
                            seg.get("operating_carrier_flight_number")
                            or seg.get("marketing_carrier_flight_number")
                            or ""
                        )
                        carrier = (
                            seg.get("marketing_carrier", {}).get("iata_code", "")
                            or seg.get("operating_carrier", {}).get("iata_code", "")
                        )
                        num_voo_txt = f"{carrier} {num}".strip()

                        dep_t = (
                            seg.get("departing_at", "").split("T")[-1][:5]
                            if "T" in seg.get("departing_at", "")
                            else ""
                        )
                        arr_t = (
                            seg.get("arriving_at", "").split("T")[-1][:5]
                            if "T" in seg.get("arriving_at", "")
                            else ""
                        )

                        return {
                            "owner": owner,
                            "price_brl": p_brl,
                            "num_voo": num_voo_txt,
                            "dep_time": dep_t,
                            "arr_time": arr_t,
                        }

                    if tipo_viagem == "Somente Ida":
                        for idx_d, offer in enumerate(voos_ida_duffel[:5]):
                            d_ida = extrair_dados_duffel(offer)
                            tag_duffel = "🏆 MELHOR OFERTA NDC" if idx_d == 0 else "✅ TARIFA NDC DIRECT"

                            st.markdown(
                                f"### ✈️ {d_ida['owner']}"
                                f" <span style='background-color:#cce5ff; color:#004085;"
                                f" padding:3px 8px; border-radius:5px;"
                                f" font-size:12px;'>{tag_duffel}</span>",
                                unsafe_allow_html=True,
                            )

                            c1, c2, c3 = st.columns([4, 4, 3])
                            with c1:
                                txt_num = f" • Voo {d_ida['num_voo']}" if d_ida['num_voo'] else ""
                                st.info(
                                    f"**🛫 IDA ({data_br_ida})**{txt_num}\n\n"
                                    f"**{origem_iata}** ({d_ida['dep_time']}) ➡️ **{destino_iata}** ({d_ida['arr_time']})"
                                )
                            with c2:
                                st.warning(
                                    f"**TARIFA NDC CONFIRMADA**\n\n"
                                    f"### R$ {d_ida['price_brl']:,.2f}\n"
                                    f"Fonte: Duffel Direct API"
                                )
                            with c3:
                                st.write("")
                                st.write("")
                                link_duffel = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}%20on%20{data_iso_ida}"
                                st.link_button("Comprar Voo 🔗", link_duffel, use_container_width=True)

                            st.divider()

                    else: # Ida e Volta Combinadas da Duffel
                        qtd_duffel = min(len(voos_ida_duffel), len(voos_volta_duffel), 5)

                        # Se não trouxe nada para a volta, usa só as idas
                        if qtd_duffel == 0:
                            qtd_duffel = min(len(voos_ida_duffel), 5)

                        for idx_d in range(qtd_duffel):
                            d_ida = extrair_dados_duffel(voos_ida_duffel[idx_d])
                            
                            has_volta = idx_d < len(voos_volta_duffel)
                            d_volta = extrair_dados_duffel(voos_volta_duffel[idx_d]) if has_volta else None

                            preco_total_duffel = d_ida['price_brl'] + (d_volta['price_brl'] if d_volta else 0.0)
                            header_cia = d_ida['owner'] if not d_volta or d_ida['owner'] == d_volta['owner'] else f"{d_ida['owner']} / {d_volta['owner']}"

                            tag_duffel = "🏆 MELHOR COMBINAÇÃO NDC" if idx_d == 0 else "✅ TARIFA NDC DIRECT"

                            st.markdown(
                                f"### ✈️ {header_cia}"
                                f" <span style='background-color:#cce5ff; color:#004085;"
                                f" padding:3px 8px; border-radius:5px;"
                                f" font-size:12px;'>{tag_duffel}</span>",
                                unsafe_allow_html=True,
                            )

                            c1, c2, c3, c4 = st.columns([3, 3, 3, 2])
                            with c1:
                                txt_num_i = f" • Voo {d_ida['num_voo']}" if d_ida['num_voo'] else ""
                                st.info(
                                    f"**🛫 IDA ({data_br_ida})**{txt_num_i}\n\n"
                                    f"**{origem_iata}** ({d_ida['dep_time']}) ➡️ **{destino_iata}** ({d_ida['arr_time']})"
                                )

                            with c2:
                                if d_volta:
                                    txt_num_v = f" • Voo {d_volta['num_voo']}" if d_volta['num_voo'] else ""
                                    st.info(
                                        f"**🛬 VOLTA ({data_br_volta})**{txt_num_v}\n\n"
                                        f"**{destino_iata}** ({d_volta['dep_time']}) ➡️ **{origem_iata}** ({d_volta['arr_time']})"
                                    )
                                else:
                                    st.info("**🛬 VOLTA**\n\nSem voos disponíveis para a volta.")

                            with c3:
                                st.warning(
                                    f"**TARIFA TOTAL NDC**\n\n"
                                    f"### R$ {preco_total_duffel:,.2f}\n"
                                    f"Fonte: Duffel Direct API"
                                )

                            with c4:
                                st.write("")
                                st.write("")
                                link_duffel = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}%20on%20{data_iso_ida}%20through%20{data_volta.strftime('%Y-%m-%d')}"
                                st.link_button("Comprar Voo 🔗", link_duffel, use_container_width=True)

                            st.divider()
