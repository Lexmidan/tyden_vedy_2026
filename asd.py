import streamlit as st
import pandas as pd
import numpy as np
import logging
import time
import os
from datetime import datetime

MAX_BONUS_RATIO = 0.2
SHARED_DATA_FILE = 'shared_team_data.csv'
TEAM_SESSIONS_FILE = 'team_sessions.csv'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('team_submissions.log'),
        logging.StreamHandler()
    ]
)

# Function to load shared data
def load_shared_data():
    if os.path.exists(SHARED_DATA_FILE):
        try:
            return pd.read_csv(SHARED_DATA_FILE).to_dict('records')
        except Exception as e:
            logging.error(f"Error loading shared data: {e}")
            return []
    return []

# Function to save shared data
def save_shared_data(records):
    try:
        df = pd.DataFrame(records)
        df.to_csv(SHARED_DATA_FILE, index=False)
        logging.info(f"Saved {len(records)} records to shared file")
        return True
    except Exception as e:
        logging.error(f"Error saving shared data: {e}")
        return False

# Function to load team sessions
def load_team_sessions():
    if os.path.exists(TEAM_SESSIONS_FILE):
        try:
            return pd.read_csv(TEAM_SESSIONS_FILE).to_dict('records')
        except Exception as e:
            logging.error(f"Error loading team sessions: {e}")
            return []
    return []

# Function to save team sessions
def save_team_sessions(sessions):
    try:
        df = pd.DataFrame(sessions)
        df.to_csv(TEAM_SESSIONS_FILE, index=False)
        logging.info(f"Saved {len(sessions)} team sessions")
        return True
    except Exception as e:
        logging.error(f"Error saving team sessions: {e}")
        return False

# Function to start team session
def start_team_session(team_name):
    sessions = load_team_sessions()
    
    # Check if team already has an active session
    existing_session = next((s for s in sessions if s['team'] == team_name and s.get('completed', False) == False), None)
    if existing_session:
        return False, "Tým už má aktivní session!"
    
    new_session = {
        'team': team_name,
        'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'completed': False
    }
    
    sessions.append(new_session)
    if save_team_sessions(sessions):
        logging.info(f"Started session for team: {team_name}")
        return True, "Úloha zahájena!"
    return False, "Chyba při ukládání výsledku!"

# Function to get team session
def get_team_session(team_name):
    sessions = load_team_sessions()
    return next((s for s in sessions if s['team'] == team_name and s.get('completed', False) == False), None)

# Function to complete team session
def complete_team_session(team_name):
    sessions = load_team_sessions()
    for session in sessions:
        if session['team'] == team_name and session.get('completed', False) == False:
            session['completed'] = True
            session['end_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_team_sessions(sessions)
            return True
    return False

# Load shared records at startup
if 'records' not in st.session_state:
    st.session_state['records'] = load_shared_data()

INT = 5.98020787258
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

st.title("Integrace per Eidam")
st.write(
    "Sem zadáte výsledky. "
    "Skóre je založeno na hodnotě chyby a času. "
    "Bonus za odhad chyby může přidat až 20% k celkovému skóre."
)

# Timer controls
st.subheader("Začít úlohu")

# Form for starting timer
with st.form("start_timer_form"):
    st.write("**Krok 1:** Zadejte název týmu a spusťte stopky")
    team_name_start = st.text_input("Název týmu", key="team_start")
    start_button = st.form_submit_button("Spustit stopky")

if start_button and team_name_start:
    success, message = start_team_session(team_name_start)
    if success:
        st.success(f"✅ {message}")
    else:
        st.error(f"❌ {message}")

# Show active sessions
sessions = load_team_sessions()
active_sessions = [s for s in sessions if not s.get('completed', False)]
if active_sessions:
    st.subheader("Active sessions")
    for session in active_sessions:
        start_time = datetime.strptime(session['start_time'], "%Y-%m-%d %H:%M:%S")
        elapsed = (datetime.now() - start_time).total_seconds()
        st.info(f"🏃 **{session['team']}** - běží {elapsed/60:.1f} minut")

# Form for submission
st.markdown("---")
with st.form("team_input_form"):
    st.subheader("Odevzdat řešení")
    st.write("**Krok 2:** Zadejte název týmu a své řešení")
    
    name = st.text_input("Název týmu", key="team_submit")
    
    # Check if team has active session
    team_session = None
    session_valid = False
    if name:
        team_session = get_team_session(name)
        if team_session:
            session_valid = True
            start_time = datetime.strptime(team_session['start_time'], "%Y-%m-%d %H:%M:%S")
            elapsed = (datetime.now() - start_time).total_seconds()
            st.success(f"✅ Nalezena aktivní session (běží {elapsed/60:.1f} minut)")
        else:
            st.warning("⚠️ Pro tento tým nebyla nalezena aktivní session!")
    
    estimate = st.number_input("Odhad integrálu", format="%.4f", disabled=not session_valid)
    error_estimate = st.number_input("Odhad chyby (volitelné - pro bonus)", min_value=0.0, value=0.0, format="%.4f", disabled=not session_valid)
    
    save_solution_button = st.form_submit_button("Odevzdat řešení", disabled=not session_valid)

if save_solution_button:
    if not name:
        st.error("Zadejte název týmu.")
    elif not team_session:
        st.error("Pro tento tým nebyla nalezena aktivní session!")
    else:
        # Calculate time from stored session
        start_time = datetime.strptime(team_session['start_time'], "%Y-%m-%d %H:%M:%S")
        time_elapsed = (datetime.now() - start_time).total_seconds()
        
        error = abs(estimate - INT)
        
        record = {
            'team': name,
            'time': time_elapsed,
            'estimate': estimate,
            'error': error,
            'error_estimate': error_estimate,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Load current shared data to avoid conflicts
        current_records = load_shared_data()
        current_records.append(record)
        
        # Save to shared file and complete session
        if save_shared_data(current_records) and complete_team_session(name):
            st.session_state.records = current_records  # Update session state
            logging.info(f"New team submitted: {name}, Time: {time_elapsed}s, Estimate: {estimate}, Error: {error:.4f}")
            st.success(f"✅ Tým '{name}' úspěšně odevzdal řešení (čas: {time_elapsed/60:.1f} minut)")
        else:
            st.error("❌ Chyba při ukládání dat!")

# Organizer section - password protected
st.markdown("---")
st.subheader("Sekce pro organizátory")
password = st.text_input("Heslo pro organizátory", type="password")

if password == "qwazsazsus":
    # Refresh data from shared file in organizer section
    st.session_state['records'] = load_shared_data()
    
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
st.caption("Aplikace vytvořena pro Týden Vědy na Jaderce 2025")