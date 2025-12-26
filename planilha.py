import customtkinter as ctk
from PIL import Image, ImageSequence
import requests
import cv2
import numpy as np
from io import BytesIO
import threading
import time
import os
import queue
import random

# --- CONFIGURAÇÕES ---
SHEET_ID = '1X1-DvnnlEirygGW3x7r7U2iw-FWTw95oICv4zCqQHhM'
API_KEY = 'AIzaSyCz9hvz0H1q1-qlnUAEDy0kVTZbcMaCZp0'
USUARIO_MESTRE = "admin"
SENHA_MESTRE = "123"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Visualizador Pre-Load 300x600")
        self.geometry("300x600")
        self.resizable(False, False)
        self.configure(fg_color="#000")

        self.tentativas = 3
        self.lista_midias = []
        self.indice_atual = 0
        self.gifs_progresso = []
        self.gif_escolhido_progresso = None
        self.playing = False
        self.cache_midia = {}                  # Cache de conteúdos baixados
        self.preload_queue = queue.Queue()     # Fila de pré-carregamento
        self.current_render_thread = None

        self.main_container = ctk.CTkFrame(self, width=300, height=600, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True)

        self.tela_progresso()

        # Inicia workers de pré-carregamento (2 threads paralelas)
        for _ in range(2):
            threading.Thread(target=self.preload_worker, daemon=True).start()

        # Carrega GIFs de progresso
        threading.Thread(target=self.carregar_dados_iniciais, daemon=True).start()

    def limpar_tela(self):
        self.stop_current_render()
        for widget in self.main_container.winfo_children():
            widget.destroy()

    def stop_current_render(self):
        self.playing = False
        if self.current_render_thread and self.current_render_thread.is_alive():
            self.current_render_thread.join(timeout=0.5)

    # ==================== 1. TELA DE PROGRESSO ====================
    def tela_progresso(self):
        self.limpar_tela()
        self.label_loading = ctk.CTkLabel(self.main_container, text="", width=300, height=450)
        self.label_loading.pack(pady=10)

        self.barra = ctk.CTkProgressBar(self.main_container, width=250, progress_color="#e50914")
        self.barra.set(0)
        self.barra.pack(pady=20)

        self.status_label = ctk.CTkLabel(self.main_container, text="Sincronizando... 0%", font=("Arial", 12))
        self.status_label.pack()

    def carregar_dados_iniciais(self):
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/Progresso!B2:B?key={API_KEY}"
        try:
            res = requests.get(url).json()
            if 'values' in res:
                self.gifs_progresso = [row[0] for row in res['values'] if row[0].startswith('http')]
                if self.gifs_progresso:
                    self.gif_escolhido_progresso = random.choice(self.gifs_progresso)  # Escolhe 1 só
        except:
            pass
        finally:
            self.after(500, self.animar_progresso_logica)

    def animar_progresso_logica(self):
        # Inicia o GIF único em loop (se existir)
        if self.gif_escolhido_progresso:
            threading.Thread(
                target=self.engine_render,
                args=(self.gif_escolhido_progresso, self.label_loading),
                daemon=True
            ).start()

        # Animação suave da barra
        prog = 0
        while prog <= 100:
            prog += 1
            self.barra.set(prog / 100)
            self.status_label.configure(text=f"Pré-carregando... {prog}%")
            time.sleep(0.08)  # ~8-10 segundos no total (ajuste se quiser mais rápido)

        time.sleep(0.5)
        self.after(0, self.tela_login)

    # ==================== 2. PRÉ-CARREGAMENTO ====================
    def gerenciar_pre_load(self):
        if not self.lista_midias:
            return
        num_preload = 3
        indices = [self.indice_atual]
        for i in range(1, num_preload + 1):
            indices.append((self.indice_atual + i) % len(self.lista_midias))
            indices.append((self.indice_atual - i) % len(self.lista_midias))

        for idx in set(indices):
            url = self.lista_midias[idx][1]
            if url not in self.cache_midia and url not in self.preload_queue.queue:
                self.preload_queue.put(url)

    def preload_worker(self):
        while True:
            url = self.preload_queue.get()
            if url is None:
                break
            try:
                if url in self.cache_midia:
                    continue
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    self.cache_midia[url] = response.content
            except:
                pass
            finally:
                self.preload_queue.task_done()

    # ==================== 3. MOTOR DE RENDERIZAÇÃO ====================
    def engine_render(self, url, label, tempo_limite=None):
        self.playing = True
        start_time = time.time()

        content = self.cache_midia.get(url)
        if not content:
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                content = requests.get(url, headers=headers, timeout=10).content
                self.cache_midia[url] = content
            except:
                label.configure(text="Erro ao carregar")
                return

        if url.lower().endswith(('.mp4', '.webm')):
            self.render_video(content, label, tempo_limite, start_time)
        else:
            self.render_image_or_gif(content, label, tempo_limite, start_time)

    def render_video(self, content, label, tempo_limite, start_time):
        temp_file = f"temp_v_{abs(hash(content))}.mp4"
        with open(temp_file, "wb") as f:
            f.write(content)
        cap = cv2.VideoCapture(temp_file)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_delay = 1.0 / fps

        while self.playing:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img.thumbnail((300, 600))
            ctk_img = ctk.CTkImage(light_image=img, size=img.size)
            self.after(0, lambda i=ctk_img: label.configure(image=i, text=""))

            if tempo_limite and (time.time() - start_time) > tempo_limite:
                break
            time.sleep(frame_delay)

        cap.release()
        try:
            os.remove(temp_file)
        except:
            pass

    def render_image_or_gif(self, content, label, tempo_limite, start_time):
        img = Image.open(BytesIO(content))
        if getattr(img, "is_animated", False):
            frames = []
            delays = []
            for f in ImageSequence.Iterator(img):
                d = f.info.get('duration', 100) / 1000.0
                delays.append(max(d, 0.01))
                cf = f.copy().convert("RGBA")
                cf.thumbnail((300, 600))
                frames.append(ctk.CTkImage(light_image=cf, size=cf.size))

            f_idx = 0
            while self.playing:
                cur_f = frames[f_idx % len(frames)]
                self.after(0, lambda f=cur_f: label.configure(image=f, text=""))
                if tempo_limite and (time.time() - start_time) > tempo_limite:
                    break
                time.sleep(delays[f_idx % len(delays)])
                f_idx += 1
        else:
            img.thumbnail((300, 600))
            ctk_img = ctk.CTkImage(light_image=img, size=img.size)
            self.after(0, lambda i=ctk_img: label.configure(image=i, text=""))

    # ==================== 4. LOGIN E NAVEGAÇÃO ====================
    def tela_login(self):
        self.limpar_tela()
        ctk.CTkLabel(self.main_container, text="LOGIN", font=("Arial", 22, "bold")).pack(pady=60)
        self.user_e = ctk.CTkEntry(self.main_container, placeholder_text="Usuário")
        self.user_e.pack(pady=10)
        self.pass_e = ctk.CTkEntry(self.main_container, placeholder_text="Senha", show="*")
        self.pass_e.pack(pady=10)
        ctk.CTkButton(self.main_container, text="ACESSAR", fg_color="#e50914", command=self.validar).pack(pady=20)

    def validar(self):
        if self.user_e.get() == USUARIO_MESTRE and self.pass_e.get() == SENHA_MESTRE:
            self.carregar_final("Geral +18")
        else:
            self.tentativas -= 1
            if self.tentativas <= 0:
                self.carregar_final("Geral -18")
            else:
                self.status_label = ctk.CTkLabel(self.main_container, text=f"Senha incorreta. Tentativas: {self.tentativas}", text_color="red")
                self.status_label.pack(pady=10)

    def carregar_final(self, aba):
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{aba}!A2:C?key={API_KEY}"
        try:
            res = requests.get(url).json()
            self.lista_midias = res.get('values', [])
            self.after(0, self.montar_visualizador)
        except:
            pass

    def montar_visualizador(self):
        self.limpar_tela()
        self.display = ctk.CTkLabel(self.main_container, text="Carregando...", width=300, height=600)
        self.display.pack()

        self.bind("<Left>", lambda e: self.navegar(-1))
        self.bind("<Right>", lambda e: self.navegar(1))

        self.navegar(0)

    def navegar(self, direcao):
        self.stop_current_render()
        if not self.lista_midias:
            return

        self.indice_atual = (self.indice_atual + direcao) % len(self.lista_midias)
        url = self.lista_midias[self.indice_atual][1]

        self.display.configure(text="Carregando...")
        self.current_render_thread = threading.Thread(
            target=self.engine_render,
            args=(url, self.display),
            daemon=True
        )
        self.current_render_thread.start()

        self.gerenciar_pre_load()


if __name__ == "__main__":
    app = App()
    app.mainloop()