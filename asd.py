import streamlit as st
import pandas as pd
import numpy as np
import logging
import time
from datetime import datetime

MAX_BONUS_RATIO = 0.2

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

INT = 0.780207872582
# Initialize timer state
if 'timer_start' not in st.session_state:
    st.session_state['timer_start'] = None
if 'timer_running' not in st.session_state:
    st.session_state['timer_running'] = False
if 'submission_time' not in st.session_state:
    st.session_state['submission_time'] = None
    
# Function to save dataframe
def save_dataframe():
    if st.session_state.records:
        df = pd.DataFrame(st.session_state.records)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"team_results_{timestamp}.csv"
        
        # Save to session state for download instead of file system
        st.session_state['latest_csv'] = df.to_csv(index=False)
        st.session_state['latest_filename'] = filename
        
        logging.info(f"Dataframe prepared for download with {len(df)} records")
        return filename
    return None

st.title("Integrování sýrovou metodou.")
st.write(
    "Aplikace pro zadávání výsledků týmů v úloze integrace pomocí sýra. "
    "Skóre je založeno na normě vektoru (E, T), kde E a T jsou normalizované hodnoty chyby a času. "
    "Bonus za odhad chyby je založen na z-statistice:"
)
st.latex(r"z = \frac{|I - \hat{I}|}{\text{error\_estimate}} \sim N(0, 1)")

# Timer controls
st.subheader("Začít úlohu")
col1, col2 = st.columns(2)

with col1:
    if st.button("Spustit stopky"):
        st.session_state['timer_start'] = datetime.now()
        st.session_state['timer_running'] = True

with col2:
    if st.session_state['timer_running']:
        elapsed = (datetime.now() - st.session_state['timer_start']).total_seconds()
        st.metric("Uplynulý čas", f"{elapsed:.1f} s")
    else:
        st.metric("Tady se zobrazí uplynulý čas", "0.0 s")

# Display current timer status
if st.session_state['timer_running']:
    st.info("⏱️ Stopky běží...")
elif st.session_state['timer_start']:
    final_time = (datetime.now() - st.session_state['timer_start']).total_seconds()
    st.success(f"✅ Poslední měření: {final_time:.1f} s")

# Form pro zadání výsledků jednoho týmu
with st.form("team_input_form"):
    st.subheader("Přidat výsledky týmu")
    
    # Check if timer has been started
    timer_started = st.session_state['timer_start'] is not None
    
    if not timer_started:
        st.warning("⚠️ Nejdříve spusťte stopky před zadáváním výsledků!")
    
    name = st.text_input("Název týmu", disabled=not timer_started)
    
    estimate = st.number_input("Odhad integrálu", format="%.4f", disabled=not timer_started)
    error_estimate = st.number_input("Odhad chyby (volitelné - pro bonus)", min_value=0.0, value=0.0, format="%.4f", disabled=not timer_started)
    
    save_solution_button = st.form_submit_button("Uložit řešení", disabled=not timer_started)
    
if save_solution_button:
    if not name:
        st.error("Zadejte název týmu.")
    else:
        # Stop timer if it's running and get the time
        if st.session_state['timer_running']:
            st.session_state['timer_running'] = False
            time = (datetime.now() - st.session_state['timer_start']).total_seconds()
        elif st.session_state['timer_start']:
            time = (datetime.now() - st.session_state['timer_start']).total_seconds()
        else:
            st.error("Spusťte prosím nejdřív stopky.")
            st.stop()

        error = abs(estimate - INT)
        record = {
            'team': name,
            'time': time,
            'estimate': estimate,
            'error': error,
            'error_estimate': error_estimate,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        st.session_state.records.append(record)
          # Save dataframe after each submission
        saved_file = save_dataframe()
        if saved_file:
            logging.info(f"New team added: {name}, Time: {time}s, Estimate: {estimate}, Error: {error:.4f}")
            st.success(f"Tým '{name}' přidán a data uložena do {saved_file} (čas: {time:.1f}s)")
        else:
            st.success(f"Tým '{name}' přidán (čas: {time:.1f}s).")
        
        # Set submission time for delayed clearing
        st.session_state['submission_time'] = datetime.now()
        
        # Reset timer for next team
        st.session_state['timer_start'] = None

# Check if 20 seconds have passed since submission to clear the form
if (st.session_state['submission_time'] and 
    (datetime.now() - st.session_state['submission_time']).total_seconds() >= 20):
    st.session_state['submission_time'] = None
    st.rerun()

# Organizer section - password protected
st.markdown("---")
st.subheader("Sekce pro organizátory")
password = st.text_input("Heslo pro organizátory", type="password")

if password == "qwazsazsus":
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

                    if z <= 3:
                        bonus = max(0, 1 - z/3) * MAX_BONUS_RATIO * row['score']
                        df.at[i, 'error_bonus'] = bonus
            
            # Apply bonus by reducing the final score
            df['final_score'] = df['score'] - df['error_bonus']
            
            ranked = df.sort_values('final_score').reset_index(drop=True)
            ranked['rank'] = range(1, len(ranked) + 1)
            
            st.subheader("Konečné pořadí týmů")
            display_cols = ['rank', 'team', 'time', 'estimate', 'error', 'error_estimate', 
                           'timestamp', 's_n', 't_n', 'score', 'z_statistic', 'error_bonus', 'final_score']
            st.dataframe(ranked[display_cols].round(4))
            
            # Stáhnout výsledky jako CSV
            csv = ranked.to_csv(index=False).encode('utf-8')
            if 'latest_csv' in st.session_state:
                st.download_button(
                    label="Stáhnout aktuální data (CSV)",
                    data=st.session_state['latest_csv'],
                    file_name=st.session_state.get('latest_filename', 'team_data.csv'),
                    mime='text/csv'
                )
    else:
        st.info("Zatím nebyly přidány žádné výsledky týmů.")
elif password:
    st.error("Nesprávné heslo!")

st.markdown("---")
st.caption("Aplikace vytvořena pro fyziko-matematickou soutěž integrační metodou se sýrem.")