from pytubefix import YouTube#Se importa la libreria para descargar videos de youtube
import ffmpeg
import os

def renombrarCancion(nombre):
    caracteresInvalidos=['<','>',':','"','/','\\','|','?','*'," "]
    for caracter in caracteresInvalidos:
        nombre=nombre.replace(caracter,'_')
    return nombre

url="https://www.youtube.com/watch?v=uLibS8Wgr9g"#Se almacena la url del video
ytObj=YouTube(url)#Se crea un objeto YouTube con la url del video
tituloVideo=renombrarCancion(ytObj.title)#Se obtiene el titulo del video y se limpia de simbolos especiales
nombreVideoEntrada="audio_files/" +tituloVideo+".mp4"#Nombre con el que se descarga
nombreVideoSalida="audio_files/" +tituloVideo+".mp3"#Se define el nombre con el que se va a convertir a mp3

variantes=ytObj.streams.get_highest_resolution()

contadorNombre=1
while os.path.exists(nombreVideoSalida):#Se verifica si el archivo ya existe
    nombreVideoEntrada=f"audio_files/{tituloVideo}_{contadorNombre}.mp4"
    nombreVideoSalida=f"audio_files/{tituloVideo}_{contadorNombre}.mp3"
    contadorNombre+=1


variantes.download(output_path="audio_files",filename=os.path.basename(nombreVideoEntrada))#Se descarga el video en la carpeta videos
print("Video descargado con éxito...!")
try: 
    ffmpeg.input(nombreVideoEntrada).output(nombreVideoSalida).run(quiet=True)
    if os.path.exists(nombreVideoSalida):
        print(f"El video ha sido convertido a MP3: {nombreVideoSalida}")
        os.remove(nombreVideoEntrada)
        metadatosVideo=ffmpeg.probe(nombreVideoSalida)
        print(metadatosVideo)
except Exception as error:
    print(f"Error:{error}")


"""
from pydub import AudioSegment
from pydub.playback import play

archivo="audio_files/Avicii_-_Waiting_For_Love.mp3"
metadatosGenerales=ffmpeg.probe(archivo)
#print("Metadatos del archivo de audio:")

metadatosStreams=metadatosGenerales["streams"][0]
metadatosFormat=metadatosGenerales["format"]
#print(metadatosFormat["filename"],type(metadatosFormat["filename"]))
print(metadatosStreams)
print(metadatosStreams["codec_name"],type(metadatosStreams["codec_name"]))
print(metadatosStreams["sample_rate"],type(metadatosStreams["sample_rate"]))
print(metadatosStreams["channels"],type(metadatosStreams["channels"]))
print(metadatosStreams["duration"],type(metadatosStreams["duration"]))
print(metadatosStreams["bit_rate"],type(metadatosStreams["bit_rate"]))

def reproducir_audio(archivo_mp3):
    try:
        audio=AudioSegment.from_mp3(archivo_mp3)
        print(audio.channels)
        print("Reproduciendo audio...")
        play(audio)
    except Exception as e:
        print(f"Error al reproducir el archivo: {str(e)}")
reproducir_audio(archivo)
"""
"""import sys; sys.path.append("gRPC_Proto")
from gRPC_Proto import G4_Audio_pb2_grpc, G4_Audio_pb2
import grpc
from pydub import AudioSegment
import io
from pydub.playback import play
canal = grpc.insecure_channel("localhost:50051")
stub = G4_Audio_pb2_grpc.AudioStub(canal)

if __name__ == "__main__":
    # Primero recibimos el encabezado WAV (primeros 44 bytes)
    header = io.BytesIO()
    request = G4_Audio_pb2.cancionS(archivo="DMAX_FEST.mp3")
    

    # Ahora recibimos el resto del audio
    audio_data = io.BytesIO()
    
    for response in stub.getStreamAudio(iter([request])):
        audio_data.write(response.cancionB)
    
    # Reproducir todo el audio recibido
    audio_data.seek(0)
    song = AudioSegment.from_wav(audio_data)
    play(song)
"""