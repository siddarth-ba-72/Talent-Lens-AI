package com.talentlens;

import com.talentlens.kafka.dto.SourcingRequestMessage;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class TalentlensBackendApplicationTests {

    @MockBean
    KafkaTemplate<String, SourcingRequestMessage> kafkaTemplate;

    @Test
    void contextLoads() {
    }
}
