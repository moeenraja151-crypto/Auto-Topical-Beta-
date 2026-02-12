import os
import fitz  # PyMuPDF
import customtkinter as ctk
from fpdf import FPDF
from io import BytesIO
from PIL import Image, ImageTk
from tkinter import filedialog, Toplevel, StringVar, Listbox, END, Label, Canvas, Scrollbar, Frame, Button, Entry
import nltk
from nltk.corpus import wordnet
import re
import json
import platform
import socket
import requests  # To send login details remotely
import concurrent.futures

nltk.download('wordnet')

PDF_FOLDER = r"C:\Users\moeen\Downloads\Maths PDFs\pdfs"
REFERENCE_PDF = "/mnt/data/Math-topic questions-IGCSE.pdf"  # Reference PDF for keyword analysis
LOGIN_FILE = "logins.json"  # Store login details
LOG_SERVER_URL = "https://your-server.com/log-login"  # Replace with your actual log server endpoint

# Default login credentials (can be updated dynamically)
def load_logins():
    if not os.path.exists(LOGIN_FILE):
        with open(LOGIN_FILE, "w") as f:
            json.dump({"admin": "admin"}, f)
    with open(LOGIN_FILE, "r") as f:
        return json.load(f)

def log_login_attempt(username):
    system_info = {
        "username": username,
        "device": platform.system(),
        "device_name": socket.gethostname(),
        "login_count": 1
    }
    try:
        requests.post(LOG_SERVER_URL, json=system_info)
    except Exception as e:
        print(f"Failed to send login details: {e}")

class LoginWindow:
    def __init__(self, root, callback):
        self.root = root
        self.root.title("Login")
        self.root.geometry("300x200")
        self.callback = callback
        self.logins = load_logins()

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.login_frame = ctk.CTkFrame(self.root, corner_radius=10, fg_color="#f0f0f0")
        self.login_frame.pack(pady=20, padx=20, fill="both", expand=True)

        self.username_label = ctk.CTkLabel(self.login_frame, text="Username:", font=("Arial", 12))
        self.username_label.pack(pady=5)

        self.username_entry = ctk.CTkEntry(self.login_frame, placeholder_text="Enter username", width=200)
        self.username_entry.pack(pady=5)

        self.password_label = ctk.CTkLabel(self.login_frame, text="Password:", font=("Arial", 12))
        self.password_label.pack(pady=5)

        self.password_entry = ctk.CTkEntry(self.login_frame, placeholder_text="Enter password", show="*", width=200)
        self.password_entry.pack(pady=5)

        self.login_button = ctk.CTkButton(self.login_frame, text="Login", command=self.verify_login, font=("Arial", 12))
        self.login_button.pack(pady=10)

    def verify_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if username in self.logins and self.logins[username] == password:
            log_login_attempt(username)
            self.root.withdraw()
            self.callback()
        else:
            self.error_label = ctk.CTkLabel(self.login_frame, text="Invalid credentials. Please try again.", text_color="red", font=("Arial", 12))
            self.error_label.pack(pady=5)
            self.username_entry.delete(0, END)
            self.password_entry.delete(0, END)

