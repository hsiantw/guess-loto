kimport streamlit as st
import random
import json
import os
from crypto_paywall import crypto_paywall  # Make sure this file exists

# === Configurations ===
GUESSES_FILE = "guesses.json"
POT_FILE = "pot.json"
CONTRIBUTION_PER_GUESS = 0.0001  # ETH
NUMBER_RANGE_MIN = 1
NUMBER_RANGE_MAX = 100_000_000_000

# === Streamlit Page Setup ===
st.set_page_config(page_title="🎯 Guess Loto", layout="centered")

# === Utility Functions ===

def load_recent_guesses(limit=50):
    if os.path.exists(GUESSES_FILE):
        try:
            with open(GUESSES_FILE, "r") as f:
                data = json.load(f)
                return data[-limit:]
        except:
            return []
    return []

def log_guess_to_file(guess):
    data = []
    if os.path.exists(GUESSES_FILE):
        try:
            with open(GUESSES_FILE, "r") as f:
                data = json.load(f)
        except:
            data = []
    data.append(int(guess))
    with open(GUESSES_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_pot():
    if os.path.exists(POT_FILE):
        try:
            with open(POT_FILE, "r") as f:
                return json.load(f).get("pot_eth", 0.0)
        except:
            return 0.0
    return 0.0

def add_to_pot(amount):
    current = load_pot()
    new_total = round(current + amount, 10)
    with open(POT_FILE, "w") as f:
        json.dump({"pot_eth": new_total}, f, indent=2)
    return new_total

# === (Optional) Crypto Paywall ===
crypto_paywall()  # You can comment this out if testing locally

# === Game State Initialization ===
if "number_to_guess" not in st.session_state:
    st.session_state.number_to_guess = random.randint(NUMBER_RANGE_MIN, NUMBER_RANGE_MAX)
    st.session_state.attempts = 0
    st.session_state.guess_history = []
    st.session_state.game_over = False

# === Scrolling Ticker with Recent Guesses ===
recent_guesses = load_recent_guesses(50)
guesses_str = " | ".join(str(g) for g in recent_guesses)

st.markdown(f"""
<style>
.ticker-container {{
    position: relative;
    width: 100vw;
    left: calc(-50vw + 50%);
    background-color: #f5f5f5;
    color: #222;
    padding: 10px 0;
    font-size: 16px;
    font-weight: bold;
    border-bottom: 1px solid #ccc;
    white-space: nowrap;
    overflow: hidden;
    z-index: 9999;
}}
.ticker-text {{
    display: inline-block;
    padding-left: 100%;
    animation: ticker 30s linear infinite;
}}
@keyframes ticker {{
    0%   {{ transform: translateX(0%); }}
    100% {{ transform: translateX(-100%); }}
}}
</style>
<div class="ticker-container">
    <div class="ticker-text">
        🧠 Recent Guesses: {guesses_str} | {guesses_str}
    </div>
</div>
""", unsafe_allow_html=True)

# === Game Title & Pot ===
st.markdown("<h1 style='text-align: center;'>🎰 Guess Loto</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center;'>Guess a number between <b>{NUMBER_RANGE_MIN}</b> and <b>{NUMBER_RANGE_MAX:,}</b>.</p>", unsafe_allow_html=True)

# 💰 Show Pot
pot = load_pot()
st.markdown(f"""
<div style='text-align: center; font-size: 24px; margin: 10px 0 20px 0;'>
💰 <b>Current Pot:</b> {pot:.6f} ETH
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# === Game Logic ===
if not st.session_state.game_over:
    with st.form("guess_form", clear_on_submit=True):
        guess = st.text_input("🔢 Enter your guess (numbers only):", value="", key="current_guess_input")
        submit = st.form_submit_button("🚀 Submit Guess")

    if submit:
        try:
            guess_int = int(guess.strip())
            if NUMBER_RANGE_MIN <= guess_int <= NUMBER_RANGE_MAX:
                st.session_state.attempts += 1
                st.session_state.guess_history.append(guess_int)
                log_guess_to_file(guess_int)
                pot = add_to_pot(CONTRIBUTION_PER_GUESS)

                if guess_int == st.session_state.number_to_guess:
                    st.success(f"🎉 Correct! You guessed it in {st.session_state.attempts} attempts.")
                    st.session_state.game_over = True
                else:
                    st.warning("❌ Incorrect. Try again!")
                st.rerun()
            else:
                st.error(f"⚠️ Guess must be between {NUMBER_RANGE_MIN} and {NUMBER_RANGE_MAX:,}")
        except:
            st.error("❗ Please enter a valid number.")

    if st.session_state.guess_history:
        st.markdown("### 🧾 Your Guesses:")
        st.markdown(" ".join([f"<code>{g}</code>" for g in st.session_state.guess_history]), unsafe_allow_html=True)

else:
    st.success(f"🎯 You guessed it in {st.session_state.attempts} attempts!")
    st.markdown("### 💾 Your Guess History:")
    st.code(", ".join(str(g) for g in st.session_state.guess_history))

    if st.button("🔄 Play Again"):
        st.session_state.number_to_guess = random.randint(NUMBER_RANGE_MIN, NUMBER_RANGE_MAX)
        st.session_state.attempts = 0
        st.session_state.guess_history = []
        st.session_state.game_over = False
        st.rerun()

# === Footer Description ===
st.markdown("---")
st.markdown(f"""
<p style="text-align: center; font-size: 14px;">
🎮 Welcome to <strong>Guess Loto</strong> — guess between <b>{NUMBER_RANGE_MIN}</b> and <b>{NUMBER_RANGE_MAX:,}</b>.<br>
Each guess contributes to the pot. Winner takes <b>88%</b>; the rest rolls over to the next round.<br>
Have fun and good luck! 🍀
</p>
""", unsafe_allow_html=True)
