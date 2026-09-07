from youtube_comment_downloader import *
import pandas as pd
import ollama
import json
from tqdm import tqdm


def obtener_comentarios(url_video, limite=None):
    downloader = YoutubeCommentDownloader()
    generador = downloader.get_comments_from_url(url_video, sort_by=SORT_BY_POPULAR)

    lista_comentarios = []
    print("Descargando comentarios. Esto puede tardar un momento...")

    for i, comentario in enumerate(generador):
        if limite is not None and i >= limite:
            break
        lista_comentarios.append(comentario['text'])

    df = pd.DataFrame(lista_comentarios, columns=['Comentario'])
    print(f"¡Listo! Se descargaron {len(df)} comentarios.")
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
        print(f"\n[ERROR EN OLLAMA]: {e}")
        return pd.Series(["Error", "Error"])


if __name__ == "__main__":
    url_del_video = "https://youtu.be/XOtLLlQ7OgM"
    tema_del_video = "Un chico se disfraza e interactúa en la vida real como las emociones de la película Intensamente 2"

    df_comentarios = obtener_comentarios(url_del_video, limite=None)

    print("\nPasando los comentarios al LLM local (Ollama)...")
    tqdm.pandas(desc="Progreso LLM")

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