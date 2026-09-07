# Emociones

Cosas usadas:

youtube_comment_downloader: Se utiliza para descargar los comentarios del video

pandas: Se usa para estructurar la información en tablas, analizar datos como la emoción más repetida y exportar el resultado final a un archivo CSV

ollama: Sirve para comunicarse con un modelo de lenguaje local Llama 3.1 que se encarga de leer cada comentario, identificar si tiene relación con el video y detectar su emoción.

json: Se emplea para interpretar la respuesta del modelo de ia local y extraer fácilmente los datos de "relacion" y "emocion" en un formato estructurado.

tqdm: Se utiliza para generar una barra de progreso, lo que permite al usuario ver el avance mientras el modelo analiza todos los comentarios.