class PDFExtractorApp:
    def __init__(self, root):
        print("Initializing GUI...")  # Debugging print
        self.root = root
        self.root.title("Maths PDF Filter")
        self.root.geometry("800x600")

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.main_frame = ctk.CTkFrame(self.root, corner_radius=10, fg_color="#f0f0f0")
        self.main_frame.pack(pady=20, padx=20, fill="both", expand=True)

        self.search_frame = ctk.CTkFrame(self.main_frame, corner_radius=10, fg_color="#ffffff")
        self.search_frame.pack(pady=10, padx=10, fill="x")

        self.search_label = ctk.CTkLabel(self.search_frame, text="Search for keywords:", font=("Arial", 12))
        self.search_label.pack(pady=5, padx=10, side="left")

        self.search_var = StringVar()
        self.search_var.trace_add("write", lambda *args: self.update_suggestions())

        self.search_entry = ctk.CTkEntry(self.search_frame, textvariable=self.search_var, placeholder_text="Enter keyword", width=200)
        self.search_entry.pack(pady=5, padx=10, side="left")

        self.suggestion_listbox = Listbox(self.main_frame, width=50, height=10)
        self.suggestion_listbox.pack(pady=10, padx=10, fill="x")

        self.add_button = ctk.CTkButton(self.main_frame, text="Add Keyword", command=self.add_keyword, font=("Arial", 12))
        self.add_button.pack(pady=10, padx=10, fill="x")

        self.keyword_frame = ctk.CTkFrame(self.main_frame, corner_radius=10, fg_color="#ffffff")
        self.keyword_frame.pack(pady=10, padx=10, fill="x")

        self.btn_select_pdf = ctk.CTkButton(self.main_frame, text="Select Math PDF", command=self.select_pdf, font=("Arial", 12))
        self.btn_select_pdf.pack(pady=10, padx=10, fill="x")

        self.btn_preview = ctk.CTkButton(self.main_frame, text="Generate Preview", command=self.preview_pdf, font=("Arial", 12))
        self.btn_preview.pack(pady=10, padx=10, fill="x")

        self.selected_pdf = None
        self.selected_keywords = []
        self.extracted_images = []
        self.keywords = {
                    "Number": ["natural numbers", "integers", "prime numbers", "square numbers", "cube numbers", "common factors", "common multiples", "rational numbers", "irrational numbers", "reciprocals", "venn diagrams", "set notation", "powers", "square roots", "cubes", "cube roots", "fractions", "decimals", "percentages", "magnitude", "symbols", "addition", "subtraction", "multiplication", "division", "indices", "standard form", "estimation", "rounding", "accuracy", "upper bounds", "lower bounds", "ratio", "proportion", "average speed", "currency conversion", "compound interest", "time zones", "surds", "exponential growth", "exponential decay", "conversion", "common measures"],
                    "Algebra": ["substitution", "expressions", "formulas", "simplifying", "expanding", "factorizing", "algebraic fractions", "linear equations", "simultaneous equations", "quadratic equations", "changing the subject", "inequalities", "nth term", "linear sequences", "cubic sequences", "direct proportion", "inverse proportion", "graphs", "rate of change", "sketching curves", "differentiation", "stationary points", "gradients", "maxima", "minima", "functions", "composite functions", "domain", "range"],
                    "Geometry": ["points", "lines", "angles", "shapes", "solids", "circles", "geometrical constructions", "nets", "scale drawings", "similarity", "symmetry", "polygons", "circle theorems", "unknown angles", "bearings", "transformations", "vectors", "enlargement", "translation", "rotation", "reflection", "position vectors", "geometric problems"],
                    "Statistics": ["classifying data", "mean", "median", "mode", "range", "scatter diagrams", "cumulative frequency", "quartiles", "histograms", "pie charts", "bar charts", "line of best fit", "stem and leaf", "frequency density", "relative frequency", "expected frequency"],
                    "Trigonometry": ["pythagoras' theorem", "sine", "cosine", "tangent", "trigonometric functions", "sine rule", "cosine rule", "angles between planes", "right-angled triangles", "trigonometric values", "30 degrees", "45 degrees", "60 degrees"],
                    "Mensuration": ["area", "perimeter", "circumference", "arc length", "sector area", "surface area", "volume", "cuboids", "prisms", "cylinders", "spheres", "pyramids", "cones", "compound shapes"],
                    "Probability": ["probability scale", "sample space", "venn diagrams", "tree diagrams", "complementary events", "conditional probability", "expected frequencies"]
}

    def process_page(self, page):
        text = page.get_text("text").lower()
        if any(kw in text for kw in self.selected_keywords):
            pix = page.get_pixmap()
            if pix:
                img_data = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                return img_data
        return None

    def preview_pdf(self):
        if not self.selected_pdf:
            print("No PDF selected!")
            return

        try:
            os.environ['FITZ_MAX_MEMORY'] = '10000000000'  # Set the memory limit to 10 GB
            doc = fitz.open(self.selected_pdf)
            self.extracted_images.clear()
            valid_images = []

            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                for page in doc:
                    futures.append(executor.submit(self.process_page, page))
                for future in concurrent.futures.as_completed(futures):
                    img_data = future.result()
                    if img_data:
                        valid_images.append(img_data)

            if not valid_images:
                print("No relevant pages found.")
                return

            preview_window = Toplevel(self.root)
            preview_window.title("Preview PDF")
            preview_window.geometry("800x600")

            canvas = Canvas(preview_window, bg="white")
            scrollbar = Scrollbar(preview_window, orient="vertical", command=canvas.yview)
            scrollable_frame = Frame(canvas, bg="white")

            scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            for img in valid_images:
                img.thumbnail((750, 750))
                img_tk = ImageTk.PhotoImage(img)
                lbl = Label(scrollable_frame, image=img_tk, bg="white")
                lbl.image = img_tk
                lbl.pack(pady=5)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            save_button = ctk.CTkButton(preview_window, text="Save as PDF", command=lambda: self.save_pdf(valid_images))
            save_button.pack(pady=10)

            zoom_in_button = ctk.CTkButton(preview_window, text="+", command=lambda: self.zoom_in(canvas, scrollable_frame, valid_images))
            zoom_in_button.pack(pady=10)

            zoom_out_button = ctk.CTkButton(preview_window, text="-", command=lambda: self.zoom_out(canvas, scrollable_frame, valid_images))
            zoom_out_button.pack(pady=10)

        except Exception as e:
            print(f"An error occurred: {e}")

    def save_pdf(self, images):
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if file_path:
            pdf = FPDF()
            for img in images:
                pdf.add_page()
                pdf.image(img, 0, 0, 210, 297)
            pdf.output(file_path, "F")

    def zoom_in(self, canvas, frame, images):
        for widget in frame.winfo_children():
            widget.destroy()
        for img in images:
            img.thumbnail((900, 900))
            img_tk = ImageTk.PhotoImage(img)
            lbl = Label(frame, image=img_tk, bg="white")
            lbl.image = img_tk
            lbl.pack(pady=5)
        canvas.configure(scrollregion=canvas.bbox("all"))

    def zoom_out(self, canvas, frame, images):
        for widget in frame.winfo_children():
            widget.destroy()
        for img in images:
            img.thumbnail((600, 600))
            img_tk = ImageTk.PhotoImage(img)
            lbl = Label(frame, image=img_tk, bg="white")
            lbl.image = img_tk
            lbl.pack(pady=5)
        canvas.configure(scrollregion=canvas.bbox("all"))

    def select_pdf(self):
        self.selected_pdf = filedialog.askopenfilename(initialdir=PDF_FOLDER, filetypes=[("PDF Files", "*.pdf")])
        print(f"Selected PDF: {self.selected_pdf}")

    def update_suggestions(self, *args):
        search_term = self.search_var.get().lower()
        self.suggestion_listbox.delete(0, END)
        if search_term:
            for category, words in self.keywords.items():
                for word in words:
                    if search_term in word:
                        self.suggestion_listbox.insert(END, word)

    def add_keyword(self):
        selected_index = self.suggestion_listbox.curselection()
        if selected_index:
            selected = self.suggestion_listbox.get(selected_index)
            if selected not in self.selected_keywords:
                self.selected_keywords.append(selected)
                self.update_selected_keywords()
                self.search_var.set("")
                self.suggestion_listbox.delete(0, END)

    def update_selected_keywords(self):
        for widget in self.keyword_frame.winfo_children():
            widget.destroy()
        for keyword in self.selected_keywords:
            frame = ctk.CTkFrame(self.keyword_frame, corner_radius=10, fg_color="#ffffff")
            label = ctk.CTkLabel(frame, text=keyword, font=("Arial", 12))
            label.pack(pady=5, padx=10, side="left")
            btn_remove = ctk.CTkButton(frame, text="X", command=lambda kw=keyword: self.remove_keyword(kw), font=("Arial", 12))
            btn_remove.pack(pady=5, padx=10, side="right")
            frame.pack(pady=2, fill="x")

    def remove_keyword(self, keyword):
        if keyword in self.selected_keywords:
            self.selected_keywords.remove(keyword)
            self.update_selected_keywords()

if __name__ == "__main__":
    root = ctk.CTk()
    def start_main_app():
        root.destroy()
        main_root = ctk.CTk()
        PDFExtractorApp(main_root)
        main_root.mainloop()
    
    login_window = LoginWindow(root, start_main_app)
    root.mainloop()
