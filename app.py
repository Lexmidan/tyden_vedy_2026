import streamlit as st
import pandas as pd
import numpy as np
import logging
from datetime import datetime

INT = 0.780207872582

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('team_submissions.log'),
        logging.StreamHandler()
    ]
)

# Initialize session state for storing team records
if 'records' not in st.session_state:
    st.session_state['records'] = []

# Initialize timer state
if 'timer_start' not in st.session_state:
    st.session_state['timer_start'] = None
if 'timer_running' not in st.session_state:
    st.session_state['timer_running'] = False
    
# Function to save dataframe
def save_dataframe():
    if st.session_state.records:
        df = pd.DataFrame(st.session_state.records)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"team_results_{timestamp}.csv"
        df.to_csv(filename, index=False)
        logging.info(f"Dataframe saved as {filename} with {len(df)} records")
        return filename
    return None

st.title("Fyziko-matematická soutěž: Integrace v kuchyni")
st.write(
    "Aplikace pro zadávání výsledků týmů v úloze integrace pomocí sýra. "
    "Skóre je založeno na normě vektoru (s_n, t_n), kde s_n a t_n jsou normalizované hodnoty chyby a času. "
    "Bonus za odhad chyby je založen na z-statistice: z = |I - Î|/error_estimate ~ N(0, 1)"
)

# Timer controls
st.subheader("Měření času")
col1, col2 = st.columns(2)

with col1:
    if st.button("Spustit stopky"):
        st.session_state['timer_start'] = datetime.now()
        st.session_state['timer_running'] = True
        st.success("Stopky spuštěny!")

with col2:
    if st.session_state['timer_running']:
        elapsed = (datetime.now() - st.session_state['timer_start']).total_seconds()
        st.metric("Uplynulý čas", f"{elapsed:.1f} s")
    else:
        st.metric("Uplynulý čas", "0.0 s")

# Display current timer status
if st.session_state['timer_running']:
    st.info("⏱️ Stopky běží...")
elif st.session_state['timer_start']:
    final_time = (datetime.now() - st.session_state['timer_start']).total_seconds()
    st.success(f"✅ Poslední měření: {final_time:.1f} s")

# Form pro zadání výsledků jednoho týmu
with st.form("team_input_form"):
    st.subheader("Přidat výsledky týmu")
    name = st.text_input("Název týmu")
    
    # Show auto-measured time if available
    if st.session_state['timer_start'] and not st.session_state['timer_running']:
        auto_time = (datetime.now() - st.session_state['timer_start']).total_seconds()
        time = st.number_input("Čas (s)", value=auto_time, min_value=0.0, step=0.1, format="%.2f")
    else:
        time = st.number_input("Čas (s)", min_value=0.0, step=0.1, format="%.2f")
    
    estimate = st.number_input("Odhad integrálu", format="%.4f")
    error_estimate = st.number_input("Odhad chyby (volitelné - pro bonus)", min_value=0.0, value=0.0, format="%.4f")
    
    col1, col2 = st.columns(2)
    with col1:
        add_button = st.form_submit_button("Přidat tým")
    with col2:
        save_solution_button = st.form_submit_button("Uložit řešení")
    
if add_button or save_solution_button:
    if not name:
        st.error("Zadejte prosím název týmu.")
    else:
        # Stop timer if it's running
        if st.session_state['timer_running']:
            st.session_state['timer_running'] = False
            final_time = (datetime.now() - st.session_state['timer_start']).total_seconds()
            time = final_time
        
        error = abs(estimate - INT)
        record = {
            'team': name,
            'time': time,
            'estimate': estimate,
            'error': error,
            'error_estimate': error_estimate
        }
        st.session_state.records.append(record)
        
        # Save dataframe after each submission
        saved_file = save_dataframe()
        if saved_file:
            logging.info(f"New team added: {name}, Time: {time}s, Estimate: {estimate}, Error: {error:.4f}")
            st.success(f"Tým '{name}' přidán a data uložena do {saved_file} (čas: {time:.1f}s)")
        else:
            st.success(f"Tým '{name}' přidán (čas: {time:.1f}s).")

# Zobrazení právě zadaných záznamů
if st.session_state.records:
    df = pd.DataFrame(st.session_state.records)
    st.subheader("Zadaná data")
    st.dataframe(df)
    if st.button("Vypočítat skóre a seřadit"):
        df['s_n'] = df['error'] / df['error'].std() if df['error'].std() > 0 else 0
        df['t_n'] = df['time'] / df['time'].std() if df['time'].std() > 0 else 0
        
        # Calculate main score as norm of (s_n, t_n)
        df['score'] = np.sqrt(df['s_n']**2 + df['t_n']**2)
        
        # Calculate z-statistic bonus for teams that provided error estimates
        df['z_statistic'] = 0.0
        df['error_bonus'] = 0.0
        
        for i, row in df.iterrows():
            if row['error_estimate'] > 0:
                z = abs(row['error']) / row['error_estimate']
                df.at[i, 'z_statistic'] = z
                
                #bonus on how close z is to expected N(0,1) distribution
                if z <= 3:  # Only give bonus for reasonable z-scores
                    df.at[i, 'error_bonus'] = max(0, 1 - z/3) * 0.5  # Max 0.5 bonus
        
        # Apply bonus by reducing the final score
        df['final_score'] = df['score'] - df['error_bonus']
        
        ranked = df.sort_values('final_score').reset_index(drop=True)
        ranked['rank'] = range(1, len(ranked) + 1)
        
        st.subheader("Konečné pořadí týmů")
        display_cols = ['rank', 'team', 'time', 'estimate', 'error', 'error_estimate', 
                       's_n', 't_n', 'score', 'z_statistic', 'error_bonus', 'final_score']
        st.dataframe(ranked[display_cols].round(4))
        
        # Stáhnout výsledky jako CSV
        csv = ranked.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Stáhnout výsledky (CSV)",
            data=csv,
            file_name='team_scores.csv',
            mime='text/csv'
        )
else:
    st.info("Zatím nebyly přidány žádné výsledky týmů.")

st.markdown("---")
st.caption("Aplikace vytvořena pro fyziko-matematickou soutěž integrační metodou se sýrem.")
