package com.talentlens.kafka.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class SourcingResultMessage {
    private String taskId;
    private String searchId;
    private String runId;
    private String status;
    private int candidatesFound;
    private String error;
    private Instant completedAt;
}
