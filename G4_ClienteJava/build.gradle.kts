import com.google.protobuf.gradle.*
import org.gradle.api.tasks.JavaExec
plugins {
    id("java")
    id("com.google.protobuf") version "0.9.4"
    id("application")
}

repositories {
    mavenCentral()
}

dependencies {
    implementation("org.jline:jline:3.29.0")
    implementation("org.fusesource.jansi:jansi:2.4.1")
    implementation("io.grpc:grpc-netty-shaded:1.72.0")
    implementation("io.grpc:grpc-protobuf:1.72.0")
    implementation("io.grpc:grpc-stub:1.72.0")
    implementation("com.google.protobuf:protobuf-java:4.30.2")
    implementation("javax.annotation:javax.annotation-api:1.3.2")

    // Opcional: logging simple
    implementation("org.slf4j:slf4j-simple:2.0.12")

    testImplementation(platform("org.junit:junit-bom:5.10.0"))
    testImplementation("org.junit.jupiter:junit-jupiter")
}

// Configuración del plugin protobuf
protobuf {
    protoc {
        artifact = "com.google.protobuf:protoc:4.30.2"
    }
    plugins {
        register("grpc") {
            artifact = "io.grpc:protoc-gen-grpc-java:1.72.0"
        }
    }
    generateProtoTasks {
        all().forEach {
            it.plugins {
                id("grpc")
            }
        }
    }
}

// Donde están tus .proto
sourceSets {
    main {
        proto {
            srcDir("src/main/java/gRPC_Proto")
        }
    }
}

// Configuración para poder hacer `gradlew run`
application {
    mainClass.set("Cliente.G4_Cliente")
    //applicationDefaultJvmArgs=listOf("-Dfile.encoding=UTF-8")
}

tasks.getByName("run", JavaExec::class) {
 standardInput = System.`in`
}
