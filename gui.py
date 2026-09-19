import customtkinter as ctk
from engine import CityIntelligenceEngine
from langchain_core.messages import HumanMessage, ToolMessage
import threading

# Set UI theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class CityApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.engine = CityIntelligenceEngine()
        self.title("City Intelligence Agent")
        self.geometry("600x700")

        # Sidebar for Input
        self.sidebar = ctk.CTkFrame(self, width=200)
        self.sidebar.pack(side="left", fill="y", padx=10, pady=10)

        self.city_input = ctk.CTkEntry(self.sidebar, placeholder_text="Enter city...")
        self.city_input.pack(pady=20, padx=10)

        self.analyze_btn = ctk.CTkButton(self.sidebar, text="Analyze", command=self.run_agent)
        self.analyze_btn.pack(pady=10, padx=10)

        # Main Display
        self.display = ctk.CTkTextbox(self, width=380, height=650)
        self.display.pack(side="right", fill="both", expand=True, padx=10, pady=10)

    def log(self, text):
        self.display.insert("end", text + "\n\n")
        self.display.see("end")

    def run_agent(self):
        city = self.city_input.get()
        if not city: return

        # Run in thread to keep GUI responsive
        threading.Thread(target=self._agent_thread, args=(city,), daemon=True).start()

    def _agent_thread(self, city):
        self.log(f"--- Analyzing {city} ---")
        messages = [self.engine.messages[0], HumanMessage(content=f"Tell me about {city}")]

        response = self.engine.run_agent_turn(messages)

        if response.tool_calls:
            for tool_call in response.tool_calls:
                # Simple Manual Approval Dialog
                dialog = ctk.CTkInputDialog(text=f"Approve {tool_call['name']}?", title="Tool Approval")
                approval = dialog.get_input()

                if approval and approval.lower() == "yes":
                    self.log(f"Executing {tool_call['name']}...")
                    result = self.engine.execute_tool(tool_call['name'], tool_call['args'])
                    self.log(str(result))
                else:
                    self.log("Tool denied.")
        else:
            self.log(f"Agent: {response.content}")

if __name__ == "__main__":
    app = CityApp()
    app.mainloop()
