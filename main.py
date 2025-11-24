from services.llm_service import LLMService

def main():
    llm = LLMService(model_name="llama3", use_dummy=False)  
    thema = "python"
    config = {
    "language": "de",
    "style": "neutral",
    "dauer": 5,
}

    script = llm.generate_script(thema,config)
    print("==Script==")
    print(script)

if __name__ == '__main__':
    main()
