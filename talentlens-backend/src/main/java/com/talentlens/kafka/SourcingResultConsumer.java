package com.talentlens.kafka;

import com.talentlens.kafka.dto.SourcingResultMessage;
import com.talentlens.service.SourcingService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class SourcingResultConsumer {

    private final SourcingService sourcingService;

    @KafkaListener(
            topics = "${app.kafka.topics.sourcing-results}",
            groupId = "${spring.kafka.consumer.group-id}",
            containerFactory = "kafkaListenerContainerFactory"
    )
    public void consume(SourcingResultMessage message) {
        log.info("Received sourcing result: taskId={}, searchId={}, runId={}, status={}",
                message.getTaskId(), message.getSearchId(), message.getRunId(), message.getStatus());
        try {
            sourcingService.processSourcingResult(message);
        } catch (Exception ex) {
            log.error("Failed to process sourcing result for taskId={}: {}",
                    message.getTaskId(), ex.getMessage(), ex);
        }
    }
}
