import datetime
from fast_flights import FlightData, Passengers, FlightType, Filter, Airport, get_flights
import streamlit as st

st.set_page_config(
    page_title="Caçador de Passagens", page_icon="✈️", layout="wide"
)

st.title("✈️ Caçador Particular de Passagens & Milhas")
st.caption(
    "Resultados extraídos em tempo real com direcionamento para emissão."
)

# Entrada de dados
col1, col2, col3, col4 = st.columns(4)

with col1:
  origem = st.text_input("🛫 Origem (IATA)", value="GRU").upper()

with col2:
  destino = st.text_input("🛬 Destino (IATA)", value="MIA").upper()

with col3:
  data_ida = st.date_input(
      "📅 Data de Ida", datetime.date.today() + datetime.timedelta(days=30)
  )

with col4:
  num_pax = st.number_input(
      "👤 Passageiros", min_value=1, max_value=9, value=1
  )

if st.button("🔎 Buscar Melhores Oportunidades Reais"):
  st.divider()
  st.subheader(
      f"📍 Voos Encontrados: {origem} ➡️ {destino} em"
      f" {data_ida.strftime('%d/%m/%Y')}"
  )

  data_str_iso = data_ida.strftime("%Y-%m-%d")

  # 1. BUSCA EM DINHEIRO (Tempo Real via Fast-Flights)
  with st.spinner("Buscando passagens em dinheiro no Google Flights..."):
    try:
      result = get_flights(
          flight_data=[
              FlightData(
                  date=data_str_iso,
                  from_airport=origem,
                  to_airport=destino,
              )
          ],
          trip=FlightType.ONE_WAY,
          passengers=Passengers(adults=num_pax),
          fetch_mode="fallback",
      )

      st.markdown("### 💵 Melhores Preços em Dinheiro")

      if result.flights:
        # Exibe os 5 voos mais baratos encontrados
        for voo in result.flights[:5]:
          col_v1, col_v2, col_v3 = st.columns([3, 2, 2])
          with col_v1:
            st.write(f"**Companhia / Voo:** {voo.name}")
            st.caption(f"Duração: {voo.duration}")
          with col_v2:
            st.write(f"**Preço:** {voo.price}")
          with col_v3:
            link_google = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino}%20from%20{origem}%20on%20{data_str_iso}"
            st.link_button("👉 Emitir este Voo", link_google)
          st.divider()
      else:
        st.warning("Nenhum voo direto em dinheiro retornado para esta data.")

    except Exception as e:
      st.error(f"Erro ao obter dados em tempo real: {e}")
      link_google = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino}%20from%20{origem}%20on%20{data_str_iso}"
      st.link_button("👉 Ver no Google Flights", link_google)

  # 2. OPÇÕES EM MILHAS
  st.markdown("### 🎫 Pesquisar Tabela de Milhas Direta")
  st.info(
      "Devido ao bloqueio de bots dos programas de fidelidade, clique abaixo"
      " para checar o assento em milhas:"
  )

  data_str_br = data_ida.strftime("%d/%m/%Y")
  timestamp_ms = int(
      datetime.datetime.combine(data_ida, datetime.time.min).timestamp() * 1000
  )

  link_smiles = f"https://www.smiles.com.br/membros/emissao-com-milhas?originAirport={origem}&destinationAirport={destino}&departureDate={timestamp_ms}&adults={num_pax}&tripType=1"
  link_latam = f"https://www.latamairlines.com/br/pt/ofertas-voos?origin={origem}&outbound={data_str_iso}T12%3A00%3A00.000Z&destination={destino}&adt={num_pax}&trip=ONE_WAY&redemption=true"
  link_azul = f"https://www.voezul.com.br/br/pt/home/selecao-voos?o1={origem}&d1={destino}&d1d={data_str_br}&p1={num_pax}&points=true"

  col_m1, col_m2, col_m3 = st.columns(3)
  with col_m1:
    st.link_button("🟠 Smiles (GOL)", link_smiles)
  with col_m2:
    st.link_button("🔴 LATAM Pass", link_latam)
  with col_m3:
    st.link_button("🔵 Azul Fidelidade", link_azul)
