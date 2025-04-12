import streamlit as st

# Initialize session state for posts if not already present.
if "posts" not in st.session_state:
    st.session_state.posts = []

# Title of the forum page.
st.title("Technique Questions Forum")

# --- Posting a Question ---
st.subheader("Post a New Technical Question")
with st.form("post_question_form"):
    question = st.text_area("Enter your technical question:", height=150)
    submit_post = st.form_submit_button("Post Question")
    if submit_post:
        if question.strip() != "":
            # Each post consists of the question and an empty list for answers
            st.session_state.posts.append({
                "question": question,
                "answers": []
            })
            st.success("Your question has been posted!")
        else:
            st.error("Please enter a valid question before posting.")

# --- Displaying Questions ---
st.header("Questions & Answers")
# Reverse the list to show the most recent posts on top.
for idx, post in enumerate(reversed(st.session_state.posts)):
    st.markdown(f"**Question:** {post['question']}")
    
    # Show any existing answers
    if post["answers"]:
        st.markdown("**Answers:**")
        for answer in post["answers"]:
            st.markdown(f"- {answer}")
    else:
        st.markdown("_No answers yet. Be the first to answer!_")
    
    # Provide a section to answer the question.
    with st.expander("Add an Answer"):
        # Note: the key ensures that each answer text area is distinct.
        answer = st.text_area("Your Answer", key=f"answer_{idx}", height=80)
        if st.button("Submit Answer", key=f"submit_{idx}") and answer.strip() != "":
            # Locate the original post using reverse index mapping.
            original_index = len(st.session_state.posts) - 1 - idx
            st.session_state.posts[original_index]["answers"].append(answer)
            st.success("Your answer has been added!")
            # Rerun the app to refresh the displayed answers.
            st.experimental_rerun()
        elif st.button("Submit Answer", key=f"submit_{idx}") and answer.strip() == "":
            st.error("Please enter a valid answer before submitting.")

    st.markdown("---")
