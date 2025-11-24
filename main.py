from services.llm_service import LLMService

def main():
    llm = LLMService(model_name="llama3", use_dummy=False)  # ← hier korrigiert!
    thema = "Künstliche Intelligenz"
    script = llm.generate_script(thema)
    print("==Script==")
    print(script)

if __name__ == '__main__':
    main()
