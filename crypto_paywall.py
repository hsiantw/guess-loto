import streamlit as st
import requests
import qrcode
from io import BytesIO
from decimal import Decimal
import json
import os
import time

# === Config ===
ETHERSCAN_API_KEY = "49E1XEPDY25A6QCQ2PDJVP1CWPNCIMVTF6"
WALLET_ADDRESS = "0x9689D356502f24836930BEC6FcCF145e6477247C"
MIN_AMOUNT_ETH = 0.0001
NUMBER_RANGE_MIN = 1
NUMBER_RANGE_MAX = 100_000_000_000
WINNERS_FILE = "winners.json"
UPDATE_INTERVAL = 60  # seconds

# === Load/Store Previous Winners and Rollovers ===
def load_winner_data():
    if os.path.exists(WINNERS_FILE):
        with open(WINNERS_FILE, "r") as f:
            return json.load(f)
    return []

def save_winner_data(winners):
    with open(WINNERS_FILE, "w") as f:
        json.dump(winners, f, indent=2)

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

# === Payment Check for Specific User ===
def check_user_payment(user_wallet_address: str):
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
            if (
                tx["to"].lower() == WALLET_ADDRESS.lower()
                and tx["from"].lower() == user_wallet_address.lower()
                and float(tx["value"]) / 10**18 >= MIN_AMOUNT_ETH
            ):
                return True

        return False
    except Exception as e:
        st.error(f"Payment check failed: {e}")
        return False

# === Pot Size Fetching ===
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

# === Main Paywall Logic ===
def crypto_paywall():
    st.title("🎰 Guess Loto")

    if "paid" not in st.session_state:
        st.session_state.paid = False
    if "user_wallet_address" not in st.session_state:
        st.session_state.user_wallet_address = ""

    if not st.session_state.paid:
        st.markdown("### 🔒 Access Locked")
        st.info(f"To play, please send **{MIN_AMOUNT_ETH} ETH** to the wallet below:")
        st.code(WALLET_ADDRESS)

        # QR Code
        st.markdown("### 📱 Scan QR Code to Pay")
        qr_image = generate_wallet_qr(WALLET_ADDRESS)
        st.image(qr_image, caption="ETH Wallet QR Code", width=200)

        # Wallet input
        st.markdown("### 🧾 Enter Your Wallet Address (Sender)")
        wallet_input = st.text_input("Your ETH Wallet Address", value=st.session_state.user_wallet_address)
        st.session_state.user_wallet_address = wallet_input.strip()

        # Real-Time Pot Calculation
        last_check_time = st.session_state.get("last_check_time", 0)
        current_time = time.time()
        if current_time - last_check_time > UPDATE_INTERVAL:
            st.session_state.total_eth = get_total_eth_received()
            st.session_state.last_check_time = current_time

        total_pot = st.session_state.get("total_eth", Decimal("0.0"))
        winner_share = total_pot * Decimal("0.88")
        carryover = total_pot * Decimal("0.12")

        st.markdown("### 💰 Current Pot Size")
        st.info(f"""
        - Total received: **{total_pot:.6f} ETH**
        - Winner takes: **{winner_share:.6f} ETH**
        - Rollover to next round: **{carryover:.6f} ETH**
        """)

        if st.button("🔍 Check Payment"):
            if wallet_input and check_user_payment(wallet_input):
                st.success("✅ Payment confirmed! You can now play.")
                st.session_state.paid = True
                st.rerun()
            else:
                st.warning("❌ No matching payment from your wallet detected. Try again in a few seconds.")

        # Game Description
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

        # Previous Winners
        st.markdown("---")
        winners = load_winner_data()
        if winners:
            st.markdown("### 🏆 Previous Winners")
            for entry in winners[-3:][::-1]:  # Show last 3
                st.markdown(f"- **{entry['winner']}** won {entry['amount']} ETH")

        st.stop()
