import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import sys
import re
from youtube_comment_downloader import *
from youtube_transcript_api import YouTubeTranscriptApi
import pandas as pd
import ollama
import json
from tqdm import tqdm


# --- FUNCIONES ORIGINALES ---

def obtener_transcripcion(url_video):
    """Obtiene la transcripción del video de YouTube"""
    print("Obteniendo la transcripción del video...")
    try:
        # Extraer el ID del video de la URL usando expresiones regulares
        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url_video)
        if not match:
            print("[ERROR] No se pudo extraer el ID del video de la URL.\n")
            return None

        video_id = match.group(1)

        # Usar la nueva sintaxis de youtube-transcript-api
        yt_api = YouTubeTranscriptApi()
        transcripcion_lista = yt_api.fetch(video_id, languages=['es', 'en'])

        # Extraer el texto dependiendo si devuelve un objeto o un diccionario
        texto_completo = []
        for fragmento in transcripcion_lista:
            if isinstance(fragmento, dict):
                texto_completo.append(fragmento.get('text', ''))
            else:
                # Para nuevas versiones que devuelven objetos
                texto_completo.append(getattr(fragmento, 'text', ''))

        texto_unido = " ".join(texto_completo)

        print(f"¡Transcripción obtenida! (Longitud: {len(texto_unido)} caracteres)\n")
        return texto_unido

    except Exception as e:
        print(f"[AVISO] No se pudo obtener la transcripción (puede que no tenga subtítulos): {e}\n")
        return None


def obtener_comentarios(url_video, limite=None):
    downloader = YoutubeCommentDownloader()
    generador = downloader.get_comments_from_url(url_video, sort_by=SORT_BY_POPULAR)

    lista_comentarios = []
    print("Descargando comentarios. Esto puede tardar un momento...\n")

    for i, comentario in enumerate(generador):
        if limite is not None and i >= limite:
            break
        lista_comentarios.append(comentario['text'])

    df = pd.DataFrame(lista_comentarios, columns=['Comentario'])
    print(f"¡Listo! Se descargaron {len(df)} comentarios.\n")
    return df


def analizar_con_llm(texto, tema_video):
    texto_corto = str(texto)[:1000]

    prompt = f"""
    Eres un analista de datos. El video de YouTube trata sobre: "{tema_video}".

    Analiza el siguiente comentario y responde ÚNICAMENTE con un objeto JSON válido con estas dos claves:
    1. "relacion": Responde "Sí" si el comentario habla sobre el video, o "No" si es spam o no tiene nada que ver.
    2. "emocion": Indica la emoción de este comentario (ej. Alegría, Ira, Tristeza, Sorpresa, Miedo, Asco, Neutro).

    Comentario: "{texto_corto}"
    """
    try:
        respuesta = ollama.chat(model='llama3.1', messages=[
            {'role': 'user', 'content': prompt}
        ], format='json')

        datos = json.loads(respuesta['message']['content'])
        return pd.Series([datos.get('relacion', 'Desconocido'), datos.get('emocion', 'Desconocida')])

    except Exception as e:
        return pd.Series(["Error", "Error"])


# --- LÓGICA DE INTERFAZ GRÁFICA ---

class RedirigirConsola:
    """Clase para redirigir los print() a la ventana de Tkinter"""

    def __init__(self, widget_texto):
        self.widget_texto = widget_texto

    def write(self, mensaje):
        self.widget_texto.insert(tk.END, mensaje)
        self.widget_texto.see(tk.END)  # Auto-scroll hacia abajo

    def flush(self):
        pass


