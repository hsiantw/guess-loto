# secure_crypto_paywall.py

import streamlit as st
import requests
import qrcode
from io import BytesIO
from decimal import Decimal
from cryptography.fernet import Fernet
import json
import os
import time
from dotenv import load_dotenv
from cryptography.fernet import Fernet

fernet = Fernet(os.getenv("SECRET_KEY").encode())
# === Load environment variables ===
load_dotenv()

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
SECRET_KEY = os.getenv("SECRET_KEY")

MIN_AMOUNT_ETH = 0.0001
NUMBER_RANGE_MIN = 1
NUMBER_RANGE_MAX = 100_000_000_000
WINNERS_FILE = "winners.json"
UPDATE_INTERVAL = 60  # seconds
fernet = Fernet(SECRET_KEY.encode())

# === Load/Store Previous Winners and Rollovers (Encrypted) ===
def save_winner_data_encrypted(winners):
    json_data = json.dumps(winners).encode()
    encrypted_data = fernet.encrypt(json_data)
    with open("winners.json", "wb") as f:
        f.write(encrypted_data)

def load_winner_data_encrypted():
    if not os.path.exists("winners.json"):
        return []
    with open("winners.json", "rb") as f:
        encrypted_data = f.read()
    try:
        decrypted_data = fernet.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode())
    except:
        return []

# === QR Code Generation ===
def generate_wallet_qr(wallet_address: str):
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(wallet_address)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

# === Fetch and Sum Payments from Specific Sender ===
def has_paid(user_wallet_address: str) -> bool:
    url = "https://api.etherscan.io/api"
    params = {
        "module": "account",
        "action": "txlist",
        "address": WALLET_ADDRESS,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "desc",
        "apikey": ETHERSCAN_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data["status"] != "1":
            return False

        for tx in data["result"]:
            if (tx["to"].lower() == WALLET_ADDRESS.lower() and
                tx["from"].lower() == user_wallet_address.lower() and
                float(tx["value"]) / 10**18 >= MIN_AMOUNT_ETH):
                return True
        return False

    except Exception as e:
        st.warning(f"⚠️ Payment check failed: {e}")
        return False

# === Calculate Total Pot ===
def get_total_eth_received(min_eth: float = MIN_AMOUNT_ETH) -> Decimal:
    url = "https://api.etherscan.io/api"
    params = {
        "module": "account",
        "action": "txlist",
        "address": WALLET_ADDRESS,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "desc",
        "apikey": ETHERSCAN_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data["status"] != "1":
            return Decimal("0.0")

        total_eth = Decimal("0.0")
        seen_tx_hashes = set()

        for tx in data["result"]:
            if tx["to"].lower() == WALLET_ADDRESS.lower():
                tx_hash = tx["hash"]
                if tx_hash not in seen_tx_hashes:
                    eth_value = Decimal(tx["value"]) / Decimal(10**18)
                    if eth_value >= Decimal(str(min_eth)):
                        total_eth += eth_value
                        seen_tx_hashes.add(tx_hash)

        return total_eth

    except Exception as e:
        st.warning(f"⚠️ Unable to fetch pot size: {e}")
        return Decimal("0.0")

# === Main Paywall Entry ===
def crypto_paywall():
    st.title("🎰 Guess Loto")

    if "paid" not in st.session_state:
        st.session_state.paid = False

    if not st.session_state.paid:
        st.markdown("### 🔒 Access Locked")
        st.info(f"To play, please send **{MIN_AMOUNT_ETH} ETH** to the wallet below:")
        st.code(WALLET_ADDRESS)

        qr_image = generate_wallet_qr(WALLET_ADDRESS)
        st.image(qr_image, caption="ETH Wallet QR Code", width=200)

        user_wallet = st.text_input("Enter your wallet address to verify payment")

        if user_wallet:
            if st.button("🔍 Check My Payment"):
                if has_paid(user_wallet):
                    st.success("✅ Payment confirmed! You can now play.")
                    st.session_state.paid = True
                    st.rerun()
                else:
                    st.error("❌ Payment not found for this address.")

        st.markdown("### 💰 Pot Size")
        if "last_check_time" not in st.session_state:
            st.session_state.last_check_time = 0
        now = time.time()
        if now - st.session_state.last_check_time > UPDATE_INTERVAL:
            st.session_state.total_eth = get_total_eth_received()
            st.session_state.last_check_time = now

        pot = st.session_state.get("total_eth", Decimal("0.0"))
        st.info(f"Current Pot: **{pot:.6f} ETH**")

        st.markdown("---")
        st.markdown(
            f"""
            <div style='font-size:16px; text-align:center; padding-top:20px; color:gray'>
                🎮 Guess a number between <b>{NUMBER_RANGE_MIN}</b> and <b>{NUMBER_RANGE_MAX:,}</b><br>
                💸 Contribute to the pot. Winner takes <b>88%</b>, the rest rolls over.<br>
                🧠 Game resets each round. Have fun!
            </div>
            """, unsafe_allow_html=True
        )

        st.markdown("---")
        winners = load_winner_data()
        if winners:
            st.markdown("### 🏆 Previous Winners")
            for entry in winners[-3:][::-1]:
                st.markdown(f"- **{entry['winner']}** won {entry['amount']} ETH")

        st.stop()
