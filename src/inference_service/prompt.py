def build_prompt(question: str) -> str:
    clean_question = question.strip()

    return (
        "Answer the following question concisely, with only the answer. "
        "Return only the final answer, without explanation.\n\n"
        f"Question: {clean_question}\n"
        "Answer:"
    )
