import streamlit as st
import time
from chat_responses import LMMentorBot
from audit_parse import extract_text_fromaudit
from feedback import append_values
import asyncio
from typing import AsyncGenerator


st.set_page_config(
    page_title="Jeeves", 
    page_icon=":avocado:", 
    layout="centered",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.extremelycoolapp.com/help',
        'Report a bug': "https://www.extremelycoolapp.com/bug",
        'About': "# Jeeves - Your Personal Health Assistant\n\nJeeves is your AI-powered health and nutrition assistant, helping you make better food choices and live a healthier lifestyle. Get personalized meal plans, track your nutrition, and receive expert guidance on your health journey."
    }
)
st.title("🥑 JIYP - Live better eat better")

with st.sidebar:
    st.header("Meet Jeeves, your health assistant!")
    
    # Add demographic information form
    with st.form("demographic_info"):
        st.subheader("Tell us about yourself")
        
        # Basic Information
        age = st.number_input("Age", min_value=18, max_value=100, value=25)
        gender = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"])
        weight = st.number_input("Weight (kg)", min_value=30.0, max_value=200.0, value=70.0)
        height = st.number_input("Height (cm)", min_value=100, max_value=250, value=170)
        
        # Health Information
        st.subheader("Health Information")
        dietary_restrictions = st.multiselect(
            "Dietary Restrictions",
            ["None", "Vegetarian", "Vegan", "Gluten-Free", "Dairy-Free", "Kosher", "Halal", "Other"]
        )
        allergies = st.text_input("Allergies (comma-separated)")
        health_conditions = st.text_area("Health Conditions (optional)")
        
        # Goals
        st.subheader("Your Goals")
        primary_goal = st.selectbox(
            "Primary Goal",
            ["Weight Loss", "Muscle Gain", "Maintenance", "General Health", "Other"]
        )
        activity_level = st.selectbox(
            "Activity Level",
            ["Sedentary", "Lightly Active", "Moderately Active", "Very Active", "Extremely Active"]
        )
        
        # Submit button
        submitted = st.form_submit_button("Update Information")
        
        if submitted:
            # Create a context string from the form data
            context = f"""
            User Profile:
            - Age: {age}
            - Gender: {gender}
            - Weight: {weight} kg
            - Height: {height} cm
            - Dietary Restrictions: {', '.join(dietary_restrictions)}
            - Allergies: {allergies}
            - Health Conditions: {health_conditions}
            - Primary Goal: {primary_goal}
            - Activity Level: {activity_level}
            """
            st.session_state.user_context = context
            st.success("Information updated successfully!")

    st.divider()
    st.write("Jeeves can help you with:")
    st.write("- Calorie tracking")
    st.write("- Meal planning")
    st.write("- Recipe recommendations")
    st.divider()
    with st.expander("Disclaimer", icon ="⚠️"):
        st.markdown("Jeeves is a virtual assistant and is **not** a replacement for health professionals. Please consult with your doctor for official advice.")
        st.write("Jeeves does not store any personal information, any feedback is anonymous.")

# Initialize chat bot
if "chatBot" not in st.session_state:
    st.session_state.chatBot = LMMentorBot()

# Initialize user context
if "user_context" not in st.session_state:
    st.session_state.user_context = ""

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Comment out file upload functionality
# uploaded_file = st.file_uploader("Upload your document here:", type=["pdf"], accept_multiple_files=False)

# Display chat messages from history
for message in st.session_state.messages:
    avatar = None
    if message["role"] == "user":
        avatar = "🧑‍💻"
    else:
        avatar = "🥑"
        
    with st.chat_message(message["role"], avatar=avatar):
        st.empty()
        st.write(message["content"])

def send_user_input(prompt:str):
    button_holder.empty()

    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt)
    
    # add to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # call response generator with user context
    with st.chat_message("assistant", avatar="🥑"):
        with st.spinner("Thinking..."):
            # Combine user context with prompt
            full_prompt = f"{st.session_state.user_context}\n\nUser: {prompt}"
            response = st.write_stream(st.session_state.chatBot.chat_stream(full_prompt))

    st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Log the interaction to Google Sheets
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        append_values(
            st.secrets["google_sheets"]["spreadsheet_id"],
            f"{st.secrets['google_sheets']['sheet_name']}!A1:D1",
            "USER_ENTERED",
            [[timestamp, "Query", prompt, response]]
        )
    except Exception as e:
        print(f"Failed to log interaction: {e}")

button_holder = st.empty()

if len(st.session_state.messages) != 0:
    button_holder.empty()
else:
    with button_holder.container():   
        st.write("Click on a prompt to get started, or start chatting below:")
        but_a = st.button("Hi Jeeves, what can you do?")
        but_b = st.button("What should I eat for lunch today?")
        but_c = st.button("Help me plan a high-protein low carb day tomorrow")

    if but_a:
        send_user_input("Hi Jeeves, what can you do?")
    elif but_b:
        send_user_input("What should I eat for lunch today?")
    elif but_c:
        send_user_input("Help me plan a high-protein low carb day tomorrow")

# Comment out file upload handling
# if uploaded_file is not None and st.session_state.degree_audit == False:
#     audit_text = extract_text_fromaudit(uploaded_file)
#     with st.chat_message("user", avatar="🧑‍💻"):
#         st.markdown("*You uploaded your information*")
#     
#     if audit_text == "":
#         st.error("Error extracting text from PDF. Please try again.")
#     if audit_text == "Invalid PDF":
#         st.error("This doesn't look like a personal information form. Please try again.")

#     with st.chat_message("assistant", avatar="🥑"):
#         with st.spinner("Analyzing your document..."):
#             response = st.write_stream(st.session_state.chatBot.upload_degree_audit(audit_text))
    
#     # add to chat history
#     st.session_state.messages.append({"role": "user", "content": "*You uploaded your document*"})
#     st.session_state.messages.append({"role": "assistant", "content": response})
#     st.session_state.degree_audit = True

# Get user input
if prompt := st.chat_input("Help me track calories, these apps are too hard! I just had a banana and greek yogurt"):
    # Display user message
    send_user_input(prompt)

selected = st.feedback("thumbs")
if selected is not None:
    sentiment = None
    if selected == 0:
        sentiment = "Negative"
    else:
        sentiment = "Positive"
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        append_values(
            st.secrets["google_sheets"]["spreadsheet_id"],
            f"{st.secrets['google_sheets']['sheet_name']}!A1:E1",
            "USER_ENTERED",
            [[timestamp, "Feedback", str(st.session_state.messages), sentiment, "Session End"]]
        )
    except Exception as e:
        print(f"Failed to log feedback: {e}")
    st.success("Thank you for your feedback!")
