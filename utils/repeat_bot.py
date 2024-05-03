import os
from collections import deque
from openai import OpenAI

def find_latest_file(directory):
    # Retorna o arquivo mais recente no diretório especificado
    files = [os.path.join(directory, file) for file in os.listdir(directory)]
    if not files:
        return None
    latest_file = max(files, key=os.path.getmtime)
    return latest_file

def read_last_n_lines(file_path, n):
    # Lê as últimas n linhas do arquivo
    with open(file_path, 'r', encoding='utf-8') as file:
        return deque(file, n)

def repeat(directory, n_lines, language):
    latest_file = find_latest_file(directory)
    if latest_file:
        last_lines = read_last_n_lines(latest_file, n_lines)
        message = ''
        for line in last_lines:
            message += line.rstrip()     
        # Point to the local server
        client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

        completion = client.chat.completions.create(
            model="lmstudio-ai/gemma-2b-it-GGUF",
            messages=[
                {"role": "system", "content": "Summarize the content into 3 sentences that capture the main ideas and key points. Translate to " + language + ": "},
                {"role": "user", "content": message}
            ],
            temperature=0.9,
            max_tokens=200,
            stream=False
        )

        return completion.choices[0].message.content.replace('\n',' ')
    else:
        print("No files found in the directory.")




