import argparse
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
import subprocess
from rich.panel import Panel
from rich.console import Console
from rich.markdown import Markdown
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def handle_error(console, chain, proc):
    stdout, stderr = proc.communicate()
    if stderr:
        error_message = stderr.decode()
        error_panel = Panel(f"{error_message}", style="red", title="Error")
        console.print(error_panel)
        response_text = chain.run(error_message)
        response_text = f"{response_text}".replace('pip', 'pipenv')
        markdown = Markdown(response_text)
        panel = Panel(markdown, title="ChatGPT", style="yellow")
        console.print(panel)
    else:
        console.print(stdout.decode())

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, console, shell_cmd, other_args, chain):
        self.console = console
        self.shell_cmd = shell_cmd
        self.other_args = other_args
        self.chain = chain
        
    def on_any_event(self, event):
        if event.is_directory:
            return None

        # Only watch for .py files
        if not event.src_path.endswith((".py", ".dart", ".conf", ".js", ".jsx", ".ts", ".tsx", ".rb")):
            return None

        self.console.clear()
        self.console.print(f"Watching for changes in: {os.path.dirname(event.src_path)}\n")

        # Run the command and display the output
        proc = subprocess.Popen([self.shell_cmd] + self.other_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        handle_error(console, chain, proc)
        
# Parse the shell command arg and the watch flag argument
parser = argparse.ArgumentParser(description='Execute shell command and log output')
parser.add_argument('shell_cmd', metavar='CMD', type=str, help='Shell command to execute')
parser.add_argument('other_args', metavar='ARGS', type=str, nargs=argparse.REMAINDER, help='Any other arguments to pass to the shell command')
parser.add_argument('--watch', action='store_true', help='Watch mode. Rerun the command on .py file changes')
args = parser.parse_args()

llm = OpenAI(temperature=0.9)
prompt = PromptTemplate(
    input_variables=["error_message"],
    template="{error_message}\n format respnse in markdown.",
)

chat = ChatOpenAI(temperature=0.9)
chain = LLMChain(llm=llm, prompt=prompt)

# Pass the remaining arguments to the shell command
shell_args = ' '.join(args.other_args)

console = Console()

# Watch mode
if args.watch:
    watch_dir = os.path.dirname(args.other_args[0])  # Get directory from first argument
    console.print(f"Watching for changes in: {watch_dir}\n")
    proc = subprocess.Popen([args.shell_cmd] + args.other_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    handle_error(console, chain, proc)
    observer = Observer()
    event_handler = FileChangeHandler(console, args.shell_cmd, args.other_args, chain)
    observer.schedule(event_handler, watch_dir, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# Regular mode
else:
    proc = subprocess.Popen([args.shell_cmd] + args.other_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    handle_error(console, chain, proc)