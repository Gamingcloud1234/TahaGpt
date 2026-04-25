import customtkinter as ctk
from tkinter import filedialog
from google import genai
import threading
import os
import docx

# --- SETTINGS ---
ctk.set_appearance_mode("Dark")  # Options: "Dark", "Light"
ctk.set_default_color_theme("blue") 

API_KEY = "AIzaSyDDW6pwhuAPFxS84BOCj64GwVYJLNBiEFQ"
MODEL_NAME = "gemini-3-flash-preview"

class TahaGptApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("TahaGpt Pro Assistant")
        self.geometry("600x800")
        self.client = genai.Client(api_key=API_KEY)
        self.selected_file = None

        # --- UI LAYOUT ---
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 1. Main Chat Area
        self.chat_display = ctk.CTkTextbox(self, font=("Segoe UI", 14), corner_radius=15, border_width=2)
        self.chat_display.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.chat_display.configure(state="disabled")

        # 2. Bottom Input Frame
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.input_frame.grid_columnconfigure(1, weight=1)

        # File Status Label (Small text above input)
        self.file_info = ctk.CTkLabel(self, text="", text_color="#10a37f", font=("Arial", 11, "bold"))
        self.file_info.grid(row=0, column=0, sticky="s", pady=35)

        # Buttons & Entry
        self.btn_attach = ctk.CTkButton(self.input_frame, text="📎", width=40, height=40, 
                                       fg_color="#333333", hover_color="#444444", command=self.select_file)
        self.btn_attach.grid(row=0, column=0, padx=(0, 10))

        self.user_input = ctk.CTkEntry(self.input_frame, placeholder_text="Ask TahaGpt anything...", 
                                      height=45, font=("Segoe UI", 13), corner_radius=10)
        self.user_input.grid(row=0, column=1, sticky="ew")
        self.user_input.bind("<Return>", lambda e: self.send_logic())

        self.btn_send = ctk.CTkButton(self.input_frame, text="Send", width=80, height=40, 
                                     fg_color="#10a37f", hover_color="#0e8a6b", font=("Arial", 12, "bold"),
                                     command=self.send_logic)
        self.btn_send.grid(row=0, column=2, padx=(10, 0))

        # Close/Cross Button for File
        self.btn_close_file = ctk.CTkButton(self, text="✖", width=20, height=20, fg_color="#ff4d4d", 
                                           hover_color="#cc0000", text_color="white", command=self.clear_file)
        # Hidden by default

    # --- LOGIC ---
    def select_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.selected_file = path
            self.file_info.configure(text=f"Ready: {os.path.basename(path)}")
            self.btn_close_file.place(relx=0.5, rely=0.88, anchor="center")

    def clear_file(self):
        self.selected_file = None
        self.file_info.configure(text="")
        self.btn_close_file.place_forget()

    def log(self, sender, text):
        self.chat_display.configure(state="normal")
        color_prefix = "➤ YOU: " if sender == "You" else "✨ TahaGpt: "
        self.chat_display.insert("end", f"{color_prefix}{text}\n\n")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def send_logic(self):
        msg = self.user_input.get()
        if not msg and not self.selected_file: return
        
        self.log("You", msg)
        self.user_input.delete(0, "end")
        self.log("TahaGpt", "Generating response...")
        
        threading.Thread(target=self.call_api, args=(msg,)).start()

    def call_api(self, text):
        try:
            contents = [text]
            if self.selected_file:
                if self.selected_file.endswith(".docx"):
                    doc = docx.Document(self.selected_file)
                    contents.append("\n".join([p.text for p in doc.paragraphs]))
                else:
                    contents.append(self.client.files.upload(file=self.selected_file))

            response = self.client.models.generate_content(model=MODEL_NAME, contents=contents)
            self.replace_thinking(response.text)
            self.clear_file()
        except Exception as e:
            self.replace_thinking(f"System Error: {e}")

    def replace_thinking(self, final_text):
        self.chat_display.configure(state="normal")
        # Remove the 'Generating...' line
        content = self.chat_display.get("1.0", "end")
        new_content = content.replace("✨ TahaGpt: Generating response...\n\n", "")
        self.chat_display.delete("1.0", "end")
        self.chat_display.insert("end", new_content)
        self.log("TahaGpt", final_text)
        self.chat_display.configure(state="disabled")

if __name__ == "__main__":
    app = TahaGptApp()
    app.mainloop()