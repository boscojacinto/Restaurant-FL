import requests
import threading
import json

url = "http://localhost:11434/api/chat"
headers = {"Content-Type": "application/json"}

def stream_chat(prompt):
    data = {
        "model": "gemma3:1b",
        "messages": [{"role": "user", "content": prompt}],
        "stream": True
    }
    print(f"\nStarting stream for: {prompt}")
    with requests.post(url, json=data, headers=headers, stream=True) as response:
        for line in response.iter_lines():
            if line:  # Filter out keep-alive new lines
                chunk = json.loads(line.decode('utf-8'))
                content = chunk.get("message", {}).get("content", "")
                if content:
                    print(content, end="", flush=True)  # Print each chunk as it arrives
                if chunk.get("done", False):  # Check if the stream is finished
                    print("\n[Stream Done]")
                    break

# Create two threads for different chats
thread1 = threading.Thread(target=stream_chat, args=("Tell me about rockets",))

# Start both threads
thread1.start()

# Wait for both to finish
thread1.join()

print("\nBoth streams completed!")