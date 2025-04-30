//sudo apt install openjdk-11.jdk
//./gradlew run --no-daemon --console=plain
package Cliente;

import G4_Audio.AudioGrpc;
import G4_Audio.G4Audio;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.stub.StreamObserver;
import javax.sound.sampled.*;
import java.util.ArrayList;
import java.util.List;
import java.util.Scanner;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

public class G4_Cliente{
    public static void main(String[]args)throws Exception{
        ManagedChannel channel=ManagedChannelBuilder.forAddress("192.168.100.9",50051)
            .usePlaintext()
            .build();

        AudioGrpc.AudioBlockingStub blockingStub=AudioGrpc.newBlockingStub(channel);
        AudioGrpc.AudioStub asyncStub=AudioGrpc.newStub(channel);

        ClienteCancion cliente=new ClienteCancion(asyncStub,blockingStub);
        Scanner sc=new Scanner(System.in);

        while(true){
            System.out.println("\n***** Menú de opciones ******");
            System.out.println("1. Escuchar Canciones");
            System.out.println("2. Salir");
            System.out.print("Ingrese una opción: ");

            String opcionMenu=sc.nextLine();

            if("2".equals(opcionMenu)){
                System.out.println("Saliendo...");
                break;
            }else if(!"1".equals(opcionMenu)){
                System.out.println("Opción inválida.");
                continue;
            }

            G4Audio.listaCancionesR listaResp=blockingStub.getListaCanciones(
                G4Audio.listaCancionesS.newBuilder().build()
            );
            List<String>listaCanciones=listaResp.getListaCancionesList();
            for(int i=0;i<listaCanciones.size();i++){
                System.out.printf("%d. %s\n",i+1,listaCanciones.get(i).replace(".mp3",""));
            }
            System.out.print("Selecciona número: ");

            int indiceCancion;
            try{
                indiceCancion=Integer.parseInt(sc.nextLine())-1;
            }catch(Exception e){
                System.out.println("Índice inválido.");
                continue;
            }
            if(indiceCancion<0||indiceCancion>=listaCanciones.size()){
                System.out.println("Índice fuera de rango.");
                continue;
            }

            cliente.iniciarReproduccion(listaCanciones.get(indiceCancion));
        }

        channel.shutdownNow().awaitTermination(5,TimeUnit.SECONDS);
        sc.close();
    }

    static class ClienteCancion{
        private final AudioGrpc.AudioStub asyncStub;
        private final AudioGrpc.AudioBlockingStub blockingStub;
        private volatile String controlPausa="";
        private volatile boolean salir=false;
        private volatile boolean hilo=true;
        private volatile boolean iniciar=false;
        private double tiempoTranscurrido=0.0;
        private double duracionTotal=0.0;
        private List<byte[]> bufferDatos=new ArrayList<>();
        private SourceDataLine audioLine;
        private Thread controlThread;
        private Thread progressThread;

        ClienteCancion(AudioGrpc.AudioStub asyncStub,
                      AudioGrpc.AudioBlockingStub blockingStub){
            this.asyncStub=asyncStub;
            this.blockingStub=blockingStub;
        }

