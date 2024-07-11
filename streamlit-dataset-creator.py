import streamlit as st
import json
from huggingface_hub import HfApi, hf_hub_download, hf_hub_url
import pandas as pd
import io

# Hugging Face API setup
hf_api = HfApi()

# Predefined values
REPO_NAME = "Isuru0x01/sinhala_questions_answers"
HF_TOKEN = ""
DATA_FILENAME = "data.jsonl"

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": "මගේ නම නවෝදි. මම ඔබට කෙසේද සහය වෙන්නේ?"}]
if "conversation_count" not in st.session_state:
    st.session_state.conversation_count = 1

def create_conversation():
    system_msg = st.text_area("System message:", st.session_state.messages[0]["content"])

    if system_msg != st.session_state.messages[0]["content"]:
        st.session_state.messages[0] = {"role": "system", "content": system_msg}

    for i in range(1, len(st.session_state.messages) // 2 + 1):
        user_msg = st.text_input(f"User message {i}:", st.session_state.messages[i*2-1]["content"] if len(st.session_state.messages) > i*2-1 else "")
        assistant_msg = st.text_input(f"Assistant message {i}:", st.session_state.messages[i*2]["content"] if len(st.session_state.messages) > i*2 else "")

        if user_msg and (i*2-1 >= len(st.session_state.messages) or user_msg != st.session_state.messages[i*2-1]["content"]):
            if len(st.session_state.messages) <= i*2-1:
                st.session_state.messages.append({"role": "user", "content": user_msg})
            else:
                st.session_state.messages[i*2-1] = {"role": "user", "content": user_msg}

        if assistant_msg and (i*2 >= len(st.session_state.messages) or assistant_msg != st.session_state.messages[i*2]["content"]):
            if len(st.session_state.messages) <= i*2:
                st.session_state.messages.append({"role": "assistant", "content": assistant_msg})
            else:
                st.session_state.messages[i*2] = {"role": "assistant", "content": assistant_msg}

    if st.button("Add new message pair"):
        st.session_state.messages.extend([
            {"role": "user", "content": ""},
            {"role": "assistant", "content": ""}
        ])

    if len(st.session_state.messages) > 1 and st.button("Clear all messages"):
        st.session_state.messages = [{"role": "system", "content": system_msg}]

    return {"messages": st.session_state.messages}

def fetch_dataset():
    try:
        file_path = hf_hub_download(repo_id=REPO_NAME, filename=DATA_FILENAME, token=HF_TOKEN)
        with open(file_path, 'r', encoding='utf-8') as file:
            return [json.loads(line) for line in file]
    except Exception as e:
        st.warning(f"Dataset file '{DATA_FILENAME}' not found or error fetching dataset: {str(e)}")
        return []

def update_dataset(dataset):
    try:
        content = '\n'.join(json.dumps(item) for item in dataset)
        hf_api.upload_file(
            path_or_fileobj=io.BytesIO(content.encode()),
            path_in_repo=DATA_FILENAME,
            repo_id=REPO_NAME,
            token=HF_TOKEN
        )
        st.success("Dataset updated successfully!")
    except Exception as e:
        st.error(f"Error updating dataset: {str(e)}")

def display_dataset(dataset):
    if not dataset:
        st.write("No data available.")
        return

    def extract_conversation_data(conv):
        system_msg = conv['messages'][0]['content']
        user_msgs = [msg['content'] for msg in conv['messages'] if msg['role'] == 'user']
        assistant_msgs = [msg['content'] for msg in conv['messages'] if msg['role'] == 'assistant']
        return {
            'System': system_msg,
            'User': ' | '.join(user_msgs),
            'Assistant': ' | '.join(assistant_msgs)
        }

    df = pd.DataFrame([extract_conversation_data(item) for item in dataset[-10:]])  # Last 10 items

    st.table(df)

    to_delete = st.multiselect(
        "Select rows to delete (0 is the oldest displayed, 9 is the newest):",
        range(len(df))
    )

    if st.button("Delete Selected Rows"):
        for index in sorted(to_delete, reverse=True):
            del dataset[-(10-index)]
        update_dataset(dataset)
        st.experimental_rerun()

def main():
    st.title("Dataset Creator and Manager for Fine-tuning Models")

    st.write(f"Repository: {REPO_NAME}")

    tab1, tab2 = st.tabs(["Create Conversation", "Manage Dataset"])

    with tab1:
        st.header("Create Conversation")
        conversation = create_conversation()

        if st.button("Add Conversation to Dataset"):
            if len(conversation["messages"]) > 2:  # Ensure we have at least one user-assistant exchange
                dataset = fetch_dataset()
                dataset.append(conversation)
                update_dataset(dataset)
                st.session_state.messages = [{"role": "system", "content": conversation["messages"][0]["content"]}]  # Reset conversation
                st.session_state.conversation_count += 1  # Increment conversation count
                st.experimental_rerun()  # Refresh to clear inputs
            else:
                st.warning("Please create a conversation with at least one user-assistant exchange before adding to the dataset.")

    with tab2:
        st.header("Manage Dataset")
        dataset = fetch_dataset()
        display_dataset(dataset)

if __name__ == "__main__":
    main()
