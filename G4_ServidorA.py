import sys; sys.path.append("gRPC_Proto")
from gRPC_Proto import G4_Audio_pb2_grpc 
from gRPC_Proto import G4_Audio_pb2
import grpc
import os
from concurrent import futures
import ffmpeg
import time
from pydub.playback import play
class ServidorAudio(G4_Audio_pb2_grpc.AudioServicer):
    carpeta="audio_files"
    pausado=False
    def getListaCanciones(self, request, context):
        listaCanciones=os.listdir(self.carpeta)
        return G4_Audio_pb2.listaCancionesR(listaCanciones=listaCanciones)
    
    def getMetadatos(self, request, context):
        archivo=request.archivo
        rutaArchivo=f"{self.carpeta}/{archivo}"
        if not os.path.exists(rutaArchivo):
            print(f"El archivo {archivo} no existe.")
            return
        metadatosGenerales=ffmpeg.probe(rutaArchivo)
        metadatosStreams=metadatosGenerales["streams"][0]
        metadatosFormat=metadatosGenerales["format"]  
        #print(metadatosStreams["duration"]) 
        #print(float(metadatosStreams["duration"])) 
        #print(metadatosGenerales)
        return G4_Audio_pb2.metadatosR(
            filename=metadatosFormat["filename"],
            codecName=metadatosStreams["codec_name"],
            sampleRate=int(metadatosStreams["sample_rate"]),
            canales=int(metadatosStreams["channels"]),
            duracion=float(metadatosStreams["duration"]),
            bitRate=int(metadatosStreams["bit_rate"])
        )

    def getStreamAudio(self, request_iterator,context):
        self.pausado=False
        for request in request_iterator:
            archivo=request.archivo
            print(archivo)
            if archivo=="Salir":
                print("Recibida señal de salida, cerrando el canal.")
                self.pausado=False
                return
            if archivo=="Pausar":
                self.pausado=True
                continue
            elif archivo=="Reanudar":
                self.pausado=False
                continue

            rutaArchivo=f"{self.carpeta}/{archivo}"
            if not os.path.exists(rutaArchivo):
                print(f"El archivo {archivo} no existe.")
                return
       
            procesoWAV=(
                ffmpeg
                .input(rutaArchivo)
                .output('pipe:1', format='wav')
                .global_args('-loglevel', 'quiet')
                .run_async(pipe_stdout=True)#pipe_stderr=False
            ) 
            
            while True:  
                if self.pausado:
                    time.sleep(0.1)  
                    continue
                cancionB=procesoWAV.stdout.read(1024)

                if not cancionB: 
                    yield G4_Audio_pb2.cancionR(cancionB=b"Fin")
                    procesoWAV.stdout.close()
                    procesoWAV.wait()    
                    return
                   
                    
                yield G4_Audio_pb2.cancionR(cancionB=cancionB)
            


                     
   




if __name__=="__main__":
    servidorgRPC=grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    G4_Audio_pb2_grpc.add_AudioServicer_to_server(ServidorAudio(),servidorgRPC)
    servidorgRPC.add_insecure_port("192.168.100.9:50051")
    print("Servidor gRPC escuchando en el puerto 50051...")
    servidorgRPC.start()
    #try:
    servidorgRPC.wait_for_termination()
    #except KeyboardInterrupt:
       # print("Servidor detenido...!")
       # servidorgRPC.stop(0)