def ejecutar_proceso(tree_csv, widget_transcripcion, boton_inicio):
    """Función que ejecuta tu código original en un hilo separado"""
    boton_inicio.config(state=tk.DISABLED)  # Deshabilita el botón mientras corre

    try:
        url_del_video = "https://youtu.be/XOtLLlQ7OgM"
        tema_del_video = "Un chico se disfraza e interactúa en la vida real como las emociones de la película Intensamente 2"

        # 1. Obtener Transcripción
        transcripcion = obtener_transcripcion(url_del_video)
        if transcripcion:
            print("--- MOSTRANDO TRANSCRIPCIÓN EN LA PESTAÑA CORRESPONDIENTE ---\n")
            # Insertar todo el texto en la nueva pestaña de Tkinter
            widget_transcripcion.delete(1.0, tk.END)
            widget_transcripcion.insert(tk.END, transcripcion)

            # Guardarla en un archivo txt como respaldo
            with open("transcripcion.txt", "w", encoding="utf-8") as f:
                f.write(transcripcion)
            print("Transcripción también guardada en 'transcripcion.txt'.\n")

        # 2. Obtener Comentarios
        df_comentarios = obtener_comentarios(url_del_video, limite=10)

        print("Pasando los comentarios al LLM local (Ollama)...")
        tqdm.pandas(desc="Progreso LLM")

        # 3. Analizar con LLM
        df_comentarios[['Relacion_Video', 'Emocion']] = df_comentarios['Comentario'].progress_apply(
            lambda x: analizar_con_llm(x, tema_del_video)
        )

        emocion_mas_repetida = df_comentarios['Emocion'].mode()[0]
        df_comentarios['Emocion_Dominante'] = emocion_mas_repetida

        print("\n--- PRIMEROS RESULTADOS ---")
        print(df_comentarios.head())

        print(f"\n[INFO] La emoción dominante en todo el video fue: {emocion_mas_repetida}")

        nombre_archivo = "comentarios_analizados_llm.csv"
        df_comentarios.to_csv(nombre_archivo, index=False, encoding='utf-8-sig')
        print(f"\n¡Proceso terminado exitosamente! Revisa el archivo '{nombre_archivo}'")

        # 4. Cargar los datos en la pestaña del CSV
        mostrar_csv_en_gui(df_comentarios, tree_csv)

    except Exception as e:
        print(f"\nError durante la ejecución: {e}")
    finally:
        boton_inicio.config(state=tk.NORMAL)  # Rehabilita el botón


def mostrar_csv_en_gui(df, tree):
    """Muestra el DataFrame de Pandas en el widget Treeview de Tkinter"""
    tree.delete(*tree.get_children())

    columnas = list(df.columns)
    tree["columns"] = columnas
    tree["show"] = "headings"

    for col in columnas:
        tree.heading(col, text=col)
        tree.column(col, width=150, anchor="w")

    for index, row in df.iterrows():
        tree.insert("", "end", values=list(row))


def iniciar_interfaz():
    """Construye la ventana principal de Tkinter"""
    root = tk.Tk()
    root.title("Analizador de Comentarios de YouTube con Ollama")
    root.geometry("900x600")

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # --- Pestaña 1: Consola ---
    frame_consola = ttk.Frame(notebook)
    notebook.add(frame_consola, text="Terminal de Procesos")

    consola_texto = scrolledtext.ScrolledText(frame_consola, wrap=tk.WORD, font=("Consolas", 10))
    consola_texto.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    redireccion = RedirigirConsola(consola_texto)
    sys.stdout = redireccion
    sys.stderr = redireccion

    # --- Pestaña 2: Visualizador CSV ---
    frame_csv = ttk.Frame(notebook)
    notebook.add(frame_csv, text="Visualizador de Datos (CSV)")

    scroll_y = ttk.Scrollbar(frame_csv, orient="vertical")
    scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
    scroll_x = ttk.Scrollbar(frame_csv, orient="horizontal")
    scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

    tree = ttk.Treeview(frame_csv, yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
    tree.pack(fill=tk.BOTH, expand=True)

    scroll_y.config(command=tree.yview)
    scroll_x.config(command=tree.xview)

    # --- Pestaña 3: Visualizador de Transcripción (¡NUEVO!) ---
    frame_transcripcion = ttk.Frame(notebook)
    notebook.add(frame_transcripcion, text="Visualizador de Transcripción")

    # Área de texto con barra de desplazamiento para ver toda la transcripción
    texto_transcripcion = scrolledtext.ScrolledText(frame_transcripcion, wrap=tk.WORD, font=("Arial", 11))
    texto_transcripcion.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # --- Botón de Ejecución ---
    frame_boton = tk.Frame(root)
    frame_boton.pack(fill=tk.X, pady=10)

    # El botón ahora pasa 'texto_transcripcion' a la función ejecutar_proceso
    btn_iniciar = tk.Button(frame_boton, text="Iniciar Análisis", font=("Arial", 12, "bold"), bg="#4CAF50", fg="white",
                            command=lambda: threading.Thread(target=ejecutar_proceso,
                                                             args=(tree, texto_transcripcion, btn_iniciar),
                                                             daemon=True).start())
    btn_iniciar.pack()

    root.mainloop()


if __name__ == "__main__":
    iniciar_interfaz()