package com.point85.mes.bridge;

import com.google.protobuf.ByteString;
import com.point85.mes.bridge.proto.*;
import io.grpc.Status;
import io.grpc.stub.StreamObserver;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.serialization.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;

/**
 * gRPC service implementation.  Wraps the official Apache Kafka Java SDK
 * ({@code kafka-clients}) and exposes three RPCs:
 *
 * <ul>
 *   <li>{@link #subscribe} — server-side streaming: consumes from Kafka and
 *       streams every record to the Python MES plugin as a {@link KafkaMessage}.</li>
 *   <li>{@link #publish} — unary: produces one message to Kafka.</li>
 *   <li>{@link #healthCheck} — unary: returns bridge version + broker reachability.</li>
 * </ul>
 *
 * <p>Each {@code Subscribe} call runs its own {@link KafkaConsumer} on a
 * dedicated daemon thread from {@code consumerExecutor} so that the gRPC
 * event-loop thread is never blocked.
 */
public class KafkaBridgeServiceImpl extends KafkaBridgeGrpc.KafkaBridgeImplBase
        implements AutoCloseable {

    private static final Logger LOG = LoggerFactory.getLogger(KafkaBridgeServiceImpl.class);
    private static final String VERSION = "1.0.0";

    private final String bootstrapServers;

    /**
     * Thread pool for Kafka consumer loops.  Each active Subscribe RPC owns
     * one thread.  Threads are daemon so they do not prevent JVM shutdown.
     */
    private final ExecutorService consumerExecutor = Executors.newCachedThreadPool(r -> {
        Thread t = new Thread(r, "kafka-consumer-" + System.nanoTime());
        t.setDaemon(true);
        return t;
    });

    public KafkaBridgeServiceImpl(String bootstrapServers) {
        this.bootstrapServers = bootstrapServers;
    }

    // ── Subscribe (server-side streaming) ────────────────────────────────────

    /**
     * Opens a {@link KafkaConsumer}, subscribes to the requested topics, polls
     * in a tight loop, and streams each record back to the Python client.
     *
     * <p>The loop continues until:
     * <ul>
     *   <li>The gRPC client cancels the stream (context is cancelled).</li>
     *   <li>The thread is interrupted (bridge is shutting down).</li>
     *   <li>An unrecoverable Kafka error is thrown.</li>
     * </ul>
     */
    @Override
    public void subscribe(SubscribeRequest request,
                          StreamObserver<KafkaMessage> responseObserver) {

        List<String> topics = request.getTopicsList();
        String group = request.getConsumerGroup().isEmpty()
                ? "mes-kafka-bridge"
                : request.getConsumerGroup();
        long pollMs = request.getPollTimeoutMs() > 0 ? request.getPollTimeoutMs() : 1000L;

        LOG.info("Subscribe RPC: topics={} group={} pollMs={}", topics, group, pollMs);

        consumerExecutor.submit(() -> {
            Properties props = buildConsumerProps(group);
            try (KafkaConsumer<String, byte[]> consumer = new KafkaConsumer<>(props)) {
                consumer.subscribe(topics);

                while (!Thread.currentThread().isInterrupted()) {
                    ConsumerRecords<String, byte[]> records =
                            consumer.poll(Duration.ofMillis(pollMs));

                    for (ConsumerRecord<String, byte[]> record : records) {
                        KafkaMessage msg = toProto(record);
                        // onNext is thread-safe in the gRPC Netty implementation
                        responseObserver.onNext(msg);
                    }
                }

                responseObserver.onCompleted();

            } catch (Exception e) {
                LOG.error("Consumer error for topics {}: {}", topics, e.getMessage(), e);
                responseObserver.onError(
                        Status.INTERNAL
                                .withDescription(e.getMessage())
                                .withCause(e)
                                .asRuntimeException());
            }
        });
    }

    // ── Publish (unary) ───────────────────────────────────────────────────────

    /**
     * Produces a single message to Kafka.
     *
     * <p>A new {@link KafkaProducer} is created per call.  For high-throughput
     * scenarios, consider caching a shared producer; the current design keeps
     * the bridge stateless and easy to reason about.
     */
    @Override
    public void publish(PublishRequest request,
                        StreamObserver<PublishResponse> responseObserver) {

        Properties props = new Properties();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG,      bootstrapServers);
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG,   StringSerializer.class.getName());
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, ByteArraySerializer.class.getName());
        props.put(ProducerConfig.ACKS_CONFIG,                   "all");
        props.put(ProducerConfig.RETRIES_CONFIG,                3);
        props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG,     true);

        try (KafkaProducer<String, byte[]> producer = new KafkaProducer<>(props)) {

            String key   = request.getKey().isEmpty() ? null : request.getKey();
            byte[] value = request.getValue().toByteArray();

            ProducerRecord<String, byte[]> record =
                    new ProducerRecord<>(request.getTopic(), key, value);

            // Propagate gRPC headers as Kafka record headers
            request.getHeadersMap().forEach((k, v) ->
                    record.headers().add(k, v.getBytes(StandardCharsets.UTF_8)));

            RecordMetadata meta = producer.send(record).get(10, TimeUnit.SECONDS);

            LOG.debug("Published to {}:{}@{}", meta.topic(), meta.partition(), meta.offset());
            responseObserver.onNext(PublishResponse.newBuilder()
                    .setSuccess(true)
                    .setPartition(meta.partition())
                    .setOffset(meta.offset())
                    .build());

        } catch (Exception e) {
            LOG.warn("Publish failed for topic {}: {}", request.getTopic(), e.getMessage());
            responseObserver.onNext(PublishResponse.newBuilder()
                    .setSuccess(false)
                    .setError(e.getMessage() != null ? e.getMessage() : e.getClass().getName())
                    .build());
        }

        responseObserver.onCompleted();
    }

    // ── Health check (unary) ──────────────────────────────────────────────────

    /**
     * Verifies broker connectivity by calling {@link KafkaConsumer#listTopics}
     * with a short timeout.  The Python plugin polls this during start-up.
     */
    @Override
    public void healthCheck(HealthRequest request,
                            StreamObserver<HealthResponse> responseObserver) {

        boolean healthy = checkBrokerConnectivity();

        responseObserver.onNext(HealthResponse.newBuilder()
                .setHealthy(healthy)
                .setVersion(VERSION)
                .setKafkaBroker(bootstrapServers)
                .build());
        responseObserver.onCompleted();
    }

    // ── AutoCloseable ─────────────────────────────────────────────────────────

    @Override
    public void close() {
        consumerExecutor.shutdownNow();
        try {
            if (!consumerExecutor.awaitTermination(5, TimeUnit.SECONDS)) {
                LOG.warn("Consumer executor did not terminate cleanly");
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    // ── Private helpers ───────────────────────────────────────────────────────

    private Properties buildConsumerProps(String groupId) {
        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG,        bootstrapServers);
        props.put(ConsumerConfig.GROUP_ID_CONFIG,                 groupId);
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG,   StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, ByteArrayDeserializer.class.getName());
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG,        "latest");
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG,       "true");
        props.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG,         "500");
        // Allow the consumer to be closed promptly when the thread is interrupted
        props.put(ConsumerConfig.REQUEST_TIMEOUT_MS_CONFIG,       "5000");
        props.put(ConsumerConfig.SESSION_TIMEOUT_MS_CONFIG,       "10000");
        return props;
    }

    private KafkaMessage toProto(ConsumerRecord<String, byte[]> record) {
        KafkaMessage.Builder builder = KafkaMessage.newBuilder()
                .setTopic(record.topic())
                .setPartition(record.partition())
                .setOffset(record.offset())
                .setKey(record.key() != null ? record.key() : "")
                .setValue(ByteString.copyFrom(
                        record.value() != null ? record.value() : new byte[0]))
                .setTimestampMs(record.timestamp());

        record.headers().forEach(h ->
                builder.putHeaders(
                        h.key(),
                        new String(h.value(), StandardCharsets.UTF_8)));

        return builder.build();
    }

    private boolean checkBrokerConnectivity() {
        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG,        bootstrapServers);
        props.put(ConsumerConfig.GROUP_ID_CONFIG,                 "__mes_health__");
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG,   StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, ByteArrayDeserializer.class.getName());
        props.put(ConsumerConfig.REQUEST_TIMEOUT_MS_CONFIG,       "3000");
        props.put(ConsumerConfig.DEFAULT_API_TIMEOUT_MS_CONFIG,   "3000");
        try (KafkaConsumer<String, byte[]> consumer = new KafkaConsumer<>(props)) {
            consumer.listTopics(Duration.ofSeconds(3));
            return true;
        } catch (Exception e) {
            LOG.debug("Health check broker connectivity failed: {}", e.getMessage());
            return false;
        }
    }
}
