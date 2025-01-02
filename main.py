import openai
import streamlit as st

#new imports for tracking
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from datetime import datetime
import pytz
import json

#initialize firebase app
try:
    key_dict = json.loads(st.secrets["textkey"])
    cred = credentials.Certificate(key_dict)
    app = firebase_admin.initialize_app(cred)

except ValueError:
    pass
firestore_client = firestore.client()

#creates a doc, sets the time value to the current time in cst and message count to 1
def create_doc():
    coll_ref = firestore_client.collection("debatebot_uses")
    create_time, doc_ref = coll_ref.add(
        {
            "time": datetime.now(pytz.timezone("US/Central")),
            "message_count": 1
        }
    )
    return doc_ref.id

#adds 1 to the message count field in the given doc
def add_count(doc_id):
    firestore_client.collection("debatebot_uses").document(doc_id).update({"message_count": firestore.firestore.Increment(1)})

#import api key
openai.api_key = st.secrets["OPENAI_API_KEY"]

# create the instruction to the system role
system_role_instructions = {"role": "system",
                            "content": "Act as high school debater. You need to respond to your opponents arguments. Allow them to choose the topic and the side they are on."}

# set the title
st.title("💬 DebateBot")

#create new doc, and set doc_id variable if the doc does not already exist
if "doc_id" not in st.session_state:
    st.session_state["doc_id"] = create_doc()

# if there isn't a session variable called messages create one and add the initial instructions
# the "messages" session variable will be used to track the entire chat
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "What topic are we debating about?"}]


# write the contents of the chat, but skip in for the system role
for msg in st.session_state.messages:
    if msg["role"] != "system":
        st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():

    #call the add_count function for tracking purposes
    add_count(st.session_state["doc_id"])

    # add what the user said to messages
    st.session_state.messages.append({"role": "user", "content": prompt})

    # write what the user said
    st.chat_message("user").write(prompt)

    # the request is only used to debug what we actally send to OpenAI
    request = ""
    for item in st.session_state.messages:
        request += "\n" + str(item)

    # messages_to_open_ai is the list of messages we send to OpenAI
    messages_to_open_ai = st.session_state.messages

    # add the system instruction as the last of the messages.
    # this will reduce the chance the user can manipulate it
    messages_to_open_ai.append(system_role_instructions)

    # call OpenAI and receive a response
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages_to_open_ai)
    msg = response.choices[0].message
    st.session_state.messages.append(msg)
    st.chat_message("assistant").write(msg.content)

# judging
# if the number of messages are greater than 2 then show the Judge button
if len(st.session_state["messages"]) > 2:
    if st.button("Judge"):
        # we have to judge the debate
        judge_instructions = "You are a high school debate coach. The following is transcript of a practice debate between you and student.\n\n\n"
        for msg in st.session_state.messages:
            if msg["role"] == "assistant":
                judge_instructions += "You said '" + msg["content"] + "'\n\n\n"
            if msg["role"] == "user":
                judge_instructions += "User said '" + msg["content"] + "'\n\n\n"
        judge_instructions += "\nDetermine who won and explain how you determined the winner."

        with st.expander("Log"):
            st.write(judge_instructions)

        judge_response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                                      messages=[{"role": "assistant", "content": judge_instructions}])
        st.chat_message("assistant").write(judge_response.choices[0].message.content)
