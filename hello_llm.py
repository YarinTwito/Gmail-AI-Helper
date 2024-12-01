from gpt4all import GPT4All

model = GPT4All("gpt4all-13b-snoozy-q4_0.gguf")
output = model.generate("Print Hello LLM", max_tokens=50)
print(output)
