import sys; sys.path.append("gRPC_Proto")
from gRPC_Proto import G4_Audio_pb2_grpc 
from gRPC_Proto import G4_Audio_pb2
import grpc
import pyaudio
import threading
import time
import getpass
class clienteCancion:

    def __init__(self):
        self.controlPausa=""
        self.salir=False 
        self.hilo=True
        self.tiempoTranscurrido=0.0
        self.duracionTotal=0.0
        self.iniciar=False
        self.totalBytesRecibidos=0

    def controlAudio(self):
        while not self.iniciar:
            pass
        print("\nControles: 1=Pausa, 2=Reanudar, 3=Salir")
        while self.hilo:
            teclado=getpass.getpass("")
            if teclado=="1" and not self.controlPausa=="Pausar":
                self.controlPausa="Pausar"
                print("\nPausa...!")
            elif teclado=="2" and not self.controlPausa=="":
                self.controlPausa="Reanudar"
                print("\nReanudar...!")
            elif teclado=="3":
                self.controlPausa=""
                self.salir=True
                print("\nSalir...!")
                break
            time.sleep(0.1)

    def formatoTiempo(self,segundos):
        minutos=int(segundos)//60
        segundosRestantes=int(segundos) % 60
        return f"{minutos:02}:{segundosRestantes:02}"

    def mostrarTiempo(self):
        barra_total=30
        while not self.iniciar:
            pass

        while self.hilo:
            porcentaje=min(self.tiempoTranscurrido/ self.duracionTotal, 1.0) if self.duracionTotal > 0 else 0
            bloques_llenos=int(barra_total * porcentaje)
            bloques_vacios=barra_total - bloques_llenos

            barra="["+"█"*bloques_llenos+"-"*bloques_vacios+"]"

            tiempo_actual=self.formatoTiempo(self.tiempoTranscurrido)
            tiempo_total=self.formatoTiempo(self.duracionTotal)

            sys.stdout.write(f"\r{barra}{tiempo_actual} / {tiempo_total}")
            sys.stdout.flush()
        #Una vez que la canción haya terminado, actualizar la barra de progreso hasta el final
        if self.salir:
            sys.stdout.write(f"\r[{'█' * barra_total}]  {self.formatoTiempo(self.duracionTotal)} / {self.formatoTiempo(self.duracionTotal)}\n")
            sys.stdout.flush()

        
    
    def iniciarReproduccion(self, stub, nombreArchivo):
        metadatos=stub.getMetadatos(G4_Audio_pb2.metadatosS(archivo=nombreArchivo))
        sampleRate=metadatos.sampleRate
        canales=metadatos.canales
        self.duracionTotal=metadatos.duracion 
        pyAudio=pyaudio.PyAudio()
        self.hilo=True
        threading.Thread(target=self.controlAudio).start()
        threading.Thread(target=self.mostrarTiempo).start()
        cancionS=G4_Audio_pb2.cancionS(archivo=nombreArchivo)
         
        flujoReproduccionAudio=pyAudio.open(
            format=pyaudio.paInt16,#Formato de audio: 'paInt16' representa audio de 16 bits por muestra (calidad común)
            channels=canales,#Número de canales de audio: 2 para estéreo (si fuera 1, sería mono)
            rate=sampleRate,#Tasa de muestreo: 44100 Hz es la estándar en audio CD
            output=True,#Especifica que el flujo será para salida (reproducción de audio)
            frames_per_buffer=1024#Tamaño de los bloques de datos de audio a procesar: 1024 frames por buffer
        )

        bufferDatos=[]#Se define un buffer para acumular chunks mientras estás en pausa
        inicioCancion=True

        for chunk in stub.getStreamAudio(iter([cancionS])):
            if(chunk==b"Fin"):
                return
            if inicioCancion:
                inicioCancion=False
                self.iniciar=True

            self.totalBytesRecibidos+=len(chunk.cancionB)
            if self.controlPausa=="Pausar":
                #print("Pausando reproducción... enviando señal al servidor.")
                mensaje=G4_Audio_pb2.cancionS(archivo="Pausar")
                stub.getStreamAudio(iter([mensaje]))  # Solo mandamos el mensaje
                bufferDatos.append(chunk.cancionB)  # Guardamos el chunk que ya llegó
                time.sleep(0.5)  # Esperamos mientras el usuario está en pausa
                continue  # No reproducimos nada aún

            elif self.controlPausa == "Reanudar":
                mensaje = G4_Audio_pb2.cancionS(archivo="Reanudar")
                stub.getStreamAudio(iter([mensaje]))  # Solo mandamos el mensaje
                self.controlPausa = ""

                if bufferDatos:
                    for datos_guardados in bufferDatos:
                        flujoReproduccionAudio.write(datos_guardados)
                    bufferDatos.clear()

            else:
                flujoReproduccionAudio.write(chunk.cancionB)
                self.tiempoTranscurrido+=len(chunk.cancionB)/(sampleRate*2*canales)

            if self.salir:
                mensaje=G4_Audio_pb2.cancionS(archivo="Salir")
                stub.getStreamAudio(iter([mensaje]))
                return



        flujoReproduccionAudio.stop_stream()
        flujoReproduccionAudio.close()
        pyAudio.terminate()

if __name__=="__main__":
    cliente=clienteCancion()
    canal=grpc.insecure_channel("192.168.100.9:50051")
    stub=G4_Audio_pb2_grpc.AudioStub(canal)
    while True:#Se inicia un bucle infinito para mostrar el menú de opciones
        cliente.hilo=False
        cliente.iniciar=True
        cliente.tiempoTranscurrido=0.0
        cliente.duracionTotal=0.0
        cliente.controlPausa=""
        cliente.salir=False
        print()
        print("""\n*****Menú de opciones******
1.Escuchar Canciones
2.Salir""")
        opcionMenu=input("Ingrese una opción:")#Se solicita al usuario que ingrese una opción
        if opcionMenu not in ["1","2"]:#Se valida la opción ingresada
            print("Eliga una opción válida...!")
            continue

        if opcionMenu=="1":#Se selecciona la opción de escuchar canciones
            
            listaCancionesR=stub.getListaCanciones(G4_Audio_pb2.listaCancionesS()).listaCanciones
            while True:
                print("\n"+"*"*5+"Canciones Disponibles"+"*"*5)
                for i,cancion in enumerate(listaCancionesR):
                    print(f"{i+1}.-{cancion.replace(".mp3","")}")
                print("*"*27)

                indiceCancion=input("Ingrese el número de la canción: ")
                
                if not indiceCancion.isdigit() or int(indiceCancion)<1 or int(indiceCancion)>len(listaCancionesR):#Se valida el número ingresado
                    print("El número ingresado no es válido...!")
                else:
                    break
            print(f"Reproduciendo:{listaCancionesR[int(indiceCancion)-1]}")
            cliente.iniciarReproduccion(stub,listaCancionesR[int(indiceCancion)-1])
               


        elif opcionMenu=="2":#Se selecciona la opción de salir
            print("Saliendo del programa...!")
            break

#sudo apt install portaudio19-dev python3-dev build-essential

