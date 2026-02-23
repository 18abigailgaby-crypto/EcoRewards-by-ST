import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from PIL import Image
import json

# --- 1. CONFIGURATION & SETUP ---
st.set_page_config(
    page_title="EcoRewards by ST",
    page_icon="🌱",
    layout="centered"
)

# Load API Key from st.secrets
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("API Key not found. Please set GEMINI_API_KEY in your secrets.")

model = genai.GenerativeModel('gemini-1.5-flash')

# Logo and Title
LOGO_URL = "https://storage.googleapis.com/generativeai-downloads/images/sang_timur_logo.png" # Placeholder for the ST Logo

# --- 2. DATABASE CONNECTION (Google Sheets) ---
# Ensure you have configured [connections.gsheets] in your .streamlit/secrets.toml
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        return conn.read(worksheet="Students", ttl="1m")
    except:
        # Create initial dataframe if sheet is empty or doesn't exist
        return pd.DataFrame(columns=["StudentID", "Name", "Points", "Rank"])

def update_data(df):
    conn.update(worksheet="Students", data=df)

# --- 3. UI STYLING ---
st.markdown("""
    <style>
    .main {
        background-color: #f8fafc;
    }
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        background-color: #059669;
        color: white;
        font-weight: bold;
    }
    .stTextInput>div>div>input {
        border-radius: 10px;
    }
    .rank-badge {
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.8em;
        font-weight: bold;
        text-transform: uppercase;
    }
    </style>
    """, unsafe_allow_value=True)

# --- 4. SIDEBAR / LOGIN ---
st.sidebar.image(LOGO_URL, width=100)
st.sidebar.title("EcoRewards by ST")
st.sidebar.markdown("---")

student_id = st.sidebar.text_input("Student ID (e.g. STU001)")
student_name = st.sidebar.text_input("Full Name")

if not student_id or not student_name:
    st.info("👋 Welcome! Please enter your Student ID and Name in the sidebar to start recycling.")
    st.stop()

# Load current data
df = get_data()

# Check if student exists, if not add them
if student_id not in df['StudentID'].values:
    new_student = pd.DataFrame([{"StudentID": student_id, "Name": student_name, "Points": 0, "Rank": "Beginner"}])
    df = pd.concat([df, new_student], ignore_index=True)
    update_data(df)

current_student = df[df['StudentID'] == student_id].iloc[0]

# --- 5. MAIN CONTENT ---
st.title("🌱 EcoRewards by ST")
st.markdown(f"Welcome back, **{student_name}**! You currently have **{current_student['Points']} points**.")

col1, col2 = st.columns(2)
with col1:
    st.metric("Your Points", f"{current_student['Points']} pts")
with col2:
    st.metric("Current Rank", current_student['Rank'])

st.divider()

st.subheader("📸 Upload Recycling Proof")
st.write("Take a photo of you disposing of plastic waste in the recycling bin.")

uploaded_file = st.file_uploader("Choose a photo...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    img = Image.open(uploaded_file)
    st.image(img, caption='Your Uploaded Proof', use_container_width=True)
    
    if st.button("Verify with AI & Earn Points"):
        with st.spinner("AI is analyzing your photo..."):
            try:
                prompt = """
                Analyze this image. Is it a photo of a student disposing of plastic trash into a recycling bin? 
                If yes, award points (10-50) based on the effort. 
                Return ONLY a JSON object: {"is_valid": boolean, "points": number, "reason": "string"}
                """
                response = model.generate_content([prompt, img])
                
                # Clean response text for JSON parsing
                result_text = response.text.strip()
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                
                result = json.loads(result_text)
                
                if result.get("is_valid"):
                    points_earned = result.get("points", 10)
                    st.success(f"✅ **Verified!** {result['reason']}")
                    st.balloons()
                    st.toast(f"You earned {points_earned} points!")
                    
                    # Update DataFrame
                    df.loc[df['StudentID'] == student_id, 'Points'] += points_earned
                    
                    # Update Rank
                    new_points = df.loc[df['StudentID'] == student_id, 'Points'].values[0]
                    new_rank = "Beginner"
                    if new_points >= 1000: new_rank = "Eco Legend"
                    elif new_points >= 500: new_rank = "Planet Protector"
                    elif new_points >= 200: new_rank = "Green Hero"
                    elif new_points >= 50: new_rank = "Eco Scout"
                    df.loc[df['StudentID'] == student_id, 'Rank'] = new_rank
                    
                    # Save to Google Sheets
                    update_data(df)
                    st.rerun()
                else:
                    st.error(f"❌ **Not Verified:** {result['reason']}")
            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")

# --- 6. LEADERBOARD ---
st.divider()
st.subheader("🏆 Leaderboard")
leaderboard_df = df.sort_values(by="Points", ascending=False).head(10)
st.table(leaderboard_df[["Name", "Points", "Rank"]])

# --- 7. REWARDS INFO ---
with st.expander("🍭 Reward Exchange Info"):
    st.write("""
    You can trade your points for candies at the school office:
    - **50 Pts:** Small Candy
    - **150 Pts:** Big Lollipop
    - **300 Pts:** Chocolate Bar
    """)
