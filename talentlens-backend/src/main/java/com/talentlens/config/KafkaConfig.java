package com.talentlens.config;

import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;

@Configuration
public class KafkaConfig {

    @Value("${app.kafka.topics.sourcing-requests}")
    private String sourcingRequestsTopic;

    @Value("${app.kafka.topics.sourcing-results}")
    private String sourcingResultsTopic;

    @Bean
    public NewTopic sourcingRequestsTopic() {
        return TopicBuilder.name(sourcingRequestsTopic)
                .partitions(1)
                .replicas(1)
                .build();
    }

    @Bean
    public NewTopic sourcingResultsTopic() {
        return TopicBuilder.name(sourcingResultsTopic)
                .partitions(1)
                .replicas(1)
                .build();
    }
}