        public void iniciarReproduccion(String nombreArchivo)throws Exception{
            G4Audio.metadatosR metadata=blockingStub.getMetadatos(
                G4Audio.metadatosS.newBuilder().setArchivo(nombreArchivo).build()
            );

            int sampleRate=metadata.getSampleRate();
            int canales=metadata.getCanales();
            this.duracionTotal=metadata.getDuracion();

            AudioFormat format=new AudioFormat(sampleRate,16,canales,true,false);
            DataLine.Info info=new DataLine.Info(SourceDataLine.class,format);
            this.audioLine=(SourceDataLine)AudioSystem.getLine(info);
            audioLine.open(format);
            audioLine.start();

            this.hilo=true;
            this.salir=false;
            this.controlPausa="";
            this.tiempoTranscurrido=0.0;
            this.bufferDatos.clear();

            controlThread=new Thread(this::controlAudio);
            progressThread=new Thread(this::mostrarTiempo);
            controlThread.start();
            progressThread.start();

            CountDownLatch finishLatch=new CountDownLatch(1);
            AtomicReference<StreamObserver<G4Audio.cancionS>> requestObserverRef=new AtomicReference<>();

            StreamObserver<G4Audio.cancionR> responseObserver=new StreamObserver<G4Audio.cancionR>(){
                @Override
                public void onNext(G4Audio.cancionR chunk){
                    if(chunk.getCancionB().equals("Fin")){
                        return;
                    }

                    if(!iniciar){
                        iniciar=true;
                    }

                    byte[] audioData=chunk.getCancionB().toByteArray();

                    if(controlPausa.equals("Pausar")){
                        requestObserverRef.get().onNext(
                            G4Audio.cancionS.newBuilder().setArchivo("Pausar").build()
                        );
                        bufferDatos.add(audioData);
                        try{
                            TimeUnit.MILLISECONDS.sleep(500);
                        }catch(InterruptedException e){
                            Thread.currentThread().interrupt();
                        }
                        return;
                    }else if(controlPausa.equals("Reanudar")){
                        requestObserverRef.get().onNext(
                            G4Audio.cancionS.newBuilder().setArchivo("Reanudar").build()
                        );
                        controlPausa="";

                        for(byte[] buffered:bufferDatos){
                            audioLine.write(buffered,0,buffered.length);
                            tiempoTranscurrido+=buffered.length/(double)(sampleRate*2*canales);
                        }
                        bufferDatos.clear();
                    }

                    if(salir){
                        requestObserverRef.get().onNext(
                            G4Audio.cancionS.newBuilder().setArchivo("Salir").build()
                        );
                        return;
                    }

                    audioLine.write(audioData,0,audioData.length);
                    tiempoTranscurrido+=audioData.length/(double)(sampleRate*2*canales);
                }

                @Override
                public void onError(Throwable t){
                    limpiarRecursos();
                    finishLatch.countDown();
                }

                @Override
                public void onCompleted(){
                    limpiarRecursos();
                    finishLatch.countDown();
                }
            };

            StreamObserver<G4Audio.cancionS> requestObserver=asyncStub.getStreamAudio(responseObserver);
            requestObserverRef.set(requestObserver);

            requestObserver.onNext(
                G4Audio.cancionS.newBuilder().setArchivo(nombreArchivo).build()
            );

            finishLatch.await();
            limpiarRecursos();
        }

        private void controlAudio(){
            Scanner scanner=new Scanner(System.in);
            while(!iniciar){
                try{
                    Thread.sleep(100);
                }catch(InterruptedException e){
                    Thread.currentThread().interrupt();
                    return;
                }
            }

            System.out.println("\nControles: 1=Pausa, 2=Reanudar, 3=Salir");

            while(hilo){
                String input=scanner.nextLine();
                if(input.equals("1")&&!controlPausa.equals("Pausar")){
                    controlPausa="Pausar";
                    System.out.println("\nPausa...!");
                }else if(input.equals("2")&&controlPausa.equals("Pausar")){
                    controlPausa="Reanudar";
                    System.out.println("\nReanudar...!");
                }else if(input.equals("3")){
                    controlPausa="";
                    salir=true;
                    hilo=false;
                    System.out.println("\nSalir...!");
                    break;
                }

                try{
                    Thread.sleep(100);
                }catch(InterruptedException e){
                    Thread.currentThread().interrupt();
                    return;
                }
            }
        }

        private String formatoTiempo(double segundos){
            int minutos=(int)segundos/60;
            int segundosRestantes=(int)segundos%60;
            return String.format("%02d:%02d",minutos,segundosRestantes);
        }

        private void mostrarTiempo(){
            final int barraTotal=30;

            while(!iniciar){
                try{
                    Thread.sleep(100);
                }catch(InterruptedException e){
                    Thread.currentThread().interrupt();
                    return;
                }
            }

            while(hilo){
                double porcentaje=(duracionTotal>0)?
                    Math.min(tiempoTranscurrido/duracionTotal,1.0):0;
                int bloquesLlenos=(int)(barraTotal*porcentaje);
                int bloquesVacios=barraTotal-bloquesLlenos;

                StringBuilder barra=new StringBuilder("[");
                barra.append("█".repeat(bloquesLlenos));
                barra.append("-".repeat(bloquesVacios));
                barra.append("]");

                String tiempoActual=formatoTiempo(tiempoTranscurrido);
                String tiempoTotal=formatoTiempo(duracionTotal);

                System.out.print("\r"+barra.toString()+" "+tiempoActual+" / "+tiempoTotal);

                try{
                    Thread.sleep(200);
                }catch(InterruptedException e){
                    Thread.currentThread().interrupt();
                    return;
                }
            }


        }

        private void limpiarRecursos(){
            hilo=false;

            if(audioLine!=null){
                audioLine.stop();
                audioLine.close();
            }

            if(controlThread!=null&&controlThread.isAlive()){
                controlThread.interrupt();
            }

            if(progressThread!=null&&progressThread.isAlive()){
                progressThread.interrupt();
            }
        }
    }
}
