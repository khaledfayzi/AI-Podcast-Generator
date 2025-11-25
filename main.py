from services.llm_service import LLMService

def main():
    llm = LLMService(model_name="llama3", use_dummy=False)

    thema = "Zukunft der Medizin durch KI"

    config = {
        "language": "de",
        "style": "freudig",
        "dauer": 12,
        "speakers": 2,
        "roles": {
            "speaker1": "Moderator",
            "speaker2": "Experte"
        },
        "pdf_text": "Dieser Text stammt aus einer Test-PDF über medizinische Innovationen."
    }

    print("========================")
    print("TEST: Volltest mit allen Parametern")
    print(config)
    print("========================")

    script = llm.generate_script(thema, config)
    print(script)

if __name__ == '__main__':
    main()
