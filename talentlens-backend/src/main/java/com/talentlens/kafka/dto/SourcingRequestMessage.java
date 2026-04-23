package com.talentlens.kafka.dto;

import com.talentlens.model.embedded.ParsedJd;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SourcingRequestMessage {
    private String taskId;
    private String searchId;
    private String runId;
    private ParsedJd parsedJd;
    private List<String> platforms;
    private Instant timestamp;
}
