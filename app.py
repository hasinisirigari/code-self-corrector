import streamlit as st
from src.llm.ollama_client import OllamaClient
from src.sandbox.docker_runner import DockerSandbox
from src.loop.orchestrator import Orchestrator

st.set_page_config(page_title="Self-Correcting Code Generator", page_icon="🔧")

@st.cache_resource
def load_system():
    llm = OllamaClient()
    sandbox = DockerSandbox()
    return Orchestrator(llm=llm, sandbox=sandbox, max_attempts=3)

orch = load_system()

st.title("🔧 Self-Correcting Code Generator")
st.markdown("Enter a function description and tests. The system will generate code and fix errors automatically.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Function Description")
    default_prompt = '''def is_prime(n: int) -> bool:
    """Return True if n is prime, False otherwise."""
'''
    prompt = st.text_area("Prompt", value=default_prompt, height=150)

with col2:
    st.subheader("Test Cases")
    default_tests = '''def test_prime():
    assert is_prime(2) == True
    assert is_prime(7) == True
    assert is_prime(10) == False
    assert is_prime(1) == False
'''
    tests = st.text_area("Tests", value=default_tests, height=150)

if st.button("Generate & Test", type="primary"):
    if not prompt.strip() or not tests.strip():
        st.error("Enter both prompt and tests")
    else:
        with st.spinner("Running..."):
            result = orch.solve(prompt, tests)
        
        for att in result.attempts:
            status = "YES" if att.status == "SUCCESS" else "NO"
            with st.expander(f"Attempt {att.number} {status}", expanded=(att.number == len(result.attempts))):
                st.code(att.code, language="python")
                if att.error:
                    st.error(f"{att.error.category.value}: {att.error.message}")
                st.caption(f"Gen: {att.gen_time:.1f}s | Exec: {att.exec_time:.1f}s")
        
        if result.solved:
            st.success(f"Solved in {len(result.attempts)} attempt(s)!")
            st.download_button("Download code", result.final_code, file_name="solution.py")
        else:
            st.error(f"Failed: {result.status}")

with st.sidebar:
    st.header("Examples")
    if st.button("Factorial"):
        st.session_state.prompt = '''def factorial(n: int) -> int:
    """Return factorial of n."""
'''
        st.session_state.tests = '''def test_factorial():
    assert factorial(0) == 1
    assert factorial(5) == 120
'''
        st.rerun()
    
    if st.button("Reverse String"):
        st.session_state.prompt = '''def reverse(s: str) -> str:
    """Return reversed string."""
'''
        st.session_state.tests = '''def test_reverse():
    assert reverse("hello") == "olleh"
    assert reverse("") == ""
'''
        st.rerun()
