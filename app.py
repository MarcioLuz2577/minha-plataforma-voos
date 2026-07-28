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


# --- BUSCA 2: DUFFEL API (REST HTTP) ---
def buscar_duffel(dep_iata, arr_iata, data_ida_obj, data_volta_obj=None):
    if not DUFFEL_TOKEN:
        return [], "Chave DUFFEL_TOKEN não configurada."
    try:
        url = "https://api.duffel.com/air/offer_requests?return_offers=true"
        headers = {
            "Authorization": f"Bearer {DUFFEL_TOKEN}",
            "Duffel-Version": "v2",
            "Content-Type": "application/json",
        }

        slices_list = [{
            "origin": dep_iata,
            "destination": arr_iata,
            "departure_date": data_ida_obj.strftime("%Y-%m-%d"),
        }]

        if data_volta_obj and tipo_viagem == "Ida e Volta":
            slices_list.append({
                "origin": arr_iata,
                "destination": dep_iata,
                "departure_date": data_volta_obj.strftime("%Y-%m-%d"),
            })

        payload = {
            "data": {
                "slices": slices_list,
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
            msg = (
                "OK"
                if offers
                else "Sem voos retornados (Sandbox de teste restringe rotas BR)."
            )
            return offers, msg
        else:
            err_msg = data.get("errors", [{}])[0].get("message", "Erro desconhecido")
            return [], f"Detalhe Duffel: {err_msg}"
    except requests.exceptions.Timeout:
        return [], "Detalhe Duffel: Tempo limite de resposta excedido (Timeout)."
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

        with st.spinner("Consultando Google Flights e Duffel API simultaneamente..."):
            voos_ida_serp = buscar_serpapi(origem_iata, destino_iata, data_ida)
            voos_volta_serp = (
                buscar_serpapi(destino_iata, origem_iata, data_volta)
                if (tipo_viagem == "Ida e Volta" and data_volta)
                else []
            )

            voos_duffel, status_duffel = buscar_duffel(
                origem_iata, destino_iata, data_ida, data_volta
            )

            col_b1, col_b2 = st.columns(2)
            with col_b1:
                st.success(
                    f"✅ Base Google Flights: {len(voos_ida_serp)} opções encontradas"
                )
            with col_b2:
                st.info(
                    f"ℹ️ Base Duffel (NDC Direct): {len(voos_duffel)} opções encontradas"
                    f" ({status_duffel})"
                )

            st.write("")

            if not voos_ida_serp and not voos_duffel:
                st.warning("Nenhum voo encontrado nas duas bases consultadas.")
            else:
                # --- BLOCO 1: EXIBIÇÃO RESULTADOS GOOGLE FLIGHTS (SERPAPI) ---
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
                                f"### ✈️ {cia} <small style='color:gray;'>• Voo {num_voo}</small>"
                                f" <span style='background-color:#d4edda; color:#155724;"
                                f" padding:3px 8px; border-radius:5px;"
                                f" font-size:12px;'>{tag_fonte}</span>",
                                unsafe_allow_html=True,
                            )

                            c1, c2, c3 = st.columns([4, 4, 3])
                            with c1:
                                st.info(
                                    f"**🛫 IDA ({data_br_ida})**\n\n"
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
                                if modalidade_busca == "Milhas":
                                    btn_texto = "Resgatar em Milhas 🔗"
                                    if "GOL" in cia.upper():
                                        link_acao = f"https://www.smiles.com.br/membros/emissao-com-milhas?originAirport={origem_iata}&destinationAirport={destino_iata}&departureDate={timestamp_ms_ida}&adults={num_pax}&tripType=1"
                                    elif "LATAM" in cia.upper():
                                        link_acao = f"https://www.latamairlines.com/br/pt/ofertas-voos?origin={origem_iata}&outbound={data_iso_ida}T12%3A00%3A00.000Z&destination={destino_iata}&adt={num_pax}&trip=ONE_WAY&redemption=true"
                                    else:
                                        link_acao = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}%20on%20{data_iso_ida}"
                                else:
                                    btn_texto = "Comprar Voo 🔗"
                                    link_acao = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}%20on%20{data_iso_ida}"

                                st.link_button(btn_texto, link_acao, use_container_width=True)

                            st.divider()

                    else:
                        data_iso_volta = data_volta.strftime("%Y-%m-%d")
                        timestamp_ms_volta = int(
                            datetime.datetime.combine(
                                data_volta, datetime.time.min
                            ).timestamp()
                            * 1000
                        )

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

                            h_dep_ida = (
                                voo_ida.get("departure_airport", {}).get("time", "").split()[-1]
                            )
                            h_arr_ida = (
                                voo_ida.get("arrival_airport", {}).get("time", "").split()[-1]
                            )

                            h_dep_volta = (
                                voo_volta.get("departure_airport", {})
                                .get("time", "")
                                .split()[-1]
                            )
                            h_arr_volta = (
                                voo_volta.get("arrival_airport", {})
                                .get("time", "")
                                .split()[-1]
                            )

                            dur_ida = (
                                f"{opt_ida.get('total_duration', 0) // 60}h"
                                f" {opt_ida.get('total_duration', 0) % 60}m"
                            )
                            dur_volta = (
                                f"{opt_volta.get('total_duration', 0) // 60}h"
                                f" {opt_volta.get('total_duration', 0) % 60}m"
                            )

                            preco_total = opt_ida.get("price", 0) + opt_volta.get("price", 0)

                            tag_comb = (
                                "🏆 MELHOR PARTIDA COMBINADA"
                                if i == 0
                                else "✅ COMBINAÇÃO RECOMENDADA"
                            )

                            st.markdown(
                                f"### ✈️ Opção #{i+1}: {cia_ida} / {cia_volta} <span"
                                " style='background-color:#d4edda; color:#155724;"
                                " padding:3px 8px; border-radius:5px;"
                                f" font-size:12px;'>{tag_comb}</span>",
                                unsafe_allow_html=True,
                            )

                            c1, c2, c3, c4 = st.columns([3, 3, 3, 2])

                            with c1:
                                st.info(
                                    f"**🛫 IDA ({data_br_ida})** • Voo {num_ida}\n\n"
                                    f"**{origem_iata}** ({h_dep_ida}) ➡️ **{destino_iata}**"
                                    f" ({h_arr_ida})\n\n"
                                    f"⏱️ Duração: {dur_ida}"
                                )

                            with c2:
                                st.info(
                                    f"**🛬 VOLTA ({data_br_volta})** • Voo {num_volta}\n\n"
                                    f"**{destino_iata}** ({h_dep_volta}) ➡️ **{origem_iata}**"
                                    f" ({h_arr_volta})\n\n"
                                    f"⏱️ Duração: {dur_volta}"
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
                                if modalidade_busca == "Milhas":
                                    btn_texto = "Resgatar em Milhas 🔗"
                                    if "GOL" in cia_ida.upper():
                                        link_acao = f"https://www.smiles.com.br/membros/emissao-com-milhas?originAirport={origem_iata}&destinationAirport={destino_iata}&departureDate={timestamp_ms_ida}&returnDate={timestamp_ms_volta}&adults={num_pax}&tripType=2"
                                    elif "LATAM" in cia_ida.upper():
                                        link_acao = f"https://www.latamairlines.com/br/pt/ofertas-voos?origin={origem_iata}&outbound={data_iso_ida}T12%3A00%3A00.000Z&destination={destino_iata}&inbound={data_iso_volta}T12%3A00%3A00.000Z&adt={num_pax}&trip=ROUND_TRIP&redemption=true"
                                    else:
                                        link_acao = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}%20on%20{data_iso_ida}%20through%20{data_iso_volta}"
                                else:
                                    btn_texto = "Comprar Voo 🔗"
                                    link_acao = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}%20on%20{data_iso_ida}%20through%20{data_iso_volta}"

                                st.link_button(btn_texto, link_acao, use_container_width=True)

                            st.divider()

                # --- BLOCO 2: EXIBIÇÃO RESULTADOS DUFFEL (NDC DIRECT) ---
                if voos_duffel:
                    st.write("")
                    st.markdown("## 🌐 Ofertas Exclusivas NDC Direct (Duffel)")

                    TAXA_EUR_BRL = 6.00

                    for idx_d, offer in enumerate(voos_duffel[:5]):
                        total_raw = float(offer.get("total_amount", 0.0))
                        currency = offer.get("total_currency", "BRL")

                        if currency == "EUR":
                            total_brl = total_raw * TAXA_EUR_BRL
                        elif currency == "USD":
                            total_brl = total_raw * 5.50
                        else:
                            total_brl = total_raw

                        owner_name = offer.get("owner", {}).get("name", "Companhia Aérea")
                        slices = offer.get("slices", [])

                        tag_duffel = (
                            "🏆 MELHOR OFERTA NDC" if idx_d == 0 else "✅ TARIFA NDC DIRECT"
                        )

                        # Extração correta dos números dos voos da Duffel
                        num_voo_ida_txt = ""
                        num_voo_volta_txt = ""

                        if slices:
                            # Número voo Ida
                            seg_i = slices[0].get("segments", [{}])[0]
                            num_i = (
                                seg_i.get("operating_carrier_flight_number")
                                or seg_i.get("marketing_carrier_flight_number")
                                or ""
                            )
                            carrier_i = seg_i.get("marketing_carrier", {}).get(
                                "iata_code", ""
                            )
                            num_voo_ida_txt = (
                                f"{carrier_i} {num_i}".strip() if (carrier_i or num_i) else ""
                            )

                            # Número voo Volta (se houver)
                            if len(slices) >= 2:
                                seg_v = slices[1].get("segments", [{}])[0]
                                num_v = (
                                    seg_v.get("operating_carrier_flight_number")
                                    or seg_v.get("marketing_carrier_flight_number")
                                    or ""
                                )
                                carrier_v = seg_v.get("marketing_carrier", {}).get(
                                    "iata_code", ""
                                )
                                num_voo_volta_txt = (
                                    f"{carrier_v} {num_v}".strip() if (carrier_v or num_v) else ""
                                )

                        # Cabeçalho da opção com o número do voo
                        num_voo_header = (
                            f"• Voo {num_voo_ida_txt}" if num_voo_ida_txt else ""
                        )

                        st.markdown(
                            f"### ✈️ {owner_name} <small style='color:gray;'>{num_voo_header}</small>"
                            f" <span style='background-color:#cce5ff; color:#004085;"
                            f" padding:3px 8px; border-radius:5px;"
                            f" font-size:12px;'>{tag_duffel}</span>",
                            unsafe_allow_html=True,
                        )

                        if len(slices) >= 2 and tipo_viagem == "Ida e Volta":
                            c1, c2, c3, c4 = st.columns([3, 3, 3, 2])

                            # Slice 1 - Ida
                            s_ida = slices[0]
                            seg_ida = s_ida.get("segments", [{}])[0]
                            dep_time_i = (
                                seg_ida.get("departing_at", "").split("T")[-1][:5]
                                if "T" in seg_ida.get("departing_at", "")
                                else ""
                            )
                            arr_time_i = (
                                seg_ida.get("arriving_at", "").split("T")[-1][:5]
                                if "T" in seg_ida.get("arriving_at", "")
                                else ""
                            )

                            # Slice 2 - Volta
                            s_volta = slices[1]
                            seg_volta = s_volta.get("segments", [{}])[0]
                            dep_time_v = (
                                seg_volta.get("departing_at", "").split("T")[-1][:5]
                                if "T" in seg_volta.get("departing_at", "")
                                else ""
                            )
                            arr_time_v = (
                                seg_volta.get("arriving_at", "").split("T")[-1][:5]
                                if "T" in seg_volta.get("arriving_at", "")
                                else ""
                            )

                            voo_ida_lbl = (
                                f" • Voo {num_voo_ida_txt}" if num_voo_ida_txt else ""
                            )
                            voo_volta_lbl = (
                                f" • Voo {num_voo_volta_txt}" if num_voo_volta_txt else ""
                            )

                            with c1:
                                st.info(
                                    f"**🛫 IDA ({data_br_ida})**{voo_ida_lbl}\n\n"
                                    f"**{origem_iata}** ({dep_time_i}) ➡️ **{destino_iata}**"
                                    f" ({arr_time_i})"
                                )

                            with c2:
                                st.info(
                                    f"**🛬 VOLTA ({data_br_volta})**{voo_volta_lbl}\n\n"
                                    f"**{destino_iata}** ({dep_time_v}) ➡️ **{origem_iata}**"
                                    f" ({arr_time_v})"
                                )

                            with c3:
                                st.warning(
                                    f"**TARIFA TOTAL NDC**\n\n"
                                    f"### R$ {total_brl:,.2f}\n"
                                    f"Fonte: Duffel Direct API"
                                )

                            with c4:
                                st.write("")
                                st.write("")
                                link_duffel = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}%20on%20{data_iso_ida}%20through%20{data_iso_volta}"
                                st.link_button(
                                    "Comprar Voo 🔗", link_duffel, use_container_width=True
                                )

                        else:
                            s_ida = slices[0] if slices else {}
                            seg_ida = (
                                s_ida.get("segments", [{}])[0]
                                if s_ida.get("segments")
                                else {}
                            )
                            dep_time_i = (
                                seg_ida.get("departing_at", "").split("T")[-1][:5]
                                if "T" in seg_ida.get("departing_at", "")
                                else ""
                            )
                            arr_time_i = (
                                seg_ida.get("arriving_at", "").split("T")[-1][:5]
                                if "T" in seg_ida.get("arriving_at", "")
                                else ""
                            )

                            voo_ida_lbl = (
                                f" • Voo {num_voo_ida_txt}" if num_voo_ida_txt else ""
                            )

                            c1, c2, c3 = st.columns([4, 4, 3])
                            with c1:
                                st.info(
                                    f"**🛫 IDA ({data_br_ida})**{voo_ida_lbl}\n\n"
                                    f"**{origem_iata}** ({dep_time_i}) ➡️ **{destino_iata}**"
                                    f" ({arr_time_i})"
                                )

                            with c2:
                                st.warning(
                                    f"**TARIFA NDC CONFIRMADA**\n\n"
                                    f"### R$ {total_brl:,.2f}\n"
                                    f"Fonte: Duffel Direct API"
                                )

                            with c3:
                                st.write("")
                                st.write("")
                                link_duffel = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}%20on%20{data_iso_ida}"
                                st.link_button(
                                    "Comprar Voo 🔗", link_duffel, use_container_width=True
                                )

                        st.divider()
