package com.point85.mes.bridge;

import io.grpc.Server;
import io.grpc.netty.shaded.io.grpc.netty.NettyServerBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.InetSocketAddress;
import java.util.concurrent.TimeUnit;

/**
 * Entry point for the MES Kafka → gRPC bridge sidecar.
 *
 * <p>This process is launched as a child subprocess by the Python
 * {@code KafkaJavaBridgePlugin} via {@code asyncio.create_subprocess_exec}.
 * It listens on loopback only (127.0.0.1) so it is never exposed externally.
 *
 * <p>Command-line arguments (all optional):
 * <pre>
 *   --port               &lt;int&gt;   gRPC listen port          (default 50051)
 *   --bind-address       &lt;str&gt;   bind interface            (default 127.0.0.1)
 *   --bootstrap-servers  &lt;str&gt;   Kafka bootstrap.servers   (default localhost:9092)
 * </pre>
 *
 * <p>Build:
 * <pre>
 *   mvn -f bridge/pom.xml clean package -q
 * </pre>
 *
 * <p>Run:
 * <pre>
 *   java -jar bridge/target/kafka-bridge-1.0.0-shaded.jar \
 *        --port 50051 --bootstrap-servers broker1:9092,broker2:9092
 * </pre>
 */
public class KafkaBridgeServer {

    private static final Logger LOG = LoggerFactory.getLogger(KafkaBridgeServer.class);

    public static void main(String[] args) throws Exception {
        // ── Parse CLI arguments ────────────────────────────────────────────
        int    port             = 50051;
        String bindAddress      = "127.0.0.1";
        String bootstrapServers = "localhost:9092";

        for (int i = 0; i < args.length - 1; i++) {
            switch (args[i]) {
                case "--port":              port             = Integer.parseInt(args[i + 1]); break;
                case "--bind-address":      bindAddress      = args[i + 1];                  break;
                case "--bootstrap-servers": bootstrapServers = args[i + 1];                  break;
                default:                                                                       break;
            }
        }

        // ── Build gRPC server ──────────────────────────────────────────────
        KafkaBridgeServiceImpl service = new KafkaBridgeServiceImpl(bootstrapServers);

        Server server = NettyServerBuilder
                .forAddress(new InetSocketAddress(bindAddress, port))
                .addService(service)
                // Limit max inbound message to 32 MB (Kafka messages can be large)
                .maxInboundMessageSize(32 * 1024 * 1024)
                .build()
                .start();

        // Signal to the Python parent that the bridge is ready.
        // The Python plugin reads stdout lines looking for this marker.
        System.out.printf("KafkaBridge ready on %s:%d (broker=%s)%n",
                bindAddress, port, bootstrapServers);
        System.out.flush();

        LOG.info("KafkaBridge gRPC server started on {}:{} (broker={})",
                bindAddress, port, bootstrapServers);

        // ── Shutdown hook ──────────────────────────────────────────────────
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            LOG.info("Shutdown signal received — stopping gRPC server");
            server.shutdown();
            try {
                if (!server.awaitTermination(10, TimeUnit.SECONDS)) {
                    LOG.warn("Server did not terminate in time — forcing shutdown");
                    server.shutdownNow();
                }
            } catch (InterruptedException e) {
                server.shutdownNow();
                Thread.currentThread().interrupt();
            }
            service.close();
        }, "grpc-shutdown-hook"));

        server.awaitTermination();
    }
}
