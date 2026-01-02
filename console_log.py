from datetime import datetime

def console_log(text: str):
    print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {text}')