import json
import streamlit as st
from src.database import setup_and_populate_db
from src.generator import compile_quiz_data
from src.config import MOCK_MODE, ENABLE_LIVE_SEARCH


@st.cache_resource
def prepare_knowledge_base():
    return setup_and_populate_db()


def render_question_card(idx: int, q: dict):
    st.markdown(f"**Q{idx+1}. {q['question']}**")
    options = q.get("options", [])
    # Render a single radio widget per question for accessibility
    radio_options = [f"{chr(65 + i)}. {opt}" for i, opt in enumerate(options)]
    _ = st.radio(f"Choose an answer for Q{idx+1}", options=radio_options, key=f"q{idx}_radio")

    if st.button("Reveal Answer", key=f"reveal_{idx}"):
        correct_letter = q.get("answer", "?")
        try:
            correct_index = ord(correct_letter) - 65
            correct_text = options[correct_index]
        except Exception:
            correct_text = "(unknown)"
        st.success(f"Answer: {correct_letter}. {correct_text}")
        with st.expander("Explanation"):
            st.write(q.get("explanation", ""))


def _build_local_fallback_quiz(sport: str, num_questions: int = 4):
    from src.database import query_historic_facts

    example_context = "No offline historic data recorded."
    try:
        db_query = f"{sport} history cup championships rules records"
        db_matches = query_historic_facts(sport=sport, query_text=db_query)
        example_context = "\n".join(db_matches) if db_matches else example_context
    except Exception:
        pass

    fallback_quiz = {"quiz": []}
    fallback_snippet = example_context.split('\n')[0]
    for i in range(num_questions):
        fallback_quiz["quiz"].append({
            "question": f"Fallback question {i+1} about {sport}",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "A",
            "explanation": f"HISTORICAL FACTS: {fallback_snippet} (Local fallback due to generation issue)"
        })
    return fallback_quiz


def main():
    st.set_page_config(page_title="Sports Quiz Agent", page_icon="🏆", layout="centered")
    st.title("🏆 AI-Powered Sports Quiz Generator")
    st.write("Generate grounded sports multiple-choice quizzes for social media.")

    # If the last LLM call fell back to a local/mock result, show a prominent banner.
    llm_raw = st.session_state.get("llm_raw")
    if isinstance(llm_raw, dict) and llm_raw.get("mock"):
        fallback_type = llm_raw.get("fallback", "")
        if fallback_type == "local":
            st.warning("A local fallback quiz was generated because the live LLM output failed validation. Facts should be verified before publishing.")
        elif fallback_type == "constructed":
            st.warning("A constructed fallback quiz was generated because the LLM did not return valid structured output. Verify all facts before publishing.")
        else:
            msg = (
                "Live LLM unavailable — the app used a mock quiz because the live LLM was unreachable or quota was exceeded. "
                "Results are best-effort; verify facts before publishing."
            )
            st.error(msg)
        if llm_raw.get("error"):
            with st.expander("LLM error details"):
                st.code(str(llm_raw.get("error")))
        if llm_raw.get("mock_context"):
            with st.expander("Fallback context used"):
                for src in llm_raw.get("mock_context"):
                    st.write(f"- {src}")
        st.info("To attempt a live generation, ensure your chosen LLM provider has a valid API key in .env (OPENAI_API_KEY or GEMINI_API_KEY), disable MOCK_MODE, and restart the app.")

    with st.sidebar:
        st.header("Quiz Settings")
        if st.button("Clear App State"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.experimental_rerun()

        sport = st.selectbox("Select Sport", ["Cricket", "Football", "Badminton", "Tennis", "Basketball"])
        difficulty = st.select_slider("Select Difficulty", options=["Easy", "Medium", "Hard"], value="Medium")
        live_search = st.checkbox("Enable Live Search", value=ENABLE_LIVE_SEARCH)

        generate_disabled = st.session_state.get("generating", False)
        if st.button("Generate Fresh Quiz", disabled=generate_disabled):
            st.session_state["generating"] = True
            try:
                with st.spinner("Generating quiz — this may take a few seconds..."):
                    quiz_json, context, raw_resp = compile_quiz_data(sport, difficulty, num_questions=4)
                    st.session_state["quiz"] = quiz_json
                    st.session_state["context"] = context
                    st.session_state["llm_raw"] = raw_resp
                    st.success("Quiz generated")
            except Exception as e:
                if isinstance(e, ValueError) and "Explanation does not reference retrieval sources" in str(e):
                    quiz_json = _build_local_fallback_quiz(sport, num_questions=4)
                    st.session_state["quiz"] = quiz_json
                    st.session_state["context"] = "Fallback local quiz generated due to citation validation failure."
                    st.session_state["llm_raw"] = {"mock": True, "fallback": "local"}
                    st.success("Fallback quiz generated")
                else:
                    import traceback
                    st.error(f"Failed to generate quiz: {e}")
                    tb = traceback.format_exc()
                    with st.expander("Generation traceback"):
                        st.code(tb)
                    # Also show any raw response stored in session for debugging
                    if st.session_state.get("llm_raw"):
                        with st.expander("Existing LLM raw response"):
                            st.json(st.session_state.get("llm_raw"))
            finally:
                st.session_state["generating"] = False

    # Ensure DB seeded
    prepare_knowledge_base()

    if "quiz" in st.session_state:
        quiz = st.session_state["quiz"]["quiz"]
        st.subheader(f"Quiz — {sport} ({difficulty})")

        if isinstance(llm_raw, dict) and llm_raw.get("mock"):
            st.info("This quiz is fallback-generated. Double-check the questions and explanations before publishing.")

        for idx, q in enumerate(quiz):
            with st.container():
                render_question_card(idx, q)

        st.markdown("---")
        st.subheader("Export / Copy")
        pretty_json = json.dumps(st.session_state["quiz"], ensure_ascii=False, indent=2)
        st.download_button("Download Quiz JSON", data=pretty_json, file_name=f"quiz_{sport}_{difficulty}.json", mime="application/json")
        st.text_area("Quiz JSON (copy)", value=pretty_json, height=250)

        with st.expander("🔍 RAG Context Used"):
            st.code(st.session_state.get("context", ""))


if __name__ == "__main__":
    main()
