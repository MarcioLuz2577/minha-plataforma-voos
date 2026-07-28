import datetime
from serpapi import GoogleSearch
import streamlit as st

# Configuração da Página
st.set_page_config(
    page_title="Caçador de Passagens",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ Caçador Particular de Passagens & Milhas")
st.caption("Resultados 100% reais consultados em tempo real via SerpApi.")

# Configuração da Chave de API
with st.sidebar:
  st.header("🔑 Configuração")
  api_key = st.text_input(
      "Sua SerpApi Key:", type="password", help="Insira sua chave da SerpApi"
  )

# Formulário Principal
col1, col2, col3, col4 = st.columns(4)

with col1:
  origem = st.text_input("🛫 Origem (IATA)", value="GRU").upper().strip()

with col2:
  destino = st.text_input("🛬 Destino (IATA)", value="CNF").upper().strip()

with col3:
  data_ida = st.date_input(
      "📅 Data de Ida", datetime.date.today() + datetime.timedelta(days=7)
  )

with col4:
  num_pax = st.number_input(
      "👤 Passageiros", min_value=1, max_value=9, value=1
  )

if st.button("🔎 Buscar Oportunidades Reais", use_container_width=True):
  if not api_key:
    st.error(
        "⚠️ Por favor, informe sua chave da SerpApi no menu lateral esquerdo."
    )
  else:
    st.divider()
    data_iso = data_ida.strftime("%Y-%m-%d")
    data_br = data_ida.strftime("%d/%m/%Y")
    timestamp_ms = int(
        datetime.datetime.combine(data_ida, datetime.time.min).timestamp()
        * 1000
    )

    st.subheader(
        f"📍 Voos Reais Encontrados de {origem} para {destino} ({data_br})"
    )

    with st.spinner("Consultando ofertas reais em tempo real..."):
      params = {
          "engine": "google_flights",
          "departure_id": origem,
          "arrival_id": destino,
          "outbound_date": data_iso,
          "currency": "BRL",
          "hl": "pt-br",
          "adults": num_pax,
          "api_key": api_key,
      }

      try:
        search = GoogleSearch(params)
        results = search.get_dict()
        best_flights = results.get("best_flights", []) + results.get(
            "other_flights", []
        )

        if not best_flights:
          st.warning(
              "Nenhum voo encontrado para esta rota/data nas buscas reais."
          )
        else:
          # Exibe até os 5 melhores voos REAIS
          for flight_option in best_flights[:5]:
            flight = flight_option["flights"][0]

            cia = flight.get("airline", "Companhia Aérea")
            num_voo = flight.get("flight_number", "")
            dep_time = flight.get("departure_token", "").split(" ")
            hora_dep = (
                flight.get("departure_airport", {}).get("time", "").split()[-1]
            )
            hora_arr = (
                flight.get("arrival_airport", {}).get("time", "").split()[-1]
            )
            duracao_min = flight_option.get("total_duration", 0)
            duracao_fmt = f"{duracao_min // 60}h {duracao_min % 60}m"
            preco_reais = flight_option.get("price", 0)

            # Cálculo de milhas com base na cotação média de R$ 20 / 1.000 milhas
            milhas_est = (
                f"{int((preco_reais / 20) * 1000):,} milhas".replace(",", ".")
                if preco_reais
                else "Consulte"
            )

            # Links diretos de resgate oficial
            if "GOL" in cia.upper():
              link_resgate = f"https://www.smiles.com.br/membros/emissao-com-milhas?originAirport={origem}&destinationAirport={destino}&departureDate={timestamp_ms}&adults={num_pax}&tripType=1"
            elif "LATAM" in cia.upper():
              link_resgate = f"https://www.latamairlines.com/br/pt/ofertas-voos?origin={origem}&outbound={data_iso}T12%3A00%3A00.000Z&destination={destino}&adt={num_pax}&trip=ONE_WAY&redemption=true"
            else:
              link_resgate = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino}%20from%20{origem}%20on%20{data_iso}"

            # Renderização do Card no Estilo Flypass com Dados Reais
            st.markdown(
                f"### ✈️ {cia} <small style='color:gray;'>• Voo"
                f" {num_voo}</small>",
                unsafe_allow_html=True,
            )

            c1, c2, c3, c4 = st.columns([3, 3, 3, 2])

            with c1:
              st.info(
                  f"**IDA (Direto)**\n\n"
                  f"**{origem}** ({hora_dep}) ➡️ **{destino}** ({hora_arr})\n\n"
                  f"⏱️ Duração: {duracao_fmt}"
              )

            with c2:
              st.success(
                  f"**ESTIMATIVA EM MILHAS**\n\n"
                  f"### {milhas_est}\n"
                  f"+ Taxas de embarque oficiais"
              )

            with c3:
              st.warning(
                  f"**PAGANDO EM DINHEIRO**\n\n"
                  f"### R$ {preco_reais:,.2f}\n"
                  f"Tarifa pagante real (Google Flights)"
              )

            with c4:
              st.write("")
              st.write("")
              st.link_button(
                  "Resgatar Voo 🔗", link_resgate, use_container_width=True
              )

            st.divider()

      except Exception as e:
        st.error(f"Erro ao buscar voos reais: {e}")
