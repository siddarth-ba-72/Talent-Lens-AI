package com.talentlens.kafka;

import com.talentlens.exception.AiServiceException;
import com.talentlens.kafka.dto.SourcingRequestMessage;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

@Component
@RequiredArgsConstructor
@Slf4j
public class SourcingRequestProducer {

    private final KafkaTemplate<String, SourcingRequestMessage> kafkaTemplate;

    @Value("${app.kafka.topics.sourcing-requests}")
    private String topic;

    public void send(SourcingRequestMessage message) {
        try {
            kafkaTemplate.send(topic, message.getSearchId(), message)
                    .get(10, TimeUnit.SECONDS);
            log.info("Published sourcing request: searchId={}, runId={}", message.getSearchId(), message.getRunId());
        } catch (ExecutionException | InterruptedException | TimeoutException ex) {
            log.error("Failed to publish sourcing request for searchId={}", message.getSearchId(), ex);
            Thread.currentThread().interrupt();
            throw new AiServiceException("Failed to enqueue sourcing request. Please try again.");
        }
    }
}
